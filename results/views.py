# Create your views here.

import os, datetime, math, logging, shutil
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.template import RequestContext
from plotty.results.DataTypes import *
from plotty.results.Blocks import *
from plotty.results.models import SavedPipeline
from plotty.results.Pipeline import *
import plotty.results.PipelineEncoder
from plotty import settings

class LoggingStream(object):
    def __init__(self):
        self.entries = []
    def write(self, s):
        self.entries.append(s)
    def flush(self):
        pass
    def val(self):
        s = ""
        for l in self.entries:
            s += l + "\r\n"
        return s

def list(request, pipeline):
    log_stream = LoggingStream()
    stream_handler = logging.StreamHandler(log_stream)
    root_logger = logging.getLogger()
    root_logger.addHandler(stream_handler)

    try:
        #dt, graph_outputs = execute_pipeline(pipeline)
        p = Pipeline(web_client=False)
        p.decode(pipeline)
        graph_outputs = p.apply()
    except LogTabulateStarted as e:
        output = ''
        return HttpResponse("Tabulating: log %s, pid %d, log number %d/%d" % (e.log, e.pid, e.index, e.length))
    except PipelineBlockException as e:
        output = '<div class="exception"><h1>Exception in executing block ' + str(e.block + 1) + '</h1>' + e.msg
        output += '<h1>Traceback</h1><pre>' + e.traceback + '</pre><h1>Log</h1><pre>' + log_stream.val() + '</pre<</div>'
        return HttpResponse(output)
    except PipelineLoadException as e:
        output = '<div class="exception"><h1>Exception in loading log files</h1>' + e.msg
        output += '<h1>Traceback</h1><pre>' + e.traceback + '</pre><h1>Log</h1><pre>' + log_stream.val() + '</pre<</div>'
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
    logs = [ f for f in os.listdir(settings.BM_LOG_DIR) if os.path.isdir(os.path.join(settings.BM_LOG_DIR,f)) and not f.endswith(".ca") ] 
    logs.sort(key=str.lower)
    pipelines = SavedPipeline.objects.all().order_by('name')
    return render_to_response('pipeline.html', {
        'logs': logs,
        'pipelines': pipelines,
        'debug': settings.DEBUG
    }, context_instance=RequestContext(request))

def debug_clear_cache(request):
    path = os.path.join(settings.CACHE_ROOT, 'log/')
    shutil.rmtree(path)
    os.mkdir(path)
    return HttpResponse('Purged cache in ' + path)
