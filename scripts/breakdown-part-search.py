from pathlib import Path
import re

p = Path('index.html')
s = p.read_text(encoding='utf-8')

# Onderhoud en depannages krijgen dezelfde autocomplete voor gebruikte onderdelen.
s = s.replace("${usageBuilder(m.usedParts||[])}", "${usageBuilder(m.usedParts||[],true)}", 1)
s = s.replace("${usageBuilder(b.usedParts||[])}", "${usageBuilder(b.usedParts||[],true)}", 1)

css = '''
.usage-autocomplete{position:relative;min-width:0}.usage-autocomplete .usage-search{width:100%;border:1px solid var(--line);border-radius:9px;padding:9px;outline:none;background:white}.usage-autocomplete .usage-search:focus{border-color:#7ea598;box-shadow:0 0 0 3px rgba(44,106,88,.09)}.usage-suggestions{position:absolute;z-index:1600;left:0;right:0;top:calc(100% + 4px);max-height:260px;overflow:auto;background:#fff;border:1px solid var(--line);border-radius:11px;box-shadow:0 14px 34px rgba(20,45,38,.18);display:none}.usage-suggestions.show{display:block}.usage-suggestion{display:grid;gap:2px;width:100%;border:0;border-bottom:1px solid #edf1ef;background:#fff;padding:10px 11px;text-align:left;cursor:pointer;color:var(--text)}.usage-suggestion:last-child{border-bottom:0}.usage-suggestion:hover,.usage-suggestion:focus{background:#f3f7f5;outline:none}.usage-suggestion strong{font-size:13px}.usage-suggestion small{font-size:11px;color:var(--muted)}.usage-no-result{padding:11px;color:var(--muted);font-size:12px}
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

for old_version in [
    'v1.43 • Onderdeel zoeken bij onderhoud',
    'v1.42 • Onderdeel zoeken bij depannage',
    'v1.41 • Beheer opgeruimd',
    'v1.40 • Back-up samengevoegd'
]:
    s = s.replace(old_version, 'v1.44 • Onderdelen autocomplete', 1)

p.write_text(s, encoding='utf-8')

sw = Path('sw.js')
ws = sw.read_text(encoding='utf-8')
for old_cache in [
    'machinepark-v1.43-maintenance-part-search',
    'machinepark-v1.42-breakdown-part-search',
    'machinepark-v1.41-admin-cleanup',
    'machinepark-v1.40-backup-card'
]:
    ws = ws.replace(old_cache, 'machinepark-v1.44-parts-autocomplete')
sw.write_text(ws, encoding='utf-8')
