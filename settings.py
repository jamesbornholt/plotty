# Django settings for django_site project.
import sys, os

# Files created by plotty are globally read/write
os.umask(0)

DEBUG = not False
TEMPLATE_DEBUG = DEBUG

# Two-tailed confidence level (i.e. this value will be halved for calls to
# the inverse t function)
CONFIDENCE_LEVEL = 0.95
if 'PLOTTY_ROOT' in os.environ:
    ROOT_DIR = os.environ['PLOTTY_ROOT']
    IS_SQUIRREL = True
else:
    ROOT_DIR = os.path.dirname(__file__)
    IS_SQUIRREL = False

APP_ROOT = os.path.dirname(__file__)

BM_LOG_DIR = os.path.join(ROOT_DIR, 'log')

CACHE_ROOT = os.path.join(ROOT_DIR, 'cache')

# 7 days; this is really redundant since we store timeouts for our cache items anyway
CACHE_TIMEOUT = 7*24*60*60
CACHE_MAX_ENTRIES = 300
CACHE_CULL_FRACTION = 2 # delete 1/CACHE_CULL_FRACTION entries when max entries reached
CACHE_OPTIONS = 'timeout=%d&max_entries=%d&cull_frequency=%d' % (CACHE_TIMEOUT, CACHE_MAX_ENTRIES, CACHE_CULL_FRACTION)
CACHE_BACKEND = "plotty.results.Cache://%s?%s" % (os.path.join(ROOT_DIR, 'cache/log'), CACHE_OPTIONS)

GNUPLOT_EXECUTABLE = 'gnuplot'
if IS_SQUIRREL:
    GNUPLOT_EXECUTABLE = '/home/web-scripts/plotty-gnuplot/bin/gnuplot'
GRAPH_CACHE_DIR = os.path.join(ROOT_DIR, 'cache/graph')
GRAPH_FONT_PATH = '/usr/share/fonts/truetype/msttcorefonts'

USE_NEW_LOGPARSER = True
LOGPARSER_PYTHON = 'python'
if USE_NEW_LOGPARSER:
    TABULATE_EXECUTABLE = os.path.join(APP_ROOT, 'results/LogParser.py')
    pypy_path = '/home/web-scripts/plotty-pypy/bin/pypy'
    if IS_SQUIRREL and os.path.exists(pypy_path):
        LOGPARSER_PYTHON = pypy_path
else:
    TABULATE_EXECUTABLE = os.path.join(APP_ROOT, 'results/Tabulate.py')

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

sys.path.insert(0, os.path.dirname(__file__))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(ROOT_DIR, 'cache/database.sqlite3'),
    }
}

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    #'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    #'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    #'debug_toolbar.panels.cache.CacheDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
)
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False
}

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

INTERNAL_IPS = ('127.0.0.1',)

def custom_show_debug_toolbar(request):
    if not DEBUG:
        return False
    
    if '__debug__' in request.path:
        return True
    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', None)
    if x_forwarded_for:
        remote_addr = x_forwarded_for.split(',')[0].strip()
    else:
        remote_addr = request.META.get('REMOTE_ADDR', None)
    
    if remote_addr in INTERNAL_IPS or request.GET.has_key('debug'):
        return True
    
    return False
    
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': custom_show_debug_toolbar,
}


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Australia/Canberra'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = False

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'o!%73-#^d%#11_gl=$1u7#d=w_@=3rce*l1g-sw4n&695b+h#8'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
#    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
#    'django.contrib.messages.middleware.MessageMiddleware',
#    'debug_toolbar.middleware.DebugToolbarMiddleware',
#    'plotty.middleware.ProfileMiddleware'
)

ROOT_URLCONF = 'plotty.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    ROOT_DIR + '/results/templates'
)

INSTALLED_APPS = (
#    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
#    'django.contrib.sites',
#    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
#    'django.contrib.admin',
    'debug_toolbar',
    'plotty.results',
)
