from django.contrib.auth.decorators import login_required
from django.conf.urls.defaults import *
import django.views.generic.list_detail

from membership.models import *
from membership.forms import *

urlpatterns = patterns('',
    (r'jsi18n/$', 'django.views.i18n.javascript_catalog', {'packages': ('membership')}),
    
    url(r'persons/application/$', 'membership.views.person_application', name='person_application'),
    url(r'organizations/new/$', 'membership.views.organization_application',
        name='organization_application'),
    url(r'organizations/new/add_contact/(\w+)/$', 'membership.views.organization_application_add_contact',
        name='organization_application_add_contact'),
    url(r'organizations/new/application/review/$', 'membership.views.organization_application_review',
        name='organization_application_review'),
    url(r'organizations/new/application/save/$', 'membership.views.organization_application_save',
        name='organization_application_save'),
    url(r'memberships/application/$', 'membership.views.new_application', name='new_application'),

    url(r'contacts/edit/(\d+)/$', 'membership.views.contact_edit', name='contact_edit'),

    url(r'memberships/edit_inline/(\d+)/$', 'membership.views.membership_edit_inline', name='membership_edit_inline'),
    url(r'memberships/edit/(\d+)/$', 'membership.views.membership_edit', name='membership_edit'),
    url(r'memberships/preapprove/(\d+)/$', 'membership.views.membership_preapprove', name='membership_preapprove'),

    url(r'memberships/approve/(\d+)/$', 'membership.views.membership_approve', name='membership_approve'),
    
    # url(r'memberships/new/handle_json/$', 'membership.views.handle_json', name='membership_pre-approval_handle_json'),
    url(r'memberships/.*/handle_json/$', 'membership.views.handle_json', name='memberships_handle_json'),
    url(r'memberships/handle_json/$', 'membership.views.handle_json', name='membership_handle_json'),
    
    url(r'static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '../membership/static/'}),
)

# FIXME: should require admin priviledge, too.
@login_required
def limited_object_list(*args, **kwargs):
    return django.views.generic.list_detail.object_list(*args, **kwargs)

@login_required
def search(request, query=None,
           template_name='membership/membership_list.html'):
    if not query:
        query = request.REQUEST.get("query", None)
    # This could be simplified into a single SQL query, but isn't done so due
    # to the most probable SQL syntax incompatibilities.
    person_first_name_ids = Contact.objects.filter(first_name__icontains=query).values('id')
    person_given_names_ids = Contact.objects.filter(given_names__icontains=query).values('id')
    person_last_name_ids = Contact.objects.filter(last_name__icontains=query).values('id')
    organization_name_ids = Contact.objects.filter(organization_name__icontains=query).values('id')
    
    all_ids = set()
    def add_dict_values_to_set(dicts):
        for dict in dicts:
            all_ids.add(str(dict["id"]))
    
    add_dict_values_to_set(person_first_name_ids)
    add_dict_values_to_set(person_given_names_ids)
    add_dict_values_to_set(person_last_name_ids)
    add_dict_values_to_set(organization_name_ids)
    
    qs = Membership.objects.extra(where=['id IN (%s)' % ", ".join(all_ids)])
    
    return django.views.generic.list_detail.object_list(request, queryset=qs,
                                                        template_name=template_name,
                                                        template_object_name='member',
                                                        paginate_by=100)

urlpatterns += patterns('django.views.generic',

    url(r'memberships/new/$', limited_object_list,
        {'queryset': Membership.objects.filter(status__exact='N'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': 100}, name='new_memberships'),
    url(r'memberships/preapproved/$', limited_object_list,
        {'queryset': Membership.objects.filter(status__exact='P'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': 100}, name='preapproved_memberships'),
    url(r'memberships/approved/$', limited_object_list,
        {'queryset': Membership.objects.filter(status__exact='A'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': 100}, name='approved_memberships'),
    url(r'memberships/disabled/$', limited_object_list,
        {'queryset': Membership.objects.filter(status__exact='D'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': 100}, name='disabled_memberships'),
    url(r'memberships/$', limited_object_list,
        {'queryset': Membership.objects.all(),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': 100}, name='all_memberships'),

    url(r'^memberships/inline/search/(?P<query>\w+)/$', search,
        {'template_name': 'membership/membership_list_inline.html'}),
    url(r'^memberships/search/((?P<query>\w+)/)?$', search, name="membership_search"),

    url(r'bills/$', limited_object_list,
        {'queryset': Bill.objects.all(),
         'template_name': 'membership/bill_list.html',
         'template_object_name': 'bill',
         'paginate_by': 100}, name='bill_list'),
    url(r'bills/unpaid/$', limited_object_list,
        {'queryset': Bill.objects.filter(is_paid__exact=False),
         'template_name': 'membership/bill_list.html',
         'template_object_name': 'bill',
         'paginate_by': 100}, name='unpaid_bill_list'),

    url(r'payments/$', limited_object_list,
        {'queryset': Payment.objects.all(),
         'template_name': 'membership/payment_list.html',
         'template_object_name': 'payment',
         'paginate_by': 100}, name='payment_list'),
    url(r'payments/unknown/$', limited_object_list,
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
