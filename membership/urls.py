from django.conf.urls.defaults import *

from membership.models import *
from membership.forms import *

urlpatterns = patterns('',
    (r'jsi18n/$', 'django.views.i18n.javascript_catalog', {'packages': ('membership')}),
    
    url(r'persons/new/$', 'membership.views.person_application', name='person_application'),
    url(r'organizations/new/$', 'membership.views.organization_application',
        name='organization_application'),
    url(r'organizations/new/add_contact/(\w+)/$', 'membership.views.organization_application_add_contact',
        name='organization_application_add_contact'),
    url(r'organizations/new/application/review/$', 'membership.views.organization_application_review',
        name='organization_application_review'),
    url(r'organizations/new/application/save/$', 'membership.views.organization_application_save',
        name='organization_application_save'),
    url(r'memberships/new/$', 'membership.views.new_application', name='new_application'),
    url(r'memberships/edit_inline/(\d+)/$', 'membership.views.membership_edit_inline', name='membership_edit_inline'),
    url(r'memberships/edit/(\d+)/$', 'membership.views.membership_edit', name='membership_edit'),
    url(r'memberships/preapprove/(\d+)/$', 'membership.views.membership_preapprove', name='membership_preapprove'),

    url(r'memberships/approve/(\d+)/$', 'membership.views.membership_approve', name='membership_approve'),
    url(r'memberships/json_detail/(\d+)/$', 'membership.views.membership_json_detail', name='membership_json_detail'),
    
    url(r'memberships/pre-approval/json_detail/(\d+)/$', 'membership.views.membership_json_detail',
        name='membership_json_detail'),
    url(r'memberships/pre-approval/preapprove_ajax/(\d+)/$', 'membership.views.membership_preapprove_json', name='membership_preapprove_json'),
    
    url(r'static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '../membership/static/'}),
)


urlpatterns += patterns('django.views.generic',
    url(r'memberships/$', 'list_detail.object_list',
        {'queryset': Membership.objects.all(),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': 100}, name='membership_list'),
    url(r'memberships/pre-approval/$', 'list_detail.object_list',
        {'queryset': Membership.objects.filter(status__exact='N'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': 100}, name='pre-approval'),
    url(r'bills/$', 'list_detail.object_list',
        {'queryset': Bill.objects.all(),
         'template_name': 'membership/bill_list.html',
         'template_object_name': 'bill',
         'paginate_by': 100}, name='bill_list'),
    url(r'bills/unpaid/$', 'list_detail.object_list',
        {'queryset': Bill.objects.filter(is_paid__exact=False),
         'template_name': 'membership/bill_list.html',
         'template_object_name': 'bill',
         'paginate_by': 100}, name='unpaid_bill_list'),

    url(r'payments/$', 'list_detail.object_list',
        {'queryset': Payment.objects.all(),
         'template_name': 'membership/payment_list.html',
         'template_object_name': 'payment',
         'paginate_by': 100}, name='payment_list'),
    url(r'payments/unknown/$', 'list_detail.object_list',
        {'queryset': Payment.objects.filter(bill__exact=None),
         'template_name': 'membership/payment_list.html',
         'template_object_name': 'payment',
         'paginate_by': 100}, name='unknown_payment_list'),

    url(r'memberships/new/success/$', 'simple.direct_to_template',
        {'template': 'membership/new_person_application_success.html'}, name='new_person_application_success'),
    url(r'organizations/new/success/$', 'simple.direct_to_template',
        {'template': 'membership/new_organization_application_success.html'}, name='new_organization_application_success'),
    url(r'memberships/new/fail/$', 'simple.direct_to_template',
        {'template': 'membership/new_application_fail.html'}, name='new_application_fail'),
)
