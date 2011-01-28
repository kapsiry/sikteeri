from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import NoArgsCommand

import logging
logger = logging.getLogger("sikteeri.membership.management.commands.makebills")
from datetime import datetime, timedelta

from membership.models import *
from membership.utils import *

class NoApprovedLogEntry(Exception): pass

def membership_approved_time(membership):
    """
    Fetches the newest 'Approved' entry and returns its time.
    """
    approve_entries = membership.logs.filter(change_message="Approved")
    approve_entry_count = approve_entries.count()
    if approve_entry_count == 0:
        logger.critical("%s doesn't have Approved log entry"
                         % repr(membership))
        raise NoApprovedLogEntry("%s doesn't have an Approved log entry,"
                                 % repr(membership)
                                 + " start time for billing cycle can't be determined.")
    newest = approve_entries.latest("action_time")
    if approve_entry_count > 1:
        logger.warning('more than one Approved-entry for %s, choosing %s'
                        % (repr(membership), newest.action_time.strftime("%Y-%m-%d %H:%M")))
    return newest.action_time

def create_billingcycle(membership):
    """
    Creates a new billing cycle for a membership.

    If a previous billing cycle exists, the end date is used as the start
    date for the new one.  If a previous one doesn't exist, e.g. it is a new
    user, we use the time when they were last approved.
    """
    try:
        newest_existing_billing_cycle = membership.billingcycle_set.latest('end')
    except ObjectDoesNotExist:
        newest_existing_billing_cycle = None

    if newest_existing_billing_cycle != None:
        cycle_start = newest_existing_billing_cycle.end
    else:
        cycle_start = membership_approved_time(membership)

    billing_cycle = BillingCycle(membership=membership, start=cycle_start)
    billing_cycle.save()
    bill = Bill(billingcycle=billing_cycle)
    bill.save()
    bill.send_as_email()
    return billing_cycle

def can_send_reminder(last_due_date):
    """
    Determine if we have recent payments so that we can be sure
    recent payments have been imported into the system.
    """
    can_send = True
    payments = Payment.objects
    if payments.count() == 0:
        logger.critical("no payments in the database.")
        can_send = False
    else:
        latest_recorded_payment = payments.latest("payment_day").payment_day
        if latest_recorded_payment > datetime.now():
            latest_recorded_payment = datetime.now()
        due_plus_margin = last_due_date + timedelta(days=14) # FIXME: hardcoded
        if latest_recorded_payment < due_plus_margin:
            can_send = False

    return can_send

def send_reminder(membership):
    billing_cycle = membership.billingcycle_set.latest('end')
    bill = Bill(billingcycle=billing_cycle)
    bill.save()
    bill.send_as_email()
    return bill

def makebills():
    for member in Membership.objects.filter(status='A'):
        # Billing cycles and bills
        cycles = member.billingcycle_set
        if cycles.count() == 0:
            create_billingcycle(member)
        else:
            latest_cycle = cycles.latest("end")
            if latest_cycle.end < datetime.now():
                logger.critical("no new billing cycle created for %s after an expired one!" % repr(member))
            if latest_cycle.end < datetime.now() + timedelta(days=28):
                create_billingcycle(member)

        # Reminders
        latest_cycle = member.billingcycle_set.latest('end')
        if not latest_cycle.is_paid:
            if latest_cycle.is_last_bill_late():
                last_due_date = latest_cycle.last_bill().due_date
                if can_send_remainder(last_due_date):
                    send_reminder(member)
                    logger.info("makebills: sent a reminder to %s." %
                                 repr(member))

class Command(NoArgsCommand):
    help = 'Find expiring billing cycles, send bills, send reminders'

    def handle_noargs(self, **options):
        makebills()
