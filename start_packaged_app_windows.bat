@echo off
setlocal
cd /d "%~dp0"

if not exist dist\SPXBot.exe (
  echo dist\SPXBot.exe not found. Run build_windows_exe.bat first.
  pause
  exit /b 1
)

cd dist
start "" SPXBot.exe
