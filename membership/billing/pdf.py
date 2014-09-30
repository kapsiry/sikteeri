# -*- coding: utf-8 -*-

"""
Code to make pdf bills and reminders
"""

from membership.reference_numbers import barcode_4
from membership.utils import humanize_string

from django.conf import settings

import os
from decimal import Decimal
from datetime import datetime, timedelta


from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, cm
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table
from reportlab.graphics.barcode import code128

import locale


locale.setlocale(locale.LC_ALL, 'fi_FI')

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..//'))

pdfmetrics.registerFont(TTFont('IstokWeb', os.path.join(PROJECT_PATH, 'media/fonts/IstokWeb-Regular.ttf')))
pdfmetrics.registerFont(TTFont('IstokWeb-Bold', os.path.join(PROJECT_PATH, 'media/fonts/IstokWeb-Bold.ttf')))

LOGO = os.path.join(PROJECT_PATH, 'media/img/kapsi-logo.jpg')

# Unit is centimeter from left upper corner of page

# TODO: use the tempfile library http://docs.python.org/2/library/tempfile.html
# TODO: Unittests for pdf

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
                               bottomup = 1)

    def addCycle(self, cycle):
        self.c.scale(72.0/self._dpi, 72.0/self._dpi)
        self.cycle = cycle
        self.createData()
        self.addTemplate()
        self.addContent()
        self.c.showPage()
        self.page_count += 1

    def addCycles(self, cycles):
        for cycle in cycles:
            self.addCycle(cycle)

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

    def drawString(self, x, y, line, font=None, size=None, aligment="left"):
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
        y = self.real_y(y)
        x = self.real_x(x)
        if aligment == 'left':
            self.c.drawString(x, y, line)
        elif aligment == 'center':
            self.c.drawCentredString(x , y, line)
        elif aligment == 'right':
            self.c.drawRightString(x, y, line)
        else:
            raise RuntimError("Invalid aligment %s" % aligment)

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

    def createData(self):
        # TODO: use Django SHORT_DATE_FORMAT
        membercontact = self.cycle.membership.get_billing_contact()
        # Calculate proper vat percentages
        full = Decimal(100)
        vatp = self.cycle.get_vat_percentage() / full
        vat = (self.cycle.sum / (Decimal(1) + vatp)) * vatp
        amount = self.cycle.sum - vat
        if self.__type__ == 'reminder':
            due_date = "HETI"
        else:
            due_date = datetime.now() + timedelta(days=settings.BILL_DAYS_TO_DUE)
            due_date = due_date.strftime("%d.%m.%Y")
        bills = []
        # ['1', 'Jäsenmaksu', '04.05.2010 - 04.05.2011', '32.74 €','7.26 €','40.00 €']
        bills.append(['1',
                      "Jäsenmaksu",
                      "%s - %s" % (self.cycle.start.strftime('%d.%m.%Y'), self.cycle.end.strftime('%d.%m.%Y')),
                      "%s €" % locale.format("%.2f", amount),
                      "%s €" % locale.format("%.2f", vat),
                      "%s €" % locale.format("%.2f", self.cycle.sum)])
        first_bill = self.cycle.first_bill()
        if first_bill:
            bill_id = first_bill.id
        else:
            bill_id = None
        self.data = {'name': self.cycle.membership.name(),
                'address': membercontact.street_address,
                'postal_code':membercontact.postal_code,
                'postal_office':membercontact.post_office,
                'date': datetime.now().strftime("%d.%m.%Y"),
                'member_id': self.cycle.membership.id,
                'due_date': due_date,
                'email': membercontact.email,
                'bill_id': bill_id,
                'amount': amount,
                'pretty_amount': locale.format('%.2f', amount),
                'vat': vat,
                'sum': self.cycle.sum,
                'pretty_sum': locale.format('%.2f', self.cycle.sum),
                'notify_period': '%d vrk' % (settings.REMINDER_GRACE_DAYS,),
                'bills': bills,
                'reference_number': humanize_string(self.cycle.reference_number)
        }

    def addTemplate(self):
        # Logo to upper left corner
        self.drawImage(0.2, 0, 5, 2.5, LOGO)
        self.drawString(10.5, 3, "%(date)s" % self.data, aligment="center", size=12)
        self.drawString(1.5, 3, "Kapsi Internet-käyttäjät ry, PL 11, 90571 OULU",
                      size=8)
        # Address block
        self.drawText(1.5, 4, "%(name)s\n%(address)s\n%(postal_code)s %(postal_office)s" % self.data, size=12)
        #self.drawHorizontalStroke()

        self.drawBox(14.5, 3.5, 5, 1.7)
        self.drawTable(14.9, 4, [['Jäsennumero:', '%(member_id)s' % self.data],
                              ['Eräpäivä:', '%(due_date)s' % self.data],
                              ['Huomautusaika:','%(notify_period)s' % self.data]
                              ], size=10)

        xtable = [1,1.5,7,13,15,17]
        #self.drawString(xtable[0],6.5, "Rivinumero", size=9)
        self.drawString(xtable[1],6.5, "Selite", size=9)
        self.drawString(xtable[2],6.5, "Aikaväli", size=9)
        self.drawString(xtable[3],6.5, "alv 0 %", size=9)
        self.drawString(xtable[4],6.5, "alv 24 %", size=9)
        self.drawString(xtable[5],6.5, "Yhteensä", size=9)
        self.drawHorizontalStroke(1,6.6, 18.5)

        y = 7
        for line in self.data['bills']:
            for i in range(len(xtable)):
                self.drawString(xtable[i],y, line[i], size=10)
            y += 0.4
        y -= 0.3
        self.drawHorizontalStroke(1,y, 18.5)
        y += 0.4
        self.drawString(xtable[3],y, "Maksettavaa yhteensä:" % self.data, size=10)
        self.drawString(xtable[5],y, "<b>%(pretty_sum)s €</b>" % self.data, size=10)



        self.drawHorizontalStroke(1,18, 18.5)

        self.drawText(1,18.5, "<b>Kapsi Internet-käyttäjät ry</b>\nPL 11\n90571 Oulu", size=7)
        self.drawText(5.5,18.5, "Kotipaikka Oulu\nhttp://www.kapsi.fi/", size=7)
        self.drawText(9.5,18.5, "Sähköposti: %s\nY-tunnus: %s\nYhdistysrekisterinumero: %s" % (settings.FROM_EMAIL,
                                             settings.BUSINESS_ID, settings.ORGANIZATIO_REGISTER_NUMBER), size=7)
        self.drawText(14,18.5, "Tilinumero: %s\nBIC: %s" % (humanize_string(settings.IBAN_ACCOUNT_NUMBER),
                                                            settings.BIC_CODE), size=7)

        # Bill part

        self.drawText(1,20, "Saajan\ntilinumero\nMottagarens\nkontonummer", size=6)
        self.drawText(3.1, 20.6, "%s   %s   %s" % (settings.BANK_OPERATOR, humanize_string(settings.IBAN_ACCOUNT_NUMBER),
                                                   settings.BIC_CODE), size=9)
        self.drawText(1,21.8, "Saaja\nMottagaren", size=6)
        self.drawText(3.1, 21.5, "Kapsi Internet-käyttäjät ry\nPL 11\n90571 Oulu", size=9)
        self.drawText(1,23, "Maksajan\nnimi ja\nosoite\n\nBetalarens\nnamn och\nadress", size=6)
        self.drawText(3.1, 23.5, "%(name)s\n%(address)s\n%(postal_code)s %(postal_office)s\n%(email)s" % self.data, size=9)
        self.drawText(1,25.4, "Alle-\nkirjoitus\nYnderskrift", size=6)
        self.drawText(1,26.5, "Tililtä nro\nFrån konto nr", size=6)

        self.drawText(2.9,20, "IBAN", size=7)

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
        self.drawString(10.5, 2, "<b>MUISTUTUS</b>", aligment="center")
        self.drawText(1, 10, """Hei!

Tämä on muistutus puuttuvasta jäsenmaksusuorituksesta. Alkuperäinen lasku on lähetetty ainoastaan sähköpostitse.
Mikäli et ole saanut sitä, tarkistathan että sähköpostiosoitteesi on oikein jäsenrekisterissä (listattu maksajan tiedoissa
alla).

Voit ottaa yhteyttä Kapsin laskutukseen osoitteeseen laskutus@tuki.kapsi.fi esimerkiksi seuraavissa tilanteissa:
- jos tämä lasku on mielestäsi virheellinen
- haluat erota yhdistyksestä
- haluat muuttaa yhteystietojasi
- haluat sopia maksuaikataulusta
- sinulla on muuta kysyttävää jäsenasioista.
""", size=10)

        self.drawText(1,16, "<b>Muistutuksen maksamatta jättäminen johtaa jäsenpalveluiden lukitsemiseen ja erottamiseen yhdistyksestä!</b>", size=10)
        self.drawText(1,17, "Jos olet jo maksanut muistutuksen, tämä viesti on aiheeton. Olemme huomioineet meille näkyvät jäsenmaksu-\nsuoritukset %(date)s asti." % self.data, size=10)
        if self.data['bill_id']:
            self.drawText(11.5,23.4, "Muistutus laskulle numero %s" % self.data['bill_id'], size=10)

