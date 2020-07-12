# encoding: utf-8
import argparse
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management import BaseCommand

from membership.billing.procountor_api import ProcountorAPIClient
from membership.billing.payments import process_payments


def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


class Command(BaseCommand):
    help = 'Import payments from Procountor'

    def add_arguments(self, parser):
        parser.add_argument('-s', "--startdate", help="Start Date (YYYY-MM-DD)",
                            default=None, type=valid_date)

    def handle(self, *args, **options):
        start = options['startdate'] or datetime.now() - timedelta(days=1)

        api = ProcountorAPIClient(api=settings.PROCOUNTOR_API_URL,
                                  company_id=settings.PROCOUNTOR_COMPANY_ID,
                                  redirect_uri=settings.PROCOUNTOR_REDIRECT_URL,
                                  client_id=settings.PROCOUNTOR_CLIENT_ID,
                                  client_secret=settings.PROCOUNTOR_CLIENT_SECRET)
        api.authenticate(username=settings.PROCOUNTOR_USER,
                         password=settings.PROCOUNTOR_PASSWORD)

        statements = api.get_referencepayments(start=start, end=datetime.now())
        for message in process_payments(statements):
            print(message)

        bankstatements = api.get_bankstatements(start=start, end=datetime.now())
        for bankstatement in bankstatements:
            for message in process_payments(
                    [x for x in bankstatement.events if x["explanationCode"] in [700, 710]]):
                print(message)
