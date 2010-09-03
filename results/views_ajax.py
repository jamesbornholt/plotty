from results.models import *
import results.PipelineEncoder
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from results.DataTypes import *
from results.Blocks import *
import json

def filter_values(request, logids, col):
    values = []
    for i in logids.split(','):
        if i == '':
            continue
        log_values = ScenarioVar.objects.filter(Log__id=int(i), Key=col).values('Value').distinct()
        for value in log_values:
            if value['Value'] not in values:
                values.append(value['Value'])
    values.sort()
    return HttpResponse(json.dumps(values))
    
def log_values(request, logids):
    columns = []
    for i in logids.split(','):
        if i == '':
            continue
        log_cols = ScenarioVar.objects.filter(Log__id=int(i)).values('Key').distinct()
        for col in log_cols:
            if col['Key'] not in columns:
                columns.append(col['Key'])
    columns.append('invocation')
    columns.sort()
    keys = []
    for i in logids.split(','):
        if i == '':
            continue
        log_keys = Result.objects.filter(Log__id=i).values('Key').distinct()
        for key in log_keys:
            if key['Key'] not in keys:
                keys.append(key['Key'])
    keys.sort()
    return HttpResponse(json.dumps({'columns': columns, 'keys': keys}))

def pipeline(request, pipeline):
    decoded = results.PipelineEncoder.decode_pipeline(pipeline)
    dt = DataTable(logs=decoded['logs'])
    dt.selectValues(decoded['columns'])
    for block in decoded['blocks']:
        if block['type'] == 'aggregate':
            AggregateBlock().process(dt, **block['params'])
        elif block['type'] == 'filter':
            FilterBlock().process(dt, block['filters'])
    
    scenarios, values = dt.headers()
    
    return render_to_response('pipeline-ajax.html', {
        'scenario_columns': scenarios,
        'value_columns': values,
        'results': dt,
    }, context_instance=RequestContext(request))
    return HttpResponse(str(results.PipelineEncoder.decode_pipeline(pipeline)))