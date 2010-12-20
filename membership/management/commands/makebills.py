from django.core.management.base import NoArgsCommand

import datetime

from membership.models import *
from membership.utils import *

# TODO: this command should also generate billing cycles
# billing_cycle = BillingCycle(membership=self)
# billing_cycle.save() # Creating an instance does not touch db and we need and id for the Bill
# bill = Bill(billingcycle=billing_cycle)
# bill.save()

class Command(NoArgsCommand):
    help = 'Find expiring billing cycles, send bills, send reminders'

    def handle_noargs(self, **options):
        for member in Membership.objects.all():
            try:
                billingcycle = member.billingcycle_set.order_by('-end')[0]
            except:
                continue
            if billingcycle.end < datetime.now() + datetime.timedelta(days=28):
                new_cycle(member)
                print "New billing cycle"
                continue
            if billingcycle.is_paid():
                continue
            
            # FIXME: should reflect last bill due date, not billing cycle start
            if billingcycle.start < datetime.now() + datetime.timedelta(days=7) \
                   and len(billingcycle.bill_set.all()) == 1:
                sendreminder(member)
                print "Reminder"
            elif billingcycle.start < datetime.now():
                disable_member(member)
                print "Disabled"


