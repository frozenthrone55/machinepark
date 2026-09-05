from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
index = INDEX.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="synology-cloud-import-v1"'

if MARKER not in index:
    anchor = '<div class="settings-card"><h4>Back-up</h4>'
    if anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: Back-upkaart niet gevonden voor cloudimport")

    card = '''<div class="settings-card">
          <h4>Resterende cloudgegevens importeren</h4>
          <p>Importeer het eenmalige Synology-cloudexportpakket met rollen, Storingen, werkbonnen, handleidingen + PDF's en historisch logboek. Lokale gebruikerswachtwoorden worden nooit overschreven.</p>
          <a class="btn" href="./synology/import-cloud.php" style="display:inline-block;text-decoration:none">Cloudexport naar Synology importeren</a>
        </div>
        '''
    index = index.replace(anchor, card + anchor, 1)
    index = index.replace(
        "</head>",
        f'<meta {MARKER}><meta name="machinepark-cloud-import" content="available">\n</head>',
        1,
    )
    INDEX.write_text(index, encoding="utf-8")

built = INDEX.read_text(encoding="utf-8")
for needle in [
    MARKER,
    './synology/import-cloud.php',
    'Cloudexport naar Synology importeren',
]:
    if needle not in built:
        raise SystemExit(f"Buildvalidatie mislukt: cloudimportkoppeling ontbreekt ({needle})")

print("[Machinepark] Synology cloudimport beschikbaar onder Beheer")
