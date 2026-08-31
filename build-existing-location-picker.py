from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="existing-location-picker-v2"'

if MARKER not in index:
    helper_anchor = 'function deviceForm(d={}){'
    helper = '''function existingDeviceLocations(current=''){const values=new Set();state.devices.forEach(device=>{const active=String(deviceLocationAt(device)||device.location||'').trim();if(active)values.add(active);(Array.isArray(device.locationHistory)?device.locationHistory:[]).forEach(row=>{const loc=String(row?.location||'').trim();if(loc)values.add(loc)})});return [...values].filter(Boolean).sort((a,b)=>a.localeCompare(b,'nl',{sensitivity:'base'}))}\nfunction deviceForm(d={}){'''
    if index.count(helper_anchor) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: deviceForm niet eenduidig gevonden ({index.count(helper_anchor)}x)')
    index = index.replace(helper_anchor, helper, 1)

    old = '<div class="field"><label>Nieuwe locatie</label><input name="newLocation" placeholder="bv. onthaal, verdieping 1"></div>'
    new = '<div class="field"><label>Nieuwe locatie</label><input id="deviceNewLocation" name="newLocation" list="deviceExistingLocations" autocomplete="off" placeholder="Typ of kies een locatie…"><datalist id="deviceExistingLocations">${existingDeviceLocations(currentLoc).map(loc=>`<option value="${esc(loc)}"></option>`).join(\'\')}</datalist><div class="muted" style="font-size:11px;margin-top:4px">Typ om bestaande locaties te zoeken en klik een suggestie aan. Bestaat de locatie nog niet, laat dan gewoon je nieuwe naam staan.</div></div>'
    if index.count(old) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: veld Nieuwe locatie niet eenduidig gevonden ({index.count(old)}x)')
    index = index.replace(old, new, 1)

    index = index.replace('</body>', f'<span {MARKER} hidden></span></body>', 1)
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'function existingDeviceLocations',
    'list="deviceExistingLocations"',
    '<datalist id="deviceExistingLocations">',
    'Typ om bestaande locaties te zoeken',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: locatie-zoekveld ontbreekt ({needle})')

if 'Bestaande locatie kiezen' in index or 'deviceExistingLocationChoice' in index:
    raise SystemExit('Buildvalidatie mislukt: apart locatiekeuzeveld is nog aanwezig')

print('[Machinepark] één zoekveld voor bestaande of nieuwe locatie actief')
