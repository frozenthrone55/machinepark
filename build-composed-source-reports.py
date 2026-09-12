from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
FEATURE_MARKER = 'data-machinepark-build-fix="composed-history-device-photos-v1"'
MARKER = 'data-machinepark-build-fix="composed-source-reports-v1"'

index = INDEX.read_text(encoding='utf-8')
if FEATURE_MARKER not in index:
    raise SystemExit('Buildvalidatie mislukt: toestel-fotokoppeling ontbreekt voor verslagtabel')

if MARKER not in index:
    style = r'''
<style data-machinepark-build-fix="composed-source-reports-v1">
.composed-source-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px;align-items:start;margin-top:6px}
.composed-source-panel{min-width:0;border:1px solid var(--line);border-radius:14px;background:#fbfcfb;padding:11px}
.composed-source-panel-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:0 0 9px;min-height:24px}
.composed-source-panel-head h4{margin:0;font-size:13px}.composed-source-panel-head span{font-size:11px;color:var(--muted);font-weight:700}
.composed-source-panel .composed-toolbar{margin-bottom:9px}.composed-source-panel .composed-toolbar-left{width:100%}
.composed-report-list-wrap{max-height:min(52vh,520px);overflow:auto;overscroll-behavior:contain}
.composed-report-list-wrap .table th{top:0;z-index:1}.composed-report-table{min-width:720px}.composed-report-table input[type="checkbox"]{width:17px;height:17px}
.composed-report-location strong{display:block}.composed-report-location small{display:block;color:var(--muted);margin-top:2px}
.composed-save-row{display:flex;justify-content:flex-end;margin-top:12px}
@media(max-width:1050px){.composed-source-grid{grid-template-columns:1fr}.composed-report-list-wrap,.composed-device-list-wrap{max-height:46vh}}
</style>
'''
    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-head ontbreekt voor verslagtabel')
    index = index.replace('</head>', style + '</head>', 1)

    anchor = '  function openComposedPreview(doc)'
    if index.count(anchor) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x preview-anker voor verslagtabel, gevonden {index.count(anchor)}x')

    script = r'''
  let selectedComposedReports=new Set();

  function composedSourceMoment(record){
    const date=record?.serviceReportDate||record?.serviceVisitDate||record?.date||'';
    const time=record?.serviceReportTime||record?.serviceVisitTime||record?.time||'';
    if(/^\d{4}-\d{2}-\d{2}$/.test(String(date)))return `${date}T${/^\d{2}:\d{2}/.test(String(time))?time:'00:00:00'}`;
    return String(record?.serviceReportClosedAt||record?.serviceVisitClosedAt||record?.updatedAt||record?.createdAt||date||'');
  }
  function composedSourceDevice(record){return (state.devices||[]).find(device=>device.id===record?.deviceId)||null;}
  function composedSourceLocation(record){
    const device=composedSourceDevice(record),moment=composedSourceMoment(record);
    return String(record?.serviceVisitLocation||record?.location||composedLocation(device,moment)||device?.location||'Locatie onbekend').trim()||'Locatie onbekend';
  }
  function composedSourceDeviceLabel(record){
    const device=composedSourceDevice(record);return [device?.assetCode,device?.brand,device?.model].filter(Boolean).join(' · ')||'Onbekend toestel';
  }
  function composedSourceReportRows(){
    const result=[],services=new Map();
    const source=[
      ...(state.maintenance||[]).filter(item=>item?.isDraft!==true).map(item=>({store:'maintenance',kind:'Onderhoud',item})),
      ...(state.breakdowns||[]).filter(item=>item?.isDraft!==true).map(item=>({store:'breakdowns',kind:item?.serviceKind==='other'?'Andere werken':'Depannage',item})),
    ];
    source.forEach(row=>{
      const record=row.item||{},location=composedSourceLocation(record),moment=composedSourceMoment(record),visitId=String(record.serviceVisitId||''),reportId=String(record.serviceReportId||'');
      if(visitId||reportId){
        const key=visitId?`service:${visitId}`:`service:${reportId}:${composedKey(location)}`;
        if(!services.has(key))services.set(key,{key,kind:'Serviceverslag',location,moment,rows:[],devices:new Set(),technicians:new Set()});
        const entry=services.get(key);entry.rows.push(row);entry.devices.add(composedSourceDeviceLabel(record));
        const tech=String(record.serviceReportTechnician||record.serviceVisitTechnician||record.technician||'').trim();if(tech)entry.technicians.add(tech);
        if(String(moment)>String(entry.moment||''))entry.moment=moment;
        return;
      }
      if(row.kind==='Andere werken')return;
      const id=String(record.id||`${record.deviceId||'device'}:${moment}`),tech=String(record.technician||'').trim();
      result.push({key:`${row.store}:${id}`,kind:row.kind,location,moment,rows:[row],devices:new Set([composedSourceDeviceLabel(record)]),technicians:new Set(tech?[tech]:[])});
    });
    services.forEach(entry=>result.push(entry));
    return result.sort((a,b)=>String(a.location||'').localeCompare(String(b.location||''),'nl',{numeric:true,sensitivity:'base'})||String(b.moment||'').localeCompare(String(a.moment||''))||String(a.kind||'').localeCompare(String(b.kind||''),'nl'));
  }
  function composedFilteredSourceReports(){
    const search=document.getElementById('composedDeviceSearch');
    composedDeviceQuery=String(search?.value??composedDeviceQuery??'');
    const q=composedKey(composedDeviceQuery);
    return composedSourceReportRows().filter(entry=>{
      if(!q)return true;
      const records=entry.rows.map(row=>row.item||{}),searchText=[entry.kind,entry.location,composedDate(entry.moment),...[...entry.devices],...[...entry.technicians],...records.flatMap(record=>{
        const device=composedSourceDevice(record);return [record.issue,record.diagnosis,record.solution,record.work,record.notes,device?.assetCode,device?.brand,device?.model,device?.serial];
      })].filter(Boolean).join(' ');
      return composedKey(searchText).includes(q);
    });
  }
  function updateComposedReportSelectedCount(){
    const el=document.getElementById('composedReportSelectedCount');if(el)el.textContent=`${selectedComposedReports.size} geselecteerd`;
  }
  function renderComposedReportTable(){
    const body=document.getElementById('composedReportBody');if(!body)return;
    const rows=composedFilteredSourceReports();
    body.innerHTML=rows.length?rows.map(entry=>{
      const devices=[...entry.devices].join(', ')||'—',tech=[...entry.technicians].join(', ')||'—';
      return `<tr><td><input type="checkbox" data-composed-report="${composedEsc(entry.key)}" ${selectedComposedReports.has(entry.key)?'checked':''}></td><td class="composed-report-location"><strong>${composedEsc(entry.location)}</strong><small>${composedEsc(devices)}</small></td><td>${composedEsc(composedDate(entry.moment))}</td><td><span class="badge">${composedEsc(entry.kind)}</span></td><td>${composedEsc(tech)}</td></tr>`;
    }).join(''):'<tr><td colspan="5"><div class="composed-empty">Geen verslagen gevonden voor deze zoekopdracht.</div></td></tr>';
    updateComposedReportSelectedCount();
  }
  function ensureComposedSourceReportUi(){
    const body=document.querySelector('#composedDocumentsWindow .composed-section .composed-section-body');
    if(!body||document.getElementById('composedReportBody'))return;
    const deviceWrap=body.querySelector('.composed-device-list-wrap'),toolbar=body.querySelector('.composed-toolbar'),toolbarLeft=toolbar?.querySelector('.composed-toolbar-left'),toolbarRight=toolbar?.querySelector('.composed-toolbar-right');
    if(!deviceWrap||!toolbar||!toolbarLeft)return;
    const grid=document.createElement('div');grid.className='composed-source-grid';
    const left=document.createElement('div');left.className='composed-source-panel composed-source-devices';
    left.innerHTML='<div class="composed-source-panel-head"><h4>Toestellen</h4><span>Volledig toesteldossier</span></div>';
    const leftToolbar=document.createElement('div');leftToolbar.className='composed-toolbar';leftToolbar.appendChild(toolbarLeft);left.append(leftToolbar,deviceWrap);
    const right=document.createElement('div');right.className='composed-source-panel composed-source-reports';
    right.innerHTML='<div class="composed-source-panel-head"><h4>Depannages, onderhouden en serviceverslagen</h4><span id="composedReportSelectedCount">0 geselecteerd</span></div><div class="composed-toolbar"><div class="composed-toolbar-left"><button class="btn small" id="composedSelectVisibleReports" type="button">Alles zichtbaar aanvinken</button><button class="btn small" id="composedClearReportSelection" type="button">Selectie wissen</button></div></div><div class="table-wrap composed-report-list-wrap"><table class="table composed-report-table"><thead><tr><th></th><th>Locatie / toestel</th><th>Datum</th><th>Type</th><th>Technieker</th></tr></thead><tbody id="composedReportBody"></tbody></table></div>';
    grid.append(left,right);body.insertBefore(grid,toolbar);
    toolbar.classList.add('composed-save-row');if(toolbarRight&&!toolbar.contains(toolbarRight))toolbar.appendChild(toolbarRight);
    document.getElementById('composedSelectVisibleReports').onclick=()=>{composedFilteredSourceReports().forEach(entry=>selectedComposedReports.add(entry.key));renderComposedReportTable();};
    document.getElementById('composedClearReportSelection').onclick=()=>{selectedComposedReports.clear();renderComposedReportTable();};
    document.getElementById('composedReportBody').addEventListener('change',event=>{const cb=event.target.closest('[data-composed-report]');if(!cb)return;if(cb.checked)selectedComposedReports.add(cb.dataset.composedReport);else selectedComposedReports.delete(cb.dataset.composedReport);updateComposedReportSelectedCount();});
    renderComposedReportTable();
  }

  const composedBaseEnsureUi=ensureComposedUi;
  ensureComposedUi=function(){composedBaseEnsureUi();ensureComposedSourceReportUi();};
  const composedBaseRenderDevices=renderComposedDevices;
  renderComposedDevices=function(){composedBaseRenderDevices();renderComposedReportTable();};

  const composedBaseSnapshot=composedSnapshot;
  composedSnapshot=function(deviceIds,reportKeys=[...selectedComposedReports]){
    const fullDeviceIds=new Set(deviceIds||[]),keys=new Set(reportKeys||[]);
    if(!keys.size)return composedBaseSnapshot([...fullDeviceIds]);
    const selectedRows=composedSourceReportRows().filter(entry=>keys.has(entry.key)).flatMap(entry=>entry.rows);
    const selectedMaintenance=new Set(selectedRows.filter(row=>row.store==='maintenance').map(row=>row.item));
    const selectedBreakdowns=new Set(selectedRows.filter(row=>row.store==='breakdowns').map(row=>row.item));
    const deviceSet=new Set(fullDeviceIds);selectedRows.forEach(row=>{if(row.item?.deviceId)deviceSet.add(row.item.deviceId);});
    const devices=(state.devices||[]).filter(device=>deviceSet.has(device.id)).map(composedClone);
    const maintenance=(state.maintenance||[]).filter(record=>record?.isDraft!==true&&(fullDeviceIds.has(record.deviceId)||selectedMaintenance.has(record))).map(composedClone);
    const breakdowns=(state.breakdowns||[]).filter(record=>record?.isDraft!==true&&(fullDeviceIds.has(record.deviceId)||selectedBreakdowns.has(record))).map(composedClone);
    const partIds=usedPartIds([...maintenance,...breakdowns]);
    const parts=(state.parts||[]).filter(part=>partIds.has(part.id)).map(composedClone);
    return {devices,maintenance,breakdowns,parts,capturedAt:new Date().toISOString()};
  };

  saveComposedDocument=async function(){
    if(!selectedComposedDevices.size&&!selectedComposedReports.size){alert('Vink minstens één toestel of verslag aan.');return;}
    const snapshot=composedSnapshot([...selectedComposedDevices],[...selectedComposedReports]);
    const nameInput=document.getElementById('composedDocumentName');let name=String(nameInput?.value||'').trim();
    if(!name){const locations=[...new Set((snapshot.devices||[]).map(device=>composedLocation(device)).filter(Boolean))];name=locations.length===1?`${locations[0]} · samengesteld overzicht`:`Samengesteld overzicht · ${new Date().toLocaleDateString('nl-BE')}`;if(nameInput)nameInput.value=name;}
    const now=new Date().toISOString(),entry={id:`cmp_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,8)}`,name,createdAt:now,updatedAt:now,createdBy:composedCurrentUser(),deviceIds:(snapshot.devices||[]).map(device=>device.id),reportKeys:[...selectedComposedReports],snapshot};
    const next=[entry,...composedList()];await persistComposedList(next);selectedComposedDevices.clear();selectedComposedReports.clear();renderComposedDevices();renderComposedReportTable();composedNotify('Samengesteld document opgeslagen');
  };
'''
    index = index.replace(anchor, script + '\n' + anchor, 1)
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
required = [
    MARKER,
    'composed-source-grid',
    'Depannages, onderhouden en serviceverslagen',
    'id="composedSelectVisibleReports"',
    'Alles zichtbaar aanvinken',
    'id="composedClearReportSelection"',
    'Selectie wissen',
    'id="composedReportBody"',
    'data-composed-report',
    'renderComposedReportTable()',
    "const search=document.getElementById('composedDeviceSearch')",
    'selectedComposedReports',
    "alert('Vink minstens één toestel of verslag aan.')",
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: verslagtabel-token ontbreekt: {needle}')

print('[Machinepark] toestellen en selecteerbare verslagen staan naast elkaar en delen hetzelfde zoekvak')
