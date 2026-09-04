from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
sw_path = ROOT / 'sw.js'
manual_path = ROOT / 'manual-library.js'

index = index_path.read_text(encoding='utf-8')
sw = sw_path.read_text(encoding='utf-8')
manual = manual_path.read_text(encoding='utf-8')

MARKER = 'data-machinepark-service-visits="v1"'
service_js = (ROOT / 'service-visits.js').read_text(encoding='utf-8')
service_css = (ROOT / 'service-visits.css').read_text(encoding='utf-8')
service_hash = hashlib.sha256((service_js + '\n' + service_css).encode('utf-8')).hexdigest()[:12]
service_js_url = f'/service-visits.js?v={service_hash}'
service_css_url = f'/service-visits.css?v={service_hash}'

if 'window.machineparkManualsForDevice' not in manual or 'window.machineparkManualListHtml' not in manual:
    raise SystemExit('Buildvalidatie mislukt: handleidingen zijn niet beschikbaar voor servicebezoeken')

if '</head>' not in index or '</body>' not in index:
    raise SystemExit('Buildvalidatie mislukt: HTML-afsluiters ontbreken voor servicebezoeken')

index = re.sub(
    r'<link rel="stylesheet" href="/service-visits\.css(?:\?v=[^"]*)?" data-machinepark-service-visits="v1">\\n?',
    '',
    index,
)
index = re.sub(
    r'<script src="/service-visits\.js(?:\?v=[^"]*)?" data-machinepark-service-visits="v1"></script>\\n?',
    '',
    index,
)
index = index.replace('</head>', f'<link rel="stylesheet" href="{service_css_url}" {MARKER}>\n</head>', 1)
index = index.replace('</body>', f'<script src="{service_js_url}" {MARKER}></script>\n</body>', 1)
index_path.write_text(index, encoding='utf-8')

sw = re.sub(r"'/service-visits\.js(?:\?v=[^']*)?'", f"'{service_js_url}'", sw)
sw = re.sub(r"'/service-visits\.css(?:\?v=[^']*)?'", f"'{service_css_url}'", sw)
if f"'{service_js_url}'" not in sw or f"'{service_css_url}'" not in sw:
    api_pos = sw.find('const CACHEABLE_API')
    assets_end = sw.rfind('];', 0, api_pos if api_pos >= 0 else len(sw))
    if assets_end < 0:
        raise SystemExit('Buildvalidatie mislukt: service-worker assetlijst ontbreekt voor servicebezoeken')
    sw = sw[:assets_end] + f"  '{service_js_url}',\n  '{service_css_url}',\n" + sw[assets_end:]
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
    service_css_url,
    service_js_url,
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: servicebezoek ontbreekt ({needle})')

for needle in [
    'serviceVisitId',
    'serviceReportId',
    'serviceReportNumber',
    'Serviceverslagen',
    'Eén serviceverslag, meerdere locaties.',
    'Concept bewaren',
    'machineparkManualListHtml',
    'machineparkServiceVisitPdfModel',
    'servicePrintLayout',
    'workPages',
    'serviceVisitDeviceCount',
    'serviceVisitTotalMinutes',
    'Servicetijd voor volledige actieve locatie',
    'Servicetijd / toestellen',
    'service-visit-mail-btn',
    '+ Toestel toevoegen',
    'deleteServiceReportAtomic',
    'service-visit-delete-btn',
    'maintenance.delete',
    'breakdowns.delete',
    'data-kind="otherworks"',
    'serviceKind:\'other\'',
    'otherWorkCount',
    'svOtherWorkTypeNames',
    'recordPartsBoxHtml',
    'service-record-parts-box',
]:
    if needle not in (ROOT / 'service-visits.js').read_text(encoding='utf-8'):
        raise SystemExit(f'Buildvalidatie mislukt: servicebezoekfunctie ontbreekt ({needle})')

if f"'{service_js_url}'" not in sw or f"'{service_css_url}'" not in sw:
    raise SystemExit('Buildvalidatie mislukt: versiegebonden servicebezoekassets ontbreken in service worker')

print(f'[Machinepark] serviceverslagen cacheveilig gekoppeld · asset {service_hash}')
