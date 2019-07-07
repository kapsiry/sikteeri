# -*- coding: utf-8 -*-

"""
Code to make pdf bills and reminders
"""

from membership.reference_numbers import barcode_4
from membership.utils import group_iban, group_reference

from django.conf import settings

import os
from decimal import Decimal
from datetime import datetime, timedelta


from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128

from email import utils as emailutils

import locale

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..//'))

pdfmetrics.registerFont(TTFont('IstokWeb', os.path.join(settings.FONT_PATH, 'IstokWeb-Regular.ttf')))
pdfmetrics.registerFont(TTFont('IstokWeb-Bold', os.path.join(settings.FONT_PATH, 'IstokWeb-Bold.ttf')))

LOGO = os.path.join(settings.IMG_PATH, 'kapsi-logo.jpg')

# Unit is centimeter from left upper corner of page

# TODO: Unittests for pdf


def get_billing_email():
    return emailutils.parseaddr(settings.BILLING_FROM_EMAIL)[1]


class PDFTemplate(object):
    __type__ = 'invoice'

    def __init__(self, filename, cycle=None):
        """
        :param filename: Filename or file-like object
        :param cycle: optional billingcycle object
        """
        self._dpi = 300.0
        self._scale = float(self._dpi/72.0)
        self.size = (self.scale(A4[0], False), self.scale(A4[1], False))
        self.font_size = 12
        self.font = 'IstokWeb'
        self.marginleft = 1.0 * cm
        self.margintop = 0.0 * cm
        self._filename = filename
        self.data = {}
        self.page_count = 0
        self.reset()
        if cycle:
            self.addCycle(cycle)

    def scale(self, n, fromcm = True):
        if fromcm:
            return float(n) * self._scale * cm
        return float(n) * self._scale

    def reset(self):
        self.c = canvas.Canvas(self._filename, pagesize=A4,
                               bottomup=1)

    def addCycle(self, cycle, payments=None):
        self.c.scale(72.0/self._dpi, 72.0/self._dpi)
        self.createData(cycle, payments=payments)
        self.addTemplate()
        self.addContent()
        self.c.showPage()
        self.page_count += 1

    def addBill(self, bill, payments=None):
        self.c.scale(72.0/self._dpi, 72.0/self._dpi)
        self.createData(cycle=bill.billingcycle, bill=bill, payments=payments)
        self.addTemplate()
        self.addContent()
        self.c.showPage()
        self.page_count += 1

    def addCycles(self, cycles, payments=None):
        for cycle in cycles:
            self.addCycle(cycle, payments=payments)

    def real_y(self, y):
        y = self.scale(y)
        y = (self.size[1] - float(y))
        return y

    def real_x(self, x):
        x = self.scale(x)
        return ((x) + self.marginleft)

    def drawImage(self, x, y, width, height, image):
        x = self.real_x(float(x))
        y = self.real_y(float(y))
        width = self.scale(width)
        height = self.scale(height)
        self.c.drawImage(image, x, (y - height), width, height)

    def drawVerticalStroke(self, startx, starty, length,
                             r=0.0, g=0.0, b=0.0, width=1):
        self.c.setStrokeColorRGB(r,g,b)
        self.c.setLineWidth(width)
        starty = self.real_y(starty)
        startx = self.real_x(startx)
        length = self.scale(length)
        self.c.line(startx,starty,startx, starty + length)

    def drawHorizontalStroke(self, startx, starty, length,
                             r=0.0, g=0.0, b=0.0, width=1):
        self.c.setStrokeColorRGB(r,g,b)
        self.c.setLineWidth(width)
        starty = self.real_y(starty)
        startx = self.real_x(startx)
        length = self.scale(length)
        self.c.line(startx,starty,startx + length,starty)

    def drawString(self, x, y, line, font=None, size=None, alignment="left", flip=False):
        if font is None:
            font = self.font
        if size is None:
            size = self.font_size
        size = self.scale(size, False)
        if line.startswith('<b>') and line.endswith("</b>"):
            line = self._strip_format(line)
            self.c.setFont("%s-Bold" % font, size)
        else:
            self.c.setFont(font, size)
        if flip:
            self.c.rotate(90)
            y = -1 * self.scale(y)
        else:
            y = self.real_y(y)
        x = self.real_x(x)
        if alignment == 'left':
            self.c.drawString(x, y, line)
        elif alignment == 'center':
            self.c.drawCentredString(x , y, line)
        elif alignment == 'right':
            self.c.drawRightString(x, y, line)
        else:
            raise RuntimeError("Invalid alignment %s" % alignment)
        if flip:
            self.c.rotate(-90)

    def drawBox(self, x, y, width, height, stroke=1):
        width = self.scale(width)
        height = self.scale(height)
        x = self.real_x(x)
        y = (self.real_y(y) - height)
        self.c.rect(x, y, width, height, fill=0, stroke=stroke)

    def _strip_format(self, line):
        if line.startswith('<b>'):
            line = line[3:-4]
        return line

    def _add_text(self, line, textobject, font, size):
        if line.startswith('<b>') and line.endswith("</b>"):
            line = self._strip_format(line)
            textobject.setFont("%s-Bold" % font, size)
        textobject.textLine(line)
        textobject.setFont(font, size)

    def drawTable(self, x, y, data, font=None, size=None):
        if font is None:
            font = self.font
        if size is None:
            size = self.font_size
        x = self.real_x(x)
        y = self.real_y(y)
        size = self.scale(size, False)
        keytextobject = self.c.beginText()
        valuetextobject = self.c.beginText()
        keytextobject.setFont(font, size)
        valuetextobject.setFont(font, size)
        longest_key = 0
        for key, value in data:
            if len(self._strip_format(key)) > longest_key:
                longest_key = len(self._strip_format(key))
        keytextobject.setTextOrigin(x, y)
        valuetextobject.setTextOrigin(x + (longest_key*size)/1.8 + 10, y)
        for key, value in data:
            self._add_text(key, keytextobject, font, size)
            self._add_text(value, valuetextobject, font, size)
        self.c.drawText(keytextobject)
        self.c.drawText(valuetextobject)


    def drawText(self, x, y, text, font=None, size=None):
        if font is None:
            font = self.font
        if size is None:
            size = self.font_size
        size = self.scale(size, False)
        textobject = self.c.beginText()
        textobject.setFont(font, size)
        y = self.real_y(y)
        x = self.real_x(x)
        textobject.setTextOrigin(x, y)
        textobject.setTextRenderMode(0)
        for line in text.splitlines():
            self._add_text(line, textobject, font, size)
        self.c.drawText(textobject)

    def createData(self, cycle, bill=None, payments=None):
        # TODO: use Django SHORT_DATE_FORMAT
        membercontact = cycle.membership.get_billing_contact()

        # Calculate vat; copied from models.Bill#render_as_text(self)
        vat = Decimal(cycle.get_vat_percentage()) / Decimal(100)
        if self.__type__ == 'reminder':
            amount_paid = cycle.amount_paid()
            sum = cycle.sum - amount_paid
            non_vat_amount = sum / (Decimal(1) + vat)
        else:
            sum = cycle.sum
            non_vat_amount = (cycle.sum / (Decimal(1) + vat))

        # Select due date
        if self.__type__ == 'reminder':
            due_date = "HETI"
        elif bill:
            due_date = bill.due_date.strftime("%d.%m.%Y")
        else:
            due_date = datetime.now() + timedelta(days=settings.BILL_DAYS_TO_DUE)
            due_date = due_date.strftime("%d.%m.%Y")

        lineitems = []
        # ['1', 'Jäsenmaksu', '04.05.2010 - 04.05.2011', '32.74 €','7.26 €','40.00 €']
        cycle_start_date = cycle.start.strftime('%d.%m.%Y')
        cycle_end_date = cycle.end_date().strftime('%d.%m.%Y')
        lineitems.append(["1",
                      "Jäsenmaksu",
                      "%s - %s" % (cycle_start_date, cycle_end_date),
                      "%s €" % locale.format("%.2f", cycle.sum / (Decimal(1) + vat)),
                      "%s %%" % locale.format("%d", cycle.get_vat_percentage()),
                      "%s €" % locale.format("%.2f", vat * non_vat_amount),
                      "%s €" % locale.format("%.2f", cycle.sum)])
        # Note any payments attached
        if self.__type__ == 'reminder' and amount_paid > 0:
            lineitems.append([
                "2",
                "Maksuja huomioitu yht.",
                "",  # start-end
                "",  # amount
                "",  # vat-percentage
                "",  # vat amount
                "%s €" % locale.format("%.2f", -amount_paid),  # total amount
                ])

        first_bill = cycle.first_bill()
        if bill:
            bill_id = bill.id
        elif first_bill:
            bill_id = first_bill.id
        else:
            bill_id = None
        if bill:
            date = bill.created
        else:
            date = datetime.now()
        if payments:
            latest_payment_date = payments.latest_payment_date()
            if latest_payment_date:
                latest_payments = min([payments.latest_payment_date(), datetime.now()])
            else:
                latest_payments = datetime(year=2003,month=1, day=1)
        else:
            latest_payments = datetime.now()
        self.data = {'name': cycle.membership.name(),
                'address': membercontact.street_address,
                'postal_code':membercontact.postal_code,
                'postal_office':membercontact.post_office,
                'date': date.strftime("%d.%m.%Y"),
                'latest_payment_date': latest_payments.strftime('%d.%m.%Y'),
                'member_id': cycle.membership.id,
                'due_date': due_date,
                'email': membercontact.email,
                'bill_id': bill_id,
                'vat': vat,
                'sum': sum,
                'pretty_sum': locale.format('%.2f', sum),
                'notify_period': '%d vrk' % (settings.REMINDER_GRACE_DAYS,),
                'lineitems': lineitems,
                'reference_number': group_reference(cycle.reference_number)
        }

    def addTemplate(self):
        # Logo to upper left corner
        self.drawImage(0.2, 0, 5, 2.5, LOGO)
        self.drawString(10.5, 3, "%(date)s" % self.data, alignment="center", size=12)
        self.drawString(1.5, 3, "Kapsi Internet-käyttäjät ry, PL 11, 90571 OULU",
                      size=8)
        # Address block
        self.drawText(1.5, 4, "%(name)s\n%(address)s\n%(postal_code)s %(postal_office)s" % self.data, size=12)
        #self.drawHorizontalStroke()

        self.drawBox(14.5, 3.5, 5, 1.7)
        self.drawTable(14.7, 4, [['Jäsennumero:', '%(member_id)s' % self.data],
                              ['Eräpäivä:', '%(due_date)s' % self.data],
                              ['Huomautusaika:','%(notify_period)s' % self.data]
                              ], size=10)

        xtable = [1,1.5,7,12,13.5,15,17]
        self.drawString(xtable[1],6.5, "Selite", size=9)
        self.drawString(xtable[2],6.5, "Aikaväli", size=9)
        self.drawString(xtable[3],6.5, "ilman alv", size=9)
        self.drawString(xtable[4],6.5, "alv", size=9)
        self.drawString(xtable[5],6.5, "alv osuus", size=9)
        self.drawString(xtable[6],6.5, "Yhteensä", size=9)
        self.drawHorizontalStroke(1,6.6, 18.5)

        y = 7
        for line in self.data['lineitems']:
            for i in range(len(xtable)):
                self.drawString(xtable[i],y, line[i], size=10)
            y += 0.4

        y -= 0.3
        self.drawHorizontalStroke(1,y, 18.5)
        y += 0.4
        self.drawString(xtable[3],y, "Maksettavaa yhteensä:" % self.data, size=10)
        self.drawString(xtable[6],y, "<b>%(pretty_sum)s €</b>" % self.data, size=10)



        self.drawHorizontalStroke(1,18, 18.5)

        self.drawText(1,18.5, "<b>Kapsi Internet-käyttäjät ry</b>\nPL 11\n90571 Oulu", size=7)
        self.drawText(5.5,18.5, "Kotipaikka Oulu\nhttps://www.kapsi.fi/", size=7)
        self.drawText(9.5,18.5, "Sähköposti: %s\nY-tunnus: %s\nYhdistysrekisterinumero: %s" % (get_billing_email(),
            settings.BUSINESS_ID, settings.ORGANIZATION_REG_ID), size=7)
        self.drawText(14,18.5, "Tilinumero: %s\nBIC: %s" % (group_iban(settings.IBAN_ACCOUNT_NUMBER),
                                                            settings.BIC_CODE), size=7)

        # Bill part

        self.drawString(2.3, 20, "Saajan", size=6, alignment="right")
        self.drawString(2.3, 20.2, "tilinumero", size=6, alignment="right")
        self.drawString(2.3, 20.5, "Mottagarens", size=6, alignment="right")
        self.drawString(2.3, 20.7, "kontonummer", size=6, alignment="right")

        self.drawText(3.0, 20.6, "%s   %s   %s" % (settings.BANK_NAME, group_iban(settings.IBAN_ACCOUNT_NUMBER),
                                                   settings.BIC_CODE), size=9)


        self.drawString(2.3, 21.7, "Saaja", size=6, alignment="right")
        self.drawString(2.3, 22.0, "Mottagaren", size=6, alignment="right")

        self.drawText(3.0, 21.5, "Kapsi Internet-käyttäjät ry\nPL 11\n90571 Oulu", size=9)

        self.drawString(2.4, 23, "Maksajan", size=6, alignment="right")
        self.drawString(2.4, 23.2, "nimi ja", size=6, alignment="right")
        self.drawString(2.4, 23.4, "osoite", size=6, alignment="right")
        self.drawString(2.4, 23.7, "Betalarens", size=6, alignment="right")
        self.drawString(2.4, 23.9, "namn och", size=6, alignment="right")
        self.drawString(2.4, 24.1, "adress", size=6, alignment="right")

        self.drawText(3.0, 23.5, "%(name)s\n%(address)s\n%(postal_code)s %(postal_office)s\n%(email)s" % self.data, size=9)


        self.drawString(2.4, 25.6, "Allekirjoitus", size=6, alignment="right")
        #self.drawString(2.3, 25.6, u"", size=6, alignment="right")
        self.drawString(2.4, 25.9, "Ynderskrift", size=6, alignment="right")

        self.drawString(2.3, 26.5, "Tililtä", size=6, alignment="right")
        self.drawString(2.3, 26.75, "Från konto nr", size=6, alignment="right")

        self.drawString(3.75, 1.4, "<b>TILISIIRTO GIRERING</b>", size=8, flip=True)

        self.drawText(3.0,20, "IBAN", size=7)

        self.drawText(11.15,25.6, "Viitenro\nRef.nr", size=7)
        self.drawText(13.15,25.7, "%(reference_number)s" % self.data, size=9)
        self.drawText(11.15,26.5, "Eräpäivä\nFörf.dag", size=7)
        self.drawText(13.15,26.65, "%(due_date)s" % self.data, size=9)
        self.drawText(15.9,26.4, "Euro", size=7)
        self.drawText(16.9,26.65, "%(pretty_sum)s" % self.data, size=9)




        # Lines on bottom part
        self.drawHorizontalStroke(1,21, 10, width=6)
        self.drawHorizontalStroke(1,22.5, 10, width=6)
        self.drawVerticalStroke(2.5,22.5, 2.8, width=6)
        self.drawVerticalStroke(11,27, 7.3, width=6)
        self.drawVerticalStroke(2.5,27, 0.9, width=6)
        self.drawHorizontalStroke(11,25.2, 8.5, width=6)
        self.drawHorizontalStroke(1,26.1, 18.5, width=6)
        self.drawHorizontalStroke(3,25.8, 7.5, width=2)
        self.drawVerticalStroke(12.3,27, 1.8, width=6)
        self.drawVerticalStroke(15.8,27, 0.9, width=6)
        self.drawHorizontalStroke(1,27, 18.5, width=6)

        self.drawText(14, 27.6, "Maksu välitetään saajalle vain Suomessa Kotimaan maksujenvälityksen\nyleisten ehtojen mukaisesti ja vain maksajan ilmoittaman tilinumeron\nperusteella.", size=5)
        self.drawText(14, 28.3, "Betalningen förmedlas till mottagare endast i Finland enligt Allmänna\nvillkor för inrikes betalningsförmedling och endast till det\nkontonummer betalaren angivit.", size=5)
        self.drawText(17.8, 29.1, "PANKKI BANKEN", size=6)

        due_date = None
        if self.__type__ != 'reminder':
            due_date = datetime.now() + timedelta(days=settings.BILL_DAYS_TO_DUE)
        barcode_string = barcode_4(settings.IBAN_ACCOUNT_NUMBER, self.data['reference_number'], due_date, self.data['sum'])
        barcode = code128.Code128(str(barcode_string), barWidth=0.12*cm, barHeight=4.5*cm)
        barcode.drawOn(self.c, self.real_x(2), self.real_y(28.7))

    def addContent(self):
        pass

    def generate(self):
        self.c.save()


