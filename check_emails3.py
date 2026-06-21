import sqlite3
conn = sqlite3.connect('outreach.db')
c = conn.cursor()
c.execute('PRAGMA table_info(email_log)')
cols = [r[1] for r in c.fetchall()]
print('email_log columns:', cols)
c.execute('SELECT COUNT(*) FROM email_log')
total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM email_log WHERE date(sent_at) = '2026-06-20'")
today = c.fetchone()[0]
print(f'Vandaag: {today} | Totaal: {total}')
col2 = cols[1] if len(cols) > 1 else cols[0]
c.execute(f'SELECT sent_at, {col2} FROM email_log ORDER BY sent_at DESC LIMIT 5')
for r in c.fetchall():
    print(' ', r[0], str(r[1])[:50])
conn.close()
