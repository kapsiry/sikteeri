from django.contrib import admin
from membership.models import Membership, Contact, Fee, BillingCycle, Bill,\
    Payment


class ContactAdmin(admin.ModelAdmin):
    search_fields = [
        'first_name',
        'given_names',
        'last_name',
        'organization_name',
        'email',
    ]


class MembershipAdmin(admin.ModelAdmin):
    # search_fields has to be set so get_search_results is called
    search_fields = ['*ignored*']
    # Display as text id field, with search button
    raw_id_fields = ['person', 'billing_contact', 'tech_contact', 'organization']

    def get_search_results(self, request, queryset, search_term):
        """Use same search as on Sikteeri site for Django Admin"""
        qs = Membership.search(search_term)
        return qs, False


admin.site.register(Membership, MembershipAdmin)
admin.site.register(Contact, ContactAdmin)
admin.site.register(Fee)
admin.site.register(BillingCycle)
admin.site.register(Bill)
admin.site.register(Payment)
