"""
Generates test data for CSV import.
"""
import codecs

from uuid import uuid4
from datetime import datetime, timedelta
from sys import stdout

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from membership.models import *

header_row = u'''Kirjauspäivä;Arvopäivä;Määrä EUROA;Tapahtumalajikoodi;Selitys;Saaja/Maksaja;Saajan tilinumero;Viite;Viesti;Arkistotunnus;'''

row = u'''{0[date]};{0[date]};{0[sum]};106;TILISIIRTO;{0[payer]};{0[account]};{0[reference]};{0[message]};{0[id]};'''

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
    args = '<file_to_write_to>'
    help = 'Generate payments CSV to be used for testing out payment import' \
        + ' form'

    def handle(self, *args, **options):
        if len(args) > 0:
            with codecs.open(args[0], 'w', encoding='iso-8859-1') as f:
                if len(args) > 1:
                    print_csv(stream=f, count=int(args[1]))
                else:
                    print_csv(stream=f)
        else:
            print_csv()


'''Kirjauspäivä;Arvopäivä;Määrä EUROA;Tapahtumalajikoodi;Selitys;Saaja/Maksaja;Saajan tilinumero;Viite;Viesti;Arkistotunnus;
21.05.2008;21.05.2008;-66,50;106;TILISIIRTO;MATTI MEIKÄLÄINEN;211135-00302106;;VUOSIKOKOUKSEN JA YLLÄPITOMATKAN MATKAKORVAUKSET. HALKO 3/2008.                                                                                                                ;20080521593497O10031;
03.08.2008;03.08.2008;-33,00;106;TILISIIRTO;MATTI MEIKÄLÄINEN;211135-00302106;;POSTIKULUKORVAUS                   LASKUTETTU POSTIKULUSTA. HYVÄKSYTTYHALKOSSA 07/2008 24.7.2008.                                                                              ;20080803593497AK0018;
27.01.2009;27.01.2009;30,00;588;VIITESIIRTO;MEIKÄLÄINEN MATTI JOHANNES;;00000000000007009017;                                                                                                                                                                               ;200901252588NGNO0290;
21.01.2010;21.01.2010;-1063,35;106;TILISIIRTO;MATTI MEIKÄLÄINEN;211135-00302106;;HALKO 3/2010                       KEVÄTKICKOFF TARVIKKEITA. KUPLAMUOVIA XOBIIN                                                                                     ;20100121593497690187;
21.01.2010;21.01.2010;-73,10;106;TILISIIRTO;MATTI MEIKÄLÄINEN;211135-00302106;;HALKO 3/2010                       SIKTEERIVIIKONLOPUN MATKOJA.                                                                                                                ;201001215934979N0174;
25.01.2010;25.01.2010;30,00;588;VIITESIIRTO;MEIKÄLÄINEN MATTI JOHANNES;;00000000000001110012;SEPA-MAKSU                         SAAJA/MOTTAG./BEN: Kapsi Internet-kKULUKOODI: SLEV                    ALKUP.MÄÄRÄ EUR              30.00+            EUR              30.00+;201001255UTZ00002150;
21.04.2010;21.04.2010;20,00;588;VIITESIIRTO;MEIKÄLÄINEN MATTI JOHANNES;;00000000000000032094;                                                                                                                                                                               ;201004202588NGN52047;

'''
