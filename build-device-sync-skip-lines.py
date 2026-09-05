from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="device-sync-skip-lines-v1"'

if MARKER not in index:
    start = index.find('function showDeviceSyncPreview(records,fileName)')
    end = index.find('async function importDeviceSyncExcel(file)', start)
    if start < 0 or end < 0:
        raise SystemExit('Buildvalidatie mislukt: toestelsynchronisatie-preview niet gevonden')

    replacement = r'''function showDeviceSyncPreview(records,fileName){
  const adds=records.filter(r=>r.action==='add'),updates=records.filter(r=>r.action==='update'),same=records.filter(r=>r.action==='same'),skips=records.filter(r=>r.action==='skip'),changes=[...updates,...adds];
  const syncKey=r=>String(r?.key||r?.code||'');
  const skipCell=r=>`<td><label class="device-sync-skip-label"><input type="checkbox" class="device-sync-skip" data-sync-key="${esc(syncKey(r))}"> Overslaan</label></td>`;
  const rows=changes.map(r=>{
    if(r.action==='add')return `<tr class="device-sync-change-row" data-sync-row="${esc(syncKey(r))}"><td>${skipCell(r).replace(/^<td>|<\/td>$/g,'')}</td><td><strong>${esc(r.code)}</strong></td><td><span class="badge blue">Nieuw</span></td><td>${esc(r.location||'—')}</td><td>${esc(installSourceDisplay(r.installInfo))}</td><td>${r.redMarked?'<span class="badge danger">Buiten dienst</span>':'<span class="badge">Actief</span>'}</td></tr>`;
    const loc=r.locationChanged?`${esc(deviceLocationAt(r.old)||'—')} → <strong>${esc(r.location)}</strong>`:esc(deviceLocationAt(r.old)||'—'),inst=r.installChanged?`${esc(currentInstallDisplay(r.old))} → <strong>${esc(installSourceDisplay(r.installInfo))}</strong>`:esc(currentInstallDisplay(r.old)),status=r.statusChanged?'<span class="badge danger">Actief → Buiten dienst</span>':statusBadge(r.old.status||'Actief');
    return `<tr class="device-sync-change-row" data-sync-row="${esc(syncKey(r))}"><td>${skipCell(r).replace(/^<td>|<\/td>$/g,'')}</td><td><strong>${esc(r.code)}</strong></td><td><span class="badge warn">Wijzigen</span></td><td>${loc}</td><td>${inst}</td><td>${status}</td></tr>`;
  }).join('');
  const body=`<div class="form-grid"><div class="field full"><div class="kpis" style="grid-template-columns:repeat(4,1fr);margin-bottom:8px"><div class="kpi" style="box-shadow:none"><div class="label">Nieuwe toestellen</div><div class="value" id="deviceSyncAddCount">${adds.length}</div></div><div class="kpi" style="box-shadow:none"><div class="label">Toestellen wijzigen</div><div class="value" id="deviceSyncUpdateCount">${updates.length}</div></div><div class="kpi" style="box-shadow:none"><div class="label">Ongewijzigd</div><div class="value">${same.length}</div></div><div class="kpi" style="box-shadow:none"><div class="label">Overgeslagen</div><div class="value" id="deviceSyncSkipCount">${skips.length}</div></div></div></div><div class="field full"><div class="alert" id="deviceSyncPlanSummary"></div><div class="muted" style="margin:12px 0 10px">Bestand: ${esc(fileName)}. Vink <strong>Overslaan</strong> aan bij een regel die niet verwerkt mag worden. Lege broncellen overschrijven bestaande locatie, merk of installatiedatum niet. Rode en lichtrode Excelregels worden herkend als Buiten dienst.</div><div class="table-wrap"><table class="table" style="min-width:900px"><thead><tr><th>Overslaan</th><th>WCL nr.</th><th>Actie</th><th>Locatie</th><th>Contract start</th><th>Status</th></tr></thead><tbody>${rows||'<tr><td colspan="6"><div class="empty">Geen wijzigingen nodig.</div></td></tr>'}</tbody></table></div>${skips.length?`<div class="alert" style="margin-top:12px"><strong>${skips.length} bronregel(s) automatisch overgeslagen</strong>${esc(skips.slice(0,6).map(r=>r.reason).join(' · '))}</div>`:''}</div></div>`;
  $('#modal').innerHTML=`<div class="modal-head"><h3>Toestellen synchroniseren</h3><button class="close" type="button">×</button></div><div class="modal-body">${body}</div><div class="modal-foot"><button class="btn" type="button" id="cancelDeviceSync">Annuleren</button><button class="btn primary" type="button" id="confirmDeviceSync">Synchronisatie verwerken</button></div>`;
  enhanceSortableTables($('#modal'));$('#modalBackdrop').classList.add('show');$('.close').onclick=closeModal;$('#cancelDeviceSync').onclick=closeModal;
  const confirm=$('#confirmDeviceSync');
  const skippedKeys=()=>new Set([...document.querySelectorAll('#modal .device-sync-skip:checked')].map(input=>String(input.dataset.syncKey||'')));
  const activePlan=()=>{const ignored=skippedKeys();return {ignored,activeAdds:adds.filter(r=>!ignored.has(syncKey(r))),activeUpdates:updates.filter(r=>!ignored.has(syncKey(r)))}};
  const updateSelectionSummary=()=>{
    const {ignored,activeAdds,activeUpdates}=activePlan(),manualSkipped=changes.filter(r=>ignored.has(syncKey(r))).length;
    const locN=activeUpdates.filter(r=>r.locationChanged).length,instN=activeUpdates.filter(r=>r.installChanged).length,brandN=activeUpdates.filter(r=>r.brandChanged).length,statusN=activeUpdates.filter(r=>r.statusChanged).length+activeAdds.filter(r=>r.redMarked).length,total=activeAdds.length+activeUpdates.length;
    const addCount=$('#deviceSyncAddCount'),updateCount=$('#deviceSyncUpdateCount'),skipCount=$('#deviceSyncSkipCount'),summary=$('#deviceSyncPlanSummary');
    if(addCount)addCount.textContent=String(activeAdds.length);if(updateCount)updateCount.textContent=String(activeUpdates.length);if(skipCount)skipCount.textContent=String(skips.length+manualSkipped);
    if(summary)summary.innerHTML=`<strong>Geplande wijzigingen · ${total} te verwerken</strong>${locN} locatiewijziging(en) · ${instN} contract-startwijziging(en) · ${brandN} merkwijziging(en) · ${statusN} toestel(len) Buiten dienst op basis van rode markering.${manualSkipped?` <strong>${manualSkipped} handmatig overgeslagen.</strong>`:''} Locatiewijzigingen worden pas bij bevestigen vastgelegd met het synchronisatiemoment.`;
    document.querySelectorAll('#modal .device-sync-change-row').forEach(row=>row.classList.toggle('device-sync-manual-skip',ignored.has(String(row.dataset.syncRow||''))));
    if(confirm){confirm.disabled=total===0;confirm.textContent=total?`Synchronisatie verwerken (${total})`:'Niets te verwerken'}
  };
  document.querySelectorAll('#modal .device-sync-skip').forEach(input=>input.addEventListener('change',updateSelectionSummary));
  updateSelectionSummary();
  if(confirm)confirm.onclick=async()=>{
    const {ignored,activeAdds,activeUpdates}=activePlan(),manualSkipped=changes.filter(r=>ignored.has(syncKey(r))).length;
    if(!activeAdds.length&&!activeUpdates.length)return;
    confirm.disabled=true;confirm.textContent='Synchroniseren…';const syncMoment=nowLocalDateTime(),loggedAt=new Date().toISOString();
    for(const r of activeAdds){const info=r.installInfo,date=info.date||'',loc=r.location||'',status=r.redMarked?'Buiten dienst':'Actief',changeLog=r.redMarked?[{id:uid('chg'),type:'status',label:'Status',oldValue:'—',newValue:'Buiten dienst',effectiveFrom:syncMoment,loggedAt,source:'rode regel toestellen-synchronisatie'}]:[];await put('devices',{id:uid('dev'),assetCode:r.code,location:loc,locationHistory:loc?[{id:uid('loc'),location:loc,effectiveFrom:syncMoment,loggedAt,source:'toestellen-synchronisatie'}]:[],deviceChangeLog:changeLog,brand:r.brand||'',model:'',serial:'',installDate:date,installDatePrecision:info.precision||'',installDateSource:info.source||'',status,nextHalf:'',nextAnnual:'',notes:'',sourceInventory:fileName,createdAt:loggedAt,updatedAt:loggedAt})}
    for(const r of activeUpdates){const old=r.old;let history=Array.isArray(old.locationHistory)?old.locationHistory.map(x=>({...x})):[];let changeLog=Array.isArray(old.deviceChangeLog)?old.deviceChangeLog.map(x=>({...x})):[];if(!history.length&&old.location)history.push({id:uid('loc'),location:old.location,effectiveFrom:normalizeMoment(old.installDate||String(old.createdAt||'').slice(0,10)||todayISO(),'00:00'),loggedAt:old.createdAt||loggedAt,source:'legacy'});if(r.locationChanged)history.push({id:uid('loc'),location:r.location,effectiveFrom:syncMoment,loggedAt,source:'toestellen-synchronisatie'});history.sort((a,b)=>normalizeMoment(a.effectiveFrom,'00:00').localeCompare(normalizeMoment(b.effectiveFrom,'00:00')));let installDate=old.installDate||'',precision=old.installDatePrecision||'',source=old.installDateSource||'',brand=old.brand||'',status=old.status||'Actief';if(r.installChanged){changeLog.push({id:uid('chg'),type:'installDate',label:'Installatiedatum / contract start',oldValue:currentInstallDisplay(old),newValue:installSourceDisplay(r.installInfo),effectiveFrom:syncMoment,loggedAt,source:'toestellen-synchronisatie'});installDate=r.installInfo.date||'';precision=r.installInfo.precision||'';source=r.installInfo.source||''}if(r.brandChanged){changeLog.push({id:uid('chg'),type:'brand',label:'Merk / toestelgegevens',oldValue:old.brand||'—',newValue:r.brand,effectiveFrom:syncMoment,loggedAt,source:'toestellen-synchronisatie'});brand=r.brand}if(r.statusChanged){changeLog.push({id:uid('chg'),type:'status',label:'Status',oldValue:status,newValue:'Buiten dienst',effectiveFrom:syncMoment,loggedAt,source:'rode regel toestellen-synchronisatie'});status='Buiten dienst'}let nextHalf=old.nextHalf||'',nextAnnual=old.nextAnnual||'';const updated={...old,location:r.locationChanged?r.location:(deviceLocationAt(old)||old.location||''),locationHistory:history,deviceChangeLog:changeLog,brand,installDate,installDatePrecision:precision,installDateSource:source,status,nextHalf,nextAnnual,sourceInventory:fileName,updatedAt:loggedAt};await put('devices',updated)}
    closeModal();await refresh();toast(`${activeAdds.length} nieuw · ${activeUpdates.length} toestel(len) bijgewerkt${manualSkipped?` · ${manualSkipped} overgeslagen`:''}`)
  }
}
'''

    index = index[:start] + replacement + index[end:]
    style = f'''\n<style {MARKER}>\n.device-sync-skip-label{{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;cursor:pointer;font-size:11px;font-weight:700;color:var(--muted)}}\n.device-sync-skip-label input{{width:16px;height:16px;accent-color:var(--brand)}}\n.device-sync-change-row td{{transition:opacity .15s ease,background .15s ease}}\n.device-sync-change-row.device-sync-manual-skip td{{opacity:.48;background:#f5f6f5!important}}\n</style>\n'''
    head = index.find('</head>')
    if head < 0:
        raise SystemExit('Buildvalidatie mislukt: </head> ontbreekt voor synchronisatie-overslaan')
    index = index[:head] + style + index[head:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'device-sync-skip',
    'device-sync-manual-skip',
    'Overslaan',
    'activeAdds',
    'activeUpdates',
    'updateSelectionSummary',
    'Niets te verwerken',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: synchronisatie-overslaan ontbreekt ({needle})')
if '.slice(0,35)' in index[index.find('function showDeviceSyncPreview'):index.find('async function importDeviceSyncExcel')]:
    raise SystemExit('Buildvalidatie mislukt: synchronisatie toont nog maar een beperkte preview')

print('[Machinepark] toestelsynchronisatie laat elke geplande regel afzonderlijk overslaan')
