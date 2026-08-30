from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
SCRIPT_START = '<script data-machinepark-build-fix="work-orders-v1">'

start = index.find(SCRIPT_START)
if start < 0:
    raise SystemExit('Buildvalidatie mislukt: werkbonscript niet gevonden voor veilige plaatsing')
end = index.find('</script>', start)
if end < 0:
    raise SystemExit('Buildvalidatie mislukt: werkbonscript heeft geen afsluitende script-tag')
end += len('</script>')
block = index[start:end]
index = index[:start] + index[end:]
body_pos = index.rfind('</body>')
if body_pos < 0:
    raise SystemExit('Buildvalidatie mislukt: echte </body> ontbreekt voor werkbonscript')
index = index[:body_pos] + block + '\n' + index[body_pos:]
index_path.write_text(index, encoding='utf-8')

if index.rfind(SCRIPT_START) < index.rfind('</head>'):
    raise SystemExit('Buildvalidatie mislukt: werkbonscript staat niet in document-body')

print('[Machinepark] werkbonmodule veilig aan het documenteinde geplaatst')
