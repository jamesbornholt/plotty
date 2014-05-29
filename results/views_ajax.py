import results.PipelineEncoder
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db import transaction
from plotty.results.DataTypes import *
from plotty.results.Blocks import *
from plotty.results.models import *
from plotty.results.Pipeline import *
from plotty import settings, install_defaults
import json, csv, logging, os, shutil, math
from datetime import datetime

def pipeline(request, pipeline):
    try:
        p = Pipeline(web_client=True)
        p.decode(pipeline)
        (block_scenario_values, block_scenario_display, block_values, block_values_display, graph_outputs) = p.apply()

    except LogTabulateStarted as e:
        return HttpResponse(json.dumps({'tabulating': True, 'log': e.log, 'pid': e.pid, 'index': e.index, 'total': e.length}))
    except PipelineBlockException as e:
        output = '<div class="exception"><h1>Exception in executing block ' + str(e.block + 1) + '</h1>' + e.msg + '<div class="foldable"><h1>Traceback<button class="foldable-toggle-show pipeline-button">Show</button></h1><div class="foldable-content hidden"><pre>' + e.traceback + '</pre></div></div>'
        return HttpResponse(json.dumps({'error': True, 'index': e.block, 'error_html': output, 'rows': 1}))
    except PipelineLoadException as e:
        output = '<div class="exception"><h1>Exception in loading data</h1>' + e.msg + '<div class="foldable"><h1>Traceback<button class="foldable-toggle-show pipeline-button">Show</button></h1><div class="foldable-content hidden"><pre>' + e.traceback + '</pre></div></div>'
        return HttpResponse(json.dumps({'error': True, 'error_html': output, 'rows': 1}))
    except PipelineError as e:
        if isinstance(e.block, str):
            output = '<div class="exception"><h1>Error in ' + e.block + '</h1>' + e.msg + '</div>'
            return HttpResponse(json.dumps({'error': True, 'index': e.block, 'error_html': output, 'rows': 1}))
        else:
            error_output = '<div class="exception"><h1>Error in block ' + str(e.block + 1) + '</h1>' + e.msg + '</div>'
            ambiguity = False
            index = e.block
            dt = e.dataTable
            msg = e.messages
            graph_outputs = e.graph_outputs
            block_values = e.block_values
            block_values_display = e.block_values_display
            block_scenario_values = e.block_scenario_values
            block_scenario_display = e.block_scenario_display
    except PipelineAmbiguityException as e:
        if isinstance(e.block, str):
            # The exception occured early on - cols, probably
            output = '<div class="ambiguity"><h1>Ambiguity in ' + e.block + '</h1>' + e.msg + '<div></strong></div></div>'
            return HttpResponse(json.dumps({'error': False, 'ambiguity': True, 'index': e.block, 'error_html': output, 'rows': 1}))
        else:
            error_output = '<div class="ambiguity"><h1>Ambiguity in block ' + str(e.block + 1) + '</h1>' + e.msg + '<div><strong>The data below shows the output of the pipeline up to but not including block ' + str(e.block + 1) + '</strong></div></div>'
            ambiguity = True
            index = e.block
            dt = e.dataTable
            msg = e.messages
            graph_outputs = e.graph_outputs
            block_values = e.block_values
            block_values_display = e.block_values_display
            block_scenario_values = e.block_scenario_values
            block_scenario_display = e.block_scenario_display
    else:
        error_output = ''
        ambiguity = False
        index = -1
        dt = p.dataTable
        msg = p.messages

    
    # Main data table
    table_output = dt.renderToTable()

    # Messages
    msg_output = ''
    if not msg.empty():
      msg_output = '<div class="messages">'

      for (t,e) in msg.warnings():
        msg_output += '<img src="static/error.png"/> <span class="message-warning-main">' + t + '</span> <span class="message-warning-extra">' + e + '</span><br/>'

      for (t,e) in msg.infos():
        msg_output += '<img src="static/information.png"/> <span class="message-information-main">' + t + '</span> <span class="message-information-extra">' + e + '</span><br/>'

      msg_output += '</div>'

    # Style stuff
    format_styles = [f.key for f in FormatStyle.objects.all()]
    graph_formats = dict([(f.key, {'value': f.value, 'parent': f.parent.key if f.parent else None, 'full_value': unicode(f)}) for f in GraphFormat.objects.all()])

    error_output
    return HttpResponse(json.dumps({'error': False, 
                                    'ambiguity': ambiguity,
                                    'index': index,
                                    'block_scenarios': block_scenario_values,
                                    'block_scenario_display': block_scenario_display,
                                    'block_values': block_values,
                                    'block_values_display': block_values_display,
                                    'format_styles': format_styles,
                                    'graph_formats': graph_formats,
                                    'error_html': error_output,
                                    'warn_html': msg_output,
                                    'table_html': table_output,
                                    'rows': len(dt.rows),
                                    'graphs': graph_outputs}))

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

