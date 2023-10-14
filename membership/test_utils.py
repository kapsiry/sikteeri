# -*- coding: utf-8 -*-
import logging
from random import Random

# Use predictable random for consistent tests
random = Random()
random.seed(1)

logger = logging.getLogger("membership.test_utils")

from membership.models import Membership, Contact


# We use realistic names in test data so that it is feasible to test
# duplicate member detection code locally without using production data.

# Finnish population register center's most popular first names for year 2009
first_names = [
    "Maria", "Juhani", "Aino", "Veeti", "Emilia", "Johannes", "Venla",
    "Eetu", "Sofia", "Mikael", "Emma", "Onni", "Olivia", "Matias",
    "Ella", "Aleksi", "Aino", "Olavi", "Sofia", "Leevi", "Amanda",
    "Onni", "Aada", "Elias", "Matilda", "Ilmari", "Sara", "Lauri",
    "Helmi", "Oskari", "Iida", "Joona", "Aurora", "Elias", "Anni",
    "Matias", "Ilona", "Oliver", "Helmi", "Leo", "Iida", "Eemeli",
    "Emilia", "Niilo", "Eveliina", "Valtteri", "Siiri", "Rasmus", "Katariina",
    "Aleksi", "Veera", "Oliver", "Ella", "Antero", "Sanni", "Miro",
    "Aada", "Viljami", "Vilma", "Jimi", "Kristiina", "Kristian", "Nea",
    "Aatu", "Anni", "Tapani", "Milla", "Daniel", "Johanna", "Samuel",
    "Pinja", "Juho", "Emma", "Lauri", "Lotta", "Aapo", "Sara",
    "Tapio", "Olivia", "Eemeli", "Linnea", "Veeti", "Elli", "Jesse",
    "Anna", "Eetu", "Emmi", "Arttu", "Elina", "Emil", "Ronja",
    "Lenni", "Venla", "Petteri", "Elsa", "Valtteri", "Julia", "Daniel",
    "Nella", "Otto", "Aleksandra", "Eemil", "Kerttu", "Aaro", "Helena",
    "Juho", "Oona", "Joel", "Siiri", "Leevi", "Viivi", "Niklas",
    "Karoliina", "Joona", "Julia", "Ville", "Inkeri", "Julius", "Pihla",
    "Roope", "Alexandra", "Elmeri", "Peppi", "Konsta", "Alisa", "Leo",
    "Nelli", "Juuso", "Susanna", "Otto", "Neea", "Luka", "Josefiina",
    "Aleksanteri", "Jenna", "Mikael", "Kaarina", "Akseli", "Laura", "Samuel",
    "Lotta", "Sakari", "Anna", "Oskari", "Alina", "Anton", "Milja",
    "Julius", "Ellen", "Veikko", "Enni", "Luukas", "Veera", "Toivo",
    "Alisa", "Jere", "Sanni", "Eino", "Ilona", "Niko", "Kerttu",
    "Niilo", "Inka", "Eelis", "Elsa", "Jaakko", "Amanda", "Eeli",
    "Elli", "Rasmus", "Minea", "Anton", "Vilma", "Antti", "Matilda",
    "Eino", "Vilhelmiina", "Väinö", "Iina", "Emil", "Nea", "Henrik",
    "Eevi", "Kasper", "Anneli", "Matti", "Ellen", "Tuomas", "Maija",
    "Aatu", "Saana", "Eemil", "Tuulia", "Kalevi", "Minttu", "Akseli",
    "Anniina", "Joonatan", "Lilja", "Viljami"]

