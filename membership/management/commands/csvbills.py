# encoding: UTF-8


import logging
import os


from django.core.management.base import BaseCommand

from membership.billing.payments import process_op_csv, process_procountor_csv

logger = logging.getLogger("membership.csvbills")


class Command(BaseCommand):

    help = 'Read a CSV list of payment transactions'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('csvfiles', nargs='+')

        # Named (optional) arguments
        parser.add_argument(
            '--procountor',
            dest='procountor',
            default=None,
            action="store_true",
            help='Use procountor import csv format')

    def handle(self, csvfiles, *args, **options):
        for csvfile in csvfiles:
            logger.info("Starting the processing of file %s." %
                os.path.abspath(csvfile))
            # Exceptions of process_csv are fatal in command line run
            with open(csvfile, 'r', encoding='ISO-8859-1') as file_handle:
                if options['procountor']:
                    process_procountor_csv(file_handle)
                else:
                    process_op_csv(file_handle)
            logger.info("Done processing file %s." % os.path.abspath(csvfile))
