from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent.parent

# Bouw eerst exact dezelfde versie die CI en Netlify al valideren.
runpy.run_path(str(ROOT / 'scripts' / 'build-machinepark.py'), run_name='__main__')

index = (ROOT / 'index.html').read_text(encoding='utf-8')
sw = (ROOT / 'sw.js').read_text(encoding='utf-8')

required = [
    '<title>Machinepark</title>',
    'usage-autocomplete',
    'device-autocomplete',
    'data-undo-audit',
    'dashboardProfessional',
    'downloadStockImportReport',
    'Machinepark_Veiligheidsbackup_',
    'Prijs excl. BTW',
    'technieker',
    'magazijnier',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Consolidatie afgebroken: ontbreekt {needle}')
if index.count('id="clerkUserButton"') != 1:
    raise SystemExit('Consolidatie afgebroken: Clerk-profielknop is niet uniek')
if 'id="clearAll"' in index:
    raise SystemExit('Consolidatie afgebroken: Alles wissen is onverwacht teruggekeerd')
if 'machinepark-v1.52-professional-foundation' not in sw:
    raise SystemExit('Consolidatie afgebroken: verkeerde service-worker versie')

# Na consolidatie is `npm run build` alleen nog een statische kwaliteitscontrole.
validator = '''from pathlib import Path\n\nROOT = Path(__file__).resolve().parent.parent\nindex = (ROOT / "index.html").read_text(encoding="utf-8")\nsw = (ROOT / "sw.js").read_text(encoding="utf-8")\nrequired = {\n    "branding": "<title>Machinepark</title>",\n    "Clerk profiel": "id=\\\"clerkUserButton\\\"",\n    "onderdeel autocomplete": "usage-autocomplete",\n    "toestel autocomplete": "device-autocomplete",\n    "audit undo": "data-undo-audit",\n    "operationeel dashboard": "dashboardProfessional",\n    "veiligheidsbackup": "Machinepark_Veiligheidsbackup_",\n    "importverslag": "downloadStockImportReport",\n    "prijsimport": "Prijs excl. BTW",\n    "technieker rol": "technieker",\n    "magazijnier rol": "magazijnier",\n}\nfor label, needle in required.items():\n    if needle not in index:\n        raise SystemExit(f"Buildvalidatie mislukt: {label} ontbreekt")\nif index.count("id=\\\"clerkUserButton\\\"") != 1:\n    raise SystemExit("Buildvalidatie mislukt: Clerk-profielknop is niet uniek")\nif "id=\\\"clearAll\\\"" in index:\n    raise SystemExit("Buildvalidatie mislukt: Alles wissen is teruggekeerd")\nif "machinepark-v1.52-professional-foundation" not in sw:\n    raise SystemExit("Buildvalidatie mislukt: verkeerde service-worker cache")\nprint("[Machinepark] broncodevalidatie geslaagd")\n'''
(ROOT / 'scripts' / 'build-machinepark.py').write_text(validator, encoding='utf-8')

legacy = [
    'part-machine-picker.py',
    'maintenance-types.py',
    'account-summary.py',
    'breakdown-part-search.py',
    'stock-price-update.py',
    'audit-undo.py',
    'professionalize.py',
]
for name in legacy:
    path = ROOT / 'scripts' / name
    if path.exists():
        path.unlink()

# De eenmalige consolidatiehulp en workflow verwijderen zichzelf uit de eindtoestand.
workflow = ROOT / '.github' / 'workflows' / 'bake-source.yml'
if workflow.exists():
    workflow.unlink()
Path(__file__).unlink()

print('[Machinepark] broncode geconsolideerd; tijdelijke patchlaag verwijderd')
