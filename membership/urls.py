from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required, permission_required
from django.conf.urls.defaults import *
from django.shortcuts import redirect
import django.views.generic.list_detail

from membership.models import *
from membership.forms import *

ENTRIES_PER_PAGE=30

urlpatterns = patterns('',
    (r'jsi18n/$', 'django.views.i18n.javascript_catalog', {'packages': ('membership')}),

    url(r'application/person/$', 'membership.views.person_application', name='person_application'),
    url(r'application/organization/$', 'membership.views.organization_application',
        name='organization_application'),
    url(r'application/organization/add_contact/(\w+)/$', 'membership.views.organization_application_add_contact',
        name='organization_application_add_contact'),
    url(r'application/organization/services/$', 'membership.views.organization_application_services',
        name='organization_application_services'),
    url(r'application/organization/review/$', 'membership.views.organization_application_review',
        name='organization_application_review'),
    url(r'application/organization/save/$', 'membership.views.organization_application_save',
        name='organization_application_save'),
    url(r'application/$', 'membership.views.new_application', name='new_application'),

    url(r'testemail/$', 'membership.views.test_email', name='test_email'),
    url(r'metrics/$', 'membership.views.membership_metrics'),

    # Should we use this?
    # <http://docs.djangoproject.com/en/dev/ref/generic-views/#django-views-generic-create-update-create-object>
    url(r'contacts/edit/(\d+)/$', 'membership.views.contact_edit', name='contact_edit'),

    url(r'memberships/edit/(\d+)/$', 'membership.views.membership_edit', name='membership_edit'),

    url(r'memberships/delete/(\d+)/$', 'membership.views.membership_delete', name='membership_delete'),
    url(r'memberships/convert_to_an_organization/(\d+)/$', 'membership.views.membership_convert_to_organization', name='membership_convert_to_organization'),

    url(r'bills/edit/(\d+)/$', 'membership.views.bill_edit', name='bill_edit'),
    url(r'billing_cycles/connect_payment/(\d+)/$', 'membership.views.billingcycle_connect_payment', name='billingcycle_connect_payment'),
    url(r'billing_cycles/edit/(\d+)/$', 'membership.views.billingcycle_edit', name='billingcycle_edit'),

    url(r'payments/edit/(\d+)/$', 'membership.views.payment_edit', name='payment_edit'),
    url(r'payments/import/$', 'membership.views.import_payments', name='import_payments'),

    # url(r'memberships/new/handle_json/$', 'membership.views.handle_json', name='membership_pre-approval_handle_json'),
    url(r'memberships/.*/handle_json/$', 'membership.views.handle_json', name='memberships_handle_json'),
    url(r'memberships/handle_json/$', 'membership.views.handle_json', name='membership_handle_json'),
    url(r'handle_json/$', 'membership.views.handle_json', name='membership_handle_json'),

    url(r'admtool/(\d+)$', 'membership.views.admtool_membership_detail_json', name='admtool'),
    url(r'admtool/lookup/alias/(.+)$', 'membership.views.admtool_lookup_alias_json', name='admtool'),

    url(r'static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '../membership/static/'}),
)

@permission_required('membership.read_members')
def member_object_list(*args, **kwargs):
    return django.views.generic.list_detail.object_list(*args, **kwargs)

@permission_required('membership.read_bills')
def billing_object_list(*args, **kwargs):
    return django.views.generic.list_detail.object_list(*args, **kwargs)

# This should list any bills/cycles that were forcefully set as paid even
# though insufficient payments were paid.
# @permission_required('membership.read_bills')
# def forced_paid_cycles_list(*args, **kwargs):
#     paid_q = Q(is_paid__exact=True)
#     payments_sum_q = Q(payment_set.aggregate(Sum('amount'))__lt=sum)
#     qs = BillingCycle.objects.filter(paid_q, payments_sum_q)
#     return django.views.generic.list_detail.object_list(request, queryset=qs, *args, **kwargs)

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

# Shortcuts
payments = Payment.objects.all().order_by('-payment_day')

urlpatterns += patterns('django.views.generic',

    url(r'memberships/new/$', member_object_list,
        {'queryset': Membership.objects.filter(status__exact='N').order_by('id'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': ENTRIES_PER_PAGE}, name='new_memberships'),
    url(r'memberships/preapproved/$', member_object_list,
        {'queryset': Membership.objects.filter(status__exact='P').order_by('id'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': ENTRIES_PER_PAGE}, name='preapproved_memberships'),
    url(r'memberships/approved/$', member_object_list,
        {'queryset': Membership.objects.filter(status__exact='A').order_by('person__last_name', 'person__first_name'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': ENTRIES_PER_PAGE}, name='approved_memberships'),
    url(r'memberships/deleted/$', member_object_list,
        {'queryset': Membership.objects.filter(status__exact='D').order_by('-id'),
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
        {'queryset': BillingCycle.objects.filter(
            membership__status='A').order_by('-start'),
         'template_name': 'membership/bill_list.html',
         'template_object_name': 'cycle',
         'paginate_by': ENTRIES_PER_PAGE}, name='cycle_list'),
    url(r'bills/unpaid/$', billing_object_list,
        {'queryset': BillingCycle.objects.filter(is_paid__exact=False,
            membership__status='A').order_by('start'),
         'template_name': 'membership/bill_list.html',
         'template_object_name': 'cycle',
         'paginate_by': ENTRIES_PER_PAGE}, name='unpaid_cycle_list'),

    url(r'payments/$', billing_object_list,
        {'queryset': payments,
         'template_name': 'membership/payment_list.html',
         'template_object_name': 'payment',
         'paginate_by': ENTRIES_PER_PAGE}, name='payment_list'),
    url(r'payments/unknown/$', billing_object_list,
        {'queryset': payments.filter(billingcycle=None, ignore=False),
         'template_name': 'membership/payment_list.html',
         'template_object_name': 'payment',
         'paginate_by': ENTRIES_PER_PAGE}, name='unknown_payment_list'),

    url(r'application/person/success/$', 'simple.direct_to_template',
        {'template': 'membership/new_person_application_success.html'}, name='new_person_application_success'),
    url(r'application/organization/success/$', 'simple.direct_to_template',
        {'template': 'membership/new_organization_application_success.html'}, name='new_organization_application_success'),
    url(r'application/error/$', 'simple.direct_to_template',
        {'template': 'membership/new_application_error.html'}, name='new_application_error'),
)
