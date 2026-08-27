from pathlib import Path
import re

p = Path('index.html')
s = p.read_text(encoding='utf-8')

# Toegankelijkere live statusmeldingen.
s = s.replace('<div id="centralSyncStatus" class="sync-status">', '<div id="centralSyncStatus" class="sync-status" role="status" aria-live="polite">', 1)
s = s.replace('<div class="toast" id="toast"></div>', '<div class="toast" id="toast" role="status" aria-live="polite"></div>', 1)

# Extra operationeel dashboard onder de bestaande twee panelen.
old_dashboard = '<div id="dashboardAlerts" class="panel-body"></div></div>\n      </div>\n    </section>'
new_dashboard = '<div id="dashboardAlerts" class="panel-body"></div></div>\n      </div>\n      <div class="panel" style="margin-top:18px"><div class="panel-head"><h3>Operationele prioriteiten</h3><span class="muted" style="font-size:12px">vandaag</span></div><div id="dashboardProfessional" class="panel-body"></div></div>\n    </section>'
if old_dashboard in s:
    s = s.replace(old_dashboard, new_dashboard, 1)
elif 'id="dashboardProfessional"' not in s:
    raise SystemExit('Dashboard kon niet professioneel worden uitgebreid')

professional_dashboard = r'''function renderProfessionalDashboard(){const box=$('#dashboardProfessional');if(!box)return;const critical=state.breakdowns.filter(b=>b.status!=='Opgelost'&&b.priority==='Kritiek').length;const treating=state.breakdowns.filter(b=>b.status==='In behandeling').length;let overdue=0;state.devices.filter(d=>d.status!=='Buiten dienst').forEach(d=>{if(d.nextHalf&&daysUntil(d.nextHalf)<0)overdue++;if(d.nextAnnual&&daysUntil(d.nextAnnual)<0)overdue++});const zero=state.parts.filter(p=>Number(p.stock||0)<=0).length;const events=[...state.maintenance.map(m=>({moment:recordMoment(m),icon:'🔧',title:`${m.type||'Onderhoud'} · ${deviceName(m.deviceId,recordMoment(m))}`})),...state.breakdowns.map(b=>({moment:recordMoment(b),icon:'⚠',title:`${b.issue||'Depannage'} · ${deviceName(b.deviceId,recordMoment(b))}`}))].filter(x=>x.moment).sort((a,b)=>b.moment.localeCompare(a.moment)).slice(0,5);box.innerHTML=`<div class="professional-metrics"><div><span>Kritieke depannages</span><strong>${critical}</strong></div><div><span>In behandeling</span><strong>${treating}</strong></div><div><span>Onderhoud vervallen</span><strong>${overdue}</strong></div><div><span>Geen voorraad</span><strong>${zero}</strong></div></div><div class="section-title" style="margin-top:16px">Laatste activiteit</div>${events.length?`<div class="professional-activity">${events.map(x=>`<div><span>${x.icon}</span><strong>${esc(x.title)}</strong><small>${dateTimeFmt(x.moment)}</small></div>`).join('')}</div>`:'<div class="muted">Nog geen recente onderhouds- of depannageactiviteit.</div>'}`}
}
'''
if 'function renderProfessionalDashboard()' not in s:
    marker='function renderAll(){'
    if marker not in s: raise SystemExit('renderAll niet gevonden')
    s=s.replace(marker,professional_dashboard+marker,1)
s=s.replace('function renderAll(){renderDashboard();renderDevices();renderMaintenance();renderBreakdowns();renderParts();enhanceSortableTables();reapplyGenericTableSorts()}', 'function renderAll(){renderDashboard();renderProfessionalDashboard();renderDevices();renderMaintenance();renderBreakdowns();renderParts();enhanceSortableTables();reapplyGenericTableSorts();applyOperationalPermissions()}', 1)

# Vier operationele rollen, zonder bestaande Gebruiker-rechten te verminderen.
role_helpers = r'''function machineparkRoleLabel(role){return ({beheerder:'Beheerder',gebruiker:'Gebruiker',technieker:'Technieker',magazijnier:'Magazijnier'})[role]||'Gebruiker'}
function machineparkCapabilities(){const role=window.machineparkRole||'gebruiker';return {devices:role==='beheerder'||role==='gebruiker',maintenance:role==='beheerder'||role==='gebruiker'||role==='technieker',breakdowns:role==='beheerder'||role==='gebruiker'||role==='technieker',parts:role==='beheerder'||role==='gebruiker'||role==='magazijnier'}}
function applyOperationalPermissions(){const cap=machineparkCapabilities();window.machineparkCanEdit=cap;const show=(sel,yes)=>{$$(sel).forEach(el=>{el.style.display=yes?'':'none'})};show('#addDevice',cap.devices);show('#addMaintenance',cap.maintenance);show('#addBreakdown',cap.breakdowns);show('#addPart',cap.parts);show('[data-edit-part]',cap.parts);show('[data-edit-breakdown]',cap.breakdowns)}
'''
if 'function machineparkRoleLabel(' not in s:
    marker='function applyMachineparkRoleAccess()'
    if marker not in s: raise SystemExit('Roltoegang niet gevonden')
    s=s.replace(marker,role_helpers+marker,1)

