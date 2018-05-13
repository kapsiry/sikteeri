# encoding: UTF-8
from __future__ import with_statement

import logging
from tempfile import NamedTemporaryFile

from django.core.management.base import BaseCommand, CommandError
from membership.models import BillingCycle

logger = logging.getLogger("paper_bills")


class Command(BaseCommand):
    help = 'Create paper reminders pdf'

    def add_arguments(self, parser):
        parser.add_argument('--member',
            dest='member',
            default=None,
            help='Create pdf-reminder for user')

    def handle(self, *args, **options):
        try:
            with NamedTemporaryFile(suffix=".pdf", prefix='sikteeri', delete=False) as target_file:

                pdfcontent = BillingCycle.get_pdf_reminders(memberid=options['member'])
                target_file.write(pdfcontent)
                target_file.close()
                pdffile = target_file.name

            if pdffile:
                print("pdf file created: %s" % pdffile)
            else:
                print("Cannot create pdffile")
        except RuntimeError as e:
            raise CommandError(e)
