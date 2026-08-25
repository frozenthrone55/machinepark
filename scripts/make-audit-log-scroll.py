from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')
old='''<div id="auditLogStatus" class="muted" style="font-size:12px;margin-bottom:10px">Logboek wordt geladen…</div>\n          <div class="table-wrap"><table class="table" style="min-width:900px">'''
new='''<div id="auditLogStatus" class="muted" style="font-size:12px;margin-bottom:10px">Logboek wordt geladen…</div>\n          <div class="table-wrap" id="auditLogScroll" style="max-height:min(620px,65vh);overflow:auto;overscroll-behavior:contain"><table class="table" style="min-width:900px">'''
if old not in s:
    raise SystemExit('Audit log wrapper niet gevonden')
s=s.replace(old,new,1)

# Zorg dat de tabelkop boven de rijen blijft tijdens scrollen.
css_anchor='.settings-card p{font-size:13px;color:var(--muted);min-height:40px}'
css_new=css_anchor+'#auditLogScroll .table th{position:sticky;top:0;z-index:3;background:#f8faf9}'
if '#auditLogScroll .table th' not in s:
    if css_anchor not in s:
        raise SystemExit('CSS anchor niet gevonden')
    s=s.replace(css_anchor,css_new,1)

s=s.replace('v1.28 • Manuele onderhoudsplanning','v1.29 • Scrollbaar logboek',1)
p.write_text(s,encoding='utf-8')

sw=Path('sw.js')
ws=sw.read_text(encoding='utf-8')
for old_cache in ['machinepark-v1.28-manual-service-dates','machinepark-v1.27-admin-audit']:
    ws=ws.replace(old_cache,'machinepark-v1.29-audit-scroll')
sw.write_text(ws,encoding='utf-8')
