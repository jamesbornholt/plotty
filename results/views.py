# Create your views here.

import os, datetime, math, logging
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.template import RequestContext
from plotty.results.DataTypes import *
from plotty.results.Blocks import *
from plotty.results.models import SavedPipeline
from plotty.results.Pipeline import *
import plotty.results.PipelineEncoder
from plotty import settings


def list(request, pipeline):
    try:
        dt, graph_outputs = execute_pipeline(pipeline)
    except PipelineBlockException as e:
        output = '<div class="exception"><h1>Exception in executing block ' + str(e.block + 1) + '</h1>' + e.msg + '<h1>Traceback</h1><pre>' + e.traceback + '</pre></div>'
        return HttpResponse(output)
    except PipelineLoadException as e:
        output = '<div class="exception"><h1>Exception in loading log files</h1>' + e.msg + '<h1>Traceback</h1><pre>' + e.traceback + '</pre></div>'
        return HttpResponse(output)
    except PipelineAmbiguityException as e:
        output = 'Ambiguity: ' + e.msg + ' in block ' + str(e.block)
        return HttpResponse(output)
    
    output = ''
    if len(graph_outputs) > 0:
        for i, graphs in enumerate(graph_outputs, start=1):
            keys = graphs.keys()
            keys.sort()
            for key in keys:
                output += '<div class="foldable"><h1>' + key + ' (block ' + str(i) + ')</h1>' + graphs[key] + '</div>'
        output += '<div class="foldable"><h1>Table</h1>' + dt.renderToTable() + '</div>'
    else:
        output += dt.renderToTable()
    
    return HttpResponse('<html><head><title>Listing</title></head><body>' + output + '</body></html')

def pipeline(request):
    logs = os.listdir(settings.BM_LOG_DIR)
    logs.sort(key=str.lower)
    pipelines = SavedPipeline.objects.all().order_by('name')
    return render_to_response('pipeline.html', {
        'logs': logs,
        'pipelines': pipelines
    }, context_instance=RequestContext(request))
