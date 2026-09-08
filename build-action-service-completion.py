from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
MARKER = 'data-machinepark-action-service-completion="v1"'

index = INDEX.read_text(encoding="utf-8")

if MARKER not in index:
    style_anchor = "</head>"
    style = r"""
<style data-machinepark-action-service-completion="v1">
.service-action-complete-check{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border:1px solid #b9ccc5;border-radius:9px;background:#fff;cursor:pointer;font-weight:800;color:#174c3d}
.service-action-complete-check:hover{background:#eef7f3}
.service-action-complete-check:disabled{background:#e8f4ee;color:#245f4b;cursor:default;opacity:1}
</style>
"""
    if style_anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: </head> ontbreekt voor service-actie afronden")
    index = index.replace(style_anchor, style + style_anchor, 1)

    helper_anchor = r"""  function serviceDraftContextLabel(ctx){
    const date=ctx&&ctx.date?dateFmt(ctx.date):'';
    const locations=Array.isArray(ctx&&ctx.locations)?ctx.locations.filter(Boolean):[];
    return [date,...locations].filter(Boolean).join(' · ');
  }
"""
    helper_new = helper_anchor + r"""
  async function completeLinkedActionFromService(actionId,ctx={}){
    const item=(state.actions||[]).find(a=>String(a.id||'')===String(actionId||''));if(!item||item.status==='done')return false;
    const me=actionCurrentUser(),now=new Date().toISOString(),deviceIds=(Array.isArray(ctx.deviceIds)?ctx.deviceIds:[]).map(String).filter(Boolean);
    const fallbackDeviceId=!item.deviceId&&deviceIds.length===1?deviceIds[0]:'',deviceId=item.deviceId||fallbackDeviceId,device=(state.devices||[]).find(d=>String(d.id)===String(deviceId));
    const detail=['Uitgevoerd door '+me.name,ctx.label?String(ctx.label):'',device?'toestel '+(device.assetCode||device.model||''):''].filter(Boolean).join(' · ');
    const updated={...item,status:'done',deviceId,location:item.location||(device?(deviceLocationAt(device)||device.location||''):''),completedDate:todayISO(),completedAt:now,completedById:me.id,completedByName:me.name,completedByEmail:me.email,updatedAt:now,history:appendActionHistory(item,historyEntry('completed','Actie uitgevoerd',detail))};
    await put('actions',updated);
    state.actions=await getAll('actions');
    renderActions();renderActionDashboard();
    if(typeof window.renderMachineparkServiceVisits==='function')window.renderMachineparkServiceVisits();
    toast('Actie afgerond');
    return true;
  }
"""
    if helper_anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: contextanker ontbreekt voor service-actie afronden")
    index = index.replace(helper_anchor, helper_new, 1)

    picker_old = r"""      main.append(name,meta);row.append(check,main);list.appendChild(row);"""
    picker_new = r"""      main.append(name,meta);row.append(check,main);
      if(linked.has(String(action.id||''))&&action.status!=='done'){
        const complete=document.createElement('button');complete.type='button';complete.className='service-action-complete-check';complete.textContent='✓';complete.title='Actie afronden';
        complete.onclick=async event=>{event.preventDefault();event.stopPropagation();complete.disabled=true;try{const ok=await completeLinkedActionFromService(action.id,{deviceIds:[...(ctx.deviceIds||[])],label:serviceDraftContextLabel(ctx)});if(ok)window.machineparkOpenServiceDraftActionPicker({...ctx,linkedActionIds:[...linked]});}finally{if(document.body.contains(complete))complete.disabled=false;}};
        row.appendChild(complete);
      }
      list.appendChild(row);"""
    if picker_old not in index:
        raise SystemExit("Buildvalidatie mislukt: actiepicker-anker ontbreekt voor afrondvinkje")
    index = index.replace(picker_old, picker_new, 1)

    linked_old = r"""<div class="action-card-actions"><button type="button" class="btn small" data-service-action-open="${esc(a.id)}">Bekijken</button><button type="button" class="btn small" data-service-action-unlink="${esc(a.id)}">Ontkoppelen</button></div>"""
    linked_new = r"""<div class="action-card-actions"><button type="button" class="service-action-complete-check" title="Actie afronden" data-service-action-complete="${esc(a.id)}" ${a.status==='done'?'disabled':''}>✓</button><button type="button" class="btn small" data-service-action-open="${esc(a.id)}">Bekijken</button><button type="button" class="btn small" data-service-action-unlink="${esc(a.id)}">Ontkoppelen</button></div>"""
    if linked_old not in index:
        raise SystemExit("Buildvalidatie mislukt: gekoppelde-actierij ontbreekt voor afrondvinkje")
    index = index.replace(linked_old, linked_new, 1)

    event_old = r"""  document.addEventListener('click',e=>{
    const open=e.target.closest('[data-service-action-open]');if(open){openActionDetails(open.dataset.serviceActionOpen);return;}
    const unlink=e.target.closest('[data-service-action-unlink]');if(unlink){const modal=document.getElementById('modal'),report=modal?.__machineparkServiceActionReport;if(report)void unlinkActionFromService(unlink.dataset.serviceActionUnlink,report);}
  });"""
    event_new = r"""  document.addEventListener('click',e=>{
    const complete=e.target.closest('[data-service-action-complete]');if(complete){const modal=document.getElementById('modal'),report=modal?.__machineparkServiceActionReport;if(report){complete.disabled=true;void completeLinkedActionFromService(complete.dataset.serviceActionComplete,{deviceIds:[...new Set((report.records||[]).map(row=>row?.item?.deviceId||row?.deviceId).filter(Boolean))],label:serviceActionReportLabel(report)}).then(ok=>{if(ok)renderLinkedServiceActions(report);}).finally(()=>{if(document.body.contains(complete))complete.disabled=false;});}return;}
    const open=e.target.closest('[data-service-action-open]');if(open){openActionDetails(open.dataset.serviceActionOpen);return;}
    const unlink=e.target.closest('[data-service-action-unlink]');if(unlink){const modal=document.getElementById('modal'),report=modal?.__machineparkServiceActionReport;if(report)void unlinkActionFromService(unlink.dataset.serviceActionUnlink,report);}
  });"""
    if event_old not in index:
        raise SystemExit("Buildvalidatie mislukt: service-actie clickhandler ontbreekt voor afrondvinkje")
    index = index.replace(event_old, event_new, 1)

    required = [
        "completeLinkedActionFromService",
        "service-action-complete-check",
        "data-service-action-complete",
        "Actie afgerond",
    ]
    for needle in required:
        if needle not in index:
            raise SystemExit(f"Buildvalidatie mislukt: service-actie afronden ontbreekt ({needle})")

INDEX.write_text(index, encoding="utf-8")
print("[Machinepark] gekoppelde acties kunnen met vinkje vanuit service worden afgerond")
