from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="existing-location-picker-v1"'

if MARKER not in index:
    helper_anchor = 'function deviceForm(d={}){'
    helper = '''function existingDeviceLocations(current=''){const values=new Set();state.devices.forEach(device=>{const active=String(deviceLocationAt(device)||device.location||'').trim();if(active)values.add(active);(Array.isArray(device.locationHistory)?device.locationHistory:[]).forEach(row=>{const loc=String(row?.location||'').trim();if(loc)values.add(loc)})});return [...values].filter(Boolean).sort((a,b)=>a.localeCompare(b,'nl',{sensitivity:'base'}))}
function initExistingLocationPicker(){const select=document.getElementById('deviceExistingLocationChoice'),input=document.getElementById('deviceNewLocation');if(!select||!input)return;select.onchange=()=>{if(select.value)input.value=select.value}}
function deviceForm(d={}){'''
    if index.count(helper_anchor) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: deviceForm niet eenduidig gevonden ({index.count(helper_anchor)}x)')
    index = index.replace(helper_anchor, helper, 1)

    old = '<div class="field"><label>Nieuwe locatie</label><input name="newLocation" placeholder="bv. onthaal, verdieping 1"></div>'
    new = '<div class="field"><label>Bestaande locatie kiezen</label><select id="deviceExistingLocationChoice"><option value="">Kies bestaande locatie…</option>${existingDeviceLocations(currentLoc).map(loc=>`<option value="${esc(loc)}">${esc(loc)}</option>`).join(\'\')}</select><div class="muted" style="font-size:11px;margin-top:4px">Kies een bestaande locatie of vul hieronder zelf een nieuwe locatie in.</div></div><div class="field"><label>Nieuwe locatie</label><input id="deviceNewLocation" name="newLocation" placeholder="bv. onthaal, verdieping 1"></div>'
    if index.count(old) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: veld Nieuwe locatie niet eenduidig gevonden ({index.count(old)}x)')
    index = index.replace(old, new, 1)

    old_open = "await put('devices',obj);closeModal();await refresh();toast(editing&&val(fd,'newLocation')?'Toestel en locatiewijziging opgeslagen':'Toestel opgeslagen')})}"
    new_open = "await put('devices',obj);closeModal();await refresh();toast(editing&&val(fd,'newLocation')?'Toestel en locatiewijziging opgeslagen':'Toestel opgeslagen')});setTimeout(initExistingLocationPicker,0)}"
    if index.count(old_open) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: openDevice-einde niet eenduidig gevonden ({index.count(old_open)}x)')
    index = index.replace(old_open, new_open, 1)

    index = index.replace('</body>', f'<span {MARKER} hidden></span></body>', 1)
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'function existingDeviceLocations',
    'Bestaande locatie kiezen',
    'deviceExistingLocationChoice',
    'setTimeout(initExistingLocationPicker,0)',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: bestaande-locatiekeuze ontbreekt ({needle})')

print('[Machinepark] bestaande locaties kiesbaar bij locatiewijziging')
