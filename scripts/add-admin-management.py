from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

# 1. Beheerknop herkenbaar maken en versie bijwerken.
s=s.replace('<button type="button" data-view="settings" onclick="switchView(\'settings\')"><span class="icon">⚙</span><span class="label">Beheer</span></button>',
            '<button type="button" id="adminNavSettings" data-view="settings" onclick="switchView(\'settings\')"><span class="icon">⚙</span><span class="label">Beheer</span></button>',1)
s=s.replace('v1.23 • Cloud sync','v1.27 • Rollen & logboek',1)
s=s.replace('.nav{grid-template-columns:repeat(6,1fr);', '.nav{grid-template-columns:repeat(var(--mobile-nav-count,6),1fr);',1)

# 2. Gebruikersbeheer en logboek bovenaan Beheer toevoegen.
anchor='''    <section class="view" id="view-settings">\n      <div class="settings-grid">'''
admin_cards='''    <section class="view" id="view-settings">\n      <div class="settings-grid">\n        <div class="settings-card" id="userManagementCard" style="grid-column:1/-1">\n          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap">\n            <div><h4>Gebruikersbeheer</h4><p style="min-height:0;margin-bottom:10px">Alleen zichtbaar voor de beheerder. <strong>kriskoffieapp@telenet.be</strong> is beheerder; alle andere accounts hebben de rol gebruiker.</p></div>\n            <button class="btn small" type="button" id="refreshUsers">Vernieuwen</button>\n          </div>\n          <form id="inviteUserForm" style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 14px">\n            <input id="inviteUserEmail" type="email" required placeholder="E-mailadres nieuwe gebruiker" style="flex:1;min-width:240px;border:1px solid var(--line);border-radius:10px;padding:10px 11px">\n            <button class="btn primary" type="submit">Gebruiker uitnodigen</button>\n          </form>\n          <div id="userManagementStatus" class="muted" style="font-size:12px;margin-bottom:10px">Gebruikers worden geladen…</div>\n          <div class="table-wrap"><table class="table" style="min-width:720px"><thead><tr><th>Gebruiker</th><th>Rol</th><th>Laatst aangemeld</th><th></th></tr></thead><tbody id="userManagementBody"></tbody></table></div>\n          <div id="pendingInvitations" style="margin-top:14px"></div>\n        </div>\n        <div class="settings-card" id="auditLogCard" style="grid-column:1/-1">\n          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap">\n            <div><h4>Wijzigingslogboek</h4><p style="min-height:0;margin-bottom:10px">Beheerder-only overzicht van <strong>wie</strong>, <strong>wat</strong> en <strong>wanneer</strong> er iets in Machinepark heeft gewijzigd.</p></div>\n            <button class="btn small" type="button" id="refreshAuditLog">Vernieuwen</button>\n          </div>\n          <div id="auditLogStatus" class="muted" style="font-size:12px;margin-bottom:10px">Logboek wordt geladen…</div>\n          <div class="table-wrap"><table class="table" style="min-width:900px"><thead><tr><th>Wanneer</th><th>Wie</th><th>Wat</th><th>Wijziging</th></tr></thead><tbody id="auditLogBody"></tbody></table></div>\n        </div>'''
if anchor not in s:
    raise SystemExit('Beheer sectie niet gevonden')
s=s.replace(anchor,admin_cards,1)

