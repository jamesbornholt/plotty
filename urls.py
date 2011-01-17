from django.conf.urls.defaults import *
from django.conf import settings
from django.views.static import serve

urlpatterns = patterns('',
    (r'^', include('plotty.results.urls')),
)
