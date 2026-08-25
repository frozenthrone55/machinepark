from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

repls=[
("nextHalf:val(fd,'nextHalf')||(install?addMonths(install,6):''),nextAnnual:val(fd,'nextAnnual')||(install?addMonths(install,12):'')",
 "nextHalf:val(fd,'nextHalf'),nextAnnual:val(fd,'nextAnnual')"),
("nextHalf:install?addMonths(install,6):'',nextAnnual:install?addMonths(install,12):''",
 "nextHalf:'',nextAnnual:''"),
("status,nextHalf:date?addMonths(date,6):'',nextAnnual:date?addMonths(date,12):'',notes:''",
 "status,nextHalf:'',nextAnnual:'',notes:''"),
("const hasHalf=state.maintenance.some(m=>m.deviceId===old.id&&m.type==='Halfjaarlijks'&&m.date),hasAnnual=state.maintenance.some(m=>m.deviceId===old.id&&m.type==='Jaarlijks'&&m.date);let nextHalf=old.nextHalf||'',nextAnnual=old.nextAnnual||'';if(r.installChanged&&!hasHalf)nextHalf=installDate?addMonths(installDate,6):'';if(r.installChanged&&!hasAnnual)nextAnnual=installDate?addMonths(installDate,12):'';",
 "let nextHalf=old.nextHalf||'',nextAnnual=old.nextAnnual||'';"),
("await put('maintenance',m);const affected=new Set();if(old.id){affected.add((old.deviceId||'')+'|'+(old.type||''))}affected.add(m.deviceId+'|'+m.type);for(const key of affected){const [deviceId,type]=key.split('|');if(deviceId&&type)await recalcNextMaintenance(deviceId,type)}closeModal();",
 "await put('maintenance',m);closeModal();")
]

for old,new in repls:
    if old not in s:
        raise SystemExit('Verwacht codefragment niet gevonden: '+old[:80])
    s=s.replace(old,new,1)

# Houd de functie aanwezig voor compatibiliteit, maar laat ze niet automatisch aanroepen.
s=s.replace('v1.27 • Rollen & logboek','v1.28 • Manuele onderhoudsplanning',1)

p.write_text(s,encoding='utf-8')

sw=Path('sw.js')
ws=sw.read_text(encoding='utf-8')
for old in ['machinepark-v1.27-admin-audit','machinepark-v1.26-search-active']:
    ws=ws.replace(old,'machinepark-v1.28-manual-service-dates')
sw.write_text(ws,encoding='utf-8')
