from django.contrib import admin

from models import *

admin.site.register(Membership)
admin.site.register(Alias)
admin.site.register(Fee)
admin.site.register(BillingCycle)
admin.site.register(Bill)
admin.site.register(Payment)