# 3. Adminconfig en servercalls toevoegen bij centrale sync.
central_anchor="const CENTRAL_SYNC_URL='/.netlify/functions/machinepark-data';"
admin_js=r'''window.MACHINEPARK_ADMIN_EMAIL='kriskoffieapp@telenet.be';
window.machineparkIsAdmin=false;
const USER_MANAGEMENT_URL='/.netlify/functions/user-management';
const AUDIT_LOG_URL='/.netlify/functions/audit-log';
function clerkCurrentEmail(){return String(window.Clerk?.user?.primaryEmailAddress?.emailAddress||window.Clerk?.user?.emailAddresses?.[0]?.emailAddress||'').trim().toLowerCase()}
function applyMachineparkRoleAccess(){const admin=Boolean(window.machineparkIsAdmin);const nav=document.getElementById('adminNavSettings');if(nav)nav.style.display=admin?'':'none';document.documentElement.style.setProperty('--mobile-nav-count',admin?'6':'5');if(!admin&&state.view==='settings')switchView('dashboard')}
window.applyMachineparkRoleAccess=applyMachineparkRoleAccess;
function adminDateFmt(value){if(!value)return '—';let v=value;if(typeof v==='string'&&/^\d+$/.test(v))v=Number(v);const d=new Date(v);return Number.isNaN(d.getTime())?'—':d.toLocaleString('nl-BE',{dateStyle:'short',timeStyle:'short'})}
async function adminFetch(url,options={}){if(!window.machineparkIsAdmin)throw new Error('Alleen de beheerder heeft toegang.');const hasBody=options.body!==undefined;const headers=await centralHeaders(hasBody);const res=await fetch(url,{...options,headers:{...headers,...(options.headers||{})},cache:'no-store'});let body=null;try{body=await res.json()}catch(_){body={}}if(!res.ok)throw new Error(body?.error||`Beheeractie mislukt (${res.status})`);return body}
async function loadUserManagement(){if(!window.machineparkIsAdmin)return;const status=$('#userManagementStatus'),body=$('#userManagementBody'),pending=$('#pendingInvitations');if(status)status.textContent='Gebruikers worden geladen…';try{const data=await adminFetch(USER_MANAGEMENT_URL);if(status)status.textContent=`${data.users.length} account(s) · beheerder: ${data.adminEmail}`;if(body)body.innerHTML=data.users.length?data.users.map(u=>`<tr><td><strong>${esc(u.fullName||u.email||'Gebruiker')}</strong><br><span class="muted">${esc(u.email||'—')}</span></td><td>${u.role==='beheerder'?'<span class="badge success">Beheerder</span>':'<span class="badge gray">Gebruiker</span>'}</td><td>${adminDateFmt(u.lastSignInAt)}</td><td>${u.role==='beheerder'?'<span class="muted">Vast beheerderaccount</span>':`<button class="btn small danger" type="button" data-remove-user="${u.id}" data-remove-user-email="${esc(u.email||'')}">Verwijder</button>`}</td></tr>`).join(''):'<tr><td colspan="4"><div class="empty">Geen gebruikers gevonden.</div></td></tr>';if(pending){const list=data.invitations||[];pending.innerHTML=list.length?`<div class="section-title">Openstaande uitnodigingen</div><div class="table-wrap"><table class="table" style="min-width:620px"><thead><tr><th>E-mail</th><th>Uitgenodigd</th><th></th></tr></thead><tbody>${list.map(i=>`<tr><td><strong>${esc(i.email)}</strong></td><td>${adminDateFmt(i.createdAt)}</td><td><button class="btn small" type="button" data-revoke-invite="${i.id}" data-revoke-email="${esc(i.email)}">Intrekken</button></td></tr>`).join('')}</tbody></table></div>`:''}bindRenderedAdminActions()}catch(e){console.error(e);if(status)status.textContent='Gebruikersbeheer kon niet worden geladen: '+e.message;if(body)body.innerHTML='<tr><td colspan="4"><div class="empty">Gebruikersbeheer niet beschikbaar.</div></td></tr>'}}
function bindRenderedAdminActions(){$$('[data-remove-user]').forEach(btn=>btn.onclick=async()=>{const email=btn.dataset.removeUserEmail||'deze gebruiker';if(!confirm(`Gebruiker ${email} verwijderen?`))return;btn.disabled=true;try{await adminFetch(USER_MANAGEMENT_URL,{method:'DELETE',body:JSON.stringify({userId:btn.dataset.removeUser})});toast('Gebruiker verwijderd');await Promise.all([loadUserManagement(),loadAuditLog()])}catch(e){alert(e.message);btn.disabled=false}});$$('[data-revoke-invite]').forEach(btn=>btn.onclick=async()=>{const email=btn.dataset.revokeEmail||'deze uitnodiging';if(!confirm(`Uitnodiging voor ${email} intrekken?`))return;btn.disabled=true;try{await adminFetch(USER_MANAGEMENT_URL,{method:'POST',body:JSON.stringify({action:'revoke-invitation',invitationId:btn.dataset.revokeInvite})});toast('Uitnodiging ingetrokken');await Promise.all([loadUserManagement(),loadAuditLog()])}catch(e){alert(e.message);btn.disabled=false}})}
function auditDetails(change){const f=change.fields||[];if(!f.length)return `${esc(change.entityType||'Item')} ${esc(change.action||'gewijzigd')}`;return f.slice(0,6).map(x=>`<div><strong>${esc(x.field)}:</strong> ${esc(x.before)} → ${esc(x.after)}</div>`).join('')+(f.length>6?`<div class="muted">+ ${f.length-6} andere wijziging(en)</div>`:'')}
async function loadAuditLog(){if(!window.machineparkIsAdmin)return;const status=$('#auditLogStatus'),body=$('#auditLogBody');if(status)status.textContent='Logboek wordt geladen…';try{const data=await adminFetch(AUDIT_LOG_URL);const rows=[];(data.entries||[]).forEach(entry=>(entry.changes||[]).forEach(change=>rows.push({entry,change})));if(status)status.textContent=`${rows.length} wijziging(en) uit de meest recente logboekregels`;if(body)body.innerHTML=rows.length?rows.map(({entry,change})=>`<tr><td class="nowrap">${adminDateFmt(entry.at)}</td><td><strong>${esc(entry.userName||entry.userEmail||'Gebruiker')}</strong>${entry.userName&&entry.userEmail?`<br><span class="muted">${esc(entry.userEmail)}</span>`:''}</td><td><strong>${esc(change.entityType||'Item')}</strong><br><span class="muted">${esc(change.entityLabel||'')}</span></td><td><span class="badge ${change.action==='verwijderd'?'danger':change.action==='toegevoegd'||change.action==='uitgenodigd'?'success':'gray'}">${esc(change.action||'gewijzigd')}</span><div style="margin-top:6px;font-size:12px;line-height:1.5">${auditDetails(change)}</div></td></tr>`).join(''):'<tr><td colspan="4"><div class="empty">Nog geen wijzigingen gelogd. Nieuwe wijzigingen verschijnen hier automatisch.</div></td></tr>'}catch(e){console.error(e);if(status)status.textContent='Logboek kon niet worden geladen: '+e.message;if(body)body.innerHTML='<tr><td colspan="4"><div class="empty">Logboek niet beschikbaar.</div></td></tr>'}}
async function loadAdminPanels(){if(!window.machineparkIsAdmin)return;await Promise.all([loadUserManagement(),loadAuditLog()])}
'''
if central_anchor not in s:
    raise SystemExit('Centrale sync anchor niet gevonden')
