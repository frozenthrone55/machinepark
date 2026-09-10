from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
index = INDEX.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="hide-obsolete-admin-migration-cards-v1"'

# Deze drie hulpmiddelen waren alleen nodig tijdens de overgang naar Synology.
# De onderliggende migratiepagina's/bestanden blijven bestaan als terugvaloptie;
# alleen de kaarten in Beheer verdwijnen.
cloud_cards = [
    '''<div class="settings-card">\n          <h4>Oude cloudfoto's migreren</h4>\n          <p>Kopieer bestaande toestel-, onderdeel- en servicefoto's uit de vroegere online opslag naar de lokale Synology. Er wordt eerst automatisch een veiligheidsback-up gemaakt.</p>\n          <a class="btn" href="./synology/migrate-media.php" style="display:inline-block;text-decoration:none">Migratie oude foto's openen</a>\n        </div>\n        ''',
    '''<div class="settings-card">\n          <h4>Resterende cloudgegevens importeren</h4>\n          <p>Importeer het eenmalige Synology-cloudexportpakket met rollen, Storingen, werkbonnen, handleidingen + PDF's en historisch logboek. Lokale gebruikerswachtwoorden worden nooit overschreven.</p>\n          <a class="btn" href="./synology/import-cloud.php" style="display:inline-block;text-decoration:none">Cloudexport naar Synology importeren</a>\n        </div>\n        ''',
]
for card in cloud_cards:
    if card not in index:
        raise SystemExit('Buildvalidatie mislukt: verwachte oude migratiekaart niet gevonden')
    index = index.replace(card, '', 1)

# Toestelfoto-import uit lokale mappen wordt dynamisch aangemaakt. Laat de oude
# code beschikbaar in de bron, maar maak de runtime-hook bewust inert zodat er
# geen kaart meer in Beheer verschijnt.
old_access = '''  function updateImportAccess() {\n    ensureImportCard();\n    const card = document.getElementById(IMPORT_CARD_ID);\n    if (card) card.style.display = canImportDevicePhotoFolders() ? '' : 'none';\n  }'''
new_access = '''  function updateImportAccess() {\n    const card = document.getElementById(IMPORT_CARD_ID);\n    if (card) card.remove();\n  }'''
if old_access not in index:
    raise SystemExit('Buildvalidatie mislukt: toestelmap-importhook niet gevonden')
index = index.replace(old_access, new_access, 1)

if MARKER not in index:
    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> niet gevonden')
    index = index[:pos] + f'<meta {MARKER}>\n' + index[pos:]

for forbidden in [
    '<h4>Oude cloudfoto\'s migreren</h4>',
    '<h4>Resterende cloudgegevens importeren</h4>',
    'href="./synology/migrate-media.php"',
    'href="./synology/import-cloud.php"',
    'ensureImportCard();\n    const card = document.getElementById(IMPORT_CARD_ID);',
]:
    if forbidden in index:
        raise SystemExit(f'Buildvalidatie mislukt: oude beheerkaart blijft zichtbaar ({forbidden})')

for needle in [MARKER, 'if (card) card.remove();']:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: beheeropruiming ontbreekt ({needle})')

INDEX.write_text(index, encoding='utf-8')
print('[Machinepark] drie verouderde migratieblokken verwijderd uit Beheer')
