from django.core.management import setup_environ
import settings, sys, os

setup_environ(settings)

from results.Importer import *
from results.models import *

if len(sys.argv) < 2:
    print "Usage: import-cli filename [title]"
    exit()

try:
    fd = open(sys.argv[1])
    fd.close()
except IOError as (errno, errstr):
    print "IO Error: %s" % errstr
    exit()

if len(sys.argv) < 3:
    title = os.path.basename(sys.argv[1])
else:
    title = sys.argv[2]

print "Importing %s into group %s..." % (sys.argv[1], title)

num = doimport(path=sys.argv[1], name=title, console=True)
if num > 0:
    print "Imported %d results into group %s." % (num, title)
else:
    print "Import failed."