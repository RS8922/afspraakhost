import schedule, time
from outreach import daily_run

def job():
    try:
        daily_run()
    except Exception as e:
        print(f'[SCHEDULER ERROR] {e}')

print('AfspraakHost Scheduler gestart — elke 2 uur')
job()
schedule.every(2).hours.do(job)
while True:
    schedule.run_pending()
    time.sleep(60)
