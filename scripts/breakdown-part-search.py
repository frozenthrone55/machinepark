from pathlib import Path
import re

p = Path('index.html')
s = p.read_text(encoding='utf-8')

# Onderhoud en depannages krijgen dezelfde autocomplete voor gebruikte onderdelen.
s = s.replace("${usageBuilder(m.usedParts||[])}", "${usageBuilder(m.usedParts||[],true)}", 1)
s = s.replace("${usageBuilder(b.usedParts||[])}", "${usageBuilder(b.usedParts||[],true)}", 1)

css = '''
.usage-autocomplete,.device-autocomplete{position:relative;min-width:0}.usage-autocomplete .usage-search,.device-autocomplete .device-search{width:100%;border:1px solid var(--line);border-radius:9px;padding:9px;outline:none;background:white}.usage-autocomplete .usage-search:focus,.device-autocomplete .device-search:focus{border-color:#7ea598;box-shadow:0 0 0 3px rgba(44,106,88,.09)}.usage-suggestions,.device-suggestions{position:absolute;z-index:1600;left:0;right:0;top:calc(100% + 4px);max-height:260px;overflow:auto;background:#fff;border:1px solid var(--line);border-radius:11px;box-shadow:0 14px 34px rgba(20,45,38,.18);display:none}.usage-suggestions.show,.device-suggestions.show{display:block}.usage-suggestion,.device-suggestion{display:grid;gap:2px;width:100%;border:0;border-bottom:1px solid #edf1ef;background:#fff;padding:10px 11px;text-align:left;cursor:pointer;color:var(--text)}.usage-suggestion:last-child,.device-suggestion:last-child{border-bottom:0}.usage-suggestion:hover,.usage-suggestion:focus,.device-suggestion:hover,.device-suggestion:focus{background:#f3f7f5;outline:none}.usage-suggestion strong,.device-suggestion strong{font-size:13px}.usage-suggestion small,.device-suggestion small{font-size:11px;color:var(--muted)}.usage-no-result,.device-no-result{padding:11px;color:var(--muted);font-size:12px}
'''
if '.usage-autocomplete{' not in s:
    s = s.replace('</style>', css + '\n</style>', 1)

pattern = re.compile(r"function usageBuilder\(existing=\[\]\)\{.*?\}\nfunction initUsageControls\(\)\{.*?\}\nfunction collectUsage\(\)", re.S)
replacement = r'''function usagePartDisplay(p){if(!p)return '';return [p.description,p.artNr].filter(Boolean).join(' · ')}
function usagePartMatches(query){const q=normalizeSearch(query);if(!q)return [];return state.parts.filter(p=>normalizeSearch([p.description,p.artNr,p.deviceBrand,p.supplierCode].filter(Boolean).join(' ')).includes(q)).sort((a,b)=>{const ad=normalizeSearch(a.description),bd=normalizeSearch(b.description);const aq=ad.startsWith(q)?0:1,bq=bd.startsWith(q)?0:1;return aq-bq||String(a.description||'').localeCompare(String(b.description||''),'nl',{sensitivity:'base'})}).slice(0,10)}
function usageSuggestionsHtml(query){const matches=usagePartMatches(query);if(!matches.length)return '<div class="usage-no-result">Geen onderdeel gevonden.</div>';return matches.map(p=>`<button type="button" class="usage-suggestion" data-part-id="${esc(p.id)}"><strong>${esc(p.description||p.artNr||'Onderdeel')}</strong><small>${esc([p.artNr,p.deviceBrand].filter(Boolean).join(' · '))}${p.artNr||p.deviceBrand?' · ':''}voorraad ${Number(p.stock||0)}</small></button>`).join('')}
function usageRowHtml(u={partId:'',qty:1},searchable=false){const selected=state.parts.find(p=>p.id===u.partId);const picker=searchable?`<div class="usage-autocomplete"><input type="search" class="usage-search" placeholder="Typ de benaming van het onderdeel…" autocomplete="off" value="${esc(usagePartDisplay(selected))}"><input type="hidden" class="usage-part" value="${esc(u.partId||'')}"><div class="usage-suggestions"></div></div>`:`<select class="usage-part"><option value="">Kies onderdeel…</option>${state.parts.map(p=>`<option value="${p.id}" ${u.partId===p.id?'selected':''}>${esc(p.artNr)} · ${esc(p.description)}${p.deviceBrand?' · '+esc(p.deviceBrand):''} (voorraad ${Number(p.stock||0)})</option>`).join('')}</select>`;return `<div class="usage-row">${picker}<input class="usage-qty" type="number" min="1" step="1" value="${u.qty||1}"><button type="button" class="remove-line">×</button></div>`}
function usageBuilder(existing=[],searchable=false){const rows=(existing.length?existing:[{partId:'',qty:1}]).map(u=>usageRowHtml(u,searchable)).join('');return `<div class="field full"><div class="section-title">Gebruikte onderdelen</div>${searchable?'<div class="muted" style="font-size:11px;margin:-4px 0 8px">Typ de benaming en tik daarna het juiste artikel aan in de lijst die verschijnt.</div>':''}<div id="usageList" class="usage-list" data-searchable="${searchable?'1':'0'}">${rows}</div><button type="button" class="btn small" id="addUsage" style="margin-top:9px">+ Onderdeelregel</button></div>`}
function initUsageControls(){const list=$('#usageList'),addBtn=$('#addUsage');if(!list||!addBtn)return;const searchable=list.dataset.searchable==='1';const hideSuggestions=row=>{const box=row?.querySelector('.usage-suggestions');if(box)box.classList.remove('show')};const showSuggestions=input=>{const row=input.closest('.usage-row'),box=row?.querySelector('.usage-suggestions'),hidden=row?.querySelector('.usage-part');if(!box)return;if(hidden)hidden.value='';const q=input.value.trim();if(!q){box.classList.remove('show');box.innerHTML='';return}box.innerHTML=usageSuggestionsHtml(q);box.classList.add('show')};addBtn.onclick=()=>{const div=document.createElement('div');div.innerHTML=usageRowHtml({partId:'',qty:1},searchable);const row=div.firstElementChild;if(row)list.appendChild(row);if(searchable){const input=row?.querySelector('.usage-search');if(input)input.focus()}};list.onclick=e=>{const suggestion=e.target.closest('.usage-suggestion');if(suggestion){const row=suggestion.closest('.usage-row'),part=state.parts.find(p=>p.id===suggestion.dataset.partId),input=row?.querySelector('.usage-search'),hidden=row?.querySelector('.usage-part');if(part&&input&&hidden){input.value=usagePartDisplay(part);hidden.value=part.id;hideSuggestions(row)}return}if(e.target.classList.contains('remove-line'))e.target.closest('.usage-row').remove()};list.oninput=e=>{if(e.target.classList.contains('usage-search'))showSuggestions(e.target)};list.onkeydown=e=>{if(!e.target.classList.contains('usage-search'))return;const row=e.target.closest('.usage-row'),box=row?.querySelector('.usage-suggestions');if(e.key==='Escape'){hideSuggestions(row);return}if(e.key==='Enter'&&box?.classList.contains('show')){const first=box.querySelector('.usage-suggestion');if(first){e.preventDefault();first.click()}}};list.onfocusout=e=>{if(e.target.classList.contains('usage-search'))setTimeout(()=>hideSuggestions(e.target.closest('.usage-row')),140)}}
function collectUsage()'''

