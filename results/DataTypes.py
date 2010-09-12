from results.models import *
from django.core.cache import cache
import logging, sys

class DataTable:
    def __init__(self, logs):
        self.rows = []
        for log_id in logs:
            logging.debug('Attempting to load log ID %d from cache' % log_id)
            rows = cache.get('log%d' % log_id)
            if rows == None:
                rows = []
                log = Log.objects.filter(id=log_id)[0]
                logging.debug('Cache empty, reloading %s from DB' % log)
                scvars = self.preloadScenarioVars(log)
                results = self.loadResults(log)
                self.collateResults(results, scvars, rows)
                ret = cache.set('log%d' % log_id, rows)
                logging.debug('Storing %d rows to cache for log ID %d (object size %d)' % (len(rows), log_id, sys.getsizeof(rows)))
            else:
                logging.debug('Loaded %d rows from cache' % len(rows))
            self.rows.extend(rows)

    def __iter__(self):
        return iter(self.rows)

    def preloadScenarioVars(self, log):
        scvars = {}
        for scvar in ScenarioVar.objects.filter(Log=log):
            if not scvar.Scenario_id in scvars:
                scvars[scvar.Scenario_id] = {}
            scvars[scvar.Scenario_id][scvar.Key] = scvar.Value
        return scvars

    def loadResults(self, log):
        results = {}
        for res in Result.objects.filter(Log=log):
            scid = res.Scenario_id
            if not scid in results:
                results[scid] = {}
            results[scid][res.Key] = res.Value
        return results

    def collateResults(self, results, scenarios, rows):
        for (sc_id,cols) in results.iteritems():
            row = DataRow(scenarios[sc_id])
            row.values = cols
            rows.append(row)

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
