"""
Volledig automatisch outreach systeem voor AfspraakHost.
- Zoekt dagelijks bedrijven die online boeken kunnen gebruiken
- Haalt contactemails op via OSM + website scraping
- Stuurt gepersonaliseerde HTML cold emails
- Verstuurt follow-ups na 3 dagen
"""
import sqlite3, smtplib, requests, time, random, re, os, builtins
from datetime import datetime, timedelta

_orig_print = builtins.print
def print(*args, **kwargs):
    _orig_print(f'[{datetime.now().strftime("%H:%M:%S")}]', *args, **kwargs)
builtins.print = print

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(override=True)

def _creds():
    load_dotenv(override=True)
    return os.getenv('GMAIL_ADDRESS', ''), os.getenv('GMAIL_APP_PASSWORD', '')

GMAIL_ADDRESS  = os.getenv('GMAIL_ADDRESS', '')
GMAIL_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')
BASE_URL       = os.getenv('BASE_URL', 'https://afspraakhost-production.up.railway.app')
SENDER_NAME    = os.getenv('SENDER_NAME', 'Robin')
DB_PATH        = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outreach.db')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
}

# Booking system signatures — skip als ze al een online boeking hebben
BOOKING_SIGNATURES = [
    'calendly', 'acuityscheduling', 'bookamat', 'simplybook', 'setmore',
    'booksy', 'treatwell', 'fresha', 'planity', 'timify', 'appointy',
    'reservio', 'doctolib', 'clinicalsoftware', 'afspraakhost', 'afspraken',
    'online-boeken', 'online boeken', 'book-appointment', 'bookappointment',
]

# Niches die afspraken gebruiken
NICHES = {
    'hairdressers':     'kapsalon',
    'beauty':           'schoonheidssalon',
    'physiotherapists': 'fysiotherapeut',
    'dentists':         'tandarts',
    'massage':          'massagesalon',
    'nail salons':      'nagelstudio',
    'personal trainers':'personal trainer',
    'yoga':             'yoga studio',
    'acupuncture':      'acupunctuur',
    'psychologists':    'psycholoog',
    'dietitians':       'diëtist',
    'opticians':        'opticien',
    'podiatry':         'pedicure',
    'osteopathy':       'osteopaat',
    'veterinarians':    'dierenarts',
}
NICHE_KEYS = list(NICHES.keys())

