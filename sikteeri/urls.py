from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'sikteeri.views.home', name='home'),
    # url(r'^sikteeri/', include('sikteeri.foo.urls')),

    url(r'^$', 'sikteeri.views.frontpage', name='frontpage'),
    url(r'^comments/', include('django_comments.urls')),
    url(r'^membership/', include('membership.urls')),
    url(r'^services/', include('services.urls')),

    url(r'^login/', 'django.contrib.auth.views.login', name='login'),
    url(r'^logout/', 'django.contrib.auth.views.logout', {'next_page': '/'},
        name='logout'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
