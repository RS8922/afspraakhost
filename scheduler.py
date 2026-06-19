"""
Automatische dagelijkse scheduler voor AfspraakHost outreach.
Start dit script 1x — het blijft draaien en doet alles zelf.
Elke 2 uur: nieuwe leads zoeken en emails sturen.
"""
import schedule, time
from outreach import daily_run, get_stats
from datetime import datetime

def job():
    print(f'\n{"="*50}')
    print(f' DAGELIJKSE OUTREACH — {datetime.now().strftime("%d/%m/%Y %H:%M")}')
    print(f'{"="*50}')
    try:
        s = daily_run()
        print(f'\n RAPPORT:')
        print(f'  Leads zonder booking : {s["leads_no_booking"]}')
        print(f'  Gemaild              : {s["emails_sent"]}')
        print(f'  Vandaag              : {s["emails_today"]} emails')
        print(f'  Klanten              : {s["active_customers"]}')
        print(f'  MRR                  : €{s["mrr"]}/maand')
    except Exception as e:
        print(f'[SCHEDULER ERROR] {e}')
    print(f'{"="*50}\n')

schedule.every(2).hours.do(job)

print('[SCHEDULER] Gestart — elke 2 uur nieuwe leads zoeken en emails sturen')
print('[SCHEDULER] Eerste run nu...')
job()

while True:
    schedule.run_pending()
    time.sleep(60)
