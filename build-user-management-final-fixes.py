from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
USER_API = ROOT / 'synology/api/user-management.php'
MARKER = 'data-machinepark-build-fix="user-management-final-fixes-v1"'

index = INDEX.read_text(encoding='utf-8')
api = USER_API.read_text(encoding='utf-8')


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    return text.replace(old, new, 1)


# Backend: alleen rollen tonen die de actieve beheerder werkelijk mag toewijzen.
if 'function user_available_roles_for_actor' not in api:
    anchor = 'function user_cloud_reference_users(): array {'
    helper = '''function user_available_roles_for_actor(array $actor): array {
    $roles = mp_role_read_config()['roles'];
    if (!empty($actor['isOwner'])) return $roles;
    $allowed = user_permissions($actor);
    return array_values(array_filter($roles, function ($role) use ($allowed) {
        return user_permissions_subset((array)($role['permissions'] ?? []), $allowed);
    }));
}

function user_forget_cloud_reference(string $email): void {
    $email = strtolower(trim($email));
    if ($email === '' || !is_file(MP_CLOUD_USERS_FILE)) return;
    $raw = @file_get_contents(MP_CLOUD_USERS_FILE);
    $data = $raw !== false ? json_decode($raw, true) : null;
    if (!is_array($data)) return;
    $changed = false;
    foreach (['users','invitations'] as $key) {
        if (!isset($data[$key]) || !is_array($data[$key])) continue;
        $before = count($data[$key]);
        $data[$key] = array_values(array_filter($data[$key], function ($item) use ($email) {
            if (!is_array($item)) return true;
            return strtolower(trim((string)($item['email'] ?? ''))) !== $email;
        }));
        if (count($data[$key]) !== $before) $changed = true;
    }
    if (!$changed) return;
    $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false) throw new RuntimeException('Cloudgebruikersreferentie kon niet worden bijgewerkt.');
    $tmp = MP_CLOUD_USERS_FILE . '.tmp-' . bin2hex(random_bytes(5));
    if (@file_put_contents($tmp, $json, LOCK_EX) === false || !@rename($tmp, MP_CLOUD_USERS_FILE)) {
        @unlink($tmp);
        throw new RuntimeException('Verwijderde cloudgebruiker kon niet definitief uit de referentielijst worden gehaald.');
    }
}

'''
    if anchor not in api:
        raise SystemExit('Buildvalidatie mislukt: cloudgebruikersanker niet gevonden')
    api = api.replace(anchor, helper + anchor, 1)

api = replace_once(
    api,
    "        'roles'=>array_map(function ($role) { return ['value'=>$role['id'],'label'=>$role['label']]; }, mp_role_read_config()['roles']),",
    "        'roles'=>array_map(function ($role) { return ['value'=>$role['id'],'label'=>$role['label']]; }, user_available_roles_for_actor($currentUser)),\n        'currentUserIsOwner'=>!empty($currentUser['isOwner']),",
    'toewijsbare rollen in gebruikers-GET',
)

api = replace_once(
    api,
    "        user_assert_target_manageable($currentUser, $target);\n        array_splice($users, $index, 1);",
    "        user_assert_target_manageable($currentUser, $target);\n        // Voorkom dat een verwijderde, eerder geïmporteerde cloudgebruiker bij Vernieuwen terug verschijnt.\n        user_forget_cloud_reference((string)($target['email'] ?? ''));\n        array_splice($users, $index, 1);",
    'permanente verwijdering cloudreferentie',
)

USER_API.write_text(api, encoding='utf-8')

