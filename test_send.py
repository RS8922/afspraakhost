import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from outreach import send_email

c = sqlite3.connect('outreach.db')
# Pak eerste echte lead uit queue
lead = c.execute("""
    SELECT id, email, business_name, url, city
    FROM leads
    WHERE email != '' AND email_sent=0 AND has_booking=0
    AND email LIKE '%@%.%'
    AND email NOT LIKE '%.png%'
    AND email NOT LIKE '%.jpg%'
    ORDER BY created_at ASC LIMIT 1
""").fetchone()

if lead:
    lid, email, name, url, city = lead
    print(f"Test verzenden naar: {email} ({name}, {city})")
    result = send_email(email, name or '', url or '', city=city or '', lead_id=lid)
    print(f"Resultaat: {'OK' if result else 'MISLUKT'}")
else:
    print("Geen lead gevonden")
