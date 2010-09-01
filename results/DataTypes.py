from results.models import *
from django.core.cache import cache
import logging

class DataTable:
    def __init__(self, log):
        self.rows = cache.get('log%d' % log.id)
        if self.rows == None:
            logging.debug('Reloading %s from DB' % log)
            self.rows = list()
            scvars = self.preloadScenarioVars(log)
            results = self.loadResults(log)
            self.collateResults(results, scvars)
            cache.set('log%d' % log.id, self.rows)
        else:
            logging.debug('Loading %s from cache' % log)
    
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
            inv = res.Invocation
            if not scid in results:
                results[scid] = {}
            if not inv in results[scid]:
                results[scid][inv] = {}
            results[scid][inv][res.Key] = res.Value
        return results

    def collateResults(self, results, scenarios):
        for (sc_id,res) in results.iteritems():
            for (inv,cols) in res.iteritems():
                row = DataRow(scenarios[sc_id], inv)
                for (key,val) in cols.iteritems():
                    row.values[key] = val
                self.rows.append(row)

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


class DataRow:
    def __init__(self, scenario=None, invocation=-1):
        if scenario == None:
            scenario = {}
        if invocation == -1:
            self.values = {}
        else:
            self.values = {'invocation': invocation}
        self.scenario = scenario


class DataAggregate:
    def __init__(self, value=0, count=0, stdev=0):
        self.value = value
        self.count = count
        self.stdev = stdev
        self.sum = 0
        self.product = 1
        self.sqsum = 0
        self.type = ''
        
    def __unicode__(self):
        return "%.3f [n=%d]" % (self.value, self.count)