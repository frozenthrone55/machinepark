from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SERVICE = ROOT / "service-visits.js"
MARKER = "machinepark-action-service-auto-complete-v1"

index = INDEX.read_text(encoding="utf-8")
service = SERVICE.read_text(encoding="utf-8")

if MARKER not in index:
    # Pas uitsluitend de service-specifieke afrondhelper aan. Een losse tekstvervanging
    # op 'Actie uitgevoerd' kan ook de gewone handmatige ToDo-afronding raken.
    helper_history_old = """    const updated={...item,status:'done',deviceId,location:item.location||(device?(deviceLocationAt(device)||device.location||''):''),completedDate:todayISO(),completedAt:now,completedById:me.id,completedByName:me.name,completedByEmail:me.email,updatedAt:now,history:appendActionHistory(item,historyEntry('completed','Actie uitgevoerd',detail))};
    await put('actions',updated);
    state.actions=await getAll('actions');"""
    helper_history_new = """    const updated={...item,status:'done',deviceId,location:item.location||(device?(deviceLocationAt(device)||device.location||''):''),completedDate:todayISO(),completedAt:now,completedById:me.id,completedByName:me.name,completedByEmail:me.email,updatedAt:now,history:appendActionHistory(item,historyEntry('completed',ctx.automatic?'Automatisch afgesloten met serviceverslag':'Actie uitgevoerd',detail))};
    await put('actions',updated);
    state.actions=await getAll('actions');"""
    if helper_history_old not in index:
        raise SystemExit("Buildvalidatie mislukt: service-specifieke historiek voor gekoppelde ToDo afronden ontbreekt")
    index = index.replace(helper_history_old, helper_history_new, 1)

    toast_old = "    toast('Actie afgerond');\n    return true;"
    toast_new = "    if(!ctx.silent)toast('Actie afgerond');\n    return true;"
    if toast_old not in index:
        raise SystemExit("Buildvalidatie mislukt: toast voor gekoppelde ToDo afronden ontbreekt")
    index = index.replace(toast_old, toast_new, 1)

    finalize_old = """  window.machineparkFinalizeServiceDraftActions=async function(ctx){
    try{await applyServiceDraftActionLinks(ctx,ctx&&ctx.linkedActionIds||[],true);}
    catch(error){console.warn('Actiekoppeling serviceconcept finaliseren',error);toast('Serviceverslag opgeslagen, maar de actiekoppeling kon niet bijgewerkt worden.');}
  };"""
    finalize_new = """  // machinepark-action-service-auto-complete-v1
  window.machineparkFinalizeServiceDraftActions=async function(ctx){
    const ids=[...new Set((Array.isArray(ctx&&ctx.linkedActionIds)?ctx.linkedActionIds:[]).map(String).filter(Boolean))];
    try{
      await applyServiceDraftActionLinks(ctx,ids,true);
    }catch(error){
      console.warn('Actiekoppeling serviceconcept finaliseren',error);
      toast('Serviceverslag opgeslagen, maar de actiekoppeling kon niet bijgewerkt worden.');
      return;
    }

    const label=serviceDraftContextLabel(ctx),deviceIds=(Array.isArray(ctx&&ctx.deviceIds)?ctx.deviceIds:[]).map(String).filter(Boolean);
    let completed=0,failed=0;
    for(const actionId of ids){
      const item=(state.actions||[]).find(a=>String(a.id||'')===String(actionId));
      if(!item||item.status==='done')continue;
      try{
        if(await completeLinkedActionFromService(actionId,{deviceIds,label,automatic:true,silent:true}))completed++;
      }catch(error){
        failed++;
        console.warn('Gekoppelde ToDo automatisch afsluiten met serviceverslag',actionId,error);
      }
    }
    if(failed){
      toast('Serviceverslag opgeslagen, maar niet alle gekoppelde ToDo’s konden automatisch worden afgesloten.');
    }else if(completed===1){
      toast('Gekoppelde ToDo automatisch afgesloten met het serviceverslag.');
    }else if(completed>1){
      toast(completed+' gekoppelde ToDo’s automatisch afgesloten met het serviceverslag.');
    }
  };"""
    if finalize_old not in index:
        raise SystemExit("Buildvalidatie mislukt: finalisatie van service-actiekoppeling ontbreekt")
    index = index.replace(finalize_old, finalize_new, 1)

service_finalize_old = """if(typeof window.machineparkFinalizeServiceDraftActions==='function')await window.machineparkFinalizeServiceDraftActions({reportId:result.id,linkedActionIds:saved.header.linkedActionIds||[],date:saved.header.date,locations:(result.visits||[]).map(v=>v.location).filter(Boolean)});"""
service_finalize_new = """if(typeof window.machineparkFinalizeServiceDraftActions==='function')await window.machineparkFinalizeServiceDraftActions({reportId:result.id,linkedActionIds:saved.header.linkedActionIds||[],date:saved.header.date,locations:(result.visits||[]).map(v=>v.location).filter(Boolean),deviceIds:[...new Set((result.finals||[]).map(item=>item&&item.deviceId).filter(Boolean))]});"""
if service_finalize_new not in service:
    if service_finalize_old not in service:
        raise SystemExit("Buildvalidatie mislukt: serviceverslag-finalisatiehook voor gekoppelde ToDo ontbreekt")
    service = service.replace(service_finalize_old, service_finalize_new, 1)

required_index = [
    MARKER,
    "completeLinkedActionFromService(actionId,{deviceIds,label,automatic:true,silent:true})",
    "ctx.automatic?'Automatisch afgesloten met serviceverslag':'Actie uitgevoerd'",
    "Gekoppelde ToDo automatisch afgesloten met het serviceverslag.",
]
for needle in required_index:
    if needle not in index:
        raise SystemExit("Buildvalidatie mislukt: automatische ToDo-afsluiting ontbreekt (" + needle + ")")

# De automatische historiekexpressie mag alleen in de service-specifieke helper voorkomen.
if index.count("ctx.automatic?'Automatisch afgesloten met serviceverslag':'Actie uitgevoerd'") != 1:
    raise SystemExit("Buildvalidatie mislukt: automatische servicehistoriek staat op een verkeerde of dubbele plaats")

if "deviceIds:[...new Set((result.finals||[]).map(item=>item&&item.deviceId).filter(Boolean))]" not in service:
    raise SystemExit("Buildvalidatie mislukt: toestelcontext ontbreekt bij automatische ToDo-afsluiting")

INDEX.write_text(index, encoding="utf-8")
SERVICE.write_text(service, encoding="utf-8")
print("[Machinepark] gekoppelde open ToDo's sluiten automatisch mee af met het serviceverslag")