# Bepaal en toon de echte operationele rol naast het account.
old_role_calc="const currentRole=String(Clerk.user?.publicMetadata?.role||'').trim().toLowerCase();window.machineparkIsAdmin=currentEmail===window.MACHINEPARK_ADMIN_EMAIL||currentRole==='beheerder';"
new_role_calc=old_role_calc+"window.machineparkRole=currentEmail===window.MACHINEPARK_ADMIN_EMAIL?'beheerder':(['beheerder','gebruiker','technieker','magazijnier'].includes(currentRole)?currentRole:'gebruiker');"
if old_role_calc in s and 'window.machineparkRole=currentEmail' not in s:
    s=s.replace(old_role_calc,new_role_calc,1)
s=s.replace("if(accountRole)accountRole.textContent=window.machineparkIsAdmin?'Beheerder':'Gebruiker';", "if(accountRole)accountRole.textContent=machineparkRoleLabel(window.machineparkRole||'gebruiker');", 1)

# Rolbadges en keuzelijst in gebruikersbeheer.
if 'function roleBadgeHtml(' not in s:
    marker='async function loadUserManagement()'
    badge="function roleBadgeHtml(role){const label=machineparkRoleLabel(role);const cls=role==='beheerder'?'success':role==='technieker'?'blue':role==='magazijnier'?'warn':'gray';return `<span class=\"badge ${cls}\">${esc(label)}</span>`}\n"
    s=s.replace(marker,badge+marker,1)
s=s.replace("${u.role==='beheerder'?'<span class=\"badge success\">Beheerder</span>':'<span class=\"badge gray\">Gebruiker</span>'}", "${roleBadgeHtml(u.role)}")
old_select='<select name="role"><option value="gebruiker" ${u.role===\'gebruiker\'?\'selected\':\'\'}>Gebruiker</option><option value="beheerder" ${u.role===\'beheerder\'?\'selected\':\'\'}>Beheerder</option></select>'
new_select='<select name="role"><option value="gebruiker" ${u.role===\'gebruiker\'?\'selected\':\'\'}>Gebruiker</option><option value="technieker" ${u.role===\'technieker\'?\'selected\':\'\'}>Technieker</option><option value="magazijnier" ${u.role===\'magazijnier\'?\'selected\':\'\'}>Magazijnier</option><option value="beheerder" ${u.role===\'beheerder\'?\'selected\':\'\'}>Beheerder</option></select>'
s=s.replace(old_select,new_select,1)
s=s.replace("if(u.id===window.machineparkCurrentAdminUserId&&newRole==='gebruiker'&&!u.isOwner){window.machineparkIsAdmin=false;", "if(u.id===window.machineparkCurrentAdminUserId&&newRole!=='beheerder'&&!u.isOwner){window.machineparkRole=newRole;window.machineparkIsAdmin=false;", 1)

# Bewerkknoppen in detailvensters respecteren de rol.
s=s.replace('<button class="btn primary" type="button" id="editMaintenanceFromDetails">Onderhoud wijzigen</button>', "${window.machineparkCanEdit?.maintenance?'<button class=\"btn primary\" type=\"button\" id=\"editMaintenanceFromDetails\">Onderhoud wijzigen</button>':''}", 1)
s=s.replace("$('#editMaintenanceFromDetails').onclick=()=>{closeModal();openMaintenance(id)}", "const editMaintenanceBtn=$('#editMaintenanceFromDetails');if(editMaintenanceBtn)editMaintenanceBtn.onclick=()=>{closeModal();openMaintenance(id)}", 1)
s=s.replace('<button type="button" class="btn small" id="editDeviceFromHistory">Bewerk toestel</button>', "${window.machineparkCanEdit?.devices?'<button type=\"button\" class=\"btn small\" id=\"editDeviceFromHistory\">Bewerk toestel</button>':''}", 1)
s=s.replace("setTimeout(()=>{$('#editDeviceFromHistory').onclick=()=>{closeModal();openDevice(id)}},0)", "setTimeout(()=>{const editDeviceBtn=$('#editDeviceFromHistory');if(editDeviceBtn)editDeviceBtn.onclick=()=>{closeModal();openDevice(id)}},0)", 1)

