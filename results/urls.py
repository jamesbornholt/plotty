from django.conf.urls.defaults import *
from django.conf import settings
from django.views.static import serve

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^static/(?P<path>.*)$', serve, {'document_root': settings.ROOT_DIR + '/results/static'}),

    (r'^ajax/log-values/(?P<logids>.*)/$', 'results.views_ajax.log_values'),    
    (r'^ajax/filter-values/(?P<logids>.*)/(?P<col>.*)/$', 'results.views_ajax.filter_values'),
    (r'^ajax/pipeline/(?P<pipeline>.*)$', 'results.views_ajax.pipeline'),
    
    (r'^import/', 'results.views.importlog'),
    (r'^list/', 'results.views.list'),
    (r'', 'results.views.pipeline'),
)
