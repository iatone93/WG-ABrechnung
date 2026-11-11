@echo off
REM Auf einem Windows-PC ausfuehren (Python 3.10+ von python.org installiert)
python -m pip install --upgrade pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name WG-Abrechnung wg_abrechnung.py
echo.
echo Fertig: dist\WG-Abrechnung.exe
pause
