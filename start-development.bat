@echo off
setlocal
cd /d "%~dp0"
title Machinepark DEVELOPMENT - ZERO NETLIFY CREDITS

echo ================================================
echo   Machinepark DEVELOPMENT - LOKAAL TESTEN
echo   ZERO NETLIFY CLOUD CREDITS
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
  echo Vul daarin ALLEEN Clerk DEVELOPMENT keys in: pk_test_... en sk_test_...
  echo.
  start "" notepad ".env"
  echo Sla .env op in Kladblok en kom daarna terug naar dit venster.
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
echo Start lokale Machinepark DEVELOPMENT server...
start "" "http://127.0.0.1:8888"
node --env-file=.env dev-server.mjs
pause
