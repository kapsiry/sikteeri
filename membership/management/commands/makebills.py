# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
import calendar

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import NoArgsCommand
from django.utils import translation
from django.conf import settings
from django.db import transaction
from django.conf import settings

from membership.models import *
from membership.utils import *

logger = logging.getLogger("membership.makebills")

class MembershipNotApproved(Exception): pass

def create_billingcycle(membership):
    """
    Creates a new billing cycle for a membership.

    If a previous billing cycle exists, the end date is used as the start
    date for the new one.  If a previous one doesn't exist, e.g. it is a new
    user, we use the time when they were approved.
    """
    billing_cycle = None
    try:
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

        with transaction.atomic():
            billing_cycle = BillingCycle(membership=membership, start=cycle_start)
            billing_cycle.save()
            bill = Bill(billingcycle=billing_cycle)
            bill.save()
        bill.send_as_email()
        return billing_cycle
    except Exception as e:
        logger.critical("%s" % traceback.format_exc())
        logger.critical("Transaction rolled back, billing cycle not created!")
        raise

def can_send_reminder(last_due_date, latest_recorded_payment):
    """
    Determine if we have recent payments so that we can be sure
    recent payments have been imported into the system.
    """
    if not settings.ENABLE_REMINDERS:
        return False
    can_send = True
    if not latest_recorded_payment:
        logger.critical("no payments in the database.")
        can_send = False
    else:
        if latest_recorded_payment > datetime.now():
            latest_recorded_payment = datetime.now()
        due_plus_margin = last_due_date + timedelta(days=settings.REMINDER_GRACE_DAYS)
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
    logger.info("Running makebills...")
    latest_recorded_payment = Payment.latest_payment_date()

    dt = datetime.now()
    last_of_month = datetime(dt.year, dt.month, calendar.monthrange(dt.year, dt.month)[1], 23, 59, 59)
    for member in Membership.objects.filter(status='A').filter(id__gt=0):
        # Billing cycles and bills
        cycles = member.billingcycle_set
        if cycles.count() == 0:
            cycle = create_billingcycle(member)
            logger.info("Created billing cycle %s for %s" % (repr(cycle), repr(member)))
        else:
            latest_cycle = cycles.latest("end")
            if latest_cycle.end <= last_of_month:
                cycle = create_billingcycle(member)
                logger.info("Created billing cycle %s for %s" %
                            (repr(cycle), repr(member)))

        # Reminders
        latest_cycle = member.billingcycle_set.latest('end')
        if not latest_cycle.is_paid:
            if latest_cycle.is_last_bill_late():
                last_due_date = latest_cycle.last_bill().due_date
                if can_send_reminder(last_due_date, latest_recorded_payment):
                    reminder = send_reminder(member)
                    logger.info("Sent reminder %s to %s." % (repr(reminder), repr(member)))
    logger.info("Done running makebills.")

class Command(NoArgsCommand):
    help = 'Find expiring billing cycles, send bills, send reminders'

    def handle_noargs(self, **options):
        translation.activate(settings.LANGUAGE_CODE)
        makebills()
