from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

old = "const REPORT_PHOTO_LIMIT = 4;"
new = "const REPORT_PHOTO_LIMIT = 5;"

if new not in index:
    if old not in index:
        raise SystemExit("Buildvalidatie mislukt: limiet voor verslagfoto's niet gevonden")
    index = index.replace(old, new, 1)
    index_path.write_text(index, encoding="utf-8")

if new not in index:
    raise SystemExit("Buildvalidatie mislukt: limiet van 5 verslagfoto's ontbreekt")

print("[Machinepark] maximaal 5 verslagfoto's actief")
