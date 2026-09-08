from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="role-management-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    # Rollenkaart boven gebruikersbeheer.
    anchor = '<div class="settings-card" id="userManagementCard" style="grid-column:1/-1">'
    card = '''<div class="settings-card" id="roleManagementCard" style="grid-column:1/-1">
          <div class="role-management-head">
            <div><h4>Rollen & rechten</h4><p>Stel per rol in welke schermen en handelingen beschikbaar zijn. De vaste hoofdbeheerder behoudt altijd alle rechten.</p></div>
            <div class="role-management-actions"><button class="btn" type="button" id="refreshRoles">Vernieuwen</button><button class="btn primary" type="button" id="addRole">+ Nieuwe rol</button></div>
          </div>
          <div id="roleManagementStatus" class="muted" style="font-size:12px;margin:8px 0 12px">Rollen worden geladen…</div>
          <div id="roleManagementBody" class="role-management-grid"></div>
        </div>
        '''
    replace_once(anchor, card + anchor, 'rollenkaart')

    # Centrale synchronisatie levert de actuele rol/rechten mee; pas die direct toe.
    replace_once(
        'const body=await res.json();if(!body.exists){',
        "const body=await res.json();if(typeof window.applyMachineparkServerAccess==='function')window.applyMachineparkServerAccess(body);if(!body.exists){",
        'rechten toepassen na centrale GET',
    )
    replace_once(
        'const body=await res.json();centralSync.etag=body.etag||centralSync.etag;',
        "const body=await res.json();if(typeof window.applyMachineparkServerAccess==='function')window.applyMachineparkServerAccess(body);centralSync.etag=body.etag||centralSync.etag;",
        'rechten toepassen na centrale PUT',
    )

    style = f'''
<style {MARKER}>
.role-management-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;flex-wrap:wrap}}
.role-management-head h4{{margin-bottom:5px}}
.role-management-head p{{margin:0;max-width:760px}}
.role-management-actions{{display:flex;gap:8px;flex-wrap:wrap}}
.role-management-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}}
.role-card{{border:1px solid var(--line);border-radius:14px;padding:14px;background:#fff;display:grid;gap:11px}}
.role-card-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}}
.role-card h5{{font-size:15px;margin:0}}
.role-card-meta{{font-size:11px;color:var(--muted);margin-top:3px}}
.role-card-count{{font-weight:800;font-size:22px;line-height:1}}
.role-card-foot{{display:flex;justify-content:flex-end;gap:7px;flex-wrap:wrap}}
.role-permission-groups{{display:grid;gap:14px}}
.role-permission-group{{border:1px solid var(--line);border-radius:12px;padding:11px}}
.role-permission-group-title{{font-weight:800;margin-bottom:8px}}
.role-permission-list{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px 12px}}
.role-permission-item{{display:flex;gap:8px;align-items:flex-start;font-size:12px;line-height:1.35}}
.role-permission-item input{{margin-top:2px}}
.role-permission-summary{{display:flex;flex-wrap:wrap;gap:5px}}
.role-permission-summary .badge{{font-size:10px}}
@media(max-width:700px){{
  .role-management-actions{{width:100%}}
  .role-management-actions .btn{{flex:1}}
  .role-permission-list{{grid-template-columns:1fr}}
}}
</style>
'''

    script = r'''
<script data-machinepark-build-fix="role-management-v1">
(() => {
  const ROLE_MANAGEMENT_URL = '/.netlify/functions/role-management';
  window.machineparkPermissions = window.machineparkPermissions || {};
  window.machineparkAvailableRoles = window.machineparkAvailableRoles || [];
  window.machineparkPermissionCatalog = window.machineparkPermissionCatalog || [];
  window.machineparkRoleConfigEtag = window.machineparkRoleConfigEtag || null;
  window.machineparkAccessReady = false;

  function hasPermission(key) {
    if (!window.machineparkAccessReady) return false;
    return Boolean(window.machineparkPermissions?.[key]);
  }
  window.machineparkHasPermission = hasPermission;

  function currentRoleLabel() {
    const role = String(window.machineparkRole || 'gebruiker');
    const found = (window.machineparkAvailableRoles || []).find((x) => (x.value || x.id) === role);
    return found?.label || window.machineparkCurrentRoleLabel || role.charAt(0).toUpperCase() + role.slice(1);
  }

  machineparkRoleLabel = function(role) {
    const id = String(role || 'gebruiker');
    const found = (window.machineparkAvailableRoles || []).find((x) => (x.value || x.id) === id);
    return found?.label || (id === 'beheerder' ? 'Beheerder' : id === 'gebruiker' ? 'Gebruiker' : id === 'technieker' ? 'Technieker' : id === 'magazijnier' ? 'Magazijnier' : id);
  };

  function viewPermission(view) { return `view.${view}`; }
  function firstAllowedView() {
    return ['dashboard','devices','maintenance','breakdowns','parts','settings'].find((view) => hasPermission(viewPermission(view))) || 'dashboard';
  }

  const originalSwitchViewForRoles = switchView;
  switchView = function(view) {
    if (window.machineparkAccessReady && !hasPermission(viewPermission(view))) view = firstAllowedView();
    return originalSwitchViewForRoles(view);
  };
  window.switchView = switchView;

  function applySettingsCards() {
    const roleCard = document.getElementById('roleManagementCard');
    const usersCard = document.getElementById('userManagementCard');
    const auditCard = document.getElementById('auditLogCard');
    if (roleCard) roleCard.style.display = hasPermission('roles.manage') ? '' : 'none';
    if (usersCard) usersCard.style.display = hasPermission('users.manage') ? '' : 'none';
    if (auditCard) auditCard.style.display = hasPermission('audit.view') ? '' : 'none';
    document.querySelectorAll('[data-undo-audit]').forEach((btn) => {
      if (!hasPermission('audit.undo')) {
        btn.disabled = true;
        btn.title = 'Deze rol mag wijzigingen niet ongedaan maken.';
      }
    });
  }

  applyMachineparkRoleAccess = function() {
    if (!window.machineparkAccessReady) return;
    document.querySelectorAll('.nav button[data-view]').forEach((btn) => {
      btn.style.display = hasPermission(viewPermission(btn.dataset.view)) ? '' : 'none';
    });
    window.machineparkIsAdmin = hasPermission('view.settings');
    const visible = [...document.querySelectorAll('.nav button[data-view]')].filter((btn) => btn.style.display !== 'none').length;
    document.documentElement.style.setProperty('--mobile-nav-count', String(Math.max(1, visible)));
    if (!hasPermission(viewPermission(state.view))) originalSwitchViewForRoles(firstAllowedView());
    applySettingsCards();
  };
  window.applyMachineparkRoleAccess = applyMachineparkRoleAccess;

  machineparkCapabilities = function() {
    return {
      devices: hasPermission('devices.edit') || hasPermission('devices.statusNotes'),
      maintenance: hasPermission('maintenance.edit') || hasPermission('maintenance.delete'),
      breakdowns: hasPermission('breakdowns.edit') || hasPermission('breakdowns.delete'),
      parts: hasPermission('parts.edit') || hasPermission('parts.stock'),
    };
  };

  applyOperationalPermissions = function() {
    if (!window.machineparkAccessReady) return;
    window.machineparkCanEdit = machineparkCapabilities();
    const visibility = [
      ['#addDevice','devices.add'], ['#addMaintenance','maintenance.add'],
      ['#addBreakdown','breakdowns.add'], ['#addPart','parts.add'],
      ['#exportPartsCsv','parts.export'],
    ];
    visibility.forEach(([selector, permission]) => document.querySelectorAll(selector).forEach((el) => el.style.display = hasPermission(permission) ? '' : 'none'));
    document.querySelectorAll('[data-edit-part]').forEach((el) => el.style.display = (hasPermission('parts.edit') || hasPermission('parts.stock')) ? '' : 'none');
    document.querySelectorAll('.page-print-btn,.service-detail-print-btn').forEach((el) => el.style.display = hasPermission('print') ? '' : 'none');
    applySettingsCards();
  };
  window.applyOperationalPermissions = applyOperationalPermissions;

  window.applyMachineparkServerAccess = function(body) {
    if (!body || typeof body !== 'object' || !body.permissions) return;
    window.machineparkPermissions = { ...body.permissions };
    window.machineparkRole = String(body.role || window.machineparkRole || 'gebruiker');
    window.machineparkCurrentRoleLabel = String(body.roleLabel || window.machineparkRole);
    window.machineparkAccessReady = true;
    window.machineparkIsAdmin = Boolean(window.machineparkPermissions['view.settings']);
    const roleEl = document.getElementById('accountDisplayRole');
    if (roleEl) roleEl.textContent = window.machineparkCurrentRoleLabel;
    applyMachineparkRoleAccess();
    applyOperationalPermissions();
  };

  const baseAdminFetch = adminFetch;
  adminFetch = async function(url, options = {}) {
    const data = await baseAdminFetch(url, options);
    const method = String(options?.method || 'GET').toUpperCase();
    if (url === USER_MANAGEMENT_URL && method === 'GET') {
      window.machineparkAvailableRoles = data.roles || [];
      const select = document.getElementById('inviteUserRole');
      if (select) fillRoleSelect(select, select.value || 'gebruiker');
    }
    return data;
  };

  roleBadgeHtml = function(role) {
    const label = machineparkRoleLabel(role);
    const cls = role === 'beheerder' ? 'success' : role === 'technieker' ? 'blue' : role === 'magazijnier' ? 'warn' : 'gray';
    return `<span class="badge ${cls}">${esc(label)}</span>`;
  };

  function fillRoleSelect(select, selected) {
    if (!select) return;
    const roles = window.machineparkAvailableRoles || [];
    select.innerHTML = roles.map((role) => `<option value="${esc(role.value || role.id)}" ${(role.value || role.id) === selected ? 'selected' : ''}>${esc(role.label || role.value || role.id)}</option>`).join('');
  }

  openUserEditor = function(userId) {
    const u = (window.machineparkAdminUsers || []).find((x) => x.id === userId);
    if (!u) { toast('Gebruiker niet gevonden'); return; }
    const options = (window.machineparkAvailableRoles || []).map((role) => `<option value="${esc(role.value || role.id)}" ${(role.value || role.id) === u.role ? 'selected' : ''}>${esc(role.label || role.value || role.id)}</option>`).join('');
    const roleField = u.isOwner
      ? `<div class="field"><label>Rol</label><input value="Beheerder" readonly style="background:#f4f6f5"><input type="hidden" name="role" value="beheerder"><div class="muted" style="font-size:11px;margin-top:4px">Vaste hoofdbeheerder · alle rechten blijven altijd actief.</div></div>`
      : `<div class="field"><label>Rol</label><select name="role">${options}</select></div>`;
    const body = `<div class="form-grid"><div class="field"><label>Voornaam</label><input name="firstName" value="${esc(u.firstName || '')}" maxlength="100"></div><div class="field"><label>Achternaam</label><input name="lastName" value="${esc(u.lastName || '')}" maxlength="100"></div><div class="field full"><label>E-mailadres</label><input value="${esc(u.email || '')}" readonly style="background:#f4f6f5"></div>${roleField}<div class="field full"><div class="alert"><strong>Rollen & rechten</strong>De toegestane handelingen worden bepaald in Beheer → Rollen & rechten.</div></div></div>`;
    showModal('Gebruiker bewerken', body, 'Wijzigingen opslaan', async (fd) => {
      try {
        const newRole = val(fd, 'role') || 'gebruiker';
        await adminFetch(USER_MANAGEMENT_URL, { method: 'POST', body: JSON.stringify({ action: 'update-user', userId: u.id, firstName: val(fd, 'firstName'), lastName: val(fd, 'lastName'), role: newRole }) });
        closeModal();
        toast('Gebruiker en rol aangepast');
        await loadUserManagement();
        centralSync.etag = null;
        await centralPull({ apply: true, quiet: true });
        if (hasPermission('audit.view')) await loadAuditLog();
      } catch (e) { alert(e.message); }
    });
  };

  const baseBindForRoles = bind;
  bind = function() {
    baseBindForRoles();
    const inviteForm = document.getElementById('inviteUserForm');
    if (inviteForm) {
      let roleSelect = document.getElementById('inviteUserRole');
      if (!roleSelect) {
        roleSelect = document.createElement('select');
        roleSelect.id = 'inviteUserRole';
        roleSelect.style.cssText = 'min-width:180px;border:1px solid var(--line);border-radius:10px;padding:10px 11px;background:white';
        inviteForm.insertBefore(roleSelect, inviteForm.querySelector('button[type=submit]'));
      }
      fillRoleSelect(roleSelect, 'gebruiker');
      inviteForm.onsubmit = async (e) => {
        e.preventDefault();
        if (!hasPermission('users.manage')) return;
        const input = document.getElementById('inviteUserEmail');
        const email = String(input?.value || '').trim().toLowerCase();
        if (!email) return;
        const role = String(roleSelect.value || 'gebruiker');
        const submit = e.target.querySelector('button[type=submit]');
        if (submit) submit.disabled = true;
        try {
          await adminFetch(USER_MANAGEMENT_URL, { method: 'POST', body: JSON.stringify({ action: 'invite', email, role }) });
          if (input) input.value = '';
          toast('Uitnodiging verstuurd');
          await loadUserManagement();
          if (hasPermission('audit.view')) await loadAuditLog();
        } catch (err) { alert(err.message); }
        finally { if (submit) submit.disabled = false; }
      };
    }
    const refreshRoles = document.getElementById('refreshRoles');
    if (refreshRoles) refreshRoles.onclick = () => loadRoleManagement();
    const addRole = document.getElementById('addRole');
    if (addRole) addRole.onclick = () => openRoleEditor();
    applyOperationalPermissions();
  };

  function permissionGroupsHtml(role) {
    const allowed = (window.machineparkPermissionCatalog || []).filter((item) => role.permissions?.[item.key]);
    if (!allowed.length) return '<span class="muted">Geen handelingen toegestaan</span>';
    return `<div class="role-permission-summary">${allowed.slice(0, 8).map((item) => `<span class="badge gray">${esc(item.label)}</span>`).join('')}${allowed.length > 8 ? `<span class="badge gray">+${allowed.length - 8}</span>` : ''}</div>`;
  }

  function renderRoleManagement() {
    const body = document.getElementById('roleManagementBody');
    const status = document.getElementById('roleManagementStatus');
    if (!body) return;
    const roles = window.machineparkRoleDefinitions || [];
    if (status) status.textContent = `${roles.length} rol${roles.length === 1 ? '' : 'len'} · vaste hoofdbeheerder is niet beperkbaar`;
    body.innerHTML = roles.map((role) => {
      const count = Object.values(role.permissions || {}).filter(Boolean).length;
      return `<div class="role-card"><div class="role-card-head"><div><h5>${esc(role.label)}</h5><div class="role-card-meta">${role.builtIn ? 'Standaardrol' : 'Eigen rol'} · ${esc(role.id)}</div></div><div class="role-card-count">${count}</div></div>${permissionGroupsHtml(role)}<div class="role-card-foot"><button class="btn small" type="button" data-role-edit="${esc(role.id)}">Bewerken</button>${role.builtIn ? '' : `<button class="btn small danger" type="button" data-role-delete="${esc(role.id)}">Verwijderen</button>`}</div></div>`;
    }).join('');
    body.querySelectorAll('[data-role-edit]').forEach((btn) => btn.onclick = () => openRoleEditor(btn.dataset.roleEdit));
    body.querySelectorAll('[data-role-delete]').forEach((btn) => btn.onclick = () => deleteRole(btn.dataset.roleDelete));
  }

  async function roleFetch(options = {}) {
    const headers = await centralHeaders(options.body !== undefined);
    const res = await fetch(ROLE_MANAGEMENT_URL, { ...options, headers: { ...headers, ...(options.headers || {}) }, cache: 'no-store' });
    let body = {};
    try { body = await res.json(); } catch (_) {}
    if (!res.ok) throw new Error(body?.error || `Rollenbeheer mislukt (${res.status})`);
    return body;
  }

  async function loadRoleManagement() {
    if (!hasPermission('roles.manage')) return;
    const status = document.getElementById('roleManagementStatus');
    if (status) status.textContent = 'Rollen worden geladen…';
    try {
      const data = await roleFetch();
      window.machineparkRoleDefinitions = data.roles || [];
      window.machineparkPermissionCatalog = data.permissionCatalog || [];
      window.machineparkRoleConfigEtag = data.etag || null;
      window.machineparkAvailableRoles = (data.roles || []).map((role) => ({ value: role.id, label: role.label }));
      renderRoleManagement();
    } catch (error) {
      if (status) status.textContent = 'Rollen konden niet worden geladen: ' + error.message;
    }
  }
  window.loadRoleManagement = loadRoleManagement;

  function groupedCatalog() {
    const groups = new Map();
    (window.machineparkPermissionCatalog || []).forEach((item) => {
      if (!groups.has(item.group)) groups.set(item.group, []);
      groups.get(item.group).push(item);
    });
    return [...groups.entries()];
  }

  function openRoleEditor(roleId = '') {
    const existing = (window.machineparkRoleDefinitions || []).find((role) => role.id === roleId) || null;
    const groups = groupedCatalog();
    const permissionHtml = groups.map(([group, items]) => `<div class="role-permission-group"><div class="role-permission-group-title">${esc(group)}</div><div class="role-permission-list">${items.map((item) => `<label class="role-permission-item"><input type="checkbox" name="perm:${esc(item.key)}" ${existing?.permissions?.[item.key] ? 'checked' : ''}><span>${esc(item.label)}</span></label>`).join('')}</div></div>`).join('');
    const name = existing?.label || '';
    const nameField = `<div class="field full"><label>Naam rol *</label><input name="roleLabel" required maxlength="80" value="${esc(name)}" ${existing?.builtIn ? 'readonly style="background:#f4f6f5"' : ''}><div class="muted" style="font-size:11px;margin-top:4px">${existing?.builtIn ? 'De naam van een standaardrol blijft behouden; de rechten zijn wel aanpasbaar.' : 'Nieuwe rollen kunnen daarna meteen aan gebruikers worden toegewezen.'}</div></div>`;
    const body = `<div class="form-grid">${nameField}<div class="field full"><div class="alert"><strong>Veiligheidsregel</strong>De vaste hoofdbeheerder behoudt altijd alle rechten, ongeacht deze schakelaars.</div></div><div class="field full role-permission-groups">${permissionHtml}</div></div>`;
    showModal(existing ? `Rol wijzigen · ${existing.label}` : 'Nieuwe rol', body, 'Rol opslaan', async (fd) => {
      const label = val(fd, 'roleLabel');
      if (!label) return;
      const permissions = {};
      (window.machineparkPermissionCatalog || []).forEach((item) => permissions[item.key] = fd.get(`perm:${item.key}`) === 'on');
      try {
        const data = await roleFetch({ method: 'POST', body: JSON.stringify({ action: 'save-role', etag: window.machineparkRoleConfigEtag, role: { id: existing?.id || '', label, permissions } }) });
        window.machineparkRoleDefinitions = data.roles || [];
        window.machineparkRoleConfigEtag = data.etag || null;
        window.machineparkAvailableRoles = (data.roles || []).map((role) => ({ value: role.id, label: role.label }));
        closeModal();
        renderRoleManagement();
        toast(existing ? 'Rol en rechten aangepast' : 'Nieuwe rol aangemaakt');
        if (hasPermission('users.manage')) await loadUserManagement();
        centralSync.etag = null;
        await centralPull({ apply: true, quiet: true });
      } catch (error) { alert(error.message); }
    });
  }
  window.openMachineparkRoleEditor = openRoleEditor;

  async function deleteRole(roleId) {
    const role = (window.machineparkRoleDefinitions || []).find((x) => x.id === roleId);
    if (!role || role.builtIn) return;
    if (!confirm(`Rol “${role.label}” verwijderen? Dit kan alleen wanneer geen gebruiker deze rol nog gebruikt.`)) return;
    try {
      const data = await roleFetch({ method: 'POST', body: JSON.stringify({ action: 'delete-role', roleId, etag: window.machineparkRoleConfigEtag }) });
      window.machineparkRoleDefinitions = data.roles || [];
      window.machineparkRoleConfigEtag = data.etag || null;
      window.machineparkAvailableRoles = (data.roles || []).map((x) => ({ value: x.id, label: x.label }));
      renderRoleManagement();
      toast('Rol verwijderd');
      if (hasPermission('users.manage')) await loadUserManagement();
    } catch (error) { alert(error.message); }
  }

  const baseLoadAdminPanels = loadAdminPanels;
  loadAdminPanels = async function() {
    if (!hasPermission('view.settings')) return;
    const tasks = [];
    if (hasPermission('roles.manage')) tasks.push(loadRoleManagement());
    if (hasPermission('users.manage')) tasks.push(loadUserManagement());
    if (hasPermission('audit.view')) tasks.push(loadAuditLog());
    await Promise.all(tasks);
    applySettingsCards();
  };

  const baseAuditUndoButton = auditUndoButton;
  auditUndoButton = function(entry, change, changeIndex) {
    if (!hasPermission('audit.undo')) return '<button class="btn small" type="button" disabled title="Deze rol mag niets herstellen.">Geblokkeerd</button>';
    return baseAuditUndoButton(entry, change, changeIndex);
  };

  const baseOpenDeviceForRoles = openDevice;
  openDevice = function(id) {
    if (!id) {
      if (!hasPermission('devices.add')) { toast('Deze rol mag geen toestellen toevoegen'); return; }
      return baseOpenDeviceForRoles(id);
    }
    if (hasPermission('devices.edit')) return baseOpenDeviceForRoles(id);
    if (!hasPermission('devices.statusNotes')) { toast('Deze rol mag toestelgegevens niet wijzigen'); return; }
    const old = state.devices.find((d) => d.id === id);
    if (!old) return;
    const body = `<div class="form-grid"><div class="field"><label>Toestel</label><input value="${esc(old.assetCode || old.model || 'Toestel')}" readonly style="background:#f4f6f5"></div><div class="field"><label>Locatie</label><input value="${esc(deviceLocationAt(old) || old.location || 'Geen locatie')}" readonly style="background:#f4f6f5"></div><div class="field"><label>Status</label><select name="status">${['Actief','In herstelling','Buiten dienst'].map((x) => `<option ${old.status === x ? 'selected' : ''}>${x}</option>`).join('')}</select></div><div class="field full"><label>Notities</label><textarea name="notes">${esc(old.notes || '')}</textarea></div></div>`;
    showModal('Toestelstatus & notities', body, 'Opslaan', async (fd) => {
      await put('devices', { ...old, status: val(fd, 'status') || old.status || 'Actief', notes: val(fd, 'notes'), updatedAt: new Date().toISOString() });
      closeModal(); await refresh(); toast('Toestelstatus en notities opgeslagen');
    });
  };

  const baseOpenPartForRoles = openPart;
  openPart = function(id) {
    if (!id) {
      if (!hasPermission('parts.add')) { toast('Deze rol mag geen onderdelen toevoegen'); return; }
      return baseOpenPartForRoles(id);
    }
    if (hasPermission('parts.edit')) return baseOpenPartForRoles(id);
    if (!hasPermission('parts.stock')) { toast('Deze rol mag onderdelen niet wijzigen'); return; }
    const old = state.parts.find((p) => p.id === id);
    if (!old) return;
    const body = `<div class="form-grid"><div class="field"><label>Art nr</label><input value="${esc(old.artNr || '—')}" readonly style="background:#f4f6f5"></div><div class="field full"><label>Omschrijving</label><input value="${esc(old.description || '—')}" readonly style="background:#f4f6f5"></div><div class="field"><label>Voorraad locatie 1</label><input name="stock" type="number" step="1" min="0" value="${Number(old.stock || 0)}"></div></div>`;
    showModal('Voorraad aanpassen', body, 'Voorraad opslaan', async (fd) => {
      await put('parts', { ...old, stock: Number(fd.get('stock') || 0), updatedAt: new Date().toISOString() });
      closeModal(); await refresh(); toast('Voorraad aangepast');
    });
  };

  const baseOpenMaintenanceForRoles = openMaintenance;
  openMaintenance = function(id) {
    if (id && !hasPermission('maintenance.edit')) { toast('Deze rol mag onderhoud niet wijzigen'); return; }
    if (!id && !hasPermission('maintenance.add')) { toast('Deze rol mag geen onderhoud registreren'); return; }
    return baseOpenMaintenanceForRoles(id);
  };

  const baseShowMaintenanceDetailsForRoles = showMaintenanceDetails;
  showMaintenanceDetails = function(id) {
    const result = baseShowMaintenanceDetailsForRoles(id);
    setTimeout(() => {
      const edit = document.getElementById('editMaintenanceFromDetails');
      const del = document.getElementById('deleteMaintenanceFromDetails');
      if (edit) edit.style.display = hasPermission('maintenance.edit') ? '' : 'none';
      if (del) del.style.display = hasPermission('maintenance.delete') ? '' : 'none';
      document.querySelectorAll('#modal .service-detail-print-btn').forEach((btn) => btn.style.display = hasPermission('print') ? '' : 'none');
    }, 0);
    return result;
  };

  function readonlyBreakdown(id) {
    const b = state.breakdowns.find((x) => x.id === id);
    if (!b) return;
    const photos = Array.isArray(b.photos) ? b.photos.filter((src) => typeof src === 'string' && src.startsWith('data:image/')) : [];
    const body = `<div class="form-grid"><div class="field"><label>Datum en uur</label><div><strong>${recordDateTimeFmt(b)}</strong></div></div><div class="field"><label>Toestel</label><div><strong>${esc(deviceName(b.deviceId, recordMoment(b)))}</strong></div></div><div class="field"><label>Prioriteit</label><div>${esc(b.priority || '—')}</div></div><div class="field"><label>Status</label><div>${esc(b.status || '—')}</div></div><div class="field"><label>Technieker</label><div>${esc(b.technician || '—')}</div></div><div class="field full"><label>Probleem / melding</label><div style="white-space:pre-wrap">${esc(b.issue || '—')}</div></div><div class="field full"><label>Diagnose</label><div style="white-space:pre-wrap">${esc(b.diagnosis || '—')}</div></div><div class="field full"><label>Oplossing / werken</label><div style="white-space:pre-wrap">${esc(b.solution || '—')}</div></div><div class="field full"><label>Gebruikte onderdelen</label><div>${esc(usedPartsText(b.usedParts || []))}</div></div>${photos.length ? `<div class="field full"><label>Foto’s</label><div class="service-photo-details">${photos.map((src) => `<img src="${src}" alt="Verslagfoto">`).join('')}</div></div>` : ''}</div>`;
    const actions = `${hasPermission('breakdowns.delete') ? '<button class="btn danger" type="button" id="roleDeleteBreakdown">Verwijderen</button>' : ''}${hasPermission('print') ? '<button class="btn" type="button" id="rolePrintBreakdown">🖨 Afdrukken</button>' : ''}`;
    document.getElementById('modal').innerHTML = `<div class="modal-head"><h3>Depannage details</h3><button class="close" type="button">×</button></div><div class="modal-body">${body}</div><div class="modal-foot"><button class="btn" type="button" id="roleCloseBreakdown">Sluiten</button>${actions}</div>`;
    document.getElementById('modalBackdrop').classList.add('show');
    document.querySelector('#modal .close').onclick = closeModal;
    document.getElementById('roleCloseBreakdown').onclick = closeModal;
    const del = document.getElementById('roleDeleteBreakdown');
    if (del) del.onclick = () => deleteServiceRecord('breakdowns', id);
    const print = document.getElementById('rolePrintBreakdown');
    if (print) print.onclick = () => window.printMachineparkServiceRecord?.('breakdowns', id);
  }

  const baseOpenBreakdownForRoles = openBreakdown;
  openBreakdown = function(id) {
    if (!id) {
      if (!hasPermission('breakdowns.add')) { toast('Deze rol mag geen depannage registreren'); return; }
      return baseOpenBreakdownForRoles(id);
    }
    if (hasPermission('breakdowns.edit')) {
      const result = baseOpenBreakdownForRoles(id);
      setTimeout(() => {
        const del = document.getElementById('deleteBreakdownFromDetails');
        if (del) del.style.display = hasPermission('breakdowns.delete') ? '' : 'none';
        document.querySelectorAll('#modal .service-detail-print-btn').forEach((btn) => btn.style.display = hasPermission('print') ? '' : 'none');
      }, 0);
      return result;
    }
    return readonlyBreakdown(id);
  };

  const baseDeleteServiceRecordForRoles = deleteServiceRecord;
  deleteServiceRecord = function(storeName, id) {
    const permission = storeName === 'maintenance' ? 'maintenance.delete' : storeName === 'breakdowns' ? 'breakdowns.delete' : '';
    if (permission && !hasPermission(permission)) { toast('Deze rol mag dit dossier niet verwijderen'); return; }
    return baseDeleteServiceRecordForRoles(storeName, id);
  };

  const basePrintMachineparkViewForRoles = window.printMachineparkView;
  if (basePrintMachineparkViewForRoles) window.printMachineparkView = function(...args) {
    if (!hasPermission('print')) { toast('Deze rol mag niet afdrukken'); return; }
    return basePrintMachineparkViewForRoles(...args);
  };
  const basePrintServiceForRoles = window.printMachineparkServiceRecord;
  if (basePrintServiceForRoles) window.printMachineparkServiceRecord = function(...args) {
    if (!hasPermission('print')) { toast('Deze rol mag niet afdrukken'); return; }
    return basePrintServiceForRoles(...args);
  };
})();
</script>
'''

    if '</head>' not in index or '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-afsluiters ontbreken voor rollenbeheer')
    index = index.replace('</head>', style + '</head>', 1)
    index = index.replace('</body>', script + '</body>', 1)
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'Rollen & rechten',
    'id="roleManagementCard"',
    'ROLE_MANAGEMENT_URL',
    'applyMachineparkServerAccess',
    'machineparkHasPermission',
    'loadRoleManagement',
    'openMachineparkRoleEditor',
    'parts.stock',
    'maintenance.delete',
    'breakdowns.delete',
    'audit.undo',
    'roles.manage',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: rollenbeheer ontbreekt ({needle})')

print('[Machinepark] configureerbare rollen en rechten actief')
