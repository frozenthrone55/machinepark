from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

old="function maintenanceMatchesQuery(m){if(!state.query)return true;const moment=recordMoment(m);return searchIncludes([m.type,m.date,m.time,recordDateTimeFmt(m),m.technician,m.notes,linkedDeviceSearchText(m.deviceId,moment),linkedPartsSearchText(m.usedParts)].join(' '))}\nfunction breakdownMatchesQuery(b){if(!state.query)return true;const moment=recordMoment(b);return searchIncludes([b.date,b.time,recordDateTimeFmt(b),b.issue,b.diagnosis,b.solution,b.technician,b.priority,b.status,linkedDeviceSearchText(b.deviceId,moment),linkedPartsSearchText(b.usedParts)].join(' '))}"
new="function searchDeviceIsActive(deviceId){const d=state.devices.find(x=>x.id===deviceId);return !d||d.status!=='Buiten dienst'}\nfunction maintenanceMatchesQuery(m){if(!state.query)return true;if(!searchDeviceIsActive(m.deviceId))return false;const moment=recordMoment(m);return searchIncludes([m.type,m.date,m.time,recordDateTimeFmt(m),m.technician,m.notes,linkedDeviceSearchText(m.deviceId,moment),linkedPartsSearchText(m.usedParts)].join(' '))}\nfunction breakdownMatchesQuery(b){if(!state.query)return true;if(!searchDeviceIsActive(b.deviceId))return false;const moment=recordMoment(b);return searchIncludes([b.date,b.time,recordDateTimeFmt(b),b.issue,b.diagnosis,b.solution,b.technician,b.priority,b.status,linkedDeviceSearchText(b.deviceId,moment),linkedPartsSearchText(b.usedParts)].join(' '))}"
if old not in s:
    raise SystemExit('Zoekhelpers niet gevonden')
s=s.replace(old,new,1)

old2="const deviceMatches=state.devices.filter(deviceMatchesQuery).slice(0,7);"
new2="const deviceMatches=state.devices.filter(d=>(state.view==='devices'||d.status!=='Buiten dienst')&&deviceMatchesQuery(d)).slice(0,7);"
if old2 not in s:
    raise SystemExit('Globale toestelzoeker niet gevonden')
s=s.replace(old2,new2,1)

p.write_text(s,encoding='utf-8')

sw=Path('sw.js')
ws=sw.read_text(encoding='utf-8')
ws=ws.replace("machinepark-v1.25-search","machinepark-v1.26-search-active")
sw.write_text(ws,encoding='utf-8')
