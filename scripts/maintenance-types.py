from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

old_filter='<select id="maintenanceTypeFilter" class="filter"><option value="">Alle types</option><option>Halfjaarlijks</option><option>Jaarlijks</option></select>'
new_filter='<select id="maintenanceTypeFilter" class="filter"><option value="">Alle types</option><option>Halfjaarlijks</option><option>Jaarlijks</option><option>Op afroep</option><option>Maandelijks</option></select>'
if old_filter in s:
    s=s.replace(old_filter,new_filter,1)
elif new_filter not in s:
    raise SystemExit('Onderhoudsfilter niet gevonden')

old_types="['Halfjaarlijks','Jaarlijks']"
new_types="['Halfjaarlijks','Jaarlijks','Op afroep','Maandelijks']"
if old_types in s:
    s=s.replace(old_types,new_types,1)
elif new_types not in s:
    raise SystemExit('Onderhoudstypes in formulier niet gevonden')

for old in ['v1.36 • Mobiel & fotovergroting','v1.35 • Zoeken per tabblad','v1.34 • Onderdelenmerken apart']:
    s=s.replace(old,'v1.37 • Extra onderhoudstypes',1)

p.write_text(s,encoding='utf-8')

sw=Path('sw.js')
ws=sw.read_text(encoding='utf-8')
for old in ['machinepark-v1.36-mobile-photo','machinepark-v1.35-search-per-view','machinepark-v1.34-parts-machine-separate']:
    ws=ws.replace(old,'machinepark-v1.37-maintenance-types')
sw.write_text(ws,encoding='utf-8')