class PDFInvoice(PDFTemplate):
    __type__ = 'invoice'
    def addContent(self):
        self.drawString(10.5, 2, "<b>LASKU</b>", aligment="center")
        self.drawText(1, 10, """
Voit ottaa yhteyttä Kapsin laskutukseen osoitteeseen laskutus@tuki.kapsi.fi esimerkiksi seuraavissa tilanteissa:
   - tämä lasku on sinusta virheellinen
   - haluat erota yhdistyksestä
   - haluat muuttaa yhteystietojasi
   - haluat sopia maksuaikataulusta
   - sinulla on muuta kysyttävää jäsenasioista
""", size=10)
        if self.data['bill_id']:
            self.drawText(11.5,23.4, "Laskunumero %s" % self.data['bill_id'], size=10)


if __name__ == '__main__':
    from membership.models import Contact, Membership, BillingCycle, Bill

    contact = Contact()
    contact.first_name = u"Antero"
    contact.given_name = u"Antero Ilmari"
    contact.last_name = u"Marttila"
    contact.street_address = u'Läppäkuja 16 A 24'
    contact.postal_code = '00500'
    contact.post_office = 'Helsinki'
    contact.country = "Suomi"
    contact.phone = '40403123123'
    contact.sms = '40403123123'
    contact.email = "test@example.com"


    member = Membership()
    member.id = 4444
    member.type = 'P'
    member.status = 'A'
    member.public_memberlist = True
    member.municipality = 'Helsinki'
    member.nationality = 'Suomi'
    member.birth_year = 1990
    member.person = contact
    member.locked = False

    cycle = BillingCycle()
    cycle.membership = member
    cycle.start = datetime.now()
    cycle.end = datetime.now() + timedelta(seconds=31536000)
    cycle.sum = Decimal(40.00)
    cycle.is_paid = False
    cycle.reference_number = "2600013"


    p = PDFReminder('example_reminder.pdf', cycle)
    p.addCycle(cycle)
    p.generate()
    PDFInvoice('example_invoice.pdf', cycle).generate()


    """
    PDFRemainder('ex.pdf').generate({'name': 'Antero Marttila', 'address': 'Läppäkuja 16 A 24',
                   'postal_code':'00500', 'postal_office':'Helsinki',
                   'date': '04.05.2011', 'member_id': '123456', 'due_date': 'HETI',
                   'email': 'antero@kapsi.fi',
                   'amount': 32.74, 'vat': 7.26, 'sum': 80.0,
                   'notify_period': '8vrk', 'bills': [['1', 'Jäsenmaksu', '04.05.2010 - 04.05.2011', '32.74 €','7.26 €','40.00 €'], ['2', 'Jäsenmaksu', '04.05.2011 - 04.05.2012', '32.74 €', '7.26 €','40.00 €']],
                   'reference_number': "2600012"})
    PDFInvoice('ex.pdf').generate({'name': 'Antero Marttila', 'address': 'Läppäkuja 16 A 24',
                   'postal_code':'00500', 'postal_office':'Helsinki',
                   'date': '04.05.2011', 'member_id': '123456', 'due_date': 'HETI',
                   'email': 'antero@kapsi.fi',
                   'amount': 32.74, 'vat': 7.26, 'sum': 80.0,
                   'notify_period': '8vrk', 'bills': [['1', 'Jäsenmaksu', '04.05.2010 - 04.05.2011', '32.74 €','7.26 €','40.00 €'], ['2', 'Jäsenmaksu', '04.05.2011 - 04.05.2012', '32.74 €', '7.26 €','40.00 €']],
                   'reference_number': "2600012"})
    """