from django.conf.urls import include
from django.urls import re_path
import sikteeri.views
import django.contrib.auth.views

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


urlpatterns = [
    # Examples:
    # url(r'^$', 'sikteeri.views.home', name='home'),
    # url(r'^sikteeri/', include('sikteeri.foo.urls')),

    re_path(r'^$', sikteeri.views.frontpage, name='frontpage'),
    re_path(r'^comments/', include('django_comments.urls')),
    re_path(r'^membership/', include('membership.urls')),
    re_path(r'^procountor/', include('procountor.urls')),
    re_path(r'^services/', include('services.urls')),

    re_path(r'^login/', django.contrib.auth.views.LoginView.as_view(), name='login'),
    re_path(r'^logout/', django.contrib.auth.views.LogoutView.as_view(next_page='/'),
        name='logout'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    re_path(r'^admin/', admin.site.urls),
]
