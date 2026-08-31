from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="offline-first-loader-v1"'

if MARKER not in index:
    if '</head>' not in index or '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-afsluiters ontbreken voor offline-first loader')
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    loader = '<script src="/offline-first.js" data-machinepark-offline-first="1"></script>\n'
    body_pos = index.rfind('</body>')
    index = index[:body_pos] + loader + index[body_pos:]
    index_path.write_text(index, encoding='utf-8')

for needle in [MARKER, '/offline-first.js', 'data-machinepark-offline-first="1"']:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: offline-first loader ontbreekt ({needle})')

print('[Machinepark] offline-first runtime wordt geladen')
