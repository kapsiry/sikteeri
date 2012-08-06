from django.conf.urls.defaults import patterns, url
from django.contrib.auth.decorators import permission_required
from django.shortcuts import redirect
from django.db.models import Count
import django.views.generic.list_detail
from membership.models import Contact, Membership, Payment, BillingCycle
from sikteeri.settings import ENTRIES_PER_PAGE
from management.commands.paper_reminders import get_data as get_paper_reminders

# Shortcuts
payments = Payment.objects.all().order_by('-payment_day', '-id')

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
    url(r'public_memberlist/$', 'membership.views.public_memberlist'),
    url(r'unpaid_members/$', 'membership.views.unpaid_members'),

    # Should we use this?
    # <http://docs.djangoproject.com/en/dev/ref/generic-views/#django-views-generic-create-update-create-object>
    url(r'contacts/edit/(\d+)/$', 'membership.views.contact_edit', name='contact_edit'),

    url(r'memberships/edit/(\d+)/$', 'membership.views.membership_edit', name='membership_edit'),
    url(r'memberships/duplicates/(\d+)/$', 'membership.views.membership_duplicates', name='membership_duplicates'),

    url(r'memberships/delete/(\d+)/$', 'membership.views.membership_delete', name='membership_delete'),
    url(r'memberships/convert_to_an_organization/(\d+)/$', 'membership.views.membership_convert_to_organization', name='membership_convert_to_organization'),

    url(r'bills/edit/(\d+)/$', 'membership.views.bill_edit', name='bill_edit'),
    url(r'billing_cycles/connect_payment/(\d+)/$', 'membership.views.billingcycle_connect_payment', name='billingcycle_connect_payment'),
    url(r'billing_cycles/edit/(\d+)/$', 'membership.views.billingcycle_edit', name='billingcycle_edit'),

    url(r'payments/edit/(\d+)/$', 'membership.views.payment_edit', name='payment_edit'),
    url(r'payments/import/$', 'membership.views.import_payments', name='import_payments'),
    url(r'payments/send_duplicate_notification/(\d+)$', 'membership.views.send_duplicate_notification', name='payment_send_duplicate_notification'),

    # url(r'memberships/new/handle_json/$', 'membership.views.handle_json', name='membership_pre-approval_handle_json'),
    url(r'memberships/.*/handle_json/$', 'membership.views.handle_json', name='memberships_handle_json'),
    url(r'memberships/handle_json/$', 'membership.views.handle_json', name='membership_handle_json'),
    url(r'handle_json/$', 'membership.views.handle_json', name='membership_handle_json'),

    url(r'admtool/(\d+)$', 'membership.views.admtool_membership_detail_json', name='admtool'),
    url(r'admtool/lookup/alias/(.+)$', 'membership.views.admtool_lookup_alias_json', name='admtool'),

    url(r'memberships/new/$', 'membership.views.member_object_list',
        {'queryset': Membership.objects.filter(status__exact='N').order_by('id'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': ENTRIES_PER_PAGE}, name='new_memberships'),
    url(r'memberships/preapproved/$', 'membership.views.member_object_list',
        {'queryset': Membership.objects.filter(status__exact='P').order_by('id'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': ENTRIES_PER_PAGE}, name='preapproved_memberships'),
    url(r'memberships/preapproved-plain/$', 'membership.views.member_object_list',
        {'queryset': Membership.objects.filter(status__exact='P').order_by('id'),
         'template_name': 'membership/membership_list_plaintext.html',
         'template_object_name': 'member'},
         name='preapproved_memberships_plain'),
    url(r'memberships/approved/$', 'membership.views.member_object_list',
        {'queryset': Membership.objects.filter(status__exact='A').
            order_by('person__last_name', 'person__first_name', 'id'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': ENTRIES_PER_PAGE}, name='approved_memberships'),
    url(r'memberships/approved-emails/$', 'membership.views.member_object_list',
        {'queryset': Membership.objects.filter(status__exact='A').
            order_by('id').values('person__email', 'organization__email'),
         'template_name': 'membership/membership_list_emails.txt',
         'template_object_name': 'member',
         'mimetype': 'text/plain'},
         name='approved_memberships_emails'),
    url(r'memberships/deleted/$', 'membership.views.member_object_list',
        {'queryset': Membership.objects.filter(status__exact='D').order_by('-id'),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': ENTRIES_PER_PAGE}, name='deleted_memberships'),
    url(r'memberships/$', 'membership.views.member_object_list',
        {'queryset': Membership.objects.all(),
         'template_name': 'membership/membership_list.html',
         'template_object_name': 'member',
         'paginate_by': ENTRIES_PER_PAGE}, name='all_memberships'),

    url(r'^memberships/inline/search/(?P<query>\w+)/$', 'membership.views.search',
        {'template_name': 'membership/membership_list_inline.html',
         'template_object_name': 'member', 'paginate_by': ENTRIES_PER_PAGE}),
    url(r'^memberships/search/((?P<query>\w+)/)?$', 'membership.views.search',
        {'template_name': 'membership/membership_list.html',
         'template_object_name': 'member', 'paginate_by': ENTRIES_PER_PAGE},
         name='membership_search'),

    url(r'bills/$', 'membership.views.billing_object_list',
        {'queryset': BillingCycle.objects.filter(
            membership__status='A').order_by('-start', '-id'),
         'template_name': 'membership/bill_list.html',
         'template_object_name': 'cycle',
         'paginate_by': ENTRIES_PER_PAGE}, name='cycle_list'),
    url(r'bills/unpaid/$', 'membership.views.billing_object_list',
        {'queryset': BillingCycle.objects.filter(is_paid__exact=False,
            membership__status='A').order_by('start', 'id'),
         'template_name': 'membership/bill_list.html',
         'template_object_name': 'cycle',
         'paginate_by': ENTRIES_PER_PAGE}, name='unpaid_cycle_list'),
    url(r'bills/locked/$', 'membership.views.billing_object_list',
        {'queryset': get_paper_reminders(),
         'template_name': 'membership/bill_list.html',
         'template_object_name': 'cycle',
         'paginate_by': ENTRIES_PER_PAGE}, name='locked_cycle_list'),
    url(r'bills/print_reminders/$', 'membership.views.print_reminders',
            name='print_reminders'),

    url(r'payments/$', 'membership.views.billing_object_list',
        {'queryset': payments,
         'template_name': 'membership/payment_list.html',
         'template_object_name': 'payment',
         'paginate_by': ENTRIES_PER_PAGE}, name='payment_list'),
    url(r'payments/unknown/$', 'membership.views.billing_object_list',
        {'queryset': payments.filter(billingcycle=None, ignore=False),
         'template_name': 'membership/payment_list.html',
         'template_object_name': 'payment',
         'paginate_by': ENTRIES_PER_PAGE}, name='unknown_payment_list'),
    url(r'payments/ignored/$', 'membership.views.billing_object_list',
        {'queryset': payments.filter(ignore=True),
         'template_name': 'membership/payment_list.html',
         'template_object_name': 'payment',
         'paginate_by': ENTRIES_PER_PAGE}, name='ignored_payment_list'),

    url(r'static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '../membership/static/'}),
)

urlpatterns += patterns('django.views.generic',

    url(r'application/person/success/$', 'simple.direct_to_template',
        {'template': 'membership/new_person_application_success.html'}, name='new_person_application_success'),
    url(r'application/organization/success/$', 'simple.direct_to_template',
        {'template': 'membership/new_organization_application_success.html'}, name='new_organization_application_success'),
    url(r'application/error/$', 'simple.direct_to_template',
        {'template': 'membership/new_application_error.html'}, name='new_application_error'),
)
