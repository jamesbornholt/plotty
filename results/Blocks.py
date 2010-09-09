import math, copy
from results.DataTypes import *
import logging

def scenario_hash(scenario, exclude):
    hashstr = ""
    for (key,val) in scenario.items():
        if not key == exclude:
            hashstr += key + val
    return hashstr

class FilterBlock:
    def process(self, datatable, filters):
        newRows = []
        for row in datatable:
            add = True
            for filt in filters:
                if filt['is']:
                    if filt['column'] not in row.scenario or row.scenario[filt['column']] <> filt['value']:
                        add = False
                        break
                else:
                    if filt['column'] in row.scenario and row.scenario[filt['column']] == filt['value']:
                        add = False
                        break
            if add:
                newRows.append(row)
        datatable.rows = newRows


class AggregateBlock:
    def process(self, datatable, **kwargs):
        groups = {}
        scenarios = {}
        for row in datatable:
            if kwargs['column'] not in row.scenario:
                continue
            schash = scenario_hash(scenario=row.scenario, exclude=kwargs['column'])
            if schash not in scenarios:
                groups[schash] = []
                scenarios[schash] = copy.copy(row.scenario)
                del scenarios[schash][kwargs['column']]
            groups[schash].append(row.values)
        
        newRows = []
        for (sc, rows) in groups.items():
            aggregates = {}
            for row in rows:
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


class NormaliseBlock:
    def process(self, datatable, **kwargs):
        scenarios = {}
        normalisers = {}
        for row in datatable:
            if kwargs['column'] not in row.scenario:
                continue
            schash = scenario_hash(scenario=row.scenario, exclude=kwargs['column'])
            if schash not in scenarios:
                scenarios[schash] = []
            scenarios[schash].append(row)
            if row.scenario[kwargs['column']] == kwargs['value']:
                normalisers[schash] = copy.copy(row.values)
        
        newRows = []
        
        logging.debug('%d scenarios' % len(scenarios))
        logging.debug('%d normalisers' % len(normalisers))
        
        for (sc, rows) in scenarios.items():
            if sc not in normalisers:
                continue
            for row in rows:
                for (key,val) in row.values.items():
                    if key not in normalisers[sc]:
                        del row.values[key]
                        continue
                    row.values[key] = row.values[key] / normalisers[sc][key]
                newRows.append(row)
        
        datatable.rows = newRows