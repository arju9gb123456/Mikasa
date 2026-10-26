@echo off
REM Mikasa start (Windows). Double-click karo.
cd /d "%~dp0"
chcp 65001 >nul
where uv >nul 2>nul || (
  echo uv nahi mila. Pehle install karo: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  pause
  exit /b 1
)
uv run --extra mikasa python -m mikasa %*
pause
