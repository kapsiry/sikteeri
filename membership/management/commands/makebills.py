from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import NoArgsCommand

import logging
logger = logging.getLogger("sikteeri.membership.management.commands.makebills")
from datetime import datetime, timedelta

from membership.models import *
from membership.utils import *

class MembershipNotApproved(Exception): pass

def create_billingcycle(membership):
    """
    Creates a new billing cycle for a membership.

    If a previous billing cycle exists, the end date is used as the start
    date for the new one.  If a previous one doesn't exist, e.g. it is a new
    user, we use the time when they were approved.
    """
    if membership.status != 'A':
        logger.critical("%s not Approved. Cannot send bill" % repr(membership))
        raise MembershipNotApproved("%s not Approved. Cannot send bill" % repr(membership))
    try:
        newest_existing_billing_cycle = membership.billingcycle_set.latest('end')
    except ObjectDoesNotExist:
        newest_existing_billing_cycle = None

    if newest_existing_billing_cycle != None:
        cycle_start = newest_existing_billing_cycle.end
    elif membership.approved != None:
        cycle_start = membership.approved
    else:
        logger.critical("%s is missing the approved timestamp. Cannot send bill" % repr(membership))
        raise MembershipNotApproved("%s is missing the approved timestamp. Cannot send bill" % repr(membership))

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
    bill.reminder_count = billing_cycle.bill_set.count()
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
                if can_send_reminder(last_due_date):
                    send_reminder(member)
                    logger.info("makebills: sent a reminder to %s." %
                                 repr(member))

class Command(NoArgsCommand):
    help = 'Find expiring billing cycles, send bills, send reminders'

    def handle_noargs(self, **options):
        makebills()
