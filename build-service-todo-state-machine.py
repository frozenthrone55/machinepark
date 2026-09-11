from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SERVICE = ROOT / "service-visits.js"
MARKER = "machinepark-service-todo-state-machine-v1"

index = INDEX.read_text(encoding="utf-8")
service = SERVICE.read_text(encoding="utf-8")

if MARKER not in index:
    status_old = """  window.machineparkServiceReportStatus=function(report) {
    const linked=linkedActionsForService(report?.id);
    if(linked.some(a=>a.status==='in_progress'))return 'In behandeling';
    if(linked.some(a=>a.status!=='done'))return 'Open';
    return 'Afgesloten';
  };"""
    status_new = """  // machinepark-service-todo-state-machine-v1
  function serviceWorkStateFromRecords(records){
    const rows=(Array.isArray(records)?records:[]).map(row=>row&&row.item?row.item:row).filter(item=>item&&item.isDraft!==true);
    if(!rows.length)return 'open';
    let open=false,inProgress=false;
    const doneValues=new Set(['opgelost','afgewerkt','voltooid','gesloten','closed','done','completed']);
    const progressValues=new Set(['in behandeling','in_progress','bezig','in uitvoering']);
    for(const item of rows){
      const isMaintenance=item.type!==undefined&&item.serviceKind!=='other';
      const raw=String(item.status||'').trim().toLowerCase();
      // Onderhoud is uitgevoerd zodra de definitieve onderhoudsregistratie bestaat.
      // Als een toekomstig onderhoudsrecord expliciet een status krijgt, respecteren we die wel.
      if(isMaintenance&&!raw)continue;
      if(doneValues.has(raw))continue;
      if(progressValues.has(raw)){inProgress=true;continue;}
      open=true;
    }
    return inProgress?'in_progress':open?'open':'done';
  }
  window.machineparkServiceWorkStateFromRecords=serviceWorkStateFromRecords;

  function serviceRecordsForReport(reportId){
    const id=String(reportId||'');
    if(!id)return [];
    return [...(state.maintenance||[]),...(state.breakdowns||[])].filter(item=>item&&item.isDraft!==true&&String(item.serviceReportId||item.serviceVisitId||'')===id);
  }

  function serviceWorkStateForReport(report){
    const records=Array.isArray(report?.records)&&report.records.length?report.records:serviceRecordsForReport(report?.id||report);
    return serviceWorkStateFromRecords(records);
  }
  window.machineparkServiceReportWorkState=serviceWorkStateForReport;

  window.machineparkServiceReportStatus=function(report) {
    const workState=serviceWorkStateForReport(report);
    if(workState==='in_progress')return 'In behandeling';
    if(workState==='open')return 'Open';
    const linked=linkedActionsForService(report?.id);
    if(linked.some(a=>a.status==='in_progress'))return 'In behandeling';
    if(linked.some(a=>a.status!=='done'))return 'Open';
    return 'Afgesloten';
  };"""
    if status_old not in index:
        raise SystemExit("Buildvalidatie mislukt: oude service-statusfunctie ontbreekt")
    index = index.replace(status_old, status_new, 1)

    finalize_start = index.find("  // machinepark-action-service-auto-complete-v1\n  window.machineparkFinalizeServiceDraftActions=async function(ctx){")
    finalize_end = index.find("\n\n  window.machineparkClearServiceDraftActionLinks=async function(context){", finalize_start)
    if finalize_start < 0 or finalize_end < 0:
        raise SystemExit("Buildvalidatie mislukt: service/ToDo-finalisatieblok ontbreekt")

    finalize_new = """  // machinepark-action-service-auto-complete-v1
  function actionWasAutoCompletedByService(item){
    const history=Array.isArray(item&&item.history)?item.history:[];
    for(let i=history.length-1;i>=0;i--){
      const entry=history[i]||{};
      if(entry.type==='reopened')return false;
      if(entry.type==='completed')return String(entry.label||'')==='Automatisch afgesloten met serviceverslag';
    }
    return false;
  }

  async function reopenAutoCompletedActionFromService(actionId,workState,label){
    const item=(state.actions||[]).find(a=>String(a.id||'')===String(actionId||''));
    if(!item||item.status!=='done'||!actionWasAutoCompletedByService(item))return false;
    const now=new Date().toISOString(),next=workState==='in_progress'?'in_progress':'open';
    const detail=[label||'',next==='in_progress'?'Werkzaamheden opnieuw in behandeling':'Werkzaamheden opnieuw open'].filter(Boolean).join(' · ');
    const updated={...item,status:next,completedDate:'',completedAt:'',completedById:'',completedByName:'',completedByEmail:'',updatedAt:now,history:appendActionHistory(item,historyEntry('reopened','Automatisch heropend door serviceverslag',detail))};
    await put('actions',updated);
    state.actions=await getAll('actions');
    renderActions();renderActionDashboard();
    if(typeof window.renderMachineparkServiceVisits==='function')window.renderMachineparkServiceVisits();
    return true;
  }

  async function reconcileServiceReportTodos(reportId,records,ctx={}){
    const id=String(reportId||'');if(!id)return {workState:'open',completed:0,reopened:0,failed:0};
    const workRecords=Array.isArray(records)&&records.length?records:serviceRecordsForReport(id);
    const workState=serviceWorkStateFromRecords(workRecords);
    const ids=[...new Set(linkedActionsForService(id).map(a=>String(a&&a.id||'')).filter(Boolean))];
    const label=ctx.label||serviceDraftContextLabel(ctx);
    const deviceIds=(Array.isArray(ctx.deviceIds)?ctx.deviceIds:workRecords.map(row=>(row&&row.item?row.item:row)?.deviceId)).map(String).filter(Boolean);
    let completed=0,reopened=0,failed=0;
    for(const actionId of ids){
      try{
        const item=(state.actions||[]).find(a=>String(a.id||'')===actionId);
        if(!item)continue;
        if(workState==='done'){
          if(item.status!=='done'&&await completeLinkedActionFromService(actionId,{deviceIds,label,automatic:true,silent:true}))completed++;
        }else if(item.status==='done'&&actionWasAutoCompletedByService(item)){
          if(await reopenAutoCompletedActionFromService(actionId,workState,label))reopened++;
        }
      }catch(error){failed++;console.warn('Service/ToDo-status synchroniseren',id,actionId,error);}
    }
    return {workState,completed,reopened,failed};
  }
  window.machineparkReconcileServiceReportTodos=reconcileServiceReportTodos;

  async function reconcileAllServiceReportTodos(){
    const rows=[...(state.maintenance||[]),...(state.breakdowns||[])].filter(item=>item&&item.isDraft!==true&&(item.serviceReportId||item.serviceVisitId));
    const reportIds=[...new Set(rows.map(item=>String(item.serviceReportId||item.serviceVisitId||'')).filter(Boolean))];
    for(const reportId of reportIds){
      const records=rows.filter(item=>String(item.serviceReportId||item.serviceVisitId||'')===reportId);
      const first=records[0]||{},locations=[...new Set(records.map(item=>String(item.serviceVisitLocation||'').trim()).filter(Boolean))];
      await reconcileServiceReportTodos(reportId,records,{date:first.serviceReportDate||first.serviceVisitDate||first.date||'',locations,deviceIds:[...new Set(records.map(item=>String(item.deviceId||'')).filter(Boolean))]});
    }
  }
  window.machineparkReconcileAllServiceReportTodos=reconcileAllServiceReportTodos;

  window.machineparkFinalizeServiceDraftActions=async function(ctx){
    const requestedIds=(Array.isArray(ctx&&ctx.linkedActionIds)?ctx.linkedActionIds:[]).map(String).filter(Boolean);
    const storedIds=typeof linkedActionsForService==='function'?linkedActionsForService(ctx&&ctx.reportId).map(a=>String(a&&a.id||'')).filter(Boolean):[];
    const ids=[...new Set([...requestedIds,...storedIds])];
    try{
      await applyServiceDraftActionLinks(ctx,ids,true);
    }catch(error){
      console.warn('ToDo-koppeling serviceconcept finaliseren',error);
      toast('Serviceverslag opgeslagen, maar de ToDo-koppeling kon niet bijgewerkt worden.');
      return;
    }

    const result=await reconcileServiceReportTodos(ctx&&ctx.reportId,ctx&&ctx.records,{...ctx,label:serviceDraftContextLabel(ctx)});
    if(result.failed){
      toast('Serviceverslag opgeslagen, maar niet alle gekoppelde ToDo’s konden worden bijgewerkt.');
    }else if(result.completed===1){
      toast('Gekoppelde ToDo automatisch afgesloten: alle werkzaamheden zijn afgewerkt.');
    }else if(result.completed>1){
      toast(result.completed+' gekoppelde ToDo’s automatisch afgesloten: alle werkzaamheden zijn afgewerkt.');
    }else if(result.reopened===1){
      toast('Gekoppelde ToDo automatisch heropend omdat het serviceverslag opnieuw open staat.');
    }else if(result.reopened>1){
      toast(result.reopened+' gekoppelde ToDo’s automatisch heropend omdat het serviceverslag opnieuw open staat.');
    }
  };"""
    index = index[:finalize_start] + finalize_new + index[finalize_end:]

    # Elke route die na een wijziging refresh() gebruikt (service-editor, losse
    # depannage, centrale sync, koppelen, heropenen...) krijgt dezelfde centrale
    # reconciliatie. Zo hangt de automatische ToDo-afwerking niet meer van één
    # specifieke knop of modal af.
    refresh_anchor = "  window.machineparkClearServiceDraftActionLinks=async function(context){"
    refresh_pos = index.find(refresh_anchor)
    if refresh_pos < 0:
        raise SystemExit("Buildvalidatie mislukt: anker voor centrale refresh-reconciliatie ontbreekt")
    refresh_wrapper = """  const machineparkBaseRefreshForServiceTodoState=refresh;
  let machineparkServiceTodoRefreshBusy=false;
  refresh=async function(){
    const result=await machineparkBaseRefreshForServiceTodoState.apply(this,arguments);
    if(!machineparkServiceTodoRefreshBusy){
      machineparkServiceTodoRefreshBusy=true;
      try{await reconcileAllServiceReportTodos();}
      catch(error){console.warn('Service/ToDo-status na refresh synchroniseren',error);}
      finally{machineparkServiceTodoRefreshBusy=false;}
    }
    return result;
  };
  window.refresh=refresh;

"""
    index = index[:refresh_pos] + refresh_wrapper + index[refresh_pos:]

