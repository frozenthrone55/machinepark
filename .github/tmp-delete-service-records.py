from pathlib import Path
import json
import re

ROOT = Path('.')
index_path = ROOT / 'index.html'
text = index_path.read_text(encoding='utf-8')

# 1. Atomaire verwijdering + voorraadteruggave.
marker = "function deviceSearchField(selectedId='')"
if marker not in text:
    raise SystemExit('deviceSearchField niet gevonden')
if 'function deleteServiceRecordAtomic(' not in text:
    helper = r'''function deleteServiceRecordAtomic(storeName,record){return new Promise((res,rej)=>{if(!['maintenance','breakdowns'].includes(storeName)){rej(new Error('Ongeldig registratietype.'));return}if(!record?.id){rej(new Error('Registratie niet gevonden.'));return}const totals={};(record.usedParts||[]).forEach(u=>{const id=String(u?.partId||'').trim(),qty=Number(u?.qty||0);if(id&&qty>0)totals[id]=(totals[id]||0)+qty});const updates=[];const now=new Date().toISOString();for(const [id,qty] of Object.entries(totals)){const part=state.parts.find(p=>p.id===id);if(!part){rej(new Error(`Onderdeel ${id} bestaat niet meer. De registratie is niet verwijderd zodat de voorraad niet fout kan worden.`));return}updates.push({...part,stock:Number(part.stock||0)+qty,updatedAt:now})}let tr;try{tr=db.transaction([storeName,'parts'],'readwrite')}catch(error){rej(error);return}const records=tr.objectStore(storeName),parts=tr.objectStore('parts');updates.forEach(part=>parts.put(part));records.delete(record.id);tr.oncomplete=()=>{scheduleCentralSync();res({restoredParts:updates.length,restoredQuantity:Object.values(totals).reduce((sum,qty)=>sum+Number(qty||0),0)})};tr.onerror=()=>rej(tr.error||new Error('Verwijderen mislukt.'));tr.onabort=()=>rej(tr.error||new Error('Verwijderen afgebroken.'))})}
async function deleteServiceRecord(storeName,id){const collection=storeName==='maintenance'?state.maintenance:storeName==='breakdowns'?state.breakdowns:null;if(!collection)return;const record=collection.find(item=>item.id===id);if(!record){toast('Registratie niet meer gevonden');return}const kind=storeName==='maintenance'?'onderhoud':'depannage',device=deviceName(record.deviceId,recordMoment(record)),hasParts=(record.usedParts||[]).some(u=>u?.partId&&Number(u?.qty||0)>0);const message=`${kind==='onderhoud'?'Onderhoud':'Depannage'} van ${device} definitief verwijderen?${hasParts?'\n\nAlle gebruikte onderdelen van deze registratie worden automatisch terug op voorraad gezet.':'\n\nEr zijn geen gebruikte onderdelen om terug op voorraad te zetten.'}\n\nDeze actie wordt opgenomen in het wijzigingslogboek.`;if(!confirm(message))return;try{const result=await deleteServiceRecordAtomic(storeName,record);closeModal();await refresh();toast(`${kind==='onderhoud'?'Onderhoud':'Depannage'} verwijderd${result.restoredParts?` · ${result.restoredParts} onderdeel${result.restoredParts===1?'':'types'} terug op voorraad`:''}`)}catch(error){console.error('Registratie verwijderen',error);alert(error?.message||'Verwijderen mislukt.')}}
'''
    text = text.replace(marker, helper + marker, 1)

# 2. Onderhoud-details: verwijderknop en event.
start = text.find('function showMaintenanceDetails(id)')
end = text.find('function breakdownForm(b={})', start)
if start < 0 or end < 0:
    raise SystemExit('showMaintenanceDetails blok niet gevonden')
block = text[start:end]
if 'deleteMaintenanceFromDetails' not in block:
    old = "<div class=\"modal-foot\"><button class=\"btn\" type=\"button\" id=\"closeMaintenanceDetails\">Sluiten</button>${window.machineparkCanEdit?.maintenance?'<button class=\"btn primary\" type=\"button\" id=\"editMaintenanceFromDetails\">Onderhoud wijzigen</button>':''}</div>"
    new = "<div class=\"modal-foot\"><button class=\"btn\" type=\"button\" id=\"closeMaintenanceDetails\">Sluiten</button>${window.machineparkCanEdit?.maintenance?'<button class=\"btn danger\" type=\"button\" id=\"deleteMaintenanceFromDetails\">Verwijderen</button><button class=\"btn primary\" type=\"button\" id=\"editMaintenanceFromDetails\">Onderhoud wijzigen</button>':''}</div>"
    if old not in block:
        raise SystemExit('Onderhoud footer niet gevonden')
    block = block.replace(old, new, 1)
    old_events = "const editMaintenanceBtn=$('#editMaintenanceFromDetails');if(editMaintenanceBtn)editMaintenanceBtn.onclick=()=>{closeModal();openMaintenance(id)}}"
    new_events = "const deleteMaintenanceBtn=$('#deleteMaintenanceFromDetails');if(deleteMaintenanceBtn)deleteMaintenanceBtn.onclick=()=>deleteServiceRecord('maintenance',id);const editMaintenanceBtn=$('#editMaintenanceFromDetails');if(editMaintenanceBtn)editMaintenanceBtn.onclick=()=>{closeModal();openMaintenance(id)}}"
    if old_events not in block:
        raise SystemExit('Onderhoud events niet gevonden')
    block = block.replace(old_events, new_events, 1)
    text = text[:start] + block + text[end:]

