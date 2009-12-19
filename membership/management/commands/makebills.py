from django.core.management.base import NoArgsCommand

from membership.models import *
from membership.utils import *

class Command(NoArgsCommand):
    help = 'Find expiring cycles, send bills, send reminders'

    def handle_noargs(self, **options):
        for member in Membership.objects.all():
            try:
                cycle = member.billingcycle_set.order_by('-end')[0]
            except:
                continue
            if cycle.end < datetime.now() + timedelta(days=28):
                new_cycle(member)
                print "New cycle"
                continue
            if cycle.is_paid():
                continue

            if cycle.start < datetime.now() + timedelta(days=7) and len(cycle.bill_set.all()) == 1:
                sendreminder(member)
                print "Reminder"
            elif cycle.start < datetime.now():
                disable_member(member)
                print "Disabled"


