from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
index = INDEX.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="synology-media-migration-v1"'

if MARKER not in index:
    anchor = '<div class="settings-card"><h4>Back-up</h4>'
    if anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: Back-upkaart niet gevonden voor migratiekoppeling")

    card = '''<div class="settings-card">
          <h4>Oude cloudfoto's migreren</h4>
          <p>Kopieer bestaande toestel-, onderdeel- en servicefoto's uit de vroegere online opslag naar de lokale Synology. Er wordt eerst automatisch een veiligheidsback-up gemaakt.</p>
          <a class="btn" href="./synology/migrate-media.php" style="display:inline-block;text-decoration:none">Migratie oude foto's openen</a>
        </div>
        '''

    index = index.replace(anchor, card + anchor, 1)
    index = index.replace(
        "</head>",
        f'<meta {MARKER}><meta name="machinepark-media-migration" content="available">\n</head>',
        1,
    )
    INDEX.write_text(index, encoding="utf-8")

built = INDEX.read_text(encoding="utf-8")
for needle in [
    MARKER,
    './synology/migrate-media.php',
    "Migratie oude foto's openen",
]:
    if needle not in built:
        raise SystemExit(f"Buildvalidatie mislukt: migratiekoppeling ontbreekt ({needle})")

print("[Machinepark] migratie oude cloudfoto's beschikbaar onder Beheer")
