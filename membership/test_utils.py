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
    u"Maria", u"Juhani", u"Aino", u"Veeti", u"Emilia", u"Johannes", u"Venla",
    u"Eetu", u"Sofia", u"Mikael", u"Emma", u"Onni", u"Olivia", u"Matias",
    u"Ella", u"Aleksi", u"Aino", u"Olavi", u"Sofia", u"Leevi", u"Amanda",
    u"Onni", u"Aada", u"Elias", u"Matilda", u"Ilmari", u"Sara", u"Lauri",
    u"Helmi", u"Oskari", u"Iida", u"Joona", u"Aurora", u"Elias", u"Anni",
    u"Matias", u"Ilona", u"Oliver", u"Helmi", u"Leo", u"Iida", u"Eemeli",
    u"Emilia", u"Niilo", u"Eveliina", u"Valtteri", u"Siiri", u"Rasmus", u"Katariina",
    u"Aleksi", u"Veera", u"Oliver", u"Ella", u"Antero", u"Sanni", u"Miro",
    u"Aada", u"Viljami", u"Vilma", u"Jimi", u"Kristiina", u"Kristian", u"Nea",
    u"Aatu", u"Anni", u"Tapani", u"Milla", u"Daniel", u"Johanna", u"Samuel",
    u"Pinja", u"Juho", u"Emma", u"Lauri", u"Lotta", u"Aapo", u"Sara",
    u"Tapio", u"Olivia", u"Eemeli", u"Linnea", u"Veeti", u"Elli", u"Jesse",
    u"Anna", u"Eetu", u"Emmi", u"Arttu", u"Elina", u"Emil", u"Ronja",
    u"Lenni", u"Venla", u"Petteri", u"Elsa", u"Valtteri", u"Julia", u"Daniel",
    u"Nella", u"Otto", u"Aleksandra", u"Eemil", u"Kerttu", u"Aaro", u"Helena",
    u"Juho", u"Oona", u"Joel", u"Siiri", u"Leevi", u"Viivi", u"Niklas",
    u"Karoliina", u"Joona", u"Julia", u"Ville", u"Inkeri", u"Julius", u"Pihla",
    u"Roope", u"Alexandra", u"Elmeri", u"Peppi", u"Konsta", u"Alisa", u"Leo",
    u"Nelli", u"Juuso", u"Susanna", u"Otto", u"Neea", u"Luka", u"Josefiina",
    u"Aleksanteri", u"Jenna", u"Mikael", u"Kaarina", u"Akseli", u"Laura", u"Samuel",
    u"Lotta", u"Sakari", u"Anna", u"Oskari", u"Alina", u"Anton", u"Milja",
    u"Julius", u"Ellen", u"Veikko", u"Enni", u"Luukas", u"Veera", u"Toivo",
    u"Alisa", u"Jere", u"Sanni", u"Eino", u"Ilona", u"Niko", u"Kerttu",
    u"Niilo", u"Inka", u"Eelis", u"Elsa", u"Jaakko", u"Amanda", u"Eeli",
    u"Elli", u"Rasmus", u"Minea", u"Anton", u"Vilma", u"Antti", u"Matilda",
    u"Eino", u"Vilhelmiina", u"Väinö", u"Iina", u"Emil", u"Nea", u"Henrik",
    u"Eevi", u"Kasper", u"Anneli", u"Matti", u"Ellen", u"Tuomas", u"Maija",
    u"Aatu", u"Saana", u"Eemil", u"Tuulia", u"Kalevi", u"Minttu", u"Akseli",
    u"Anniina", u"Joonatan", u"Lilja", u"Viljami"]

