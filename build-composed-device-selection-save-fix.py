from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
FEATURE_MARKER = 'data-machinepark-build-fix="composed-source-reports-v1"'
MARKER = 'data-machinepark-build-fix="composed-device-selection-save-v1"'
TODO_MARKER = 'data-machinepark-build-fix="composed-todos-v1"'
HISTORY_CARD_MARKER = 'data-machinepark-build-fix="composed-history-cards-v1"'

index = INDEX.read_text(encoding='utf-8')
if FEATURE_MARKER not in index:
    raise SystemExit('Buildvalidatie mislukt: verslagtabel ontbreekt voor toestel-opslagfix')

if MARKER not in index:
    anchor = '  function openComposedPreview(doc)'
    if index.count(anchor) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x preview-anker voor toestel-opslagfix, gevonden {index.count(anchor)}x')

    script = r'''
  function composedSyncVisibleDeviceSelection(){
    document.querySelectorAll('#composedDeviceBody [data-composed-device]').forEach(cb=>{
      const id=String(cb.dataset.composedDevice||'');if(!id)return;
      if(cb.checked)selectedComposedDevices.add(id);else selectedComposedDevices.delete(id);
    });
    updateComposedSelectedCount();
  }

  const composedReportAwareSaveDocument=saveComposedDocument;
  saveComposedDocument=async function(){
    composedSyncVisibleDeviceSelection();
    return composedReportAwareSaveDocument();
  };

  const composedEnsureUiWithSourceReports=ensureComposedUi;
  ensureComposedUi=function(){
    composedEnsureUiWithSourceReports();
    const saveButton=document.getElementById('composedSaveDocument');
    if(saveButton)saveButton.onclick=()=>saveComposedDocument();
  };
'''
    index = index.replace(anchor, script + '\n' + anchor, 1)
    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-head ontbreekt voor toestel-opslagfix')
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)

