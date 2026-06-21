from flask import Flask, request, jsonify, send_from_directory, redirect
from html import escape as html_escape
import os, uuid, sqlite3, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

app      = Flask(__name__, static_folder='static')
ADMIN_KEY    = os.getenv('ADMIN_KEY', 'jarvis-admin-2024')
BASE_URL     = os.getenv('BASE_URL', 'https://afspraakhost-production.up.railway.app')
OUTREACH_DB  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outreach.db')

# â”€â”€ Database â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def db():
    conn = sqlite3.connect('customers.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = db()
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        api_key TEXT UNIQUE NOT NULL,
        active INTEGER DEFAULT 0,
        trial_ends_at TEXT,
        business_name TEXT DEFAULT '',
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        customer_phone TEXT DEFAULT '',
        service TEXT DEFAULT '',
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        note TEXT DEFAULT '',
        status TEXT DEFAULT 'confirmed',
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key TEXT NOT NULL,
        weekday INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        slot_duration INTEGER DEFAULT 60
    )''')
    try: c.execute('ALTER TABLE customers ADD COLUMN trial_ends_at TEXT')
    except: pass
    try: c.execute('ALTER TABLE customers ADD COLUMN email_clicked INTEGER DEFAULT 0')
    except: pass
    try: c.execute('ALTER TABLE customers ADD COLUMN email_clicked_at TEXT')
    except: pass
    c.commit(); c.close()

init_db()

# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_customer(api_key):
    c = db()
    row = c.execute('SELECT * FROM customers WHERE api_key=?', (api_key,)).fetchone()
    if not row:
        c.close(); return None
    cust = dict(row)
    if cust.get('trial_ends_at') and cust['active'] and datetime.now().isoformat() > cust['trial_ends_at']:
        c.execute('UPDATE customers SET active=0 WHERE api_key=?', (api_key,))
        c.commit(); cust['active'] = 0
    c.close()
    return cust

def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.headers.get('X-Admin-Key') != ADMIN_KEY and request.args.get('admin_key') != ADMIN_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return wrapper

def send_welcome_email(email, api_key, business_name, trial=False):
    gmail = os.getenv('GMAIL_ADDRESS', '')
    pwd   = os.getenv('GMAIL_APP_PASSWORD', '')
    if not gmail or not pwd: return
    trial_end = (datetime.now() + timedelta(days=7)).strftime('%d-%m-%Y')
    trial_block = f"""
    <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:16px;margin:16px 0">
      <strong>Je hebt 7 dagen gratis toegang tot en met {trial_end}.</strong><br>
      <span style="font-size:13px;color:#666">Daarna: â‚¬20,00/maand via bankoverschrijving (zie onderaan).</span>
    </div>""" if trial else ''
    iban_block = """
    <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
    <p style="font-size:13px;color:#888"><strong>Na je proefperiode doorgaan?</strong><br>
    Maak â‚¬20,00 over met je e-mailadres als omschrijving:<br>
    <strong>IBAN: NL26 REVO 1741 4708 03</strong> Â· R. Spronken<br>
    Je account blijft dan actief.</p>""" if trial else ''
    body = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#333">
  <div style="background:linear-gradient(135deg,#10b981,#059669);padding:32px;border-radius:12px 12px 0 0;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:28px">Welkom bij AfspraakHost!</h1>
    <p style="color:rgba(255,255,255,.8);margin:8px 0 0;font-size:15px">Je online boekingssysteem staat klaar</p>
  </div>
  <div style="background:#f9f9f9;padding:32px;border-radius:0 0 12px 12px">
    <p>Hallo{' ' + business_name if business_name else ''},</p>
    {trial_block}
    <p style="margin-top:12px">Open je dashboard om je beschikbaarheid in te stellen en de widget op je website te plaatsen:</p>
    <div style="text-align:center;margin:24px 0">
      <a href="{BASE_URL}/track/click?key={api_key}" style="background:linear-gradient(135deg,#10b981,#059669);color:#fff;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:700;font-size:15px">Open mijn dashboard</a>
    </div>
    {iban_block}
    <p style="color:#888;font-size:13px;margin-top:20px">Vragen? Mail naar spronken1234@gmail.com</p>
  </div>
</div>"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Je AfspraakHost proefperiode is gestart!' if trial else 'Je AfspraakHost account is geactiveerd!'
    msg['From']    = f'{os.getenv("SENDER_NAME", "Robin")} <{gmail}>'
    msg['To']      = email
    msg.attach(MIMEText(body, 'html'))
    import threading
    def _send():
        for attempt in range(3):
            try:
                try:
                    with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as s:
                        s.ehlo(); s.starttls(); s.ehlo()
                        s.login(gmail, pwd)
                        s.sendmail(gmail, email, msg.as_string())
                        print(f'[EMAIL OK] {email}'); return
                except Exception:
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as s:
                        s.login(gmail, pwd)
                        s.sendmail(gmail, email, msg.as_string())
                        print(f'[EMAIL OK] {email}'); return
            except Exception as e:
                import time; time.sleep(2)
        print(f'[EMAIL FAIL] {email}')
    threading.Thread(target=_send, daemon=True).start()

def send_appointment_email(business_email, customer_name, customer_email, date, time, service, business_name, api_key):
    gmail = os.getenv('GMAIL_ADDRESS', '')
    pwd   = os.getenv('GMAIL_APP_PASSWORD', '')
    if not gmail or not pwd: return
    # Email to business
    body_biz = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#333">
  <div style="background:linear-gradient(135deg,#10b981,#059669);padding:24px;border-radius:12px 12px 0 0">
    <h2 style="color:#fff;margin:0">Nieuwe afspraak!</h2>
  </div>
  <div style="background:#f9f9f9;padding:24px;border-radius:0 0 12px 12px">
    <p><strong>Klant:</strong> {customer_name}</p>
    <p><strong>Email:</strong> {customer_email}</p>
    <p><strong>Dienst:</strong> {service or 'â€”'}</p>
    <p><strong>Datum:</strong> {date}</p>
    <p><strong>Tijd:</strong> {time}</p>
    <p style="margin-top:16px"><a href="{BASE_URL}/dashboard?key={api_key}" style="color:#10b981">Bekijk in dashboard â†’</a></p>
  </div>
</div>"""
    msg_biz = MIMEMultipart('alternative')
    msg_biz['Subject'] = f'Nieuwe afspraak â€” {customer_name} op {date} om {time}'
    msg_biz['From']    = f'{os.getenv("SENDER_NAME", "Robin")} <{gmail}>'
    msg_biz['To']      = business_email
    msg_biz.attach(MIMEText(body_biz, 'html'))
    # Email to customer
    body_cust = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#333">
  <div style="background:linear-gradient(135deg,#10b981,#059669);padding:24px;border-radius:12px 12px 0 0">
    <h2 style="color:#fff;margin:0">Afspraakbevestiging</h2>
  </div>
  <div style="background:#f9f9f9;padding:24px;border-radius:0 0 12px 12px">
    <p>Hallo {customer_name},</p>
    <p>Je afspraak bij <strong>{business_name}</strong> is bevestigd!</p>
    <div style="background:#e8f5e9;border-radius:8px;padding:16px;margin:16px 0">
      <p style="margin:4px 0"><strong>Dienst:</strong> {service or 'â€”'}</p>
      <p style="margin:4px 0"><strong>Datum:</strong> {date}</p>
      <p style="margin:4px 0"><strong>Tijd:</strong> {time}</p>
    </div>
    <p style="color:#888;font-size:13px">Wil je annuleren? Neem contact op met {business_name}.</p>
  </div>
</div>"""
    msg_cust = MIMEMultipart('alternative')
    msg_cust['Subject'] = f'Afspraakbevestiging â€” {date} om {time}'
    msg_cust['From']    = f'{os.getenv("SENDER_NAME", "Robin")} <{gmail}>'
    msg_cust['To']      = customer_email
    msg_cust.attach(MIMEText(body_cust, 'html'))
    import threading
    def _send():
        for attempt in range(3):
            try:
                try:
                    with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as s:
                        s.ehlo(); s.starttls(); s.ehlo()
                        s.login(gmail, pwd)
                        s.sendmail(gmail, business_email, msg_biz.as_string())
                        s.sendmail(gmail, customer_email, msg_cust.as_string())
                        print(f'[EMAIL OK] biz+klant'); return
                except Exception:
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as s:
                        s.login(gmail, pwd)
                        s.sendmail(gmail, business_email, msg_biz.as_string())
                        s.sendmail(gmail, customer_email, msg_cust.as_string())
                        print(f'[EMAIL OK] biz+klant'); return
            except Exception as e:
                import time; time.sleep(2)
        print(f'[EMAIL FAIL] afspraak emails')
    threading.Thread(target=_send, daemon=True).start()

# â”€â”€ Static pages â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory('static', 'dashboard.html')

@app.route('/admin')
def admin():
    return send_from_directory('static', 'admin.html')

@app.route('/live')
@require_admin
def live():
    return send_from_directory('static', 'live.html')

@app.route('/book')
def book():
    return send_from_directory('static', 'book.html')

@app.route('/track/click')
def track_click():
    key = request.args.get('key', '')
    lid = request.args.get('lid', '')
    ref = request.args.get('ref', '')
    if key:
        c = db()
        c.execute("UPDATE customers SET email_clicked=COALESCE(email_clicked,0)+1, email_clicked_at=? WHERE api_key=?",
                  (datetime.now().isoformat(), key))
        c.commit(); c.close()
        return redirect(f'/dashboard?key={key}')
    if lid:
        try:
            oc = sqlite3.connect(OUTREACH_DB)
            oc.execute('UPDATE leads SET link_clicks=COALESCE(link_clicks,0)+1 WHERE id=?', (lid,))
            oc.commit(); oc.close()
        except: pass
    dest = BASE_URL + '/demo' + (f'?ref={ref}' if ref else '')
    return redirect(dest, 302)

@app.route('/widget.js')
def widget_js():
    response = app.make_response(send_from_directory('static', 'widget.js'))
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# â”€â”€ Checkout â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/checkout', methods=['POST'])
def checkout():
    data     = request.json
    email    = data.get('email', '').strip()
    business = data.get('business', '').strip()
    if not email:
        return jsonify({'error': 'Email required'}), 400
    c = db()
    existing = c.execute('SELECT * FROM customers WHERE email=?', (email,)).fetchone()
    if existing and existing['active']:
        c.close()
        return jsonify({'redirect': f'/dashboard?key={existing["api_key"]}'}), 200
    trial_ends = (datetime.now() + timedelta(days=7)).isoformat()
    if existing:
        api_key = existing['api_key']
        c.execute('UPDATE customers SET active=1, trial_ends_at=? WHERE email=?', (trial_ends, email))
        c.commit(); c.close()
    else:
        cid     = str(uuid.uuid4())
        api_key = str(uuid.uuid4()).replace('-', '')
        c.execute('INSERT INTO customers (id,email,api_key,active,trial_ends_at,business_name,created_at) VALUES (?,?,?,1,?,?,?)',
                  (cid, email, api_key, trial_ends, business, datetime.now().isoformat()))
        c.commit(); c.close()
    send_welcome_email(email, api_key, business, trial=True)
    print(f'[TRIAL] {email} | {business}')
    return jsonify({'ok': True, 'trial': True})

# â”€â”€ Admin: activate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/admin/activate', methods=['POST'])
@require_admin
def admin_activate():
    data     = request.json
    email    = data.get('email', '').strip()
    business = data.get('business', '').strip()
    c = db()
    row = c.execute('SELECT * FROM customers WHERE email=?', (email,)).fetchone()
    if row:
        c.execute('UPDATE customers SET active=1, trial_ends_at=NULL WHERE email=?', (email,))
        c.commit(); api_key = row['api_key']
    else:
        api_key = str(uuid.uuid4()).replace('-', '')
        cid     = str(uuid.uuid4())
        c.execute('INSERT INTO customers (id,email,api_key,active,business_name,created_at) VALUES (?,?,?,1,?,?)',
                  (cid, email, api_key, business, datetime.now().isoformat()))
        c.commit()
    c.close()
    send_welcome_email(email, api_key, business, trial=False)
    return jsonify({'ok': True, 'api_key': api_key})

# â”€â”€ Admin: cancel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/admin/cancel', methods=['POST'])
@require_admin
def admin_cancel():
    email = request.json.get('email', '').strip()
    c = db()
    c.execute('UPDATE customers SET active=0 WHERE email=?', (email,))
    c.commit(); c.close()
    return jsonify({'ok': True})

# â”€â”€ Admin: stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/admin/stats')
@require_admin
def admin_stats():
    c = db()
    total  = c.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
    active = c.execute('SELECT COUNT(*) FROM customers WHERE active=1').fetchone()[0]
    trial  = c.execute("SELECT COUNT(*) FROM customers WHERE active=1 AND trial_ends_at IS NOT NULL AND trial_ends_at > datetime('now')").fetchone()[0]
    apts   = c.execute('SELECT COUNT(*) FROM appointments').fetchone()[0]
    today  = c.execute("SELECT COUNT(*) FROM appointments WHERE created_at>=date('now')").fetchone()[0]
    custs  = c.execute('SELECT email,business_name,active,api_key,created_at,trial_ends_at,email_clicked FROM customers ORDER BY created_at DESC').fetchall()
    email_clicks = c.execute("SELECT COALESCE(SUM(email_clicked),0) FROM customers").fetchone()[0]
    c.close()
    emails_sent = total_clicks = leads_clicked = 0
    try:
        oc = sqlite3.connect(OUTREACH_DB)
        emails_sent   = oc.execute('SELECT COUNT(*) FROM leads WHERE email_sent=1').fetchone()[0]
        total_clicks  = oc.execute('SELECT COALESCE(SUM(link_clicks),0) FROM leads').fetchone()[0]
        leads_clicked = oc.execute('SELECT COUNT(*) FROM leads WHERE link_clicks>0').fetchone()[0]
        oc.close()
    except: pass
    mrr = (active - trial) * 20
    now = datetime.now().isoformat()
    return jsonify({
        'total_customers': total, 'active_customers': active, 'trial_customers': trial,
        'mrr': mrr, 'arr': mrr * 12,
        'total_appointments': apts, 'appointments_today': today,
        'emails_sent': emails_sent, 'total_clicks': total_clicks, 'leads_clicked': leads_clicked,
        'email_clicks': email_clicks,
        'customers': [{
            **dict(r),
            'is_trial': bool(r['trial_ends_at'] and r['active'] and r['trial_ends_at'] > now)
        } for r in custs]
    })

# â”€â”€ Live stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/live-stats')
@require_admin
def live_stats():
    c = db()
    total  = c.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
    active = c.execute('SELECT COUNT(*) FROM customers WHERE active=1').fetchone()[0]
    apts   = c.execute('SELECT COUNT(*) FROM appointments').fetchone()[0]
    today  = c.execute("SELECT COUNT(*) FROM appointments WHERE created_at>=date('now')").fetchone()[0]
    trial  = c.execute("SELECT COUNT(*) FROM customers WHERE active=1 AND trial_ends_at IS NOT NULL AND trial_ends_at > datetime('now')").fetchone()[0]
    custs  = c.execute('SELECT email,business_name,active,created_at FROM customers ORDER BY created_at DESC').fetchall()
    days   = c.execute("SELECT date(created_at) as d, COUNT(*) as n FROM appointments GROUP BY date(created_at) ORDER BY date(created_at) DESC LIMIT 14").fetchall()
    c.close()
    mrr = (active - trial) * 20
    return jsonify({
        'active': active, 'total': total, 'mrr': mrr, 'arr': mrr * 12,
        'appointments_total': apts, 'appointments_today': today,
        'customers': [{'name': r['business_name'] or r['email'], 'email': r['email'],
                       'active': bool(r['active']), 'date': (r['created_at'] or '')[:10]} for r in custs],
        'chart': [{'date': r['d'], 'count': r['n']} for r in reversed(days)],
    })

# â”€â”€ Customer: get config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/config')
def get_config():
    key  = request.args.get('key', '')
    cust = get_customer(key)
    if not cust or not cust['active']:
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({
        'business_name': cust['business_name'],
        'email': cust['email'],
        'api_key': key,
    })

# â”€â”€ Customer: update config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/config', methods=['POST'])
def update_config():
    key  = request.args.get('key', '')
    cust = get_customer(key)
    if not cust or not cust['active']:
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.json
    c = db()
    c.execute('UPDATE customers SET business_name=? WHERE api_key=?',
              (data.get('business_name', cust['business_name']), key))
    c.commit(); c.close()
    return jsonify({'ok': True})

# â”€â”€ Customer: get availability â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/availability')
def get_availability():
    key = request.args.get('key', '')
    c = db()
    rows = c.execute('SELECT * FROM availability WHERE api_key=? ORDER BY weekday, start_time', (key,)).fetchall()
    c.close()
    return jsonify([dict(r) for r in rows])

# â”€â”€ Customer: set availability â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/availability', methods=['POST'])
def set_availability():
    key  = request.args.get('key', '')
    cust = get_customer(key)
    if not cust or not cust['active']:
        return jsonify({'error': 'Unauthorized'}), 403
    slots = request.json.get('slots', [])
    c = db()
    c.execute('DELETE FROM availability WHERE api_key=?', (key,))
    for s in slots:
        c.execute('INSERT INTO availability (api_key,weekday,start_time,end_time,slot_duration) VALUES (?,?,?,?,?)',
                  (key, s['weekday'], s['start_time'], s['end_time'], s.get('slot_duration', 60)))
    c.commit(); c.close()
    return jsonify({'ok': True})

# â”€â”€ Customer: get appointments â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/appointments')
def get_appointments():
    key  = request.args.get('key', '')
    cust = get_customer(key)
    if not cust or not cust['active']:
        return jsonify({'error': 'Unauthorized'}), 403
    c = db()
    rows = c.execute('SELECT * FROM appointments WHERE api_key=? ORDER BY date DESC, time DESC', (key,)).fetchall()
    c.close()
    return jsonify([dict(r) for r in rows])

# â”€â”€ Customer: cancel appointment â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/appointments/<int:aid>/cancel', methods=['POST'])
def cancel_appointment(aid):
    key  = request.args.get('key', '')
    cust = get_customer(key)
    if not cust or not cust['active']:
        return jsonify({'error': 'Unauthorized'}), 403
    c = db()
    c.execute("UPDATE appointments SET status='cancelled' WHERE id=? AND api_key=?", (aid, key))
    c.commit(); c.close()
    return jsonify({'ok': True})

# â”€â”€ Public: get available slots for a date â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/slots')
def get_slots():
    key  = request.args.get('key', '')
    date = request.args.get('date', '')
    if not key or not date:
        return jsonify({'error': 'Missing params'}), 400
    try:
        dt      = datetime.strptime(date, '%Y-%m-%d')
        weekday = dt.weekday()  # 0=Mon, 6=Sun
    except:
        return jsonify({'error': 'Invalid date'}), 400
    c = db()
    avail = c.execute('SELECT * FROM availability WHERE api_key=? AND weekday=?', (key, weekday)).fetchall()
    if not avail:
        c.close()
        return jsonify([])
    booked = c.execute(
        "SELECT time FROM appointments WHERE api_key=? AND date=? AND status!='cancelled'",
        (key, date)).fetchall()
    booked_times = {r['time'] for r in booked}
    c.close()
    slots = []
    for av in avail:
        duration = av['slot_duration'] or 60
        start    = datetime.strptime(av['start_time'], '%H:%M')
        end      = datetime.strptime(av['end_time'], '%H:%M')
        cur      = start
        while cur + timedelta(minutes=duration) <= end:
            t = cur.strftime('%H:%M')
            if t not in booked_times:
                slots.append(t)
            cur += timedelta(minutes=duration)
    return jsonify(slots)

# â”€â”€ Public: book appointment â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/book', methods=['POST'])
def book_appointment():
    key  = request.args.get('key', '')
    cust = get_customer(key)
    if not cust or not cust['active']:
        return jsonify({'error': 'Bedrijf niet gevonden'}), 404
    data  = request.json
    name  = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    date  = data.get('date', '').strip()
    time  = data.get('time', '').strip()
    svc   = data.get('service', '').strip()
    note  = data.get('note', '').strip()
    if not name or not email or not date or not time:
        return jsonify({'error': 'Vul alle verplichte velden in'}), 400
    c = db()
    existing = c.execute(
        "SELECT id FROM appointments WHERE api_key=? AND date=? AND time=? AND status!='cancelled'",
        (key, date, time)).fetchone()
    if existing:
        c.close()
        return jsonify({'error': 'Dit tijdslot is al bezet. Kies een ander tijdstip.'}), 409
    c.execute('INSERT INTO appointments (api_key,customer_name,customer_email,customer_phone,service,date,time,note,created_at) VALUES (?,?,?,?,?,?,?,?,?)',
              (key, name, email, phone, svc, date, time, note, datetime.now().isoformat()))
    c.commit(); c.close()
    send_appointment_email(cust['email'], name, email, date, time, svc, cust['business_name'], key)
    print(f'[BOOKING] {cust["business_name"]} | {name} | {date} {time}')
    return jsonify({'ok': True})

# â”€â”€ Unsubscribe â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/unsubscribe')
def unsubscribe():
    email = request.args.get('email', '')
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Uitgeschreven</title>
<style>body{{font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#f0fdf4}}
.box{{background:#fff;border-radius:12px;padding:40px;text-align:center;max-width:400px;box-shadow:0 2px 20px rgba(0,0,0,.08)}}
h2{{color:#333;margin-bottom:12px}}p{{color:#888;font-size:14px}}</style></head>
<body><div class="box"><h2>Je bent uitgeschreven</h2>
<p>{html_escape(email)} ontvangt geen e-mails meer van AfspraakHost.</p></div></body></html>'''

