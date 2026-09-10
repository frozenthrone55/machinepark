from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="user-management-hardening-v1"'

if MARKER not in index:
    old_card_start = '<div class="settings-card" id="userManagementCard" style="grid-column:1/-1">'
    start = index.find(old_card_start)
    if start < 0:
        raise SystemExit('Buildvalidatie mislukt: kaart Gebruikersbeheer niet gevonden')
    next_card = index.find('<div class="settings-card" id="auditLogCard"', start)
    if next_card < 0:
        raise SystemExit('Buildvalidatie mislukt: einde Gebruikersbeheer niet gevonden')

    card = '''<div class="settings-card user-management-card" id="userManagementCard" style="grid-column:1/-1">
          <div class="user-management-head">
            <div><h4>Gebruikersbeheer</h4><p>Beheer lokale accounts, rollen, toegang en wachtwoorden. De vaste hoofdbeheerder blijft altijd actief.</p></div>
            <button class="btn small" type="button" id="refreshUsers">Vernieuwen</button>
          </div>
          <form id="inviteUserForm" class="user-create-form">
            <div class="field"><label>Voornaam</label><input id="inviteUserFirstName" autocomplete="given-name" maxlength="100"></div>
            <div class="field"><label>Achternaam</label><input id="inviteUserLastName" autocomplete="family-name" maxlength="100"></div>
            <div class="field"><label>E-mailadres *</label><input id="inviteUserEmail" type="email" required autocomplete="email" placeholder="naam@bedrijf.be"></div>
            <div class="field"><label>Gebruikersnaam <span class="muted">(optioneel)</span></label><input id="inviteUserUsername" autocomplete="username" autocapitalize="none" spellcheck="false" placeholder="bv. jan.peters"></div>
            <div class="field"><label>Rol *</label><select id="inviteUserRole" required></select></div>
            <div class="field"><label>Eerste wachtwoord *</label><input id="inviteUserPassword" type="password" required minlength="10" autocomplete="new-password" placeholder="Minstens 10 tekens"></div>
            <div class="user-create-actions"><button class="btn primary" type="submit">Gebruiker toevoegen</button></div>
          </form>
          <div id="userManagementStatus" class="muted user-management-status">Gebruikers worden geladen…</div>
          <div class="table-wrap user-management-table-wrap"><table class="table user-management-table"><thead><tr><th>Gebruiker</th><th>Login</th><th>Rol</th><th>Status</th><th>Laatst aangemeld</th><th>Acties</th></tr></thead><tbody id="userManagementBody"></tbody></table></div>
          <div id="pendingInvitations" style="display:none"></div>
        </div>
        '''
    index = index[:start] + card + index[next_card:]

    style = f'''
<style {MARKER}>
.user-management-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}}
.user-management-head p{{margin:2px 0 0;min-height:0}}
.user-create-form{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:16px 0}}
.user-create-form .field{{min-width:0}}
.user-create-form input,.user-create-form select{{width:100%;border:1px solid var(--line);border-radius:10px;padding:10px 11px;background:#fff}}
.user-create-actions{{display:flex;align-items:end}}
.user-create-actions .btn{{width:100%}}
.user-management-status{{font-size:12px;margin-bottom:10px}}
.user-management-table{{min-width:980px}}
.user-management-table td{{vertical-align:top}}
.user-login-lines{{display:grid;gap:2px;font-size:12px}}
.user-actions{{display:flex;gap:6px;align-items:center;flex-wrap:wrap}}
.user-actions .btn{{white-space:nowrap}}
.user-status-active{{background:#e5f5ec;color:#24734f}}
.user-status-disabled{{background:#feeaea;color:#9e3030}}
@media(max-width:900px){{.user-create-form{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
@media(max-width:700px){{
  .user-create-form{{grid-template-columns:1fr;gap:10px}}
  .user-create-actions{{align-items:stretch}}
  .user-management-card{{padding:14px}}
  .user-management-table-wrap{{margin-left:-2px;margin-right:-2px}}
}}
</style>
'''
    index = index.replace('</head>', style + '</head>', 1)

    script = r'''
<script data-machinepark-build-fix="user-management-hardening-v1">
(() => {
  function rolesForUsers() {
    return (window.machineparkAvailableRoles || []).map((role) => ({
      value: String(role.value || role.id || ''),
      label: String(role.label || role.value || role.id || ''),
    })).filter((role) => role.value);
  }

  function fillUserRoleSelect(select, selected = 'gebruiker') {
    if (!select) return;
    const roles = rolesForUsers();
    select.innerHTML = roles.map((role) => `<option value="${esc(role.value)}" ${role.value === selected ? 'selected' : ''}>${esc(role.label)}</option>`).join('');
    if (!roles.length) select.innerHTML = '<option value="gebruiker">Gebruiker</option>';
  }

  function userStatusBadge(user) {
    if (user.isOwner) return '<span class="badge success">Hoofdbeheerder</span>';
    return user.disabled
      ? '<span class="badge user-status-disabled">Geblokkeerd</span>'
      : '<span class="badge user-status-active">Actief</span>';
  }

  loadUserManagement = async function() {
    if (!window.machineparkHasPermission?.('users.manage') && !window.machineparkIsAdmin) return;
    const status = document.getElementById('userManagementStatus');
    const body = document.getElementById('userManagementBody');
    if (status) status.textContent = 'Gebruikers worden geladen…';
    try {
      const data = await adminFetch(USER_MANAGEMENT_URL);
      window.machineparkAdminUsers = data.users || [];
      window.machineparkCurrentAdminUserId = data.currentUserId || '';
      if (Array.isArray(data.roles) && data.roles.length) window.machineparkAvailableRoles = data.roles;
      fillUserRoleSelect(document.getElementById('inviteUserRole'), 'gebruiker');
      const active = window.machineparkAdminUsers.filter((u) => !u.disabled).length;
      const blocked = window.machineparkAdminUsers.filter((u) => u.disabled).length;
      if (status) status.textContent = `${window.machineparkAdminUsers.length} account(s) · ${active} actief${blocked ? ` · ${blocked} geblokkeerd` : ''}`;
      if (!body) return;
      body.innerHTML = window.machineparkAdminUsers.length ? window.machineparkAdminUsers.map((u) => {
        const login = `<div class="user-login-lines"><span>${esc(u.email || '—')}</span>${u.username ? `<span class="muted">@${esc(u.username)}</span>` : '<span class="muted">login via e-mailadres</span>'}</div>`;
        const own = u.id === window.machineparkCurrentAdminUserId;
        const toggle = u.isOwner ? '' : `<button class="btn small" type="button" data-toggle-user="${esc(u.id)}" data-toggle-disabled="${u.disabled ? '0' : '1'}">${u.disabled ? 'Activeren' : 'Blokkeren'}</button>`;
        const remove = u.isOwner || own ? '' : `<button class="btn small danger" type="button" data-remove-user="${esc(u.id)}" data-remove-user-email="${esc(u.email || u.username || '')}">Verwijderen</button>`;
        return `<tr><td><strong>${esc(u.fullName || u.email || u.username || 'Gebruiker')}</strong>${own ? '<br><span class="muted">Dit account</span>' : ''}</td><td>${login}</td><td>${roleBadgeHtml(u.role)}</td><td>${userStatusBadge(u)}</td><td>${adminDateFmt(u.lastSignInAt)}</td><td><div class="user-actions"><button class="btn small" type="button" data-edit-user="${esc(u.id)}">Bewerken</button>${toggle}${remove}</div></td></tr>`;
      }).join('') : '<tr><td colspan="6"><div class="empty">Geen gebruikers gevonden.</div></td></tr>';
      bindRenderedAdminActions();
    } catch (error) {
      console.error('Gebruikersbeheer', error);
      if (status) status.textContent = 'Gebruikersbeheer kon niet worden geladen: ' + error.message;
      if (body) body.innerHTML = '<tr><td colspan="6"><div class="empty">Gebruikersbeheer niet beschikbaar.</div></td></tr>';
    }
  };
  window.loadUserManagement = loadUserManagement;

  openUserEditor = function(userId) {
    const u = (window.machineparkAdminUsers || []).find((x) => x.id === userId);
    if (!u) { toast('Gebruiker niet gevonden'); return; }
    const options = rolesForUsers().map((role) => `<option value="${esc(role.value)}" ${role.value === u.role ? 'selected' : ''}>${esc(role.label)}</option>`).join('');
    const roleField = u.isOwner
      ? `<div class="field"><label>Rol</label><input value="Beheerder" readonly style="background:#f4f6f5"><input type="hidden" name="role" value="beheerder"><div class="muted" style="font-size:11px;margin-top:4px">Vaste hoofdbeheerder · altijd volledige toegang.</div></div>`
      : `<div class="field"><label>Rol</label><select name="role">${options}</select></div>`;
    const usernameField = u.isOwner
      ? `<div class="field"><label>Gebruikersnaam</label><input value="admin" readonly style="background:#f4f6f5"><input type="hidden" name="username" value="admin"></div>`
      : `<div class="field"><label>Gebruikersnaam</label><input name="username" value="${esc(u.username || '')}" autocomplete="username" autocapitalize="none" spellcheck="false" placeholder="Optioneel"></div>`;
    const emailRequired = u.isOwner ? '' : 'required';
    const body = `<div class="form-grid"><div class="field"><label>Voornaam</label><input name="firstName" value="${esc(u.firstName || '')}" maxlength="100"></div><div class="field"><label>Achternaam</label><input name="lastName" value="${esc(u.lastName || '')}" maxlength="100"></div><div class="field"><label>E-mailadres${u.isOwner ? '' : ' *'}</label><input name="email" type="email" ${emailRequired} value="${esc(u.email || '')}"></div>${usernameField}${roleField}<div class="field"><label>Nieuw wachtwoord</label><input name="password" type="password" minlength="10" autocomplete="new-password" placeholder="Leeg = behouden"><div class="muted" style="font-size:11px;margin-top:4px">Alleen invullen om het wachtwoord te wijzigen.</div></div><div class="field full"><div class="alert"><strong>Toegang</strong>${u.isOwner ? 'De vaste hoofdbeheerder kan niet worden geblokkeerd of verwijderd.' : (u.disabled ? 'Dit account is momenteel geblokkeerd en kan niet aanmelden.' : 'Dit account is actief.')}</div></div></div>`;
    showModal('Gebruiker bewerken', body, 'Wijzigingen opslaan', async (fd) => {
      const payload = {
        action: 'update-user',
        userId: u.id,
        firstName: val(fd, 'firstName'),
        lastName: val(fd, 'lastName'),
        email: val(fd, 'email'),
        username: val(fd, 'username'),
        role: val(fd, 'role') || u.role || 'gebruiker',
        password: val(fd, 'password'),
      };
      await adminFetch(USER_MANAGEMENT_URL, { method: 'POST', body: JSON.stringify(payload) });
      closeModal();
      toast('Gebruiker opgeslagen');
      await loadUserManagement();
      if (window.machineparkHasPermission?.('audit.view')) await loadAuditLog();
      if (u.id === window.machineparkCurrentAdminUserId) {
        centralSync.etag = null;
        await centralPull({ apply: true, quiet: true });
      }
    });
  };
  window.openUserEditor = openUserEditor;

  bindRenderedAdminActions = function() {
    document.querySelectorAll('[data-edit-user]').forEach((btn) => btn.onclick = () => openUserEditor(btn.dataset.editUser));
    document.querySelectorAll('[data-toggle-user]').forEach((btn) => btn.onclick = async () => {
      const userId = btn.dataset.toggleUser;
      const user = (window.machineparkAdminUsers || []).find((u) => u.id === userId);
      if (!user) return;
      const disabled = btn.dataset.toggleDisabled === '1';
      const actionText = disabled ? 'blokkeren' : 'activeren';
      if (!confirm(`${user.fullName || user.email || user.username || 'Deze gebruiker'} ${actionText}?`)) return;
      btn.disabled = true;
      try {
        await adminFetch(USER_MANAGEMENT_URL, { method: 'POST', body: JSON.stringify({ action: 'toggle-user', userId, disabled }) });
        toast(disabled ? 'Gebruiker geblokkeerd' : 'Gebruiker geactiveerd');
        await loadUserManagement();
        if (window.machineparkHasPermission?.('audit.view')) await loadAuditLog();
      } catch (error) {
        alert(error.message);
        btn.disabled = false;
      }
    });
    document.querySelectorAll('[data-remove-user]').forEach((btn) => btn.onclick = async () => {
      const email = btn.dataset.removeUserEmail || 'deze gebruiker';
      if (!confirm(`Gebruiker ${email} definitief verwijderen?\n\nDit verwijdert het lokale account. Deze actie kan niet via Gebruikersbeheer worden teruggedraaid.`)) return;
      btn.disabled = true;
      try {
        await adminFetch(USER_MANAGEMENT_URL, { method: 'DELETE', body: JSON.stringify({ userId: btn.dataset.removeUser }) });
        toast('Gebruiker verwijderd');
        await loadUserManagement();
        if (window.machineparkHasPermission?.('audit.view')) await loadAuditLog();
      } catch (error) {
        alert(error.message);
        btn.disabled = false;
      }
    });
  };
  window.bindRenderedAdminActions = bindRenderedAdminActions;

  const previousBind = bind;
  bind = function() {
    previousBind();
    const form = document.getElementById('inviteUserForm');
    if (form) {
      fillUserRoleSelect(document.getElementById('inviteUserRole'), 'gebruiker');
      form.onsubmit = async (event) => {
        event.preventDefault();
        if (!window.machineparkHasPermission?.('users.manage') && !window.machineparkIsAdmin) return;
        const email = String(document.getElementById('inviteUserEmail')?.value || '').trim().toLowerCase();
        const username = String(document.getElementById('inviteUserUsername')?.value || '').trim().toLowerCase();
        const password = String(document.getElementById('inviteUserPassword')?.value || '');
        const firstName = String(document.getElementById('inviteUserFirstName')?.value || '').trim();
        const lastName = String(document.getElementById('inviteUserLastName')?.value || '').trim();
        const role = String(document.getElementById('inviteUserRole')?.value || 'gebruiker');
        if (!email) return;
        if (password.length < 10) { alert('Gebruik een eerste wachtwoord van minstens 10 tekens.'); return; }
        const submit = form.querySelector('button[type=submit]');
        if (submit) submit.disabled = true;
        try {
          await adminFetch(USER_MANAGEMENT_URL, { method: 'POST', body: JSON.stringify({ action: 'create-user', email, username, password, firstName, lastName, role }) });
          form.reset();
          fillUserRoleSelect(document.getElementById('inviteUserRole'), 'gebruiker');
          toast('Gebruiker toegevoegd');
          await loadUserManagement();
          if (window.machineparkHasPermission?.('audit.view')) await loadAuditLog();
        } catch (error) {
          alert(error.message);
        } finally {
          if (submit) submit.disabled = false;
        }
      };
    }
    const refresh = document.getElementById('refreshUsers');
    if (refresh) refresh.onclick = () => loadUserManagement();
  };
  window.bind = bind;
})();
</script>
'''
    index = index.replace('</body>', script + '</body>', 1)
    index_path.write_text(index, encoding='utf-8')

built = index_path.read_text(encoding='utf-8')
for needle in [
    MARKER,
    'id="inviteUserUsername"',
    'data-toggle-user=',
    "action: 'toggle-user'",
    "action: 'create-user'",
    'Gebruiker toevoegen',
    'Nieuw wachtwoord',
    'user-management-table',
]:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: gebruikersbeheer hardening ontbreekt ({needle})')

print('[Machinepark] Gebruikersbeheer volledig gehard: toevoegen, wijzigen, blokkeren, activeren en verwijderen')
