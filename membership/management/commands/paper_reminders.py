# encoding: UTF-8
from __future__ import with_statement

import logging
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from membership.billing import pdf_utils

logger = logging.getLogger("paper_bills")

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
            pdffile = pdf_utils.generate_pdf_reminders(memberid=options['member'])
            if pdffile:
                print "pdf file created: %s" % pdffile
            else:
                print "Cannot create pdffile"
        except RuntimeError as e:
            raise CommandError(e)