@app.route('/demo')
def demo():
    return send_from_directory('static', 'demo.html')

# â”€â”€ Trial expiring reminder â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def send_trial_expiring_email(email, business_name):
    gmail = os.getenv('GMAIL_ADDRESS', '')
    pwd   = os.getenv('GMAIL_APP_PASSWORD', '')
    if not gmail or not pwd: return
    body = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#333">
  <div style="background:linear-gradient(135deg,#10b981,#059669);padding:32px;border-radius:12px 12px 0 0;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:24px">Nog 2 dagen proefperiode!</h1>
  </div>
  <div style="background:#f9f9f9;padding:32px;border-radius:0 0 12px 12px">
    <p>Hallo{' ' + business_name if business_name else ''},</p>
    <p>Je gratis proefperiode bij AfspraakHost eindigt over <strong>2 dagen</strong>.</p>
    <p>Wil je blijven werken met online afspraken? Maak dan â‚¬20,00 over:</p>
    <div style="background:#e8f5e9;border-radius:8px;padding:20px;margin:20px 0">
      <p style="margin:4px 0;font-size:15px"><strong>IBAN:</strong> NL26 REVO 1741 4708 03</p>
      <p style="margin:4px 0;font-size:15px"><strong>Naam:</strong> R. Spronken</p>
      <p style="margin:4px 0;font-size:15px"><strong>Omschrijving:</strong> {email}</p>
      <p style="margin:4px 0;font-size:15px"><strong>Bedrag:</strong> â‚¬20,00/maand</p>
    </div>
    <p>Na ontvangst wordt je account direct verlengd. Geen creditcard, geen abonnement â€” gewoon overmaken.</p>
    <p style="color:#888;font-size:13px">Vragen? Mail naar spronken1234@gmail.com</p>
  </div>
