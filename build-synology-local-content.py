from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
manual_path = ROOT / "manual-library.js"
index = index_path.read_text(encoding="utf-8")
manual = manual_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="synology-local-content-v1"'

if MARKER not in index:
    old_manual = "const MANUAL_LIBRARY_URL = '/.netlify/functions/manual-library';"
    if manual.count(old_manual) != 1:
        raise SystemExit(f"Buildvalidatie mislukt: handleidingen-URL verwacht 1x, gevonden {manual.count(old_manual)}x")
    manual = manual.replace(old_manual, "const MANUAL_LIBRARY_URL = './synology/api/manual-library.php';", 1)
    manual_path.write_text(manual, encoding="utf-8")

    old_work = "const WORK_ORDER_URL = '/.netlify/functions/work-order-templates';"
    if index.count(old_work) != 1:
        raise SystemExit(f"Buildvalidatie mislukt: werkbon-URL verwacht 1x, gevonden {index.count(old_work)}x")
    index = index.replace(old_work, "const WORK_ORDER_URL = './synology/api/work-order-templates.php';", 1)

    # Excel-import en import-undo voor storingen zitten in losse featureblokken.
    index = index.replace("const endpoint = '/.netlify/functions/fault-library';", "const endpoint = './synology/api/fault-library.php';")
    index = index.replace("fetch('/.netlify/functions/fault-library', {", "fetch('./synology/api/fault-library.php', {")

    index = index.replace(
        "</head>",
        f'<meta {MARKER}><meta name="machinepark-content-backend" content="synology-local">\n</head>',
        1,
    )
    index_path.write_text(index, encoding="utf-8")

built_index = index_path.read_text(encoding="utf-8")
built_manual = manual_path.read_text(encoding="utf-8")
for needle in [
    MARKER,
    "./synology/api/work-order-templates.php",
    "./synology/api/fault-library.php",
]:
    if needle not in built_index:
        raise SystemExit(f"Buildvalidatie mislukt: lokale contentkoppeling ontbreekt ({needle})")
if "./synology/api/manual-library.php" not in built_manual:
    raise SystemExit("Buildvalidatie mislukt: lokale handleidingen-API ontbreekt")

for forbidden in [
    "/.netlify/functions/manual-library",
    "/.netlify/functions/work-order-templates",
]:
    if forbidden in built_index or forbidden in built_manual:
        raise SystemExit(f"Buildvalidatie mislukt: oude contentendpoint blijft aanwezig ({forbidden})")

print("[Machinepark] handleidingen, werkbonnen en alle storingsacties lokaal gekoppeld")
