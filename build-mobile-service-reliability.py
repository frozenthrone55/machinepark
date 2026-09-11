from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SERVICE = ROOT / "service-visits.js"
MARKER = 'data-machinepark-mobile-service-reliability="v1"'

index = INDEX.read_text(encoding="utf-8")
service = SERVICE.read_text(encoding="utf-8")

# Touchscreens mogen niet eerst in een hover-status terechtkomen. De bestaande
# .btn:hover en .device-card:hover verplaatsen het element 1px; op mobiele
# browsers kan daardoor de eerste tik alleen hover/focus activeren.
if MARKER not in index:
    style_anchor = "</head>"
    style = r"""
<style data-machinepark-mobile-service-reliability="v1">
button,[role="button"],.device-card,.global-search-result,.service-draft-action-choice,.maintenance-machine-title{
  touch-action:manipulation;
  -webkit-tap-highlight-color:rgba(23,63,53,.12);
}
@media (hover:none), (pointer:coarse){
  .btn:hover{transform:none !important;box-shadow:none !important}
  .device-card:hover{transform:none !important}
  .service-action-complete-check:hover{background:#fff !important}
}
</style>
"""
    if style_anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: </head> ontbreekt voor mobiele touch-fix")
    index = index.replace(style_anchor, style + style_anchor, 1)

# Wanneer een serviceconcept opnieuw wordt geopend, combineer de ids uit de
# conceptheader met de werkelijk aan het gereserveerde report-id gekoppelde
# ToDo's. Zo blijft de koppeling behouden als een mobiele autosave net achterliep.
active_old = "linkedActionIds:Array.isArray(header?.linkedActionIds)?header.linkedActionIds:(report&&typeof window.machineparkLinkedActionIdsForService==='function'?window.machineparkLinkedActionIdsForService(report.id):[])"
active_new = "linkedActionIds:[...new Set([...(Array.isArray(header?.linkedActionIds)?header.linkedActionIds:[]),...(typeof window.machineparkLinkedActionIdsForService==='function'?window.machineparkLinkedActionIdsForService(report?.id||header?.draftReportId||''):[])].map(String).filter(Boolean))]"
if active_new not in service:
    if active_old not in service:
        raise SystemExit("Buildvalidatie mislukt: concept-heropenroute voor ToDo-koppeling ontbreekt")
    service = service.replace(active_old, active_new, 1)

# Bij het voltooien van een serviceverslag mag een geldige koppeling nooit
# verdwijnen omdat linkedActionIds uit de conceptheader leeg/verouderd is.
# Neem daarom de unie van de header en de werkelijk opgeslagen koppelingen.
finalize_old = "    const ids=[...new Set((Array.isArray(ctx&&ctx.linkedActionIds)?ctx.linkedActionIds:[]).map(String).filter(Boolean))];"
finalize_new = """    const requestedIds=(Array.isArray(ctx&&ctx.linkedActionIds)?ctx.linkedActionIds:[]).map(String).filter(Boolean);
    const storedIds=typeof linkedActionsForService==='function'?linkedActionsForService(ctx&&ctx.reportId).map(a=>String(a&&a.id||'')).filter(Boolean):[];
    const ids=[...new Set([...requestedIds,...storedIds])];"""
if finalize_new not in index:
    if finalize_old not in index:
        raise SystemExit("Buildvalidatie mislukt: service-finalisatieroute voor ToDo-koppeling ontbreekt")
    index = index.replace(finalize_old, finalize_new, 1)

required_index = [
    MARKER,
    "touch-action:manipulation",
    "@media (hover:none), (pointer:coarse)",
    "const storedIds=typeof linkedActionsForService==='function'?linkedActionsForService(ctx&&ctx.reportId)",
    "const ids=[...new Set([...requestedIds,...storedIds])]",
]
for needle in required_index:
    if needle not in index:
        raise SystemExit("Buildvalidatie mislukt: mobiele servicebetrouwbaarheid ontbreekt (" + needle + ")")

required_service = [
    "window.machineparkLinkedActionIdsForService(report?.id||header?.draftReportId||'')",
    "linkedActionIds:[...new Set([",
]
for needle in required_service:
    if needle not in service:
        raise SystemExit("Buildvalidatie mislukt: concept-koppelherstel ontbreekt (" + needle + ")")

INDEX.write_text(index, encoding="utf-8")
SERVICE.write_text(service, encoding="utf-8")
print("[Machinepark] mobiele tikbediening en service/ToDo conceptroute robuuster gemaakt")
