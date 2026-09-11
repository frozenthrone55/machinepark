from pathlib import Path

ROOT = Path(__file__).resolve().parent
setup_path = ROOT / "machinepark-outlook-classic-setup.cmd"

if not setup_path.exists():
    raise SystemExit("Buildvalidatie mislukt: Outlook Classic setupbestand ontbreekt")

text = setup_path.read_text(encoding="utf-8")

old_loader = '''powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$raw=Get-Content -LiteralPath $env:MP_SELF -Raw; $mark='###MACHINEPARK_POWERSHELL###'; $pos=$raw.IndexOf($mark); if($pos -lt 0){throw 'Installatie-inhoud ontbreekt.'}; $payload=$raw.Substring($pos+$mark.Length); Invoke-Expression $payload"
if errorlevel 1 (
  echo.
  echo De Outlook Classic-koppeling kon niet worden geinstalleerd.
  echo Controleer of Windows PowerShell beschikbaar is en probeer opnieuw.
  pause
  exit /b 1
)
exit /b 0'''

safe_loader = '''rem machinepark-outlook-installer-temp-ps1-v3
set "MP_PS1=%TEMP%\\Machinepark-Outlook-Classic-Setup-%RANDOM%%RANDOM%.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$raw=Get-Content -LiteralPath $env:MP_SELF -Raw; $hit=[regex]::Match($raw,'(?m)^###MACHINEPARK_POWERSHELL###\\r?$'); if(-not $hit.Success){throw 'Installatie-inhoud ontbreekt.'}; $payload=$raw.Substring($hit.Index+$hit.Length); [IO.File]::WriteAllText($env:MP_PS1,$payload,(New-Object Text.UTF8Encoding($false)))"
if errorlevel 1 goto :install_failed
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%MP_PS1%"
set "MP_RC=%ERRORLEVEL%"
del /q "%MP_PS1%" >nul 2>&1
set "MP_PS1="
if not "%MP_RC%"=="0" goto :install_failed
exit /b 0

:install_failed
if defined MP_PS1 del /q "%MP_PS1%" >nul 2>&1
echo.
echo De Outlook Classic-koppeling kon niet worden geinstalleerd.
echo Controleer of Windows PowerShell beschikbaar is en probeer opnieuw.
pause
exit /b 1'''

# Elke build start van de setup die build-mail-pdf-desktop-mail.py genereert.
# Vervang uitsluitend die gekende loader; zo blijft de wijziging geïsoleerd.
if "machinepark-outlook-installer-temp-ps1-v3" not in text:
    if text.count(old_loader) != 1:
        raise SystemExit(
            "Buildvalidatie mislukt: verwacht exact 1 oude Outlook installer-loader, "
            f"gevonden {text.count(old_loader)}"
        )
    text = text.replace(old_loader, safe_loader, 1)
    setup_path.write_text(text, encoding="utf-8", newline="\r\n")

final_text = setup_path.read_text(encoding="utf-8")
required = [
    "machinepark-outlook-installer-temp-ps1-v3",
    "[regex]::Match($raw,'(?m)^###MACHINEPARK_POWERSHELL###\\r?$')",
    "[IO.File]::WriteAllText($env:MP_PS1,$payload,(New-Object Text.UTF8Encoding($false)))",
    'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%MP_PS1%"',
    ':install_failed',
]
for needle in required:
    if needle not in final_text:
        raise SystemExit(f"Buildvalidatie mislukt: veilige Outlook installer-loader ontbreekt ({needle})")

for unsafe in (
    "Invoke-Expression $payload",
    "$mark='###MACHINEPARK_POWERSHELL###'; $pos=$raw.IndexOf($mark)",
):
    if unsafe in final_text:
        raise SystemExit(f"Buildvalidatie mislukt: foutgevoelige Outlook loader is nog aanwezig ({unsafe})")

print("[Machinepark] Outlook Classic installer: PowerShell payload wordt veilig als tijdelijk .ps1-bestand uitgevoerd")
