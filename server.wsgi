import os
import sys

path = os.path.dirname(__file__)
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'plotty.settings'
os.environ['PLOTTY_ROOT'] = os.path.join(path, "../")

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()