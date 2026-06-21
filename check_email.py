import sqlite3
c = sqlite3.connect('outreach.db')
sent = c.execute('SELECT COUNT(*) FROM leads WHERE email_sent=1').fetchone()[0]
queue = c.execute('SELECT COUNT(*) FROM leads WHERE email_sent=0 AND has_booking=0').fetchone()[0]
try:
    today = c.execute("SELECT COUNT(*) FROM email_log WHERE sent_at LIKE '2026-06-20%'").fetchone()[0]
    recent = c.execute("SELECT to_email, sent_at FROM email_log ORDER BY sent_at DESC LIMIT 3").fetchall()
except Exception as e:
    today = 0
    recent = []
    print(f"email_log error: {e}")
print(f"Total sent: {sent}, Today (20-06): {today}, Queue: {queue}")
for r in recent:
    print(f"  Recent: {r[0][:30]} @ {r[1][:16]}")
