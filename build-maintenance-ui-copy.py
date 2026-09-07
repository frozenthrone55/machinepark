from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')

old = '<div class=\"field maintenance-work\"><label>Uitgevoerde werkzaamheden / notitie</label>'
new = '<div class=\"field maintenance-work\"><label>Opmerkingen</label>'

count = index.count(old)
if count != 1:
    raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x onderhoudslabel per machine, gevonden {count}x')

index = index.replace(old, new, 1)
index_path.write_text(index, encoding='utf-8')

if new not in index:
    raise SystemExit('Buildvalidatie mislukt: label Opmerkingen ontbreekt per onderhoudsmachine')

print('[Machinepark] onderhoudslabel per machine gewijzigd naar Opmerkingen')
