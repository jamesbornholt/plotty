from django.core.management import setup_environ
import settings, sys

setup_environ(settings)

from results.DataTypes import *
from results.models import *
from results.Blocks import *

print 'Building data table...'
dt = DataTable(logs=['../logs/i7-Bloomfield-2661data.csv'])
print 'Built data table with %d rows.' % len(dt.rows)
print 'Selecting values...'
dt.selectValueColumns(['power.avg', 'bmtime'])
print 'Filtering to benchmark=compress, iteration=4...'
FilterBlock().process(dt, [{'column': 'benchmark', 'is': True, 'value': 'compress'},
                           {'column': 'iteration', 'is': True, 'value': '4'}])
print 'Filtered to %d rows.' % len(dt.rows)
print 'Aggregating with mean over invocations...'
AggregateBlock().process(dt, column='invocation', type='mean')
print 'Aggregated to %d rows.' % len(dt.rows)