# 3. Bestaande depannage: verwijderknop in de bewerkmodal.
start = text.find('function openBreakdown(id)')
end = text.find('function showDeviceHistory(id)', start)
if start < 0 or end < 0:
    raise SystemExit('openBreakdown blok niet gevonden')
block = text[start:end]
if 'deleteBreakdownFromDetails' not in block:
    old = "setTimeout(()=>{initDeviceSearch(old.deviceId||'');initUsageControls()},0);return}"
    new = "setTimeout(()=>{initDeviceSearch(old.deviceId||'');initUsageControls();if(window.machineparkCanEdit?.breakdowns){const foot=$('#modal .modal-foot');if(foot&&!$('#deleteBreakdownFromDetails')){const btn=document.createElement('button');btn.type='button';btn.id='deleteBreakdownFromDetails';btn.className='btn danger';btn.textContent='Verwijderen';btn.onclick=()=>deleteServiceRecord('breakdowns',old.id);foot.insertBefore(btn,foot.querySelector('.btn.primary')||null)}}},0);return}"
    if old not in block:
        raise SystemExit('Depannage init niet gevonden')
    block = block.replace(old, new, 1)
    text = text[:start] + block + text[end:]

# 4. Zichtbare versie corrigeren.
text = re.sub(r'v1\.\d+\s*•\s*[^<]+</div>\n\s*</aside>', 'v1.59 • Registraties veilig verwijderen</div>\n  </aside>', text, count=1)
index_path.write_text(text, encoding='utf-8')

# 5. Service-worker cache.
sw_path = ROOT / 'sw.js'
sw = sw_path.read_text(encoding='utf-8')
sw = re.sub(r"machinepark-v[0-9.]+-[^']+", 'machinepark-v1.59-delete-service-records', sw, count=1)
sw_path.write_text(sw, encoding='utf-8')

# 6. Build smoke tests uitbreiden.
test_path = ROOT / 'tests/build-smoke.test.mjs'
t = test_path.read_text(encoding='utf-8')
if 'deleteServiceRecordAtomic' not in t:
    needle = "    'breakdownBatchSelectedItems',\n"
    repl = "    'breakdownBatchSelectedItems',\n    'deleteServiceRecordAtomic',\n    \"deleteServiceRecord('maintenance',id)\",\n    \"deleteServiceRecord('breakdowns',old.id)\",\n    'Alle gebruikte onderdelen van deze registratie worden automatisch terug op voorraad gezet.',\n"
    if needle not in t:
        raise SystemExit('Test invoegpunt niet gevonden')
    t = t.replace(needle, repl, 1)
t = re.sub(r"machinepark-v[0-9.]+-[^']+", 'machinepark-v1.59-delete-service-records', t)
test_path.write_text(t, encoding='utf-8')

# 7. Buildvalidator uitbreiden.
validator_path = ROOT / 'scripts/build-machinepark.py'
v = validator_path.read_text(encoding='utf-8')
if 'registraties verwijderen' not in v:
    needle = '    "depannage per toestel": "breakdown-machine-card",\n'
    repl = needle + '    "registraties verwijderen": "deleteServiceRecordAtomic",\n    "onderhoud verwijderen": "deleteMaintenanceFromDetails",\n    "depannage verwijderen": "deleteBreakdownFromDetails",\n'
    if needle not in v:
        raise SystemExit('Validator invoegpunt niet gevonden')
    v = v.replace(needle, repl, 1)
v = re.sub(r"machinepark-v[0-9.]+-[^\"]+", 'machinepark-v1.59-delete-service-records', v)
validator_path.write_text(v, encoding='utf-8')

# 8. Packageversie gelijkzetten.
pkg_path = ROOT / 'package.json'
pkg = json.loads(pkg_path.read_text(encoding='utf-8'))
pkg['version'] = '1.59.0'
pkg_path.write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
