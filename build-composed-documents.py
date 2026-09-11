from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
NETLIFY_PERMISSIONS = ROOT / "netlify/functions/_shared/permissions.mjs"
NETLIFY_DATA = ROOT / "netlify/functions/machinepark-data.mjs"
SYNOLOGY_DATA = ROOT / "synology/api/machinepark-data.php"
MARKER = 'data-machinepark-build-fix="composed-documents-v1"'
SERVER_MARKER = 'machinepark-composed-documents-v1'


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    return text.replace(old, new, 1)


index = INDEX.read_text(encoding="utf-8")
if MARKER not in index:
    settings_anchor = '<div class="settings-card"><h4>Back-up</h4>'
    settings_card = '''<div class="settings-card" id="composedDocumentsSettingsCard"><h4>Samengestelde overzichten</h4><p>Maak een apart dossier met geselecteerde toestellen en hun volledige onderhouds-, depannage-, service- en onderdelenhistoriek.</p><button class="btn primary" type="button" id="openComposedDocuments">Samengesteld overzicht maken</button></div>\n        '''
    index = replace_once(index, settings_anchor, settings_card + settings_anchor, "knop Samengesteld overzicht maken in Beheer")

    style = r'''
<style data-machinepark-build-fix="composed-documents-v1">
.composed-window{position:fixed;inset:0;z-index:2600;background:#f2f5f3;display:none;overflow:auto;color:var(--text)}
.composed-window.show{display:block}
.composed-shell{min-height:100vh;padding:24px 28px 46px;max-width:1500px;margin:0 auto}
.composed-head{position:sticky;top:0;z-index:4;margin:-24px -28px 20px;padding:18px 28px;background:rgba(242,245,243,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:14px;align-items:center}
.composed-head h2{margin:0;font-size:24px}.composed-head p{margin:3px 0 0;color:var(--muted);font-size:12px}
.composed-section{background:#fff;border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);margin-bottom:18px;overflow:hidden}
.composed-section-head{padding:16px 18px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap}
.composed-section-head h3{margin:0;font-size:16px}.composed-section-body{padding:16px 18px}
.composed-create-grid{display:grid;grid-template-columns:minmax(220px,1fr) minmax(260px,1.4fr);gap:12px;margin-bottom:12px}
.composed-create-grid .field{min-width:0}.composed-create-grid input{width:100%;border:1px solid var(--line);border-radius:10px;padding:10px 11px;background:#fff}
.composed-toolbar{display:flex;align-items:center;justify-content:space-between;gap:9px;flex-wrap:wrap;margin-bottom:11px}.composed-toolbar-left,.composed-toolbar-right{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.composed-count{font-size:12px;font-weight:800;color:#355147}.composed-device-table{min-width:880px}.composed-device-table input[type="checkbox"]{width:17px;height:17px}
.composed-location-cell{max-width:330px}.composed-location-cell strong{display:block}.composed-location-cell small{display:block;color:var(--muted);margin-top:2px}
.composed-saved-search{width:min(360px,100%);border:1px solid var(--line);border-radius:10px;padding:9px 11px;background:#fff}
.composed-actions{display:flex;gap:6px;flex-wrap:wrap}.composed-actions .btn{white-space:nowrap}
.composed-preview{position:fixed;inset:0;z-index:2700;background:rgba(13,29,24,.55);display:none;padding:18px;overflow:auto}.composed-preview.show{display:block}
.composed-preview-card{max-width:1120px;margin:0 auto;background:#fff;border-radius:16px;box-shadow:0 30px 80px rgba(0,0,0,.28);overflow:hidden}
.composed-preview-head{position:sticky;top:0;z-index:2;background:#fff;border-bottom:1px solid var(--line);padding:14px 17px;display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap}
.composed-preview-head h3{margin:0;font-size:18px}.composed-preview-actions{display:flex;gap:7px;flex-wrap:wrap}
.composed-document{padding:24px 26px 34px}.composed-document h1{font-size:25px;margin:0 0 4px}.composed-document>.muted{margin-bottom:18px}
.composed-doc-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:16px 0}.composed-doc-summary>div{border:1px solid var(--line);border-radius:11px;padding:10px;background:#f8faf9}.composed-doc-summary span{display:block;font-size:10px;text-transform:uppercase;color:var(--muted);font-weight:800}.composed-doc-summary strong{display:block;margin-top:4px;font-size:14px}
.composed-device-block{border-top:2px solid #294f43;padding-top:16px;margin-top:23px;break-inside:avoid}.composed-device-block h2{margin:0;font-size:19px}.composed-device-meta{display:flex;gap:8px 16px;flex-wrap:wrap;font-size:12px;margin:5px 0 13px;color:#4f5d57}
.composed-subsection{margin-top:15px}.composed-subsection h3{font-size:13px;margin:0 0 8px;text-transform:uppercase;letter-spacing:.04em;color:#40534b}.composed-doc-table{width:100%;border-collapse:collapse}.composed-doc-table th,.composed-doc-table td{border:1px solid #dfe6e3;padding:7px 8px;text-align:left;font-size:11px;vertical-align:top}.composed-doc-table th{background:#f3f6f4;font-size:10px;text-transform:uppercase;color:#61706a}.composed-doc-table td.qty{text-align:right;font-weight:800;white-space:nowrap}
.composed-empty{padding:26px 16px;text-align:center;color:var(--muted);font-size:12px}
@media(max-width:760px){.composed-shell{padding:14px 12px 32px}.composed-head{margin:-14px -12px 14px;padding:13px 12px}.composed-head h2{font-size:19px}.composed-create-grid{grid-template-columns:1fr}.composed-section-body{padding:12px}.composed-doc-summary{grid-template-columns:1fr}.composed-document{padding:18px 14px 26px}.composed-preview{padding:0}.composed-preview-card{min-height:100vh;border-radius:0}.composed-preview-actions{width:100%}.composed-preview-actions .btn{flex:1 1 auto}}
@media print{.composed-preview-head{display:none!important}.composed-preview{display:block!important;position:static!important;padding:0!important;background:#fff!important}.composed-preview-card{box-shadow:none!important;max-width:none!important}.composed-document{padding:0!important}}
</style>
'''
    index = index.replace("</head>", style + "</head>", 1)

    script = r'''
<script data-machinepark-build-fix="composed-documents-v1">
(() => {
  const COMPOSED_STORAGE_KEY = 'machinepark-composed-documents-v1';
  const JSPDF_SRC = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
  let selectedComposedDevices = new Set();
  let composedDeviceQuery = '';
  let composedSavedQuery = '';
  let jsPdfPromise = null;

  function composedEsc(value){
    if(typeof esc === 'function') return esc(String(value ?? ''));
    return String(value ?? '').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  }
  function composedKey(value){
    if(typeof normalizeSearch === 'function') return normalizeSearch(String(value ?? ''));
    return String(value ?? '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim();
  }
  function composedClone(value){return JSON.parse(JSON.stringify(value ?? null));}
  function composedDate(value){
    if(!value)return '—';
    const d=new Date(value.length<=10?`${value}T00:00:00`:value);
    return Number.isNaN(d.getTime())?String(value):d.toLocaleString('nl-BE',{dateStyle:'short',timeStyle:value.length>10?'short':undefined});
  }
  function composedRead(){
    try{const parsed=JSON.parse(localStorage.getItem(COMPOSED_STORAGE_KEY)||'[]');return Array.isArray(parsed)?parsed:[];}catch(_){return [];}
  }
  function composedWrite(list){
    const safe=Array.isArray(list)?list:[];
    try{localStorage.setItem(COMPOSED_STORAGE_KEY,JSON.stringify(safe));}catch(e){console.warn('[Machinepark] samengesteld document lokaal bewaren',e);}
    state.composedDocuments=safe;
    return safe;
  }
  function composedList(){return Array.isArray(state?.composedDocuments)?state.composedDocuments:composedRead();}
  function composedNotify(message){if(typeof toast==='function')toast(message);else alert(message);}
  function composedLocation(device,when=''){
    try{return typeof deviceLocationAt==='function'?deviceLocationAt(device,when||undefined)||(device.location||''):device.location||'';}catch(_){return device?.location||'';}
  }
  function composedCurrentUser(){
    const u=window.Clerk?.user||{};
    return String(u.fullName||[u.firstName,u.lastName].filter(Boolean).join(' ')||u.username||u.primaryEmailAddress?.emailAddress||'Gebruiker');
  }
  function composedCanManage(){
    if(window.machineparkIsAdmin)return true;
    if(typeof window.machineparkHasPermission==='function')return Boolean(window.machineparkHasPermission('view.settings'));
    return state?.view==='settings';
  }

  // Bewaar samengestelde documenten mee in de centrale snapshot zonder de bestaande IndexedDB-stores te wijzigen.
  if(typeof localSnapshot==='function'){
    const originalLocalSnapshot=localSnapshot;
    localSnapshot=async function(){const data=await originalLocalSnapshot();data.composedDocuments=composedList();return data;};
  }
  if(typeof replaceLocalSnapshot==='function'){
    const originalReplaceLocalSnapshot=replaceLocalSnapshot;
    replaceLocalSnapshot=async function(data){await originalReplaceLocalSnapshot(data);composedWrite(Array.isArray(data?.composedDocuments)?data.composedDocuments:[]);};
  }
  if(typeof makeBackupPayload==='function'){
    const originalMakeBackupPayload=makeBackupPayload;
    makeBackupPayload=async function(){const data=await originalMakeBackupPayload();data.composedDocuments=composedList();data.counts={...(data.counts||{}),composedDocuments:data.composedDocuments.length};return data;};
  }
  if(typeof refresh==='function'){
    const originalRefresh=refresh;
    refresh=async function(){await originalRefresh();state.composedDocuments=composedRead();if(document.getElementById('composedDocumentsWindow')?.classList.contains('show'))renderComposedSavedTable();};
  }
  state.composedDocuments=composedRead();

  function ensureComposedUi(){
    if(document.getElementById('composedDocumentsWindow'))return;
    const windowEl=document.createElement('div');
    windowEl.id='composedDocumentsWindow';
    windowEl.className='composed-window';
    windowEl.innerHTML=`<div class="composed-shell">
      <div class="composed-head"><div><h2>Samengesteld overzicht maken</h2><p>Selecteer toestellen en bewaar daarna het volledige dossier in Samengestelde documenten.</p></div><button class="btn" type="button" id="closeComposedDocuments">Terug naar Beheer</button></div>
      <section class="composed-section"><div class="composed-section-head"><h3>Nieuw samengesteld document</h3><span class="composed-count" id="composedSelectedCount">0 toestellen geselecteerd</span></div><div class="composed-section-body">
        <div class="composed-create-grid"><div class="field"><label>Naam / firma van het document</label><input id="composedDocumentName" maxlength="140" placeholder="Bijv. Firma X · volledig toesteldossier"></div><div class="field"><label>Zoek firma, locatie of toestel</label><input id="composedDeviceSearch" type="search" autocomplete="off" placeholder="Typ locatie, WCL-nummer, merk, model of serienummer…"></div></div>
        <div class="composed-toolbar"><div class="composed-toolbar-left"><button class="btn small" id="composedSelectVisible" type="button">Alles zichtbaar aanvinken</button><button class="btn small" id="composedClearSelection" type="button">Selectie wissen</button></div><div class="composed-toolbar-right"><button class="btn primary" id="composedSaveDocument" type="button">Opslaan in samengestelde documenten</button></div></div>
        <div class="table-wrap"><table class="table composed-device-table"><thead><tr><th></th><th>WCL nr.</th><th>Firma / locatie</th><th>Toestel</th><th>Status</th></tr></thead><tbody id="composedDeviceBody"></tbody></table></div>
      </div></section>
      <section class="composed-section"><div class="composed-section-head"><h3>Samengestelde documenten</h3><input class="composed-saved-search" id="composedSavedSearch" type="search" autocomplete="off" placeholder="Zoek in opgeslagen documenten…"></div><div class="composed-section-body"><div class="table-wrap"><table class="table" style="min-width:900px"><thead><tr><th>Naam / firma</th><th>Opgeslagen</th><th>Toestellen</th><th>Opgeslagen door</th><th>Acties</th></tr></thead><tbody id="composedSavedBody"></tbody></table></div></div></section>
    </div>`;
    document.body.appendChild(windowEl);
    const preview=document.createElement('div');
    preview.id='composedDocumentPreview';preview.className='composed-preview';
    preview.innerHTML='<div class="composed-preview-card"><div class="composed-preview-head"><h3 id="composedPreviewTitle">Samengesteld document</h3><div class="composed-preview-actions"><button class="btn" type="button" id="composedPreviewMail">E-mailen</button><button class="btn" type="button" id="composedPreviewPrint">Afdrukken</button><button class="btn" type="button" id="composedPreviewPdf">PDF opslaan</button><button class="btn" type="button" id="composedPreviewClose">Sluiten</button></div></div><div id="composedPreviewBody" class="composed-document"></div></div>';
    document.body.appendChild(preview);

    document.getElementById('closeComposedDocuments').onclick=closeComposedWindow;
    document.getElementById('composedDeviceSearch').oninput=e=>{composedDeviceQuery=e.target.value||'';renderComposedDevices();};
    document.getElementById('composedSavedSearch').oninput=e=>{composedSavedQuery=e.target.value||'';renderComposedSavedTable();};
    document.getElementById('composedSelectVisible').onclick=()=>{composedFilteredDevices().forEach(d=>selectedComposedDevices.add(d.id));renderComposedDevices();};
    document.getElementById('composedClearSelection').onclick=()=>{selectedComposedDevices.clear();renderComposedDevices();};
    document.getElementById('composedSaveDocument').onclick=saveComposedDocument;
    document.getElementById('composedDeviceBody').addEventListener('change',event=>{const cb=event.target.closest('[data-composed-device]');if(!cb)return;if(cb.checked)selectedComposedDevices.add(cb.dataset.composedDevice);else selectedComposedDevices.delete(cb.dataset.composedDevice);updateComposedSelectedCount();});
    document.getElementById('composedSavedBody').addEventListener('click',handleSavedAction);
    document.getElementById('composedPreviewClose').onclick=closeComposedPreview;
  }

  function openComposedWindow(){
    if(!composedCanManage()){alert('Je hebt geen toegang tot Beheer.');return;}
    ensureComposedUi();
    selectedComposedDevices.clear();composedDeviceQuery='';composedSavedQuery='';
    document.getElementById('composedDeviceSearch').value='';document.getElementById('composedSavedSearch').value='';
    const name=document.getElementById('composedDocumentName');if(name)name.value='';
    document.getElementById('composedDocumentsWindow').classList.add('show');document.body.style.overflow='hidden';
    renderComposedDevices();renderComposedSavedTable();
  }
  function closeComposedWindow(){document.getElementById('composedDocumentsWindow')?.classList.remove('show');document.body.style.overflow='';}

  function composedFilteredDevices(){
    const q=composedKey(composedDeviceQuery);
    return [...(state.devices||[])].filter(d=>{
      if(!q)return true;
      return composedKey([d.assetCode,composedLocation(d),d.location,d.brand,d.model,d.serial,d.status].filter(Boolean).join(' ')).includes(q);
    }).sort((a,b)=>String(composedLocation(a)||'').localeCompare(String(composedLocation(b)||''),'nl',{numeric:true,sensitivity:'base'})||String(a.assetCode||'').localeCompare(String(b.assetCode||''),'nl',{numeric:true,sensitivity:'base'}));
  }
  function updateComposedSelectedCount(){const el=document.getElementById('composedSelectedCount');if(el)el.textContent=`${selectedComposedDevices.size} toestel${selectedComposedDevices.size===1?'':'len'} geselecteerd`;}
  function renderComposedDevices(){
    const body=document.getElementById('composedDeviceBody');if(!body)return;
    const rows=composedFilteredDevices();
    body.innerHTML=rows.length?rows.map(d=>`<tr><td><input type="checkbox" data-composed-device="${composedEsc(d.id)}" ${selectedComposedDevices.has(d.id)?'checked':''}></td><td><strong>${composedEsc(d.assetCode||'—')}</strong></td><td class="composed-location-cell"><strong>${composedEsc(composedLocation(d)||'—')}</strong>${d.location&&d.location!==composedLocation(d)?`<small>Bronlocatie: ${composedEsc(d.location)}</small>`:''}</td><td>${composedEsc([d.brand,d.model].filter(Boolean).join(' · ')||'—')}<br><small class="muted">${d.serial?'S/N '+composedEsc(d.serial):''}</small></td><td>${typeof statusBadge==='function'?statusBadge(d.status||'Actief'):composedEsc(d.status||'Actief')}</td></tr>`).join(''):'<tr><td colspan="5"><div class="composed-empty">Geen toestellen gevonden voor deze zoekopdracht.</div></td></tr>';
    updateComposedSelectedCount();
  }

  function usedPartIds(records){const ids=new Set();records.forEach(r=>(r.usedParts||[]).forEach(u=>{if(u?.partId)ids.add(u.partId);}));return ids;}
  function composedSnapshot(deviceIds){
    const ids=new Set(deviceIds),devices=(state.devices||[]).filter(d=>ids.has(d.id)).map(composedClone);
    const maintenance=(state.maintenance||[]).filter(r=>r?.isDraft!==true&&ids.has(r.deviceId)).map(composedClone);
    const breakdowns=(state.breakdowns||[]).filter(r=>r?.isDraft!==true&&ids.has(r.deviceId)).map(composedClone);
    const partIds=usedPartIds([...maintenance,...breakdowns]);
    const parts=(state.parts||[]).filter(p=>partIds.has(p.id)).map(composedClone);
    return {devices,maintenance,breakdowns,parts,capturedAt:new Date().toISOString()};
  }
  async function persistComposedList(next){composedWrite(next);if(typeof scheduleCentralSync==='function')scheduleCentralSync();renderComposedSavedTable();}
  async function saveComposedDocument(){
    if(!selectedComposedDevices.size){alert('Vink minstens één toestel aan.');return;}
    const nameInput=document.getElementById('composedDocumentName');let name=String(nameInput?.value||'').trim();
    if(!name){const selected=(state.devices||[]).filter(d=>selectedComposedDevices.has(d.id)),locations=[...new Set(selected.map(d=>composedLocation(d)).filter(Boolean))];name=locations.length===1?`${locations[0]} · samengesteld overzicht`:`Samengesteld overzicht · ${new Date().toLocaleDateString('nl-BE')}`;if(nameInput)nameInput.value=name;}
    const now=new Date().toISOString(),entry={id:`cmp_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,8)}`,name,createdAt:now,updatedAt:now,createdBy:composedCurrentUser(),deviceIds:[...selectedComposedDevices],snapshot:composedSnapshot([...selectedComposedDevices])};
    const next=[entry,...composedList()];await persistComposedList(next);selectedComposedDevices.clear();renderComposedDevices();composedNotify('Samengesteld document opgeslagen');
  }

  function renderComposedSavedTable(){
    const body=document.getElementById('composedSavedBody');if(!body)return;
    const q=composedKey(composedSavedQuery),list=[...composedList()].filter(doc=>!q||composedKey([doc.name,doc.createdBy,(doc.snapshot?.devices||[]).map(d=>[d.assetCode,composedLocation(d),d.location].join(' ')).join(' ')].join(' ')).includes(q)).sort((a,b)=>String(b.createdAt||'').localeCompare(String(a.createdAt||'')));
    body.innerHTML=list.length?list.map(doc=>`<tr><td><strong>${composedEsc(doc.name||'Samengesteld document')}</strong></td><td>${composedEsc(composedDate(doc.createdAt))}</td><td>${(doc.snapshot?.devices||[]).length||doc.deviceIds?.length||0}</td><td>${composedEsc(doc.createdBy||'—')}</td><td><div class="composed-actions"><button class="btn small" data-composed-action="view" data-composed-id="${composedEsc(doc.id)}">Bekijken</button><button class="btn small" data-composed-action="mail" data-composed-id="${composedEsc(doc.id)}">E-mailen</button><button class="btn small" data-composed-action="print" data-composed-id="${composedEsc(doc.id)}">Afdrukken</button><button class="btn small" data-composed-action="pdf" data-composed-id="${composedEsc(doc.id)}">PDF opslaan</button><button class="btn small danger" data-composed-action="delete" data-composed-id="${composedEsc(doc.id)}">Wissen</button></div></td></tr>`).join(''):'<tr><td colspan="5"><div class="composed-empty">Nog geen samengestelde documenten opgeslagen.</div></td></tr>';
  }
  function composedById(id){return composedList().find(doc=>doc.id===id)||null;}
  async function handleSavedAction(event){const button=event.target.closest('[data-composed-action]');if(!button)return;const doc=composedById(button.dataset.composedId);if(!doc)return;const action=button.dataset.composedAction;if(action==='view')openComposedPreview(doc);if(action==='mail')await mailComposedDocument(doc,button);if(action==='print')printComposedDocument(doc);if(action==='pdf')await saveComposedPdf(doc,button);if(action==='delete')await deleteComposedDocument(doc);}
  async function deleteComposedDocument(doc){if(!confirm(`Samengesteld document “${doc.name}” wissen? De originele toestellen, onderhouden, depannages, services en onderdelen blijven volledig behouden.`))return;await persistComposedList(composedList().filter(x=>x.id!==doc.id));composedNotify('Samengesteld document gewist');}

  function partLabel(snapshot,usage){const p=(snapshot.parts||[]).find(x=>x.id===usage?.partId);return {code:p?.artNr||usage?.partId||'—',description:p?.description||'Onbekend onderdeel',qty:Number(usage?.qty||0)};}
  function recordParts(snapshot,record){
    const rows=[];(record?.usedParts||[]).forEach(u=>{const row=partLabel(snapshot,u);if(row.qty>0)rows.push({...row,kind:'stock'});});
    (record?.oneOffParts||[]).forEach(p=>{const code=String(p?.supplierCode||p?.supplier||'Eenmalig'),description=[p?.supplierCode&&p?.supplier?p.supplier:'',p?.description||''].filter(Boolean).join(' · ')||'Eenmalig onderdeel';rows.push({code,description,qty:Number(p?.qty||1),kind:'oneoff'});});return rows;
  }
  function deviceRecords(snapshot,deviceId){
    const maintenance=(snapshot.maintenance||[]).filter(r=>r.deviceId===deviceId).map(r=>({kind:'Onderhoud',item:r}));
    const breakdowns=(snapshot.breakdowns||[]).filter(r=>r.deviceId===deviceId).map(r=>({kind:r.serviceKind==='other'?(r.workTypeName||'Andere werken'):'Depannage',item:r}));
    return [...maintenance,...breakdowns].sort((a,b)=>String(a.item.date||a.item.createdAt||'').localeCompare(String(b.item.date||b.item.createdAt||'')));
  }
  function deviceServiceVisits(snapshot,deviceId){
    const rows=deviceRecords(snapshot,deviceId).filter(row=>row.item?.serviceVisitId);const map=new Map();
    rows.forEach(row=>{const r=row.item,id=r.serviceReportId||r.serviceVisitId;if(!map.has(id))map.set(id,{id,date:r.serviceReportDate||r.serviceVisitDate||r.date||'',location:r.serviceVisitLocation||'',technician:r.serviceReportTechnician||r.serviceVisitTechnician||r.technician||'',kinds:new Set()});map.get(id).kinds.add(row.kind);});
    return [...map.values()].map(v=>({...v,kinds:[...v.kinds].join(', ')})).sort((a,b)=>String(a.date).localeCompare(String(b.date)));
  }
  function mergedDeviceParts(snapshot,deviceId){
    const map=new Map();deviceRecords(snapshot,deviceId).forEach(row=>recordParts(snapshot,row.item).forEach(p=>{const key=composedKey(`${p.kind}|${p.code}|${p.description}`);if(!map.has(key))map.set(key,{...p,qty:0});map.get(key).qty+=Number(p.qty||0);}));return [...map.values()].sort((a,b)=>String(a.code).localeCompare(String(b.code),'nl',{numeric:true,sensitivity:'base'}));
  }
  function mergedAllParts(snapshot){const map=new Map();(snapshot.devices||[]).forEach(d=>mergedDeviceParts(snapshot,d.id).forEach(p=>{const key=composedKey(`${p.kind}|${p.code}|${p.description}`);if(!map.has(key))map.set(key,{...p,qty:0,devices:new Set()});const row=map.get(key);row.qty+=Number(p.qty||0);row.devices.add(d.assetCode||d.id);}));return [...map.values()].map(x=>({...x,devices:[...x.devices]}));}
  function recordDescription(kind,r){if(kind==='Onderhoud')return r.notes||r.workNotes||'—';return [r.issue,r.diagnosis,r.solution].filter(Boolean).join(' · ')||r.notes||'—';}
  function htmlPartTable(rows){return rows.length?`<table class="composed-doc-table"><thead><tr><th>Onderdeel</th><th>Omschrijving</th><th>Aantal</th></tr></thead><tbody>${rows.map(p=>`<tr><td>${composedEsc(p.code)}</td><td>${composedEsc(p.description)}${p.kind==='oneoff'?'<br><small>Eenmalig / leverancier</small>':''}</td><td class="qty">${composedEsc(p.qty)}</td></tr>`).join('')}</tbody></table>`:'<div class="muted">Geen onderdelen geregistreerd.</div>';}
  function documentHtml(doc){
    const s=doc.snapshot||{devices:[],maintenance:[],breakdowns:[],parts:[]};const totalRecords=(s.maintenance||[]).length+(s.breakdowns||[]).length;
    const devices=(s.devices||[]).map(d=>{
      const records=deviceRecords(s,d.id),visits=deviceServiceVisits(s,d.id),parts=mergedDeviceParts(s,d.id),locations=Array.isArray(d.locationHistory)?[...d.locationHistory].sort((a,b)=>String(a.effectiveFrom||'').localeCompare(String(b.effectiveFrom||''))):[];
      const locationHtml=locations.length?`<table class="composed-doc-table"><thead><tr><th>Vanaf</th><th>Locatie</th></tr></thead><tbody>${locations.map(x=>`<tr><td>${composedEsc(composedDate(x.effectiveFrom||''))}</td><td>${composedEsc(x.location||'—')}</td></tr>`).join('')}</tbody></table>`:'<div class="muted">Geen locatiehistoriek geregistreerd.</div>';
      const visitHtml=visits.length?`<table class="composed-doc-table"><thead><tr><th>Datum</th><th>Locatie</th><th>Technieker</th><th>Werkzaamheden</th></tr></thead><tbody>${visits.map(v=>`<tr><td>${composedEsc(composedDate(v.date))}</td><td>${composedEsc(v.location||composedLocation(d)||'—')}</td><td>${composedEsc(v.technician||'—')}</td><td>${composedEsc(v.kinds||'—')}</td></tr>`).join('')}</tbody></table>`:'<div class="muted">Geen gekoppelde servicebezoeken.</div>';
      const recordHtml=records.length?`<table class="composed-doc-table"><thead><tr><th>Datum</th><th>Type</th><th>Technieker</th><th>Details</th><th>Onderdelen</th></tr></thead><tbody>${records.map(row=>`<tr><td>${composedEsc(composedDate(row.item.date||row.item.createdAt))}</td><td>${composedEsc(row.kind)}</td><td>${composedEsc(row.item.technician||row.item.serviceVisitTechnician||'—')}</td><td>${composedEsc(recordDescription(row.kind,row.item))}</td><td>${recordParts(s,row.item).length?recordParts(s,row.item).map(p=>`${composedEsc(p.code)} × ${composedEsc(p.qty)}`).join('<br>'):'—'}</td></tr>`).join('')}</tbody></table>`:'<div class="muted">Geen onderhoud, depannage of andere service geregistreerd.</div>';
      return `<section class="composed-device-block"><h2>${composedEsc(d.assetCode||'Toestel')} · ${composedEsc([d.brand,d.model].filter(Boolean).join(' ')||'—')}</h2><div class="composed-device-meta"><span><strong>Huidige locatie:</strong> ${composedEsc(composedLocation(d)||d.location||'—')}</span><span><strong>Serienummer:</strong> ${composedEsc(d.serial||'—')}</span><span><strong>Status:</strong> ${composedEsc(d.status||'Actief')}</span><span><strong>Installatie:</strong> ${composedEsc(d.installDateSource||composedDate(d.installDate)||'—')}</span></div><div class="composed-subsection"><h3>Locatiehistoriek</h3>${locationHtml}</div><div class="composed-subsection"><h3>Serviceverslagen / servicebezoeken</h3>${visitHtml}</div><div class="composed-subsection"><h3>Onderhoud, depannages en andere services</h3>${recordHtml}</div><div class="composed-subsection"><h3>Alle ooit gebruikte onderdelen voor dit toestel</h3>${htmlPartTable(parts)}</div></section>`;
    }).join('');
    const allParts=mergedAllParts(s);
    return `<h1>${composedEsc(doc.name||'Samengesteld document')}</h1><div class="muted">Vastgelegd op ${composedEsc(composedDate(s.capturedAt||doc.createdAt))} · opgeslagen door ${composedEsc(doc.createdBy||'—')}</div><div class="composed-doc-summary"><div><span>Toestellen</span><strong>${(s.devices||[]).length}</strong></div><div><span>Onderhoud / depannage / service</span><strong>${totalRecords}</strong></div><div><span>Unieke gebruikte onderdelen</span><strong>${allParts.length}</strong></div></div>${devices||'<div class="composed-empty">Geen toestelgegevens in dit document.</div>'}<section class="composed-device-block"><h2>Totaal gebruikte onderdelen · alle geselecteerde toestellen</h2><div class="composed-subsection">${allParts.length?`<table class="composed-doc-table"><thead><tr><th>Onderdeel</th><th>Omschrijving</th><th>Totaal aantal</th><th>Toestellen</th></tr></thead><tbody>${allParts.map(p=>`<tr><td>${composedEsc(p.code)}</td><td>${composedEsc(p.description)}</td><td class="qty">${composedEsc(p.qty)}</td><td>${composedEsc(p.devices.join(', '))}</td></tr>`).join('')}</tbody></table>`:'<div class="muted">Geen onderdelen geregistreerd.</div>'}</div></section>`;
  }

  function openComposedPreview(doc){ensureComposedUi();const preview=document.getElementById('composedDocumentPreview');preview.dataset.composedId=doc.id;document.getElementById('composedPreviewTitle').textContent=doc.name||'Samengesteld document';document.getElementById('composedPreviewBody').innerHTML=documentHtml(doc);document.getElementById('composedPreviewMail').onclick=event=>mailComposedDocument(doc,event.currentTarget);document.getElementById('composedPreviewPrint').onclick=()=>printComposedDocument(doc);document.getElementById('composedPreviewPdf').onclick=event=>saveComposedPdf(doc,event.currentTarget);preview.classList.add('show');}
  function closeComposedPreview(){document.getElementById('composedDocumentPreview')?.classList.remove('show');}

  function printStyles(){return `body{font-family:Arial,sans-serif;color:#17231f;margin:18mm;font-size:11px}h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;border-top:2px solid #294f43;padding-top:12px;margin-top:20px}h3{font-size:11px;text-transform:uppercase;margin:13px 0 6px}.muted{color:#67756f}.composed-doc-summary{display:flex;gap:10px;margin:14px 0}.composed-doc-summary>div{border:1px solid #dfe6e3;padding:8px;min-width:120px}.composed-doc-summary span{display:block;font-size:9px;text-transform:uppercase}.composed-doc-summary strong{display:block;margin-top:3px}.composed-device-meta{display:flex;gap:8px 16px;flex-wrap:wrap;margin:5px 0 10px}.composed-doc-table{width:100%;border-collapse:collapse}.composed-doc-table th,.composed-doc-table td{border:1px solid #cfd8d4;padding:5px 6px;text-align:left;vertical-align:top;font-size:9px}.composed-doc-table th{background:#f2f5f3}.qty{text-align:right!important}.composed-device-block{break-inside:auto}table{break-inside:auto}tr{break-inside:avoid}@page{size:A4;margin:13mm}`;}
  function printComposedDocument(doc){const win=window.open('','_blank');if(!win){alert('Het afdrukvenster kon niet worden geopend. Sta pop-ups toe en probeer opnieuw.');return;}win.document.open();win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${composedEsc(doc.name||'Samengesteld document')}</title><style>${printStyles()}</style></head><body class="composed-document">${documentHtml(doc)}<script>window.onload=()=>setTimeout(()=>window.print(),120)<\/script></body></html>`);win.document.close();}

  function loadJsPdf(){
    if(window.jspdf?.jsPDF)return Promise.resolve(window.jspdf.jsPDF);if(jsPdfPromise)return jsPdfPromise;
    jsPdfPromise=new Promise((resolve,reject)=>{let script=document.getElementById('machineparkJsPdfScript');const ready=()=>window.jspdf?.jsPDF?resolve(window.jspdf.jsPDF):reject(new Error('PDF-bibliotheek is niet beschikbaar.'));if(script){script.addEventListener('load',ready,{once:true});script.addEventListener('error',()=>reject(new Error('PDF-bibliotheek kon niet worden geladen.')),{once:true});setTimeout(ready,0);return;}script=document.createElement('script');script.id='machineparkJsPdfScript';script.src=JSPDF_SRC;script.async=true;script.onload=ready;script.onerror=()=>reject(new Error('PDF-bibliotheek kon niet worden geladen.'));document.head.appendChild(script);}).catch(e=>{jsPdfPromise=null;throw e;});return jsPdfPromise;
  }
  function pdfSafe(value){return String(value??'').replace(/[–—]/g,'-').replace(/[‘’]/g,"'").replace(/[“”]/g,'"').replace(/…/g,'...').replace(/[^\x20-\x7E\xA0-\xFF\n]/g,' ');}
  function pdfLinesForDocument(doc){
    const s=doc.snapshot||{devices:[],maintenance:[],breakdowns:[],parts:[]},lines=[];lines.push(doc.name||'Samengesteld document');lines.push(`Vastgelegd: ${composedDate(s.capturedAt||doc.createdAt)} | Opgeslagen door: ${doc.createdBy||'—'}`);lines.push(`Toestellen: ${(s.devices||[]).length} | Onderhoud/depannage/service: ${(s.maintenance||[]).length+(s.breakdowns||[]).length}`);lines.push('');
    (s.devices||[]).forEach(d=>{lines.push(`TOESTEL ${d.assetCode||'—'} | ${[d.brand,d.model].filter(Boolean).join(' ')||'—'}`);lines.push(`Locatie: ${composedLocation(d)||d.location||'—'} | Serienummer: ${d.serial||'—'} | Status: ${d.status||'Actief'} | Installatie: ${d.installDateSource||d.installDate||'—'}`);const locs=Array.isArray(d.locationHistory)?d.locationHistory:[];if(locs.length){lines.push('Locatiehistoriek:');locs.forEach(x=>lines.push(`  ${composedDate(x.effectiveFrom||'')} - ${x.location||'—'}`));}const visits=deviceServiceVisits(s,d.id);if(visits.length){lines.push('Serviceverslagen / servicebezoeken:');visits.forEach(v=>lines.push(`  ${composedDate(v.date)} | ${v.location||'—'} | ${v.technician||'—'} | ${v.kinds||'—'}`));}const records=deviceRecords(s,d.id);lines.push('Onderhoud, depannages en andere services:');if(!records.length)lines.push('  Geen registraties.');records.forEach(row=>{lines.push(`  ${composedDate(row.item.date||row.item.createdAt)} | ${row.kind} | ${row.item.technician||row.item.serviceVisitTechnician||'—'}`);lines.push(`    ${recordDescription(row.kind,row.item)}`);const parts=recordParts(s,row.item);if(parts.length)lines.push(`    Onderdelen: ${parts.map(p=>`${p.code} x ${p.qty}`).join(', ')}`);});const parts=mergedDeviceParts(s,d.id);lines.push('Alle ooit gebruikte onderdelen:');if(!parts.length)lines.push('  Geen onderdelen geregistreerd.');parts.forEach(p=>lines.push(`  ${p.code} | ${p.description} | totaal ${p.qty}`));lines.push('');});
    const all=mergedAllParts(s);lines.push('TOTAAL GEBRUIKTE ONDERDELEN - ALLE GESELECTEERDE TOESTELLEN');if(!all.length)lines.push('Geen onderdelen geregistreerd.');all.forEach(p=>lines.push(`${p.code} | ${p.description} | totaal ${p.qty} | ${p.devices.join(', ')}`));return lines;
  }
  async function createComposedPdfFile(doc){
    const JsPDF=await loadJsPdf(),pdf=new JsPDF({unit:'mm',format:'a4',orientation:'portrait',compress:true});const margin=15,maxY=282,width=180;let y=18,page=1;
    const header=()=>{pdf.setFont('helvetica','bold');pdf.setFontSize(16);pdf.text(pdfSafe(doc.name||'Samengesteld document'),margin,12);pdf.setFontSize(7);pdf.setFont('helvetica','normal');pdf.text(`Pagina ${page}`,195,12,{align:'right'});pdf.setDrawColor(70);pdf.line(margin,15,195,15);y=21;};header();
    for(const raw of pdfLinesForDocument(doc)){const text=pdfSafe(raw||' '),isTitle=/^(TOESTEL |TOTAAL GEBRUIKTE ONDERDELEN)/.test(text);pdf.setFont('helvetica',isTitle?'bold':'normal');pdf.setFontSize(isTitle?11:8.5);const wrapped=pdf.splitTextToSize(text,width);const needed=Math.max(1,wrapped.length)*(isTitle?5:4.1)+(isTitle?3:1);if(y+needed>maxY){pdf.addPage();page+=1;header();}pdf.text(wrapped,margin,y);y+=needed;}
    const blob=pdf.output('blob'),safe=String(doc.name||'Samengesteld_document').replace(/[\\/:*?"<>|]+/g,'-').replace(/\s+/g,'_').slice(0,100);return new File([blob],`${safe||'Samengesteld_document'}.pdf`,{type:'application/pdf'});
  }
  function downloadFile(file){const url=URL.createObjectURL(file),a=document.createElement('a');a.href=url;a.download=file.name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}
  async function withBusy(button,label,work){const old=button?.textContent;if(button){button.disabled=true;button.textContent=label;}try{return await work();}finally{if(button){button.disabled=false;button.textContent=old;}}}
  async function saveComposedPdf(doc,button){try{await withBusy(button,'PDF maken…',async()=>{const file=await createComposedPdfFile(doc);downloadFile(file);});composedNotify('PDF opgeslagen');}catch(e){console.error(e);alert(e.message||'PDF maken is mislukt.');}}
  async function mailComposedDocument(doc,button){try{await withBusy(button,'PDF maken…',async()=>{const file=await createComposedPdfFile(doc);if(navigator.share&&navigator.canShare?.({files:[file]})){await navigator.share({files:[file],title:doc.name||'Samengesteld document',text:'Samengesteld Machinepark-overzicht als PDF.'});return;}downloadFile(file);const subject=doc.name||'Samengesteld Machinepark-overzicht',body=`In bijlage het samengestelde Machinepark-overzicht.\n\nDe PDF ${file.name} is op dit toestel opgeslagen. Voeg dit bestand als bijlage toe aan de e-mail.`;setTimeout(()=>{window.location.href=`mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;},120);});}catch(e){if(e?.name==='AbortError')return;console.error(e);alert(e.message||'E-mailen is mislukt.');}}

  function bindComposedButton(){const btn=document.getElementById('openComposedDocuments');if(btn&&!btn.dataset.composedBound){btn.dataset.composedBound='1';btn.addEventListener('click',openComposedWindow);}}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bindComposedButton,{once:true});else bindComposedButton();
  window.machineparkOpenComposedDocuments=openComposedWindow;
})();
</script>
'''
    index = index.replace("</body>", script + "</body>", 1)
    INDEX.write_text(index, encoding="utf-8")

