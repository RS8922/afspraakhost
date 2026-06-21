import sqlite3
c = sqlite3.connect('outreach.db')
total = c.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
with_email = c.execute("SELECT COUNT(*) FROM leads WHERE email != ''").fetchone()[0]
unsent = c.execute("SELECT COUNT(*) FROM leads WHERE email != '' AND email_sent=0 AND has_booking=0").fetchone()[0]
# Sample 5 unsent leads
samples = c.execute("SELECT email, business_name, city FROM leads WHERE email != '' AND email_sent=0 AND has_booking=0 LIMIT 5").fetchall()
print(f"Total leads: {total}, With email: {with_email}, Ready to send: {unsent}")
print("Sample queue:")
for s in samples:
    print(f"  {s[0][:40]} | {s[1][:30]} | {s[2][:20]}")
# Check if any table issues
try:
    cols = c.execute("PRAGMA table_info(leads)").fetchall()
    print(f"Table columns: {[c[1] for c in cols]}")
except Exception as e:
    print(f"Table error: {e}")
