# -*- coding: utf-8 -*-
from random import choice, random, randint
import logging

# Finnish population register center's most popular first names for year 2009
male_first_names = [
    u'Juhani', u'Veeti', u'Johannes', u'Eetu', u'Mikael', u'Onni', u'Matias',
    u'Aleksi', u'Olavi', u'Leevi', u'Onni', u'Elias', u'Ilmari', u'Lauri',
    u'Oskari', u'Joona', u'Elias', u'Matias', u'Oliver', u'Leo', u'Eemeli',
    u'Niilo', u'Valtteri', u'Rasmus', u'Aleksi', u'Oliver', u'Antero', u'Miro',
    u'Viljami', u'Jimi', u'Kristian', u'Aatu', u'Tapani', u'Daniel', u'Samuel',
    u'Juho', u'Lauri', u'Aapo', u'Tapio', u'Eemeli', u'Veeti', u'Jesse', u'Eetu',
    u'Arttu', u'Emil', u'Lenni', u'Petteri', u'Valtteri', u'Daniel', u'Otto',
    u'Eemil', u'Aaro', u'Juho', u'Joel', u'Leevi', u'Niklas', u'Joona', u'Ville',
    u'Julius', u'Roope', u'Elmeri', u'Konsta', u'Leo', u'Juuso', u'Otto', u'Luka',
    u'Aleksanteri', u'Mikael', u'Akseli', u'Samuel', u'Sakari', u'Oskari', u'Anton',
    u'Julius', u'Veikko', u'Luukas', u'Toivo', u'Jere', u'Eino', u'Niko', u'Niilo',
    u'Eelis', u'Jaakko', u'Eeli', u'Rasmus', u'Anton', u'Antti', u'Eino', u'Väinö',
    u'Emil', u'Henrik', u'Kasper', u'Matti', u'Tuomas', u'Aatu', u'Eemil', u'Kalevi',
    u'Akseli', u'Joonatan', u'Viljami'
]

flemale_first_names = [
    u'Maria', u'Aino', u'Emilia', u'Venla', u'Sofia', u'Emma', u'Olivia', u'Ella',
    u'Aino', u'Sofia', u'Amanda', u'Aada', u'Matilda', u'Sara', u'Helmi', u'Iida',
    u'Aurora', u'Anni', u'Ilona', u'Helmi', u'Iida', u'Emilia', u'Eveliina', u'Siiri',
    u'Katariina', u'Veera', u'Ella', u'Sanni', u'Aada', u'Vilma', u'Kristiina', u'Nea',
    u'Anni', u'Milla', u'Johanna', u'Pinja', u'Emma', u'Lotta', u'Sara', u'Olivia',
    u'Linnea', u'Elli', u'Anna', u'Emmi', u'Elina', u'Ronja', u'Venla', u'Elsa',
    u'Julia', u'Nella', u'Aleksandra', u'Kerttu', u'Helena', u'Oona', u'Siiri',
    u'Viivi', u'Karoliina', u'Julia', u'Inkeri', u'Pihla', u'Alexandra', u'Peppi',
    u'Alisa', u'Nelli', u'Susanna', u'Neea', u'Josefiina', u'Jenna', u'Kaarina',
    u'Laura', u'Lotta', u'Anna', u'Alina', u'Milja', u'Ellen', u'Enni', u'Veera',
    u'Alisa', u'Sanni', u'Ilona', u'Kerttu', u'Inka', u'Elsa', u'Amanda', u'Elli',
    u'Minea', u'Vilma', u'Matilda', u'Vilhelmiina', u'Iina', u'Nea', u'Eevi', u'Anneli',
    u'Ellen', u'Maija', u'Saana', u'Tuulia', u'Minttu', u'Anniina', u'Lilja'
    ]

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

