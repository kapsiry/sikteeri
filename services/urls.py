from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'aliases/edit/(\d+)/$', 'services.views.alias_edit', name='alias_edit'),
    url(r'aliases/add_for_member/(\d+)/$', 'services.views.alias_add_for_member', name='alias_add'),
)