# Kapsi members public unique last name listing as of today.
last_names = [
    "Aalto", "Aaltonen", "Addams-Moring", "Aho", "Ahola", "Ahonen",
    "Aimonen", "Al-Khanji", "Ala-Kojola", "Alakotila", "Alanenpää", "Alanko",
    "Alardt", "Alaspää", "Alatalo", "Andelin", "Annala", "Antinkaapo",
    "Anttila", "Anttonen", "Arstila", "Arvelin", "Auvinen", "Averio",
    "Bainton", "Behm", "Blomberg", "Borén", "Brander", "Brockman",
    "Brunberg", "Busk", "Ceder", "Corsini", "Duldin", "Eerikäinen",
    "Eerola", "Ekblom", "Ekman", "Eloranta", "Emas", "Eriksson",
    "Ernsten", "Erola", "Eräluoto", "Eskelinen", "Eskola", "Everilä",
    "Finnilä", "Fjällström", "Forslund", "Grandell", "Grenrus", "Gröhn",
    "Grönlund", "Haapajärvi", "Haapala", "Haasanen", "Haatainen", "Haataja",
    "Haavisto", "Hagelberg", "Hahtola", "Haikonen", "Haimi", "Hakanen",
    "Hakkarainen", "Halkosaari", "Halla", "Hallamaa", "Hallikainen", "Halme",
    "Halmu", "Halonen", "Hamara", "Hanhijärvi", "Hannola", "Hannus",
    "Hansson", "Harju", "Harkila", "Harma", "Hasanen", "Hassinen",
    "Hast", "Hastrup", "Hatanpää", "Haverinen", "Heikkerö", "Heikkilä",
    "Heikkinen", "Heikura", "Heimonen", "Heinikangas", "Heinonen", "Heinänen",
    "Heiramo", "Heiskanen", "Helander", "Helenius", "Herd", "Herranen",
    "Herukka", "Heusala", "Hietala", "Hietanen", "Hietaranta", "Hiilesrinne",
    "Hiljander", "Hill", "Hillervo", "Hiltunen", "Hinkula", "Hintikka",
    "Hirvojärvi", "Holopainen", "Hongisto", "Honkanen", "Honkonen", "Hopiavuori",
    "Hotti", "Huhtala", "Huhtinen", "Hulkko", "Huoman", "Huotari",
    "Huovinen", "Hurtta", "Huttunen", "Huuhtanen", "Huuskonen", "Hyttinen",
    "Hyvärinen", "Häkkinen", "Hämeenkorpi", "Hämäläinen", "Hänninen", "Höglund",
    "Ihatsu", "Ijäs", "Ikonen", "Ilmonen", "Iltanen", "Ingman",
    "Inha", "Inkinen", "Isaksson", "Isomäki", "Ituarte", "Itäsalo",
    "Jaakkola", "Jaatinen", "Jakobsson", "Jalonen", "Jetsu", "Johansson",
    "Jokela", "Jokinen", "Jokitalo", "Jormanainen", "Junni", "Juopperi",
    "Juutinen", "Juvankoski", "Juvonen", "Järvenpää", "Järvensivu", "Järvinen",
    "Jääskelä", "Jääskeläinen", "Kaarela", "Kaartti", "Kaija", "Kaikkonen",
    "Kaila", "Kainulainen", "Kajan", "Kakko", "Kallio", "Kanniainen",
    "Kanninen", "Kare-Mäkiaho", "Karhunen", "Kari", "Karimäki", "Karisalmi",
    "Karjalainen", "Karlsson", "Karppi", "Karttunen", "Karvinen", "Karvonen",
    "Kasari", "Kataja", "Katavisto", "Kattelus", "Kauppi", "Kauppinen",
    "Keihänen", "Keijonen", "Kekki", "Kekkonen", "Kelanne", "Kenttälä",
    "Keränen", "Keskitalo", "Kesti", "Ketolainen", "Ketonen", "Kettinen",
    "Kianto", "Kiiskilä", "Kilpiäinen", "Kinnula", "Kinnunen", "Kirkkopelto",
    "Kirves", "Kittilä", "Kiviharju", "Kivikunnas", "Kivilahti", "Kiviluoto",
    "Kivimäki", "Kivirinta", "Knuutinen", "Kohtamäki", "Kois", "Koivisto",
    "Koivu", "Koivula", "Koivulahti", "Koivumaa", "Koivunalho", "Koivunen",
    "Koivuranta", "Kokkonen", "Kokkoniemi", "Komulainen", "Konsala", "Konttila",
    "Konttinen", "Koponen", "Korhonen", "Kortesalmi", "Kortetmäki", "Koskela",
    "Koskenniemi", "Koski", "Petteri", "Koskinen", "Kotanen", "Koulu",
    "Kraft", "Krohn", "Krüger", "Kudjoi", "Kuhanen", "Kuittinen",
    "Kuitunen", "Kujala", "Kujansuu", "Kulju", "Kurkimäki", "Kuukasjärvi",
    "Kuusisto", "Kuvaja", "Kymäläinen", "Kyntöaho", "Kähkönen", "Käki",
    "Kärkkäinen", "Kärnä", "Laaksonen", "Laalo", "Laapotti", "Lagren",
    "Lagus", "Lahdenmäki", "Lahdenperä", "Lahikainen", "Lahtela", "Laine",
    "Lainiola", "Laitila", "Laitinen", "Untamo", "Lakhan", "Lamminen",
    "Lammio", "Lampela", "Lampén", "Lampi", "Lampinen", "Lankila",
    "Lapinniemi", "Lappalainen", "Larivaara", "Larja", "Latvatalo", "Laurila",
    "Laxström", "Lehmuskenttä", "Lehtinen", "Lehtola", "Lehtonen", "Leikkari",
    "Leiviskä", "Leivo", "Lempinen", "Lepistö", "Leppänen", "Levonen",
    "Lievemaa", "Liimatta", "Likitalo", "Liljeqvist", "Lindeman", "Lindén",
    "Lindfors", "Lindström", "Linkoaho", "Linkola", "Linnaluoto", "Linnamäki",
    "Lintervo", "Lintumäki", "Lipsanen", "Liukkonen", "Loikkanen", "Loponen",
    "Louhiranta", "Lundan", "Luosmaa", "Luukko", "Luukkonen", "Lähdemäki",
    "Lähteenmäki", "Löfgren", "Löytty", "Maaranen", "Magga", "Makkonen",
    "Maksimainen", "Malinen", "Malm", "Malmivirta", "Manner", "Manninen",
    "Mansikkala", "Marin", "Marjamaa", "Marjoneva", "Markkanen", "Martikainen",
    "Marttila", "Matikainen", "Matkaselkä", "Mattila", "Maukonen", "Melama",
    "Melenius", "Mellin", "Merikivi", "Meriläinen", "Merisalo", "Meskanen",
    "Miettunen", "Miinin", "Mikkonen", "Moisala", "Moisio", "Mononen",
    "Montonen", "Mustonen", "Myllymäki", "Myllyselkä", "Myntti", "Myyry",
    "Mähönen", "Mäkelä", "Mäkeläinen", "Mäkinen", "Mäkitalo", "Mänki",
    "Mäntylä", "Märsy", "Mättö", "Mäyränen", "Määttä", "Möller",
    "Nemeth", "Niemelä", "Niemenmaa", "Niemi", "Nieminen", "Niiranen",
    "Nikander", "Nikkonen", "Nikula", "Niskanen", "Nisula", "Nousiainen",
    "Nummiaho", "Nurmi", "Nurminen", "Nygren", "Nykänen", "Nylund",
    "Nyrhilä", "Näyhä", "Ohtamaa", "Ojala", "Ollila", "Olmari",
    "Oras", "Paajanen", "Paalanen", "Paananen", "Packalen", "Pahalahti",
    "Paimen", "Pakkanen", "Palo", "Palokangas", "Palomäki", "Palosaari",
    "Panula", "Pappinen", "Parkkinen", "Partanen", "Parviainen", "Pasila",
    "Paul", "Pekkanen", "Peltola", "Peltonen", "Pennala", "Pentikäinen",
    "Penttilä", "Perttunen", "Perälä", "Pesonen", "Peuhkuri", "Peurakoski",
    "Piesala", "Pietarinen", "Pietikäinen", "Pietilä", "Pieviläinen", "Pihkala",
    "Pihlaja", "Pihlajaniemi", "Piittinen", "Pikkarainen", "Pirinen", "Pirttijärvi",
    "Pitkänen", "Pohjalainen", "Pohjanraito", "Pohjola", "Pokkinen", "Polso",
    "Portaankorva", "Portti", "Posti", "Prusi", "Pulliainen", "Puranen",
    "Pusa", "Pussinen", "Pyhäjärvi", "Pylvänäinen", "Pölönen", "Pöykkö",
    "Raatikainen", "Rahikainen", "Rainela", "Raitanen", "Raitmaa", "Raittila",
    "Rajala", "Rajamäki", "Ranki", "Ranta", "Rantala", "Rantamäki",
    "Rapo", "Rasilainen", "Rauhala", "Rautiainen", "Rehu", "Reijonen",
    "Reunanen", "Riikonen", "Rimpiläinen", "Rissanen", "Ristilä", "Rokka",
    "Roponen", "Ruhanen", "Runonen", "Rutanen", "Ruuhonen", "Ruusu",
    "Ryhänen", "Rytkönen", "Räsänen", "Räty", "Rönkkö", "Rössi",
    "Saarenmäki", "Saarijoki", "Saarikoski", "Saarinen", "Saastamoinen", "Saine",
    "Saksa", "Salkia", "Salmela", "Salmi", "Salminen", "Salo",
    "Salokanto", "Salomaa", "Salomäki", "Salonen", "Sand", "Sanisalo",
    "Santala", "Savolainen", "Schwartz", "Selin", "Seppä", "Seppälä",
    "Seppänen", "Setälä", "Siekkinen", "Sievänen", "Sihvo", "Siironen",
    "Siitonen", "Silfver", "Sillanpää", "Siltala", "Simola", "Simon",
    "Siniluoto", "Sinivaara", "Sipilä", "Sivula", "Sjöberg", "Soili",
    "Soini", "Soininen", "Solja", "Solkio", "Sonck", "Sopanen",
    "Sotejeff", "Staven", "Strand", "Suckman", "Sunell", "Suolahti",
    "Suominen", "Suoniitty", "Suonvieri", "Suorsa", "Suvanne", "Syreeni",
    "Syrjä", "Syrjälä", "Syvänen", "Särkkä", "Säämäki", "Sääskilahti",
    "Södervall", "Tahvanainen", "Taina", "Taipale", "Taivalsalmi", "Tallqvist",
    "Tamminen", "Tammisto", "Tanhua", "Tanner", "Tanskanen", "Tapper-Veirto",
    "Tarsa", "Tarvainen", "Tiainen", "Tiira", "Tikka", "Tikkanen",
    "Toivanen", "Toivonen", "Tolvanen", "Tulonen", "Tunkkari", "Tuohimaa",
    "Tuomela", "Tuomi", "Tuomimaa", "Tuominen", "Tuomivaara", "Turanlahti",
    "Turpeinen", "Turunen", "Tuunainen", "Tuusa", "Tykkä", "Tyrväinen",
    "Tähtinen", "Töttö", "Urhonen", "Uuksulainen", "Uusitalo", "Vaarala",
    "Vaaramaa", "Vainio", "Vainionpää", "Valkeinen", "Valkonen", "Valtonen",
    "Valve", "Varanka", "Varrio", "Varsaluoma", "Vartiainen", "Veijalainen",
    "Veijola", "Velhonoja", "Venäläinen", "Vesala", "Vesiluoma", "Vestu",
    "Vierimaa", "Viippola", "Viitala", "Viitanen", "Vilkki", "Vilppunen",
    "Vire", "Virta", "Virtala", "Virtanen", "Vitikka", "Voipio",
    "Vuokko", "Vuola", "Vuollet", "Vuorela", "Vuorinen", "Vähäkylä",
    "Vähämäki", "Vähänen", "Väisänen", "Välimaa", "Väänänen", "Wahalahti",
    "Wikman", "Yli-Hukka", "Ylimäinen", "Ylinen", "Ylönen", "Yrttikoski",
    "Äijänen", "Ärmänen"]


