from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="synology-local-admin-v1"'

def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)

if MARKER not in index:
    replace_once(
        "const USER_MANAGEMENT_URL='/.netlify/functions/user-management';",
        "const USER_MANAGEMENT_URL='./synology/api/user-management.php';",
        "gebruikersbeheer-URL",
    )
    replace_once(
        "const AUDIT_LOG_URL='/.netlify/functions/audit-log';",
        "const AUDIT_LOG_URL='./synology/api/audit-log.php';",
        "logboek-URL",
    )
    replace_once(
        "const ROLE_MANAGEMENT_URL = '/.netlify/functions/role-management';",
        "const ROLE_MANAGEMENT_URL = './synology/api/role-management.php';",
        "rollenbeheer-URL",
    )

    old_form = '''<form id="inviteUserForm" style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 14px">
            <input id="inviteUserEmail" type="email" required placeholder="E-mailadres nieuwe gebruiker" style="flex:1;min-width:240px;border:1px solid var(--line);border-radius:10px;padding:10px 11px">
            <button class="btn primary" type="submit">Gebruiker uitnodigen</button>
          </form>'''
    new_form = '''<form id="inviteUserForm" style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 14px">
            <input id="inviteUserEmail" type="email" required placeholder="E-mailadres nieuwe gebruiker" style="flex:1;min-width:220px;border:1px solid var(--line);border-radius:10px;padding:10px 11px">
            <input id="inviteUserPassword" type="password" required minlength="10" autocomplete="new-password" placeholder="Eerste wachtwoord (min. 10 tekens)" style="flex:1;min-width:220px;border:1px solid var(--line);border-radius:10px;padding:10px 11px">
            <button class="btn primary" type="submit">Gebruiker toevoegen</button>
          </form>'''
    replace_once(old_form, new_form, "lokaal gebruiker toevoegen-formulier")

    old_handler = """        const email = String(input?.value || '').trim().toLowerCase();
        if (!email) return;
        const role = String(roleSelect.value || 'gebruiker');"""
    new_handler = """        const email = String(input?.value || '').trim().toLowerCase();
        if (!email) return;
        const passwordInput = document.getElementById('inviteUserPassword');
        const password = String(passwordInput?.value || '');
        if (password.length < 10) { alert('Gebruik een eerste wachtwoord van minstens 10 tekens.'); return; }
        const role = String(roleSelect.value || 'gebruiker');"""
    replace_once(old_handler, new_handler, "lokaal gebruikerswachtwoord in handler")

    replace_once(
        "JSON.stringify({ action: 'invite', email, role })",
        "JSON.stringify({ action: 'create-user', email, password, role })",
        "lokale gebruiker-aanmaakactie",
    )
    replace_once(
        """          if (input) input.value = '';
          toast('Uitnodiging verstuurd');""",
        """          if (input) input.value = '';
          if (passwordInput) passwordInput.value = '';
          toast('Gebruiker toegevoegd');""",
        "lokale gebruikersfeedback",
    )

    # Optioneel lokaal wachtwoord wijzigen bij het bewerken van een gebruiker.
    password_anchor = '<div class="field full"><div class="alert"><strong>Rollen & rechten</strong>'
    password_field = '<div class="field full"><label>Nieuw wachtwoord</label><input name="password" type="password" minlength="10" autocomplete="new-password" placeholder="Leeg laten om niet te wijzigen"><div class="muted" style="font-size:11px;margin-top:4px">Minstens 10 tekens wanneer je het wachtwoord wijzigt.</div></div>' + password_anchor
    replace_once(password_anchor, password_field, "wachtwoordveld gebruikerseditor")

    replace_once(
        "lastName: val(fd, 'lastName'), role: newRole })",
        "lastName: val(fd, 'lastName'), role: newRole, password: val(fd, 'password') })",
        "wachtwoord in gebruikersupdate",
    )

    # Oude uitnodigingen bestaan lokaal niet.
    index = index.replace(
        '<div id="pendingInvitations" style="margin-top:14px"></div>',
        '<div id="pendingInvitations" style="display:none"></div>',
        1,
    )

    index = index.replace(
        "</head>",
        f'<meta {MARKER}><meta name="machinepark-admin-backend" content="synology-local">\n</head>',
        1,
    )
    index_path.write_text(index, encoding="utf-8")

built = index_path.read_text(encoding="utf-8")
required = [
    MARKER,
    "./synology/api/user-management.php",
    "./synology/api/audit-log.php",
    "./synology/api/role-management.php",
    "id=\"inviteUserPassword\"",
    "action: 'create-user'",
    "Gebruiker toevoegen",
]
for needle in required:
    if needle not in built:
        raise SystemExit(f"Buildvalidatie mislukt: lokaal Beheer ontbreekt ({needle})")

for forbidden in [
    "/.netlify/functions/user-management",
    "/.netlify/functions/audit-log",
    "/.netlify/functions/role-management",
    "Uitnodiging verstuurd",
]:
    if forbidden in built:
        raise SystemExit(f"Buildvalidatie mislukt: oude beheerafhankelijkheid blijft aanwezig ({forbidden})")

print("[Machinepark] gebruikers, rollen en logboek gekoppeld aan lokale Synology API")
