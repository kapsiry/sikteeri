# encoding: UTF-8

from __future__ import with_statement

from django.db.models import Count
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _
from membership.reference_numbers import barcode_4
from django.conf import settings

import os

from optparse import make_option

from datetime import datetime, timedelta
from decimal import Decimal
from string import Template

from subprocess import Popen

import logging
logger = logging.getLogger("paper_bills")

from membership.models import BillingCycle
from membership.utils import log_change

TMPDIR = '/tmp/sikteeritex'

class LatexTemplate(Template):
    delimiter = '\$'

def get_data(memberid=None):
    if not settings.ENABLE_REMINDERS:
        # return empty queryset
        return BillingCycle.objects.filter(id=-1)
    elif memberid:
        print('memberid: %s' % memberid)
        return BillingCycle.objects.filter(membership__id=memberid
                ).exclude(bill__type='P')
    return BillingCycle.objects.annotate(bills=Count('bill')).filter(bills__gt=2,
         is_paid__exact=False,membership__status='A',membership__id__gt=-1
         ).exclude(bill__type='P').order_by('start')

def prettyname(cycle):
    return u"%d & Jäsenmaksu kaudelle & %s - %s \\\\\n" % (1, 
                    cycle.start.strftime('%d.%m.%Y'), cycle.end.strftime('%d.%m.%Y'))
                    
def data2pdf(data):
    t = LatexTemplate(open(settings.PAPER_REMINDER_TEMPLATE).read().decode("UTF-8"))
    targetfile = "m_%d.tex" % int(data['JASENNRO'])
    targetfile = os.path.join(TMPDIR, targetfile)
    target = open(targetfile, 'w')
    target.write(t.safe_substitute(data).encode("UTF-8"))
    target.close()
    return generate_pdf(targetfile)

def create_datalist(memberid=None):
    datalist = []
    for cycle in get_data(memberid).all():
        membercontact = cycle.membership.get_billing_contact()
        data = {
            'DATE'      : datetime.now().strftime("%d.%m.%Y"),
            'JASENNRO'  : cycle.membership.id,
            'NIMI'      : cycle.membership.name(),
            'SUMMA'     : cycle.sum,
            'VIITENRO'  : cycle.reference_number,
            'MAKSUDATA' : prettyname(cycle),
            'EMAIL'     : membercontact.email.replace("_", "\_"),
            'OSOITE'    : membercontact.street_address,
            'POSTI'     : "%s %s" % (membercontact.postal_code, membercontact.post_office),
            'BARCODE'   : barcode_4(settings.IBAN_ACCOUNT_NUMBER,cycle.reference_number,None,cycle.sum)
        }
        datalist.append(data)
    return datalist

def generate_pdf(latexfile):
    # set umask to 0077
    oldumask = os.umask(63)
    pid = Popen(['pdflatex', '-interaction=batchmode', '-output-directory=%s' % TMPDIR, 
                '-no-file-line-error','-halt-on-error','-output-format','pdf',latexfile])
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
    if os.path.exist(pdffile)
        return pdffile
    else:
        return None

def generate_reminders(memberid=None):
    if not settings.PAPER_REMINDER_TEMPLATE or not settings.PAPER_REMINDER_TEMPLATE.endswith('.tex'):
        raise RuntimeError('Cannot create reminders without latex template!')
    elif not os.path.exists(settings.PAPER_REMINDER_TEMPLATE):
        raise RuntimeError('Reminders template file %s does not found' % settings.PAPER_REMINDER_TEMPLATE)
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