s=s.replace(central_anchor,central_anchor+'\n'+admin_js,1)

# 4. Beheer blokkeren voor gewone gebruikers en adminpanels laden bij openen.
old_switch="function switchView(view){state.view=view;$$('.view').forEach(v=>v.classList.remove('active'));$('#view-'+view).classList.add('active');$$('.nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));const [t,s]=pageMeta(view);$('#pageTitle').textContent=t;$('#pageSubtitle').textContent=s;renderAll()}"
new_switch="function switchView(view){if(view==='settings'&&!window.machineparkIsAdmin)view='dashboard';state.view=view;$$('.view').forEach(v=>v.classList.remove('active'));$('#view-'+view).classList.add('active');$$('.nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));const [t,s]=pageMeta(view);$('#pageTitle').textContent=t;$('#pageSubtitle').textContent=s;renderAll();if(view==='settings'&&window.machineparkIsAdmin)loadAdminPanels()}"
if old_switch not in s:
    raise SystemExit('switchView niet gevonden')
s=s.replace(old_switch,new_switch,1)

# 5. Admin event handlers aan bind() toevoegen.
old_bind="$('#clearAll').onclick=clearAll;['deviceStatusFilter','maintenanceTypeFilter','breakdownStatusFilter','breakdownPriorityFilter','partStockFilter'].forEach(id=>$('#'+id).onchange=renderAll);"
new_bind="$('#clearAll').onclick=clearAll;const inviteForm=$('#inviteUserForm');if(inviteForm)inviteForm.onsubmit=async e=>{e.preventDefault();if(!window.machineparkIsAdmin)return;const input=$('#inviteUserEmail'),email=String(input?.value||'').trim().toLowerCase();if(!email)return;const submit=e.target.querySelector('button[type=submit]');if(submit)submit.disabled=true;try{await adminFetch(USER_MANAGEMENT_URL,{method:'POST',body:JSON.stringify({action:'invite',email})});if(input)input.value='';toast('Uitnodiging verstuurd');await Promise.all([loadUserManagement(),loadAuditLog()])}catch(err){alert(err.message)}finally{if(submit)submit.disabled=false}};const refreshUsers=$('#refreshUsers');if(refreshUsers)refreshUsers.onclick=()=>loadUserManagement();const refreshAudit=$('#refreshAuditLog');if(refreshAudit)refreshAudit.onclick=()=>loadAuditLog();['deviceStatusFilter','maintenanceTypeFilter','breakdownStatusFilter','breakdownPriorityFilter','partStockFilter'].forEach(id=>$('#'+id).onchange=renderAll);"
if old_bind not in s:
    raise SystemExit('bind anchor niet gevonden')
