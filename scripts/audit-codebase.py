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

# 3. Alle top-level Netlify-functions moeten syntactisch gecontroleerd worden.
function_files = sorted(
    path.relative_to(ROOT).as_posix()
    for path in (ROOT / 'netlify/functions').glob('*.mjs')
)
for relative in function_files:
    if f'node --check {relative}' not in CHECK_FUNCTIONS:
        error(f'Netlify-function ontbreekt in check:functions: {relative}')

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

# 5. Centrale foto-instellingen moeten na de build overal dezelfde limiet gebruiken.
if 'const REPORT_PHOTO_LIMIT = 5;' not in INDEX:
    error('Verslagfoto-limiet is niet 5 in de gebouwde app.')
if 'const REPORT_PHOTO_LIMIT = 4;' in INDEX:
    error('Oude verslagfoto-limiet 4 is nog aanwezig.')
if 'Maximaal 3 foto’s. Kies één foto als overzichtsfoto' in INDEX:
    error('Oude toestelfoto-limiet 3 is nog aanwezig.')
if 'van maximaal 3 foto’s' in INDEX:
    error('Oude toestelfoto-statuslimiet 3 is nog aanwezig.')
if 'Een toestel kan maximaal 3 foto’s bevatten.' in INDEX:
    error('Oude toestelfoto-foutmelding met limiet 3 is nog aanwezig.')
if 'Maximaal 5 foto’s. Kies één foto als overzichtsfoto' not in INDEX:
    error('Toestelfoto-limiet 5 ontbreekt in de editor.')

# 6. Service-worker cacheversie moet aansluiten bij package major.minor.
version = str(PACKAGE.get('version', '')).strip()
version_parts = version.split('.')
if len(version_parts) >= 2:
    expected_cache_prefix = f'machinepark-v{version_parts[0]}.{version_parts[1]}'
    if expected_cache_prefix not in SW:
        error(f'Service-worker cache wijkt af van packageversie: verwacht {expected_cache_prefix}.')

# 7. Rapportage over onderhoudbaarheid: niet fataal, wel zichtbaar in elke CI-run.
index_kb = round(len(INDEX.encode('utf-8')) / 1024, 1)
note(f'Gebouwde index.html: {index_kb} KB')
note(f'Actieve root-buildpatches: {len(active_root_builds)}')
note(f'Netlify-functions: {len(function_files)}')

if index_kb > 350:
    warning('index.html groeit boven 350 KB; opsplitsing in modules wordt dan sterk aanbevolen.')

server_files = list((ROOT / 'netlify/functions').glob('*.mjs'))
server_texts = {path.name: path.read_text(encoding='utf-8') for path in server_files}
auth_files = [name for name, text in server_texts.items() if re.search(r'async function authenticate(?:Manager)?\s*\(', text)]
if len(auth_files) >= 4:
    warning(f'Clerk-authenticatie wordt in {len(auth_files)} serverfuncties apart geïmplementeerd; kandidaat voor één _shared/auth.mjs.')

admin_email_files = [name for name, text in server_texts.items() if "const ADMIN_EMAIL =" in text]
if len(admin_email_files) >= 4:
    warning(f'ADMIN_EMAIL staat dubbel in {len(admin_email_files)} serverfuncties; kandidaat voor gedeelde serverconfig.')

# De verslagfoto’s zitten nog als data:image in de centrale snapshot. Dat is functioneel,
# maar vormt de grootste resterende schaalbaarheidsgrens na de Blob-migratie van toestel- en onderdeelfoto’s.
base_build = (ROOT / 'scripts/build-machinepark.py').read_text(encoding='utf-8')
if "collectServicePhotos" in base_build and "data:image/" in base_build:
    warning('Onderhouds-/depannagefoto’s worden nog als base64 in de centrale snapshot bewaard; bij veel dossiers kan de PUT opnieuw te groot worden.')

role_management = server_texts.get('role-management.mjs', '')
if "getUserList({ limit: 100" in role_management:
    warning('Rollen verwijderen controleert maximaal 100 Clerk-gebruikers; bij >100 gebruikers is paginering nodig.')

# Wrapperlagen zijn nuttig tijdens ontwikkeling, maar veel overschrijvingen maken de runtime moeilijker te volgen.
for name in ['openDevice', 'showDeviceHistory', 'applyOperationalPermissions', 'localSnapshot']:
    assignments = len(re.findall(rf'\b{re.escape(name)}\s*=\s*(?:async\s+)?function\b', INDEX))
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
