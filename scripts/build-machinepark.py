from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent.parent
STEPS = [
    'part-machine-picker.py',
    'maintenance-types.py',
    'account-summary.py',
    'breakdown-part-search.py',
    'stock-price-update.py',
    'audit-undo.py',
]

for name in STEPS:
    path = ROOT / 'scripts' / name
    if not path.exists():
        raise SystemExit(f'Buildstap ontbreekt: {name}')
    print(f'[Machinepark build] {name}')
    runpy.run_path(str(path), run_name='__main__')

index = (ROOT / 'index.html').read_text(encoding='utf-8')
sw = (ROOT / 'sw.js').read_text(encoding='utf-8')

required = {
    'Machinepark branding': '<title>Machinepark</title>',
    'Clerk profiel': 'id="clerkUserButton"',
    'Onderdeel autocomplete': 'usage-autocomplete',
    'Toestel autocomplete': 'device-autocomplete',
    'Audit undo': 'data-undo-audit',
    'Prijs excl. BTW import': 'Prijs excl. BTW',
    'Categorie import': "['categorie','category','Merk toestel','merk']",
    'Extra onderhoudstypes': 'Op afroep',
}
for label, needle in required.items():
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: {label} ontbreekt')

if index.count('id="clerkUserButton"') != 1:
    raise SystemExit('Buildvalidatie mislukt: Clerk-profielknop is niet uniek')
if 'id="clearAll"' in index:
    raise SystemExit('Buildvalidatie mislukt: verwijderde Alles wissen-knop is teruggekeerd')
if 'machinepark-v1.' not in sw:
    raise SystemExit('Buildvalidatie mislukt: service-worker cacheversie ontbreekt')

print('[Machinepark build] validatie geslaagd')
