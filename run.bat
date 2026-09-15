@echo off
if not exist .venv py -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo Energy AI startar pa http://localhost:8000
echo Om detta ar forsta starten: fyll i FERROAMP_USERNAME och FERROAMP_PASSWORD i .env och starta om.
start http://localhost:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
