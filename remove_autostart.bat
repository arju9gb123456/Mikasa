@echo off
REM Mikasa ka autostart band karo (Mikasa delete nahi hogi, bas laptop on hone pe khud nahi chalegi).
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Mikasa.lnk"
if exist "%LNK%" (
  del "%LNK%"
  echo [OK] Autostart hata diya. Mikasa ab sirf start_mikasa.bat se chalegi.
) else (
  echo Autostart pehle se off hai.
)
pause
