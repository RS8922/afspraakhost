import sqlite3
from datetime import date
conn = sqlite3.connect('outreach.db')
c = conn.cursor()
today = date.today().isoformat()
c.execute("SELECT COUNT(*) FROM sent WHERE date(sent_at) = ?", (today,))
vandaag = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM sent")
totaal = c.fetchone()[0]
print(f"Emails vandaag ({today}): {vandaag}")
print(f"Emails totaal: {totaal}")
c.execute("SELECT sent_at FROM sent ORDER BY sent_at DESC LIMIT 3")
print("Laatste 3:")
for row in c.fetchall():
    print(f"  {row[0]}")
conn.close()
