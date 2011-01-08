from django.db.models import Q
from django.contrib.auth.decorators import login_required, permission_required
from django.conf.urls.defaults import *
from django.shortcuts import redirect
import django.views.generic.list_detail

from membership.models import *
from membership.forms import *

ENTRIES_PER_PAGE=30

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

    url(r'testemail/$', 'membership.views.test_email', name='test_email'),

    url(r'contacts/edit/(\d+)/$', 'membership.views.contact_edit', name='contact_edit'),

    url(r'memberships/edit_inline/(\d+)/$', 'membership.views.membership_edit_inline', name='membership_edit_inline'),
    url(r'memberships/edit/(\d+)/$', 'membership.views.membership_edit', name='membership_edit'),

    url(r'memberships/delete/(\d+)/$', 'membership.views.membership_delete', name='membership_delete'),

    # url(r'memberships/new/handle_json/$', 'membership.views.handle_json', name='membership_pre-approval_handle_json'),
    url(r'memberships/.*/handle_json/$', 'membership.views.handle_json', name='memberships_handle_json'),
    url(r'memberships/handle_json/$', 'membership.views.handle_json', name='membership_handle_json'),
    url(r'handle_json/$', 'membership.views.handle_json', name='membership_handle_json'),

    url(r'static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '../membership/static/'}),
)

@permission_required('membership.read_members')
def member_object_list(*args, **kwargs):
    return django.views.generic.list_detail.object_list(*args, **kwargs)

@permission_required('membership.read_bills')
def billing_object_list(*args, **kwargs):
    return django.views.generic.list_detail.object_list(*args, **kwargs)


@permission_required('membership.read_members')
def search(request, query=None,
           template_name='membership/membership_list.html'):
    if not query:
        query = request.REQUEST.get("query", None)

    if query.startswith("#"):
        return redirect('membership_edit', query.lstrip("#"))

    person_contacts = Contact.objects
    org_contacts = Contact.objects
    # Split into words and remove duplicates
    d = {}.fromkeys(query.split(" "))
    for word in d.keys():
        # Common search parameters
        email_q = Q(email__icontains=word)
        phone_q = Q(phone__icontains=word)
        sms_q = Q(sms__icontains=word)
        common_q = email_q | phone_q | sms_q

        # Search query for people
        f_q = Q(first_name__icontains=word)
        l_q = Q(last_name__icontains=word)
        g_q = Q(given_names__icontains=word)
        person_contacts = person_contacts.filter(f_q | l_q | g_q | common_q)

        # Search for organizations
        o_q = Q(organization_name__icontains=word)
        org_contacts = org_contacts.filter(o_q | common_q)

    # Combined single query
    person_q = Q(person__in=person_contacts)
    org_q = Q(organization__in=org_contacts)
    qs = Membership.objects.filter(person_q | org_q)
    if qs.count() == 1:
        return redirect('membership_edit', qs[0].id)

    qs = qs.order_by("organization__organization_name",
                     "person__last_name",
                     "person__first_name")
    return django.views.generic.list_detail.object_list(request, queryset=qs,
                                                        template_name=template_name,
                                                        template_object_name='member',
                                                        paginate_by=ENTRIES_PER_PAGE)

urlpatterns += patterns('django.views.generic',

    url(r'memberships/new/$', member_object_list,
        {'queryset': Membership.objects.filter(status__exact='N'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': ENTRIES_PER_PAGE}, name='new_memberships'),
    url(r'memberships/preapproved/$', member_object_list,
        {'queryset': Membership.objects.filter(status__exact='P'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': ENTRIES_PER_PAGE}, name='preapproved_memberships'),
    url(r'memberships/approved/$', member_object_list,
        {'queryset': Membership.objects.filter(status__exact='A'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': ENTRIES_PER_PAGE}, name='approved_memberships'),
    url(r'memberships/deleted/$', member_object_list,
        {'queryset': Membership.objects.filter(status__exact='D'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': ENTRIES_PER_PAGE}, name='deleted_memberships'),
    url(r'memberships/$', member_object_list,
        {'queryset': Membership.objects.all(),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': ENTRIES_PER_PAGE}, name='all_memberships'),

    url(r'^memberships/inline/search/(?P<query>\w+)/$', search,
        {'template_name': 'membership/membership_list_inline.html'}),
    url(r'^memberships/search/((?P<query>\w+)/)?$', search, name="membership_search"),

    url(r'bills/$', billing_object_list,
        {'queryset': Bill.objects.all(),
         'template_name': 'membership/bill_list.html',
         'template_object_name': 'bill',
         'paginate_by': ENTRIES_PER_PAGE}, name='bill_list'),
    url(r'bills/unpaid/$', billing_object_list,
        {'queryset': Bill.objects.filter(billingcycle__is_paid__exact=False),
         'template_name': 'membership/bill_list.html',
         'template_object_name': 'bill',
         'paginate_by': ENTRIES_PER_PAGE}, name='unpaid_bill_list'),

    url(r'payments/$', billing_object_list,
        {'queryset': Payment.objects.all(),
         'template_name': 'membership/payment_list.html',
         'template_object_name': 'payment',
         'paginate_by': ENTRIES_PER_PAGE}, name='payment_list'),
    url(r'payments/unknown/$', billing_object_list,
        {'queryset': Payment.objects.filter(billingcycle__exact=None),
         'template_name': 'membership/payment_list.html',
         'template_object_name': 'payment',
         'paginate_by': ENTRIES_PER_PAGE}, name='unknown_payment_list'),

    url(r'memberships/new/success/$', 'simple.direct_to_template',
        {'template': 'membership/new_person_application_success.html'}, name='new_person_application_success'),
    url(r'organizations/new/success/$', 'simple.direct_to_template',
        {'template': 'membership/new_organization_application_success.html'}, name='new_organization_application_success'),
    url(r'memberships/new/fail/$', 'simple.direct_to_template',
        {'template': 'membership/new_application_fail.html'}, name='new_application_fail'),
)
