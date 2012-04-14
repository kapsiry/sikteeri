from django.contrib import admin
from membership.models import Membership, Contact, Fee, BillingCycle, Bill,\
    Payment

admin.site.register(Membership)
admin.site.register(Contact)
admin.site.register(Fee)
admin.site.register(BillingCycle)
admin.site.register(Bill)
admin.site.register(Payment)
