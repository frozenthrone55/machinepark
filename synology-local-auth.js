'use strict';

(() => {
  const AUTH_URL = './synology/api/auth.php';

  function els() {
    return {
      gate: document.getElementById('authGate'),
      shell: document.getElementById('appShell'),
      loading: document.getElementById('authLoading'),
      error: document.getElementById('authError'),
      form: document.getElementById('localAuthForm'),
      logout: document.getElementById('localLogoutBtn'),
    };
  }

  function clearError() {
    const box = els().error;
    if (!box) return;
    box.textContent = '';
    box.classList.remove('show');
  }

  function showError(message) {
    const { loading, error } = els();
    if (loading) loading.style.display = 'none';
    if (!error) return;
    error.textContent = message || 'Aanmelden is mislukt.';
    error.classList.add('show');
  }

  async function request(payload = null) {
    const options = { cache: 'no-store', credentials: 'same-origin' };
    if (payload) {
      options.method = 'POST';
      options.headers = { 'Content-Type': 'application/json' };
      options.body = JSON.stringify(payload);
    }
    const response = await fetch(AUTH_URL, options);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(body.error || ('Lokale login mislukt (' + response.status + ')'));
      error.status = response.status;
      error.body = body;
      throw error;
    }
    return body;
  }

  function installCompatibilitySession(session) {
    const user = session && session.user ? session.user : {};
    const email = String(user.email || '');
    const firstName = String(user.firstName || '');
    const lastName = String(user.lastName || '');
    const fullName = String(user.fullName || [firstName, lastName].filter(Boolean).join(' ') || email || 'Gebruiker');

    // Een kleine lokale compatibiliteitslaag zodat bestaande offline/sync-code
    // niet op Clerk hoeft te worden herschreven.
    window.Clerk = {
      isSignedIn: true,
      user: {
        id: String(user.id || ''),
        firstName,
        lastName,
        fullName,
        username: email,
        publicMetadata: { role: String((session && session.role) || user.role || 'gebruiker') },
        primaryEmailAddress: { emailAddress: email },
        emailAddresses: [{ emailAddress: email }],
      },
      session: { getToken: async () => 'synology-local-session' },
    };
  }

  function setAccount(session) {
    const user = session && session.user ? session.user : {};
    const name = String(user.fullName || [user.firstName, user.lastName].filter(Boolean).join(' ') || user.email || 'Gebruiker');
    const role = String((session && (session.roleLabel || session.role)) || user.role || 'Gebruiker');
    const roleId = String((session && session.role) || user.role || '').toLowerCase();
    const nameEl = document.getElementById('accountDisplayName');
    const roleEl = document.getElementById('accountDisplayRole');
    if (nameEl) nameEl.textContent = name;
    if (roleEl) roleEl.textContent = role;

    // De eerste lokale eigenaar is de vaste hoofdbeheerder. Zorg dat een
    // bestaande browsercache/sessie Beheer nooit per ongeluk kan blokkeren.
    if (roleId === 'beheerder' || user.isOwner === true) {
      window.machineparkIsAdmin = true;
      window.machineparkRole = 'beheerder';
      if (window.machineparkPermissions && typeof window.machineparkPermissions === 'object') {
        window.machineparkPermissions['view.settings'] = true;
      }
    }
  }

  async function databaseStatus() {
    const response = await fetch(CENTRAL_SYNC_URL, {
      method: 'GET',
      headers: await centralHeaders(false),
      cache: 'no-store',
      credentials: 'same-origin',
    });
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) throw new Error('De lokale sessie is niet meer geldig.');
    if (!response.ok) throw new Error(body.error || ('Lokale databasecontrole mislukt (' + response.status + ')'));
    return body;
  }

  function showMigrationRequired() {
    const { gate, shell, loading, form } = els();
    if (shell) shell.style.display = 'none';
    if (gate) gate.classList.remove('hidden');
    if (loading) loading.style.display = 'none';
    if (!form) return;

    form.innerHTML =
      '<div style="width:100%;max-width:440px">' +
        '<div class="auth-error show" style="display:block">' +
          '<strong>Lokale database nog niet overgezet.</strong><br><br>' +
          'Maak eerst in de huidige online Machinepark-app een back-up en importeer die via de lokale migratiepagina.' +
        '</div>' +
        '<a class="btn primary" style="display:inline-block;margin-top:14px;text-decoration:none" href="./synology/migrate-data.php">Migratie openen</a>' +
      '</div>';
  }

  async function enterApp(session) {
    installCompatibilitySession(session);
    setAccount(session);
    if (typeof window.applyMachineparkServerAccess === 'function') {
      window.applyMachineparkServerAccess(session);
    }

    const db = await databaseStatus();
    if (!db.exists || !db.initialized) {
      showMigrationRequired();
      return;
    }

    const { gate, shell, loading } = els();
    if (gate) gate.classList.add('hidden');
    if (shell) shell.style.display = 'block';
    if (loading) loading.style.display = 'none';
    await startKoffieServiceApp();
  }

  function renderLogin() {
    clearError();
    const { form, loading } = els();
    if (loading) loading.style.display = 'none';
    if (!form) return;

    form.innerHTML =
      '<form id="localLoginForm" style="width:100%;max-width:440px;display:grid;gap:12px">' +
        '<div class="field"><label>E-mailadres</label><input name="email" type="email" autocomplete="username" required></div>' +
        '<div class="field"><label>Wachtwoord</label><input name="password" type="password" autocomplete="current-password" required></div>' +
        '<button class="btn primary" type="submit">Aanmelden</button>' +
      '</form>';

    const login = document.getElementById('localLoginForm');
    login.onsubmit = async (event) => {
      event.preventDefault();
      clearError();
      const button = login.querySelector('button[type=submit]');
      button.disabled = true;
      try {
        const fd = new FormData(login);
        const result = await request({
          action: 'login',
          email: String(fd.get('email') || '').trim(),
          password: String(fd.get('password') || ''),
        });
        await enterApp(result.session);
      } catch (error) {
        showError(error.message);
      } finally {
        button.disabled = false;
      }
    };
  }

  function renderSetup() {
    clearError();
    const { form, loading } = els();
    if (loading) loading.style.display = 'none';
    if (!form) return;

    form.innerHTML =
      '<form id="localSetupForm" style="width:100%;max-width:440px;display:grid;gap:12px">' +
        '<div style="text-align:left;margin-bottom:4px"><strong>Eerste lokale beheerder</strong><div class="muted" style="font-size:12px;margin-top:4px">Dit account wordt uitsluitend op je Synology opgeslagen.</div></div>' +
        '<div class="form-grid">' +
          '<div class="field"><label>Voornaam</label><input name="firstName" autocomplete="given-name"></div>' +
          '<div class="field"><label>Achternaam</label><input name="lastName" autocomplete="family-name"></div>' +
        '</div>' +
        '<div class="field"><label>E-mailadres</label><input name="email" type="email" autocomplete="username" required></div>' +
        '<div class="field"><label>Wachtwoord</label><input name="password" type="password" minlength="10" autocomplete="new-password" required><div class="muted" style="font-size:11px;margin-top:4px">Minstens 10 tekens.</div></div>' +
        '<div class="field"><label>Wachtwoord herhalen</label><input name="password2" type="password" minlength="10" autocomplete="new-password" required></div>' +
        '<button class="btn primary" type="submit">Lokale beheerder aanmaken</button>' +
      '</form>';

    const setup = document.getElementById('localSetupForm');
    setup.onsubmit = async (event) => {
      event.preventDefault();
      clearError();
      const fd = new FormData(setup);
      const password = String(fd.get('password') || '');
      if (password !== String(fd.get('password2') || '')) {
        showError('De twee wachtwoorden zijn niet gelijk.');
        return;
      }
      const button = setup.querySelector('button[type=submit]');
      button.disabled = true;
      try {
        const result = await request({
          action: 'setup',
          firstName: String(fd.get('firstName') || '').trim(),
          lastName: String(fd.get('lastName') || '').trim(),
          email: String(fd.get('email') || '').trim(),
          password,
        });
        await enterApp(result.session);
      } catch (error) {
        showError(error.message);
      } finally {
        button.disabled = false;
      }
    };
  }

  async function boot() {
    try {
      const status = await request();
      if (status.signedIn && status.session) {
        await enterApp(status.session);
      } else if (status.initialized) {
        renderLogin();
      } else {
        renderSetup();
      }
    } catch (error) {
      if (error.status === 403) {
        showError('Open Machinepark voorlopig via het lokale IP-adres van je Synology. Externe toegang zetten we later veilig op HTTPS.');
      } else {
        showError(error.message || 'De lokale Synology-login kon niet worden gestart.');
      }
    }

    const logout = els().logout;
    if (logout) {
      logout.onclick = async () => {
        logout.disabled = true;
        try { await request({ action: 'logout' }); } catch (_) {}
        location.reload();
      };
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
