from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'new/', 'membership.views.new_application', name='new_application'),
    url(r'list/', 'membership.views.membership_list', name='membership_list'),
    url(r'edit_inline/(\d+)/', 'membership.views.membership_edit_inline', name='membership_edit_inline'),
    url(r'edit/(\d+)/', 'membership.views.membership_edit', name='membership_edit'),
)
