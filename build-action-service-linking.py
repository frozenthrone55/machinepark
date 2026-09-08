from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SERVICE = ROOT / "service-visits.js"
MARKER = 'data-machinepark-action-service-linking="v1"'

index = INDEX.read_text(encoding="utf-8")
service = SERVICE.read_text(encoding="utf-8")

if MARKER not in index:
    style_anchor = "</head>"
    style = r"""
<style data-machinepark-action-service-linking="v1">
.action-badge.inprogress{background:#dceaf5;color:#245d80}
.service-linked-actions{margin:14px 0 4px;border:1px solid #dbe5e1;border-radius:12px;background:#f8faf9;padding:11px}
.service-linked-actions-head{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:8px}
.service-linked-actions-list{display:grid;gap:6px}
.service-linked-action-row{display:flex;justify-content:space-between;align-items:center;gap:10px;border-top:1px solid #e4ebe7;padding-top:7px}
.service-linked-action-row:first-child{border-top:0;padding-top:0}
.service-linked-action-main{min-width:0}
.service-linked-action-main strong{display:block;overflow-wrap:anywhere}
.service-linked-action-meta{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}
.service-action-link-picker{display:grid;gap:10px}
.service-action-link-picker select{width:100%;border:1px solid var(--line);border-radius:9px;padding:10px;background:#fff}
.service-draft-action-picker-backdrop{position:fixed;inset:0;z-index:5000;background:rgba(20,35,31,.36);display:flex;align-items:center;justify-content:center;padding:18px}
.service-draft-action-picker-panel{width:min(680px,100%);max-height:min(78vh,760px);overflow:auto;background:#fff;border-radius:16px;border:1px solid #dbe5e1;box-shadow:0 18px 55px rgba(16,35,29,.22);padding:16px}
.service-draft-action-picker-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:12px}
.service-draft-action-picker-list{display:grid;gap:8px;margin:12px 0}
.service-draft-action-choice{display:grid;grid-template-columns:auto 1fr;gap:10px;align-items:start;border:1px solid #dbe5e1;border-radius:12px;padding:10px;background:#f8faf9}
.service-draft-action-choice input{margin-top:4px}
.service-draft-action-choice strong{display:block}
.service-draft-action-choice small{display:block;margin-top:3px;color:var(--muted)}
.service-draft-action-picker-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-top:14px}
@media(max-width:700px){.service-linked-action-row{align-items:flex-start;flex-direction:column}.service-linked-action-row .action-card-actions{width:100%}}
</style>
"""
    if style_anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: </head> ontbreekt voor actie/servicekoppeling")
    index = index.replace(style_anchor, style + style_anchor, 1)

    helper_anchor = "  function actionPriorityLabel(value) { return ({urgent:'Dringend',normal:'Normaal',low:'Laag'})[value]||'Normaal'; }"
    helper_new = helper_anchor + """
  function actionStatusLabel(value) { return value==='in_progress'?'In behandeling':value==='done'?'Uitgevoerd':'Nog te doen'; }
  function actionStatusBadge(value) {
    if(value==='in_progress')return '<span class="action-badge inprogress">In behandeling</span>';
    if(value==='done')return '<span class="action-badge done">✓ Uitgevoerd</span>';
    return '<span class="action-badge">Nog te doen</span>';
  }
"""
    if helper_anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: actiestatus-anker ontbreekt")
    index = index.replace(helper_anchor, helper_new, 1)

    badge_anchor = """      `<span class="action-badge ${priority==='urgent'?'urgent':''}">${esc(actionPriorityLabel(priority))}</span>`,
      due==='late'?'<span class="action-badge late">Te laat</span>':due==='today'?'<span class="action-badge today">Vandaag</span>':'',
      done?'<span class="action-badge done">✓ Uitgevoerd</span>':''"""
    badge_new = """      `<span class="action-badge ${priority==='urgent'?'urgent':''}">${esc(actionPriorityLabel(priority))}</span>`,
      !done&&item.status==='in_progress'?'<span class="action-badge inprogress">In behandeling</span>':'',
      due==='late'?'<span class="action-badge late">Te laat</span>':due==='today'?'<span class="action-badge today">Vandaag</span>':'',
      done?'<span class="action-badge done">✓ Uitgevoerd</span>':''"""
    if badge_anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: actiebadge-anker ontbreekt")
    index = index.replace(badge_anchor, badge_new, 1)

    delete_anchor = "  async function deleteAction(id) {"
    status_fn = r"""
  async function setActionWorkStatus(id,status) {
    const item=(state.actions||[]).find(a=>a.id===id);if(!item||item.status==='done')return;
    const next=status==='in_progress'?'in_progress':'open';
    if((item.status||'open')===next)return;
    const label=next==='in_progress'?'In behandeling':'Nog te doen';
    const updated={...item,status:next,updatedAt:new Date().toISOString(),history:appendActionHistory(item,historyEntry('status','Status gewijzigd',label))};
    await put('actions',updated);closeModal();await refresh();toast(`Actie staat op ${label.toLowerCase()}`);
  }

"""
    if delete_anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: deleteAction-anker ontbreekt")
    index = index.replace(delete_anchor, status_fn + delete_anchor, 1)

    details_badge_old = """<span class="action-badge ${item.priority==='urgent'?'urgent':''}">${esc(actionPriorityLabel(item.priority))}</span>${item.status==='done'?'<span class="action-badge done">✓ Uitgevoerd</span>':''}"""
    details_badge_new = """<span class="action-badge ${item.priority==='urgent'?'urgent':''}">${esc(actionPriorityLabel(item.priority))}</span>${actionStatusBadge(item.status)}"""
    if details_badge_old not in index:
        raise SystemExit("Buildvalidatie mislukt: actie-detailsstatus ontbreekt")
    index = index.replace(details_badge_old, details_badge_new, 1)

    footer_old = """if(item.status==='done'){const reopen=document.createElement('button');reopen.type='button';reopen.className='btn';reopen.textContent='Heropenen';reopen.onclick=()=>{closeModal();void reopenAction(item.id);};foot.insertBefore(reopen,submit);}else{const complete=document.createElement('button');complete.type='button';complete.className='btn primary';complete.textContent='✓ Afronden';complete.onclick=()=>{closeModal();void openCompleteAction(item.id);};submit.classList.remove('primary');foot.appendChild(complete);}"""
    footer_new = """if(item.status==='done'){const reopen=document.createElement('button');reopen.type='button';reopen.className='btn';reopen.textContent='Heropenen';reopen.onclick=()=>{closeModal();void reopenAction(item.id);};foot.insertBefore(reopen,submit);}else{const progress=document.createElement('button');progress.type='button';progress.className='btn';progress.textContent=item.status==='in_progress'?'↩ Nog te doen':'▶ In behandeling';progress.onclick=()=>void setActionWorkStatus(item.id,item.status==='in_progress'?'open':'in_progress');foot.insertBefore(progress,submit);const complete=document.createElement('button');complete.type='button';complete.className='btn primary';complete.textContent='✓ Afronden';complete.onclick=()=>{closeModal();void openCompleteAction(item.id);};submit.classList.remove('primary');foot.appendChild(complete);}"""
    if footer_old not in index:
        raise SystemExit("Buildvalidatie mislukt: actie-detailfooter ontbreekt")
    index = index.replace(footer_old, footer_new, 1)

    decorator_start = index.find("  window.machineparkDecorateServiceReportActions=function(report,foot){")
    decorator_end = index.find("\n  document.addEventListener('click',e=>{", decorator_start)
    if decorator_start < 0 or decorator_end < 0:
        raise SystemExit("Buildvalidatie mislukt: service-actiedecorator ontbreekt")

    enhanced = r"""
  function actionServiceIds(item) {
    const ids=Array.isArray(item?.serviceReportIds)?item.serviceReportIds.filter(Boolean).map(String):[];
    if(item?.sourceKind==='service-report'&&item?.sourceId)ids.push(String(item.sourceId));
    return [...new Set(ids)];
  }
  function linkedActionsForService(reportId) {
    const id=String(reportId||'');
    return (state.actions||[]).filter(a=>actionServiceIds(a).includes(id));
  }
  function serviceActionReportLabel(report) {
    const date=report?.date?dateFmt(report.date):'',location=report?.visits?.[0]?.location||'';
    return [date,location].filter(Boolean).join(' · ');
  }
  window.machineparkServiceReportStatus=function(report) {
    const linked=linkedActionsForService(report?.id);
    if(linked.some(a=>a.status==='in_progress'))return 'In behandeling';
    if(linked.some(a=>a.status!=='done'))return 'Open';
    return 'Afgesloten';
  };


  window.machineparkLinkedActionIdsForService=function(reportId){
    return linkedActionsForService(reportId).map(a=>String(a.id||'')).filter(Boolean);
  };

  function serviceDraftContextLabel(ctx){
    const date=ctx&&ctx.date?dateFmt(ctx.date):'';
    const locations=Array.isArray(ctx&&ctx.locations)?ctx.locations.filter(Boolean):[];
    return [date,...locations].filter(Boolean).join(' · ');
  }

  async function applyServiceDraftActionLinks(ctx,ids,finalized=false){
    const reportId=String(ctx&&ctx.reportId||'');
    if(!reportId)throw new Error('Serviceconcept heeft nog geen koppeling-id.');
    const desired=new Set((Array.isArray(ids)?ids:[]).map(String).filter(Boolean));
    const currentLinked=new Set(linkedActionsForService(reportId).map(a=>String(a.id)));
    const relevant=(state.actions||[]).filter(a=>desired.has(String(a.id))||currentLinked.has(String(a.id)));
    const contextLabel=serviceDraftContextLabel(ctx);
    const linkLabel=(finalized?'Serviceverslag ':'Serviceconcept ')+(contextLabel||reportId);
    let changed=false;
    for(const item of relevant){
      const id=String(item.id||''),was=currentLinked.has(id),want=desired.has(id);
      let serviceIds=actionServiceIds(item),links=Array.isArray(item.serviceLinks)?item.serviceLinks.filter(x=>String(x&&x.id||'')!==reportId):[];
      if(want){
        if(!serviceIds.includes(reportId))serviceIds.push(reportId);
        links.push({id:reportId,label:linkLabel});
      }else{
        serviceIds=serviceIds.filter(x=>String(x)!==reportId);
      }
      const oldLink=(Array.isArray(item.serviceLinks)?item.serviceLinks:[]).find(x=>String(x&&x.id||'')===reportId);
      const labelChanged=Boolean(want&&oldLink&&String(oldLink.label||'')!==linkLabel);
      if(was===want&&!labelChanged)continue;
      let updated={...item,serviceReportIds:[...new Set(serviceIds.map(String))],serviceLinks:links,updatedAt:new Date().toISOString()};
      if(want&&!was)updated.history=appendActionHistory(item,historyEntry('linked',finalized?'Gekoppeld aan serviceverslag':'Gekoppeld aan serviceconcept',contextLabel));
      if(!want&&was)updated.history=appendActionHistory(item,historyEntry('unlinked',finalized?'Losgekoppeld van serviceverslag':'Losgekoppeld van serviceconcept',contextLabel));
      if(!want&&item.sourceKind==='service-report'&&String(item.sourceId||'')===reportId)updated={...updated,sourceKind:'',sourceId:'',sourceLabel:''};
      await put('actions',updated);changed=true;
    }
    if(changed){
      state.actions=await getAll('actions');
      renderActions();
      renderActionDashboard();
      if(typeof window.renderMachineparkServiceVisits==='function')window.renderMachineparkServiceVisits();
    }
    return [...desired];
  }

  function closeServiceDraftActionPicker(){
    document.querySelector('.service-draft-action-picker-backdrop')?.remove();
  }

  window.machineparkOpenServiceDraftActionPicker=function(ctx){
    closeServiceDraftActionPicker();
    const linked=new Set((Array.isArray(ctx&&ctx.linkedActionIds)?ctx.linkedActionIds:[]).map(String));
    const deviceIds=new Set((Array.isArray(ctx&&ctx.deviceIds)?ctx.deviceIds:[]).map(String));
    const candidates=(state.actions||[]).filter(a=>a.status!=='done'||linked.has(String(a.id))).sort((a,b)=>{
      const am=deviceIds.has(String(a.deviceId||''))?0:1,bm=deviceIds.has(String(b.deviceId||''))?0:1;
      return am-bm||actionOpenSort(a,b);
    });
    if(!candidates.length){toast('Er zijn geen openstaande acties om te koppelen.');return;}
    const backdrop=document.createElement('div');backdrop.className='service-draft-action-picker-backdrop';
    const panel=document.createElement('section');panel.className='service-draft-action-picker-panel';
    const head=document.createElement('div');head.className='service-draft-action-picker-head';
    const title=document.createElement('div');title.innerHTML='<strong>Acties koppelen</strong><div class="muted" style="margin-top:4px">Kies één of meer acties voor dit serviceverslag.</div>';
    const close=document.createElement('button');close.type='button';close.className='btn small';close.textContent='×';close.onclick=closeServiceDraftActionPicker;
    head.append(title,close);panel.appendChild(head);
    const list=document.createElement('div');list.className='service-draft-action-picker-list';
    for(const action of candidates){
      const row=document.createElement('label');row.className='service-draft-action-choice';
      const check=document.createElement('input');check.type='checkbox';check.value=String(action.id||'');check.checked=linked.has(String(action.id||''));
      const main=document.createElement('div'),name=document.createElement('strong'),meta=document.createElement('small');
      name.textContent=String(action.title||'Actie');
      const parts=[actionStatusLabel(action.status),actionDeviceLabel(action),action.assigneeName?('Toegewezen aan '+action.assigneeName):''].filter(Boolean);
      meta.textContent=parts.join(' · ');
      main.append(name,meta);row.append(check,main);list.appendChild(row);
    }
    panel.appendChild(list);
    const actions=document.createElement('div');actions.className='service-draft-action-picker-actions';
    const cancel=document.createElement('button');cancel.type='button';cancel.className='btn';cancel.textContent='Annuleren';cancel.onclick=closeServiceDraftActionPicker;
    const save=document.createElement('button');save.type='button';save.className='btn primary';save.textContent='Koppeling bewaren';
    save.onclick=async()=>{
      save.disabled=true;
      try{
        const ids=[...list.querySelectorAll('input[type="checkbox"]:checked')].map(x=>x.value).filter(Boolean);
        await applyServiceDraftActionLinks(ctx,ids,false);
        if(typeof ctx.onChange==='function')await ctx.onChange(ids);
        closeServiceDraftActionPicker();toast(ids.length?'Actie gekoppeld aan serviceconcept':'Actiekoppeling verwijderd');
      }catch(error){alert(error&&error.message||'Actie koppelen mislukt.');}
      finally{if(document.body.contains(save))save.disabled=false;}
    };
    actions.append(cancel,save);panel.appendChild(actions);backdrop.appendChild(panel);
    backdrop.addEventListener('click',event=>{if(event.target===backdrop)closeServiceDraftActionPicker();});
    document.body.appendChild(backdrop);
  };

  window.machineparkFinalizeServiceDraftActions=async function(ctx){
    try{await applyServiceDraftActionLinks(ctx,ctx&&ctx.linkedActionIds||[],true);}
    catch(error){console.warn('Actiekoppeling serviceconcept finaliseren',error);toast('Serviceverslag opgeslagen, maar de actiekoppeling kon niet bijgewerkt worden.');}
  };

  window.machineparkClearServiceDraftActionLinks=async function(reportId){
    try{await applyServiceDraftActionLinks({reportId:reportId,locations:[],date:''},[],false);}
    catch(error){console.warn('Actiekoppeling verwijderd serviceconcept opruimen',error);}
  };

  async function linkExistingActionToService(report) {
    const linkedIds=new Set(linkedActionsForService(report.id).map(a=>a.id));
    const deviceIds=new Set((report?.records||[]).map(row=>row?.item?.deviceId||row?.deviceId).filter(Boolean));
    const candidates=(state.actions||[]).filter(a=>a.status!=='done'&&!linkedIds.has(a.id)).sort((a,b)=>{
      const am=deviceIds.has(a.deviceId)?0:1,bm=deviceIds.has(b.deviceId)?0:1;
      return am-bm||actionOpenSort(a,b);
    });
    if(!candidates.length){toast('Er zijn geen open of in behandeling zijnde acties om te koppelen.');return;}
    const options=candidates.map(a=>`<option value="${esc(a.id)}">${esc(actionStatusLabel(a.status))} · ${esc(a.title)}${actionDeviceLabel(a)?' · '+esc(actionDeviceLabel(a)):''}</option>`).join('');
    const body=`<div class="service-action-link-picker"><div class="alert"><strong>Bestaande actie koppelen</strong>Kies een actie met status Nog te doen of In behandeling. De actiestatus blijft behouden.</div><label>Actie</label><select name="actionId">${options}</select></div>`;
    closeModal();
    setTimeout(()=>showModal('Actie koppelen aan serviceverslag',body,'Koppelen',async fd=>{
      const actionId=val(fd,'actionId'),item=(state.actions||[]).find(a=>a.id===actionId);if(!item)throw new Error('Actie niet gevonden.');
      const label=serviceActionReportLabel(report),ids=[...new Set([...actionServiceIds(item),String(report.id)])],links=Array.isArray(item.serviceLinks)?item.serviceLinks.filter(x=>x&&String(x.id)!==String(report.id)):[];
      links.push({id:String(report.id),label:`Serviceverslag ${label}`});
      const updated={...item,serviceReportIds:ids,serviceLinks:links,updatedAt:new Date().toISOString(),history:appendActionHistory(item,historyEntry('linked','Gekoppeld aan serviceverslag',label))};
      await put('actions',updated);closeModal();await refresh();toast('Actie gekoppeld aan serviceverslag');setTimeout(()=>window.showMachineparkServiceVisit?.(report.id),0);
    }),0);
  }

  async function unlinkActionFromService(actionId,report) {
    const item=(state.actions||[]).find(a=>a.id===actionId);if(!item)return;
    if(!confirm(`Actie “${item.title||'Actie'}” loskoppelen van dit serviceverslag?`))return;
    const ids=actionServiceIds(item).filter(id=>String(id)!==String(report.id)),links=(Array.isArray(item.serviceLinks)?item.serviceLinks:[]).filter(x=>String(x?.id||'')!==String(report.id));
    let updated={...item,serviceReportIds:ids,serviceLinks:links,updatedAt:new Date().toISOString(),history:appendActionHistory(item,historyEntry('unlinked','Losgekoppeld van serviceverslag',serviceActionReportLabel(report)))};
    if(item.sourceKind==='service-report'&&String(item.sourceId||'')===String(report.id))updated={...updated,sourceKind:'',sourceId:'',sourceLabel:''};
    await put('actions',updated);await refresh();toast('Actie losgekoppeld');closeModal();setTimeout(()=>window.showMachineparkServiceVisit?.(report.id),0);
  }

  function renderLinkedServiceActions(report) {
    const body=document.querySelector('#modal .modal-body');if(!body)return;
    body.querySelector('.service-linked-actions')?.remove();
    const linked=linkedActionsForService(report.id).sort((a,b)=>a.status==='done'&&b.status!=='done'?1:a.status!=='done'&&b.status==='done'?-1:actionOpenSort(a,b));
    const box=document.createElement('section');box.className='service-linked-actions';
    box.innerHTML=`<div class="service-linked-actions-head"><strong>Gekoppelde acties (${linked.length})</strong><span class="action-badge">Service-status: ${esc(window.machineparkServiceReportStatus(report))}</span></div><div class="service-linked-actions-list">${linked.length?linked.map(a=>`<div class="service-linked-action-row"><div class="service-linked-action-main"><strong>${esc(a.title)}</strong><div class="service-linked-action-meta">${actionStatusBadge(a.status)}${a.assigneeName?`<span class="action-badge">${esc(a.assigneeName)}</span>`:''}</div></div><div class="action-card-actions"><button type="button" class="btn small" data-service-action-open="${esc(a.id)}">Bekijken</button><button type="button" class="btn small" data-service-action-unlink="${esc(a.id)}">Ontkoppelen</button></div></div>`).join(''):'<div class="muted">Nog geen actie gekoppeld.</div>'}</div>`;
    body.appendChild(box);
  }

  window.machineparkDecorateServiceReportActions=function(report,foot){
    if(!foot)return;
    renderLinkedServiceActions(report);
    if(foot.querySelector('[data-create-service-action]'))return;
    const deviceIds=[...new Set((report?.records||[]).map(row=>row?.item?.deviceId||row?.deviceId).filter(Boolean))],deviceId=deviceIds.length===1?deviceIds[0]:'',location=report?.visits?.[0]?.location||'',label=serviceActionReportLabel(report);
    const link=document.createElement('button');link.type='button';link.className='btn';link.dataset.linkExistingServiceAction='1';link.textContent='Bestaande actie koppelen';link.onclick=()=>void linkExistingActionToService(report);foot.insertBefore(link,foot.firstChild);
    const btn=document.createElement('button');btn.type='button';btn.className='btn';btn.dataset.createServiceAction='1';btn.textContent='+ Actie maken';btn.onclick=()=>{closeModal();setTimeout(()=>void openActionEditor('',{deviceId,location,sourceKind:'service-report',sourceId:report?.id||'',sourceLabel:`Serviceverslag ${label}`}),0);};foot.insertBefore(btn,link);
    const modal=document.getElementById('modal');if(modal){modal.dataset.serviceActionReportId=String(report.id||'');modal.__machineparkServiceActionReport=report;}
  };

  document.addEventListener('click',e=>{
    const open=e.target.closest('[data-service-action-open]');if(open){openActionDetails(open.dataset.serviceActionOpen);return;}
    const unlink=e.target.closest('[data-service-action-unlink]');if(unlink){const modal=document.getElementById('modal'),report=modal?.__machineparkServiceActionReport;if(report)void unlinkActionFromService(unlink.dataset.serviceActionUnlink,report);}
  });
"""
    index = index[:decorator_start] + enhanced + index[decorator_end:]

    required = [
        "actionStatusLabel",
        "In behandeling",
        "setActionWorkStatus",
        "linkExistingActionToService",
        "Bestaande actie koppelen",
        "linkedActionsForService",
        "machineparkServiceReportStatus",
        "Ontkoppelen",
    ]
    for needle in required:
        if needle not in index:
            raise SystemExit(f"Buildvalidatie mislukt: actie/servicefunctie ontbreekt ({needle})")


