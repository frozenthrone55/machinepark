from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
BUILD_COMMAND = PACKAGE.get('scripts', {}).get('build', '')
CHECK_FUNCTIONS = PACKAGE.get('scripts', {}).get('check:functions', '')
INDEX = (ROOT / 'index.html').read_text(encoding='utf-8')
SW = (ROOT / 'sw.js').read_text(encoding='utf-8')
BUILD_JS_PATH = ROOT / 'assets/machinepark-build.js'
BUILD_CSS_PATH = ROOT / 'assets/machinepark-build.css'
BUILD_JS = BUILD_JS_PATH.read_text(encoding='utf-8') if BUILD_JS_PATH.exists() else ''
BUILD_CSS = BUILD_CSS_PATH.read_text(encoding='utf-8') if BUILD_CSS_PATH.exists() else ''
APP_SOURCE = '\n'.join([INDEX, BUILD_JS, BUILD_CSS])

errors = []
warnings = []
notes = []


def error(message):
    errors.append(message)


def warning(message):
    warnings.append(message)


def note(message):
    notes.append(message)


# 1. Buildketen: elk root build-*.py-bestand moet exact één keer actief zijn.
active_build_files = []
for step in BUILD_COMMAND.split('&&'):
    step = step.strip()
    match = re.fullmatch(r'python3\s+([^\s]+)', step)
    if match:
        active_build_files.append(match.group(1))

root_build_files = sorted(path.name for path in ROOT.glob('build-*.py'))
active_root_builds = [Path(path).name for path in active_build_files if Path(path).parent == Path('.')]

for path in sorted(set(root_build_files) - set(active_root_builds)):
    error(f'Ongebruikt root-buildbestand: {path}')
for path in sorted(set(active_root_builds) - set(root_build_files)):
    error(f'Buildketen verwijst naar ontbrekend bestand: {path}')
for path in sorted(set(active_root_builds)):
    if active_root_builds.count(path) > 1:
        error(f'Dubbele buildstap: {path}')

if 'scripts/extract-build-assets.py' not in active_build_files:
    error('De build wordt niet afgesloten met de frontend-assetextractie.')

# 2. Buildmarkers mogen niet door verschillende patches gedeeld worden.
marker_owners = {}
marker_pattern = re.compile(r'data-machinepark-build-fix=\\?"([^"\\]+)\\?"')
for relative in active_build_files:
    path = ROOT / relative
    if not path.exists() or path.suffix != '.py':
        continue
    text = path.read_text(encoding='utf-8')
    for marker in set(marker_pattern.findall(text)):
        marker_owners.setdefault(marker, []).append(relative)
for marker, owners in sorted(marker_owners.items()):
    if len(set(owners)) > 1:
        error(f'Buildmarker {marker!r} zit in meerdere bestanden: {", ".join(sorted(set(owners)))}')

# 3. Alle Netlify JavaScript-modules, inclusief _shared, moeten syntactisch gecontroleerd worden.
function_files = sorted(
    path.relative_to(ROOT).as_posix()
    for path in (ROOT / 'netlify/functions').rglob('*.mjs')
)
for relative in function_files:
    if f'node --check {relative}' not in CHECK_FUNCTIONS:
        error(f'Netlify-module ontbreekt in check:functions: {relative}')

# 4. Dependencies moeten werkelijk gebruikt worden buiten package.json.
source_paths = [
    *ROOT.glob('*.html'),
    *ROOT.glob('*.js'),
    *ROOT.glob('*.py'),
    *(ROOT / 'scripts').glob('*.py'),
    *(ROOT / 'netlify/functions').rglob('*.mjs'),
]
source_text = '\n'.join(path.read_text(encoding='utf-8') for path in source_paths if path.exists())
for dependency in sorted(PACKAGE.get('dependencies', {})):
    if dependency not in source_text:
        error(f'Ongebruikte package dependency: {dependency}')

# 5. Centrale foto-instellingen en opslagarchitectuur.
if 'const REPORT_PHOTO_LIMIT = 5;' not in APP_SOURCE:
    error('Verslagfoto-limiet is niet 5 in de gebouwde app.')
if 'const REPORT_PHOTO_LIMIT = 4;' in APP_SOURCE:
    error('Oude verslagfoto-limiet 4 is nog aanwezig.')
if 'const DEVICE_PHOTO_LIMIT = 5;' not in APP_SOURCE:
    error('Toestelfoto-limiet is niet centraal op 5 ingesteld.')
if 'Een toestel kan maximaal 3 foto’s bevatten.' in APP_SOURCE or 'van maximaal 3 foto’s' in APP_SOURCE:
    error('Oude toestelfoto-limiet 3 is nog aanwezig.')
if 'machineparkPersistServicePhotos' not in APP_SOURCE or '/.netlify/functions/service-photos' not in APP_SOURCE:
    error('Verslagfoto’s gebruiken de aparte Blob-opslag niet.')
