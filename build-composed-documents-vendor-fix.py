from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
MARKER = 'data-machinepark-build-fix="composed-documents-vendor-v1"'
CDN = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js'
LOCAL = './vendor/jspdf.umd.min.js'

index = INDEX.read_text(encoding='utf-8')
if MARKER not in index:
    if 'data-machinepark-build-fix="composed-documents-v1"' not in index:
        raise SystemExit('Buildvalidatie mislukt: samengestelde documenten ontbreken voor lokale PDF-fix')
    if CDN not in index:
        raise SystemExit('Buildvalidatie mislukt: PDF-bron van samengestelde documenten niet gevonden')
    index = index.replace(CDN, LOCAL)
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
if MARKER not in built or LOCAL not in built:
    raise SystemExit('Buildvalidatie mislukt: lokale PDF-library voor samengestelde documenten ontbreekt')
if CDN in built:
    raise SystemExit('Buildvalidatie mislukt: externe jsPDF CDN bleef aanwezig')

print('[Machinepark] samengestelde documenten gebruiken lokale jsPDF-library')