def random_first_name():
    return random.choice(first_names)


def random_last_name():
    return random.choice(last_names)


def create_dummy_member(status, type='P', mid=None):
    if status not in ['N', 'P', 'A']:
        raise Exception("Unknown membership status")  # pragma: no cover
    if type not in ['P', 'S', 'O', 'H']:
        raise Exception("Unknown membership type")  # pragma: no cover
    i = random.randint(1, 300)
    fname = random_first_name()
    d = {
        'street_address' : 'Testikatu %d'%i,
        'postal_code' : '%d' % (i+1000),
        'post_office' : 'Paska kaupunni',
        'country' : 'Finland',
        'phone' : "%09d" % (40123000 + i),
        'sms' : "%09d" % (40123000 + i),
        'email' : 'user%d@example.com' % i,
        'homepage' : 'http://www.example.com/%d'%i,
        'first_name' : fname,
        'given_names' : '%s %s' % (fname, "Kapsi"),
        'last_name' : random_last_name(),
    }
    contact = Contact(**d)
    contact.save()
    if type in ('O', 'S'):
        contact.organization_name = contact.name()
        contact.first_name = ''
        contact.last_name = ''
        contact.save()
        membership = Membership(id=mid, type=type, status=status,
                                organization=contact,
                                nationality='Finnish',
                                municipality='Paska kaupunni',
                                extra_info='Hintsunlaisesti semmoisia tietoja.')
    else:
        membership = Membership(id=mid, type=type, status=status,
                                person=contact,
                                nationality='Finnish',
                                municipality='Paska kaupunni',
                                extra_info='Hintsunlaisesti semmoisia tietoja.')
    logger.info("New application %s from %s:." % (str(contact), '::1'))
    membership.save()
    return membership


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
