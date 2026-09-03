from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
sw_path = ROOT / 'sw.js'
manual_path = ROOT / 'manual-library.js'

index = index_path.read_text(encoding='utf-8')
sw = sw_path.read_text(encoding='utf-8')
manual = manual_path.read_text(encoding='utf-8')

MARKER = 'data-machinepark-service-visits="v1"'

if 'window.machineparkManualsForDevice' not in manual or 'window.machineparkManualListHtml' not in manual:
    raise SystemExit('Buildvalidatie mislukt: handleidingen zijn niet beschikbaar voor servicebezoeken')

if MARKER not in index:
    if '</head>' not in index or '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-afsluiters ontbreken voor servicebezoeken')
    index = index.replace('</head>', f'<link rel="stylesheet" href="/service-visits.css" {MARKER}>\\n</head>', 1)
    index = index.replace('</body>', f'<script src="/service-visits.js" {MARKER}></script>\\n</body>', 1)
    index_path.write_text(index, encoding='utf-8')

asset_anchor = "  '/offline-first.js',\\n"
if "'/service-visits.js'" not in sw or "'/service-visits.css'" not in sw:
    if asset_anchor not in sw:
        raise SystemExit('Buildvalidatie mislukt: service-worker assetanker ontbreekt voor servicebezoeken')
    sw = sw.replace(asset_anchor, asset_anchor + "  '/service-visits.js',\\n  '/service-visits.css',\\n", 1)

sw = re.sub(
    r"const CACHE='machinepark-v1\\.68\\.9-[^']+';",
    "const CACHE='machinepark-v1.68.9-service-visits-v1';",
    sw,
    count=1,
)
sw_path.write_text(sw, encoding='utf-8')

built = index_path.read_text(encoding='utf-8')
required = [
    MARKER,
    '/service-visits.css',
    '/service-visits.js',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: servicebezoek ontbreekt ({needle})')

for needle in [
    'serviceVisitId',
    'Servicebezoeken per locatie',
    'Concept bewaren',
    'machineparkManualListHtml',
    'machineparkServiceVisitPdfModel',
    'service-visit-mail-btn',
    '+ Toestel toevoegen',
]:
    if needle not in (ROOT / 'service-visits.js').read_text(encoding='utf-8'):
        raise SystemExit(f'Buildvalidatie mislukt: servicebezoekfunctie ontbreekt ({needle})')

if "'/service-visits.js'" not in sw or "'/service-visits.css'" not in sw:
    raise SystemExit('Buildvalidatie mislukt: servicebezoekassets ontbreken in service worker')

print('[Machinepark] gezamenlijke servicebezoeken per locatie met concepten, handleidingen, afdruk en Mail PDF actief')
