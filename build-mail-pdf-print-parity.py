from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

DIRECT_MARKER = 'data-machinepark-' + 'build-fix=' + '"mail-pdf-direct-v4"'
MARKER = 'data-machinepark-build-fix="mail-pdf-print-parity-v2"'

if DIRECT_MARKER not in index:
    raise SystemExit("Buildvalidatie mislukt: directe Mail PDF v4 ontbreekt voor print-pariteit")

required = [
    ".replace(/[·•]/g, '.')",
    ".replace(/[×✕✖]/g, 'x')",
    'function serviceOneOffParts(record)',
    'function serviceWorkSummary(kind, record)',
    'function servicePhotos(record)',
    "cleanText(item?.supplier)",
    "cleanText(item?.supplierCode)",
    "cleanText(item?.description)",
    "label:'Werkminuten / toestellen'",
    "label:'Eenmalige onderdelen'",
    "headerTitle: `Machinepark . ${title}`",
    "record.photos",
    "photoTitle: 'Foto’s bij verslag'",
    "photoColumns: 2",
    "Afgedrukt vanuit Machinepark",
]

for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: Mail PDF wijkt af van afdrukopbouw ({needle})")

if index.count("label:'Werkminuten / toestellen'") < 2:
    raise SystemExit("Buildvalidatie mislukt: werkminuten ontbreken bij onderhoud of depannage")

if MARKER not in index:
    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor Mail PDF print-pariteit')
    index = index[:pos] + f'\n<span {MARKER} hidden></span>\n' + index[pos:]
    index_path.write_text(index, encoding='utf-8')

print('[Machinepark] Mail PDF volgt afdrukopbouw voor depannage en onderhoud, inclusief veilige tekens en fotos')
