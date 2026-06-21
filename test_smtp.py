import smtplib, os
from dotenv import load_dotenv
load_dotenv(override=True)
gmail = os.getenv('GMAIL_ADDRESS','')
pwd = os.getenv('GMAIL_APP_PASSWORD','')
print(f"Credentials aanwezig: gmail={bool(gmail)}, pwd={bool(pwd)}")
print(f"Gmail: {gmail[:10]}..." if gmail else "GEEN GMAIL")
try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as s:
        s.login(gmail, pwd)
        print("LOGIN OK — SMTP werkt!")
except Exception as e:
    print(f"SMTP FOUT: {e}")
