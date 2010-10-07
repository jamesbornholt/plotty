import math, copy
from results.DataTypes import *
from results.Utilities import present_value, scenario_hash
from django.template.loader import render_to_string
import logging


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
                del row.scenario[filt['column']]
                newRows.append(row)
        datatable.rows = newRows


class AggregateBlock:
    def process(self, datatable, **kwargs):
        groups = {}
        scenarios = {}
        for row in datatable:
            if kwargs['column'] not in row.scenario:
                continue
            schash = scenario_hash(scenario=row.scenario, exclude=[kwargs['column']])
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
                        aggregates[key] = DataAggregate(kwargs['type'])
                    aggregates[key].append(val)
            newRow = DataRow()
            newRow.scenario = scenarios[sc]
            newRow.values = aggregates
            newRows.append(newRow)
        
        datatable.rows = newRows


class NormaliseBlock:
    def process(self, datatable, **kwargs):
        if kwargs['normaliser'] == 'select':
            self.processSelectNormaliser(datatable, **kwargs)
        elif kwargs['normaliser'] == 'best':
            self.processBestNormaliser(datatable, **kwargs)
        
    def processSelectNormaliser(self, datatable, **kwargs):
        scenarios = {}
        normalisers = {}
        for row in datatable:
            if kwargs['column'] not in row.scenario:
                continue
            schash = scenario_hash(scenario=row.scenario, exclude=[kwargs['column']])
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
    
    def processBestNormaliser(self, datatable, **kwargs):
        scenarios = {}
        normalisers = {}
        
        if kwargs['group'] == ['']:
            kwargs['group'] = []
        
        #import pdb; pdb.set_trace();
        
        for row in datatable:
            throw = False
            for key in kwargs['group']:
                if key not in row.scenario:
                    throw = True
                    break
            if throw:
                continue
            
            schash = scenario_hash(scenario=row.scenario, include=kwargs['group'])
            if schash not in scenarios:
                scenarios[schash] = []
                normalisers[schash] = {}
            scenarios[schash].append(row)
            for (key,val) in row.values.items():
                if val > 0 and val < normalisers[schash].get(key, float('inf')):
                    normalisers[schash][key] = val
        
        newRows = []
        
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


class GraphBlock:
    def process(self, datatable, **kwargs):
        if kwargs['graph-type'] == 'histogram':
            return self.processHistogram(datatable, **kwargs)
    
    def processHistogram(self, datatable, **kwargs):
        """ Pivots the datatable into a histogram-style row vs column table and
            returns the resulting HTML. We return a list of HTML strings, one per
            table, to provide the possibility that a graph generates more than
            one table. """
        graph_rows = {}
        column_keys = []
        for row in datatable:
            if kwargs['column'] in row.scenario and kwargs['row'] in row.scenario and kwargs['value'] in row.values:
                if row.scenario[kwargs['row']] not in graph_rows:
                    graph_rows[row.scenario[kwargs['row']]] = {}
                graph_rows[row.scenario[kwargs['row']]][row.scenario[kwargs['column']]] = row.values[kwargs['value']]
                if row.scenario[kwargs['column']] not in column_keys:
                    column_keys.append(row.scenario[kwargs['column']])
        
        return [self.renderTable(graph_rows, column_keys, kwargs['row'], kwargs['column'])]
    
    def renderTable(self, rows, column_keys, row_title, column_title):
        """ Renders a pivoted table (e.g. generated by processHistogram) 
            into HTML. """
        row_keys = rows.keys()
        # Try to sort keys numerically first, if they're not floats, sort as lowercase strings
        try:
            row_keys.sort(key=float)
        except ValueError:
            row_keys.sort(key=str.lower)
        
        try:
            column_keys.sort(key=float)
        except ValueError:
            column_keys.sort(key=str.lower)
        
        output = '<table><thead><tr><th>' + row_title + '</th>'
        for key in column_keys:
            output += '<th>' + column_title + '=' + key + '</th>'
        output += '</tr></thead><tbody>'
        for row in row_keys:
            output += '<tr><td>' + row + '</td>'
            for key in column_keys:
                if key in rows[row]:
                    output += '<td>' + present_value(rows[row][key]) + '</td>'
                else:
                    output += '<td>*</td>'
            output += '</tr>'
        output += '</tbody></table>'
        
        return output
            
        