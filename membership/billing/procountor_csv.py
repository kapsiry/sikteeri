# encoding: UTF-8
from __future__ import unicode_literals
import csv
import logging
from datetime import datetime, timedelta
from StringIO import StringIO
from decimal import Decimal

from django.conf import settings
from membership.models import Bill, CancelledBill

logger = logging.getLogger("membership.billing.procountor")


def finnish_timeformat(t):
    return t.strftime("%d.%m.%Y")


ft = finnish_timeformat


def _bill_to_rows(bill, cancel=False):
    """Map bills to Procountor CSV format

    http://support.procountor.com/fi/aineiston-sisaanluku/laskuaineiston-siirtotiedosto.html
    """
    rows = []
    c = bill.billingcycle
    if c.membership.type in ['H']:
        return rows
    rows.append([
        'M',  # laskutyyppi
        'EUR',  # valuuttakoodi
        c.reference_number,  # viitenumero
        settings.IBAN_ACCOUNT_NUMBER,  # pankkitili
        '',  # Y-tunnus/HETU/ALV-tunnus
        'tilisiirto',  # Maksutapa
        c.membership.name(),  # Liikekumppanin nimi
        '',  # Toimitustapa
        '0',  # Laskun alennus %
        't',  # Sis. alv koodi
        'f' if cancel else 't',  # Hyvityslaskukoodi
        '0.0',  # Viivästyskorko %
        ft(bill.created),  # Laskun päivä
        ft(bill.created),  # Toimituspäivämäärä
        ft(bill.created + timedelta(days=settings.BILL_DAYS_TO_DUE)),  # Eräpäivämäärä
        '',  # Liikekumppanin osoite
        '%s\%s\%s\%s\%s' % (c.membership.name(),
                            c.membership.get_billing_contact().street_address,
                            c.membership.get_billing_contact().postal_code,
                            c.membership.get_billing_contact().post_office,
                            'FI'),  # Laskutusosoite
        '',  # Toimitusosoite
        '',  # Laskun lisätiedot
        'Lasku %d sikteerissä, tuotu %s, jäsen %d' % (bill.id, ft(datetime.now()), c.membership.id),  # Muistiinpanto
        c.membership.get_billing_contact().email,  # Sähköpostiosoite
        '',  # Maksupäivämäärä
        '',  # Valuuttakurssi
        "%.2f" % Decimal.copy_negate(c.get_fee()) if cancel else c.get_fee(),  # Laskun loppusumma
        "%d" % c.get_vat_percentage(),  # ALV-%
        '6',  # Laskukanava
        '',  # Verkkolaskutunnus
        '%d' % bill.id,  # Tilausviite
        't',  # Kirjanpito riveittäin -koodi)
        '',  # Finvoice-osoite 1(ei enää käytössä)
        '',  # Finvoice-osoite 2(ei enää käytössä)
        '%d' % c.membership.id,  # Asiakasnumero
        'X',  # Automaattinen lähetys tai maksettu muualla tieto
        '',  # Liitetiedoston nimi ZIP-paketissa
        '',  # Yhteyshenkilö
        '',  # Liikekumppanin pankin SWIFT-tunnus
        '',  # Verkkolaskuoperaattori
        '',  # Liikekumppanin OVT-tunnus
        "%s" % bill.id,  # Laskuttajan laskunumero
        '',  # Faktoring-rahoitussopimuksen numero
        '',  # ALV-käsittelyn maakoodi
        '',  # Kielikoodi
        '0',  # Käteisalennuksen päivien lukumäärä
        '0'  # Käteisalennuksen prosentti
    ])
    member_type = settings.BILLING_ACCOUNTING_MAP[c.membership.type]
    r2 = ['',  # TYHJÄ
          '',  # Tuotteen kuvaus
          '%s%s' % (member_type[0], c.start.strftime("%y")),  # Tuotteen koodi
          '-1' if cancel else '1',  # Määrä
          '',  # Yksikkö
          '%.2f' % c.get_fee(),  # Yksikköhinta
          '0',  # Rivin alennusprosentti
          "%d" % c.get_vat_percentage(),  # Rivin ALV-%
          '',  # Rivikommentti
          '',  # Tilausviite
          '',  # Asiakkaan ostotilausnumero
          '',  # Tilausvahvistusnumero
          '',  # Lähetysluettelonumero
          '%s' % member_type[1]  # Kirjanpitotili
          ]
    r2 += [''] * (len(rows[0]) - len(r2))
    rows.append(r2)
    return rows


def create_csv(start=None, mark_cancelled=True):
    """
    Create procountor bill export csv
    :return: path to csv file
    """

    if start is None:
        start = datetime.now()
        start = datetime(year=start.year, month=start.month(), day=1)

    filehandle = StringIO()
    output = csv.writer(filehandle, delimiter=b';', quoting=csv.QUOTE_NONE)

    for bill in Bill.objects.filter(created__gte=start, reminder_count=0).all():
        for row in _bill_to_rows(bill):
            row2 = []
            for v in row:
                if type(v) == unicode:
                    row2.append(v.encode("iso-8859-1"))
                else:
                    row2.append(v)
            output.writerow(row2)

    cancelled_bills = CancelledBill.objects.filter(exported=False)
    for cb in cancelled_bills:
        for row in _bill_to_rows(cb.bill, cancel=True):
            row2 = []
            for v in row:
                if type(v) == unicode:
                    row2.append(v.encode("iso-8859-1"))
                else:
                    row2.append(v)
            output.writerow(row2)
    if mark_cancelled:
        cancelled_bills.update(exported=True)
        logger.info("Marked all cancelled bills as exported.")

    return filehandle.getvalue()
