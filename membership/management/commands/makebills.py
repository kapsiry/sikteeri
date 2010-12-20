from django.core.management.base import NoArgsCommand

import logging
import datetime

from membership.models import *
from membership.utils import *

class NoApprovedLogEntry(Exception): pass

def create_billingcycle(membership):
    """
    Creates a new billing cycle for a membership.
    
    If a previous billing cycle exists, the end date is used as the start
    date for the new one.  If a previous one doesn't exist, the event log
    of the membership is consulted and the newest 'Approved" entry is used
    as the start date.
    """
    try:
        old_cycle = membership.billingcycle_set.order_by('-end')[0]
    except IndexError, ie:
        old_cycle = None

    if old_cycle != None:
        cycle_start = old_cycle.end
    else:
        log_items = membership.logs.all()
        approve_entries = m.logs.filter(change_message="Approved").order_by('-action_time')
        if len(approve_entries) == 0:
            logging.critical("makebills: %s doesn't have Approved log entry"
                             % repr(membership))
            raise NoApprovedLogEntry("%s doesn't have an Approved log entry,"
                                     % repr(membership)
                                     + " start time for billing cycle can't be determined")
        newest = approve_entries[0]
        if len(approve_entries) > 1:
            logging.warning('makebills: more than one Approved-entry for %s, choosing %s'
                            % (repr(membership), newest.action_time.strftime("%Y-%m-%d %H:%M")))
        cycle_start = newest.action_time

    billing_cycle = BillingCycle(membership=membership, start=cycle_start)
    billing_cycle.save()
    bill = Bill(billingcycle=billing_cycle)
    bill.save()
    bill.send_as_email()

def sendreminder(membership): # XXX Test if cycle is paid?
    billing_cycle = membership.billingcycle_set.order_by('-end')[0]
    bill = Bill(billingcycle=billing_cycle)
    bill.save()
    bill.send_as_email()

def disable_member(membership):
    pass # XXX


class Command(NoArgsCommand):
    help = 'Find expiring billing cycles, send bills, send reminders'

    def handle_noargs(self, **options):
        for member in Membership.objects.filter(status='A'):
            cycles = member.billingcycle_set.order_by('-end')

            if len(cycles) == 0:
                billing_cycle = BillingCycle(membership=self)
                billing_cycle.save()
                bill = Bill(billingcycle=billing_cycle)
                bill.save()
                
            latest_cycle = cycles

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