# De servicelijst wordt al geladen vóór de hoofdapp. Zorg dat elke algemene
# refresh (dus ook na actie koppelen/status wijzigen) de serviceverslagen
# opnieuw tekent zodra de runtime beschikbaar is.
render_all_old = "function renderAll(){renderDashboard();renderProfessionalDashboard();renderDevices();renderMaintenance();renderBreakdowns();renderParts();enhanceSortableTables();reapplyGenericTableSorts();applyOperationalPermissions()}"
render_all_new = "function renderAll(){renderDashboard();renderProfessionalDashboard();renderDevices();renderMaintenance();renderBreakdowns();renderParts();enhanceSortableTables();reapplyGenericTableSorts();applyOperationalPermissions();if(typeof window.renderMachineparkServiceVisits==='function')window.renderMachineparkServiceVisits()}"
if render_all_new not in index:
    if render_all_old not in index:
        raise SystemExit("Buildvalidatie mislukt: renderAll-anker ontbreekt voor servicestatus refresh")
    index = index.replace(render_all_old, render_all_new, 1)

INDEX.write_text(index, encoding="utf-8")

# Serviceverslagen krijgen hun zichtbare status van gekoppelde acties:
# In behandeling > Open > Afgesloten.
report_status_old = "<div><small>Status</small><strong>Afgesloten</strong></div>"
report_status_new = "<div><small>Status</small><strong>${svEsc(typeof window.machineparkServiceReportStatus==='function'?window.machineparkServiceReportStatus(report):'Afgesloten')}</strong></div>"
if report_status_new not in service:
    if report_status_old not in service:
        raise SystemExit("Buildvalidatie mislukt: serviceverslag-statusblok ontbreekt")
    service = service.replace(report_status_old, report_status_new, 1)

