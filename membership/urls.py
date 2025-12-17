from django.urls import re_path
from django.conf.urls.static import static
from django.views.generic.base import TemplateView

from membership.models import Membership, Payment, BillingCycle
from django.conf import settings
from django.views.i18n import JavaScriptCatalog
import membership.views

# Shortcuts
payments = Payment.objects.all().order_by('-payment_day', '-id')
ENTRIES_PER_PAGE = settings.ENTRIES_PER_PAGE

urlpatterns = [
    re_path(r'^jsi18n/$', JavaScriptCatalog.as_view(packages=["membership"]), name='javascript-catalog'),

    re_path(r'application/person/$', membership.views.person_application, name='person_application'),
    re_path(r'application/organization/$', membership.views.organization_application,
        name='organization_application'),
    re_path(r'application/organization/add_contact/(\w+)/$', membership.views.organization_application_add_contact,
        name='organization_application_add_contact'),
    re_path(r'application/organization/services/$', membership.views.organization_application_services,
        name='organization_application_services'),
    re_path(r'application/organization/review/$', membership.views.organization_application_review,
        name='organization_application_review'),
    re_path(r'application/organization/save/$', membership.views.organization_application_save,
        name='organization_application_save'),
    re_path(r'application/$', membership.views.new_application, name='new_application'),

    re_path(r'testemail/$', membership.views.test_email, name='test_email'),
    re_path(r'metrics/$', membership.views.membership_metrics),
    re_path(r'public_memberlist/$', membership.views.public_memberlist),
    re_path(r'unpaid_members/$', membership.views.unpaid_members),
    re_path(r'users_to_lock/$', membership.views.users_to_lock),

    # Should we use this?
    # <http://docs.djangoproject.com/en/dev/ref/generic-views/#django-views-generic-create-update-create-object>
    re_path(r'contacts/edit/(\d+)/$', membership.views.contact_edit, name='contact_edit'),

    re_path(r'contacts/add/(billing_contact|tech_contact)/(\d+)/$', membership.views.contact_add, name='contact_add'),

    re_path(r'memberships/edit/(\d+)/$', membership.views.membership_edit, name='membership_edit'),
    re_path(r'memberships/duplicates/(\d+)/$', membership.views.membership_duplicates, name='membership_duplicates'),

    re_path(r'memberships/delete/(\d+)/$', membership.views.membership_delete, name='membership_delete'),
    re_path(r'memberships/dissociate/(\d+)/$', membership.views.membership_dissociate, name='membership_dissociate'),
    re_path(r'memberships/request_dissociation/(\d+)/$', membership.views.membership_request_dissociation,
        name='membership_request_dissociation'),
    re_path(r'memberships/cancel_dissociation_request/(\d+)/$', membership.views.membership_cancel_dissociation_request,
    name='membership_cancel_dissociation_request'),
    re_path(r'memberships/convert_to_an_organization/(\d+)/$', membership.views.membership_convert_to_organization,
        name='membership_convert_to_organization'),

    re_path(r'bills/edit/(\d+)/$', membership.views.bill_edit, name='bill_edit'),
    re_path(r'bills/pdf/bill_(\d+)\.pdf$', membership.views.bill_pdf, name='bill_pdf'),
    re_path(r'billing_cycles/connect_payment/(\d+)/$', membership.views.billingcycle_connect_payment,
        name='billingcycle_connect_payment'),
    re_path(r'billing_cycles/edit/(\d+)/$', membership.views.billingcycle_edit, name='billingcycle_edit'),

    re_path(r'payments/edit/(\d+)/$', membership.views.payment_edit, name='payment_edit'),
    re_path(r'payments/import/$', membership.views.import_payments, name='import_payments'),
    re_path(r'payments/send_duplicate_notification/(\d+)$', membership.views.send_duplicate_notification,
        name='payment_send_duplicate_notification'),

    # re_path(r'memberships/new/handle_json/$', 'membership.views.handle_json', name='membership_pre-approval_handle_json'),
    re_path(r'memberships/.*/handle_json/$', membership.views.handle_json, name='memberships_handle_json'),
    re_path(r'application/.*/handle_json/$', membership.views.handle_json, name='memberships_handle_json'),
    re_path(r'application/handle_json/$', membership.views.handle_json, name='memberships_handle_json'),
    re_path(r'memberships/handle_json/$', membership.views.handle_json, name='membership_handle_json'),
    re_path(r'handle_json/$', membership.views.handle_json, name='membership_handle_json'),

    re_path(r'admtool/(\d+)$', membership.views.admtool_membership_detail_json, name='admtool'),
    re_path(r'admtool/lookup/alias/(.+)$', membership.views.admtool_lookup_alias_json, name='admtool'),

    re_path(r'memberships/new/$', membership.views.member_object_list,
        {'queryset': Membership.objects.filter(status__exact='N').order_by('id'),
         'template_name': 'membership/membership_list.html',
         'context_object_name': 'member_list',
         'paginate_by': ENTRIES_PER_PAGE}, name='new_memberships'),
    re_path(r'memberships/preapproved/$', membership.views.member_object_list,
        {'queryset': Membership.objects.filter(status__exact='P').order_by('id'),
         'template_name': 'membership/membership_list.html',
         'context_object_name': 'member_list',
         'paginate_by': ENTRIES_PER_PAGE}, name='preapproved_memberships'),
    re_path(r'memberships/preapproved-plain/$', membership.views.member_object_list,
        {'queryset': Membership.objects.filter(status__exact='P').order_by('id'),
         'template_name': 'membership/membership_list_plaintext.html',
         'context_object_name': 'member_list'},
        name='preapproved_memberships_plain'),
    re_path(r'memberships/approved/$', membership.views.member_object_list,
        {'queryset': Membership.objects.filter(status__exact='A').
            order_by('person__last_name', 'person__first_name', 'id'),
         'template_name': 'membership/membership_list.html',
         'context_object_name': 'member_list',
         'paginate_by': ENTRIES_PER_PAGE}, name='approved_memberships'),
    re_path(r'memberships/dissociation_requested/$', membership.views.member_object_list,
        {'queryset': Membership.objects.filter(status__exact='S').
            order_by('person__last_name', 'person__first_name', 'id'),
         'template_name': 'membership/membership_list.html',
         'context_object_name': 'member_list',
         'paginate_by': ENTRIES_PER_PAGE}, name='dissociation_requested_memberships'),
    re_path(r'memberships/dissociation_requested-plain/$', membership.views.member_object_list,
        {'queryset': Membership.objects.filter(status__exact='S').order_by('id'),
         'template_name': 'membership/membership_list_plaintext.html',
         'context_object_name': 'member_list'},
        name='dissociation_requested_memberships_plain'),
    re_path(r'memberships/dissociated/$', membership.views.member_object_list,
        {'queryset': Membership.objects.filter(status__exact='I').
            order_by('person__last_name', 'person__first_name', 'id'),
         'template_name': 'membership/membership_list.html',
         'context_object_name': 'member_list',
         'paginate_by': ENTRIES_PER_PAGE}, name='dissociated_memberships'),
    re_path(r'memberships/approved-emails/$', membership.views.member_object_list,
        {'queryset': Membership.objects.filter(status__exact='A').
            order_by('id').values('person__email', 'organization__email'),
         'template_name': 'membership/membership_list_emails.txt',
         'context_object_name': 'member_list'},
        name='approved_memberships_emails'),
    re_path(r'memberships/unpaid_paper_reminded/$', membership.views.unpaid_paper_reminded,
        name='unpaid_paper_reminded_memberships'),
    re_path(r'memberships/unpaid_paper_reminded-plain/$', membership.views.unpaid_paper_reminded_plain,
        name='unpaid_paper_reminded_memberships_plain'),
    re_path(r'memberships/deleted/$', membership.views.member_object_list,
        {'queryset': Membership.objects.filter(status__exact='D').order_by('-id'),
         'template_name': 'membership/membership_list.html',
         'context_object_name': 'member_list',
         'paginate_by': ENTRIES_PER_PAGE}, name='deleted_memberships'),
    re_path(r'memberships/$', membership.views.member_object_list,
        {'queryset': Membership.objects.all(),
         'template_name': 'membership/membership_list.html',
         'context_object_name': 'member_list',
         'paginate_by': ENTRIES_PER_PAGE}, name='all_memberships'),

    re_path(r'^memberships/inline/search/$', membership.views.search,
        {'template_name': 'membership/membership_list_inline.html',
         'context_object_name': 'member_list', 'paginate_by': ENTRIES_PER_PAGE}),
    re_path(r'^memberships/search/$', membership.views.search,
        {'template_name': 'membership/membership_list.html',
         'context_object_name': 'member_list', 'paginate_by': ENTRIES_PER_PAGE},
        name='membership_search'),

    re_path(r'bills/$', membership.views.billing_object_list,
        {'queryset': BillingCycle.objects.filter(
            membership__status='A').order_by('-start', '-id'),
         'template_name': 'membership/bill_list.html',
         'context_object_name': 'cycle_list',
         'paginate_by': ENTRIES_PER_PAGE}, name='cycle_list'),
    re_path(r'bills/unpaid/$', membership.views.billing_object_list,
        {'queryset': BillingCycle.objects.filter(is_paid__exact=False, membership__status='A').order_by('start', 'id'),
         'template_name': 'membership/bill_list.html',
         'context_object_name': 'cycle_list',
         'paginate_by': ENTRIES_PER_PAGE}, name='unpaid_cycle_list'),
    re_path(r'bills/locked/$', membership.views.billing_object_list,
        {'queryset': BillingCycle.get_reminder_billingcycles(),
         'template_name': 'membership/bill_list.html',
         'context_object_name': 'cycle_list',
         'paginate_by': ENTRIES_PER_PAGE}, name='locked_cycle_list'),
    re_path(r'bills/print_reminders/$', membership.views.print_reminders,
        name='print_reminders'),

    re_path(r'payments/$', membership.views.billing_object_list,
        {'queryset': payments,
         'template_name': 'membership/payment_list.html',
         'context_object_name': 'payment_list',
         'paginate_by': ENTRIES_PER_PAGE}, name='payment_list'),
    re_path(r'payments/unknown/$', membership.views.billing_object_list,
        {'queryset': payments.filter(billingcycle=None, ignore=False),
         'template_name': 'membership/payment_list.html',
         'context_object_name': 'payment_list',
         'paginate_by': ENTRIES_PER_PAGE}, name='unknown_payment_list'),
    re_path(r'payments/ignored/$', membership.views.billing_object_list,
        {'queryset': payments.filter(ignore=True),
         'template_name': 'membership/payment_list.html',
         'context_object_name': 'payment_list',
         'paginate_by': ENTRIES_PER_PAGE}, name='ignored_payment_list'),
]

urlpatterns += [
    re_path(r'application/person/success/$',
        TemplateView.as_view(template_name='membership/new_person_application_success.html'),
        name='new_person_application_success'),
    re_path(r'application/organization/success/$',
        TemplateView.as_view(template_name='membership/new_organization_application_success.html'),
        name='new_organization_application_success'),
    re_path(r'application/error/$',
        TemplateView.as_view(template_name='membership/new_application_error.html'),
        name='new_application_error'),
]

urlpatterns += static(settings.STATIC_URL, document_root='../membership/static/')
