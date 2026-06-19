@echo off
title AfspraakHost SaaS
color 0A
echo.
echo  ====================================
echo   AfspraakHost — Online Boekingen
echo  ====================================
echo.
cd /d "%~dp0"
pip install -r requirements.txt -q
echo  [OK] Starten op http://localhost:8082
echo  [OK] Admin panel: http://localhost:8082/admin?admin_key=jarvis-admin-2024
echo  [OK] Live stats:  http://localhost:8082/live?admin_key=jarvis-admin-2024
echo.
python server.py
pause
