# Create your views here.

import os, datetime, math
#from scipy import stats
from django.shortcuts import render_to_response
from django.template import RequestContext
from results.DataTypes import *
from results.Blocks import *
from plotty import settings


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
    dt = DataTable(logs=['i7-Bloomfield-2661data.csv'])
    dt.selectValueColumns(['power.avg', 'bmtime'])
    dt.selectScenarioColumns(['benchmark', 'iteration', 'invocation', 'build', 'hfac', 'heap'])
    logging.debug('%d rows initially' % len(dt.rows))
    #FilterBlock().process(dt, benchmark='compress', iteration='4')
    FilterBlock().process(dt, [{'column': 'benchmark', 'is': True, 'value': 'compress'},
                               {'column': 'iteration', 'is': True, 'value': '4'}])
    logging.debug('%d rows after filtering' % len(dt.rows))
    NormaliseBlock().process(dt, column='build', value='jdk1.6.0.s')
    logging.debug('%d rows after normalising' % len(dt.rows))
    AggregateBlock().process(dt, column='invocation', type='mean')
    logging.debug('%d rows after aggregating' % len(dt.rows))

    scenarios, values = dt.headers()
    
    return render_to_response('list.html', {
        'scenario_columns': scenarios,
        'value_columns': values,
        'results': dt,
    }, context_instance=RequestContext(request))

def pipeline(request):
    logs = os.listdir(settings.BM_LOG_DIR)
    return render_to_response('pipeline.html', {
        'logs': logs,
    }, context_instance=RequestContext(request))
