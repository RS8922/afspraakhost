import builtins, sqlite3, smtplib, os, time, random, requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

_print = builtins.print
def print(*args, **kwargs):
    _print(f'[{datetime.now().strftime("%H:%M:%S")}]', *args, **kwargs)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outreach.db')
BASE_URL = os.getenv('BASE_URL', 'https://afspraakhost-production.up.railway.app')

CITIES = [
    'Amsterdam','Rotterdam','Den Haag','Utrecht','Eindhoven','Groningen','Tilburg','Almere',
    'Breda','Nijmegen','Enschede','Haarlem','Arnhem','Zaandam','Amersfoort','Apeldoorn',
    'Zwolle','Maastricht','Leiden','Dordrecht','Antwerp','Ghent','Brussels','Liege','Bruges',
    'London','Birmingham','Manchester','Leeds','Glasgow','Liverpool','Bristol','Sheffield',
    'Berlin','Hamburg','Munich','Cologne','Frankfurt','Stuttgart','Düsseldorf','Leipzig',
    'Paris','Lyon','Marseille','Toulouse','Nice','Bordeaux','Lille','Nantes',
    'Madrid','Barcelona','Valencia','Seville','Zaragoza','Málaga','Murcia','Palma',
    'Rome','Milan','Naples','Turin','Palermo','Genoa','Bologna','Florence',
    'Lisbon','Porto','Braga','Coimbra','Faro',
    'Vienna','Zurich','Geneva','Basel','Graz',
]

NICHES = [
    'kapsalon','schoonheidssalon','massagesalon','tandarts','fysiotherapeut',
    'nagelstudio','pedicure','osteopaat','personal trainer','yoga studio',
    'acupunctuur','huidtherapeut','logopedist','diëtist','psycholoog',
]