# Veilige en valideerbare back-up/restore met automatische veiligheidskopie.
backup_pattern=re.compile(r"async function exportBackup\(\)\{.*?\}\nasync function importBackup\(file\)\{.*?\}\nfunction bind\(\)",re.S)
backup_replacement=r'''function validateBackupData(data){if(!data||data.app!=='Machinepark')throw new Error('Dit bestand is niet als Machinepark-back-up herkenbaar.');for(const store of stores)if(!Array.isArray(data[store]))throw new Error(`Back-up mist geldige gegevens voor ${store}.`);return true}
async function makeBackupPayload(){const data={app:'Machinepark',schema:1,backupVersion:2,exportedAt:new Date().toISOString()};for(const store of stores)data[store]=await getAll(store);data.counts=Object.fromEntries(stores.map(store=>[store,data[store].length]));return data}
async function exportBackup(){const data=await makeBackupPayload();download('Machinepark_Backup_'+todayISO()+'.json',JSON.stringify(data,null,2));toast(`Back-up gemaakt · ${data.devices.length} toestellen · ${data.parts.length} onderdelen`)}
async function importBackup(file){try{if(!file)return;const data=JSON.parse(await file.text());validateBackupData(data);const summary=`${data.devices.length} toestellen, ${data.parts.length} onderdelen, ${data.maintenance.length} onderhoudsregels en ${data.breakdowns.length} depannages`;if(!confirm(`Deze geldige back-up bevat ${summary}. Bestaande gegevens vervangen? Vooraf wordt automatisch een veiligheidsback-up gedownload.`))return;const safety=await makeBackupPayload();download('Machinepark_Veiligheidsbackup_'+todayISO()+'.json',JSON.stringify(safety,null,2));const normalized={...data,app:'Machinepark',schema:1};await replaceLocalSnapshot(normalized);await refresh();setCentralSyncStatus('☁ Back-up centraal opslaan…','busy');await centralPush();toast('Back-up gecontroleerd en teruggezet')}catch(e){console.error(e);alert('Back-up terugzetten mislukt: '+(e.message||'onbekende fout'))}}
function bind()'''
if backup_pattern.search(s):
    s=backup_pattern.sub(backup_replacement,s,count=1)
elif 'function validateBackupData(' not in s:
    raise SystemExit('Back-upfuncties niet gevonden')

# Stocktelling: categorie én prijzen expliciet in preview + downloadbaar importverslag.
old_stock_head='<thead><tr><th>Art nr</th><th>Actie</th><th>Oude voorraad</th><th>Nieuwe voorraad</th><th>Oude prijs</th><th>Nieuwe prijs</th></tr></thead>'
new_stock_head='<thead><tr><th>Art nr</th><th>Actie</th><th>Oude voorraad</th><th>Nieuwe voorraad</th><th>Oude prijs</th><th>Nieuwe prijs</th><th>Oud merk toestel</th><th>Nieuw merk toestel</th></tr></thead>'
s=s.replace(old_stock_head,new_stock_head,1)
old_stock_row="<td>${r.action==='update'?'€ '+Number(r.old.price||0).toFixed(2):'—'}</td><td><strong>€ ${Number(r.action==='update'?r.newPrice:r.newPart.price).toFixed(2)}</strong></td>"
new_stock_row=old_stock_row+"<td>${r.action==='update'?esc(r.old.deviceBrand||'—'):'—'}</td><td><strong>${esc(r.action==='update'?(r.newDeviceBrand||'—'):(r.newPart.deviceBrand||'—'))}</strong></td>"
s=s.replace(old_stock_row,new_stock_row,1)
s=s.replace('colspan="6" class="muted">… en nog ${records.length-25} regels','colspan="8" class="muted">… en nog ${records.length-25} regels',1)

report_fn=r'''function downloadStockImportReport(records,fileName){const rows=[['Bestand','Art nr','Actie','Oude voorraad','Nieuwe voorraad','Oude prijs','Nieuwe prijs','Oud merk toestel','Nieuw merk toestel','Opmerking']];for(const r of records){rows.push([fileName,r.artNr,r.action,r.action==='update'?r.old.stock:'',r.action==='update'?r.newStock:r.newPart?.stock??'',r.action==='update'?r.old.price:'',r.action==='update'?r.newPrice:r.newPart?.price??'',r.action==='update'?r.old.deviceBrand||'':'',r.action==='update'?r.newDeviceBrand||'':r.newPart?.deviceBrand||'',r.reason||''])}download('Machinepark_Importverslag_'+todayISO()+'.csv','\ufeff'+rows.map(row=>row.map(csvEscape).join(';')).join('\n'),'text/csv;charset=utf-8')}
'''
if 'function downloadStockImportReport(' not in s:
    s=s.replace('function showStockImportPreview(',report_fn+'function showStockImportPreview(',1)
