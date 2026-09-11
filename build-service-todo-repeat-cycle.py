from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
MARKER = "machinepark-service-todo-repeat-cycle-v2"

index = INDEX.read_text(encoding="utf-8")

if MARKER not in index:
    start = index.find("  function actionWasAutoCompletedByService(item){")
    end_marker = "\n  window.machineparkReconcileServiceReportTodos=reconcileServiceReportTodos;"
    end = index.find(end_marker, start)
    if start < 0 or end < 0:
        raise SystemExit("Buildvalidatie mislukt: service/ToDo state-machineblok niet gevonden voor herhaalcycli")
    end += len(end_marker)

    replacement = r'''  // machinepark-service-todo-repeat-cycle-v2
  function serviceAutoManagedReportIds(item){
    return [...new Set((Array.isArray(item?.serviceAutoManagedReportIds)?item.serviceAutoManagedReportIds:[]).map(String).filter(Boolean))];
  }

  function actionHasLegacyServiceAutomation(item){
    const history=Array.isArray(item?.history)?item.history:[];
    return history.some(entry=>entry?.serviceAutomation===true||String(entry?.label||'')==='Automatisch afgesloten met serviceverslag');
  }

  function actionIsServiceAutoManaged(item,reportId=''){
    const id=String(reportId||'');
    const managed=serviceAutoManagedReportIds(item);
    if(id&&managed.includes(id))return true;
    // Migratie voor ToDo's die al vóór deze fix automatisch door service werden
    // afgesloten. Een oude history-regel blijft dus geldig na meerdere heropeningen.
    return actionHasLegacyServiceAutomation(item);
  }

  function serviceActionLinkedWorkState(item,currentReportId='',currentWorkState=''){
    const currentId=String(currentReportId||'');
    const ids=typeof actionServiceIds==='function'?actionServiceIds(item):[];
    if(!ids.length)return currentWorkState||'open';
    const states=ids.map(reportId=>String(reportId)===currentId&&currentWorkState
      ? currentWorkState
      : serviceWorkStateFromRecords(serviceRecordsForReport(reportId)));
    if(states.some(state=>state==='in_progress'))return 'in_progress';
    if(states.some(state=>state==='open'))return 'open';
    return 'done';
  }

  async function persistServiceManagedActionState(item,reportId,targetState,label=''){
    if(!item)return false;
    const id=String(reportId||'');
    const now=new Date().toISOString(),me=actionCurrentUser();
    const linkedIds=typeof actionServiceIds==='function'?actionServiceIds(item):[id].filter(Boolean);
    const managedIds=new Set(serviceAutoManagedReportIds(item));
    const wasManaged=actionIsServiceAutoManaged(item,id);
    let updated=null;

    if(targetState==='done'){
      if(item.status==='done')return false;
      linkedIds.forEach(linkedId=>managedIds.add(String(linkedId)));
      if(id)managedIds.add(id);
      const detail=[label||'', 'Alle gekoppelde servicewerkzaamheden zijn afgewerkt', 'Uitgevoerd door '+me.name].filter(Boolean).join(' · ');
      updated={
        ...item,
        status:'done',
        completedDate:todayISO(),
        completedAt:now,
        completedById:me.id,
        completedByName:me.name,
        completedByEmail:me.email,
        serviceAutoManagedReportIds:[...managedIds],
        updatedAt:now,
        history:appendActionHistory(item,{...historyEntry('completed','Automatisch afgesloten met serviceverslag',detail),serviceAutomation:true,serviceReportId:id})
      };
    }else{
      const next=targetState==='in_progress'?'in_progress':'open';
      if(item.status==='done'){
        if(!wasManaged)return false;
        if(id)managedIds.add(id);
        const detail=[label||'',next==='in_progress'?'Werkzaamheden opnieuw in behandeling':'Werkzaamheden opnieuw open'].filter(Boolean).join(' · ');
        updated={
          ...item,
          status:next,
          completedDate:'',completedAt:'',completedById:'',completedByName:'',completedByEmail:'',
          serviceAutoManagedReportIds:[...managedIds],
          updatedAt:now,
          history:appendActionHistory(item,{...historyEntry('reopened','Automatisch heropend door serviceverslag',detail),serviceAutomation:true,serviceReportId:id})
        };
      }else{
        // Zodra service deze ToDo eenmaal automatisch beheert, blijft hij ook
        // tussen Open en In behandeling de werkelijke servicestatus volgen.
        if(!wasManaged||item.status===next)return false;
        if(id)managedIds.add(id);
        const detail=[label||'',next==='in_progress'?'In behandeling':'Open'].filter(Boolean).join(' · ');
        updated={
          ...item,
          status:next,
          serviceAutoManagedReportIds:[...managedIds],
          updatedAt:now,
          history:appendActionHistory(item,{...historyEntry('status','Servicestatus automatisch gevolgd',detail),serviceAutomation:true,serviceReportId:id})
        };
      }
    }

    await put('actions',updated);
    const pos=(state.actions||[]).findIndex(action=>String(action.id||'')===String(updated.id||''));
    if(pos>=0)state.actions[pos]=updated;else state.actions=[...(state.actions||[]),updated];
    return true;
  }

  async function reconcileServiceReportTodos(reportId,records,ctx={}){
    const id=String(reportId||'');if(!id)return {workState:'open',completed:0,reopened:0,changed:0,failed:0};
    const workRecords=Array.isArray(records)&&records.length?records:serviceRecordsForReport(id);
    const currentWorkState=serviceWorkStateFromRecords(workRecords);
    const actions=linkedActionsForService(id);
    const label=ctx.label||serviceDraftContextLabel(ctx);
    let completed=0,reopened=0,changed=0,failed=0;

    for(const action of actions){
      try{
        const targetState=serviceActionLinkedWorkState(action,id,currentWorkState);
        const before=action.status||'open';
        const didChange=await persistServiceManagedActionState(action,id,targetState,label);
        if(!didChange)continue;
        changed++;
        if(targetState==='done'&&before!=='done')completed++;
        else if(before==='done'&&targetState!=='done')reopened++;
      }catch(error){
        failed++;
        console.warn('Service/ToDo-status synchroniseren',id,action?.id,error);
      }
    }

    if(changed){
      state.actions=await getAll('actions');
      renderActions();renderActionDashboard();
      if(typeof window.renderMachineparkServiceVisits==='function')window.renderMachineparkServiceVisits();
    }
    return {workState:currentWorkState,completed,reopened,changed,failed};
  }
  window.machineparkReconcileServiceReportTodos=reconcileServiceReportTodos;'''

    index = index[:start] + replacement + index[end:]

required = [
    MARKER,
    "serviceAutoManagedReportIds",
    "actionHasLegacyServiceAutomation",
    "serviceActionLinkedWorkState",
    "persistServiceManagedActionState",
    "Servicestatus automatisch gevolgd",
    "serviceAutomation:true",
    "currentWorkState=serviceWorkStateFromRecords(workRecords)",
]
for needle in required:
    if needle not in index:
        raise SystemExit("Buildvalidatie mislukt: herhaalbare service/ToDo-status ontbreekt (" + needle + ")")

# De oude history-heuristiek mocht niet blijven staan. Die stopte bij een
# 'reopened'-regel en was daardoor te kwetsbaar voor meerdere statuscycli.
if "if(entry.type==='reopened')return false;" in index:
    raise SystemExit("Buildvalidatie mislukt: oude eenmalige service/ToDo-historyheuristiek is nog actief")

INDEX.write_text(index, encoding="utf-8")
print("[Machinepark] service/ToDo koppeling blijft stabiel over onbeperkte open-afgewerkt cycli")