def load_graphformat(request, key):
    if key == '':
        return HttpResponse(json.dumps({'error': True}))
    try:
        graphformat = GraphFormat.objects.get(key=key)
    except GraphFormat.DoesNotExist:
        return HttpResponse(json.dumps({'error': True, 'reason': 'No format for that key'}))
    return HttpResponse(json.dumps({'error': False, 'parent': None if not graphformat.parent else graphformat.parent.key, 'value' : graphformat.value, 'full' : unicode(graphformat)}))
    
def save_graphformat(request, key):
    if key == '' or 'value' not in request.POST:
        return HttpResponse(json.dumps({'error': True}))

    parent = request.POST['parent'] if ('parent' in request.POST) else None

    dbparent = None
    if parent:
        dbparent = GraphFormat.objects.get(key=parent)

    value = request.POST['value']
    (graphformat, created) = GraphFormat.objects.get_or_create(key=key, defaults={'parent': dbparent, 'value': value})
    
 
    if not created:
        graphformat.parent = dbparent
        graphformat.value = value
        graphformat.save()

    return HttpResponse(json.dumps({'error': False}))
    
def delete_graphformat(request, key):
    if key == '':
        return HttpResponse(json.dumps({'error': True}))
    try:
        graphformat = GraphFormat.objects.get(key=key)
    except GraphFormat.DoesNotExist:
        return HttpResponse(json.dumps({'error': True, 'reason': 'No format for that key'}))
    graphformat.delete()
    return HttpResponse(json.dumps({'error': False}))
    
def load_formatstyle(request, key):
    if key == '':
        return HttpResponse(json.dumps({'error': True}))
    try:
        style = FormatStyle.objects.get(key=key)
        dbentries = FormatStyleEntry.objects.filter(formatstyle=style).order_by('index').all()
        entries = []
        for dbentry in dbentries:
          entries.append({'value': dbentry.value, 'display': dbentry.display, 'group': dbentry.group, 'color': dbentry.color})
        return HttpResponse(json.dumps({'error': False, 'styles': entries}))
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
        style.save()
    except:
        return HttpResponse(json.dumps({'error': True}))
    return HttpResponse(json.dumps({'error': False}))

def delete_formatstyle(request, key):
    if key == '':
        return HttpResponse(json.dumps({'error': True}))
    try:
        style = FormatStyle.objects.get(key=key)
    except FormatStyle.DoesNotExist:
        return HttpResponse(json.dumps({'error': True, 'reason': 'No style for that key'}))
    style.delete()
    return HttpResponse(json.dumps({'error': False}))

def create_shorturl(request):
    if 'encoded' not in request.POST:
        return HttpResponse(json.dumps({'error': True}))
    try:
        old = ShortURL.objects.get(encoded=request.POST['encoded'])
        return HttpResponse(json.dumps({'error': False, 'url': request.build_absolute_uri('../../p/'+old.url)}))
    except ShortURL.DoesNotExist:
        # Create a short URL
        url = ""
        num = float(abs(hash(request.POST['encoded']))) # could be random instead
        # To avoid confusion, don't use 0/o/O, l/L/i/I/1
        valid_chars = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
        base = len(valid_chars)
        url_length = 6
        if num < base**url_length:
            t = math.floor(math.log(num, base))
            while t <= url_length:
                num *= base**t
        num = num % (base**url_length)
        for t in xrange(url_length-1, -1, -1):
            factor = base**t
            i = int(math.floor(num / factor) % base)
            url += valid_chars[i]
            num -= i * factor
        
        # Save it
        new = ShortURL(url=url, encoded=request.POST['encoded'])
        new.save()
        return HttpResponse(json.dumps({'error': False, 'url': request.build_absolute_uri('../../p/'+url)}))
    except:
        return HttpResponse(json.dumps({'error': True}))

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

def reinstall_defaults(request):
    try:
        install_defaults.reinstall_defaults()
    except Exception:
        raise
    else:
        return HttpResponse(json.dumps({'error': False}))
        