table_old = '<td><span class="service-visit-status">Afgesloten</span></td>'
table_new = '<td><span class="service-visit-status">${svEsc(typeof window.machineparkServiceReportStatus===`function`?window.machineparkServiceReportStatus(r):`Afgesloten`)}</span></td>'
if table_new not in service:
    if table_old not in service:
        raise SystemExit("Buildvalidatie mislukt: servicetabel-status ontbreekt")
    service = service.replace(table_old, table_new, 1)

pdf_old = "{label:'Status',value:'Afgesloten'}"
pdf_new = "{label:'Status',value:(typeof window.machineparkServiceReportStatus==='function'?window.machineparkServiceReportStatus(report):'Afgesloten')}"
if pdf_new not in service:
    count = service.count(pdf_old)
    if count != 2:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 2 PDF-statusvelden, gevonden {count}")
    service = service.replace(pdf_old, pdf_new)


# Acties moeten ook tijdens een nieuw of heropend serviceconcept gekoppeld kunnen
# worden. Het concept reserveert daarom meteen het uiteindelijke serviceReportId.
draft_header_old = "appendToVisitId:activeVisitDraft.appendToVisitId||'',appendToReportId:activeVisitDraft.appendToReportId||'',editMode:Boolean(activeVisitDraft.editMode)"
draft_header_new = "appendToVisitId:activeVisitDraft.appendToVisitId||'',appendToReportId:activeVisitDraft.appendToReportId||'',draftReportId:activeVisitDraft.draftReportId||'',linkedActionIds:Array.isArray(activeVisitDraft.linkedActionIds)?activeVisitDraft.linkedActionIds:[],editMode:Boolean(activeVisitDraft.editMode)"
if draft_header_new not in service:
    if draft_header_old not in service:
        raise SystemExit("Buildvalidatie mislukt: serviceconcept-headeranker voor acties ontbreekt")
    service = service.replace(draft_header_old, draft_header_new, 1)

