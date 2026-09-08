from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
MARKER = 'data-machinepark-action-timeline="v1"'

index = INDEX.read_text(encoding="utf-8")

if MARKER not in index:
    style = """
<style data-machinepark-action-timeline="v1">
.timeline-item.event-action{border-left:4px solid #4d806e}
.timeline-item.event-action:before{background:#4d806e}
.event-label.action{background:#e8f2ee;color:#245f4b}
.timeline-action-footer{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:8px}
</style>
"""
    if "</head>" not in index:
        raise SystemExit("Buildvalidatie mislukt: </head> ontbreekt voor actie-tijdlijn")
    index = index.replace("</head>", style + "</head>", 1)

    timeline_start = index.find("function deviceUnifiedTimelineHtml(d){")
    timeline_end = index.find("\nfunction deviceMatchesQuery", timeline_start)
    if timeline_start < 0 or timeline_end < 0:
        raise SystemExit("Buildvalidatie mislukt: uniforme machinetijdlijn niet gevonden")
    timeline = index[timeline_start:timeline_end]

    sort_anchor = " events.sort((a,b)=>(b.moment||'').localeCompare(a.moment||''));"
    action_events = """
 (state.actions||[]).filter(a=>a.deviceId===d.id).forEach(a=>{
   const done=a.status==='done',moment=normalizeMoment(done?(a.completedAt||a.completedDate||a.updatedAt):(a.createdAt||a.updatedAt),'00:00');
   const status=done?'Uitgevoerd':a.status==='in_progress'?'In behandeling':'Nog te doen';
   const meta=[];
   if(a.assigneeName)meta.push('Toegewezen aan: '+esc(a.assigneeName));
   if(a.dueDate&&!done)meta.push('Tegen: '+dateFmt(a.dueDate));
   if(done&&a.completedByName)meta.push('Uitgevoerd door: '+esc(a.completedByName));
   if(a.notes)meta.push(esc(a.notes));
   const extra=meta.length?'<p>'+meta.join('<br>')+'</p>':'';
   const html='<div class="event-label action">Actie</div><div class="date">'+dateTimeFmt(moment)+' · '+esc(status)+'</div><strong>'+esc(a.title||'Actie')+'</strong>'+extra+'<div class="timeline-action-footer"><button type="button" class="btn small" data-action-open="'+esc(a.id)+'">Bekijken</button></div>';
   events.push({moment,type:'action',html});
 });
"""
    if "type:'action'" not in timeline:
        if sort_anchor not in timeline:
            raise SystemExit("Buildvalidatie mislukt: sorteeranker machinetijdlijn ontbreekt")
        timeline = timeline.replace(sort_anchor, action_events + sort_anchor, 1)

    legend_old = '<span class="event-label breakdown">Depannage</span><span class="event-label location">Locatiewijziging</span>'
    legend_new = '<span class="event-label breakdown">Depannage</span><span class="event-label action">Actie</span><span class="event-label location">Locatiewijziging</span>'
    if legend_new not in timeline:
        if legend_old not in timeline:
            raise SystemExit("Buildvalidatie mislukt: legenda machinetijdlijn ontbreekt")
        timeline = timeline.replace(legend_old, legend_new, 1)

    index = index[:timeline_start] + timeline + index[timeline_end:]

    summary_start = index.find("  function deviceActionsHtml(deviceId) {")
    summary_end = index.find("\n\n  const baseRenderAll=", summary_start)
    if summary_start < 0 or summary_end < 0:
        raise SystemExit("Buildvalidatie mislukt: apart machine-actieblok niet gevonden")
    summary_replacement = """  function decorateDeviceModal(deviceId) {
    decorateContextModal('device',deviceId);
  }"""
    index = index[:summary_start] + summary_replacement + index[summary_end:]

required = [
    MARKER,
    "type:'action'",
    "event-label action",
    "data-action-open=",
    "decorateContextModal('device',deviceId)",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: actie-tijdlijn ontbreekt ({needle})")
if "function deviceActionsHtml(deviceId)" in index:
    raise SystemExit("Buildvalidatie mislukt: apart machine-actieblok is nog aanwezig")
if "holder.innerHTML=deviceActionsHtml" in index:
    raise SystemExit("Buildvalidatie mislukt: apart actieblok wordt nog in machinedetails geplaatst")

INDEX.write_text(index, encoding="utf-8")
print("[Machinepark] machine-acties geïntegreerd in chronologische tijdlijn; apart actieblok verwijderd")