if pattern.search(s):
    s = pattern.sub(replacement, s, count=1)
elif 'function usagePartDisplay(' not in s:
    raise SystemExit('Autocomplete voor onderdelen kon niet worden aangepast')

# Overschrijf de bestaande toestelzoeker met één autocompleteveld.
device_autocomplete = r'''function deviceAutocompleteDisplay(d){if(!d)return '';return [d.assetCode,deviceLocationAt(d),d.brand,d.model].filter(Boolean).join(' · ')}
function deviceAutocompleteMatches(query){const q=normalizeSearch(query);if(!q)return [];return state.devices.filter(d=>String(d.status||'Actief').trim().toLowerCase()==='actief'&&normalizeSearch([d.assetCode,d.serial,deviceLocationAt(d),d.location,d.brand,d.model].filter(Boolean).join(' ')).includes(q)).sort((a,b)=>{const aa=normalizeSearch(a.assetCode),ba=normalizeSearch(b.assetCode),aq=aa.startsWith(q)?0:1,bq=ba.startsWith(q)?0:1;return aq-bq||String(a.assetCode||'').localeCompare(String(b.assetCode||''),'nl',{numeric:true,sensitivity:'base'})}).slice(0,10)}
function deviceAutocompleteSuggestionsHtml(query){const matches=deviceAutocompleteMatches(query);if(!matches.length)return '<div class="device-no-result">Geen actief toestel gevonden.</div>';return matches.map(d=>`<button type="button" class="device-suggestion" data-device-id="${esc(d.id)}"><strong>${esc(d.assetCode||d.model||'Toestel')}</strong><small>${esc([deviceLocationAt(d),d.brand,d.model,d.serial&&'S/N '+d.serial].filter(Boolean).join(' · '))}</small></button>`).join('')}
function deviceSearchField(selectedId=''){const selected=state.devices.find(d=>d.id===selectedId);return `<div class="field full"><label>Toestel *</label><div class="device-autocomplete"><input type="search" class="device-search" required placeholder="Typ WCL, locatie, merk of serienummer…" autocomplete="off" value="${esc(deviceAutocompleteDisplay(selected))}"><input type="hidden" name="deviceId" class="device-select" value="${esc(selectedId||'')}"><div class="device-suggestions"></div></div><div class="muted" style="font-size:11px;margin-top:4px">Alleen actieve toestellen worden aangeboden. Typ in het vak en tik daarna het juiste toestel aan.</div></div>`}
function initDeviceSearch(selectedId=''){const input=$('.device-search'),hidden=$('.device-select'),box=$('.device-suggestions');if(!input||!hidden||!box)return;const selected=state.devices.find(d=>d.id===(selectedId||hidden.value));if(selected){hidden.value=selected.id;if(!input.value)input.value=deviceAutocompleteDisplay(selected);input.setCustomValidity('')}else if(!hidden.value){input.setCustomValidity('Kies een actief toestel uit de lijst.')}const hide=()=>box.classList.remove('show');const show=()=>{const q=input.value.trim();if(!q){box.innerHTML='';hide();return}box.innerHTML=deviceAutocompleteSuggestionsHtml(q);box.classList.add('show')};input.oninput=()=>{hidden.value='';input.setCustomValidity('Kies een actief toestel uit de lijst.');show()};input.onfocus=()=>{if(input.value.trim()&&!hidden.value)show()};input.onkeydown=e=>{if(e.key==='Escape'){hide();return}if(e.key==='Enter'&&box.classList.contains('show')){const first=box.querySelector('.device-suggestion');if(first){e.preventDefault();first.click()}}};box.onclick=e=>{const choice=e.target.closest('.device-suggestion');if(!choice)return;const d=state.devices.find(x=>x.id===choice.dataset.deviceId);if(!d||String(d.status||'Actief').trim().toLowerCase()!=='actief')return;hidden.value=d.id;input.value=deviceAutocompleteDisplay(d);input.setCustomValidity('');hide()};input.onfocusout=()=>setTimeout(hide,140)}
'''
if 'function deviceAutocompleteDisplay(' not in s:
    marker='async function startKoffieServiceApp()'
    if marker not in s:
        raise SystemExit('Plaats voor toestel-autocomplete niet gevonden')
    s=s.replace(marker,device_autocomplete+'\n'+marker,1)

