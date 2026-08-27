from pathlib import Path
import re

p = Path('index.html')
s = p.read_text(encoding='utf-8')

old_head = '<table class="table" style="min-width:900px"><thead><tr><th>Wanneer</th><th>Wie</th><th>Wat</th><th>Wijziging</th></tr></thead><tbody id="auditLogBody"></tbody></table>'
new_head = '<table class="table" style="min-width:1020px"><thead><tr><th>Wanneer</th><th>Wie</th><th>Wat</th><th>Wijziging</th><th>Actie</th></tr></thead><tbody id="auditLogBody"></tbody></table>'
if old_head in s:
    s = s.replace(old_head, new_head, 1)
elif '<th>Wijziging</th><th>Actie</th>' not in s:
    raise SystemExit('Kop van wijzigingslogboek niet gevonden')

pattern = re.compile(r"async function loadAuditLog\(\)\{.*?\}\nasync function loadAdminPanels\(\)", re.S)
replacement = r'''function auditUndoButton(entry,change,changeIndex){
  if(change.undone)return '<button class="btn small" type="button" disabled title="Deze wijziging is al ongedaan gemaakt.">Ongedaan gemaakt</button>';
  if(!change.reversible)return '<button class="btn small" type="button" disabled title="Deze oudere logboekregel bevat nog geen volledige hersteldata.">Niet beschikbaar</button>';
  const linked=Number(change.linkedUndoCount||0),title=linked?`Deze handeling heeft ${linked} gekoppelde voorraadwijziging(en); die worden veilig mee teruggedraaid.`:'Alleen deze wijziging wordt teruggedraaid.';
  return `<button class="btn small" type="button" data-undo-audit="1" data-audit-key="${esc(entry.auditKey||'')}" data-change-index="${changeIndex}" data-linked-count="${linked}" data-audit-label="${esc(change.entityLabel||change.entityType||'deze wijziging')}" title="${esc(title)}">Ongedaan maken</button>`
}
async function undoAuditChange(btn){
  if(centralSync.pushing){alert('Er wordt nog een wijziging gesynchroniseerd. Wacht even en probeer opnieuw.');return}
  if(centralSync.pushTimer){clearTimeout(centralSync.pushTimer);centralSync.pushTimer=null;try{await centralPush()}catch(e){alert('De laatste lokale wijziging kon nog niet centraal worden opgeslagen. '+e.message);return}}
  const label=btn.dataset.auditLabel||'deze wijziging',linked=Number(btn.dataset.linkedCount||0);const extra=linked?` De ${linked} gekoppelde voorraadwijziging(en) worden mee hersteld om de gegevens consistent te houden.`:'';
  if(!confirm(`De wijziging aan “${label}” ongedaan maken?${extra} Nieuwere wijzigingen worden nooit overschreven.`))return;
  btn.disabled=true;const oldText=btn.textContent;btn.textContent='Herstellen…';
  try{
    const result=await adminFetch(AUDIT_LOG_URL,{method:'POST',body:JSON.stringify({auditKey:btn.dataset.auditKey,changeIndex:Number(btn.dataset.changeIndex)})});
    centralSync.etag=null;
    await centralPull({apply:true,quiet:false});
    await loadAuditLog();
    toast(Number(result.linkedCount||0)>0?'Wijziging en gekoppelde voorraad hersteld':'Wijziging ongedaan gemaakt');
  }catch(e){alert(e.message);btn.disabled=false;btn.textContent=oldText}
}
function bindAuditUndoActions(){$$('[data-undo-audit]').forEach(btn=>btn.onclick=()=>undoAuditChange(btn))}
async function loadAuditLog(){if(!window.machineparkIsAdmin)return;const status=$('#auditLogStatus'),body=$('#auditLogBody');if(status)status.textContent='Logboek wordt geladen…';try{const data=await adminFetch(AUDIT_LOG_URL);const rows=[];(data.entries||[]).forEach(entry=>(entry.changes||[]).forEach((change,changeIndex)=>rows.push({entry,change,changeIndex})));if(status)status.textContent=`${rows.length} wijziging(en) uit de meest recente logboekregels`;if(body){body.innerHTML=rows.length?rows.map(({entry,change,changeIndex})=>`<tr><td class="nowrap">${adminDateFmt(entry.at)}</td><td><strong>${esc(entry.userName||entry.userEmail||'Gebruiker')}</strong>${entry.userName&&entry.userEmail?`<br><span class="muted">${esc(entry.userEmail)}</span>`:''}</td><td><strong>${esc(change.entityType||'Item')}</strong><br><span class="muted">${esc(change.entityLabel||'')}</span></td><td><span class="badge ${change.action==='verwijderd'?'danger':change.action==='toegevoegd'||change.action==='uitgenodigd'?'success':change.action==='ongedaan gemaakt'?'blue':'gray'}">${esc(change.action||'gewijzigd')}</span><div style="margin-top:6px;font-size:12px;line-height:1.5">${auditDetails(change)}</div>${Number(change.linkedUndoCount||0)>0?`<div class="muted" style="font-size:11px;margin-top:5px">↳ ${Number(change.linkedUndoCount)} gekoppelde voorraadwijziging(en)</div>`:''}</td><td class="nowrap">${auditUndoButton(entry,change,changeIndex)}</td></tr>`).join(''):'<tr><td colspan="5"><div class="empty">Nog geen wijzigingen gelogd. Nieuwe wijzigingen verschijnen hier automatisch.</div></td></tr>';bindAuditUndoActions()}}catch(e){console.error(e);if(status)status.textContent='Logboek kon niet worden geladen: '+e.message;if(body)body.innerHTML='<tr><td colspan="5"><div class="empty">Logboek niet beschikbaar.</div></td></tr>'}}
async function loadAdminPanels()'''

if pattern.search(s):
    s = pattern.sub(replacement, s, count=1)
elif 'function auditUndoButton(' not in s:
    raise SystemExit('Functie loadAuditLog niet gevonden')

for old_version in [
    'v1.50 • Prijsimport hersteld',
    'v1.49 • Importprijzen zijn leidend',
    'v1.48 • Prijzen bij stocktelling',
    'v1.47 • Categorie bij stocktelling'
]:
    s = s.replace(old_version, 'v1.51 • Logboek undo', 1)

p.write_text(s, encoding='utf-8')

sw = Path('sw.js')
ws = sw.read_text(encoding='utf-8')
for old_cache in [
    'machinepark-v1.50-stock-price-fix',
    'machinepark-v1.49-import-prices-authoritative',
    'machinepark-v1.48-stock-prices',
    'machinepark-v1.47-stock-category'
]:
    ws = ws.replace(old_cache, 'machinepark-v1.51-audit-undo')
sw.write_text(ws, encoding='utf-8')
