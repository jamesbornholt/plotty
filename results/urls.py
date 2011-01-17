from django.conf.urls.defaults import *
from django.conf import settings
from django.views.static import serve

urlpatterns = patterns('',
    (r'^static/(?P<path>.*)$', serve, {'document_root': settings.ROOT_DIR + '/results/static'}),
    (r'^graph/(?P<path>.*)$', serve, {'document_root': settings.GRAPH_CACHE_DIR}),

    (r'^ajax/log-values/(?P<logs>.*)/$', 'results.views_ajax.log_values'),    
    (r'^ajax/filter-values/(?P<logs>.*)/(?P<col>.*)/$', 'results.views_ajax.filter_values'),
    (r'^ajax/pipeline/(?P<pipeline>.*)$', 'results.views_ajax.pipeline'),
    (r'^ajax/save-pipeline/$', 'results.views_ajax.save_pipeline'),
    (r'^ajax/pipeline-csv-table/(?P<pipeline>.*)$', 'results.views_ajax.csv_table'),
    (r'^ajax/pipeline-csv-graph/(?P<pipeline>.*)/(?P<index>.*)/(?P<graph>.*)/$', 'results.views_ajax.csv_graph'),
    
    # Debugging
    (r'^list/graph/(?P<path>.*)$', serve, {'document_root': settings.GRAPH_CACHE_DIR}),
    (r'^list/(?P<pipeline>.*)$', 'results.views.list'),
    (r'', 'results.views.pipeline'),
)
