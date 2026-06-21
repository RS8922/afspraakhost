import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
c = sqlite3.connect('outreach.db')
total = c.execute('SELECT COUNT(*) FROM leads WHERE email_sent=1').fetchone()[0]
today = c.execute("SELECT COUNT(*) FROM email_log WHERE sent_at >= '2026-06-20T07:00'").fetchone()[0]
print(f'Totaal verstuurd: {total}')
print(f'Vandaag gestuurd (na 07:00): {today}')
last5 = c.execute("SELECT l.email, el.sent_at FROM email_log el JOIN leads l ON el.lead_id=l.id ORDER BY el.sent_at DESC LIMIT 5").fetchall()
print('Laatste 5 mails:')
for r in last5:
    print(f'  {r[0][:40]} | {r[1][:16]}')