s=s.replace('<button class="btn" type="button" id="cancelStockImport">Annuleren</button><button class="btn primary" type="button" id="confirmStockImport">Stocktelling verwerken</button>', '<button class="btn" type="button" id="cancelStockImport">Annuleren</button><button class="btn" type="button" id="downloadStockReport">Importverslag downloaden</button><button class="btn primary" type="button" id="confirmStockImport">Stocktelling verwerken</button>',1)
s=s.replace("$('#cancelStockImport').onclick=closeModal;$('#confirmStockImport').onclick=async()=>{", "$('#cancelStockImport').onclick=closeModal;const reportBtn=$('#downloadStockReport');if(reportBtn)reportBtn.onclick=()=>downloadStockImportReport(records,fileName);$('#confirmStockImport').onclick=async()=>{",1)
old_stock_save="for(const r of updates)await put('parts',{...r.old,stock:r.newStock,deviceBrand:r.newDeviceBrand??r.old.deviceBrand??'',price:r.newPrice,updatedAt:new Date().toISOString()});for(const r of adds)await put('parts',r.newPart);"
new_stock_save="const changed=[...updates.map(r=>({...r.old,stock:r.newStock,deviceBrand:r.newDeviceBrand??r.old.deviceBrand??'',price:r.newPrice,updatedAt:new Date().toISOString()})),...adds.map(r=>r.newPart)];btn.textContent=`${changed.length} artikel(en) verwerken…`;await putMany('parts',changed);"
s=s.replace(old_stock_save,new_stock_save,1)

# Dubbel klikken/dubbel opslaan voorkomen in alle modals.
old_modal_submit="$('#modalForm').onsubmit=async e=>{e.preventDefault();await onSave(new FormData(e.target));}"
new_modal_submit="$('#modalForm').onsubmit=async e=>{e.preventDefault();const submit=e.target.querySelector('button[type=submit]');const oldText=submit?.textContent||'Opslaan';if(submit){submit.disabled=true;submit.textContent='Opslaan…'}try{await onSave(new FormData(e.target))}catch(err){console.error(err);alert(err?.message||'Opslaan mislukt.')}finally{if(submit&&document.body.contains(submit)){submit.disabled=false;submit.textContent=oldText}}}"
s=s.replace(old_modal_submit,new_modal_submit,1)

# Extra mobiele en touch-afwerking.
css=r'''
.professional-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.professional-metrics>div{border:1px solid var(--line);background:var(--panel2);border-radius:12px;padding:12px;display:grid;gap:5px}.professional-metrics span{font-size:11px;color:var(--muted)}.professional-metrics strong{font-size:22px}.professional-activity{display:grid;gap:7px}.professional-activity>div{display:grid;grid-template-columns:28px 1fr auto;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid #edf1ef}.professional-activity>div:last-child{border-bottom:0}.professional-activity strong{font-size:12px}.professional-activity small{font-size:11px;color:var(--muted);white-space:nowrap}
@media(max-width:700px){button,.btn,input,select{min-height:44px}.modal-backdrop{padding:0;align-items:flex-end}.modal{width:100%;max-height:96dvh;border-radius:18px 18px 0 0}.modal-body{padding:18px 14px}.modal-head{padding:15px 14px}.modal-foot{padding:12px 14px calc(12px + env(safe-area-inset-bottom));flex-wrap:wrap}.modal-foot .btn{flex:1;min-width:120px}.usage-row{grid-template-columns:minmax(0,1fr) 76px 44px}.usage-suggestions,.device-suggestions{max-height:min(42vh,300px)}.professional-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.professional-activity>div{grid-template-columns:26px 1fr}.professional-activity small{grid-column:2;white-space:normal}.topbar{align-items:flex-start;flex-wrap:wrap}.top-actions{width:100%}.search,.search input{width:100%}.kpis{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}
@media(max-width:430px){.main{padding-left:12px;padding-right:12px}.kpis{grid-template-columns:1fr 1fr}.kpi{padding:13px}.kpi .value{font-size:24px}.professional-metrics{grid-template-columns:1fr 1fr}.usage-row{grid-template-columns:minmax(0,1fr) 68px 44px}}
'''
if '.professional-metrics{' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

# Versie/cache.
for old in ['v1.51 • Logboek undo','v1.50 • Prijsimport hersteld','v1.49 • Importprijzen zijn leidend']:
    s=s.replace(old,'v1.52 • Professionele basis',1)
p.write_text(s,encoding='utf-8')

sw=Path('sw.js')
ws=sw.read_text(encoding='utf-8')
for old in ['machinepark-v1.51-audit-undo','machinepark-v1.50-stock-price-fix','machinepark-v1.49-import-prices-authoritative']:
    ws=ws.replace(old,'machinepark-v1.52-professional-foundation')
sw.write_text(ws,encoding='utf-8')