draft_report_id_old = "reportId=report?.id||header.appendToReportId||uid('sr')"
draft_report_id_new = "reportId=report?.id||header.appendToReportId||header.draftReportId||uid('sr')"
if draft_report_id_new not in service:
    if draft_report_id_old not in service:
        raise SystemExit("Buildvalidatie mislukt: serviceReportId-anker voor concept ontbreekt")
    service = service.replace(draft_report_id_old, draft_report_id_new, 1)

active_draft_old = "appendToReportId:report?.id||header?.appendToReportId||'',appendToVisitId:activeVisit?.id||header?.appendToVisitId||'',editMode"
active_draft_new = "appendToReportId:report?.id||header?.appendToReportId||'',appendToVisitId:activeVisit?.id||header?.appendToVisitId||'',draftReportId:report?.id||header?.draftReportId||uid('sr'),linkedActionIds:Array.isArray(header?.linkedActionIds)?header.linkedActionIds:(report&&typeof window.machineparkLinkedActionIdsForService==='function'?window.machineparkLinkedActionIdsForService(report.id):[]),editMode"
if active_draft_new not in service:
    if active_draft_old not in service:
        raise SystemExit("Buildvalidatie mislukt: activeVisitDraft-anker voor acties ontbreekt")
    service = service.replace(active_draft_old, active_draft_new, 1)

