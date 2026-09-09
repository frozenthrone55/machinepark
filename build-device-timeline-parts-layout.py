from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
index = INDEX.read_text(encoding="utf-8")

helper_anchor = "function deviceUnifiedTimelineHtml(d){"
helper = """function deviceTimelineUsedPartsHtml(items=[]){
 if(!Array.isArray(items)||!items.length)return '';
 return '<div class="device-timeline-used-parts"><strong>Onderdelen:</strong><div class="device-timeline-used-parts-list">'+items.map(item=>'<div class="device-timeline-used-part">• '+esc(partName(item.partId))+' × '+esc(String(item.qty??''))+'</div>').join('')+'</div></div>'
}
"""
if "function deviceTimelineUsedPartsHtml(items=[])" not in index:
    if helper_anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: deviceUnifiedTimelineHtml niet gevonden")
    index = index.replace(helper_anchor, helper + helper_anchor, 1)

maintenance_old = """<p>${esc(m.notes||'Geen notitie')}${m.usedParts?.length?'<br>Onderdelen: '+esc(usedPartsText(m.usedParts)):''}</p>"""
maintenance_new = """<p>${esc(m.notes||'Geen notitie')}</p>${m.usedParts?.length?deviceTimelineUsedPartsHtml(m.usedParts):''}"""
if maintenance_new not in index:
    if maintenance_old not in index:
        raise SystemExit("Buildvalidatie mislukt: onderhoudsonderdelen in machinelogboek niet gevonden")
    index = index.replace(maintenance_old, maintenance_new, 1)

breakdown_old = """if(b.usedParts?.length)extras.push('Onderdelen: '+esc(usedPartsText(b.usedParts)));events.push"""
breakdown_new = """const partsHtml=b.usedParts?.length?deviceTimelineUsedPartsHtml(b.usedParts):'';events.push"""
if breakdown_new not in index:
    if breakdown_old not in index:
        raise SystemExit("Buildvalidatie mislukt: depannageonderdelen in machinelogboek niet gevonden")
    index = index.replace(breakdown_old, breakdown_new, 1)

breakdown_html_old = """<p>${extras.join('<br>')}</p>${workOrderTimelineHtml(b.workOrder)}"""
breakdown_html_new = """<p>${extras.join('<br>')}</p>${partsHtml}${workOrderTimelineHtml(b.workOrder)}"""
if breakdown_html_new not in index:
    if breakdown_html_old not in index:
        raise SystemExit("Buildvalidatie mislukt: depannage-timeline HTML niet gevonden")
    index = index.replace(breakdown_html_old, breakdown_html_new, 1)

style = """
<style data-machinepark-device-timeline-parts="v1">
.device-timeline-used-parts{margin-top:8px}
.device-timeline-used-parts>strong{display:block;margin-bottom:4px}
.device-timeline-used-parts-list{display:flex;flex-direction:column;gap:3px}
.device-timeline-used-part{display:block;font-size:14px;line-height:1.35;overflow-wrap:anywhere}
</style>
"""
if 'data-machinepark-device-timeline-parts="v1"' not in index:
    if "</head>" not in index:
        raise SystemExit("Buildvalidatie mislukt: </head> ontbreekt")
    index = index.replace("</head>", style + "</head>", 1)

for needle in [
    "deviceTimelineUsedPartsHtml",
    "device-timeline-used-parts-list",
    "m.usedParts?.length?deviceTimelineUsedPartsHtml(m.usedParts)",
    "b.usedParts?.length?deviceTimelineUsedPartsHtml(b.usedParts)",
]:
    if needle not in index:
        raise SystemExit("Buildvalidatie mislukt: onderdelenopmaak ontbreekt (" + needle + ")")

INDEX.write_text(index, encoding="utf-8")
print("[Machinepark] gebruikte onderdelen in Machinedetails & logboek onder elkaar gezet")