if TODO_MARKER not in index:
    history_marker = 'data-machinepark-build-fix="composed-history-photos-v1"'
    if history_marker not in index:
        raise SystemExit('Buildvalidatie mislukt: chronologische geschiedenis ontbreekt voor ToDo-opname')

    anchor = '  function openComposedPreview(doc)'
    if index.count(anchor) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x preview-anker voor ToDo-opname, gevonden {index.count(anchor)}x')

    todo_script = r'''
  function composedTodoServiceIds(item){
    const ids=[
      ...(Array.isArray(item?.serviceReportIds)?item.serviceReportIds:[]),
      ...(Array.isArray(item?.serviceLinks)?item.serviceLinks.map(link=>link?.id):[]),
      item?.sourceKind==='service-report'?item.sourceId:''
    ].filter(Boolean).map(String);
    return [...new Set(ids)];
  }
  function composedTodoMoment(item){
    if(item?.status==='done')return String(item.completedAt||item.completedDate||item.updatedAt||item.createdAt||'');
    return String(item?.createdAt||item?.updatedAt||item?.dueDate||'');
  }
  function composedTodoStatusLabel(value){return value==='done'?'Uitgevoerd':value==='in_progress'?'In behandeling':'Nog te doen';}
  function composedTodoPriorityLabel(value){return value==='urgent'?'Dringend':value==='low'?'Laag':'Normaal';}
  function composedTodoLinkedRows(snapshot,item){
    const ids=new Set(composedTodoServiceIds(item));if(!ids.size)return [];
    return [...(snapshot?.maintenance||[]),...(snapshot?.breakdowns||[])].filter(record=>ids.has(String(record?.serviceReportId||''))||ids.has(String(record?.serviceVisitId||'')));
  }
  function composedTodoContext(snapshot,item,moment=''){
    const linkedRows=composedTodoLinkedRows(snapshot,item),first=linkedRows[0]||null;
    const device=(snapshot?.devices||[]).find(device=>String(device.id||'')===String(item?.deviceId||''))||(snapshot?.devices||[]).find(device=>String(device.id||'')===String(first?.deviceId||''))||null;
    const location=String(first?.serviceVisitLocation||first?.location||composedLocation(device,moment)||device?.location||'Locatie onbekend').trim()||'Locatie onbekend';
    return {device,location};
  }

  const composedSnapshotWithReportsAndTodosBase=composedSnapshot;
  composedSnapshot=function(deviceIds,reportKeys=[...selectedComposedReports]){
    const snapshot=composedSnapshotWithReportsAndTodosBase(deviceIds,reportKeys),fullDeviceIds=new Set((deviceIds||[]).map(String)),keys=new Set(reportKeys||[]),includedReportIds=new Set();
    [...(snapshot?.maintenance||[]),...(snapshot?.breakdowns||[])].forEach(record=>{
      [record?.serviceReportId,record?.serviceVisitId].filter(Boolean).forEach(id=>includedReportIds.add(String(id)));
    });
    composedSourceReportRows().filter(entry=>keys.has(entry.key)).flatMap(entry=>entry.rows).forEach(row=>{
      const record=row?.item||{};
      [record.serviceReportId,record.serviceVisitId].filter(Boolean).forEach(id=>includedReportIds.add(String(id)));
    });
    const actions=(state.actions||[]).filter(item=>{
      if(!item)return false;
      if(fullDeviceIds.has(String(item.deviceId||'')))return true;
      return includedReportIds.size>0&&composedTodoServiceIds(item).some(id=>includedReportIds.has(id));
    }).map(composedClone);
    return {...snapshot,actions};
  };

  const composedHistoryRowsWithoutTodos=composedHistoryRows;
  composedHistoryRows=function(snapshot){
    const groups=composedHistoryRowsWithoutTodos(snapshot).map(group=>({...group,events:[...(group.events||[])]})),grouped=new Map(groups.map(group=>[composedKey(group.location)||'locatie-onbekend',group]));
    for(const item of (snapshot?.actions||[])){
      const moment=composedTodoMoment(item),ctx=composedTodoContext(snapshot,item,moment),location=ctx.location||'Locatie onbekend',key=composedKey(location)||'locatie-onbekend';
      let group=grouped.get(key);
      if(!group){group={location,events:[]};groups.push(group);grouped.set(key,group);}
      group.events.push({kind:'ToDo',moment,location,rows:[{kind:'ToDo',item,__composedTodo:true}],devices:new Set([ctx.device?composedHistoryDeviceLabel(ctx.device):'ToDo']),technicians:new Set(),todo:item});
    }
    groups.forEach(group=>group.events.sort((a,b)=>String(b.moment||'').localeCompare(String(a.moment||''))));
    return groups.sort((a,b)=>String(b.events[0]?.moment||'').localeCompare(String(a.events[0]?.moment||'')));
  };

  const composedHistoryEventHtmlWithoutTodos=composedHistoryEventHtml;
  composedHistoryEventHtml=function(snapshot,event){
    const item=event?.todo;if(!item)return composedHistoryEventHtmlWithoutTodos(snapshot,event);
    const context=composedTodoContext(snapshot,item,event.moment),deviceLabel=context.device?composedHistoryDeviceLabel(context.device):'ToDo',status=composedTodoStatusLabel(item.status),priority=composedTodoPriorityLabel(item.priority);
    const description=[String(item.title||'ToDo').trim(),String(item.notes||'').trim()].filter(Boolean).join('\n\n');
    const meta=[
      `<span><strong>Status:</strong> ${composedEsc(status)}</span>`,
      `<span><strong>Prioriteit:</strong> ${composedEsc(priority)}</span>`,
      item.assigneeName?`<span><strong>Toegewezen aan:</strong> ${composedEsc(item.assigneeName)}</span>`:'',
      item.dueDate?`<span><strong>Deadline:</strong> ${composedEsc(composedDate(item.dueDate))}</span>`:'',
      item.completedDate?`<span><strong>Afgerond:</strong> ${composedEsc(composedDate(item.completedDate))}</span>`:''
    ].filter(Boolean).join('');
    const serviceIds=composedTodoServiceIds(item),link=serviceIds.length?`<div class="composed-history-work-parts"><strong>Koppeling:</strong> ${serviceIds.length===1?'serviceverslag':'serviceverslagen'}</div>`:'',photos=composedHistoryPhotosHtml(event.rows,'ToDo');
    return `<article class="composed-history-event"><div class="composed-history-event-head"><div><div class="composed-history-event-title"><span class="badge">ToDo</span><strong>${composedEsc(deviceLabel)}</strong></div><div class="composed-history-meta">${meta}</div></div><div class="composed-history-date">${composedEsc(composedDate(event.moment))}</div></div><div class="composed-history-work"><div class="composed-history-work-head">ToDo · ${composedEsc(deviceLabel)}</div><div class="composed-history-work-detail">${composedEsc(description||'ToDo')}</div>${link}</div>${photos}</article>`;
  };
'''
    index = index.replace(anchor, todo_script + '\n' + anchor, 1)

    history_intro = 'Onderhoud, depannages, serviceverslagen en andere relevante registraties · nieuwste gebeurtenis eerst. Foto’s staan bij het bijbehorende verslag.'
    todo_intro = 'Onderhoud, depannages, serviceverslagen, ToDo’s en andere relevante registraties · nieuwste gebeurtenis eerst. Foto’s staan bij het bijbehorende verslag. ToDo-foto’s blijven bij de bijbehorende ToDo.'
    if index.count(history_intro) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x geschiedenisintro voor ToDo-opname, gevonden {index.count(history_intro)}x')
    index = index.replace(history_intro, todo_intro, 1)

    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-head ontbreekt voor ToDo-opname')
    index = index.replace('</head>', f'<meta {TODO_MARKER}>\n</head>', 1)