</div>"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Je AfspraakHost proefperiode eindigt over 2 dagen'
    msg['From']    = f'{os.getenv("SENDER_NAME", "Robin")} <{gmail}>'
    msg['To']      = email
    msg.attach(MIMEText(body, 'html'))
    import threading
    def _send():
        try:
            with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as s:
                s.ehlo(); s.starttls(); s.ehlo()
                s.login(gmail, pwd)
                s.sendmail(gmail, email, msg.as_string())
                print(f'[TRIAL-EXPIRING] {email}'); return
        except Exception:
            try:
                with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as s:
                    s.login(gmail, pwd)
                    s.sendmail(gmail, email, msg.as_string())
                    print(f'[TRIAL-EXPIRING] {email}')
            except Exception as e:
                print(f'[TRIAL-EXPIRING FAIL] {email}: {e}')
    threading.Thread(target=_send, daemon=True).start()

def check_expiring_trials():
    import time as _time
    while True:
        try:
            c = db()
            soon = (datetime.now() + timedelta(days=2, hours=1)).isoformat()
            cutoff = (datetime.now() + timedelta(days=2)).isoformat()
            rows = c.execute(
                "SELECT email,business_name FROM customers WHERE active=1 AND trial_ends_at IS NOT NULL AND trial_ends_at <= ? AND trial_ends_at > ? AND (trial_expiring_sent IS NULL OR trial_expiring_sent=0)",
                (soon, datetime.now().isoformat())).fetchall()
            for r in rows:
                send_trial_expiring_email(r['email'], r['business_name'] or '')
                c.execute("UPDATE customers SET trial_expiring_sent=1 WHERE email=?", (r['email'],))
            c.commit(); c.close()
        except Exception as e:
            print(f'[TRIAL-CHECK ERROR] {e}')
        _time.sleep(3600)

import threading as _threading
def _ensure_trial_expiring_col():
    try:
        c = db()
        c.execute('ALTER TABLE customers ADD COLUMN trial_expiring_sent INTEGER DEFAULT 0')
        c.commit(); c.close()
    except: pass
_ensure_trial_expiring_col()
_threading.Thread(target=check_expiring_trials, daemon=True).start()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8082))
    print(f'AfspraakHost â€” online op poort {port}')
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)


