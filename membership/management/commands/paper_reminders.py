# encoding: UTF-8
from __future__ import with_statement

import os
import signal
import logging

from threading import currentThread
from subprocess import Popen

from datetime import datetime, timedelta
from decimal import Decimal
from string import Template
from optparse import make_option
from tempfile import mkdtemp

from django.db.models import Count
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _
from django.conf import settings

from membership.models import BillingCycle
from membership.utils import log_change
from membership.reference_numbers import barcode_4

logger = logging.getLogger("paper_bills")
TMPDIR = mkdtemp('sikteeritex')

class LatexTemplate(Template):
    delimiter = '\$'

class Timeout(Exception):
    pass

def timeout_handler(signum, frame):
    raise Timeout

def get_data(memberid=None):
    # TODO: refactor central parts into classmethod BillingCycle.paper_reminders
    # TODO: rename (data is never a good name for anything)
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

def tex_sanitize(input_string):
    return input_string.replace("#","\#").replace("$", "\$")

def prettyname(cycle):
    # TODO: use translations
    return u"%d & Jäsenmaksu kaudelle & %s - %s & %s \\\\\n" % (1,
                    cycle.start.strftime('%d.%m.%Y'),
                    cycle.end.strftime('%d.%m.%Y'), cycle.sum)

def data2pdf(data):
    # TODO: use Django templates, use with-statement
    t = LatexTemplate(open(settings.PAPER_REMINDER_TEMPLATE).read().decode("UTF-8"))
    targetfile = "m_%d.tex" % int(data['JASENNRO'])
    targetfile = os.path.join(TMPDIR, targetfile)
    target = open(targetfile, 'w')
    target.write(t.safe_substitute(data).encode("UTF-8"))
    target.close()

    try:
        return generate_pdf(targetfile)
    except RuntimeError as e:
        logger.exception(e)
        print("Failed to generate pdf for member %d" % int(data['JASENNRO']))
        print("Data was %s" % data)
    return None

def create_datalist(memberid=None):
    # TODO: template variable names in English
    # TODO: use Django SHORT_DATE_FORMAT
    # TODO: do LaTeX-specific escaping utilities belong into an application-wide latex_utils.py?
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

        membercontact = cycle.membership.get_billing_contact()
        full = Decimal(100)
        vat = (cycle.sum * (cycle.get_vat_percentage() / full))
        amount = cycle.sum - vat
        data = {
            'DATE'      : datetime.now().strftime("%d.%m.%Y"),
            'JASENNRO'  : cycle.membership.id,
            'NIMI'      : tex_sanitize(cycle.membership.name()),
            'AMOUNT'    : "%.2f" % amount,
            'SUM'       : "%.2f" % cycle.sum,
            'VAT'       : "%.2f" % vat,
            'VIITENRO'  : cycle.reference_number,
            'MAKSUDATA' : prettyname(cycle),
            'EMAIL'     : tex_sanitize(membercontact.email.replace("_", "\_")),
            'OSOITE'    : tex_sanitize(membercontact.street_address),
            'POSTI'     : tex_sanitize("%s %s" % (membercontact.postal_code, membercontact.post_office)),
            'BARCODE'   : barcode_4(settings.IBAN_ACCOUNT_NUMBER,cycle.reference_number,None,cycle.sum)
        }
        datalist.append(data)
    return datalist

def generate_pdf(latexfile):
    # TODO: with_timeouting_process(...)
    # set umask to 0077
    oldumask = os.umask(63)
    penv = os.environ.copy()
    pid = Popen(['pdflatex', '-interaction=batchmode', '-output-directory=%s' % TMPDIR, 
        '-no-file-line-error','-halt-on-error','-output-format','pdf',latexfile],
        env=penv, cwd=os.path.dirname(os.path.realpath(settings.PAPER_REMINDER_TEMPLATE)))
    # wait until process ends
    pid.wait()
    try:
        os.remove(latexfile)
    except OSError as e:
        logging.exception(e)
    if pid.returncode != 0:
        logging.error('Error processing %s: pdflatex returncode was %s' % (latexfile, pid.returncode))
        raise RuntimeError('Error processing %s: pdflatex returncode was %s' % (latexfile, pid.returncode))
        return None
    # Restore previous umask
    os.umask(oldumask)
    pdffile = latexfile.replace('.tex','.pdf')
    if os.path.exists(pdffile):
        return pdffile
    else:
        return None

def generate_reminders(memberid=None):
    # TODO: use the tempfile library http://docs.python.org/2/library/tempfile.html
    # TODO: refactor LaTeX-specific things into a latex_utils.py
    # TODO: use Django templates
    if not os.path.isdir(TMPDIR) and not os.path.exists(TMPDIR):
        os.mkdir(TMPDIR)
    elif os.path.exists(TMPDIR) and not os.path.isdir(TMPDIR):
        logging.error('Cannot create tmpdir %s, file exist' % TMPDIR)
        return
    
    filelist = []
    for data in create_datalist(memberid):
        output = data2pdf(data)
        if output != None:
            filelist.append(output)
    if len(filelist) == 0:
        raise RuntimeError('No need for remainders')
    single_latex = "\\documentclass[a4paper,10pt]{letter}\n"
    single_latex += "\\usepackage{pdfpages}\n"
    single_latex += "\\begin{document}\n"
    for filename in filelist:
        single_latex += "\includepdf[pages=-]{%s}\n" % filename
    single_latex += "\\end{document}\n"
    if memberid:
        singlefile = os.path.join(TMPDIR, 'reminders_%s.tex' % memberid)
    else:
        singlefile = os.path.join(TMPDIR, 'reminders.tex')
    f = open(singlefile, 'w')
    f.write(single_latex)
    f.close()
    singlefile = generate_pdf(singlefile)
    # cleanup
    for filename in os.listdir(TMPDIR):
        filename = os.path.join(TMPDIR, filename)
        if filename.endswith(singlefile):
            continue
        if 'reminder' in filename and '.pdf' in filename:
            continue
        try:
            os.remove(filename)
        except OSError as e:
            logging.exception(e)
    if not singlefile:
        return None
    return singlefile

def get_reminders(memberid=None):
    # TODO: don't do signals, don't do threads
    # TODO: call with Popen, wait in our own while loop with a counter
    # TODO: use with-statement for reading files
    if currentThread().getName() == 'MainThread':
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(28)  # 28 sec
    else:
        logging.error("Cannot use signals on child thread")
    try:
        singlefile = generate_reminders(memberid)
        signal.alarm(0)
    except Timeout:
        return
    if singlefile:
        f = open(singlefile, 'r')
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
