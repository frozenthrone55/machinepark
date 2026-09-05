from pathlib import Path

ROOT = Path(__file__).resolve().parent
frontend_path = ROOT / "fault-library.js"
frontend = frontend_path.read_text(encoding="utf-8")
MARKER = "// machinepark-synology-local-faults-v1"

if MARKER not in frontend:
    old = "const FAULT_LIBRARY_URL = '/.netlify/functions/fault-library';"
    new = "const FAULT_LIBRARY_URL = './synology/api/fault-library.php'; " + MARKER
    count = frontend.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: storingen-URL verwacht 1x, gevonden {count}x")
    frontend = frontend.replace(old, new, 1)
    frontend_path.write_text(frontend, encoding="utf-8")

built = frontend_path.read_text(encoding="utf-8")
if "./synology/api/fault-library.php" not in built or MARKER not in built:
    raise SystemExit("Buildvalidatie mislukt: lokale storings-API niet gekoppeld")
if "/.netlify/functions/fault-library" in built:
    raise SystemExit("Buildvalidatie mislukt: storingen verwijzen nog naar Netlify")

print("[Machinepark] storingsbibliotheek gekoppeld aan lokale Synology API")
