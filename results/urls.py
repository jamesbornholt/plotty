from django.conf.urls.defaults import *
from django.conf import settings
from django.views.static import serve
import os

urlpatterns = patterns('plotty.results',
    (r'^static/(?P<path>.*)$', serve, {'document_root': os.path.join(os.path.dirname(__file__), 'static')}),
    (r'^graph/(?P<path>.*)$', serve, {'document_root': settings.GRAPH_CACHE_DIR}),
    (r'^p/(?P<url>[A-Za-z0-9]{6})$', 'views.shorturl'),

    (r'^ajax/log-values/(?P<logs>.*)/$', 'views_ajax.log_values'),    
    (r'^ajax/filter-values/(?P<logs>.*)/(?P<col>.*)/$', 'views_ajax.filter_values'),
    (r'^ajax/pipeline/(?P<pipeline>.*)$', 'views_ajax.pipeline'),
    (r'^ajax/save-pipeline/$', 'views_ajax.save_pipeline'),
    (r'^ajax/delete-pipeline/$', 'views_ajax.delete_saved_pipeline'),
    (r'^ajax/create-shorturl/$', 'views_ajax.create_shorturl'),
    (r'^ajax/load-formatstyle/(?P<key>.*)/$', 'views_ajax.load_formatstyle'),
    (r'^ajax/save-formatstyle/(?P<key>.*)/$', 'views_ajax.save_formatstyle'),
    (r'^ajax/delete-formatstyle/(?P<key>.*)/$', 'views_ajax.delete_formatstyle'),
    (r'^ajax/load-graphformat/(?P<key>.*)/$', 'views_ajax.load_graphformat'),
    (r'^ajax/save-graphformat/(?P<key>.*)/$', 'views_ajax.save_graphformat'),
    (r'^ajax/delete-graphformat/(?P<key>.*)/$', 'views_ajax.delete_graphformat'),
    (r'^ajax/purge-cache/$', 'views_ajax.purge_cache'),
    (r'^ajax/reinstall-defaults/$', 'views_ajax.reinstall_defaults'),
    (r'^ajax/pipeline-csv-table/(?P<pipeline>.*)$', 'views_ajax.csv_table'),
    (r'^ajax/pipeline-csv-graph/(?P<pipeline>.*)/(?P<index>.*)/(?P<graph>.*)/$', 'views_ajax.csv_graph'),
    (r'^ajax/tabulate-progress/(?P<pid>[0-9]*)/$', 'views_ajax.tabulate_progress'),
    
    # Debugging
    (r'^list/graph/(?P<path>.*)$', serve, {'document_root': settings.GRAPH_CACHE_DIR}),
    (r'^list/(?P<pipeline>.*)$', 'views.list'),
    (r'^debug-clear-cache/$', 'views.debug_clear_cache'),

    (r'', 'views.pipeline'),
)
