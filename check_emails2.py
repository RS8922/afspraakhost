import sqlite3
from datetime import date
conn = sqlite3.connect('outreach.db')
c = conn.cursor()

# email_log table
today = date.today().isoformat()
c.execute("SELECT COUNT(*) FROM email_log WHERE date(sent_at) = ?", (today,))
vandaag = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM email_log")
totaal = c.fetchone()[0]
print(f"email_log vandaag ({today}): {vandaag}")
print(f"email_log totaal: {totaal}")

c.execute("SELECT sent_at, email FROM email_log ORDER BY sent_at DESC LIMIT 5")
print("Laatste 5 emails:")
for row in c.fetchall():
    print(f"  {row[0]}  {row[1][:30] if row[1] else '?'}")

# stats
c.execute("SELECT * FROM stats")
print(f"\nStats: {c.fetchall()}")
conn.close()