class PDFReminder(PDFTemplate):
    __type__ = 'reminder'
    def addContent(self):
        self.drawString(10.5, 2, "<b>MUISTUTUS</b>", alignment="center")
        self.drawText(1, 10, """Hei!

Tämä on muistutus puuttuvasta jäsenmaksusuorituksesta. Alkuperäinen lasku on lähetetty ainoastaan sähköpostitse.
Mikäli et ole saanut sitä, tarkistathan että sähköpostiosoitteesi on oikein jäsenrekisterissä (listattu maksajan tiedoissa
alla).

Voit ottaa yhteyttä Kapsin laskutukseen osoitteeseen %s esimerkiksi seuraavissa tilanteissa:
- jos tämä lasku on mielestäsi virheellinen
- haluat erota yhdistyksestä
- haluat muuttaa yhteystietojasi
- haluat sopia maksuaikataulusta
- sinulla on muuta kysyttävää jäsenasioista.
""" % (get_billing_email(),), size=10)

        self.drawText(1,16, "<b>Muistutuksen maksamatta jättäminen johtaa jäsenpalveluiden lukitsemiseen ja erottamiseen yhdistyksestä!</b>", size=10)
        self.drawText(1,17, "Jos olet jo maksanut muistutuksen, tämä viesti on aiheeton. Olemme huomioineet meille näkyvät jäsenmaksu-\nsuoritukset %(latest_payment_date)s asti." % self.data, size=10)
        if self.data['bill_id']:
            self.drawText(11.5,23.4, "Muistutus laskulle numero %s" % self.data['bill_id'], size=10)

class PDFInvoice(PDFTemplate):
    __type__ = 'invoice'
    def addContent(self):
        self.drawString(10.5, 2, "<b>LASKU</b>", alignment="center")
        self.drawText(1, 10, """
Voit ottaa yhteyttä Kapsin laskutukseen osoitteeseen %s esimerkiksi seuraavissa tilanteissa:
   - tämä lasku on sinusta virheellinen
   - haluat erota yhdistyksestä
   - haluat muuttaa yhteystietojasi
   - haluat sopia maksuaikataulusta
   - sinulla on muuta kysyttävää jäsenasioista
""" % (get_billing_email(),), size=10)
        if self.data['bill_id']:
            self.drawText(11.5,23.4, "Laskunumero %s" % self.data['bill_id'], size=10)
