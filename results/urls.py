from django.conf.urls.defaults import *
from django.conf import settings
from django.views.static import serve

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('results.views',
    (r'^static/(?P<path>.*)$', serve, {'document_root': settings.ROOT_DIR + '/results/static'}),
    
    (r'^import/', 'importlog'),
    (r'^list/', 'list'),
    (r'', 'pipeline')
)