COPY = {
    'nl': {
        'subject': 'Klanten laten 24/7 zelf een afspraak boeken — {business}',
        'body': '''Hallo,

Ik zag dat {business} actief is op Google Maps — daarom stuur ik dit bericht.

Veel bedrijven missen afspraken omdat klanten bellen terwijl je bezig bent, of laat op de avond willen boeken.

AfspraakHost lost dat op: klanten boeken zelf een tijdstip via je website. Automatisch. 24/7.

✓ Widget in 2 minuten op je site
✓ Automatische bevestigingsmail naar jou én de klant
✓ 7 dagen gratis proberen — geen creditcard nodig
✓ Daarna €54,50/maand

Gratis starten: {url}

Met vriendelijke groet,
AfspraakHost
''',
        'price': '7 dagen gratis, daarna €54,50/maand',
    },
    'en': {
        'subject': 'Let customers book appointments 24/7 — {business}',
        'body': '''Hi,

I noticed {business} on Google Maps — that's why I'm reaching out.

Many businesses miss appointments because customers call when you're busy, or want to book late at night.

AfspraakHost fixes that: customers book their own time slot directly on your website. Automatically. 24/7.

✓ Widget live in 2 minutes
✓ Automatic confirmation email to you and the customer
✓ 7-day free trial — no credit card needed
✓ Then €54.50/month

Start free: {url}

Best regards,
AfspraakHost
''',
        'price': '7-day free trial, then €54.50/month',
    },
    'de': {
        'subject': 'Kunden buchen 24/7 selbst Termine — {business}',
        'body': '''Hallo,

Ich habe {business} auf Google Maps entdeckt — deshalb schreibe ich Ihnen.

Viele Unternehmen verpassen Termine, weil Kunden anrufen, wenn man beschäftigt ist, oder spät abends buchen möchten.

AfspraakHost löst das: Kunden buchen selbst einen Termin über Ihre Website. Automatisch. 24/7.

✓ Widget in 2 Minuten auf Ihrer Website
✓ Automatische Bestätigungs-E-Mail an Sie und den Kunden
✓ 7 Tage kostenlos testen — keine Kreditkarte nötig
✓ Danach €54,50/Monat

Kostenlos starten: {url}

Mit freundlichen Grüßen,
AfspraakHost
''',
        'price': '7 Tage kostenlos, danach €54,50/Monat',
    },
    'fr': {
        'subject': 'Laissez vos clients prendre rendez-vous 24h/24 — {business}',
        'body': '''Bonjour,

J'ai trouvé {business} sur Google Maps — c'est pourquoi je vous contacte.

Beaucoup d'entreprises manquent des rendez-vous parce que les clients appellent pendant qu'on est occupé, ou souhaitent réserver tard le soir.

AfspraakHost résout cela: les clients réservent eux-mêmes un créneau sur votre site. Automatiquement. 24h/24.

✓ Widget en ligne en 2 minutes
✓ E-mail de confirmation automatique pour vous et le client
✓ 7 jours d'essai gratuit — sans carte bancaire
✓ Ensuite €54,50/mois

Commencer gratuitement: {url}

Cordialement,
AfspraakHost
''',
        'price': '7 jours gratuits, ensuite €54,50/mois',
    },
    'es': {
        'subject': 'Deje que sus clientes reserven citas 24/7 — {business}',
        'body': '''Hola,

Encontré {business} en Google Maps — por eso me pongo en contacto.

Muchas empresas pierden citas porque los clientes llaman cuando están ocupados, o quieren reservar tarde por la noche.

AfspraakHost soluciona esto: los clientes reservan su propio horario directamente en su sitio web. Automáticamente. 24/7.

✓ Widget en su web en 2 minutos
✓ Email de confirmación automático para usted y el cliente
✓ 7 días de prueba gratuita — sin tarjeta de crédito
✓ Luego €54,50/mes

Empezar gratis: {url}

Saludos,
AfspraakHost
''',
        'price': '7 días gratis, luego €54,50/mes',
    },
    'it': {
        'subject': 'Lascia che i clienti prenotino appuntamenti 24/7 — {business}',
        'body': '''Salve,

Ho trovato {business} su Google Maps — per questo mi metto in contatto.

Molte aziende perdono appuntamenti perché i clienti chiamano mentre si è occupati, o vogliono prenotare tardi la sera.

AfspraakHost risolve questo: i clienti prenotano il proprio orario direttamente sul tuo sito. Automaticamente. 24/7.

✓ Widget online in 2 minuti
✓ Email di conferma automatica per te e il cliente
✓ 7 giorni di prova gratuita — nessuna carta di credito
✓ Poi €54,50/mese

Inizia gratis: {url}

Cordiali saluti,
AfspraakHost
''',
        'price': '7 giorni gratis, poi €54,50/mese',
    },
    'pt': {
        'subject': 'Deixe os clientes marcar consultas 24/7 — {business}',
        'body': '''Olá,

Encontrei {business} no Google Maps — por isso estou a entrar em contacto.

Muitas empresas perdem marcações porque os clientes ligam quando estão ocupados, ou querem marcar tarde à noite.

AfspraakHost resolve isso: os clientes marcam o seu próprio horário diretamente no seu site. Automaticamente. 24/7.

✓ Widget no seu site em 2 minutos
✓ Email de confirmação automático para si e para o cliente
✓ 7 dias de teste gratuito — sem cartão de crédito
✓ Depois €54,50/mês

Começar grátis: {url}

Com os melhores cumprimentos,
AfspraakHost
''',
        'price': '7 dias grátis, depois €54,50/mês',
    },
}

CITY_LANG = {
    'Amsterdam':'nl','Rotterdam':'nl','Den Haag':'nl','Utrecht':'nl','Eindhoven':'nl',
    'Groningen':'nl','Tilburg':'nl','Almere':'nl','Breda':'nl','Nijmegen':'nl',
    'Enschede':'nl','Haarlem':'nl','Arnhem':'nl','Zaandam':'nl','Amersfoort':'nl','Apeldoorn':'nl',
    'Zwolle':'nl','Maastricht':'nl','Leiden':'nl','Dordrecht':'nl',
    'Antwerp':'nl','Ghent':'nl','Brussels':'nl','Liege':'fr','Bruges':'nl',
    'London':'en','Birmingham':'en','Manchester':'en','Leeds':'en','Glasgow':'en',
    'Liverpool':'en','Bristol':'en','Sheffield':'en',
    'Berlin':'de','Hamburg':'de','Munich':'de','Cologne':'de','Frankfurt':'de',
    'Stuttgart':'de','Düsseldorf':'de','Leipzig':'de',
    'Paris':'fr','Lyon':'fr','Marseille':'fr','Toulouse':'fr','Nice':'fr',
    'Bordeaux':'fr','Lille':'fr','Nantes':'fr',
    'Madrid':'es','Barcelona':'es','Valencia':'es','Seville':'es','Zaragoza':'es',
    'Málaga':'es','Murcia':'es','Palma':'es',
    'Rome':'it','Milan':'it','Naples':'it','Turin':'it','Palermo':'it',
    'Genoa':'it','Bologna':'it','Florence':'it',
    'Lisbon':'pt','Porto':'pt','Braga':'pt','Coimbra':'pt','Faro':'pt',
    'Vienna':'de','Zurich':'de','Geneva':'fr','Basel':'de','Graz':'de',
}

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = db()
    c.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, city TEXT, niche TEXT,
        sent INTEGER DEFAULT 0, sent_at TEXT, created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_at TEXT, leads_found INTEGER, emails_sent INTEGER
    )''')
    c.commit(); c.close()

def search_businesses(city, niche, limit=30):
    query   = f'{niche} {city}'
    url     = 'https://overpass-api.de/api/interpreter'
    payload = f'''[out:json][timeout:25];
