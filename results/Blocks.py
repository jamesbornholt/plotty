import math, copy
from results.DataTypes import *
import logging

class FilterBlock:
    def process(self, datatable, **kwargs):
        newRows = []
        for row in datatable:
            add = True
            for (key,val) in kwargs.items():
                if key not in row.scenario or row.scenario[key] <> val:
                    add = False
                    break
            if add:
                newRows.append(row)
        datatable.rows = newRows


class AggregateBlock:
    def process(self, datatable, **kwargs):
        groups = {}
        scenarios = {}
        invocation = kwargs['column'] == 'invocation'
        for row in datatable:
            if not invocation and kwargs['column'] not in row.scenario:
                continue
            schash = self.scenario_hash(scenario=row.scenario, exclude=kwargs['column'])
            if schash not in scenarios:
                groups[schash] = []
                scenarios[schash] = copy.copy(row.scenario)
                if not invocation:
                    del scenarios[schash][kwargs['column']]
            groups[schash].append(row.values)
        
        newRows = []
        for (sc, rows) in groups.items():
            aggregates = {}
            for row in rows:
                if 'invocation' in row:
                    del row['invocation']
                for (key,val) in row.items():
                    if key not in aggregates:
                        aggregates[key] = DataAggregate()
                    aggregates[key].sum += val
                    aggregates[key].product *= val
                    #logging.debug('product *= %s = %s' % (str(val), aggregates[key].product))
                    aggregates[key].sqsum += val * val
                    aggregates[key].count += 1
            for (key,agg) in aggregates.items():
                aggregates[key].type = 'mean'
                aggregates[key].value = agg.sum / agg.count
                if agg.count > 1:
                    aggregates[key].stdev = math.sqrt((1/(agg.count - 1)) * (agg.sqsum - (agg.count * agg.value * agg.value)))
                if kwargs['type'] == 'geomean':
                    aggregates[key].value = math.pow(agg.product, 1.0/agg.count)
                    #logging.debug(agg.product)
                    #logging.debug('geomean: %dth root of %s', (agg.count, str(agg.product)))
                    aggregates[key].type = 'geomean'
            newRow = DataRow()
            newRow.scenario = scenarios[sc]
            newRow.values = aggregates
            newRows.append(newRow)
        
        datatable.rows = newRows

    def scenario_hash(self, scenario, exclude):
        hashstr = ""
        for (key,val) in scenario.items():
            if not key == exclude:
                hashstr += key + val
        return hashstr