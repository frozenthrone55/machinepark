from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
SCRIPT_START = '<script data-machinepark-build-fix="composed-documents-v1">'
MARKER = 'data-machinepark-build-fix="composed-documents-placement-v1"'

index = INDEX.read_text(encoding='utf-8')
start = index.find(SCRIPT_START)
if start < 0:
    raise SystemExit('Buildvalidatie mislukt: script voor samengestelde documenten ontbreekt')
end = index.find('</script>', start)
if end < 0:
    raise SystemExit('Buildvalidatie mislukt: einde script voor samengestelde documenten ontbreekt')
end += len('</script>')
script = index[start:end]

# build-composed-documents-v1 gebruikte historisch de eerste </body>-match. In
# Machinepark komt </body> ook voor als tekst in de ToDo-afdruk-HTML. Haal het
# volledige feature-script daarom uit zijn huidige positie en plaats het vlak
# voor de echte, laatste afsluitende body-tag.
index = index[:start] + index[end:]
body_pos = index.rfind('</body>')
if body_pos < 0:
    raise SystemExit('Buildvalidatie mislukt: finale </body> ontbreekt')
index = index[:body_pos] + '\n' + script + '\n<meta ' + MARKER + '>\n' + index[body_pos:]

# De ToDo-afdrukstring moet na het verplaatsen opnieuw één geldige JS-string zijn.
needle = "photoHtml+'<section><h2>Historiek</h2>'+history+'</section></body></html>';"
if needle not in index:
    raise SystemExit('Buildvalidatie mislukt: ToDo-afdrukstring bleef onderbroken')
if index.count(SCRIPT_START) != 1:
    raise SystemExit('Buildvalidatie mislukt: samengesteld-overzichtscript staat niet exact één keer in de pagina')
if index.find(SCRIPT_START) > index.rfind('</body>'):
    raise SystemExit('Buildvalidatie mislukt: samengesteld-overzichtscript staat buiten de body')

INDEX.write_text(index, encoding='utf-8')
print('[Machinepark] samengesteld-overzichtscript staat veilig voor de finale body-tag')
