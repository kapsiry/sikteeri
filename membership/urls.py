from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # XXX Would be nice to use just the name for redirect, but how to import from
    # urlconf that is not yet defined...
    url(r'pre-approval/', 'membership.views.membership_list_new', name='pre-approval'),

    url(r'new/', 'membership.views.new_application', name='new_application'),
    url(r'list/', 'membership.views.membership_list', name='membership_list'),
    url(r'edit_inline/(\d+)/', 'membership.views.membership_edit_inline', name='membership_edit_inline'),
    url(r'edit/(\d+)/', 'membership.views.membership_edit', name='membership_edit'),
)