s=s.replace(old_bind,new_bind,1)

# 6. Clerk login bepaalt de rol voor de UI vóór de app start.
old_auth="""      if(shell)shell.style.display='block';\n      if(!userButtonsMounted){"""
new_auth="""      if(shell)shell.style.display='block';\n      window.machineparkIsAdmin=String(Clerk.user?.primaryEmailAddress?.emailAddress||Clerk.user?.emailAddresses?.[0]?.emailAddress||'').trim().toLowerCase()===window.MACHINEPARK_ADMIN_EMAIL;\n      if(typeof window.applyMachineparkRoleAccess==='function')window.applyMachineparkRoleAccess();\n      if(!userButtonsMounted){"""
if old_auth not in s:
    raise SystemExit('Clerk signed-in anchor niet gevonden')
s=s.replace(old_auth,new_auth,1)

old_signout="""    }else{\n      if(shell)shell.style.display='none';"""
new_signout="""    }else{\n      window.machineparkIsAdmin=false;\n      if(typeof window.applyMachineparkRoleAccess==='function')window.applyMachineparkRoleAccess();\n      if(shell)shell.style.display='none';"""
if old_signout not in s:
    raise SystemExit('Clerk signed-out anchor niet gevonden')
s=s.replace(old_signout,new_signout,1)

required=['id="adminNavSettings"','id="userManagementCard"','id="auditLogCard"','window.MACHINEPARK_ADMIN_EMAIL','function loadUserManagement()','function loadAuditLog()','machineparkIsAdmin']
missing=[x for x in required if x not in s]
if missing:
    raise SystemExit('Adminpatch onvolledig: '+', '.join(missing))

p.write_text(s,encoding='utf-8')

sw=Path('sw.js')
ws=sw.read_text(encoding='utf-8')
for old in ['machinepark-v1.26-search-active','machinepark-v1.25-search','machinepark-v1.24-brand']:
    ws=ws.replace(old,'machinepark-v1.27-admin-audit')
sw.write_text(ws,encoding='utf-8')