# 200+ steden wereldwijd
STEDEN = [
    # Nederland
    'Amsterdam, Netherlands', 'Rotterdam, Netherlands', 'Den Haag, Netherlands',
    'Utrecht, Netherlands', 'Eindhoven, Netherlands', 'Groningen, Netherlands',
    'Tilburg, Netherlands', 'Almere, Netherlands', 'Breda, Netherlands',
    'Nijmegen, Netherlands', 'Haarlem, Netherlands', 'Arnhem, Netherlands',
    'Zaandam, Netherlands', 'Amersfoort, Netherlands', 'Apeldoorn, Netherlands',
    'Zwolle, Netherlands', 'Maastricht, Netherlands', 'Leiden, Netherlands',
    # Belgie
    'Antwerp, Belgium', 'Ghent, Belgium', 'Brussels, Belgium', 'Bruges, Belgium', 'Liege, Belgium',
    # VS
    'New York, NY', 'Los Angeles, CA', 'Chicago, IL', 'Houston, TX',
    'Phoenix, AZ', 'Philadelphia, PA', 'San Antonio, TX', 'San Diego, CA',
    'Dallas, TX', 'San Jose, CA', 'Austin, TX', 'Jacksonville, FL',
    'Fort Worth, TX', 'Columbus, OH', 'Indianapolis, IN', 'Charlotte, NC',
    'San Francisco, CA', 'Seattle, WA', 'Denver, CO', 'Nashville, TN',
    'Las Vegas, NV', 'Portland, OR', 'Memphis, TN', 'Louisville, KY',
    'Baltimore, MD', 'Milwaukee, WI', 'Atlanta, GA', 'Miami, FL',
    'Minneapolis, MN', 'Tampa, FL', 'Cleveland, OH', 'Orlando, FL',
    # VK
    'London, UK', 'Manchester, UK', 'Birmingham, UK', 'Leeds, UK',
    'Glasgow, UK', 'Liverpool, UK', 'Edinburgh, UK', 'Bristol, UK',
    'Sheffield, UK', 'Leicester, UK', 'Cardiff, UK',
    # Canada
    'Toronto, Canada', 'Vancouver, Canada', 'Montreal, Canada', 'Calgary, Canada',
    'Edmonton, Canada', 'Ottawa, Canada',
    # Australie
    'Sydney, Australia', 'Melbourne, Australia', 'Brisbane, Australia',
    'Perth, Australia', 'Adelaide, Australia',
    # Duitsland
    'Berlin, Germany', 'Munich, Germany', 'Hamburg, Germany', 'Cologne, Germany',
    'Frankfurt, Germany', 'Stuttgart, Germany', 'Dusseldorf, Germany', 'Leipzig, Germany',
    # Oostenrijk / Zwitserland
    'Vienna, Austria', 'Zurich, Switzerland', 'Geneva, Switzerland', 'Basel, Switzerland',
    # Spanje
    'Madrid, Spain', 'Barcelona, Spain', 'Valencia, Spain', 'Seville, Spain',
    'Zaragoza, Spain', 'Malaga, Spain',
    # Italie
    'Rome, Italy', 'Milan, Italy', 'Naples, Italy', 'Turin, Italy', 'Florence, Italy',
    # Frankrijk
    'Paris, France', 'Lyon, France', 'Marseille, France', 'Toulouse, France',
    'Nice, France', 'Bordeaux, France', 'Lille, France', 'Nantes, France',
    # Portugal
    'Lisbon, Portugal', 'Porto, Portugal', 'Braga, Portugal',
    # Ierland
    'Dublin, Ireland', 'Cork, Ireland', 'Galway, Ireland',
    # Scandinavie
    'Stockholm, Sweden', 'Oslo, Norway', 'Copenhagen, Denmark', 'Helsinki, Finland',
    # Oost-Europa
    'Warsaw, Poland', 'Prague, Czech Republic', 'Budapest, Hungary',
    'Bucharest, Romania', 'Athens, Greece',
    # Midden-Oosten
    'Dubai, UAE', 'Tel Aviv, Israel',
    # Azie
    'Singapore', 'Tokyo, Japan', 'Seoul, South Korea',
    'Bangkok, Thailand', 'Kuala Lumpur, Malaysia',
    # Latijns-Amerika
    'Mexico City, Mexico', 'Sao Paulo, Brazil', 'Buenos Aires, Argentina',
    'Bogota, Colombia', 'Lima, Peru',
    # Afrika
    'Cape Town, South Africa', 'Johannesburg, South Africa',
    # Nieuw-Zeeland
    'Auckland, New Zealand',
]

# OSM tags per niche
OSM_TAGS = {
    'hairdressers':     [('shop', 'hairdresser'), ('amenity', 'hairdresser')],
    'beauty':           [('shop', 'beauty'), ('amenity', 'beauty'), ('leisure', 'spa')],
    'physiotherapists': [('amenity', 'physiotherapist'), ('healthcare', 'physiotherapist')],
    'dentists':         [('amenity', 'dentist'), ('healthcare', 'dentist')],
    'massage':          [('amenity', 'massage'), ('shop', 'massage')],
    'nail salons':      [('shop', 'nail_salon'), ('shop', 'nails')],
    'personal trainers':[('leisure', 'fitness_centre'), ('amenity', 'gym')],
    'yoga':             [('sport', 'yoga'), ('leisure', 'yoga')],
    'acupuncture':      [('healthcare', 'acupuncture'), ('amenity', 'alternative')],
    'psychologists':    [('amenity', 'social_facility'), ('healthcare', 'psychologist')],
    'dietitians':       [('healthcare', 'dietitian'), ('amenity', 'clinic')],
    'opticians':        [('shop', 'optician'), ('healthcare', 'optometrist')],
    'podiatry':         [('healthcare', 'podiatrist'), ('amenity', 'podiatrist')],
    'osteopathy':       [('healthcare', 'osteopath'), ('amenity', 'osteopath')],
    'veterinarians':    [('amenity', 'veterinary'), ('healthcare', 'veterinary')],
}