# Frontend: geïmporteerde accounts zonder lokaal wachtwoord duidelijk onderscheiden.
if MARKER not in index:
    style = '''
<style data-machinepark-build-fix="user-management-final-fixes-v1">
.user-status-setup{background:#fff4d8;color:#805c00}
.user-password-setup-btn{font-weight:800}
</style>
'''
    index = replace_once(index, '</head>', style + '</head>', 'Gebruikersbeheer statusstijl')

    old_badge = '''  function userStatusBadge(user) {
    if (user.isOwner) return '<span class="badge success">Hoofdbeheerder</span>';
    return user.disabled
      ? '<span class="badge user-status-disabled">Geblokkeerd</span>'
      : '<span class="badge user-status-active">Actief</span>';
  }
'''
    new_badge = '''  function userStatusBadge(user) {
    if (user.isOwner) return '<span class="badge success">Hoofdbeheerder</span>';
    if (user.needsPassword) return '<span class="badge user-status-setup">Lokaal wachtwoord instellen</span>';
    return user.disabled
      ? '<span class="badge user-status-disabled">Geblokkeerd</span>'
      : '<span class="badge user-status-active">Actief</span>';
  }
'''
    index = replace_once(index, old_badge, new_badge, 'statusbadge zonder wachtwoord')

    old_counts = '''      const active = window.machineparkAdminUsers.filter((u) => !u.disabled).length;
      const blocked = window.machineparkAdminUsers.filter((u) => u.disabled).length;
      if (status) status.textContent = `${window.machineparkAdminUsers.length} account(s) · ${active} actief${blocked ? ` · ${blocked} geblokkeerd` : ''}`;
'''
    new_counts = '''      const active = window.machineparkAdminUsers.filter((u) => !u.disabled).length;
      const setup = window.machineparkAdminUsers.filter((u) => u.needsPassword).length;
      const blocked = window.machineparkAdminUsers.filter((u) => u.disabled && !u.needsPassword).length;
      if (status) status.textContent = `${window.machineparkAdminUsers.length} account(s) · ${active} actief${setup ? ` · ${setup} lokaal wachtwoord instellen` : ''}${blocked ? ` · ${blocked} geblokkeerd` : ''}`;
'''
    index = replace_once(index, old_counts, new_counts, 'gebruikersaantallen')

    old_toggle = '''        const toggle = u.isOwner ? '' : `<button class="btn small" type="button" data-toggle-user="${esc(u.id)}" data-toggle-disabled="${u.disabled ? '0' : '1'}">${u.disabled ? 'Activeren' : 'Blokkeren'}</button>`;
'''
    new_toggle = '''        const toggle = u.isOwner ? '' : (u.needsPassword
          ? `<button class="btn small primary user-password-setup-btn" type="button" data-edit-user="${esc(u.id)}">Wachtwoord instellen</button>`
          : `<button class="btn small" type="button" data-toggle-user="${esc(u.id)}" data-toggle-disabled="${u.disabled ? '0' : '1'}">${u.disabled ? 'Activeren' : 'Blokkeren'}</button>`);
'''
    index = replace_once(index, old_toggle, new_toggle, 'wachtwoord instellen actie')

    old_access = "${u.isOwner ? 'De vaste hoofdbeheerder kan niet worden geblokkeerd of verwijderd.' : (u.disabled ? 'Dit account is momenteel geblokkeerd en kan niet aanmelden.' : 'Dit account is actief.')}"
    new_access = "${u.isOwner ? 'De vaste hoofdbeheerder kan niet worden geblokkeerd of verwijderd.' : (u.needsPassword ? 'Dit geïmporteerde account heeft nog geen lokaal wachtwoord. Stel hieronder een nieuw wachtwoord in en sla op; daarna kan het account worden geactiveerd.' : (u.disabled ? 'Dit account is momenteel geblokkeerd en kan niet aanmelden.' : 'Dit account is actief.'))}"
    index = replace_once(index, old_access, new_access, 'toegangstekst geïmporteerde gebruiker')

    # Een rol die alleen toegang tot ToDo, storingen of handleidingen heeft moet ook naar zo'n toegestane eerste pagina kunnen springen.
    index = replace_once(
        index,
        "    return ['dashboard','devices','maintenance','breakdowns','parts','settings'].find((view) => hasPermission(viewPermission(view))) || 'dashboard';",
        "    return ['dashboard','devices','maintenance','breakdowns','faults','manuals','actions','parts','settings'].find((view) => hasPermission(viewPermission(view))) || 'dashboard';",
        'eerste toegestane rolweergave',
    )

    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)

INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
built_api = USER_API.read_text(encoding='utf-8')
for needle in [
    MARKER,
    'Lokaal wachtwoord instellen',
    'Wachtwoord instellen',
    "'faults','manuals','actions'",
]:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: finale gebruikersfix ontbreekt ({needle})')
for needle in [
    'function user_available_roles_for_actor',
    'function user_forget_cloud_reference',
    'currentUserIsOwner',
    'user_forget_cloud_reference',
]:
    if needle not in built_api:
        raise SystemExit(f'Buildvalidatie mislukt: finale gebruikers-API-fix ontbreekt ({needle})')

print('[Machinepark] Gebruikersbeheer finaal: alle gekende accounts zichtbaar, veilige rollen en permanente verwijdering')
