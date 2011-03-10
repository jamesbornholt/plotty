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
        #dt, graph_outputs = execute_pipeline(pipeline)
        p = Pipeline(web_client=True)
        p.decode(pipeline)
        graph_outputs = p.apply()
    except LogTabulateStarted as e:
        output = ''
        return HttpResponse("Tabulating: log %s, pid %d, log number %d/%d" % (e.log, e.pid, e.index, e.length))
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
        for i, graph_set in enumerate(graph_outputs, start=1):
            titles = graph_set.keys()
            titles.sort()
            for title in titles:
                output += '<div class="foldable"><h1>' + title + ' (block ' + str(i) + ')</h1>' + graph_set[title] + '</div>'
        output += '<div class="foldable"><h1>Table</h1>' + p.dataTable.renderToTable() + '</div>'
    else:
        output += p.dataTable.renderToTable()
    
    return HttpResponse('<html><head><title>Listing</title></head><body>' + output + '</body></html')

def pipeline(request):
    logs = [ f for f in os.listdir(settings.BM_LOG_DIR) if os.path.isdir(os.path.join(settings.BM_LOG_DIR,f)) ] 
    logs.sort(key=str.lower)
    pipelines = SavedPipeline.objects.all().order_by('name')
    return render_to_response('pipeline.html', {
        'logs': logs,
        'pipelines': pipelines
    }, context_instance=RequestContext(request))
