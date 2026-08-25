from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')

anchor="function filterQuery(obj,fields){if(!state.query)return true;const q=state.query.toLowerCase();return fields.some(f=>String(obj[f]??'').toLowerCase().includes(q))}"
helpers=r'''function normalizeSearch(value){return String(value??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()}
function searchIncludes(text){const q=normalizeSearch(state.query);return !q||normalizeSearch(text).includes(q)}
function linkedDeviceSearchText(deviceId,moment=''){const d=state.devices.find(x=>x.id===deviceId);if(!d)return '';const locs=locationEvents(d).map(x=>x.location||'').join(' ');const current=deviceLocationAt(d,moment)||'';return [d.assetCode,d.brand,d.model,d.serial,d.status,d.notes,d.installDate,dateFmt(d.installDate),d.nextHalf,dateFmt(d.nextHalf),d.nextAnnual,dateFmt(d.nextAnnual),current,locs].join(' ')}
function linkedPartsSearchText(items=[]){return (items||[]).map(i=>{const p=state.parts.find(x=>x.id===i.partId);return p?[p.artNr,p.description,p.deviceBrand,p.supplierCode,p.warehouse,i.qty].join(' '):i.partId||''}).join(' ')}
function deviceMatchesQuery(d){if(!state.query)return true;const locs=locationEvents(d).map(x=>x.location||'').join(' ');return searchIncludes([d.assetCode,d.brand,d.model,d.serial,d.status,d.notes,d.installDate,dateFmt(d.installDate),d.nextHalf,dateFmt(d.nextHalf),d.nextAnnual,dateFmt(d.nextAnnual),deviceLocationAt(d)||'',locs].join(' '))}
function maintenanceMatchesQuery(m){if(!state.query)return true;const moment=recordMoment(m);return searchIncludes([m.type,m.date,m.time,recordDateTimeFmt(m),m.technician,m.notes,linkedDeviceSearchText(m.deviceId,moment),linkedPartsSearchText(m.usedParts)].join(' '))}
function breakdownMatchesQuery(b){if(!state.query)return true;const moment=recordMoment(b);return searchIncludes([b.date,b.time,recordDateTimeFmt(b),b.issue,b.diagnosis,b.solution,b.technician,b.priority,b.status,linkedDeviceSearchText(b.deviceId,moment),linkedPartsSearchText(b.usedParts)].join(' '))}
function partMatchesQuery(p){if(!state.query)return true;return searchIncludes([p.artNr,p.description,p.deviceBrand,p.supplierCode,p.warehouse,p.stock,p.minStock,p.price].join(' '))}
'''
if anchor not in s:
    raise SystemExit('Basis filterQuery niet gevonden')
if 'function maintenanceMatchesQuery(' not in s:
    s=s.replace(anchor,anchor+'\n'+helpers,1)

# Verwijder de oude beperkte deviceMatchesQuery wanneer die naast de nieuwe helper staat.
old_device="function deviceMatchesQuery(d){if(!state.query)return true;const q=state.query.toLowerCase();const base=['assetCode','brand','model','serial'].some(f=>String(d[f]??'').toLowerCase().includes(q));return base||locationEvents(d).some(e=>String(e.location||'').toLowerCase().includes(q))}"
# Na invoegen van helpers staat de nieuwe functie eerder; verwijder alleen de laatste oude variant.
if old_device in s:
    pos=s.rfind(old_device)
    first=s.find('function deviceMatchesQuery(d){')
    if pos!=first:
        s=s[:pos]+s[pos+len(old_device):]

old_m="let list=state.maintenance.filter(m=>(!f||m.type===f)&&(filterQuery(m,['technician','notes'])||deviceName(m.deviceId,recordMoment(m)).toLowerCase().includes(state.query.toLowerCase()))).sort((a,b)=>recordMoment(b).localeCompare(recordMoment(a)));"
new_m="let list=state.maintenance.filter(m=>(!f||m.type===f)&&maintenanceMatchesQuery(m)).sort((a,b)=>recordMoment(b).localeCompare(recordMoment(a)));"
if old_m in s:s=s.replace(old_m,new_m,1)

old_b="let list=state.breakdowns.filter(b=>(!fs||b.status===fs)&&(!fp||b.priority===fp)&&(filterQuery(b,['issue','diagnosis','solution','technician'])||deviceName(b.deviceId,recordMoment(b)).toLowerCase().includes(state.query.toLowerCase()))).sort((a,b)=>recordMoment(b).localeCompare(recordMoment(a)));"
new_b="let list=state.breakdowns.filter(b=>(!fs||b.status===fs)&&(!fp||b.priority===fp)&&breakdownMatchesQuery(b)).sort((a,b)=>recordMoment(b).localeCompare(recordMoment(a)));"
if old_b in s:s=s.replace(old_b,new_b,1)

old_p="&&filterQuery(p,['artNr','description','deviceBrand','supplierCode','warehouse'])}).sort((a,b)=>(a.artNr||'').localeCompare(b.artNr||''));"
new_p="&&partMatchesQuery(p)}).sort((a,b)=>(a.artNr||'').localeCompare(b.artNr||''));"
if old_p in s:s=s.replace(old_p,new_p,1)