if 'const baseLocalSnapshotForPartPhotos = localSnapshot;' in APP_SOURCE:
    error('Achtergrondfotomigratie blokkeert nog de centrale snapshot.')

# 6. De featurelaag moet na de build uit de grote HTML gehaald zijn.
if not BUILD_JS_PATH.exists() or BUILD_JS_PATH.stat().st_size < 1000:
    error('Gegenereerde JavaScript-asset ontbreekt of is onverwacht klein.')
if not BUILD_CSS_PATH.exists() or BUILD_CSS_PATH.stat().st_size < 1000:
    error('Gegenereerde CSS-asset ontbreekt of is onverwacht klein.')
if '/assets/machinepark-build.js' not in INDEX or '/assets/machinepark-build.css' not in INDEX:
    error('index.html verwijst niet naar beide gegenereerde frontend-assets.')
if re.search(r'<script\b[^>]*data-machinepark-build-fix=', INDEX, flags=re.IGNORECASE):
    error('Feature-JavaScript staat nog inline in index.html.')
if re.search(r'<style\b[^>]*data-machinepark-build-fix=', INDEX, flags=re.IGNORECASE):
    error('Feature-CSS staat nog inline in index.html.')

# 7. Service-worker cacheversie moet aansluiten bij package major.minor en externe assets bevatten.
version = str(PACKAGE.get('version', '')).strip()
version_parts = version.split('.')
if len(version_parts) >= 2:
    expected_cache_prefix = f'machinepark-v{version_parts[0]}.{version_parts[1]}'
    if expected_cache_prefix not in SW:
        error(f'Service-worker cache wijkt af van packageversie: verwacht {expected_cache_prefix}.')
for asset in ['/assets/machinepark-build.js', '/assets/machinepark-build.css']:
    if asset not in SW:
        error(f'Service worker cachet gegenereerde asset niet: {asset}')

# 8. Serverauth hoort uitsluitend in de gedeelde module thuis.
server_files = list((ROOT / 'netlify/functions').glob('*.mjs'))
server_texts = {path.name: path.read_text(encoding='utf-8') for path in server_files}
for name, text in server_texts.items():
    if "from '@clerk/backend'" in text:
        error(f'{name} implementeert Clerk nog rechtstreeks; gebruik _shared/server-auth.mjs.')
    if re.search(r'^const ADMIN_EMAIL\s*=', text, flags=re.MULTILINE):
        error(f'{name} bevat nog een eigen ADMIN_EMAIL; gebruik de gedeelde serverconfig.')

shared_auth = (ROOT / 'netlify/functions/_shared/server-auth.mjs').read_text(encoding='utf-8') if (ROOT / 'netlify/functions/_shared/server-auth.mjs').exists() else ''
if "from '@clerk/backend'" not in shared_auth or "export const ADMIN_EMAIL" not in shared_auth:
    error('Gedeelde server-authenticatie/config ontbreekt of is onvolledig.')

# 9. Rapportage over onderhoudbaarheid.
index_kb = round(len(INDEX.encode('utf-8')) / 1024, 1)
js_kb = round(len(BUILD_JS.encode('utf-8')) / 1024, 1)
css_kb = round(len(BUILD_CSS.encode('utf-8')) / 1024, 1)
note(f'index.html: {index_kb} KB')
note(f'Feature-JavaScript: {js_kb} KB')
note(f'Feature-CSS: {css_kb} KB')
note(f'Actieve root-buildpatches: {len(active_root_builds)}')
note(f'Netlify-modules: {len(function_files)}')

if index_kb > 350:
    warning('index.html blijft boven 350 KB ondanks assetextractie; verdere bronmodularisatie is aanbevolen.')

# Veel wrappers maken runtime-volgorde moeilijker. Twee lagen (feature + rechten) zijn acceptabel;
# drie of meer worden als onderhoudsprobleem gerapporteerd.
for name in ['openDevice', 'showDeviceHistory', 'applyOperationalPermissions', 'localSnapshot']:
    assignments = len(re.findall(rf'\b{re.escape(name)}\s*=\s*(?:async\s+)?function\b', APP_SOURCE))
    if assignments > 2:
        warning(f'{name} wordt {assignments} keer opnieuw toegewezen in de gebouwde app; kandidaat voor consolidatie.')

print('[Machinepark audit]')
for message in notes:
    print(f'  INFO  {message}')
for message in warnings:
    print(f'  LET OP  {message}')
for message in errors:
    print(f'  FOUT  {message}')

if errors:
    print(f'[Machinepark audit] mislukt met {len(errors)} fout(en).')
    sys.exit(1)
print(f'[Machinepark audit] geslaagd met {len(warnings)} onderhoudswaarschuwing(en).')