# Kapsi members public unique last name listing as of today.
last_names = [
    u"Aalto", u"Aaltonen", u"Addams-Moring", u"Aho", u"Ahola", u"Ahonen",
    u"Aimonen", u"Al-Khanji", u"Ala-Kojola", u"Alakotila", u"Alanenpää", u"Alanko",
    u"Alardt", u"Alaspää", u"Alatalo", u"Andelin", u"Annala", u"Antinkaapo",
    u"Anttila", u"Anttonen", u"Arstila", u"Arvelin", u"Auvinen", u"Averio",
    u"Bainton", u"Behm", u"Blomberg", u"Borén", u"Brander", u"Brockman",
    u"Brunberg", u"Busk", u"Ceder", u"Corsini", u"Duldin", u"Eerikäinen",
    u"Eerola", u"Ekblom", u"Ekman", u"Eloranta", u"Emas", u"Eriksson",
    u"Ernsten", u"Erola", u"Eräluoto", u"Eskelinen", u"Eskola", u"Everilä",
    u"Finnilä", u"Fjällström", u"Forslund", u"Grandell", u"Grenrus", u"Gröhn",
    u"Grönlund", u"Haapajärvi", u"Haapala", u"Haasanen", u"Haatainen", u"Haataja",
    u"Haavisto", u"Hagelberg", u"Hahtola", u"Haikonen", u"Haimi", u"Hakanen",
    u"Hakkarainen", u"Halkosaari", u"Halla", u"Hallamaa", u"Hallikainen", u"Halme",
    u"Halmu", u"Halonen", u"Hamara", u"Hanhijärvi", u"Hannola", u"Hannus",
    u"Hansson", u"Harju", u"Harkila", u"Harma", u"Hasanen", u"Hassinen",
    u"Hast", u"Hastrup", u"Hatanpää", u"Haverinen", u"Heikkerö", u"Heikkilä",
    u"Heikkinen", u"Heikura", u"Heimonen", u"Heinikangas", u"Heinonen", u"Heinänen",
    u"Heiramo", u"Heiskanen", u"Helander", u"Helenius", u"Herd", u"Herranen",
    u"Herukka", u"Heusala", u"Hietala", u"Hietanen", u"Hietaranta", u"Hiilesrinne",
    u"Hiljander", u"Hill", u"Hillervo", u"Hiltunen", u"Hinkula", u"Hintikka",
    u"Hirvojärvi", u"Holopainen", u"Hongisto", u"Honkanen", u"Honkonen", u"Hopiavuori",
    u"Hotti", u"Huhtala", u"Huhtinen", u"Hulkko", u"Huoman", u"Huotari",
    u"Huovinen", u"Hurtta", u"Huttunen", u"Huuhtanen", u"Huuskonen", u"Hyttinen",
    u"Hyvärinen", u"Häkkinen", u"Hämeenkorpi", u"Hämäläinen", u"Hänninen", u"Höglund",
    u"Ihatsu", u"Ijäs", u"Ikonen", u"Ilmonen", u"Iltanen", u"Ingman",
    u"Inha", u"Inkinen", u"Isaksson", u"Isomäki", u"Ituarte", u"Itäsalo",
    u"Jaakkola", u"Jaatinen", u"Jakobsson", u"Jalonen", u"Jetsu", u"Johansson",
    u"Jokela", u"Jokinen", u"Jokitalo", u"Jormanainen", u"Junni", u"Juopperi",
    u"Juutinen", u"Juvankoski", u"Juvonen", u"Järvenpää", u"Järvensivu", u"Järvinen",
    u"Jääskelä", u"Jääskeläinen", u"Kaarela", u"Kaartti", u"Kaija", u"Kaikkonen",
    u"Kaila", u"Kainulainen", u"Kajan", u"Kakko", u"Kallio", u"Kanniainen",
    u"Kanninen", u"Kare-Mäkiaho", u"Karhunen", u"Kari", u"Karimäki", u"Karisalmi",
    u"Karjalainen", u"Karlsson", u"Karppi", u"Karttunen", u"Karvinen", u"Karvonen",
    u"Kasari", u"Kataja", u"Katavisto", u"Kattelus", u"Kauppi", u"Kauppinen",
    u"Keihänen", u"Keijonen", u"Kekki", u"Kekkonen", u"Kelanne", u"Kenttälä",
    u"Keränen", u"Keskitalo", u"Kesti", u"Ketolainen", u"Ketonen", u"Kettinen",
    u"Kianto", u"Kiiskilä", u"Kilpiäinen", u"Kinnula", u"Kinnunen", u"Kirkkopelto",
    u"Kirves", u"Kittilä", u"Kiviharju", u"Kivikunnas", u"Kivilahti", u"Kiviluoto",
    u"Kivimäki", u"Kivirinta", u"Knuutinen", u"Kohtamäki", u"Kois", u"Koivisto",
    u"Koivu", u"Koivula", u"Koivulahti", u"Koivumaa", u"Koivunalho", u"Koivunen",
    u"Koivuranta", u"Kokkonen", u"Kokkoniemi", u"Komulainen", u"Konsala", u"Konttila",
    u"Konttinen", u"Koponen", u"Korhonen", u"Kortesalmi", u"Kortetmäki", u"Koskela",
    u"Koskenniemi", u"Koski", u"Petteri", u"Koskinen", u"Kotanen", u"Koulu",
    u"Kraft", u"Krohn", u"Krüger", u"Kudjoi", u"Kuhanen", u"Kuittinen",
    u"Kuitunen", u"Kujala", u"Kujansuu", u"Kulju", u"Kurkimäki", u"Kuukasjärvi",
    u"Kuusisto", u"Kuvaja", u"Kymäläinen", u"Kyntöaho", u"Kähkönen", u"Käki",
    u"Kärkkäinen", u"Kärnä", u"Laaksonen", u"Laalo", u"Laapotti", u"Lagren",
    u"Lagus", u"Lahdenmäki", u"Lahdenperä", u"Lahikainen", u"Lahtela", u"Laine",
    u"Lainiola", u"Laitila", u"Laitinen", u"Untamo", u"Lakhan", u"Lamminen",
    u"Lammio", u"Lampela", u"Lampén", u"Lampi", u"Lampinen", u"Lankila",
    u"Lapinniemi", u"Lappalainen", u"Larivaara", u"Larja", u"Latvatalo", u"Laurila",
    u"Laxström", u"Lehmuskenttä", u"Lehtinen", u"Lehtola", u"Lehtonen", u"Leikkari",
    u"Leiviskä", u"Leivo", u"Lempinen", u"Lepistö", u"Leppänen", u"Levonen",
    u"Lievemaa", u"Liimatta", u"Likitalo", u"Liljeqvist", u"Lindeman", u"Lindén",
    u"Lindfors", u"Lindström", u"Linkoaho", u"Linkola", u"Linnaluoto", u"Linnamäki",
    u"Lintervo", u"Lintumäki", u"Lipsanen", u"Liukkonen", u"Loikkanen", u"Loponen",
    u"Louhiranta", u"Lundan", u"Luosmaa", u"Luukko", u"Luukkonen", u"Lähdemäki",
    u"Lähteenmäki", u"Löfgren", u"Löytty", u"Maaranen", u"Magga", u"Makkonen",
    u"Maksimainen", u"Malinen", u"Malm", u"Malmivirta", u"Manner", u"Manninen",
    u"Mansikkala", u"Marin", u"Marjamaa", u"Marjoneva", u"Markkanen", u"Martikainen",
    u"Marttila", u"Matikainen", u"Matkaselkä", u"Mattila", u"Maukonen", u"Melama",
    u"Melenius", u"Mellin", u"Merikivi", u"Meriläinen", u"Merisalo", u"Meskanen",
    u"Miettunen", u"Miinin", u"Mikkonen", u"Moisala", u"Moisio", u"Mononen",
    u"Montonen", u"Mustonen", u"Myllymäki", u"Myllyselkä", u"Myntti", u"Myyry",
    u"Mähönen", u"Mäkelä", u"Mäkeläinen", u"Mäkinen", u"Mäkitalo", u"Mänki",
    u"Mäntylä", u"Märsy", u"Mättö", u"Mäyränen", u"Määttä", u"Möller",
    u"Nemeth", u"Niemelä", u"Niemenmaa", u"Niemi", u"Nieminen", u"Niiranen",
    u"Nikander", u"Nikkonen", u"Nikula", u"Niskanen", u"Nisula", u"Nousiainen",
    u"Nummiaho", u"Nurmi", u"Nurminen", u"Nygren", u"Nykänen", u"Nylund",
    u"Nyrhilä", u"Näyhä", u"Ohtamaa", u"Ojala", u"Ollila", u"Olmari",
    u"Oras", u"Paajanen", u"Paalanen", u"Paananen", u"Packalen", u"Pahalahti",
    u"Paimen", u"Pakkanen", u"Palo", u"Palokangas", u"Palomäki", u"Palosaari",
    u"Panula", u"Pappinen", u"Parkkinen", u"Partanen", u"Parviainen", u"Pasila",
    u"Paul", u"Pekkanen", u"Peltola", u"Peltonen", u"Pennala", u"Pentikäinen",
    u"Penttilä", u"Perttunen", u"Perälä", u"Pesonen", u"Peuhkuri", u"Peurakoski",
    u"Piesala", u"Pietarinen", u"Pietikäinen", u"Pietilä", u"Pieviläinen", u"Pihkala",
    u"Pihlaja", u"Pihlajaniemi", u"Piittinen", u"Pikkarainen", u"Pirinen", u"Pirttijärvi",
    u"Pitkänen", u"Pohjalainen", u"Pohjanraito", u"Pohjola", u"Pokkinen", u"Polso",
    u"Portaankorva", u"Portti", u"Posti", u"Prusi", u"Pulliainen", u"Puranen",
    u"Pusa", u"Pussinen", u"Pyhäjärvi", u"Pylvänäinen", u"Pölönen", u"Pöykkö",
    u"Raatikainen", u"Rahikainen", u"Rainela", u"Raitanen", u"Raitmaa", u"Raittila",
    u"Rajala", u"Rajamäki", u"Ranki", u"Ranta", u"Rantala", u"Rantamäki",
    u"Rapo", u"Rasilainen", u"Rauhala", u"Rautiainen", u"Rehu", u"Reijonen",
    u"Reunanen", u"Riikonen", u"Rimpiläinen", u"Rissanen", u"Ristilä", u"Rokka",
    u"Roponen", u"Ruhanen", u"Runonen", u"Rutanen", u"Ruuhonen", u"Ruusu",
    u"Ryhänen", u"Rytkönen", u"Räsänen", u"Räty", u"Rönkkö", u"Rössi",
    u"Saarenmäki", u"Saarijoki", u"Saarikoski", u"Saarinen", u"Saastamoinen", u"Saine",
    u"Saksa", u"Salkia", u"Salmela", u"Salmi", u"Salminen", u"Salo",
    u"Salokanto", u"Salomaa", u"Salomäki", u"Salonen", u"Sand", u"Sanisalo",
    u"Santala", u"Savolainen", u"Schwartz", u"Selin", u"Seppä", u"Seppälä",
    u"Seppänen", u"Setälä", u"Siekkinen", u"Sievänen", u"Sihvo", u"Siironen",
    u"Siitonen", u"Silfver", u"Sillanpää", u"Siltala", u"Simola", u"Simon",
    u"Siniluoto", u"Sinivaara", u"Sipilä", u"Sivula", u"Sjöberg", u"Soili",
    u"Soini", u"Soininen", u"Solja", u"Solkio", u"Sonck", u"Sopanen",
    u"Sotejeff", u"Staven", u"Strand", u"Suckman", u"Sunell", u"Suolahti",
    u"Suominen", u"Suoniitty", u"Suonvieri", u"Suorsa", u"Suvanne", u"Syreeni",
    u"Syrjä", u"Syrjälä", u"Syvänen", u"Särkkä", u"Säämäki", u"Sääskilahti",
    u"Södervall", u"Tahvanainen", u"Taina", u"Taipale", u"Taivalsalmi", u"Tallqvist",
    u"Tamminen", u"Tammisto", u"Tanhua", u"Tanner", u"Tanskanen", u"Tapper-Veirto",
    u"Tarsa", u"Tarvainen", u"Tiainen", u"Tiira", u"Tikka", u"Tikkanen",
    u"Toivanen", u"Toivonen", u"Tolvanen", u"Tulonen", u"Tunkkari", u"Tuohimaa",
    u"Tuomela", u"Tuomi", u"Tuomimaa", u"Tuominen", u"Tuomivaara", u"Turanlahti",
    u"Turpeinen", u"Turunen", u"Tuunainen", u"Tuusa", u"Tykkä", u"Tyrväinen",
    u"Tähtinen", u"Töttö", u"Urhonen", u"Uuksulainen", u"Uusitalo", u"Vaarala",
    u"Vaaramaa", u"Vainio", u"Vainionpää", u"Valkeinen", u"Valkonen", u"Valtonen",
    u"Valve", u"Varanka", u"Varrio", u"Varsaluoma", u"Vartiainen", u"Veijalainen",
    u"Veijola", u"Velhonoja", u"Venäläinen", u"Vesala", u"Vesiluoma", u"Vestu",
    u"Vierimaa", u"Viippola", u"Viitala", u"Viitanen", u"Vilkki", u"Vilppunen",
    u"Vire", u"Virta", u"Virtala", u"Virtanen", u"Vitikka", u"Voipio",
    u"Vuokko", u"Vuola", u"Vuollet", u"Vuorela", u"Vuorinen", u"Vähäkylä",
    u"Vähämäki", u"Vähänen", u"Väisänen", u"Välimaa", u"Väänänen", u"Wahalahti",
    u"Wikman", u"Yli-Hukka", u"Ylimäinen", u"Ylinen", u"Ylönen", u"Yrttikoski",
    u"Äijänen", u"Ärmänen"]

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
    if type == 'O':
        contact.organization_name = contact.name()
        contact.first_name = u''
        contact.last_name = u''
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
