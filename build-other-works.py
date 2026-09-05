from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="other-works-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    index = index.replace(old, new, 1)


if MARKER not in index:
    # Andere werken blijft technisch in breakdowns zodat centrale/offline sync,
    # voorraad, foto's, werkbonnen en conflictbeveiliging exact dezelfde route gebruiken.
    replace_once(
        "      date, time, technician, workSessions, hours:totalMinutes / 60,\n      createdAt:existing?.createdAt || activeDraft.createdAt || now, updatedAt:now,",
        "      date, time, technician, workSessions, hours:totalMinutes / 60,\n      serviceKind:String(form?.querySelector('[name=\"serviceKind\"]')?.value || existing?.serviceKind || ''),\n      workTypeName:String(form?.querySelector('[name=\"workTypeName\"]')?.value || existing?.workTypeName || '').trim(),\n      createdAt:existing?.createdAt || activeDraft.createdAt || now, updatedAt:now,",
        'werksoort in conceptheader',
    )
    replace_once(
        "const headers = (state[info.store] || []).filter(item => isDraftHeader(item, kind)).sort((a,b) => String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')));",
        "const headers = (state[info.store] || []).filter(item => isDraftHeader(item, kind) && !(kind === 'breakdowns' && item.serviceKind === 'other')).sort((a,b) => String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')));",
        'andere-werkenconcepten uit depannageconcepten',
    )
    replace_once(
        "  function restoreDraftForm(kind, header, items) {",
        "  function restoreDraftForm(kind, header, items) {\n    if (kind === 'breakdowns' && header?.serviceKind === 'other' && typeof window.machineparkPrepareOtherWorkModal === 'function') window.machineparkPrepareOtherWorkModal(header.workTypeName || 'Plaatsing');",
        'andere-werkenconcept herstellen',
    )
    replace_once(
        "    if (!selected.length) throw new Error(`Selecteer minstens één toestel voor ${kind === 'maintenance' ? 'het onderhoud' : 'de depannage'}.`);",
        "    if (!selected.length) throw new Error(`Selecteer minstens één toestel voor ${kind === 'maintenance' ? 'het onderhoud' : (header?.serviceKind === 'other' ? 'de werkzaamheden' : 'de depannage')}.`);\n    if (kind === 'breakdowns' && header?.serviceKind === 'other' && !String(header.workTypeName || '').trim()) throw new Error('Kies of vul een naam voor Andere werken in.');",
        'werksoort verplicht bij concept afronden',
    )
    replace_once(
        "    record.batchId = batchId;\n    if (kind === 'breakdowns') record.batchSize = batchSize;",
        "    record.batchId = batchId;\n    if (kind === 'breakdowns') {\n      record.batchSize = batchSize;\n      if (header?.serviceKind === 'other') { record.serviceKind = 'other'; record.workTypeName = String(header.workTypeName || 'Plaatsing').trim() || 'Plaatsing'; }\n      else { delete record.serviceKind; delete record.workTypeName; }\n    }",
        'andere werken definitief markeren',
    )
    replace_once(
        "toast(`${selected.length} ${current.kind === 'maintenance' ? 'onderhoudsregistratie' : 'depannageregistratie'}${selected.length === 1 ? '' : 's'} opgeslagen`);",
        "toast(`${selected.length} ${current.kind === 'maintenance' ? 'onderhoudsregistratie' : (saved.header?.serviceKind === 'other' ? (saved.header.workTypeName || 'andere werkzaamheid') : 'depannageregistratie')}${selected.length === 1 ? '' : 's'} opgeslagen`);",
        'melding concept Andere werken',
    )

    replace_once(
        '<div class="event-label breakdown">Depannage</div><div class="date">${recordDateTimeFmt(b)}',
        '<div class="event-label breakdown">${b.serviceKind===\'other\'?esc(b.workTypeName||\'Andere werken\'):\'Depannage\'}</div><div class="date">${recordDateTimeFmt(b)}',
        'gekozen andere-werknaam in toesteltijdlijn',
    )
    replace_once(
        "    const title = isMaintenance ? 'Onderhoudsverslag' : 'Depannageverslag';",
        "    const title = isMaintenance ? 'Onderhoudsverslag' : (record?.serviceKind === 'other' ? `${record.workTypeName || 'Andere werken'} · verslag` : 'Depannageverslag');",
        'andere werken afdruktitel',
    )
    replace_once(
        "    const label = kind === 'maintenance' ? 'Onderhoud' : 'Depannage';",
        "    const label = kind === 'maintenance' ? 'Onderhoud' : (record?.serviceKind === 'other' ? (record.workTypeName || 'Andere werken') : 'Depannage');",
        'andere werken documenttitel',
    )

    feature = r'''
<style data-machinepark-build-fix="other-works-v1">
.other-work-type-field{grid-column:1/-1;border:1px solid #d8e2de;border-radius:12px;padding:12px;background:#f8faf9}
.other-work-type-line{display:grid;grid-template-columns:minmax(220px,1fr) minmax(220px,1fr);gap:10px;align-items:end}
.other-work-type-line .field{margin:0}.other-work-type-help{font-size:11px;color:var(--muted);margin-top:7px}
.other-work-badge{background:#f1ecfb;color:#5f4190}.work-activity-type.other-work{color:#674997}
.other-work-draft-host{margin-bottom:14px}.other-work-draft-host:empty{display:none}
#view-otherworks .table{min-width:1080px}
@media(max-width:700px){.other-work-type-line{grid-template-columns:1fr}#view-otherworks .toolbar-right{width:100%}#view-otherworks .toolbar-right .btn{width:100%}}
</style>
<script data-machinepark-build-fix="other-works-v1">
(() => {
  const isOtherWork=item=>Boolean(item&&item.serviceKind==='other'&&item.isDraft!==true);
  const isOtherDraftHeader=item=>Boolean(item?.isDraft===true&&item.draftRole==='header'&&item.draftKind==='breakdowns'&&item.serviceKind==='other');
  const isOtherDraftItem=(item,id)=>Boolean(item?.isDraft===true&&item.draftRole==='item'&&item.draftKind==='breakdowns'&&item.draftBatchId===id);
  const canView=()=>!window.machineparkAccessReady||typeof window.machineparkHasPermission!=='function'||window.machineparkHasPermission('view.breakdowns');
  const canAdd=()=>!window.machineparkAccessReady||typeof window.machineparkHasPermission!=='function'||window.machineparkHasPermission('breakdowns.add');

  function typeNames(extra=''){
    const names=['Plaatsing'];
    (state.breakdowns||[]).forEach(item=>{if((isOtherWork(item)||isOtherDraftHeader(item))&&String(item.workTypeName||'').trim())names.push(String(item.workTypeName).trim())});
    if(String(extra||'').trim())names.push(String(extra).trim());
    return [...new Set(names)].sort((a,b)=>a==='Plaatsing'?-1:b==='Plaatsing'?1:a.localeCompare(b,'nl-BE',{numeric:true,sensitivity:'base'}));
  }

  function typeFieldHtml(selected='Plaatsing'){
    const names=typeNames(selected),known=names.includes(selected),choice=known?selected:'__new__';
    return `<div class="other-work-type-field" data-other-work-type-field><input type="hidden" name="serviceKind" value="other"><input type="hidden" name="workTypeName" value="${esc(selected||'Plaatsing')}"><div class="other-work-type-line"><div class="field"><label>Soort werkzaamheden *</label><select data-other-work-type-choice required>${names.map(name=>`<option value="${esc(name)}" ${choice===name?'selected':''}>${esc(name)}</option>`).join('')}<option value="__new__" ${choice==='__new__'?'selected':''}>+ Nieuwe naam toevoegen…</option></select></div><div class="field" data-other-work-new-field style="${choice==='__new__'?'':'display:none'}"><label>Nieuwe naam *</label><input data-other-work-new-name maxlength="100" value="${choice==='__new__'?esc(selected):''}" placeholder="bv. Ombouw, Verplaatsing…"></div></div><div class="other-work-type-help">Plaatsing staat standaard klaar. Een nieuwe naam wordt na opslaan automatisch een keuze voor volgende registraties en synchroniseert mee naar andere toestellen.</div></div>`;
  }

  function syncTypeField(root){
    const choice=root?.querySelector('[data-other-work-type-choice]'),newField=root?.querySelector('[data-other-work-new-field]'),newName=root?.querySelector('[data-other-work-new-name]'),hidden=root?.querySelector('[name="workTypeName"]');
    if(!choice||!hidden)return;const custom=choice.value==='__new__';if(newField)newField.style.display=custom?'':'none';if(newName)newName.required=custom;hidden.value=custom?String(newName?.value||'').trim():String(choice.value||'').trim();
  }

  window.machineparkPrepareOtherWorkModal=function(selected='Plaatsing'){
    const form=document.getElementById('modalForm'),grid=form?.querySelector('.modal-body .form-grid');if(!form||!grid)return;
    let field=grid.querySelector('[data-other-work-type-field]');
    if(!field){const holder=document.createElement('div');holder.innerHTML=typeFieldHtml(selected);field=holder.firstElementChild;grid.insertBefore(field,grid.firstChild)}
    else{const select=field.querySelector('[data-other-work-type-choice]');if(select&&selected&&![...select.options].some(o=>o.value===selected)){const option=document.createElement('option');option.value=selected;option.textContent=selected;select.insertBefore(option,select.querySelector('option[value="__new__"]'))}if(select&&selected)select.value=selected}
    form.dataset.otherWorkMode='1';syncTypeField(field);
    const title=document.querySelector('#modal .modal-head h3');if(title)title.textContent=selected&&selected!=='Plaatsing'?`${selected} registreren`:'Andere werken registreren';
    const submit=form.querySelector('.modal-foot button[type="submit"]');if(submit&&!form.dataset.otherWorkEdit)submit.textContent='Werkzaamheden registreren';
  };
  document.addEventListener('change',e=>{if(e.target.matches?.('[data-other-work-type-choice]'))syncTypeField(e.target.closest('[data-other-work-type-field]'))});
  document.addEventListener('input',e=>{if(e.target.matches?.('[data-other-work-new-name]'))syncTypeField(e.target.closest('[data-other-work-type-field]'))});

  const basePut=put;
  put=async function(storeName,obj){const form=document.getElementById('modalForm');if(storeName==='breakdowns'&&obj&&form?.dataset.otherWorkMode==='1'){const type=String(form.querySelector('[name="workTypeName"]')?.value||'').trim();if(!type)throw new Error('Kies of vul een naam voor Andere werken in.');obj={...obj,serviceKind:'other',workTypeName:type}}return basePut(storeName,obj)};
  window.put=put;

  function withClassic(callback){const all=state.breakdowns;state.breakdowns=(all||[]).filter(item=>!isOtherWork(item));try{return callback()}finally{state.breakdowns=all}}
  const baseRenderBreakdowns=renderBreakdowns;renderBreakdowns=function(){return withClassic(()=>baseRenderBreakdowns())};window.renderBreakdowns=renderBreakdowns;
  const baseRenderDashboard=renderDashboard;renderDashboard=function(){return withClassic(()=>baseRenderDashboard())};window.renderDashboard=renderDashboard;
  const baseProfessional=renderProfessionalDashboard;renderProfessionalDashboard=function(){return withClassic(()=>baseProfessional())};window.renderProfessionalDashboard=renderProfessionalDashboard;

  const workNav=document.querySelector('.nav button[data-view="work"]'),otherNav=document.createElement('button');otherNav.type='button';otherNav.dataset.otherWorksNav='1';otherNav.innerHTML='<span class="icon">🧰</span><span class="label">Andere werken</span>';if(workNav?.parentNode)workNav.insertAdjacentElement('afterend',otherNav);
  const workView=document.getElementById('view-work'),otherView=document.createElement('section');otherView.className='view';otherView.id='view-otherworks';
  otherView.innerHTML=`<div id="otherWorkDraftPanel" class="other-work-draft-host"></div><div class="toolbar"><div class="toolbar-left"><select id="otherWorkTypeFilter" class="filter"><option value="">Alle soorten</option></select><select id="otherWorkStatusFilter" class="filter"><option value="">Alle statussen</option><option>Open</option><option>In behandeling</option><option>Opgelost</option></select><select id="otherWorkPriorityFilter" class="filter"><option value="">Alle prioriteiten</option><option>Laag</option><option>Normaal</option><option>Hoog</option><option>Kritiek</option></select></div><div class="toolbar-right"><button class="btn primary" id="addOtherWork">+ Andere werken registreren</button></div></div><div class="table-wrap"><table class="table"><thead><tr><th>Datum / uur</th><th>Type</th><th>Toestel</th><th>Werkzaamheid</th><th>Status / prioriteit</th><th>Technieker</th><th>Onderdelen</th><th>Oplossing</th><th></th></tr></thead><tbody id="otherWorkBody"></tbody></table></div>`;
  if(workView?.parentNode)workView.insertAdjacentElement('afterend',otherView);machineparkViewQueries.otherworks=machineparkViewQueries.otherworks||'';
  const kindFilter=document.getElementById('workKindFilter');if(kindFilter&&!kindFilter.querySelector('option[value="otherworks"]'))kindFilter.insertAdjacentHTML('beforeend','<option value="otherworks">Andere werken</option>');
  const workDrafts=document.getElementById('workDraftPanels');if(workDrafts&&!document.getElementById('otherWorkDraftPanelWork')){const host=document.createElement('div');host.id='otherWorkDraftPanelWork';host.className='other-work-draft-host';workDrafts.appendChild(host)}

  function partsCount(item){const total=list=>(Array.isArray(list)?list:[]).reduce((sum,p)=>sum+Math.max(0,Number(p?.qty||0)||0),0);return total(item?.usedParts)+total(item?.oneOffParts)}
  function matchesOther(item){if(!isOtherWork(item))return false;const type=document.getElementById('otherWorkTypeFilter')?.value||'',status=document.getElementById('otherWorkStatusFilter')?.value||'',priority=document.getElementById('otherWorkPriorityFilter')?.value||'';if(type&&item.workTypeName!==type||status&&item.status!==status||priority&&item.priority!==priority)return false;if(!state.query)return true;const moment=recordMoment(item);return searchDeviceIsActive(item.deviceId)&&searchIncludes([item.workTypeName,item.date,item.time,recordDateTimeFmt(item),item.issue,item.diagnosis,item.solution,item.technician,item.priority,item.status,linkedDeviceSearchText(item.deviceId,moment),linkedPartsSearchText(item.usedParts)].join(' '))}
  function otherRow(item){const moment=recordMoment(item),type=String(item.workTypeName||'Andere werken');return `<tr data-work-kind="otherworks"><td class="nowrap">${recordDateTimeFmt(item)}</td><td><span class="badge other-work-badge">${esc(type)}</span></td><td><strong>${esc(deviceName(item.deviceId,moment))}</strong></td><td><span class="work-activity-type other-work">${esc(item.issue||type)}</span></td><td><div class="work-status-stack">${statusBadge(item.priority||'Normaal')}${breakdownStatusBadge(item.status||'Open')}</div></td><td>${esc(item.technician||'—')}</td><td class="work-parts-count">${partsCount(item)}</td><td>${esc(item.solution||item.diagnosis||'—')}</td><td><button class="btn small" data-other-work-details="${esc(item.id)}">Details</button></td></tr>`}
  function fillTypeFilter(){const select=document.getElementById('otherWorkTypeFilter');if(!select)return;const current=select.value;select.innerHTML='<option value="">Alle soorten</option>'+typeNames().map(name=>`<option value="${esc(name)}">${esc(name)}</option>`).join('');if([...select.options].some(o=>o.value===current))select.value=current}
  function draftDeviceText(header){const items=(state.breakdowns||[]).filter(item=>isOtherDraftItem(item,header.id)&&item.draftSelected!==false),names=items.map(item=>{const d=state.devices.find(x=>x.id===item.deviceId);return d?.assetCode||d?.model||''}).filter(Boolean);return names.length?`${names.length} toestel${names.length===1?'':'len'} · ${names.slice(0,3).join(', ')}${names.length>3?' …':''}`:'nog geen toestel geselecteerd'}
  function draftHtml(){const headers=(state.breakdowns||[]).filter(isOtherDraftHeader).sort((a,b)=>String(b.updatedAt||'').localeCompare(String(a.updatedAt||'')));if(!headers.length)return '';return `<div class="service-draft-panel show"><div class="service-draft-head"><strong>Andere-werkenconcepten (${headers.length})</strong><span class="muted" style="font-size:11px">Automatisch lokaal bewaard en centraal gesynchroniseerd.</span></div><div class="service-draft-list">${headers.map(h=>`<div class="service-draft-row"><div><div class="service-draft-row-title"><span class="service-draft-badge">CONCEPT</span>${esc(h.workTypeName||'Andere werken')} · ${esc(h.locationLabel||'Nog geen locatie')}</div><div class="service-draft-row-meta">${esc(draftDeviceText(h))} · laatst aangepast ${h.updatedAt?esc(new Date(h.updatedAt).toLocaleString('nl-BE')):'nog niet opgeslagen'}</div></div><div class="service-draft-actions"><button type="button" class="btn small service-draft-button" data-service-draft-open="${esc(h.id)}" data-service-draft-kind="breakdowns">Verdergaan</button><button type="button" class="btn small danger" data-service-draft-delete="${esc(h.id)}" data-service-draft-kind="breakdowns">Verwijderen</button></div></div>`).join('')}</div></div>`}
  function renderDrafts(){const html=draftHtml();['otherWorkDraftPanel','otherWorkDraftPanelWork'].forEach(id=>{const host=document.getElementById(id);if(host)host.innerHTML=html})}
  function renderOtherWorks(){fillTypeFilter();renderDrafts();const body=document.getElementById('otherWorkBody');if(!body)return;const list=(state.breakdowns||[]).filter(matchesOther).sort((a,b)=>recordMoment(b).localeCompare(recordMoment(a)));body.innerHTML=list.length?list.map(otherRow).join(''):'<tr><td colspan="9"><div class="empty">Nog geen andere werken geregistreerd.</div></td></tr>'}
  window.renderOtherWorks=renderOtherWorks;

  function renderCombined(){const body=document.getElementById('workHistoryBody');if(!body)return;const kind=document.getElementById('workKindFilter')?.value||'',mt=document.getElementById('workMaintenanceTypeFilter')?.value||'',bs=document.getElementById('workBreakdownStatusFilter')?.value||'',bp=document.getElementById('workBreakdownPriorityFilter')?.value||'',canM=!window.machineparkAccessReady||window.machineparkHasPermission?.('view.maintenance'),canB=canView(),rows=[];
    if(canM&&(!kind||kind==='maintenance'))(state.maintenance||[]).forEach(item=>{if(item?.isDraft===true||mt&&item.type!==mt||typeof maintenanceMatchesQuery==='function'&&!maintenanceMatchesQuery(item))return;rows.push({kind:'maintenance',item,moment:recordMoment(item)})});
    if(canB&&(!kind||kind==='breakdowns'))(state.breakdowns||[]).forEach(item=>{if(item?.isDraft===true||isOtherWork(item)||bs&&item.status!==bs||bp&&item.priority!==bp||typeof breakdownMatchesQuery==='function'&&!breakdownMatchesQuery(item))return;rows.push({kind:'breakdowns',item,moment:recordMoment(item)})});
    if(canB&&(!kind||kind==='otherworks'))(state.breakdowns||[]).forEach(item=>{if(!isOtherWork(item)||bs&&item.status!==bs||bp&&item.priority!==bp)return;if(state.query){const moment=recordMoment(item);if(!searchDeviceIsActive(item.deviceId)||!searchIncludes([item.workTypeName,item.issue,item.diagnosis,item.solution,item.technician,item.priority,item.status,linkedDeviceSearchText(item.deviceId,moment),linkedPartsSearchText(item.usedParts)].join(' ')))return}rows.push({kind:'otherworks',item,moment:recordMoment(item)})});
    rows.sort((a,b)=>String(b.moment||'').localeCompare(String(a.moment||'')));
    body.innerHTML=rows.length?rows.map(row=>{if(row.kind==='otherworks')return otherRow(row.item);const item=row.item,moment=row.moment;if(row.kind==='maintenance')return `<tr data-work-kind="maintenance"><td class="nowrap">${recordDateTimeFmt(item)}</td><td><span class="badge blue">Onderhoud</span></td><td><strong>${esc(deviceName(item.deviceId,moment))}</strong></td><td><span class="work-activity-type maintenance">${esc(item.type||'Onderhoud')}</span></td><td>—</td><td>${esc(item.technician||'—')}</td><td class="work-parts-count">${partsCount(item)}</td><td>${esc(item.notes||'—')}</td><td><button class="btn small" data-maintenance-details="${item.id}">Details</button></td></tr>`;return `<tr data-work-kind="breakdowns"><td class="nowrap">${recordDateTimeFmt(item)}</td><td><span class="badge danger">Depannage</span></td><td><strong>${esc(deviceName(item.deviceId,moment))}</strong></td><td><span class="work-activity-type breakdown">${esc(item.issue||'Depannage')}</span></td><td><div class="work-status-stack">${statusBadge(item.priority||'Normaal')}${breakdownStatusBadge(item.status||'Open')}</div></td><td>${esc(item.technician||'—')}</td><td class="work-parts-count">${partsCount(item)}</td><td>${esc(item.solution||item.diagnosis||'—')}</td><td><button class="btn small" data-edit-breakdown="${item.id}">Details</button></td></tr>`}).join(''):'<tr><td colspan="9"><div class="empty">Nog geen werkzaamheden gevonden.</div></td></tr>';renderDrafts()}
  window.machineparkRenderCombinedWork=renderCombined;

  ['workKindFilter','workMaintenanceTypeFilter','workBreakdownStatusFilter','workBreakdownPriorityFilter'].forEach(id=>{const input=document.getElementById(id);if(input)input.onchange=renderCombined});
  const baseRenderAll=renderAll;renderAll=function(){baseRenderAll();renderOtherWorks();renderCombined()};window.renderAll=renderAll;

  const baseGlobal=renderGlobalSearchResults;renderGlobalSearchResults=function(){withClassic(()=>baseGlobal());if(state.view!=='dashboard'||!state.query||!canView())return;const box=document.getElementById('globalSearchResults');if(!box)return;const matches=(state.breakdowns||[]).filter(item=>{if(!isOtherWork(item)||!searchDeviceIsActive(item.deviceId))return false;const moment=recordMoment(item);return searchIncludes([item.workTypeName,item.issue,item.diagnosis,item.solution,item.technician,linkedDeviceSearchText(item.deviceId,moment),linkedPartsSearchText(item.usedParts)].join(' '))}).sort((a,b)=>recordMoment(b).localeCompare(recordMoment(a))).slice(0,6);if(!matches.length)return;if(box.querySelector('.global-search-empty'))box.innerHTML='';box.insertAdjacentHTML('beforeend','<div class="global-search-head">Andere werken</div>'+matches.map(item=>`<button type="button" class="global-search-result" data-global-other-work="${esc(item.id)}"><strong>🧰 ${esc(item.workTypeName||'Andere werken')} · ${esc(deviceName(item.deviceId,recordMoment(item)))}</strong><small>${esc(item.issue||'')} · ${esc(item.technician||'Geen technieker')}</small></button>`).join(''));box.classList.add('show')};window.renderGlobalSearchResults=renderGlobalSearchResults;

  function openView(){if(!canView())return switchView('dashboard');state.view='otherworks';document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));otherView.classList.add('active');document.querySelectorAll('.nav button').forEach(b=>b.classList.remove('active'));otherNav.classList.add('active');document.getElementById('pageTitle').textContent='Andere werken';document.getElementById('pageSubtitle').textContent='Plaatsingen en andere werkzaamheden met dezelfde registratievelden als een depannage.';const input=document.getElementById('globalSearch'),actions=document.querySelector('.top-actions');if(actions)actions.style.display='';state.query=machineparkViewQueries.otherworks||'';if(input){input.value=state.query;input.placeholder='Zoek in andere werken…'}closeGlobalSearch();renderAll()}
  const baseSwitch=switchView;switchView=function(view){if(view==='otherworks')return openView();otherNav.classList.remove('active');return baseSwitch(view)};window.switchView=switchView;otherNav.onclick=openView;

  function access(){const allowed=canView();otherNav.style.display=allowed?'':'none';const add=document.getElementById('addOtherWork');if(add)add.style.display=allowed&&canAdd()?'':'none';const visible=[...document.querySelectorAll('.nav button')].filter(b=>b.style.display!=='none'&&b.getAttribute('aria-hidden')!=='true').length;document.documentElement.style.setProperty('--mobile-nav-count',String(Math.max(1,visible)));if(state.view==='otherworks'&&!allowed)baseSwitch('dashboard')}
  const baseRole=window.applyMachineparkRoleAccess||applyMachineparkRoleAccess;applyMachineparkRoleAccess=function(){const was=state.view==='otherworks';if(was)state.view='breakdowns';try{baseRole()}finally{if(was&&canView())state.view='otherworks';access()}if(was&&canView()){document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));otherView.classList.add('active');document.querySelectorAll('.nav button').forEach(b=>b.classList.remove('active'));otherNav.classList.add('active')}};window.applyMachineparkRoleAccess=applyMachineparkRoleAccess;
  const baseOperational=window.applyOperationalPermissions||applyOperationalPermissions;applyOperationalPermissions=function(){baseOperational();access()};window.applyOperationalPermissions=applyOperationalPermissions;

  function prepareAfterOpen(selected='Plaatsing',editing=false){setTimeout(()=>{window.machineparkPrepareOtherWorkModal(selected);const form=document.getElementById('modalForm');if(form&&editing){form.dataset.otherWorkEdit='1';const title=document.querySelector('#modal .modal-head h3');if(title)title.textContent=`${selected||'Andere werken'} bijwerken`;const submit=form.querySelector('.modal-foot button[type="submit"]');if(submit)submit.textContent='Wijzigingen opslaan'}},0);setTimeout(()=>window.machineparkPrepareOtherWorkModal(selected),120)}
  function openOtherWork(id=''){if(id){const record=(state.breakdowns||[]).find(item=>item.id===id&&isOtherWork(item));if(!record){toast('Werkzaamheid niet gevonden');return}openBreakdown(id);prepareAfterOpen(record.workTypeName||'Plaatsing',true);return}if(!canAdd()){toast('Geen recht om andere werken toe te voegen');return}openBreakdown();prepareAfterOpen('Plaatsing',false)}window.openOtherWork=openOtherWork;
  function showDetails(id){const record=(state.breakdowns||[]).find(item=>item.id===id&&isOtherWork(item));if(!record){toast('Werkzaamheid niet gevonden');return}if(typeof window.machineparkShowBreakdownDetails==='function')window.machineparkShowBreakdownDetails(id);else openBreakdown(id);setTimeout(()=>{const title=document.querySelector('#modal .modal-head h3');if(title)title.textContent=`${record.workTypeName||'Andere werken'} details`;const edit=document.getElementById('editBreakdownFromDetails');if(edit){edit.textContent=`${record.workTypeName||'Werkzaamheid'} bewerken`;edit.onclick=()=>{closeModal();openOtherWork(id)}}},30)}window.machineparkShowOtherWorkDetails=showDetails;

  document.getElementById('addOtherWork').onclick=()=>openOtherWork();['otherWorkTypeFilter','otherWorkStatusFilter','otherWorkPriorityFilter'].forEach(id=>{const input=document.getElementById(id);if(input)input.onchange=renderOtherWorks});
  document.addEventListener('click',e=>{const detail=e.target.closest?.('[data-other-work-details]');if(detail){showDetails(detail.dataset.otherWorkDetails);return}const global=e.target.closest?.('[data-global-other-work]');if(global){closeGlobalSearch();showDetails(global.dataset.globalOtherWork)}});
  access();renderOtherWorks();renderCombined();
})();
</script>
'''
    pos=index.rfind('</body>')
    if pos<0: raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor Andere werken')
    index=index[:pos]+feature+'\n'+index[pos:]
    index_path.write_text(index,encoding='utf-8')

built=index_path.read_text(encoding='utf-8')
required=[MARKER,"serviceKind === 'other'",'workTypeName','Andere werken registreren','Plaatsing','Nieuwe naam toevoegen',"otherView.id='view-otherworks'",'data-other-work-details','function typeNames',"header?.serviceKind === 'other'","record.serviceKind = 'other'",'machineparkPrepareOtherWorkModal',"workTypeName||'Andere werken'",'window.machineparkRenderCombinedWork=renderCombined']
for needle in required:
    if needle not in built: raise SystemExit(f'Buildvalidatie mislukt: Andere werken ontbreekt ({needle})')
print('[Machinepark] Andere werken gebruikt depannagevelden, leerbare werktypes, concepten en gezamenlijke historiek')
