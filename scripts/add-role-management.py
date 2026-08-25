from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

s=s.replace(
    'Alleen zichtbaar voor de beheerder. <strong>kriskoffieapp@telenet.be</strong> is beheerder; alle andere accounts hebben de rol gebruiker.',
    'Alleen zichtbaar voor beheerders. <strong>kriskoffieapp@telenet.be</strong> blijft de vaste hoofdbeheerder. Andere accounts kunnen de rol <strong>Gebruiker</strong> of <strong>Beheerder</strong> krijgen.',
    1
)

s=s.replace(
    "window.machineparkAdminUsers=data.users||[];if(status)status.textContent=`${data.users.length} account(s) · beheerder: ${data.adminEmail}`;",
    "window.machineparkAdminUsers=data.users||[];window.machineparkCurrentAdminUserId=data.currentUserId||'';if(status)status.textContent=`${data.users.length} account(s) · vaste hoofdbeheerder: ${data.adminEmail}`;",
    1
)

old_action='''<td><div style="display:flex;gap:7px;align-items:center;flex-wrap:wrap"><button class="btn small" type="button" data-edit-user="${u.id}">Bewerk</button>${u.role==='beheerder'?'<span class="muted">Vast beheerderaccount</span>':`<button class="btn small danger" type="button" data-remove-user="${u.id}" data-remove-user-email="${esc(u.email||'')}">Verwijder</button>`}</div></td>'''
new_action='''<td><div style="display:flex;gap:7px;align-items:center;flex-wrap:wrap"><button class="btn small" type="button" data-edit-user="${u.id}">Bewerk</button>${u.isOwner?'<span class="muted">Vaste hoofdbeheerder</span>':`<button class="btn small danger" type="button" data-remove-user="${u.id}" data-remove-user-email="${esc(u.email||'')}">Verwijder</button>`}</div></td>'''
if old_action not in s:
    raise SystemExit('Actiekolom gebruikers niet gevonden')
s=s.replace(old_action,new_action,1)

start=s.find('function openUserEditor(userId){')
end=s.find('\nfunction bindRenderedAdminActions()', start)
if start<0 or end<0:
    raise SystemExit('openUserEditor niet gevonden')
new_editor='''function openUserEditor(userId){const u=(window.machineparkAdminUsers||[]).find(x=>x.id===userId);if(!u){toast('Gebruiker niet gevonden');return}const roleField=u.isOwner?`<div class="field"><label>Rol</label><input value="Beheerder" readonly style="background:#f4f6f5"><input type="hidden" name="role" value="beheerder"><div class="muted" style="font-size:11px;margin-top:4px">Vaste hoofdbeheerder</div></div>`:`<div class="field"><label>Rol</label><select name="role"><option value="gebruiker" ${u.role==='gebruiker'?'selected':''}>Gebruiker</option><option value="beheerder" ${u.role==='beheerder'?'selected':''}>Beheerder</option></select></div>`;const body=`<div class="form-grid"><div class="field"><label>Voornaam</label><input name="firstName" value="${esc(u.firstName||'')}" maxlength="100"></div><div class="field"><label>Achternaam</label><input name="lastName" value="${esc(u.lastName||'')}" maxlength="100"></div><div class="field full"><label>E-mailadres</label><input value="${esc(u.email||'')}" readonly style="background:#f4f6f5"><div class="muted" style="font-size:11px;margin-top:4px">Het login-e-mailadres wordt door Clerk beheerd en vereist verificatie om te wijzigen.</div></div>${roleField}<div class="field full"><div class="alert"><strong>Rechten</strong>Beheerders zien Beheer, gebruikersbeheer en het wijzigingslogboek. Gebruikers zien Beheer niet. ${esc(window.MACHINEPARK_ADMIN_EMAIL)} blijft altijd hoofdbeheerder.</div></div></div>`;showModal('Gebruiker bewerken',body,'Wijzigingen opslaan',async fd=>{try{const newRole=val(fd,'role')||'gebruiker';await adminFetch(USER_MANAGEMENT_URL,{method:'POST',body:JSON.stringify({action:'update-user',userId:u.id,firstName:val(fd,'firstName'),lastName:val(fd,'lastName'),role:newRole})});closeModal();toast('Gebruiker en rol aangepast');if(u.id===window.machineparkCurrentAdminUserId&&newRole==='gebruiker'&&!u.isOwner){window.machineparkIsAdmin=false;if(typeof window.applyMachineparkRoleAccess==='function')window.applyMachineparkRoleAccess();switchView('dashboard');return}await Promise.all([loadUserManagement(),loadAuditLog()])}catch(e){alert(e.message)}})}'''
s=s[:start]+new_editor+s[end:]

old_auth="window.machineparkIsAdmin=String(Clerk.user?.primaryEmailAddress?.emailAddress||Clerk.user?.emailAddresses?.[0]?.emailAddress||'').trim().toLowerCase()===window.MACHINEPARK_ADMIN_EMAIL;"
new_auth="const currentEmail=String(Clerk.user?.primaryEmailAddress?.emailAddress||Clerk.user?.emailAddresses?.[0]?.emailAddress||'').trim().toLowerCase();const currentRole=String(Clerk.user?.publicMetadata?.role||'').trim().toLowerCase();window.machineparkIsAdmin=currentEmail===window.MACHINEPARK_ADMIN_EMAIL||currentRole==='beheerder';"
if old_auth not in s:
    raise SystemExit('Clerk roltoekenning niet gevonden')
s=s.replace(old_auth,new_auth,1)

s=s.replace('v1.30 • Gebruikers bewerken','v1.31 • Rollenbeheer',1)
p.write_text(s,encoding='utf-8')

sw=Path('sw.js')
ws=sw.read_text(encoding='utf-8')
for old_cache in ['machinepark-v1.30-user-editing','machinepark-v1.29-audit-scroll']:
    ws=ws.replace(old_cache,'machinepark-v1.31-role-management')
sw.write_text(ws,encoding='utf-8')
