# encoding: UTF-8
from __future__ import with_statement

import os
import logging

from optparse import make_option
from tempfile import mkstemp

from membership import pdf

from django.db.models import Count
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _
from django.conf import settings

from membership.models import BillingCycle

logger = logging.getLogger("paper_bills")


def get_data(memberid=None):
    # TODO: refactor central parts into classmethod BillingCycle.paper_reminders
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

def data2pdf(cycles):
    fd, targetfile = mkstemp(suffix=".pdf", prefix='sikteeri')
    p = pdf.PDFReminder(targetfile)
    try:
        for cycle in cycles:
            p.addCycle(cycle)
        p.generate()
        return targetfile
    except RuntimeError as e:
        logger.exception(e)
        print("Failed to generate pdf for member %d" % int(cycle.membership.id))
    return None

def create_datalist(memberid=None):
    # TODO: use Django SHORT_DATE_FORMAT
    datalist = []
    for cycle in get_data(memberid).all():
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

def generate_pdf(cycle, pdffile):
    # TODO: with_timeouting_process(...)
    # set umask to 0077
    oldumask = os.umask(63)

    pdf.PDFReminder(pdffile, cycle).generate()

    # Restore previous umask
    os.umask(oldumask)
    if os.path.exists(pdffile):
        return pdffile
    else:
        return None

def generate_reminders(memberid=None):
    cycles = create_datalist(memberid)
    if len(cycles) == 0:
        raise RuntimeError('No need for remainders')
    singlefile = data2pdf(cycles)
    if not singlefile:
        return None
    return singlefile

def get_reminders(memberid=None):
    singlefile = generate_reminders(memberid)
    if singlefile:
        f = open(singlefile, 'rb')
        return f.read()

class Command(BaseCommand):
    args = ''
    help = 'Create paper reminders pdf'
    option_list = BaseCommand.option_list + (
        make_option('--member',
            dest='member',
            default=None,
            help='Create pdf-reminder for user'),
        )

    def handle(self, *args, **options):
        try:
            pdffile = generate_reminders(memberid=options['member'])
            if pdffile:
                print "pdf file created: %s" % pdffile
            else:
                print "Cannot create pdffile"
        except RuntimeError as e:
            raise CommandError(e)
