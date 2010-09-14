import results.PipelineEncoder
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from results.DataTypes import *
from results.Blocks import *
import json, csv

def filter_values(request, logs, col):
    """ Given a particular scenario column, find all possible values of that
        column inside the given log files """
    values = []
    # The log files are almost certainly cached by now, so this is quick
    dt = DataTable(logs.split(','))
    for row in dt:
        if row.scenario[col] not in values:
            values.append(row.scenario[col])
    values.sort()
    return HttpResponse(json.dumps(values))
    
def log_values(request, logs):
    """ Given a set of log files, find all possible scenario variables in those
        logs, and all possible value keys """
    columns = []
    keys = []
    dt = DataTable(logs.split(','))
    for row in dt:
        for col in row.scenario.iterkeys():
            if col not in columns:
                columns.append(col)
        for key in row.values.iterkeys():
            if key not in keys:
                keys.append(key)
    columns.sort()
    keys.sort()
    return HttpResponse(json.dumps({'scenarioCols': columns, 'valueCols': keys}))

def pipeline(request, pipeline):
    decoded = results.PipelineEncoder.decode_pipeline(pipeline)
    dt = DataTable(logs=decoded['logs'])
    dt.selectValueColumns(decoded['value_columns'])
    dt.selectScenarioColumns(decoded['scenario_columns'])
    for block in decoded['blocks']:
        if block['type'] == 'aggregate':
            AggregateBlock().process(dt, **block['params'])
        elif block['type'] == 'filter':
            FilterBlock().process(dt, block['filters'])
        elif block['type'] == 'normalise':
            NormaliseBlock().process(dt, **block['params'])
    
    scenarios, values = dt.headers()
    
    return render_to_response('pipeline-ajax.html', {
        'scenario_columns': scenarios,
        'value_columns': values,
        'results': dt,
    }, context_instance=RequestContext(request))
    return HttpResponse(str(results.PipelineEncoder.decode_pipeline(pipeline)))