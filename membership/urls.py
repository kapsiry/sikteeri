from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'', 'membership.views.new_application', name='new_application'),
)