# Geef de definitieve records mee aan de state-machine. Dit is essentieel bij
# bewerken: IndexedDB is al bijgewerkt, maar state is pas na de hook ververst.
finalize_call_old = """if(typeof window.machineparkFinalizeServiceDraftActions==='function')await window.machineparkFinalizeServiceDraftActions({reportId:result.id,linkedActionIds:saved.header.linkedActionIds||[],date:saved.header.date,locations:(result.visits||[]).map(v=>v.location).filter(Boolean),deviceIds:[...new Set((result.finals||[]).map(item=>item&&item.deviceId).filter(Boolean))]});"""
finalize_call_new = """if(typeof window.machineparkFinalizeServiceDraftActions==='function')await window.machineparkFinalizeServiceDraftActions({reportId:result.id,linkedActionIds:saved.header.linkedActionIds||[],date:saved.header.date,locations:(result.visits||[]).map(v=>v.location).filter(Boolean),deviceIds:[...new Set((result.finals||[]).map(item=>item&&item.deviceId).filter(Boolean))],records:result.finals||[]});"""
if finalize_call_new not in service:
    if finalize_call_old not in service:
        raise SystemExit("Buildvalidatie mislukt: service-finalisatiecall ontbreekt voor werkzaamhedenstatus")
    service = service.replace(finalize_call_old, finalize_call_new, 1)