pattern=r"function renderGlobalSearchResults\(\)\{.*?\n\}\nfunction closeGlobalSearch\(\)\{const box=\$\('#globalSearchResults'\);if\(box\)box\.classList\.remove\('show'\)\}"
replacement=r'''function renderGlobalSearchResults(){
 const box=$('#globalSearchResults'),input=$('#globalSearch');if(!box||!input)return;
 const q=normalizeSearch(state.query);
 if(!q){box.classList.remove('show');box.innerHTML='';return}
 const deviceMatches=state.devices.filter(deviceMatchesQuery).slice(0,7);
 const maintenanceMatches=state.maintenance.filter(maintenanceMatchesQuery).sort((a,b)=>recordMoment(b).localeCompare(recordMoment(a))).slice(0,6);
 const breakdownMatches=state.breakdowns.filter(breakdownMatchesQuery).sort((a,b)=>recordMoment(b).localeCompare(recordMoment(a))).slice(0,6);
 const partMatches=state.parts.filter(partMatchesQuery).slice(0,7);
 let html='';
 if(deviceMatches.length){html+='<div class="global-search-head">Toestellen & locaties</div>'+deviceMatches.map(d=>`<button type="button" class="global-search-result" data-global-device="${d.id}"><strong>☕ ${esc(d.assetCode||d.model||'Toestel')}</strong><small>${esc(deviceLocationAt(d)||'Geen locatie')} · ${esc([d.brand,d.model].filter(Boolean).join(' ')||'Geen toesteltype')}</small></button>`).join('')}
 if(maintenanceMatches.length){html+='<div class="global-search-head">Onderhoud</div>'+maintenanceMatches.map(m=>`<button type="button" class="global-search-result" data-global-maintenance="${m.id}"><strong>🔧 ${esc(deviceName(m.deviceId,recordMoment(m)))} · ${esc(m.type||'Onderhoud')}</strong><small>${esc(recordDateTimeFmt(m))} · ${esc(m.technician||'Geen technieker')}</small></button>`).join('')}
 if(breakdownMatches.length){html+='<div class="global-search-head">Depannages</div>'+breakdownMatches.map(b=>`<button type="button" class="global-search-result" data-global-breakdown="${b.id}"><strong>⚠ ${esc(deviceName(b.deviceId,recordMoment(b)))} · ${esc(b.issue||'Depannage')}</strong><small>${esc(b.priority||'')} · ${esc(b.status||'')} · ${esc(b.technician||'Geen technieker')}</small></button>`).join('')}
 if(partMatches.length){html+='<div class="global-search-head">Onderdelen</div>'+partMatches.map(p=>`<button type="button" class="global-search-result" data-global-part="${p.id}"><strong>▣ ${esc(p.artNr||'—')} · ${esc(p.description||'Onderdeel')}</strong><small>${esc(p.deviceBrand||'Geen merk')} · voorraad ${Number(p.stock||0)}</small></button>`).join('')}
 if(!html)html='<div class="global-search-empty">Geen resultaten gevonden in Machinepark.</div>';
 box.innerHTML=html;box.classList.add('show');
}
function closeGlobalSearch(){const box=$('#globalSearchResults');if(box)box.classList.remove('show')}'''
s,n=re.subn(pattern,replacement,s,count=1,flags=re.S)
if n!=1:
    raise SystemExit('Globale zoekfunctie niet gevonden')

old_click="document.body.addEventListener('click',e=>{const gd=e.target.closest('[data-global-device]');if(gd){closeGlobalSearch();showDeviceHistory(gd.dataset.globalDevice);return}const gp=e.target.closest('[data-global-part]');if(gp){closeGlobalSearch();openPart(gp.dataset.globalPart);return}"
new_click="document.body.addEventListener('click',e=>{const gm=e.target.closest('[data-global-maintenance]');if(gm){closeGlobalSearch();showMaintenanceDetails(gm.dataset.globalMaintenance);return}const gb=e.target.closest('[data-global-breakdown]');if(gb){closeGlobalSearch();openBreakdown(gb.dataset.globalBreakdown);return}const gd=e.target.closest('[data-global-device]');if(gd){closeGlobalSearch();showDeviceHistory(gd.dataset.globalDevice);return}const gp=e.target.closest('[data-global-part]');if(gp){closeGlobalSearch();openPart(gp.dataset.globalPart);return}"
if old_click not in s:
    raise SystemExit('Globale klikhandler niet gevonden')
s=s.replace(old_click,new_click,1)

s=s.replace('placeholder="Zoek toestel, locatie, onderdeel…"','placeholder="Zoek overal in Machinepark…"',1)

required=['maintenanceMatchesQuery(m)','breakdownMatchesQuery(b)','partMatchesQuery(p)','data-global-maintenance','data-global-breakdown','Zoek overal in Machinepark…']
missing=[x for x in required if x not in s]
if missing:raise SystemExit('Onvolledige patch: '+', '.join(missing))

p.write_text(s,encoding='utf-8')

sw=Path('sw.js')
ws=sw.read_text(encoding='utf-8')
ws=ws.replace("machinepark-v1.23","machinepark-v1.24")
sw.write_text(ws,encoding='utf-8')
