@echo off
title AfspraakHost — Automatisch Outreach Systeem
color 0B
echo.
echo  ================================================
echo   AFSPRAAKHOST — LEAD GENERATION ^& EMAIL OUTREACH
echo  ================================================
echo.
echo  Installeert packages...
cd /d "%~dp0"
pip install -r requirements.txt -q
echo.
echo  [OK] Elke 2 uur worden automatisch:
echo       - Bedrijven gevonden zonder online boekingssysteem
echo       - HTML emails verstuurd (NL/EN/DE/FR/ES/IT/PT)
echo       - Follow-ups gestuurd na 3 dagen
echo.
echo  !! Zorg dat GMAIL_APP_PASSWORD is ingesteld in .env !!
echo.
python scheduler.py
pause
