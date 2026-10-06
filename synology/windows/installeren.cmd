@echo off
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0install-device-excel-task.ps1"
if errorlevel 1 echo Installatie niet voltooid. Stuur een screenshot van de foutmelding.
pause