# Stocktelling: Excel-kolom "categorie" hoort uitsluitend bij Onderdelen -> Merk toestel.
old_brand_index="deviceBrand:findHeaderIndex(headers,['Merk toestel','merk']),"
new_brand_index="deviceBrand:findHeaderIndex(headers,['categorie','category','Merk toestel','merk']),"
if old_brand_index in s:
    s=s.replace(old_brand_index,new_brand_index,1)
elif new_brand_index not in s:
    raise SystemExit('Kolomkoppeling Merk toestel bij stocktelling niet gevonden')

old_existing="if(old){records.push({artNr,key,action:'update',old,newStock:stock})}"
new_existing="if(old){const importedDeviceBrand=get('deviceBrand');records.push({artNr,key,action:'update',old,newStock:stock,newDeviceBrand:importedDeviceBrand||old.deviceBrand||''})}"
if old_existing in s:
    s=s.replace(old_existing,new_existing,1)
elif 'newDeviceBrand:importedDeviceBrand||old.deviceBrand' not in s:
    raise SystemExit('Update van bestaande onderdelen bij stocktelling niet gevonden')

old_apply="for(const r of updates)await put('parts',{...r.old,stock:r.newStock,updatedAt:new Date().toISOString()});"
new_apply="for(const r of updates)await put('parts',{...r.old,stock:r.newStock,deviceBrand:r.newDeviceBrand??r.old.deviceBrand??'',updatedAt:new Date().toISOString()});"
if old_apply in s:
    s=s.replace(old_apply,new_apply,1)
elif "deviceBrand:r.newDeviceBrand??r.old.deviceBrand" not in s:
    raise SystemExit('Verwerking van stockupdates niet gevonden')

old_help='Ondersteunde kolommen: Art nr, omschrijving, Merk toestel, prijs, Voorraad locatie 1, Code leverancier, Magazijnlocatie en Minimumvoorraad. Alleen Art nr en Voorraad locatie 1 zijn vereist voor een stockupdate.'
new_help='Ondersteunde kolommen: Art nr, omschrijving, categorie, Merk toestel, prijs, Voorraad locatie 1, Code leverancier, Magazijnlocatie en Minimumvoorraad. De kolom categorie wordt opgeslagen als Merk toestel bij Onderdelen en staat volledig los van het merk bij Toestellen. Alleen Art nr en Voorraad locatie 1 zijn vereist voor een stockupdate.'
if old_help in s:
    s=s.replace(old_help,new_help,1)
elif new_help not in s:
    raise SystemExit('Toelichting bij stocktelling niet gevonden')

for old_version in [
    'v1.45 • Toestellen autocomplete',
    'v1.44 • Onderdelen autocomplete',
    'v1.43 • Onderdeel zoeken bij onderhoud',
    'v1.42 • Onderdeel zoeken bij depannage',
    'v1.41 • Beheer opgeruimd',
    'v1.40 • Back-up samengevoegd'
]:
    s = s.replace(old_version, 'v1.47 • Categorie bij stocktelling', 1)

p.write_text(s, encoding='utf-8')

sw = Path('sw.js')
ws = sw.read_text(encoding='utf-8')
for old_cache in [
    'machinepark-v1.45-device-autocomplete',
    'machinepark-v1.44-parts-autocomplete',
    'machinepark-v1.43-maintenance-part-search',
    'machinepark-v1.42-breakdown-part-search',
    'machinepark-v1.41-admin-cleanup',
    'machinepark-v1.40-backup-card'
]:
    ws = ws.replace(old_cache, 'machinepark-v1.47-stock-category')
sw.write_text(ws, encoding='utf-8')