# Netlify: alleen gebruikers met Beheer mogen de aparte documentlijst wijzigen.
permissions = NETLIFY_PERMISSIONS.read_text(encoding="utf-8")
if SERVER_MARKER not in permissions:
    anchor = "  const role = normalizeRole(roleValue, { owner, config }); const permissions = permissionsForRole(role, config, { owner });\n"
    addition = anchor + "  if (stable(before?.composedDocuments || []) !== stable(after?.composedDocuments || [])) requirePermission(permissions, 'view.settings', 'Deze rol mag geen samengestelde documenten beheren.');\n"
    permissions = replace_once(permissions, anchor, addition, "Netlify rechten samengestelde documenten")
    permissions += f"\n// {SERVER_MARKER}\n"
    NETLIFY_PERMISSIONS.write_text(permissions, encoding="utf-8")

# Netlify: oudere clients kennen composedDocuments niet; laat die nooit een bestaande lijst wissen.
data = NETLIFY_DATA.read_text(encoding="utf-8")
if SERVER_MARKER not in data:
    anchor = "      const previousData = previousEntry?.data || null;\n"
    addition = anchor + "      if (!Array.isArray(data.composedDocuments) && Array.isArray(previousData?.composedDocuments)) data.composedDocuments = previousData.composedDocuments;\n      if (!Array.isArray(data.composedDocuments)) data.composedDocuments = [];\n"
    data = replace_once(data, anchor, addition, "Netlify compatibiliteit samengestelde documenten")
    data += f"\n// {SERVER_MARKER}\n"
    NETLIFY_DATA.write_text(data, encoding="utf-8")