municipalities = [
    u"Akaa",u"Alajärvi",u"Alavus",u"Espoo",u"Forssa",u"Haapajärvi",u"Haapavesi",
    u"Hamina",u"Hanko",u"Harjavalta",u"Heinola",u"Helsinki",u"Huittinen",u"Hyvinkää",
    u"Hämeenlinna",u"Iisalmi",u"Ikaalinen",u"Imatra",u"Joensuu",u"Juankoski",u"Jyväskylä",
    u"Jämsä",u"Järvenpää",u"Kaarina",u"Kajaani",u"Kalajoki",u"Kankaanpää",u"Kannus",
    u"Karkkila",u"Kaskinen",u"Kauhajoki",u"Kauhava",u"Kauniainen",u"Kemi",u"Kemijärvi",
    u"Kerava",u"Keuruu",u"Kitee",u"Kiuruvesi",u"Kokemäki",u"Kokkola",u"Kotka",u"Kouvola",
    u"Kristiinankaupunki",u"Kuhmo",u"Kuopio",u"Kurikka",u"Kuusamo",u"Lahti",u"Laitila",
    u"Lappeenranta",u"Lapua",u"Lieksa",u"Lohja",u"Loimaa",u"Loviisa",u"Maarianhamina",
    u"Mikkeli",u"Mänttä-Vilppula",u"Naantali",u"Nilsiä",u"Nivala",u"Nokia",u"Nurmes",
    u"Närpiö",u"Orimattila",u"Orivesi",u"Oulainen",u"Oulu",u"Outokumpu",u"Paimio",
    u"Parainen",u"Parkano",u"Pieksämäki",u"Pietarsaari",u"Pori",u"Porvoo",u"Pudasjärvi",
    u"Pyhäjärvi",u"Raahe",u"Raasepori",u"Raisio",u"Rauma",u"Riihimäki",u"Rovaniemi",
    u"Saarijärvi",u"Salo",u"Sastamala",u"Savonlinna",u"Seinäjoki",u"Somero",u"Suonenjoki",
    u"Tampere",u"Tornio",u"Turku",u"Ulvila",u"Uusikaarlepyy",u"Uusikaupunki",u"Vaasa",
    u"Valkeakoski",u"Vantaa",u"Varkaus",u"Viitasaari",u"Virrat",u"Ylivieska",u"Ylöjärvi",
    u"Ähtäri",u"Äänekoski"
    ]

email_provders = [
    u"gmail.com", u"google.com", u"kapsi.fi", u"hotmail.com", u"company.com", u"nokia.fi",
    u"provider.org", u"freeemail.com", u"mail.ru", u"example.com", u"iki.fi", u"yahoo.com",
    u"invalid.ccom",u"aol.com",u"msn.com",u"comcast.net", u"hotmail.co.uk",u"sbcglobal.net",
    u"yahoo.co.uk",u"yahoo.co.in",u"bellsouth.net", u"verizon.net",u"earthlink.net",u"cox.net",
    u"rediffmail.com",u"yahoo.ca",u"btinternet.com",u"charter.net",u"ntlworld.com"
    ]

