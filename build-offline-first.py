from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
sw_path = ROOT / 'sw.js'
package = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
version = str(package.get('version') or '1')
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="offline-first-loader-v1"'
loader = f'<script src="/offline-first.js?v={version}" data-machinepark-offline-first="1"></script>'

if MARKER not in index:
    if '</head>' not in index or '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-afsluiters ontbreken voor offline-first loader')
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    body_pos = index.rfind('</body>')
    index = index[:body_pos] + loader + '\n' + index[body_pos:]
else:
    # Ook bestaande builds moeten bij iedere appversie een nieuwe runtime-URL krijgen.
    pattern = r'<script src="/offline-first\.js(?:\?v=[^"]*)?" data-machinepark-offline-first="1"></script>'
    updated, count = re.subn(pattern, loader, index, count=1)
    if count != 1:
        raise SystemExit('Buildvalidatie mislukt: bestaande offline-first loader niet uniek gevonden')
    index = updated

index_path.write_text(index, encoding='utf-8')

# De service-worker moet exact dezelfde versiegebonden URL vooraf cachen. Zelfs een
# oudere controller mist deze nieuwe URL en moet ze daardoor van het netwerk halen.
sw = sw_path.read_text(encoding='utf-8')
sw, count = re.subn(
    r"'/offline-first\.js(?:\?v=[^']*)?'",
    f"'/offline-first.js?v={version}'",
    sw,
    count=1,
)
if count != 1:
    raise SystemExit('Buildvalidatie mislukt: offline-first asset ontbreekt in service worker')
sw_path.write_text(sw, encoding='utf-8')

built_index = index_path.read_text(encoding='utf-8')
built_sw = sw_path.read_text(encoding='utf-8')
for needle in [MARKER, f'/offline-first.js?v={version}', 'data-machinepark-offline-first="1"']:
    if needle not in built_index:
        raise SystemExit(f'Buildvalidatie mislukt: offline-first loader ontbreekt ({needle})')
if f"'/offline-first.js?v={version}'" not in built_sw:
    raise SystemExit('Buildvalidatie mislukt: service worker cachet niet de actuele offline runtime')

print(f'[Machinepark] offline-first runtime wordt versiegebonden geladen ({version})')
