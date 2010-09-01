from django.core.management import setup_environ
import settings

setup_environ(settings)

from results.DataTypes import *
from results.models import *

#import psyco
#psyco.profile()

print 'Building datatable...'
dt = DataTable(log=Log.objects.all()[0])
print 'Length: ', len(dt.rows)

print 'Filtering datatable...'
dt.filter(benchmark='compress')
print 'Length: ', len(dt.rows)

print 'Finding headers...'
sc, val = dt.headers()
print (sc + val)