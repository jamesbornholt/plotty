import results.PipelineEncoder
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from plotty.results.DataTypes import *
from plotty.results.Blocks import *
from plotty.results.models import *
from plotty.results.Pipeline import *
from plotty import settings
import json, csv, logging, os, shutil
from datetime import datetime

def filter_values(request, logs, col):
    """ Given a particular scenario column, find all possible values of that
        column inside the given log files """
    values = []
    # The log files are almost certainly cached by now, so this is quick
    dt = DataTable(logs.split(','))
    for row in dt:
        if col in row.scenario and row.scenario[col] not in values:
            values.append(row.scenario[col])
    values.sort()
    return HttpResponse(json.dumps(values))
    
def log_values(request, logs):
    """ Given a set of log files, find all possible scenario variables in those
        logs, and all possible value keys """
    
    if logs == '':
        return HttpResponse(json.dumps({'scenarioCols': [], 'valueCols': [], 'scenairoValues': []}))
    
    try:
        dt = DataTable(logs.split(','), wait=False)
    except LogTabulateStarted as e:
        return HttpResponse(json.dumps({'tabulating': True, 'log': e.log, 'pid': e.pid, 'index': e.index, 'total': e.length}))

    # Grab and sort scenario and value columns
    scenarioCols = list(dt.scenarioColumns)
    valueCols = list(dt.valueColumns)
    scenarioCols.sort()
    valueCols.sort()
    
    # Grab possible values for scenario columns
    scenarioValues = dt.getScenarioValues()
    
    return HttpResponse(json.dumps({'scenarioCols': scenarioCols, 'valueCols': valueCols, 'scenarioValues': scenarioValues}))

def pipeline(request, pipeline):
    try:
        p = Pipeline(web_client=True)
        p.decode(pipeline)
        graph_outputs = p.apply()

    except LogTabulateStarted as e:
        return HttpResponse(json.dumps({'tabulating': True, 'log': e.log, 'pid': e.pid, 'index': e.index, 'total': e.length}))
    except PipelineBlockException as e:
        output = '<div class="exception"><h1>Exception in executing block ' + str(e.block + 1) + '</h1>' + e.msg + '<div class="foldable"><h1>Traceback<a href="" class="toggle">[show]</a></h1><div class="foldable-content hidden"><pre>' + e.traceback + '</pre></div></div>'
        return HttpResponse(json.dumps({'error': True, 'index': e.block, 'html': output, 'rows': 1}))
    except PipelineLoadException as e:
        output = '<div class="exception"><h1>Exception in loading data</h1>' + e.msg + '<div class="foldable"><h1>Traceback<a href="" class="toggle">[show]</a></h1><div class="foldable-content hidden"><pre>' + e.traceback + '</pre></div></div>'
        return HttpResponse(json.dumps({'error': True, 'html': output, 'rows': 1}))
    except PipelineError as e:
        if isinstance(e.block, str):
            output = '<div class="exception"><h1>Error in' + e.block + '</h1>' + e.msg + '</div>'
        else:
            output = '<div class="exception"><h1>Error in block ' + str(e.block + 1) + '</h1>' + e.msg + '</div>'
        return HttpResponse(json.dumps({'error': True, 'index': e.block, 'html': output, 'rows': 1}))
    except PipelineAmbiguityException as e:
        if isinstance(e.block, str):
            # The exception occured early on - cols, probably
            output = '<div class="ambiguity"><h1>Ambiguity in ' + e.block + '</h1>' + e.msg + '<div></strong></div></div>'
            return HttpResponse(json.dumps({'error': False, 'ambiguity': True, 'index': e.block, 'html': output, 'rows': 1}))
        else:
            output = '<div class="ambiguity"><h1>Ambiguity in block ' + str(e.block + 1) + '</h1>' + e.msg + '<div><strong>The data below shows the output of the pipeline up to but not including block ' + str(e.block + 1) + '</strong></div></div>'
            ambiguity = True
            ambiguityIndex = e.block
            dt = e.dataTable
            msg = e.messages
            graph_outputs = e.graph_outputs
    else:
        output = ''
        ambiguity = False
        ambiguityIndex = -1
        dt = p.dataTable
        msg = p.messages

    
    if len(graph_outputs) > 0:
        for i, graph_set in enumerate(graph_outputs, start=1):
            titles = graph_set.keys()
            titles.sort()
            for title in titles:
                output += '<div class="foldable"><h1>' + title + ' (block ' + str(i) + ')</h1>' + graph_set[title] + '</div>'
        output += '<div class="foldable"><h1>Table</h1>' + dt.renderToTable() + '</div>'
    else:
        output += dt.renderToTable()

    if not msg.empty():
      msg_output = '<div class="messages"><h1>Messages</h1>'

      for (t,e) in msg.warnings():
        msg_output += '<img src="static/error.png"/> <span class="message-warning-main">' + t + '</span> <span class="message-warning-extra">' + e + '</span><br/>'

      for (t,e) in msg.infos():
        msg_output += '<img src="static/information.png"/> <span class="message-information-main">' + t + '</span> <span class="message-information-extra">' + e + '</span><br/>'

      msg_output += '</div>'
      output += msg_output
    
    return HttpResponse(json.dumps({'error': False, 'ambiguity': ambiguity, 'index': ambiguityIndex, 'html': output, 'rows': len(dt.rows), 'graph': len(graph_outputs) > 0}))

