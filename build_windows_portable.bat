@echo off
setlocal
cd /d "%~dp0"

set PY_VERSION=3.11.9
set PY_ZIP=python-%PY_VERSION%-embed-amd64.zip
set PY_URL=https://www.python.org/ftp/python/%PY_VERSION%/%PY_ZIP%
set OUT=dist_portable\SPXBot
set PYDIR=%OUT%\python

where powershell >nul 2>nul
if errorlevel 1 (
  echo PowerShell was not found.
  pause
  exit /b 1
)

if exist dist_portable (
  rmdir /s /q dist_portable
)

mkdir "%PYDIR%"
mkdir "%OUT%\spx_options_bot"
mkdir "%OUT%\tests"

echo Downloading portable Python runtime...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest '%PY_URL%' -OutFile '%TEMP%\%PY_ZIP%'"
if errorlevel 1 (
  echo Could not download Python runtime.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive '%TEMP%\%PY_ZIP%' '%PYDIR%'"
if errorlevel 1 (
  echo Could not extract Python runtime.
  pause
  exit /b 1
)

echo Enabling site-packages in embedded Python...
powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Content '%PYDIR%\python311._pth') -replace '#import site','import site' | Set-Content '%PYDIR%\python311._pth'"

echo Installing pip...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TEMP%\get-pip.py'"
"%PYDIR%\python.exe" "%TEMP%\get-pip.py" --no-warn-script-location
if errorlevel 1 (
  echo Could not install pip.
  pause
  exit /b 1
)

echo Installing dependencies into portable runtime...
"%PYDIR%\python.exe" -m pip install --no-warn-script-location -r requirements.txt
if errorlevel 1 (
  echo Could not install dependencies.
  pause
  exit /b 1
)

echo Copying app files...
xcopy spx_options_bot "%OUT%\spx_options_bot" /E /I /Y >nul
copy requirements.txt "%OUT%\" >nul
copy README.md "%OUT%\" >nul
copy .env.example "%OUT%\.env" >nul

(
  echo @echo off
  echo cd /d "%%~dp0"
  echo start "" "http://127.0.0.1:8765"
  echo python\python.exe -m spx_options_bot.web_gui
  echo pause
) > "%OUT%\Start SPXBot.bat"

(
  echo @echo off
  echo cd /d "%%~dp0"
  echo python\python.exe -m spx_options_bot
  echo pause
) > "%OUT%\Run Terminal Check.bat"

echo.
echo Portable build complete:
echo %OUT%
echo.
echo Give the whole SPXBot folder to the Windows user.
echo They start the app with: Start SPXBot.bat
pause
