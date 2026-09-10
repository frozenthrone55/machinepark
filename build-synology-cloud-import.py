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

# De migratiehulpmiddelen blijven technisch beschikbaar, maar zijn na de
# Synology-overgang niet meer nodig in het gewone Beheer-scherm.
obsolete_cards = [
    '''<div class="settings-card">
          <h4>Oude cloudfoto's migreren</h4>
          <p>Kopieer bestaande toestel-, onderdeel- en servicefoto's uit de vroegere online opslag naar de lokale Synology. Er wordt eerst automatisch een veiligheidsback-up gemaakt.</p>
          <a class="btn" href="./synology/migrate-media.php" style="display:inline-block;text-decoration:none">Migratie oude foto's openen</a>
        </div>
        ''',
    '''<div class="settings-card">
          <h4>Resterende cloudgegevens importeren</h4>
          <p>Importeer het eenmalige Synology-cloudexportpakket met rollen, Storingen, werkbonnen, handleidingen + PDF's en historisch logboek. Lokale gebruikerswachtwoorden worden nooit overschreven.</p>
          <a class="btn" href="./synology/import-cloud.php" style="display:inline-block;text-decoration:none">Cloudexport naar Synology importeren</a>
        </div>
        ''',
]
for obsolete in obsolete_cards:
    index = index.replace(obsolete, '', 1)

# 'Toestelfoto’s uit lokale mappen' wordt door een oudere buildlaag dynamisch
# aangemaakt. Schakel alleen die beheerkaart uit; de gewone toestelfoto-opslag
# en alle reeds opgeslagen foto's blijven volledig intact.
old_access = '''  function updateImportAccess() {
    ensureImportCard();
    const card = document.getElementById(IMPORT_CARD_ID);
    if (card) card.style.display = canImportDevicePhotoFolders() ? '' : 'none';
  }'''
new_access = '''  function updateImportAccess() {
    const card = document.getElementById(IMPORT_CARD_ID);
    if (card) card.remove();
  }'''
if old_access in index:
    index = index.replace(old_access, new_access, 1)
elif new_access not in index:
    raise SystemExit('Buildvalidatie mislukt: toestelmap-fotoimporthook niet gevonden')

INDEX.write_text(index, encoding="utf-8")

built = INDEX.read_text(encoding="utf-8")
for needle in [MARKER, './synology/import-cloud.php', './synology/migrate-media.php']:
    # De routes mogen in metadata/scripts blijven bestaan; ze mogen alleen niet
    # meer als zichtbare beheerknop worden aangeboden.
    if needle == MARKER and needle not in built:
        raise SystemExit(f"Buildvalidatie mislukt: cloudimportmarker ontbreekt ({needle})")

for forbidden in [
    '<h4>Oude cloudfoto\'s migreren</h4>',
    '<h4>Resterende cloudgegevens importeren</h4>',
    'href="./synology/migrate-media.php"',
    'href="./synology/import-cloud.php"',
    'ensureImportCard();\n    const card = document.getElementById(IMPORT_CARD_ID);',
]:
    if forbidden in built:
        raise SystemExit(f"Buildvalidatie mislukt: verouderde beheerkaart blijft zichtbaar ({forbidden})")

if 'if (card) card.remove();' not in built:
    raise SystemExit('Buildvalidatie mislukt: toestelmap-fotokaart wordt niet verwijderd')

print("[Machinepark] oude migratiehulpmiddelen technisch behouden, maar verwijderd uit Beheer")
