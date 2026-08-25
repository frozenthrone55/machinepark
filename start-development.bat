@echo off
setlocal
cd /d "%~dp0"
title Machinepark DEVELOPMENT - lokaal

echo ================================================
echo   Machinepark DEVELOPMENT - LOKAAL TESTEN
echo   Geen production deploy nodig
echo ================================================
echo.

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is niet gevonden.
  echo Installeer eerst Node.js LTS via https://nodejs.org/
  pause
  exit /b 1
)

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo Een lokaal .env-bestand is aangemaakt.
  echo Vul daarin je Clerk DEVELOPMENT keys in: pk_test_... en sk_test_...
  start "" notepad ".env"
  echo Sla .env op en kom daarna terug naar dit venster.
  pause
)

echo Dependencies controleren/installeren...
call npm install
if errorlevel 1 (
  echo npm install is mislukt.
  pause
  exit /b 1
)

echo.
echo Netlify Dev wordt lokaal gestart op http://localhost:8888
echo Sluit dit venster of druk Ctrl+C om te stoppen.
echo.
call npx netlify-cli dev --offline --port 8888

pause
