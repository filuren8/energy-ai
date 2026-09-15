@echo off
setlocal
py -m venv .buildvenv
call .buildvenv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller==6.16.0
pyinstaller --noconfirm --clean --name EnergyAI --onefile --console ^
  --add-data "app\static;app\static" ^
  launcher.py
echo.
echo Klar. EXE finns i dist\EnergyAI.exe
pause