area["name"="{city}"]->.a;
(node["name"]["email"](area.a);
 way["name"]["email"](area.a););
out center {limit};'''
    try:
        r = requests.post(url, data=payload, timeout=30)
        elements = r.json().get('elements', [])
        results = []
        for el in elements:
            tags  = el.get('tags', {})
            name  = tags.get('name', '')
            email = tags.get('email', '')
            if name and email and '@' in email:
                results.append({'name': name, 'email': email})
        return results
    except Exception as e:
        print(f'[OSM ERROR] {city}/{niche}: {e}')
        return []

def send_email(to_email, business_name, lang):
    gmail = os.getenv('GMAIL_ADDRESS', '')
    pwd   = os.getenv('GMAIL_APP_PASSWORD', '')
    if not gmail or not pwd:
        return False
    copy = COPY.get(lang, COPY['en'])
    url  = BASE_URL
    body = copy['body'].format(business=business_name, url=url)
    subj = copy['subject'].format(business=business_name)
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subj
    msg['From']    = gmail
    msg['To']      = to_email
    msg['List-Unsubscribe'] = f'<{BASE_URL}/unsubscribe?email={to_email}>'
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(gmail, pwd)
            s.sendmail(gmail, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f'[EMAIL ERROR] {to_email}: {e}')
        return False

def get_stats():
    try:
        cust_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'customers.db')
        c = sqlite3.connect(cust_db)
        active = c.execute('SELECT COUNT(*) FROM customers WHERE active=1').fetchone()[0]
        total  = c.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
        c.close()
        mrr = active * 54.5
        return {'active': active, 'total': total, 'mrr': mrr}
    except:
        return {'active': 0, 'total': 0, 'mrr': 0}

def daily_run():
    init_db()
    print('=== AfspraakHost Outreach gestart ===')
    s = get_stats()
    print(f'Klanten: {s["active"]} actief / {s["total"]} totaal | MRR: €{s["mrr"]:.2f}')
    c = db()
    cities  = random.sample(CITIES, min(50, len(CITIES)))
    niches  = random.sample(NICHES, min(15, len(NICHES)))
    found   = 0
    sent    = 0
    max_emails = 300
    for city in cities:
        if sent >= max_emails: break
        for niche in niches:
            if sent >= max_emails: break
            businesses = search_businesses(city, niche, limit=30)
            for biz in businesses:
                if sent >= max_emails: break
                email = biz['email'].lower().strip()
                name  = biz['name']
                existing = c.execute('SELECT id, sent FROM leads WHERE email=?', (email,)).fetchone()
                if existing:
                    continue
                c.execute('INSERT INTO leads (name,email,city,niche,created_at) VALUES (?,?,?,?,?)',
                          (name, email, city, niche, datetime.now().isoformat()))
                c.commit()
                found += 1
                lang = CITY_LANG.get(city, 'en')
                time.sleep(random.uniform(1.5, 3.5))
                if send_email(email, name, lang):
                    c.execute('UPDATE leads SET sent=1, sent_at=? WHERE email=?',
                              (datetime.now().isoformat(), email))
                    c.commit()
                    sent += 1
                    print(f'[{sent}] {name} | {city} | {lang} | {email}')
    c.execute('INSERT INTO stats (run_at,leads_found,emails_sent) VALUES (?,?,?)',
              (datetime.now().isoformat(), found, sent))
    c.commit(); c.close()
    s2 = get_stats()
    print(f'=== Klaar: {found} leads gevonden, {sent} emails verstuurd ===')
    print(f'=== Klanten: {s2["active"]} actief | MRR: €{s2["mrr"]:.2f} ===')

if __name__ == '__main__':
    daily_run()
