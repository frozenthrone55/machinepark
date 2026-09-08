from pathlib import Path
from hashlib import sha256
import re

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SERVICE = ROOT / "service-visits.js"

index = INDEX.read_text(encoding="utf-8")
service = SERVICE.read_text(encoding="utf-8")

helper_anchor = "  function serviceReportDeleteImpact(report) {"
helper = """  function serviceReportLinkedActions(reportId) {
    const id=String(reportId||'');
    return (state.actions||[]).filter(action=>{
      const ids=Array.isArray(action?.serviceReportIds)?action.serviceReportIds.map(String):[];
      const links=Array.isArray(action?.serviceLinks)?action.serviceLinks:[];
      return ids.includes(id)||links.some(link=>String(link?.id||'')===id)||(action?.sourceKind==='service-report'&&String(action?.sourceId||'')===id);
    });
  }

"""
if "function serviceReportLinkedActions(reportId)" not in service:
    if helper_anchor not in service:
        raise SystemExit("Buildvalidatie mislukt: serviceReportDeleteImpact ontbreekt")
    service = service.replace(helper_anchor, helper + helper_anchor, 1)

start = service.find("  function deleteServiceReportAtomic(report) {")
end = service.find("\n  async function deleteServiceReport(id) {", start)
if start < 0 or end < 0:
    raise SystemExit("Buildvalidatie mislukt: deleteServiceReportAtomic niet gevonden")
block = service[start:end]

action_anchor = "      let tr;"
action_code = """      const reportId=String(report.id),actionUpdates=serviceReportLinkedActions(reportId).map(action=>{
        const serviceReportIds=(Array.isArray(action.serviceReportIds)?action.serviceReportIds:[]).map(String).filter(id=>id!==reportId);
        const serviceLinks=(Array.isArray(action.serviceLinks)?action.serviceLinks:[]).filter(link=>String(link?.id||'')!==reportId);
        const sourceLinked=action.sourceKind==='service-report'&&String(action.sourceId||'')===reportId;
        const history=[...(Array.isArray(action.history)?action.history:[]),{id:uid('actlog'),at:now,type:'unlinked',label:'Serviceverslag verwijderd',detail:'Servicekoppeling automatisch verwijderd'}].slice(-120);
        return sourceLinked
          ? {...action,serviceReportIds,serviceLinks,sourceKind:'',sourceId:'',sourceLabel:'',updatedAt:now,history}
          : {...action,serviceReportIds,serviceLinks,updatedAt:now,history};
      });
"""
if "actionUpdates=serviceReportLinkedActions(reportId).map" not in block:
    if action_anchor not in block:
        raise SystemExit("Buildvalidatie mislukt: transactieanker voor actie-opruiming ontbreekt")
    block = block.replace(action_anchor, action_code + action_anchor, 1)

old_tr = "try{tr=db.transaction(['maintenance','breakdowns','parts'],'readwrite');}"
new_tr = "try{tr=db.transaction(['maintenance','breakdowns','parts','actions'],'readwrite');}"
if new_tr not in block:
    if old_tr not in block:
        raise SystemExit("Buildvalidatie mislukt: service-delete transactie ontbreekt")
    block = block.replace(old_tr, new_tr, 1)

old_stores = "const ms=tr.objectStore('maintenance'),bs=tr.objectStore('breakdowns'),ps=tr.objectStore('parts');"
new_stores = "const ms=tr.objectStore('maintenance'),bs=tr.objectStore('breakdowns'),ps=tr.objectStore('parts'),as=tr.objectStore('actions');"
if new_stores not in block:
    if old_stores not in block:
        raise SystemExit("Buildvalidatie mislukt: service-delete objectstores ontbreken")
    block = block.replace(old_stores, new_stores, 1)

old_put = "updates.forEach(part=>ps.put(part));"
new_put = "updates.forEach(part=>ps.put(part));actionUpdates.forEach(action=>as.put(action));"
if new_put not in block:
    if old_put not in block:
        raise SystemExit("Buildvalidatie mislukt: service-delete action update-anker ontbreekt")
    block = block.replace(old_put, new_put, 1)

old_resolve = "tr.oncomplete=()=>{scheduleCentralSync();resolve(impact);};"
new_resolve = "tr.oncomplete=()=>{scheduleCentralSync();resolve({...impact,actionUnlinked:actionUpdates.length});};"
if new_resolve not in block:
    if old_resolve not in block:
        raise SystemExit("Buildvalidatie mislukt: service-delete resolve ontbreekt")
    block = block.replace(old_resolve, new_resolve, 1)

service = service[:start] + block + service[end:]

required = [
    "serviceReportLinkedActions(reportId)",
    "actionUpdates=serviceReportLinkedActions(reportId).map",
    "['maintenance','breakdowns','parts','actions']",
    "serviceReportIds,serviceLinks,sourceKind:'',sourceId:'',sourceLabel:''",
    "Serviceverslag verwijderd",
    "actionUnlinked",
]
for needle in required:
    if needle not in service:
        raise SystemExit("Buildvalidatie mislukt: service-actie-opruiming ontbreekt (" + needle + ")")

service_version = sha256(service.encode("utf-8")).hexdigest()[:12]
pattern = r'(service-visits\.js\?v=)[^"\'\s>]+'
index, count = re.subn(pattern, lambda match: match.group(1) + service_version, index, count=1)
if count != 1:
    raise SystemExit("Buildvalidatie mislukt: service-visits cacheversie niet gevonden")

SERVICE.write_text(service, encoding="utf-8")
INDEX.write_text(index, encoding="utf-8")
print("[Machinepark] verwijderen serviceverslag ruimt gekoppelde acties atomair op")
