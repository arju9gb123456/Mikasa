@echo off
REM Ek baar double-click karo: ab har baar laptop on (login) hote hi Mikasa khud start hogi.
title Mikasa Autostart Setup
cd /d "%~dp0"
chcp 65001 >nul

echo.
echo  ==========================================
echo    Mikasa Autostart Setup
echo  ==========================================
echo.

REM ── uv check ──
set "UV="
where uv >nul 2>nul && set "UV=uv"
if not defined UV if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV (
  echo [X] uv nahi mila. Pehle ye command PowerShell mein chalao, phir ye file dobara kholo:
  echo     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  echo.
  pause
  exit /b 1
)

REM ── libraries install / update (pehli baar 5-10 min) ──
echo [1/2] Mikasa ki libraries check / install kar rahi hoon...
"%UV%" sync --extra mikasa
if errorlevel 1 (
  echo [X] Install fail hua. Upar ka error copy karke bhejo.
  pause
  exit /b 1
)

REM ── Startup folder mein shortcut (minimized window) ──
echo [2/2] Startup mein Mikasa add kar rahi hoon...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'Mikasa.lnk';" ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk);" ^
  "$s.TargetPath = '%~dp0start_mikasa.bat';" ^
  "$s.WorkingDirectory = '%~dp0';" ^
  "$s.WindowStyle = 7;" ^
  "$s.Description = 'Mikasa voice assistant - Made by Arjun Ahirwar';" ^
  "$s.Save(); Write-Host ('    Shortcut: ' + $lnk)"
if errorlevel 1 (
  echo [X] Shortcut nahi ban paya.
  pause
  exit /b 1
)

echo.
echo  [OK] Ho gaya! Ab laptop on karke login karte hi Mikasa khud start hogi
echo       (taskbar mein minimized window). Bas "Mikasa" bolo.
echo.
echo  Autostart hatana ho to: remove_autostart.bat
echo.
set /p NOW="Abhi Mikasa start karun? (y/n): "
if /i "%NOW%"=="y" start "" /min "%~dp0start_mikasa.bat"
exit /b 0
