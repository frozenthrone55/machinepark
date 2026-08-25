from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')
old='<div class="top-actions"><div class="search"><span>⌕</span><input id="globalSearch" autocomplete="off" placeholder="Zoek overal in Machinepark…" /><div id="globalSearchResults" class="global-search-results" role="listbox" aria-label="Zoekresultaten"></div></div><button class="btn primary" id="quickAdd">+ Nieuw</button></div><div id="clerkUserButton" class="clerk-user-slot clerk-user-single"></div>'
new='<div class="top-actions"><div class="search"><span>⌕</span><input id="globalSearch" autocomplete="off" placeholder="Zoek overal in Machinepark…" /><div id="globalSearchResults" class="global-search-results" role="listbox" aria-label="Zoekresultaten"></div></div></div><div id="clerkUserButton" class="clerk-user-slot clerk-user-single"></div>'
if old not in s:
    raise SystemExit('Bovenste + Nieuw knop niet gevonden')
s=s.replace(old,new,1)
handler="$('#quickAdd').onclick=()=>({dashboard:openDevice,devices:openDevice,maintenance:openMaintenance,breakdowns:openBreakdown,parts:openPart,settings:openDevice}[state.view]||openDevice)();"
if handler not in s:
    raise SystemExit('quickAdd handler niet gevonden')
s=s.replace(handler,'',1)
s=s.replace('v1.31 • Rollenbeheer','v1.32 • Vereenvoudigde acties',1)
p.write_text(s,encoding='utf-8')

sw=Path('sw.js')
ws=sw.read_text(encoding='utf-8')
ws=ws.replace('machinepark-v1.31-role-management','machinepark-v1.32-simplified-actions')
sw.write_text(ws,encoding='utf-8')