if HISTORY_CARD_MARKER not in index:
    history_marker = 'data-machinepark-build-fix="composed-history-photos-v1"'
    if history_marker not in index:
        raise SystemExit('Buildvalidatie mislukt: chronologische geschiedenis ontbreekt voor kaderweergave')
    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-head ontbreekt voor kaderweergave')

    card_style = r'''
<style data-machinepark-build-fix="composed-history-cards-v1">
.composed-history-list{display:grid;gap:10px;padding:10px;background:#f5f8f6}
.composed-history-event{margin:0!important;padding:12px 13px!important;border:1px solid #d7e1dc!important;border-radius:12px;background:#fff;box-shadow:0 2px 8px rgba(20,45,38,.05);break-inside:avoid;overflow:hidden}
.composed-history-event:last-child{border-bottom:1px solid #d7e1dc!important}
.composed-history-event-head{padding-bottom:8px;margin-bottom:8px;border-bottom:1px solid #edf1ef}
.composed-history-work{margin-top:8px!important;padding:9px 10px!important;border:1px solid #dce5e1!important;border-radius:10px!important;background:#f9fbfa!important;break-inside:avoid}
.composed-history-work+.composed-history-work{margin-top:8px!important}
@media(max-width:700px){.composed-history-list{gap:8px;padding:8px}.composed-history-event{padding:10px!important}}
@media print{.composed-history-list{gap:3mm;padding:3mm;background:#f7f7f7}.composed-history-event{border:1px solid #bfc9c4!important;border-radius:2mm!important;padding:3mm!important;box-shadow:none!important}.composed-history-event-head{padding-bottom:2mm;margin-bottom:2mm;border-bottom:1px solid #dde3e0}.composed-history-work{border:1px solid #ccd5d1!important;border-radius:2mm!important;padding:2.5mm!important;margin-top:2.5mm!important;background:#fff!important}}
</style>
'''
    index = index.replace('</head>', card_style + f'<meta {HISTORY_CARD_MARKER}>\n</head>', 1)

    anchor = '  function openComposedPreview(doc)'
    if index.count(anchor) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x preview-anker voor kaderweergave, gevonden {index.count(anchor)}x')
    card_script = r'''
  const composedReadablePrintStylesBase=printStyles;
  printStyles=function(){
    return composedReadablePrintStylesBase()+`.composed-history-list{display:grid;gap:3mm;padding:3mm;background:#f7f7f7}.composed-history-event{border:1px solid #bfc9c4!important;border-radius:2mm;padding:3mm!important;margin:0!important;background:#fff;break-inside:avoid}.composed-history-event:last-child{border-bottom:1px solid #bfc9c4!important}.composed-history-event-head{padding-bottom:2mm;margin-bottom:2mm;border-bottom:1px solid #dde3e0}.composed-history-work{border:1px solid #ccd5d1!important;border-radius:2mm;padding:2.5mm!important;margin-top:2.5mm!important;background:#fff}.composed-history-work+.composed-history-work{margin-top:2.5mm!important}`;
  };
'''
    index = index.replace(anchor, card_script + '\n' + anchor, 1)

INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
required = [
    MARKER,
    'function composedSyncVisibleDeviceSelection()',
    "document.querySelectorAll('#composedDeviceBody [data-composed-device]')",
    'if(cb.checked)selectedComposedDevices.add(id)',
    'const composedReportAwareSaveDocument=saveComposedDocument',
    'composedSyncVisibleDeviceSelection();',
    "const saveButton=document.getElementById('composedSaveDocument')",
    'saveButton.onclick=()=>saveComposedDocument()',
    TODO_MARKER,
    'function composedTodoServiceIds(item)',
    'const actions=(state.actions||[]).filter',
    "fullDeviceIds.has(String(item.deviceId||''))",
    'includedReportIds',
    "[...(snapshot?.maintenance||[]),...(snapshot?.breakdowns||[])]",
    "kind:'ToDo'",
    'todo:item',
    'composedHistoryEventHtml=function(snapshot,event)',
    "composedHistoryPhotosHtml(event.rows,'ToDo')",
    'serviceverslagen, ToDo’s',
    'Foto’s staan bij het bijbehorende verslag.',
    HISTORY_CARD_MARKER,
    'composed-history-cards-v1',
    '.composed-history-event{margin:0!important',
    '.composed-history-work+.composed-history-work',
    'const composedReadablePrintStylesBase=printStyles',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: toestel/ToDo/kadertoken ontbreekt: {needle}')

print('[Machinepark] samengesteld document bewaart toestelkeuze, neemt gekoppelde ToDo’s mee en kadert elke geschiedenisgebeurtenis duidelijk af')