# Bewaar de echte rapportstatus ook in de records. Daardoor klopt de data zelf
# bij nieuw verslag, bewerken en opnieuw openen; niet alleen het zichtbare label.
transaction_anchor = """    const visits=[...visitMeta.values()].map(meta=>({...meta,count:finals.filter(item=>item.serviceVisitId===meta.id).length}));
    return new Promise((resolve,reject)=>{let tr;try{tr=db.transaction(['maintenance','breakdowns','parts'],'readwrite');"""
transaction_new = """    const reportWorkState=typeof window.machineparkServiceWorkStateFromRecords==='function'?window.machineparkServiceWorkStateFromRecords(finals):'done';
    const reportStatus=reportWorkState==='done'?'closed':reportWorkState==='in_progress'?'in_progress':'open';
    for(const item of finals){item.serviceReportStatus=reportStatus;item.serviceReportClosedAt=reportWorkState==='done'?now:'';}
    for(const visitId of new Set(finals.map(item=>item.serviceVisitId).filter(Boolean))){
      const visitRows=finals.filter(item=>item.serviceVisitId===visitId),visitState=typeof window.machineparkServiceWorkStateFromRecords==='function'?window.machineparkServiceWorkStateFromRecords(visitRows):'done';
      const visitStatus=visitState==='done'?'closed':visitState==='in_progress'?'in_progress':'open';
      for(const item of visitRows){item.serviceVisitStatus=visitStatus;item.serviceVisitClosedAt=visitState==='done'?now:'';}
    }
    const visits=[...visitMeta.values()].map(meta=>({...meta,count:finals.filter(item=>item.serviceVisitId===meta.id).length}));
    return new Promise((resolve,reject)=>{let tr;try{tr=db.transaction(['maintenance','breakdowns','parts'],'readwrite');"""
if transaction_new not in service:
    if transaction_anchor not in service:
        raise SystemExit("Buildvalidatie mislukt: service-transactieanker ontbreekt voor echte rapportstatus")
    service = service.replace(transaction_anchor, transaction_new, 1)

required_index = [
    MARKER,
    "function serviceWorkStateFromRecords(records)",
    "window.machineparkServiceReportWorkState=serviceWorkStateForReport",
    "async function reconcileServiceReportTodos",
    "window.machineparkReconcileAllServiceReportTodos=reconcileAllServiceReportTodos",
    "Automatisch heropend door serviceverslag",
    "const machineparkBaseRefreshForServiceTodoState=refresh",
    "ctx&&ctx.records",
]
for needle in required_index:
    if needle not in index:
        raise SystemExit("Buildvalidatie mislukt: service/ToDo state-machine ontbreekt (" + needle + ")")

required_service = [
    "records:result.finals||[]",
    "const reportWorkState=typeof window.machineparkServiceWorkStateFromRecords==='function'",
    "item.serviceReportStatus=reportStatus",
    "item.serviceVisitStatus=visitStatus",
]
for needle in required_service:
    if needle not in service:
        raise SystemExit("Buildvalidatie mislukt: service-recordstatus ontbreekt (" + needle + ")")

INDEX.write_text(index, encoding="utf-8")
SERVICE.write_text(service, encoding="utf-8")
print("[Machinepark] servicewerkzaamheden sturen ToDo-status centraal in beide richtingen")