# ── Database ────────────────────────────────────────────────
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = db()
    # Migreer van oud schema (email UNIQUE, geen url kolom) naar nieuw schema
    try:
        c.execute('SELECT url FROM leads LIMIT 1')
    except Exception:
        try:
            c.execute('ALTER TABLE leads RENAME TO leads_v1_backup')
            c.commit()
            print('[DB] Oud leads-schema geback-upt naar leads_v1_backup')
        except Exception: pass
    c.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        business_name TEXT DEFAULT '',
        email TEXT DEFAULT '',
        niche TEXT DEFAULT '',
        city TEXT DEFAULT '',
        has_booking INTEGER DEFAULT 0,
        email_sent INTEGER DEFAULT 0,
        email_sent_at TEXT,
        followup_sent INTEGER DEFAULT 0,
        followup_sent_at TEXT,
        replied INTEGER DEFAULT 0,
        converted INTEGER DEFAULT 0,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS email_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        to_email TEXT,
        subject TEXT,
        type TEXT,
        sent_at TEXT
    )''')
    try: c.execute('ALTER TABLE leads ADD COLUMN link_clicks INTEGER DEFAULT 0')
    except: pass
    c.commit(); c.close()

init_db()

_city_coords_cache = {}

def get_city_coords(city):
    if city in _city_coords_cache:
        return _city_coords_cache[city]
    try:
        r = requests.get('https://nominatim.openstreetmap.org/search',
            params={'q': city, 'format': 'json', 'limit': 1},
            headers={'User-Agent': 'AfspraakHost-Outreach/1.0 (afspraakhost.nl)'}, timeout=10)
        data = r.json()
        if data:
            coords = float(data[0]['lat']), float(data[0]['lon'])
            _city_coords_cache[city] = coords
            return coords
    except: pass
    return None, None

# ── Lead finder via OSM → website scraping ──────────────────
def search_businesses(niche, city, count=10, radius=5000):
    """Zoek bedrijven via OSM. Geeft website-URLs terug."""
    lat, lon = get_city_coords(city)
    if not lat:
        print(f'  [OSM] Geocode mislukt voor {city}')
        return []

    tag_list = OSM_TAGS.get(niche, [('shop', 'hairdresser')])
    union_parts = []
    for key, val in tag_list:
        union_parts.append(f'node["{key}"="{val}"](around:{radius},{lat},{lon});')
        union_parts.append(f'way["{key}"="{val}"](around:{radius},{lat},{lon});')
    query = f'[out:json][timeout:30];({" ".join(union_parts)});out body;'

    try:
        r = requests.post('https://overpass-api.de/api/interpreter',
            data={'data': query},
            headers={'User-Agent': 'AfspraakHost-Outreach/1.0'}, timeout=35)
        elements = r.json().get('elements', [])
    except Exception as e:
        print(f'  [OSM ERROR] {city}: {e}')
        return []

    random.shuffle(elements)
    urls = []
    for e in elements:
        if len(urls) >= count:
            break
        tags = e.get('tags', {})
        website = (tags.get('website') or tags.get('contact:website')
                   or tags.get('url') or tags.get('contact:url') or '')
        if not website:
            continue
        if not website.startswith('http'):
            website = 'https://' + website
        try:
            parsed = urlparse(website)
            base = f"{parsed.scheme}://{parsed.netloc}"
            if base not in urls and len(parsed.netloc) > 3:
                urls.append(base)
                name = tags.get('name', '?')
                try:
                    print(f'  [OSM] {name}: {base}')
                except UnicodeEncodeError:
                    print(f'  [OSM] (naam): {base}')
        except: continue

    return urls[:count]

# ── Detectie bestaand boekingssysteem ──────────────────────
def has_booking_system(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        html = r.text.lower()
        return any(sig.lower() in html for sig in BOOKING_SIGNATURES)
    except:
        return True  # bij fout: niet mailen

# ── Email scraper ───────────────────────────────────────────
def find_email(url):
    emails = set()
    pages = [url, urljoin(url, '/contact'), urljoin(url, '/over-ons'),
             urljoin(url, '/contact-us'), urljoin(url, '/kontakt')]
    for page in pages:
        try:
            r = requests.get(page, headers=HEADERS, timeout=8)
            found = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', r.text)
            for e in found:
                if not any(x in e.lower() for x in ['example', 'test', 'placeholder',
                           '@sentry', '@schema', '@w3', 'noreply', 'no-reply']):
                    emails.add(e.lower())
            if emails: break
        except:
            continue
    if emails:
        for prefix in ['info@', 'contact@', 'hallo@', 'hello@', 'afspraken@', 'boeken@']:
            for e in emails:
                if e.startswith(prefix): return e
        return sorted(emails)[0]
    return ''

# ── Business name ───────────────────────────────────────────
def get_business_name(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        og = soup.find('meta', property='og:site_name')
        if og and og.get('content'): return og['content'].strip()[:60]
        title = soup.find('title')
        if title: return title.text.split('|')[0].split('-')[0].strip()[:60]
    except: pass
    return urlparse(url).netloc.replace('www.', '').split('.')[0].capitalize()

# ── Taaldetectie ────────────────────────────────────────────
def detect_language(city: str) -> str:
    c = city.lower()
    if any(x in c for x in [
        'netherlands', 'amsterdam', 'rotterdam', 'den haag', 'utrecht', 'eindhoven',
        'groningen', 'tilburg', 'almere', 'breda', 'nijmegen', 'haarlem', 'arnhem',
        'zaandam', 'amersfoort', 'apeldoorn', 'maastricht', 'leiden', 'zwolle',
        'antwerp', 'ghent', 'bruges', 'belgium']):
        return 'nl'
    if any(x in c for x in [
        'germany', 'berlin', 'munich', 'hamburg', 'cologne', 'frankfurt', 'stuttgart',
        'dusseldorf', 'leipzig', 'austria', 'vienna', 'zurich', 'switzerland', 'basel']):
        return 'de'
    if any(x in c for x in [
        'france', 'paris', 'lyon', 'marseille', 'toulouse', 'nice', 'bordeaux',
        'lille', 'nantes', 'brussels', 'liege', 'morocco', 'geneva']):
        return 'fr'
    if any(x in c for x in [
        'spain', 'madrid', 'barcelona', 'valencia', 'seville', 'zaragoza', 'malaga',
        'mexico', 'colombia', 'bogota', 'peru', 'lima', 'argentina', 'buenos aires']):
        return 'es'
    if any(x in c for x in ['italy', 'rome', 'milan', 'naples', 'turin', 'florence']):
        return 'it'
    if any(x in c for x in ['portugal', 'lisbon', 'porto', 'braga', 'brazil', 'sao paulo']):
        return 'pt'
    return 'en'

COPY = {
    'nl': {
        'tagline':   'Online Afspraken — Volledig Automatisch',
        'greeting':  'Hallo {name},',
        'followup':  'Ik stuurde u vorige week een bericht — ik wil even controleren of het is aangekomen.',
        'intro':     'Ik bezocht <strong>{domain}</strong> en zag dat klanten nog geen afspraak online kunnen boeken.',
        'hook':      'Terwijl u dit leest, missen klanten de mogelijkheid om zelf een tijdstip te kiezen. AfspraakHost lost dat op:',
        'bullets':   ['✅&nbsp; Klanten boeken zelf een afspraak — 24/7, ook \'s avonds',
                      '✅&nbsp; U én de klant krijgen automatisch een bevestiging per e-mail',
                      '✅&nbsp; Eén regel code op uw website — binnen 2 minuten live',
                      '✅&nbsp; Zelf uw beschikbaarheid instellen per dag en tijdslot'],
        'cta':       'Bekijk een live demo',
        'price':     '<strong style="color:#333">7 dagen gratis proberen</strong> — geen creditcard nodig. Daarna slechts €54,50/maand.',
        'sign':      'Met vriendelijke groet,',
        'unsub':     'U ontvangt dit omdat uw bedrijf online vindbaar is.',
        'unsub_link':'Uitschrijven',
        'subject':   'Klanten kunnen nu geen afspraak online boeken bij {domain}',
        'subject_fu':'Nog even — online boeken voor {name}',
    },
    'en': {
        'tagline':   'Online Appointments — Fully Automated',
        'greeting':  'Hi {name},',
        'followup':  'I reached out last week and just wanted to make sure my message got through.',
        'intro':     'I visited <strong>{domain}</strong> and noticed customers can\'t book an appointment online yet.',
        'hook':      'Right now, customers who want to book are reaching for the phone — or going to a competitor. AfspraakHost fixes that:',
        'bullets':   ['✅&nbsp; Customers book their own time slot — 24/7, even late at night',
                      '✅&nbsp; You and the customer both get an automatic confirmation email',
                      '✅&nbsp; One line of code on your site — live in under 2 minutes',
                      '✅&nbsp; Set your own availability by day and time slot'],
        'cta':       'See a live demo',
        'price':     '<strong style="color:#333">7-day free trial</strong> — no credit card needed. Then just €54.50/month.',
        'sign':      'Best regards,',
        'unsub':     'You received this because your business is publicly listed online.',
        'unsub_link':'Unsubscribe',
        'subject':   'Your customers can\'t book an appointment online yet',
        'subject_fu':'Following up about online booking for {name}',
    },
    'de': {
        'tagline':   'Online-Termine — Vollautomatisch',
        'greeting':  'Guten Tag,',
        'followup':  'Letzte Woche habe ich Ihnen eine Nachricht geschickt — ich wollte sicherstellen, dass sie angekommen ist.',
        'intro':     'Ich habe <strong>{domain}</strong> besucht und festgestellt, dass Kunden noch keine Termine online buchen können.',
        'hook':      'Im Moment greifen buchungswillige Kunden zum Telefon — oder gehen zur Konkurrenz. AfspraakHost löst das:',
        'bullets':   ['✅&nbsp; Kunden buchen selbst einen Termin — 24/7, auch abends',
                      '✅&nbsp; Sie und der Kunde erhalten automatisch eine Bestätigungs-E-Mail',
                      '✅&nbsp; Eine Zeile Code auf Ihrer Website — in unter 2 Minuten live',
                      '✅&nbsp; Eigene Verfügbarkeit nach Tag und Zeitfenster festlegen'],
        'cta':       'Live-Demo ansehen',
        'price':     '<strong style="color:#333">7 Tage kostenlos testen</strong> — keine Kreditkarte erforderlich. Danach nur €54,50/Monat.',
        'sign':      'Mit freundlichen Grüßen,',
        'unsub':     'Sie erhalten diese E-Mail, weil Ihr Unternehmen öffentlich online gelistet ist.',
        'unsub_link':'Abmelden',
        'subject':   'Kunden können noch keine Termine bei {domain} online buchen',
        'subject_fu':'Nachfrage wegen Online-Buchung für {name}',
    },
    'fr': {
        'tagline':   'Rendez-vous en ligne — Entièrement automatisé',
        'greeting':  'Bonjour {name},',
        'followup':  'Je vous ai contacté la semaine dernière et voulais m\'assurer que mon message vous est bien parvenu.',
        'intro':     'J\'ai visité <strong>{domain}</strong> et remarqué que les clients ne peuvent pas encore prendre rendez-vous en ligne.',
        'hook':      'En ce moment, les clients qui veulent réserver décrochent le téléphone — ou vont chez un concurrent. AfspraakHost résout cela :',
        'bullets':   ['✅&nbsp; Les clients réservent eux-mêmes un créneau — 24h/24, même le soir',
                      '✅&nbsp; Vous et le client recevez automatiquement un e-mail de confirmation',
                      '✅&nbsp; Une ligne de code sur votre site — en ligne en moins de 2 minutes',
                      '✅&nbsp; Définissez vos disponibilités par jour et créneau horaire'],
        'cta':       'Voir une démo en direct',
        'price':     '<strong style="color:#333">7 jours gratuits</strong> — sans carte bancaire. Ensuite seulement 54,50 €/mois.',
        'sign':      'Cordialement,',
        'unsub':     'Vous recevez ceci car votre entreprise est répertoriée en ligne.',
        'unsub_link':'Se désabonner',
        'subject':   'Vos clients ne peuvent pas encore réserver en ligne sur {domain}',
        'subject_fu':'Suivi — réservation en ligne pour {name}',
    },
    'es': {
        'tagline':   'Citas en línea — Totalmente automatizado',
        'greeting':  'Hola {name},',
        'followup':  'Le contacté la semana pasada y quería asegurarme de que mi mensaje le llegó.',
        'intro':     'Visité <strong>{domain}</strong> y noté que los clientes aún no pueden reservar una cita en línea.',
        'hook':      'Ahora mismo, los clientes que quieren reservar llaman por teléfono — o van a la competencia. AfspraakHost lo soluciona:',
        'bullets':   ['✅&nbsp; Los clientes reservan su propio horario — 24/7, incluso por la noche',
                      '✅&nbsp; Usted y el cliente reciben automáticamente un e-mail de confirmación',
                      '✅&nbsp; Una línea de código en su sitio — activo en menos de 2 minutos',
                      '✅&nbsp; Configure su disponibilidad por día y franja horaria'],
        'cta':       'Ver una demo en vivo',
        'price':     '<strong style="color:#333">7 días gratis</strong> — sin tarjeta de crédito. Después solo 54,50 €/mes.',
        'sign':      'Saludos cordiales,',
        'unsub':     'Recibe esto porque su empresa está listada públicamente en línea.',
        'unsub_link':'Darse de baja',
        'subject':   'Sus clientes aún no pueden reservar citas en línea en {domain}',
        'subject_fu':'Seguimiento — reserva en línea para {name}',
    },
    'it': {
        'tagline':   'Appuntamenti online — Completamente automatizzato',
        'greeting':  'Buongiorno {name},',
        'followup':  'La scorsa settimana le ho inviato un messaggio e volevo assicurarmi che fosse arrivato.',
        'intro':     'Ho visitato <strong>{domain}</strong> e ho notato che i clienti non possono ancora prenotare un appuntamento online.',
        'hook':      'In questo momento, i clienti che vogliono prenotare chiamano al telefono — o si rivolgono alla concorrenza. AfspraakHost risolve il problema:',
        'bullets':   ['✅&nbsp; I clienti prenotano il proprio orario — 24/7, anche la sera',
                      '✅&nbsp; Lei e il cliente ricevono automaticamente un\'e-mail di conferma',
                      '✅&nbsp; Una riga di codice sul sito — attivo in meno di 2 minuti',
                      '✅&nbsp; Imposti la sua disponibilità per giorno e fascia oraria'],
        'cta':       'Guarda una demo live',
        'price':     '<strong style="color:#333">7 giorni gratuiti</strong> — nessuna carta di credito. Poi solo €54,50/mese.',
        'sign':      'Cordiali saluti,',
        'unsub':     'Riceve questa e-mail perché la sua azienda è elencata pubblicamente online.',
        'unsub_link':'Annulla iscrizione',
        'subject':   'I suoi clienti non possono ancora prenotare online su {domain}',
        'subject_fu':'Aggiornamento — prenotazione online per {name}',
    },
    'pt': {
        'tagline':   'Marcações online — Totalmente automatizado',
        'greeting':  'Olá {name},',
        'followup':  'Entrei em contacto na semana passada e queria garantir que a minha mensagem chegou.',
        'intro':     'Visitei <strong>{domain}</strong> e reparei que os clientes ainda não podem marcar uma consulta online.',
        'hook':      'Neste momento, os clientes que querem marcar ligam para o telefone — ou vão a um concorrente. AfspraakHost resolve isso:',
        'bullets':   ['✅&nbsp; Os clientes marcam o seu próprio horário — 24/7, mesmo à noite',
                      '✅&nbsp; Você e o cliente recebem automaticamente um e-mail de confirmação',
                      '✅&nbsp; Uma linha de código no seu site — ativo em menos de 2 minutos',
                      '✅&nbsp; Defina a sua disponibilidade por dia e horário'],
        'cta':       'Ver uma demo ao vivo',
        'price':     '<strong style="color:#333">7 dias gratuitos</strong> — sem cartão de crédito. Depois apenas €54,50/mês.',
        'sign':      'Com os melhores cumprimentos,',
        'unsub':     'Recebe isto porque o seu negócio está listado publicamente online.',
        'unsub_link':'Cancelar subscrição',
        'subject':   'Os seus clientes ainda não podem marcar online em {domain}',
        'subject_fu':'Seguimento — marcações online para {name}',
    },
}

def email_html(name, url, follow_up=False, city='', to_email='', lead_id=''):
    lang   = detect_language(city)
    t      = COPY[lang]
    domain = urlparse(url).netloc.replace('www.', '')
    clean_name = name if name and name.lower() not in ('there', '', '-') else ''

    subject = (t['subject_fu'].format(name=clean_name or domain)
               if follow_up else t['subject'].format(domain=domain, name=clean_name or domain))
    greeting = t['greeting'].format(name=clean_name) if clean_name else t['greeting'].format(name='')
    greeting = greeting.strip().rstrip(',').strip() + ',' if not clean_name and '{name}' in t['greeting'] else greeting

    followup_html = (f'<p style="margin:0 0 16px;font-size:15px;color:#333">{t["followup"]}</p>'
                     if follow_up else '')
    bullets_html = ''.join(f'<tr><td style="padding:8px 0;font-size:14px;color:#555">{b}</td></tr>'
                            for b in t['bullets'])

    body = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:30px 10px">
<table width="580" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 20px rgba(0,0,0,.08)">
<tr><td style="background:linear-gradient(135deg,#10b981,#059669);padding:30px 40px">
  <h1 style="color:#fff;margin:0;font-size:22px">AfspraakHost</h1>
  <p style="color:rgba(255,255,255,.7);margin:6px 0 0;font-size:13px">{t['tagline']}</p>
</td></tr>
<tr><td style="padding:36px 40px">
  <p style="margin:0 0 16px;font-size:15px;color:#333">{greeting}</p>
  {followup_html}
  <p style="margin:0 0 16px;font-size:15px;color:#333">{t['intro'].format(domain=domain)}</p>
  <p style="font-size:15px;color:#333;margin:0 0 20px">{t['hook']}</p>
  <table style="margin:0 0 24px;width:100%">{bullets_html}</table>
  <table cellpadding="0" cellspacing="0" style="margin:0 auto 28px"><tr>
    <td style="background:linear-gradient(135deg,#10b981,#059669);border-radius:8px;padding:14px 32px">
      <a href="{BASE_URL}/track/click?lid={lead_id}&ref={domain}" style="color:#fff;text-decoration:none;font-size:15px;font-weight:700">{t['cta']}</a>
    </td>
  </tr></table>
  <p style="font-size:14px;color:#888;margin:0 0 6px">{t['price']}</p>
  <p style="font-size:15px;color:#333;margin:20px 0 0">{t['sign']}<br><strong>{SENDER_NAME}</strong><br>
  <span style="color:#888;font-size:13px">AfspraakHost — <a href="{BASE_URL}" style="color:#10b981">{BASE_URL.replace('https://','').replace('http://','')}</a></span></p>
</td></tr>
<tr><td style="padding:16px 40px;border-top:1px solid #eee">
  <p style="font-size:11px;color:#aaa;margin:0">{t['unsub']}
    <a href="{BASE_URL}/unsubscribe?email={to_email}" style="color:#aaa">{t['unsub_link']}</a>
  </p>
</td></tr>
</table></td></tr></table>
</body></html>"""
    return subject, body

# ── Email verzenden ─────────────────────────────────────────
def send_email(to_email, business_name, url, follow_up=False, city='', lead_id=''):
    gmail, pwd = _creds()
    if not gmail or not pwd:
        print('[MAIL] Geen Gmail credentials in .env')
        return False
    sender = os.getenv('SENDER_NAME', 'Robin')
    try:
        subject, html = email_html(business_name, url, follow_up, city=city, to_email=to_email, lead_id=lead_id)
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f'{sender} <{gmail}>'
        msg['To']      = to_email
        msg['Reply-To']= gmail
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(gmail, pwd)
            s.sendmail(gmail, to_email, msg.as_string())
        print(f'[MAIL ✓] {to_email} — {business_name}')
        return True
    except Exception as e:
        print(f'[MAIL ✗] {to_email} — {e}')
        return False

# ── Pipeline ────────────────────────────────────────────────
def find_and_queue_leads(niche=None, city=None, count=10):
    niche_key  = niche if niche in NICHES else random.choice(NICHE_KEYS)
    niche_name = NICHES.get(niche_key, niche_key)
    city       = city or random.choice(STEDEN)
    print(f'\n[FINDER] {niche_name} in {city}...')
    urls = search_businesses(niche_key, city, count)
    new_leads = 0
    c = db()
    for url in urls:
        existing = c.execute('SELECT id FROM leads WHERE url=?', (url,)).fetchone()
        if existing: continue
        time.sleep(random.uniform(1.5, 3.0))
        booking = has_booking_system(url)
        if booking:
            print(f'  [SKIP] {url} — al een boekingssysteem')
            c.execute('INSERT OR IGNORE INTO leads (url,niche,city,has_booking,created_at) VALUES (?,?,?,1,?)',
                (url, niche_name, city, datetime.now().isoformat()))
            c.commit()
            continue
        email = find_email(url)
        name  = get_business_name(url)
        print(f'  [LEAD] {url} | {name} | {email or "geen email"}')
        c.execute('''INSERT OR IGNORE INTO leads
            (url,business_name,email,niche,city,has_booking,created_at)
            VALUES (?,?,?,?,?,0,?)''',
            (url, name, email, niche_name, city, datetime.now().isoformat()))
        c.commit()
        if email: new_leads += 1
    c.close()
    print(f'[FINDER] {new_leads} nieuwe leads met email in {city}')
    return new_leads

def send_cold_emails(max_per_day=200):
    c = db()
    leads = c.execute('''SELECT * FROM leads
        WHERE email != '' AND email_sent=0 AND has_booking=0
        AND email LIKE '%@%.%'
        AND email NOT LIKE '%.png%' AND email NOT LIKE '%.jpg%'
        AND email NOT LIKE '%.gif%' AND email NOT LIKE '%.svg%'
        AND LENGTH(email) <= 100
        ORDER BY created_at ASC LIMIT ?''', (max_per_day,)).fetchall()
    sent = 0
    for lead in leads:
        lang = detect_language(lead['city'] or '')
        if send_email(lead['email'], lead['business_name'] or '', lead['url'], city=lead['city'] or '', lead_id=lead['id']):
            c.execute('UPDATE leads SET email_sent=1, email_sent_at=? WHERE id=?',
                (datetime.now().isoformat(), lead['id']))
            c.execute('INSERT INTO email_log (lead_id,to_email,subject,type,sent_at) VALUES (?,?,?,?,?)',
                (lead['id'], lead['email'], f'Cold [{lang}]', 'cold', datetime.now().isoformat()))
            c.commit()
            sent += 1
            time.sleep(random.uniform(30, 90))
    c.close()
    print(f'[MAILER] {sent} cold emails verstuurd')
    return sent

def send_followups():
    cutoff = (datetime.now() - timedelta(days=3)).isoformat()
    c = db()
    leads = c.execute('''SELECT * FROM leads
        WHERE email_sent=1 AND followup_sent=0 AND replied=0
        AND email_sent_at < ? AND email != ''
        LIMIT 50''', (cutoff,)).fetchall()
    sent = 0
    for lead in leads:
        lang = detect_language(lead['city'] or '')
        if send_email(lead['email'], lead['business_name'] or '', lead['url'],
                      follow_up=True, city=lead['city'] or '', lead_id=lead['id']):
            c.execute('UPDATE leads SET followup_sent=1, followup_sent_at=? WHERE id=?',
                (datetime.now().isoformat(), lead['id']))
            c.execute('INSERT INTO email_log (lead_id,to_email,subject,type,sent_at) VALUES (?,?,?,?,?)',
                (lead['id'], lead['email'], f'Follow-up [{lang}]', 'followup', datetime.now().isoformat()))
            c.commit()
            sent += 1
            time.sleep(random.uniform(30, 90))
    c.close()
    print(f'[FOLLOWUP] {sent} follow-ups verstuurd')
    return sent

def get_stats():
    c = db()
    total    = c.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
    no_book  = c.execute('SELECT COUNT(*) FROM leads WHERE has_booking=0').fetchone()[0]
    emailed  = c.execute('SELECT COUNT(*) FROM leads WHERE email_sent=1').fetchone()[0]
    replied  = c.execute('SELECT COUNT(*) FROM leads WHERE replied=1').fetchone()[0]
    converted= c.execute('SELECT COUNT(*) FROM leads WHERE converted=1').fetchone()[0]
    today    = datetime.now().strftime('%Y-%m-%d')
    today_sent = c.execute("SELECT COUNT(*) FROM email_log WHERE sent_at LIKE ?", (today+'%',)).fetchone()[0]
    try:
        cc = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'customers.db'))
        active = cc.execute('SELECT COUNT(*) FROM customers WHERE active=1').fetchone()[0]
        mrr    = active * 54.5
        cc.close()
    except: active=0; mrr=0
    c.close()
    return {
        'leads_total': total, 'leads_no_booking': no_book,
        'emails_sent': emailed, 'emails_today': today_sent,
        'replies': replied, 'converted': converted,
        'active_customers': active, 'mrr': mrr,
    }

def daily_run():
    print(f'\n[AUTO] Run gestart: {datetime.now().strftime("%d/%m/%Y %H:%M")}')
    cities_today = random.sample(STEDEN, min(50, len(STEDEN)))
    niches_today = random.sample(NICHE_KEYS, min(15, len(NICHE_KEYS)))
    print(f'[AUTO] {len(cities_today)} steden × {len(niches_today)} niches')
    for i, city in enumerate(cities_today):
        niche = niches_today[i % len(niches_today)]
        find_and_queue_leads(niche=niche, city=city, count=20)
        time.sleep(random.uniform(2, 4))
    send_cold_emails(max_per_day=200)
    send_followups()
    s = get_stats()
    print(f'\n[RAPPORT] Leads: {s["leads_no_booking"]} zonder booking | '
          f'Gemaild: {s["emails_sent"]} | Klanten: {s["active_customers"]} | MRR: €{s["mrr"]}')
    return s

if __name__ == '__main__':
    daily_run()
