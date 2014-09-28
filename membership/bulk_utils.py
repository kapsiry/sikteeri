# encoding: utf-8

from django.conf import settings

from membership import pdf
from membership.models import BillingCycle

from django.db.models import Count
from cStringIO import StringIO

import logging
from tempfile import mkstemp

logger = logging.getLogger("pdf_utils")

def get_reminder_billingcycles(memberid=None):
    if not settings.ENABLE_REMINDERS:
        return BillingCycle.objects.none()

    qs = BillingCycle.objects

    # Single membership case
    if memberid:
        logger.info('memberid: %s' % memberid)
        qs = qs.filter(membership__id=memberid)
        qs = qs.exclude(bill__type='P')
        return qs

    # For all memberships in Approved state
    qs = qs.annotate(bills=Count('bill'))
    qs = qs.filter(bills__gt=2,
                   is_paid__exact=False,
                   membership__status='A',
                   membership__id__gt=-1)
    qs = qs.exclude(bill__type='P')
    qs = qs.order_by('start')

    return qs

def create_reminder_pdf(cycles, output_file):

    p = pdf.PDFReminder(output_file)
    try:
        for cycle in cycles:
            p.addCycle(cycle)
        p.generate()
        return True
    except RuntimeError as e:
        logger.exception(e)
        print("Failed to generate reminder pdf '%s'" % output_file)
    return False

def create_remainder_list(memberid=None):
    datalist = []
    for cycle in get_reminder_billingcycles(memberid).all():
        # check if paper reminder already sent
        cont = False
        for bill in cycle.bill_set.all():
            if bill.type == 'P':
                cont=True
                break
        if cont:
            continue

        datalist.append(cycle)
    return datalist

def generate_pdf_reminders(memberid=None):
    """
    :param memberid: optional member id
    :return: path to pdf file
    """
    fd, target_file = mkstemp(suffix=".pdf", prefix='sikteeri')
    cycles = create_remainder_list(memberid)
    if len(cycles) == 0:
        raise RuntimeError('No need for remainders')
    return_value = create_reminder_pdf(cycles, target_file)
    if not return_value:
        return None
    return target_file

def get_pdf_reminders(memberid=None):
    """
    :param memberid: optional member id
    :return: pdf content as string
    """
    buffer = StringIO()
    cycles = create_remainder_list(memberid)
    if len(cycles) == 0:
        return None
    return_value = create_reminder_pdf(cycles, buffer)
    if return_value:
        pdf_content = buffer.getvalue()
        buffer.close()
        return pdf_content