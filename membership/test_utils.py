# -*- coding: utf-8 -*-
from random import choice, random, randint
import logging

# Finnish population register center's most popular first names for year 2009
first_names = [
    u"Iines", u"Aku", u"Minni", u"Mikki", u"Tupu", u"Hupu", u"Lupu",
    u"Leenu", u"Liinu", u"Tiinu", u"Pluto", u"Roope", u"Taavi", u"Touho",
    u"Kulta-Into", u"Kroisos", u"Velmu", u"Pelle", u"Hannu", u"Hansu", u"Mummo",
    u"Milla", u"Toope", u"Mortti", u"Vertti", u"Hessu", u"Polle", u"Heluna",
    u"Klaara", u"Sisu", u"Matami", u"Tiku", u"Tiku", u"Veli", u"Sepe",
    u"Tipsu", u"Timotei", u"Bumba", u"Dumbo", u"Jopi", u"Neiti"]

# Kapsi members public unique last name listing as of today.
last_names = [
    u"Ankka", u"Hiiri", u"Koninkaulus", u"Peloton", u"Hanhi", u"Pennonen",
    u"Pii", u"Magia", u"Hopo", u"Kotro", u"Jalkapuoli", u"Kaasi", u"Kani"
    u"Susi", u"Hukka",u"Ponteva", u"Sirkka", u"Näpsä"
    ]

# Random finctonal municipalities
municipalities = [
    u"Ankkalinna", u"Hanhivaara", u"Mummola", u"Duckburg", u"Kaukastan", u"Takametsä",
    u"Timpuktu", u"Toisaala", u"Mäentaus", u"Vuorisola", u"Mikälie", u"Jokimutka"
    ]

street_addresses = [
    u"Paratiisitie", u"Onnitie", "Pääkatu", "Sivukuja", u"Jullentie", u"Säiliökatu",
    u"Rahakuja", u"Rosvotie", u"Hassukuja", u"Puutarhakatu", u"Lähitie"
    ]

def random_first_name():
    return choice(first_names)

def random_last_name():
    return choice(last_names)

def random_municipality():
    return choice(municipalities)

def random_street():
    return choice(street_addresses)

def random_email(firstname, lastname):
    firstname = firstname.lower()
    lastname = lastname.lower()
    return ("%s.%s@example.com" % (firstname, lastname))

class MockLoggingHandler(logging.Handler):
    """Mock logging handler to check for expected logs as per:
    <http://stackoverflow.com/questions/899067/how-should-i-verify-a-log-message-when-testing-python-code-under-nose/1049375#1049375>"""
    def __init__(self, *args, **kwargs):
        self.reset()
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.messages[record.levelname.lower()].append(record.getMessage())

    def reset(self):
        self.messages = {
            'debug': [],
            'info': [],
            'warning': [],
            'error': [],
            'critical': [],
        }
