from django.core.cache import cache
import logging, sys, csv, os
from plotty import settings

def scenario_hash(scenario, exclude=[]):
    hashstr = ""
    for (key,val) in scenario.items():
        if key not in exclude:
            hashstr += key + val
    return hashstr

class DataTable:
    def __init__(self, logs):
        self.rows = []
        for log in logs:
            logging.debug('Attempting to load log %s from cache' % log)
            rows = cache.get(log)
            if rows == None:
                logging.debug('Cache empty, reloading %s from file' % log)
                rows = self.loadCSV(log)
                ret = cache.set(log, rows)
                logging.debug('Storing %d rows to cache for log %s' % (len(rows), log))
            else:
                logging.debug('Loaded %d rows from cache' % len(rows))
            self.rows.extend(rows)

    def __iter__(self):
        return iter(self.rows)

    def loadCSV(self, log):
        scenarios = {}
        
        reader = csv.DictReader(open(os.path.join(settings.BM_LOG_DIR, log), 'rb'))
        for line in reader:
            key = line.pop('key')
            value = line.pop('value')
            schash = scenario_hash(line)
            if schash not in scenarios:
                scenarios[schash] = DataRow(line)
            scenarios[schash].values[key] = float(value)
        
        return scenarios.values()

    def headers(self):
        scenarios = list()
        values = list()
        for row in self.rows:
            for key in row.scenario.iterkeys():
                if key not in scenarios:
                    scenarios.append(key)
            for val in row.values.iterkeys():
                if val not in values:
                    values.append(val)
        return scenarios, values
    
    def selectValueColumns(self, vals):
        for row in self.rows:
            for (key,val) in row.values.items():
                if key not in vals:
                    del row.values[key]
    def selectScenarioColumns(self, cols):
        for row in self.rows:
            for (key,val) in row.scenario.items():
                if key not in cols:
                    del row.scenario[key]


class DataRow:
    def __init__(self, scenario=None):
        if scenario == None:
            scenario = {}
        self.values = {}
        self.scenario = scenario


class DataAggregate:
    def __init__(self, value=0, count=0, stdev=0):
        # Actual values
        self.value = value
        self.count = count
        self.stdev = stdev
        self.min = float('+inf')
        self.max = float('-inf')
        
        # Intermediate values
        self.sum = 0
        self.product = 1
        self.sqsum = 0
        self.type = ''
        
    def __unicode__(self):
        return "%.3f [n=%d]" % (self.value, self.count)
