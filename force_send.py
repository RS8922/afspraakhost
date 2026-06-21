import sys
sys.stdout.reconfigure(encoding='utf-8')
from outreach import send_cold_emails, get_stats

print("=== FORCE SEND START ===")
s_before = get_stats()
print(f"Voor: sent={s_before['emails_sent']}, today={s_before['emails_today']}")

sent = send_cold_emails(max_per_day=50)

s_after = get_stats()
print(f"Na: sent={s_after['emails_sent']}, today={s_after['emails_today']}")
print(f"Verstuurd in deze run: {sent}")
