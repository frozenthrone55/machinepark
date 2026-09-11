from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
setup_path = ROOT / "machinepark-outlook-classic-setup.cmd"

if not setup_path.exists():
    raise SystemExit("Buildvalidatie mislukt: Outlook Classic setupbestand ontbreekt")

text = setup_path.read_text(encoding="utf-8")

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

# Elke build start opnieuw van het setupbestand dat build-mail-pdf-desktop-mail.py
# genereert. Zoek daarom structureel de batch-loader vóór de echte payload-marker,
# in plaats van een volledige regel met alle quoting exact te moeten matchen.
if "machinepark-outlook-installer-temp-ps1-v3" not in text:
    marker_match = re.search(r"(?m)^###MACHINEPARK_POWERSHELL###\r?$", text)
    if not marker_match:
        raise SystemExit("Buildvalidatie mislukt: Outlook PowerShell payload-marker ontbreekt")

    batch_prefix = text[:marker_match.start()]
    payload_part = text[marker_match.start():]

    if batch_prefix.count("Invoke-Expression $payload") != 1:
        raise SystemExit(
            "Buildvalidatie mislukt: verwacht exact 1 foutgevoelige Outlook loader vóór de payload-marker, "
            f"gevonden {batch_prefix.count('Invoke-Expression $payload')}"
        )

    loader_start = batch_prefix.find(
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
    )
    if loader_start < 0:
        raise SystemExit("Buildvalidatie mislukt: start van Outlook installer-loader niet gevonden")

    loader_end_token = "exit /b 0"
    loader_end = batch_prefix.find(loader_end_token, loader_start)
    if loader_end < 0:
        raise SystemExit("Buildvalidatie mislukt: einde van Outlook installer-loader niet gevonden")
    loader_end += len(loader_end_token)

    text = (
        batch_prefix[:loader_start]
        + safe_loader
        + batch_prefix[loader_end:]
        + payload_part
    )
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

real_markers = [line for line in final_text.splitlines() if line == "###MACHINEPARK_POWERSHELL###"]
if len(real_markers) != 1:
    raise SystemExit(
        "Buildvalidatie mislukt: verwacht exact 1 echte Outlook payload-markerregel, "
        f"gevonden {len(real_markers)}"
    )

print("[Machinepark] Outlook Classic installer: PowerShell payload wordt veilig als tijdelijk .ps1-bestand uitgevoerd")