draft_footer_old = "foot.insertBefore(status,submit);foot.insertBefore(button,submit);if(cancel)cancel.textContent='Sluiten';"
draft_footer_new = """const actionButton=document.createElement('button');actionButton.type='button';actionButton.className='btn service-draft-action-button';
    const updateActionButton=()=>{const count=Array.isArray(activeVisitDraft?.linkedActionIds)?activeVisitDraft.linkedActionIds.length:0;actionButton.textContent=count?('Acties ('+count+')'):'Actie koppelen';};
    updateActionButton();
    actionButton.onclick=async()=>{if(typeof window.machineparkOpenServiceDraftActionPicker!=='function'){toast('Actiekoppeling is nog niet geladen.');return;}actionButton.disabled=true;try{activeVisitDraft.touched=true;const saved=await queueDraftSave({force:true});if(!saved||!activeVisitDraft)return;const deviceIds=[...new Set((saved.items||[]).map(item=>String(item.deviceId||'')).filter(Boolean))],locations=(saved.header.locations||[]).map(loc=>loc.label).filter(Boolean);window.machineparkOpenServiceDraftActionPicker({reportId:activeVisitDraft.draftReportId,linkedActionIds:[...(activeVisitDraft.linkedActionIds||[])],deviceIds,date:saved.header.date,locations,onChange:async ids=>{if(!activeVisitDraft)return;activeVisitDraft.linkedActionIds=[...ids];activeVisitDraft.header={...(activeVisitDraft.header||saved.header),linkedActionIds:[...ids],draftReportId:activeVisitDraft.draftReportId};activeVisitDraft.touched=true;await queueDraftSave({force:true});updateActionButton();}});}catch(e){alert(e?.message||'Actie koppelen mislukt.');}finally{if(document.body.contains(actionButton))actionButton.disabled=false;}};
    foot.insertBefore(status,submit);foot.insertBefore(actionButton,submit);foot.insertBefore(button,submit);if(cancel)cancel.textContent='Sluiten';"""