street_addresses = [
    u"Aittakuja",u"Ala-Topparintie",u"Alatie",u"Alhontie",u"Emännänmutka",u"Emännäntie",
    u"Hakalanrinne",u"Hakalantie",u"Hakatie",u"Hakolantie",u"Hakotie",u"Hannantie",
    u"Harjutie",u"Hauskalantie",u"Hinkankuja",u"Hollihaantie",u"Hollipolku",u"Honkatie",
    u"Huhtalantie",u"Ikolantie",u"Isonkylän",u"Isännäntie",u"Jalmarintie",u"Jukolantie",
    u"Kaanaantie",u"Kaarnatie",u"Kaarnikka",u"Kaislaranta",u"Kanervatie",u"Kanervikkopolku",
    u"Karoliinankuja",u"Katajamäentie",u"Katajatie",u"Kaukolanranta",u"Kauppakuja",
    u"Kauppilantie",u"Kauppilanvälitie",u"Kekäletie",u"Keskustie",u"Ketotie",u"Ketunmutka",
    u"Ketunpolku",u"Kiehispolku",u"Kinkorinne",u"Kinkovuorentie",u"Kirkkokankaantie",
    u"Kirkkokuja",u"Kirkkotie",u"Kivimäentie",u"Koivikontie",u"Koivuahteentie",u"Koivumäentie",
    u"Koivuniementie",u"Koivutie",u"Korpikoskentie",u"Korteelantie",u"Kotimäenpolku",
    u"Kotimäentie",u"Koulutie",u"Kuivamäentie",u"Kumurinmaanpolku",u"Kunnastie",u"Kuulankatu",
    u"Kuusimäentie",u"Kylätie",u"Kyrönmaantie",u"Kytönevantie",u"Kytötie",u"Kämppätie",u"Laaksotie",
    u"Lakiankuja",u"Larvatie",u"Lauttamuksentie",u"Lehtokuja",u"Leppätie",u"Lietniementie",
    u"Linjamanpolku",u"Louhikonmäentie",u"Lukuhaara",u"Lundintie",u"Lyytintie",u"Majatie",
    u"Malkaniementie",u"Manninkuja",u"Marttilantie",u"Matinpalontie",u"Miilutie",u"Mäkilammintie",
    u"Mäkitie",u"Mäntyniementie",u"Neulastie",u"Niementie",u"Nikkarintie",u"Notkotie",
    u"Noukanniementie",u"Ojalankuja",u"Ojalantie",u"Paavalinranta",u"Pajutie",u"Palaspolku",
    u"Papinpolku",u"Pappilanpolku",u"Peltolantie",u"Peltovainiontie",u"Perälänmäentie",
    u"Peräläntie",u"Pihapolku",u"Pihlapolku",u"Pikkusaarenmäki",u"Pikkusaarentie",u"Pitkäjärventie",
    u"Poikkisarkaantie",u"Poppelitie",u"Puimapolku",u"Rajala",u"Rannantie",u"Rantatie",
    u"Ranteentie",u"Riihelänkuja",u"Riihikalliontie",u"Riihikuja",u"Riihitie",u"Rikuntie",
    u"Rinnetie",u"Rinteentie",u"Ristimajanpolku",u"Roopelantie",u"Sanantie",u"Seinäjoentie",
    u"Siikalankuja",u"Sompinkyläntie",u"Sompintie",u"Soratie",u"Suntiontie",u"Suvantotie",
    u"Sysimetsäntie",u"Sysitie",u"Säynätsalontie",u"Tanhuantie",u"Teollisuustie",u"Teräsmäentie",
    u"Tiltantie",u"Topparintie",u"Tuomipuro",u"Tuukikuja",u"Tyynitie",u"Uimarannantie",u"Uitonkuja",
    u"Uitonsalmentie",u"Uljaantie",u"Vaasantie",u"Valkamantie",u"Varesvuontie",u"Varismäen",
    u"Varismäentie",u"Varrasjärvenpolku",u"Vehkaojantie",u"Viitalantie",u"Vuorimäentie",
    u"Välimaantie",u"Välinevantie",u"Ylistarontie",u"Yrittäjäntie",u"metsätie"
]

def random_sex():
    if random() < 0.3:
        return "f"
    else:
        return "m"

def random_first_name(sex=None):
    if sex is None:
        sex = random_sex()
    if sex is "f":
        return choice(flemale_first_names)
    else:
        return choice(male_first_names)

def random_last_name():
    return choice(last_names)

def random_municipality():
    return choice(municipalities)

def random_street():
    return choice(street_addresses)

def random_email(firstname, lastname):
    firstname = firstname.lower()
    lastname = lastname.lower()
    if random() < 0.7:
        if random() > 0.55:
            return ("%s.%s@%s" % (firstname, lastname, choice(email_provders)))
        elif random() > 0.35:
            return ("%s.%s.%s@%s" % (firstname, chr(randint(97,122)), lastname, choice(email_provders)))
        else:
            return ("%s_%s@%s" % (firstname, lastname, choice(email_provders)))
    return ("%s%s@%s" % (firstname, randint(50,99), choice(email_provders)))

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
