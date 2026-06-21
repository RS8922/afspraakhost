import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8')

c = sqlite3.connect('outreach.db')

# Wat zijn de leads die vandaag gestuurd zijn?
today_sent = c.execute("""
    SELECT l.email, l.business_name, el.sent_at
    FROM email_log el JOIN leads l ON el.lead_id = l.id
    WHERE el.sent_at LIKE '2026-06-20%'
    ORDER BY el.sent_at
""").fetchall()
print(f"Vandaag gestuurd ({len(today_sent)}):")
for row in today_sent:
    try:
        print(f"  {row[0][:40]} | {str(row[1] or '')[:25]} | {row[2][:16]}")
    except: print(f"  [encode error]")

# Check volgende 10 leads die geprobeerd zouden worden
next_leads = c.execute("""
    SELECT email, business_name FROM leads
    WHERE email != '' AND email_sent=0 AND has_booking=0
    AND email LIKE '%@%.%'
    AND email NOT LIKE '%.png%'
    ORDER BY created_at ASC LIMIT 10
""").fetchall()
print(f"\nVolgende leads in queue:")
for r in next_leads:
    try:
        print(f"  {r[0][:40]} | {str(r[1] or '')[:25]}")
    except: print(f"  [encode error]")
