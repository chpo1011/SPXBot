@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher "py" was not found.
  echo Install Python from https://www.python.org/downloads/windows/ and enable "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist .venv (
  py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist .env (
  copy .env.example .env >nul
  echo Created .env from .env.example
)

echo.
echo Setup complete.
echo Edit .env if needed, then run start_web_gui_windows.bat
pause
