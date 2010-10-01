# Create your views here.

import os, datetime, math, logging
#from scipy import stats
from django.shortcuts import render_to_response
from django.template import RequestContext
from results.DataTypes import *
from results.Blocks import *
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

    scenarios, values = dt.headers()
    
    return render_to_response('list.html', {
        'scenario_columns': scenarios,
        'value_columns': values,
        'results': dt,
        'graph_outputs': graph_outputs
    }, context_instance=RequestContext(request))

def pipeline(request):
    logs = os.listdir(settings.BM_LOG_DIR)
    logs.sort(key=str.lower)
    return render_to_response('pipeline.html', {
        'logs': logs,
    }, context_instance=RequestContext(request))
