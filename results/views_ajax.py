import results.PipelineEncoder
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from results.DataTypes import *
from results.Blocks import *
from results.models import SavedPipeline
from results.Pipeline import *
import json, csv, logging

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
    try:
        dt, graph_outputs = execute_pipeline(pipeline)
    except PipelineBlockException as e:
        output = '<div class="exception"><h1>Exception in executing block ' + str(e.block + 1) + '</h1>' + e.msg + '<div class="foldable"><h1>Traceback<a href="">[show]</a></h1><div class="foldable-content hidden"><pre>' + e.traceback + '</pre></div></div>'
        return HttpResponse(json.dumps({'error': True, 'index': e.block, 'html': output, 'rows': 1}))
    except PipelineLoadException as e:
        output = '<div class="exception"><h1>Exception in loading log files</h1>' + e.msg + '<div class="foldable"><h1>Traceback<a href="">[show]</a></h1><div class="foldable-content hidden">' + e.traceback + '</div></div>'
        return HttpResponse(json.dumps({'error': True, 'html': output, 'rows': 1}))
    
    output = ''
    if len(graph_outputs) > 0:
        for i, graph in enumerate(graph_outputs, start=1):
            output += '<div class="foldable"><h1>Graph ' + str(i) + '<a href="">[hide]</a></h1><div class="foldable-content">' + graph + '</div></div>'
        output += '<div class="foldable"><h1>Table<a href="">[show]</a></h1><div class="foldable-content hidden">' + dt.renderToTable() + '</div></div>'
    else:
        output += dt.renderToTable()
    
    return HttpResponse(json.dumps({'error': False, 'html': output, 'rows': len(dt.rows)}))

def save_pipeline(request):
    if 'name' not in request.POST or 'encoded' not in request.POST:
        return HttpResponse(json.dumps({'error': True}))
    new = SavedPipeline(name=request.POST['name'], encoded=request.POST['encoded'])
    new.save()
    return HttpResponse(json.dumps({'error': False}))