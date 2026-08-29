from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="device-photo-limit-5-v1"'


def replace_exact(old, new, expected, label):
    global index
    count = index.count(old)
    if count != expected:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht {expected}x {label}, gevonden {count}x")
    index = index.replace(old, new)


if MARKER not in index:
    replace_exact('.slice(0,3)', '.slice(0,5)', 1, 'compacte limiet toestelfoto’s')
    replace_exact('.slice(0, 3)', '.slice(0, 5)', 3, 'limiet toestelfoto’s')
    replace_exact('Maximaal 3 foto’s.', 'Maximaal 5 foto’s.', 1, 'uitleg maximum foto’s')
    replace_exact('van maximaal 3 foto’s', 'van maximaal 5 foto’s', 1, 'status maximum foto’s')
    replace_exact('photos.length >= 3', 'photos.length >= 5', 2, 'knoplimiet foto’s')
    replace_exact('const available = 3 - photos.length;', 'const available = 5 - photos.length;', 1, 'beschikbare fotoplaatsen')
    replace_exact('Een toestel kan maximaal 3 foto’s bevatten.', 'Een toestel kan maximaal 5 foto’s bevatten.', 1, 'melding maximum foto’s')
    replace_exact('${photos.length} van 3', '${photos.length} van 5', 1, 'detailteller foto’s')
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    index_path.write_text(index, encoding="utf-8")
    print('[Machinepark] maximaal 5 toestelfoto’s actief')
else:
    print('[Machinepark] limiet van 5 toestelfoto’s reeds actief')
