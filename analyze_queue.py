import sys, sqlite3, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = sqlite3.connect('outreach.db')

# Count by TLD
all_unsent = c.execute("""
    SELECT email FROM leads
    WHERE email != '' AND email_sent=0 AND has_booking=0
    AND email LIKE '%@%.%'
""").fetchall()

tld_counts = {}
suspicious = 0
for (email,) in all_unsent:
    try:
        tld = email.rsplit('.', 1)[-1].lower()
        tld_counts[tld] = tld_counts.get(tld, 0) + 1
        # Check for suspicious patterns
        if tld in ('site', 'online', 'shop', 'store', 'xyz', 'top', 'click', 'bid', 'win', 'loan', 'work', 'party'):
            suspicious += 1
    except: pass

print(f"Totaal unsent leads: {len(all_unsent)}")
print(f"Suspicious TLDs: {suspicious}")
print(f"\nTop TLDs:")
for tld, cnt in sorted(tld_counts.items(), key=lambda x: -x[1])[:15]:
    flag = " ⚠️" if tld in ('site', 'online', 'shop', 'store', 'xyz') else ""
    print(f"  .{tld}: {cnt}{flag}")

# Count legit leads (nl, com, be, org, net, etc.)
legit_tlds = ('nl', 'com', 'be', 'org', 'net', 'eu', 'de', 'fr', 'co', 'ca', 'uk', 'au', 'nz', 'ar', 'info', 'biz')
legit = sum(1 for (e,) in all_unsent if e.rsplit('.',1)[-1].lower() in legit_tlds)
print(f"\nLegitieme leads (TLD in {legit_tlds[:5]}...): {legit}")