def delete_saved_pipeline(request):
    if 'name' not in request.POST:
        return HttpResponse(json.dumps({'error': True}))
    try:
        pipeline = SavedPipeline.objects.get(name=request.POST['name'])
    except SavedPipeline.DoesNotExist: # We assume since it's a primary key there's 0 or 1
        return HttpResponse(json.dumps({'error': True, 'reason': 'No pipeline by that name'}))
    pipeline.delete()
    return HttpResponse(json.dumps({'error': False}))

def save_pipeline(request):
    if 'name' not in request.POST or 'encoded' not in request.POST:
        return HttpResponse(json.dumps({'error': True}))
    try:
        new = SavedPipeline(name=request.POST['name'], encoded=request.POST['encoded'])
        new.save()
    except:
        return HttpResponse(json.dumps({'error': True}))
    return HttpResponse(json.dumps({'error': False}))

def list_formatstyle(request):
    try:
        return HttpResponse(json.dumps([f.key for f in FormatStyle.objects.all()]))
    except:
        return HttpResponse(json.dumps({'error': True}))

def load_formatstyle(request, key):
    if key == '':
        return HttpResponse(json.dumps({'error': True}))
    try:
        style = FormatStyle.objects.get(key=key);
        dbentries = FormatStyleEntry.objects.filter(formatstyle=style).order_by('index').all()
        entries = []
        for dbentry in dbentries:
          entries.append({'value': dbentry.value, 'display': dbentry.display, 'group': dbentry.group, 'color': dbentry.color});
        return HttpResponse(json.dumps({'error': False, 'styles': entries}));
    except:
        return HttpResponse(json.dumps({'error': True}))
        

def save_formatstyle(request, key):
    if key == '' or 'style' not in request.POST:
        return HttpResponse(json.dumps({'error': True}))
    try:
        (style, created) = FormatStyle.objects.get_or_create(key=key)

        def load_row(row_dict):
            load_row.count = load_row.count + 1
            return FormatStyleEntry(formatstyle=style, 
                                    index=load_row.count,
                                    value=row_dict['value'],
                                    display=row_dict['display'],
                                    group=(None if not 'group' in row_dict or row_dict['group'] == '' else row_dict['group']),
                                    color=(None if not 'color' in row_dict or row_dict['color'] == '' else row_dict['color']))

        load_row.count = 0
        in_rows = json.loads(request.POST['style'], object_hook=load_row)
        if not created:
            FormatStyleEntry.objects.filter(formatstyle=style).delete()
        for row in in_rows:
            row.save()
    except:
        return HttpResponse(json.dumps({'error': True}))
    return HttpResponse(json.dumps({'error': False}))
    
def purge_cache(request):
    try:
      for cache_part in ('log', 'csv', 'graph'):
        dir_path = os.path.join(settings.CACHE_ROOT, cache_part)
        for entry in os.listdir(dir_path):
          entry_path = os.path.join(dir_path, entry) 
          if os.path.isdir(entry_path):
            shutil.rmtree(entry_path)
          else:
            os.unlink(entry_path)
    except:
      return HttpResponse(json.dumps({'error': True}))
    return HttpResponse(json.dumps({'error': False}))
    
def tabulate_progress(request, pid):
    if not os.path.exists(os.path.join(settings.CACHE_ROOT, pid + ".status")):
        return HttpResponse(json.dumps({'complete': True, 'reason': 'file'}))
    else:
        resp = None
        done = False
        f = open(os.path.join(settings.CACHE_ROOT, pid + ".status"), 'r')
        lines = f.readlines()
        if lines[-1] == '':
            del lines[-1]
        if len(lines) > 1 and lines[-1] == lines[0]:
            resp = HttpResponse(json.dumps({'complete': True, 'reason': 'finished'}))
            done = True
        else:
            # Sanity check: does the process still exist?
            try:
                os.kill(int(pid), 0)
                exists = True
            except OSError:
                exists = False
            if not exists:
                resp = HttpResponse(json.dumps({'complete': True, 'reason': 'process'}))
                done = True
            else:
                if len(lines) > 1:
                    progress = '%.0f' % (float(lines[-1]) * 100.0 / float(lines[0]))
                else:
                    progress = "0"
                resp = HttpResponse(json.dumps({'complete': False, 'percent': progress}))
        f.close()
        if done:
            os.remove(os.path.join(settings.CACHE_ROOT, pid + ".status"))
        return resp
