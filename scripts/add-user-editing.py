from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

old="const data=await adminFetch(USER_MANAGEMENT_URL);if(status)status.textContent=`${data.users.length} account(s) · beheerder: ${data.adminEmail}`;"
new="const data=await adminFetch(USER_MANAGEMENT_URL);window.machineparkAdminUsers=data.users||[];if(status)status.textContent=`${data.users.length} account(s) · beheerder: ${data.adminEmail}`;"
if old not in s:
    raise SystemExit('Gebruikerslijst laadpunt niet gevonden')
s=s.replace(old,new,1)

old_action="<td>${u.role==='beheerder'?'<span class=\"muted\">Vast beheerderaccount</span>':`<button class=\"btn small danger\" type=\"button\" data-remove-user=\"${u.id}\" data-remove-user-email=\"${esc(u.email||'')}\">Verwijder</button>`}</td>"
new_action="<td><div style=\"display:flex;gap:7px;align-items:center;flex-wrap:wrap\"><button class=\"btn small\" type=\"button\" data-edit-user=\"${u.id}\">Bewerk</button>${u.role==='beheerder'?'<span class=\"muted\">Vast beheerderaccount</span>':`<button class=\"btn small danger\" type=\"button\" data-remove-user=\"${u.id}\" data-remove-user-email=\"${esc(u.email||'')}\">Verwijder</button>`}</div></td>"
if old_action not in s:
    raise SystemExit('Actiekolom gebruikers niet gevonden')
s=s.replace(old_action,new_action,1)

anchor="function bindRenderedAdminActions(){"
if anchor not in s:
    raise SystemExit('bindRenderedAdminActions niet gevonden')
editor="""function openUserEditor(userId){const u=(window.machineparkAdminUsers||[]).find(x=>x.id===userId);if(!u){toast('Gebruiker niet gevonden');return}const role=u.role==='beheerder'?'Beheerder':'Gebruiker';const body=`<div class=\"form-grid\"><div class=\"field\"><label>Voornaam</label><input name=\"firstName\" value=\"${esc(u.firstName||'')}\" maxlength=\"100\"></div><div class=\"field\"><label>Achternaam</label><input name=\"lastName\" value=\"${esc(u.lastName||'')}\" maxlength=\"100\"></div><div class=\"field full\"><label>E-mailadres</label><input value=\"${esc(u.email||'')}\" readonly style=\"background:#f4f6f5\"><div class=\"muted\" style=\"font-size:11px;margin-top:4px\">Het login-e-mailadres wordt door Clerk beheerd en vereist verificatie om te wijzigen.</div></div><div class=\"field\"><label>Rol</label><input value=\"${role}\" readonly style=\"background:#f4f6f5\"></div><div class=\"field full\"><div class=\"alert\"><strong>Rechten</strong>Het beheerderaccount blijft vast gekoppeld aan ${esc(window.MACHINEPARK_ADMIN_EMAIL)}. Alle andere accounts blijven gebruiker.</div></div></div>`;showModal('Gebruiker bewerken',body,'Wijzigingen opslaan',async fd=>{try{await adminFetch(USER_MANAGEMENT_URL,{method:'POST',body:JSON.stringify({action:'update-user',userId:u.id,firstName:val(fd,'firstName'),lastName:val(fd,'lastName')})});closeModal();toast('Gebruiker aangepast');await Promise.all([loadUserManagement(),loadAuditLog()])}catch(e){alert(e.message)}})}
"""
s=s.replace(anchor,editor+anchor,1)

old_bind="function bindRenderedAdminActions(){$$('[data-remove-user]').forEach"
new_bind="function bindRenderedAdminActions(){$$('[data-edit-user]').forEach(btn=>btn.onclick=()=>openUserEditor(btn.dataset.editUser));$$('[data-remove-user]').forEach"
if old_bind not in s:
    raise SystemExit('Gebruikersactie binding niet gevonden')
s=s.replace(old_bind,new_bind,1)

s=s.replace('v1.29 • Scrollbaar logboek','v1.30 • Gebruikers bewerken',1)
p.write_text(s,encoding='utf-8')

sw=Path('sw.js')
ws=sw.read_text(encoding='utf-8')
for old_cache in ['machinepark-v1.29-audit-scroll','machinepark-v1.28-manual-service-dates']:
    ws=ws.replace(old_cache,'machinepark-v1.30-user-editing')
sw.write_text(ws,encoding='utf-8')
