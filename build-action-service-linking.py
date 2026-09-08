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

SERVICE.write_text(service, encoding="utf-8")

print("[Machinepark] Acties: status In behandeling + bestaande actie koppelen aan service + dynamische servicestatus")
