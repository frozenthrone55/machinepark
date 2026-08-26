from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

old='<div id="clerkUserButton" class="clerk-user-slot clerk-user-single"></div>'
new='''<div class="account-summary" id="accountSummary"><div class="account-copy"><strong id="accountDisplayName">Aangemeld</strong><span id="accountDisplayRole">Gebruiker</span></div><div id="clerkUserButton" class="clerk-user-slot clerk-user-single"></div></div>'''
if old in s:
    s=s.replace(old,new,1)
elif 'id="accountSummary"' not in s:
    raise SystemExit('Clerk accountknop niet gevonden')

css='''
.account-summary{display:flex;align-items:center;gap:9px;min-width:0;margin-left:auto}.account-copy{display:grid;gap:2px;text-align:right;min-width:0}.account-copy strong{font-size:13px;line-height:1.15;max-width:190px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.account-copy span{font-size:11px;line-height:1.15;color:var(--muted);font-weight:750}.clerk-user-slot{flex:0 0 auto}
@media(max-width:700px){.account-summary{gap:7px}.account-copy strong{font-size:11px;max-width:120px}.account-copy span{font-size:10px}}
'''
if '.account-summary{' not in s:
    s=s.replace('</style>',css+'\n</style>',1)

old_role="const currentEmail=String(Clerk.user?.primaryEmailAddress?.emailAddress||Clerk.user?.emailAddresses?.[0]?.emailAddress||'').trim().toLowerCase();const currentRole=String(Clerk.user?.publicMetadata?.role||'').trim().toLowerCase();window.machineparkIsAdmin=currentEmail===window.MACHINEPARK_ADMIN_EMAIL||currentRole==='beheerder';"
new_role=old_role+"const accountName=document.getElementById('accountDisplayName'),accountRole=document.getElementById('accountDisplayRole');const currentName=String(Clerk.user?.fullName||[Clerk.user?.firstName,Clerk.user?.lastName].filter(Boolean).join(' ')||Clerk.user?.username||currentEmail||'Gebruiker').trim();if(accountName)accountName.textContent=currentName;if(accountRole)accountRole.textContent=window.machineparkIsAdmin?'Beheerder':'Gebruiker';"
if old_role in s and "accountDisplayName" not in s[s.find(old_role):s.find(old_role)+1200]:
    s=s.replace(old_role,new_role,1)
elif "accountRole.textContent=window.machineparkIsAdmin?'Beheerder':'Gebruiker'" not in s:
    raise SystemExit('Clerk rollogica niet gevonden')

for old_version in ['v1.37 • Extra onderhoudstypes','v1.36 • Mobiel & fotovergroting','v1.35 • Zoeken per tabblad','v1.34 • Onderdelenmerken apart']:
    s=s.replace(old_version,'v1.38 • Accountnaam & rol',1)
p.write_text(s,encoding='utf-8')

sw=Path('sw.js')
ws=sw.read_text(encoding='utf-8')
for old_cache in ['machinepark-v1.37-maintenance-types','machinepark-v1.36-mobile-photo','machinepark-v1.35-search-per-view','machinepark-v1.34-parts-machine-separate']:
    ws=ws.replace(old_cache,'machinepark-v1.38-account-summary')
sw.write_text(ws,encoding='utf-8')
