@echo off
setlocal
echo [1/3] Installing dependencies...
python -m pip install -r requirements.txt
python -m pip install pyinstaller
echo [2/3] Building (onedir, windowed)...
set ICONARG=
if exist icon.ico set ICONARG=--icon icon.ico
python -m PyInstaller --noconfirm --onedir --windowed --name "AV Combiner" %ICONARG% main.py
echo [3/3] Done. Test: dist\AV Combiner\AV Combiner.exe
pause