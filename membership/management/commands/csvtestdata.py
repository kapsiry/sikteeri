# encoding: UTF-8
"""
Generates test data for CSV import.
"""

import codecs
from datetime import timedelta, datetime

from uuid import uuid4
from sys import stdout

from django.core.management.base import BaseCommand
from django.conf import settings

from membership.models import BillingCycle

header_row = "Kirjauspäivä;Arvopäivä;Määrä EUROA;Tapahtumalajikoodi;Selitys;Saaja/Maksaja;Saajan tilinumero;Viite;" \
             "Viesti;Arkistotunnus;"

row = "{0[date]};{0[date]};{0[sum]};106;TILISIIRTO;{0[payer]};{0[account]};{0[reference]};{0[message]};{0[id]};"


def dict_for_cycle(cycle):
    payment_date = cycle.last_bill().due_date - timedelta(days=1)
    if payment_date > datetime.now():
        payment_date = datetime.now()

    return {
        'date': payment_date.strftime('%d.%m.%Y'),
        'sum': cycle.sum,
        'payer': cycle.membership.name(),
        'account': settings.IBAN_ACCOUNT_NUMBER,
        'reference': cycle.reference_number,
        'message': "Maksu",
        'id': str(uuid4())
        }


def print_csv(stream=stdout, count=10):
    print(header_row, file=stream)
    short_sum = False
    high_sum = False
    wrong_reference = False

    for cycle in BillingCycle.objects.filter(is_paid=False):
        if count == 0:
            break

        d = dict_for_cycle(cycle)
        if short_sum is False:
            d['sum'] -= 5
            short_sum = True
        elif high_sum is False:
            d['sum'] += 5
            high_sum = True
        elif wrong_reference is False:
            d['reference'] = d['reference'][2:]
            wrong_reference = True

        print(row.format(d), file=stream)
        count -= 1

    paid_cycle = BillingCycle.objects.filter(is_paid=True)[0]
    print(row.format(dict_for_cycle(paid_cycle)), file=stream)


class Command(BaseCommand):
    help = 'Generate payments CSV to be used for testing out payment import' \
        + ' form'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('csvfile')

    def handle(self, *args, **options):
        if len(args) > 0:
            with codecs.open(args[0], 'w', encoding='iso-8859-1') as f:
                if len(args) > 1:
                    print_csv(stream=f, count=int(args[1]))
                else:
                    print_csv(stream=f)
        else:
            print_csv()
