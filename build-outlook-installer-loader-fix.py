from pathlib import Path

ROOT = Path(__file__).resolve().parent
setup_path = ROOT / "machinepark-outlook-classic-setup.cmd"

if not setup_path.exists():
    raise SystemExit("Buildvalidatie mislukt: Outlook Classic setupbestand ontbreekt")

text = setup_path.read_text(encoding="utf-8")

old_loader = '''powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$raw=Get-Content -LiteralPath $env:MP_SELF -Raw; $mark='###MACHINEPARK_POWERSHELL###'; $pos=$raw.IndexOf($mark); if($pos -lt 0){throw 'Installatie-inhoud ontbreekt.'}; $payload=$raw.Substring($pos+$mark.Length); Invoke-Expression $payload"'''
new_loader = '''rem machinepark-outlook-installer-loader-v2
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$raw=Get-Content -LiteralPath $env:MP_SELF -Raw; $hit=[regex]::Match($raw,'(?m)^###MACHINEPARK_POWERSHELL###\\r?$'); if(-not $hit.Success){throw 'Installatie-inhoud ontbreekt.'}; $payload=$raw.Substring($hit.Index+$hit.Length); Invoke-Expression $payload"'''

if "machinepark-outlook-installer-loader-v2" not in text:
    if text.count(old_loader) != 1:
        raise SystemExit(
            "Buildvalidatie mislukt: verwacht exact 1 oude Outlook installer-loader, "
            f"gevonden {text.count(old_loader)}"
        )
    text = text.replace(old_loader, new_loader, 1)
    setup_path.write_text(text, encoding="utf-8", newline="\r\n")

final_text = setup_path.read_text(encoding="utf-8")
required = [
    "machinepark-outlook-installer-loader-v2",
    "[regex]::Match($raw,'(?m)^###MACHINEPARK_POWERSHELL###\\r?$')",
    "$payload=$raw.Substring($hit.Index+$hit.Length)",
    "Invoke-Expression $payload",
]
for needle in required:
    if needle not in final_text:
        raise SystemExit(f"Buildvalidatie mislukt: Outlook installer-loader fix ontbreekt ({needle})")

if "$mark='###MACHINEPARK_POWERSHELL###'; $pos=$raw.IndexOf($mark)" in final_text:
    raise SystemExit("Buildvalidatie mislukt: foutgevoelige Outlook marker-zoekactie is nog aanwezig")

print("[Machinepark] Outlook Classic installer: payload-marker wordt nu alleen als aparte regel gevonden")
