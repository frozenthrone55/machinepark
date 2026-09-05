from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SW = ROOT / "sw.js"
index = INDEX.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="synology-local-photos-v1"'

if MARKER not in index:
    replacements = {
        "'/.netlify/functions/device-photos?'": "'./synology/api/device-photos.php?'",
        "'/.netlify/functions/part-photos?'": "'./synology/api/part-photos.php?'",
        "'/.netlify/functions/device-photos'": "'./synology/api/device-photos.php'",
        "'/.netlify/functions/part-photos'": "'./synology/api/part-photos.php'",
        "'/.netlify/functions/service-photos'": "'./synology/api/service-photos.php'",
        "'/.netlify/functions/service-photos?'": "'./synology/api/service-photos.php?'",
        "'/.netlify/functions/purge-service-audit-photos'": "'./synology/api/purge-service-audit-photos.php'",
        '"/.netlify/functions/device-photos?"': '"./synology/api/device-photos.php?"',
        '"/.netlify/functions/part-photos?"': '"./synology/api/part-photos.php?"',
        '"/.netlify/functions/device-photos"': '"./synology/api/device-photos.php"',
        '"/.netlify/functions/part-photos"': '"./synology/api/part-photos.php"',
        '"/.netlify/functions/service-photos"': '"./synology/api/service-photos.php"',
        '"/.netlify/functions/service-photos?"': '"./synology/api/service-photos.php?"',
        '"/.netlify/functions/purge-service-audit-photos"': '"./synology/api/purge-service-audit-photos.php"',
    }
    replaced = 0
    for old, new in replacements.items():
        count = index.count(old)
        if count:
            index = index.replace(old, new)
            replaced += count

    if replaced < 8:
        raise SystemExit(f"Buildvalidatie mislukt: te weinig foto-endpoints lokaal gemaakt ({replaced})")

    # Relatieve fotorefs moeten vanaf /machinepark/ worden geïnterpreteerd.
    index = index.replace(
        "const url = new URL(value, location.origin);",
        "const url = new URL(value, location.href);",
    )

    # De lokale API gebruikt de PHP-sessie; geen Clerk-token meer bij opschonen.
    old_purge = """    const token = await window.Clerk?.session?.getToken();
    if (!token) throw new Error('Geen actieve Clerk-sessie.');
    const response = await fetch('./synology/api/purge-service-audit-photos.php', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },"""
    new_purge = """    const headers = await centralHeaders(true);
    const response = await fetch('./synology/api/purge-service-audit-photos.php', {
      method: 'POST',
      headers,"""
    if old_purge not in index:
        raise SystemExit("Buildvalidatie mislukt: oude Clerk-opruimcode voor servicefoto’s niet gevonden")
    index = index.replace(old_purge, new_purge, 1)

    # Bij lokaal opslaan herkennen we lokale refs. Oude cloudrefs blijven als data
    # behouden tot een expliciete migratie ze kan overzetten.
    index = index.replace(
        "if (value.includes('./synology/api/part-photos.php?')) return value;",
        "if (value.includes('./synology/api/part-photos.php?') || value.includes('/machinepark/synology/api/part-photos.php?')) return value;",
    )

    index = index.replace(
        "</head>",
        f'<meta {MARKER}><meta name="machinepark-photo-backend" content="synology-local">\n</head>',
        1,
    )
    INDEX.write_text(index, encoding="utf-8")

sw = SW.read_text(encoding="utf-8")
sw = re.sub(
    r"const CACHEABLE_API=new Set\(\[[\s\S]*?\]\);",
    "const CACHEABLE_API=new Set([]);",
    sw,
    count=1,
)
SW.write_text(sw, encoding="utf-8")

built = INDEX.read_text(encoding="utf-8")
for needle in [
    "./synology/api/device-photos.php",
    "./synology/api/part-photos.php",
    "./synology/api/service-photos.php",
    "./synology/api/purge-service-audit-photos.php",
    MARKER,
]:
    if needle not in built:
        raise SystemExit(f"Buildvalidatie mislukt: lokale foto-opslag ontbreekt ({needle})")

for forbidden in [
    "/.netlify/functions/device-photos",
    "/.netlify/functions/part-photos",
    "/.netlify/functions/service-photos",
    "/.netlify/functions/purge-service-audit-photos",
]:
    if forbidden in built:
        raise SystemExit(f"Buildvalidatie mislukt: oude foto-endpoint blijft aanwezig ({forbidden})")

if "/.netlify/functions/" in SW.read_text(encoding="utf-8"):
    raise SystemExit("Buildvalidatie mislukt: service worker bevat nog een Netlify function-cache")

print(f"[Machinepark] foto-opslag lokaal gekoppeld ({replaced} endpointverwijzingen) en Netlify API-cache verwijderd")
