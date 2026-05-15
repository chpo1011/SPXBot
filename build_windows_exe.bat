@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\activate.bat (
  echo Virtual environment not found. Run setup_windows.bat first.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
pip install -r requirements.txt

pyinstaller ^
  --name SPXBot ^
  --onefile ^
  --clean ^
  --noconsole ^
  --add-data ".env.example;." ^
  --hidden-import ib_insync ^
  spx_options_bot\desktop_app.py

if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)

if not exist dist\config (
  mkdir dist\config
)

copy .env.example dist\.env >nul

echo.
echo Build complete.
echo App: dist\SPXBot.exe
echo Config template copied to: dist\.env
pause
