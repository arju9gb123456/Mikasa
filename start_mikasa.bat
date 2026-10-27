@echo off
REM Mikasa start (Windows). Double-click karo, ya laptop on hone pe autostart isse chalata hai.
title Mikasa
cd /d "%~dp0"
chcp 65001 >nul

REM ── uv dhoondo (startup pe PATH kabhi-kabhi late load hota hai) ──
set "UV="
where uv >nul 2>nul && set "UV=uv"
if not defined UV if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV (
  echo [Mikasa] uv nahi mila. Pehle install karo:
  echo powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  pause
  exit /b 1
)

REM ── libraries update (naye features / GPU files aaye hon to install, warna 1 second) ──
echo [Mikasa] Libraries check kar rahi hoon (pehli baar GPU files ~1.5 GB download hongi)...
"%UV%" sync --extra mikasa
if errorlevel 1 echo [Mikasa] Library install mein dikkat aayi, purane setup se chala rahi hoon.

REM ── Ollama (AI brain) ready hone ka intezaar, max ~60 second ──
echo [Mikasa] Ollama ka intezaar kar rahi hoon...
set /a TRIES=0
:waitollama
curl -s -o nul http://127.0.0.1:11434/api/version && goto ollama_ok
if %TRIES%==0 (
  where ollama >nul 2>nul && start "" /min ollama serve
)
set /a TRIES+=1
if %TRIES% geq 30 goto ollama_skip
timeout /t 2 /nobreak >nul
goto waitollama
:ollama_skip
echo [Mikasa] Ollama nahi mila. Bina AI ke start kar rahi hoon (apps, search, notes chalenge).
:ollama_ok

REM ── Mikasa chalao. Crash ho to 10 second mein khud restart ──
REM    ("Mikasa band ho jao" bologe to restart nahi hogi)
:run
"%UV%" run --extra mikasa python -m mikasa %*
if %errorlevel%==0 goto end
echo.
echo [Mikasa] Kuch gadbad hui (error %errorlevel%). 10 second mein phir start kar rahi hoon...
echo          Band karna ho to ye window close kar do.
timeout /t 10 /nobreak >nul
goto run

:end
exit /b 0