# Synology: dezelfde rechten en compatibiliteit op de PHP 7.2 backend.
php = SYNOLOGY_DATA.read_text(encoding="utf-8")
if SERVER_MARKER not in php:
    permission_anchor = "    $permissions = mp_role_permissions((string)($user['role'] ?? 'gebruiker'), !empty($user['isOwner']));\n"
    permission_add = permission_anchor + "    $beforeDocuments = isset($before['composedDocuments']) && is_array($before['composedDocuments']) ? $before['composedDocuments'] : [];\n    $afterDocuments = isset($after['composedDocuments']) && is_array($after['composedDocuments']) ? $after['composedDocuments'] : [];\n    if (json_encode($beforeDocuments) !== json_encode($afterDocuments)) mp_require_permission($permissions, 'view.settings', 'Deze rol mag geen samengestelde documenten beheren.');\n"
    php = replace_once(php, permission_anchor, permission_add, "Synology rechten samengestelde documenten")
    compatibility_anchor = "    if (!isset($data['actions']) || !is_array($data['actions'])) {\n        $data['actions'] = isset($before['actions']) && is_array($before['actions']) ? $before['actions'] : [];\n    }\n"
    compatibility_add = compatibility_anchor + "\n    // Oudere clients kennen samengestelde documenten nog niet. Bewaar een bestaande lijst.\n    if (!isset($data['composedDocuments']) || !is_array($data['composedDocuments'])) {\n        $data['composedDocuments'] = isset($before['composedDocuments']) && is_array($before['composedDocuments']) ? $before['composedDocuments'] : [];\n    }\n"
    php = replace_once(php, compatibility_anchor, compatibility_add, "Synology compatibiliteit samengestelde documenten")
    php += f"\n// {SERVER_MARKER}\n"
    SYNOLOGY_DATA.write_text(php, encoding="utf-8")

built = INDEX.read_text(encoding="utf-8")
for needle in [MARKER, 'id="openComposedDocuments"', 'Samengestelde documenten', 'data-composed-action="view"', 'data-composed-action="mail"', 'data-composed-action="print"', 'data-composed-action="pdf"', 'data-composed-action="delete"', 'composedDocuments']:
    if needle not in built:
        raise SystemExit(f"Buildvalidatie mislukt: samengestelde documenten ontbreken ({needle})")
for path in [NETLIFY_PERMISSIONS, NETLIFY_DATA, SYNOLOGY_DATA]:
    if SERVER_MARKER not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"Buildvalidatie mislukt: serverbescherming ontbreekt in {path.name}")

print("[Machinepark] samengestelde documenten toegevoegd aan Beheer")