if "service-draft-action-button" not in service:
    if draft_footer_old not in service:
        raise SystemExit("Buildvalidatie mislukt: footeranker serviceconcept voor actieknop ontbreekt")
    service = service.replace(draft_footer_old, draft_footer_new, 1)

finalize_old = "const result=await finalizeDraftTransaction(saved.header,saved.items,selected,report);\n      activeVisitDraft=null;baseCloseModal();await refresh();"
finalize_new = "const result=await finalizeDraftTransaction(saved.header,saved.items,selected,report);\n      if(typeof window.machineparkFinalizeServiceDraftActions==='function')await window.machineparkFinalizeServiceDraftActions({reportId:result.id,linkedActionIds:saved.header.linkedActionIds||[],date:saved.header.date,locations:(result.visits||[]).map(v=>v.location).filter(Boolean)});\n      activeVisitDraft=null;baseCloseModal();await refresh();"
if "machineparkFinalizeServiceDraftActions" not in service:
    if finalize_old not in service:
        raise SystemExit("Buildvalidatie mislukt: finalize-anker voor actiekoppeling ontbreekt")
    service = service.replace(finalize_old, finalize_new, 1)

delete_draft_old = "await refreshVisitState();await syncVisitDraft();toast('Serviceconcept verwijderd');"
delete_draft_new = "if(header.draftReportId&&typeof window.machineparkClearServiceDraftActionLinks==='function')await window.machineparkClearServiceDraftActionLinks(header.draftReportId);await refreshVisitState();await syncVisitDraft();toast('Serviceconcept verwijderd');"
if "machineparkClearServiceDraftActionLinks(header.draftReportId)" not in service:
    if delete_draft_old not in service:
        raise SystemExit("Buildvalidatie mislukt: verwijderen-serviceconceptanker voor acties ontbreekt")
    service = service.replace(delete_draft_old, delete_draft_new, 1)

SERVICE.write_text(service, encoding="utf-8")

print("[Machinepark] Acties: status In behandeling + bestaande actie koppelen aan service + dynamische servicestatus")
