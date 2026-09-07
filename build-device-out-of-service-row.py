from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'index.html'
text = path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="device-out-of-service-row-v1"'

if MARKER not in text:
    old = 'return `<tr data-device-history="${d.id}">'
    new = 'return `<tr class="${d.status===\'Buiten dienst\'?\'device-row-out-of-service\':\'\'}" data-device-history="${d.id}">'
    count = text.count(old)
    if count < 1:
        raise SystemExit('Buildvalidatie mislukt: geen toestelrij-anker gevonden')
    text = text.replace(old, new)

    style = r'''
<style data-machinepark-build-fix="device-out-of-service-row-v1">
.device-table tr.device-row-out-of-service td{
  background:#f8dada;
  color:#7d2424;
  border-bottom-color:#e7b5b5;
}
.device-table tr.device-row-out-of-service:hover td{background:#f3cccc}
.device-table tr.device-row-out-of-service .muted{color:#9a5050}
.device-table tr.device-row-out-of-service .btn{
  background:#fff8f8;
  color:#7d2424;
  border-color:#dfaaaa;
}
</style>
'''
    if '</head>' not in text:
        raise SystemExit('Buildvalidatie mislukt: </head> ontbreekt voor toestelrijstijl')
    text = text.replace('</head>', style + '\n</head>', 1)
    path.write_text(text, encoding='utf-8')

built = path.read_text(encoding='utf-8')
required = [
    MARKER,
    "d.status==='Buiten dienst'?'device-row-out-of-service':''",
    '.device-table tr.device-row-out-of-service td',
    '.device-table tr.device-row-out-of-service:hover td',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: buiten-dienst rijmarkering ontbreekt ({needle})')
if 'return `<tr data-device-history="${d.id}">' in built:
    raise SystemExit('Buildvalidatie mislukt: niet alle toestelrij-renderpaden zijn gemarkeerd')

print('[Machinepark] volledige toestelrij wordt rood bij status Buiten dienst')
