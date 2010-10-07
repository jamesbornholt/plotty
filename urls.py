from django.conf.urls.defaults import *
from django.conf import settings
from django.views.static import serve
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^django_site/', include('django_site.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
    (r'^results/', include('results.urls')),
    (r'^results(?P<path>.*)$', 'django.views.generic.simple.redirect_to', {'url': '/results/%(path)s'}),
    (r'^(?P<path>.*)$', serve, {'document_root': settings.ROOT_DIR + '/static-root', 'show_indexes': True}),
)
