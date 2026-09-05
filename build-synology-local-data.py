from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="synology-local-data-v1"'

if MARKER not in index:
    old_url = "const CENTRAL_SYNC_URL='/.netlify/functions/machinepark-data';"
    new_url = "const CENTRAL_SYNC_URL='./synology/api/machinepark-data.php';"
    count = index.count(old_url)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: centrale data-URL verwacht 1x, gevonden {count}x")
    index = index.replace(old_url, new_url, 1)

    old_alert = "alert('Machinepark kon niet worden gestart. Controleer de Netlify HTTPS-link en probeer opnieuw.')"
    if old_alert in index:
        index = index.replace(
            old_alert,
            "alert('Machinepark kon niet worden gestart. Controleer de Synology-verbinding en probeer opnieuw.')",
            1,
        )

    index = index.replace(
        "</head>",
        f'<meta {MARKER}><meta name="machinepark-backend" content="synology-local">\n</head>',
        1,
    )
    index_path.write_text(index, encoding="utf-8")

built = index_path.read_text(encoding="utf-8")
required = [
    MARKER,
    "const CENTRAL_SYNC_URL='./synology/api/machinepark-data.php';",
    'machinepark-backend',
    'synology-local',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f"Buildvalidatie mislukt: Synology lokale data ontbreekt ({needle})")

if "/.netlify/functions/machinepark-data" in built:
    raise SystemExit("Buildvalidatie mislukt: centrale Machinepark-data verwijst nog naar Netlify")

print("[Machinepark] centrale data wijst naar lokale Synology PHP API")
