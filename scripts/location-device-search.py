from pathlib import Path
import re
import json

ROOT = Path('.')
index_path = ROOT / 'index.html'
text = index_path.read_text(encoding='utf-8')

old = "function maintenanceLocationMatches(query){const q=normalizeSearch(query);const groups=maintenanceLocationGroups();return groups.filter(g=>!q||normalizeSearch(g.label).includes(q)).slice(0,12)}"
new = "function locationGroupMatches(group,query){const q=normalizeSearch(query);if(!q)return true;if(normalizeSearch(group.label).includes(q))return true;return (group.devices||[]).some(d=>normalizeSearch(d.assetCode||'').includes(q))}\nfunction locationGroupMatchHint(group,query){const q=normalizeSearch(query);if(!q||normalizeSearch(group.label).includes(q))return '';const codes=(group.devices||[]).filter(d=>normalizeSearch(d.assetCode||'').includes(q)).map(d=>d.assetCode).filter(Boolean).slice(0,3);return codes.length?` · gevonden via ${codes.join(', ')}`:''}\nfunction maintenanceLocationMatches(query){return maintenanceLocationGroups().filter(g=>locationGroupMatches(g,query)).slice(0,12)}"
if old not in text:
    raise SystemExit('maintenanceLocationMatches niet gevonden')
text = text.replace(old, new, 1)

old = "function breakdownLocationMatches(query){const q=normalizeSearch(query);return breakdownLocationGroups().filter(g=>!q||normalizeSearch(g.label).includes(q)).slice(0,12)}"
new = "function breakdownLocationMatches(query){return breakdownLocationGroups().filter(g=>locationGroupMatches(g,query)).slice(0,12)}"
if old not in text:
    raise SystemExit('breakdownLocationMatches niet gevonden')
text = text.replace(old, new, 1)

text = text.replace('placeholder="Typ een locatie…"', 'placeholder="Typ locatie of toestelnummer…"')
text = text.replace('Typ een deel van de locatie. De zoeklijst wordt automatisch korter.', 'Typ een locatie of toestelnummer. De zoeklijst wordt automatisch korter.')
text = text.replace('Geen locatie gevonden.', 'Geen locatie of toestelnummer gevonden.')

needle = "${g.devices.length} actief toestel${g.devices.length===1?'':'len'}</small></button>"
replacement = "${g.devices.length} actief toestel${g.devices.length===1?'':'len'}${esc(locationGroupMatchHint(g,input.value))}</small></button>"
count = text.count(needle)
if count != 2:
    raise SystemExit(f'Verwacht 2 suggestielabels, vond {count}')
text = text.replace(needle, replacement)

text = text.replace('v1.59 • Registraties veilig verwijderen', 'v1.60 • Zoeken op locatie of toestelnummer')
index_path.write_text(text, encoding='utf-8')

sw_path = ROOT / 'sw.js'
sw = sw_path.read_text(encoding='utf-8')
sw = re.sub(r"machinepark-v[0-9.]+-[^']+", 'machinepark-v1.60-location-device-search', sw, count=1)
sw_path.write_text(sw, encoding='utf-8')

package_path = ROOT / 'package.json'
pkg = json.loads(package_path.read_text(encoding='utf-8'))
pkg['version'] = '1.60.0'
package_path.write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

smoke_path = ROOT / 'tests/build-smoke.test.mjs'
test = smoke_path.read_text(encoding='utf-8')
insert_after = "    'maintenanceLocationMatches',\n"
extra = "    'locationGroupMatches',\n    'locationGroupMatchHint',\n    'Typ locatie of toestelnummer…',\n"
if "'locationGroupMatches'" not in test:
    if insert_after not in test:
        raise SystemExit('test invoegpunt niet gevonden')
    test = test.replace(insert_after, insert_after + extra, 1)
test = re.sub(r"machinepark-v[0-9.]+-[^']+", 'machinepark-v1.60-location-device-search', test)
smoke_path.write_text(test, encoding='utf-8')

validator_path = ROOT / 'scripts/build-machinepark.py'
validator = validator_path.read_text(encoding='utf-8')
needle = '    "locatiegericht onderhoud": "id=\\"maintenanceLocationSearch\\"",\n'
extra = '    "zoeken op toestelnummer": "locationGroupMatches",\n    "zoekhint locatie of toestel": "Typ locatie of toestelnummer…",\n'
if '"zoeken op toestelnummer"' not in validator:
    if needle not in validator:
        raise SystemExit('validator invoegpunt niet gevonden')
    validator = validator.replace(needle, needle + extra, 1)
validator = re.sub(r"machinepark-v[0-9.]+-[^\"]+", 'machinepark-v1.60-location-device-search', validator)
validator_path.write_text(validator, encoding='utf-8')
