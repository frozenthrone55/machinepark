from pathlib import Path
import re

p = Path('index.html')
s = p.read_text(encoding='utf-8')

# Alleen depannages krijgen de zoekbare onderdelenkiezer.
s = s.replace("${usageBuilder(b.usedParts||[])}", "${usageBuilder(b.usedParts||[],true)}", 1)

pattern = re.compile(r"function usageBuilder\(existing=\[\]\)\{.*?\}\nfunction initUsageControls\(\)\{.*?\}\nfunction collectUsage\(\)", re.S)
replacement = r'''function usagePartOptions(selectedId='',query=''){const q=normalizeSearch(query);return state.parts.filter(p=>!q||normalizeSearch([p.description,p.artNr,p.deviceBrand,p.supplierCode].filter(Boolean).join(' ')).includes(q)).map(p=>`<option value="${p.id}" ${selectedId===p.id?'selected':''}>${esc(p.artNr)} · ${esc(p.description)}${p.deviceBrand?' · '+esc(p.deviceBrand):''} (voorraad ${Number(p.stock||0)})</option>`).join('')}
function usageRowHtml(u={partId:'',qty:1},searchable=false){const picker=searchable?`<div style="display:grid;gap:6px;min-width:0"><input type="search" class="usage-search" placeholder="Zoek onderdeel op benaming…" autocomplete="off"><select class="usage-part"><option value="">Kies onderdeel…</option>${usagePartOptions(u.partId||'')}</select></div>`:`<select class="usage-part"><option value="">Kies onderdeel…</option>${usagePartOptions(u.partId||'')}</select>`;return `<div class="usage-row">${picker}<input class="usage-qty" type="number" min="1" step="1" value="${u.qty||1}"><button type="button" class="remove-line">×</button></div>`}
function usageBuilder(existing=[],searchable=false){const rows=(existing.length?existing:[{partId:'',qty:1}]).map(u=>usageRowHtml(u,searchable)).join('');return `<div class="field full"><div class="section-title">Gebruikte onderdelen</div>${searchable?'<div class="muted" style="font-size:11px;margin:-4px 0 8px">Typ (een deel van) de benaming om de onderdelenlijst meteen te filteren.</div>':''}<div id="usageList" class="usage-list" data-searchable="${searchable?'1':'0'}">${rows}</div><button type="button" class="btn small" id="addUsage" style="margin-top:9px">+ Onderdeelregel</button></div>`}
function initUsageControls(){const list=$('#usageList'),addBtn=$('#addUsage');if(!list||!addBtn)return;const searchable=list.dataset.searchable==='1';addBtn.onclick=()=>{const div=document.createElement('div');div.innerHTML=usageRowHtml({partId:'',qty:1},searchable);const row=div.firstElementChild;if(row)list.appendChild(row);if(searchable){const input=row?.querySelector('.usage-search');if(input)input.focus()}};list.onclick=e=>{if(e.target.classList.contains('remove-line'))e.target.closest('.usage-row').remove()};list.oninput=e=>{if(!e.target.classList.contains('usage-search'))return;const row=e.target.closest('.usage-row'),select=row?.querySelector('.usage-part');if(!select)return;select.innerHTML=`<option value="">Kies onderdeel…</option>${usagePartOptions('',e.target.value)}`;select.value=''}}
function collectUsage()'''

if pattern.search(s):
    s = pattern.sub(replacement, s, count=1)
elif 'function usagePartOptions(' not in s:
    raise SystemExit('Onderdelenkiezer voor depannage kon niet worden aangepast')

for old_version in [
    'v1.41 • Beheer opgeruimd',
    'v1.40 • Back-up samengevoegd',
    'v1.39 • Veiliger beheer',
    'v1.38 • Accountnaam & rol'
]:
    s = s.replace(old_version, 'v1.42 • Onderdeel zoeken bij depannage', 1)

p.write_text(s, encoding='utf-8')

sw = Path('sw.js')
ws = sw.read_text(encoding='utf-8')
for old_cache in [
    'machinepark-v1.41-admin-cleanup',
    'machinepark-v1.40-backup-card',
    'machinepark-v1.39-safer-admin',
    'machinepark-v1.38-account-summary'
]:
    ws = ws.replace(old_cache, 'machinepark-v1.42-breakdown-part-search')
sw.write_text(ws, encoding='utf-8')
