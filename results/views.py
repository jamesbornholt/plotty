# Create your views here.

# Create your views here.

import os, datetime, math
#from scipy import stats
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db.models import *
from results.models import *
from results.Importer import *
from results.DataTypes import *
from results.Blocks import *
from plotty import settings

def importlog(request):
    files = os.listdir(settings.BM_LOG_DIR)
    import_error = False
    import_count = 0
    delta = 0
    if ( request.POST ):
        start = datetime.datetime.now()
        import_count = doimport(path=settings.BM_LOG_DIR + '/' + request.POST['file'], name=request.POST['name'])
        end = datetime.datetime.now()
        delta = end - start
        
        if ( import_count == 0 ):
            import_error = True

    return render_to_response('importlog.html', {
        'file_list': files,
        'import_count': import_count,
        'import_error': import_error,
        'delta': str(delta)
    }, context_instance=RequestContext(request))

def list(request):
#    objs = Result.objects.filter(Key='power.watts', Scenario__Columns__Key='benchmark', Scenario__Columns__Value='antlr')
#    headers = {}
#    for var in objs[0].Scenario.Columns.all():
#        headers[var.Key] = var.Value
#    
#    aggs = objs.values('Scenario_id').annotate(avg=Avg('Value'), n=Count('Value'), stdev=StdDev('Value', sample=True))
#    for agg in aggs:
#        agg['ci'] = stats.t.isf(0.025, agg['n']-1) * agg['stdev'] / math.sqrt(agg['n'])
#        agg['ciperc'] = agg['ci'] / agg['avg'] * 100
#        agg['Scenario'] = Scenario.objects.get(id=agg['Scenario_id'])
#    
    dt = DataTable(log=Log.objects.all()[0])
    logging.debug('%d rows initially' % len(dt.rows))
    #FilterBlock().process(dt, benchmark='compress', iteration='4')
    FilterBlock().process(dt, benchmark='compress', iteration='4')
    logging.debug('%d rows after filtering' % len(dt.rows))
    AggregateBlock().process(dt, column='invocation', type='mean')
    logging.debug('%d rows after aggregating' % len(dt.rows))

    scenarios, values = dt.headers()
    
    return render_to_response('list.html', {
        'scenario_columns': scenarios,
        'value_columns': values,
        'results': dt,
    }, context_instance=RequestContext(request))

def pipeline(request):
    logs = Log.objects.all()
    
    return render_to_response('pipeline.html', {
        'logs': logs
    }, context_instance=RequestContext(request))
