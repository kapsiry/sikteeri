from django.conf.urls.defaults import *

from membership.models import *

urlpatterns = patterns('',
    # XXX Would be nice to use just the name for redirect, but how to import from
    # urlconf that is not yet defined...
    url(r'pre-approval/', 'membership.views.membership_list_new', name='pre-approval'),

    url(r'new/', 'membership.views.new_application', name='new_application'),
    url(r'list/', 'membership.views.membership_list', name='membership_list'),
    url(r'edit_inline/(\d+)/', 'membership.views.membership_edit_inline', name='membership_edit_inline'),
    url(r'edit/(\d+)/', 'membership.views.membership_edit', name='membership_edit'),
    url(r'preapprove/(\d+)/', 'membership.views.membership_preapprove', name='membership_preapprove'),
    url(r'unpaid/', 'django.views.generic.list_detail.object_list',
        {'queryset': Bill.objects.filter(is_paid__exact=False),
         'template_name': 'membership/bill_list.html',
         'template_object_name': 'bill'}, name='unpaid_bill_list'),
    url(r'bills/', 'django.views.generic.list_detail.object_list',
        {'queryset': Bill.objects.all(),
         'template_name': 'membership/bill_list.html',
         'template_object_name': 'bill'}, name='bill_list'),
    url(r'approve/(\d+)/', 'membership.views.membership_approve', name='membership_approve'),
)
