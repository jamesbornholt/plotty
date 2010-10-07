# Create your views here.

import os, datetime, math, logging
#from scipy import stats
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.template import RequestContext
from results.DataTypes import *
from results.Blocks import *
from results.models import SavedPipeline
import results.PipelineEncoder
from plotty import settings


def list(request, pipeline):
    decoded = results.PipelineEncoder.decode_pipeline(pipeline)
    dt = DataTable(logs=decoded['logs'])
    dt.selectValueColumns(decoded['value_columns'])
    dt.selectScenarioColumns(decoded['scenario_columns'])
    graph_outputs = []
    for block in decoded['blocks']:
        if block['type'] == 'aggregate':
            AggregateBlock().process(dt, **block['params'])
        elif block['type'] == 'filter':
            FilterBlock().process(dt, block['filters'])
        elif block['type'] == 'normalise':
            NormaliseBlock().process(dt, **block['params'])
        elif block['type'] == 'graph':
            graph_outputs.extend(GraphBlock().process(dt, **block['params']))
    
    output = '<html><head><title>Listing</title></head><body>'
    if len(graph_outputs) > 0:
        for i, graph in enumerate(graph_outputs, start=1):
            output += '<div class="foldable"><h1>Graph ' + str(i) + '<a href="">[hide]</a></h1><div class="foldable-content">' + graph + '</div></div>'
        output += '<div class="foldable"><h1>Table</h1><a href="">[show]</a><div class="foldable-content hidden">' + dt.renderToTable() + '</div></div>'
    else:
        output += dt.renderToTable()
    output += '</body></html>'
    
    return HttpResponse(output)

def pipeline(request):
    logs = os.listdir(settings.BM_LOG_DIR)
    logs.sort(key=str.lower)
    pipelines = SavedPipeline.objects.all().order_by('name')
    return render_to_response('pipeline.html', {
        'logs': logs,
        'pipelines': pipelines
    }, context_instance=RequestContext(request))
