<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';
require_once __DIR__ . '/_audit-lib.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('X-Content-Type-Options: nosniff');

define('MP_USERS_LOCK_FILE', '/volume1/MachineparkData/data/users.lock');
define('MP_CLOUD_USERS_FILE', '/volume1/MachineparkData/data/cloud-users-v1.json');

function user_json(array $body, int $status = 200): void {
    http_response_code($status);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function user_can_manage(array $user): bool {
    if (!empty($user['isOwner'])) return true;
    $permissions = mp_role_permissions((string)($user['role'] ?? 'gebruiker'));
    return !empty($permissions['users.manage']);
}

function user_public_admin(array $user): array {
    $public = mp_auth_public_user($user);
    $public['role'] = !empty($user['isOwner']) ? 'beheerder' : (string)($user['role'] ?? 'gebruiker');
    $public['lastSignInAt'] = $user['lastSignInAt'] ?? null;
    $public['createdAt'] = $user['createdAt'] ?? null;
    $public['disabled'] = !empty($user['disabled']);
    $public['needsPassword'] = empty($user['isOwner']) && trim((string)($user['passwordHash'] ?? '')) === '';
    $public['importedReference'] = !empty($user['importedReference']);
    return $public;
}

function user_owner_email(array $users): string {
    foreach ($users as $user) if (!empty($user['isOwner'])) return (string)($user['email'] ?? '');
    return '';
}

function user_find_index(array $users, string $id): int {
    foreach ($users as $index => $user) if ((string)($user['id'] ?? '') === $id) return (int)$index;
    return -1;
}

function user_lock() {
    $dir = dirname(MP_USERS_LOCK_FILE);
    if (!is_dir($dir) || !is_writable($dir)) throw new RuntimeException('Machinepark gebruikersmap is niet schrijfbaar.');
    $lock = @fopen(MP_USERS_LOCK_FILE, 'c+');
    if ($lock === false) throw new RuntimeException('Gebruikerslock kon niet worden geopend.');
    if (!flock($lock, LOCK_EX)) {
        fclose($lock);
        throw new RuntimeException('Gebruikerslock kon niet worden verkregen.');
    }
    return $lock;
}

function user_unlock($lock): void {
    if (is_resource($lock)) {
        @flock($lock, LOCK_UN);
        @fclose($lock);
    }
}

function user_normalize_username($value): string {
    return strtolower(trim((string)$value));
}

function user_validate_username(string $username): void {
    if ($username === '') return;
    if (strlen($username) < 3 || strlen($username) > 60) throw new RuntimeException('Een gebruikersnaam moet tussen 3 en 60 tekens bevatten.');
    if (!preg_match('/^[a-z0-9._-]+$/', $username)) throw new RuntimeException('Gebruik in de gebruikersnaam alleen letters, cijfers, punt, streepje of underscore.');
    if ($username === 'admin') throw new RuntimeException('De gebruikersnaam admin is voorbehouden voor de vaste hoofdbeheerder.');
}

function user_assert_unique(array $users, string $email, string $username, string $exceptId = ''): void {
    foreach ($users as $user) {
        if ($exceptId !== '' && (string)($user['id'] ?? '') === $exceptId) continue;
        $existingEmail = strtolower(trim((string)($user['email'] ?? '')));
        $existingUsername = user_normalize_username($user['username'] ?? '');
        if ($email !== '' && $existingEmail !== '' && hash_equals($existingEmail, $email)) throw new RuntimeException('Er bestaat al een gebruiker met dit e-mailadres.');
        if ($username !== '' && $existingUsername !== '' && hash_equals($existingUsername, $username)) throw new RuntimeException('Er bestaat al een gebruiker met deze gebruikersnaam.');
    }
}

function user_permissions(array $user): array {
    if (!empty($user['isOwner'])) return mp_role_permission_set('all');
    return mp_role_permissions((string)($user['role'] ?? 'gebruiker'));
}

function user_permissions_subset(array $candidate, array $allowed): bool {
    foreach ($candidate as $key => $enabled) if ($enabled && empty($allowed[$key])) return false;
    return true;
}

function user_assert_target_manageable(array $actor, array $target): void {
    if (!empty($actor['isOwner'])) return;
    if (!empty($target['isOwner'])) throw new RuntimeException('De vaste hoofdbeheerder kan alleen zichzelf beheren.');
    if (!user_permissions_subset(user_permissions($target), user_permissions($actor))) {
        throw new RuntimeException('Je kunt geen gebruiker beheren met meer rechten dan je eigen rol.');
    }
}

function user_assert_role_assignable(array $actor, string $role): void {
    if (!mp_role_exists($role)) throw new RuntimeException('De gekozen rol bestaat niet.');
    if (!empty($actor['isOwner'])) return;
    if (!user_permissions_subset(mp_role_permissions($role), user_permissions($actor))) {
        throw new RuntimeException('Je kunt geen rol toewijzen met meer rechten dan je eigen rol.');
    }
}

function user_cloud_reference_users(): array {
    if (!is_file(MP_CLOUD_USERS_FILE)) return [];
    $raw = @file_get_contents(MP_CLOUD_USERS_FILE);
    $data = $raw !== false ? json_decode($raw, true) : null;
    if (!is_array($data) || !isset($data['users']) || !is_array($data['users'])) return [];
    return array_values(array_filter($data['users'], 'is_array'));
}

function user_sync_cloud_references(array $users): array {
    $byEmail = [];
    foreach ($users as $user) {
        $email = strtolower(trim((string)($user['email'] ?? '')));
        if ($email !== '') $byEmail[$email] = true;
    }
    $added = 0;
    foreach (user_cloud_reference_users() as $source) {
        $email = strtolower(trim((string)($source['email'] ?? '')));
        if ($email === '' || !filter_var($email, FILTER_VALIDATE_EMAIL) || isset($byEmail[$email])) continue;
        $role = mp_role_sanitize_id($source['role'] ?? 'gebruiker');
        if (!mp_role_exists($role) || $role === 'beheerder') $role = 'gebruiker';
        $users[] = [
            'id'=>'usr_cloud_' . substr(hash('sha256', $email), 0, 20),
            'username'=>'',
            'email'=>$email,
            'firstName'=>trim((string)($source['firstName'] ?? '')),
            'lastName'=>trim((string)($source['lastName'] ?? '')),
            'passwordHash'=>'',
            'role'=>$role,
            'isOwner'=>false,
            'createdAt'=>(string)($source['createdAt'] ?? date(DATE_ATOM)),
            'lastSignInAt'=>null,
            'disabled'=>true,
            'importedReference'=>true,
        ];
        $byEmail[$email] = true;
        $added++;
    }
    return ['users'=>$users,'added'=>$added];
}

try { mp_auth_require_request_access(); }
catch (Throwable $e) { user_json(mp_auth_access_error_payload($e), 403); }

try { $currentUser = mp_auth_require_user(); }
catch (Throwable $e) { user_json(['error'=>'Niet aangemeld.'], 401); }

if (!user_can_manage($currentUser)) user_json(['error'=>'Deze rol mag gebruikers niet beheren.'], 403);

$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));

if ($method === 'GET') {
    $lock = null;
    try {
        $lock = user_lock();
        $users = mp_auth_read_users();
        $sync = user_sync_cloud_references($users);
        $users = $sync['users'];
        if ((int)$sync['added'] > 0) mp_auth_write_users($users);
        user_unlock($lock);
        $lock = null;
    } catch (Throwable $e) {
        if (isset($lock)) user_unlock($lock);
        user_json(['error'=>$e->getMessage()], 400);
    }

    usort($users, function ($a, $b) {
        if (!empty($a['isOwner']) !== !empty($b['isOwner'])) return !empty($a['isOwner']) ? -1 : 1;
        $aName = trim(((string)($a['firstName'] ?? '')) . ' ' . ((string)($a['lastName'] ?? '')));
        $bName = trim(((string)($b['firstName'] ?? '')) . ' ' . ((string)($b['lastName'] ?? '')));
        $cmp = strcasecmp($aName, $bName);
        return $cmp !== 0 ? $cmp : strcasecmp((string)($a['email'] ?? ''), (string)($b['email'] ?? ''));
    });
    user_json([
        'users'=>array_map('user_public_admin', $users),
        'invitations'=>[],
        'currentUserId'=>(string)($currentUser['id'] ?? ''),
        'adminEmail'=>user_owner_email($users),
        'roles'=>array_map(function ($role) { return ['value'=>$role['id'],'label'=>$role['label']]; }, mp_role_read_config()['roles']),
        'importedReferencesAdded'=>(int)($sync['added'] ?? 0),
        'mode'=>'synology-local',
    ]);
}

if ($method !== 'POST' && $method !== 'DELETE') user_json(['error'=>'Methode niet toegestaan.'], 405);

$raw = file_get_contents('php://input');
$body = json_decode($raw === false ? '' : $raw, true);
if (!is_array($body)) $body = [];

try {
    $lock = user_lock();
    $users = mp_auth_read_users();

    if ($method === 'DELETE') {
        $userId = trim((string)($body['userId'] ?? ''));
        $index = user_find_index($users, $userId);
        if ($index < 0) throw new RuntimeException('Gebruiker niet gevonden.');
        $target = $users[$index];
        if (!empty($target['isOwner'])) throw new RuntimeException('De vaste hoofdbeheerder kan niet worden verwijderd.');
        if ((string)($target['id'] ?? '') === (string)($currentUser['id'] ?? '')) throw new RuntimeException('Je kunt je eigen actieve account niet verwijderen.');
        user_assert_target_manageable($currentUser, $target);
        array_splice($users, $index, 1);
        mp_auth_write_users($users);
        user_unlock($lock); unset($lock);
        try { mp_audit_append($currentUser, [[
            'entityType'=>'Gebruikersbeheer','entityId'=>$userId,
            'entityLabel'=>(string)($target['email'] ?? ($target['username'] ?? 'Gebruiker')),
            'action'=>'verwijderd','fields'=>[['field'=>'Rol','before'=>mp_role_label((string)($target['role'] ?? 'gebruiker')),'after'=>'—']],
        ]]); } catch (Throwable $e) {}
        user_json(['ok'=>true]);
    }

    $action = (string)($body['action'] ?? '');

    if ($action === 'create-user') {
        $email = strtolower(trim((string)($body['email'] ?? '')));
        $username = user_normalize_username($body['username'] ?? '');
        $password = (string)($body['password'] ?? '');
        $role = mp_role_sanitize_id($body['role'] ?? 'gebruiker');
        $firstName = trim((string)($body['firstName'] ?? ''));
        $lastName = trim((string)($body['lastName'] ?? ''));
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) throw new RuntimeException('Vul een geldig e-mailadres in.');
        user_validate_username($username);
        if (strlen($password) < 10) throw new RuntimeException('Gebruik een eerste wachtwoord van minstens 10 tekens.');
        if (strlen($firstName) > 100 || strlen($lastName) > 100) throw new RuntimeException('Naam is te lang.');
        user_assert_role_assignable($currentUser, $role);
        user_assert_unique($users, $email, $username);
        $newUser = [
            'id'=>'usr_' . bin2hex(random_bytes(10)),'username'=>$username,'email'=>$email,
            'firstName'=>$firstName,'lastName'=>$lastName,'passwordHash'=>password_hash($password, PASSWORD_DEFAULT),
            'role'=>$role,'isOwner'=>false,'createdAt'=>date(DATE_ATOM),'lastSignInAt'=>null,'disabled'=>false,
        ];
        $users[] = $newUser;
        mp_auth_write_users($users);
        user_unlock($lock); unset($lock);
        try { mp_audit_append($currentUser, [[
            'entityType'=>'Gebruikersbeheer','entityId'=>$newUser['id'],'entityLabel'=>$email,'action'=>'toegevoegd',
            'fields'=>[['field'=>'Rol','before'=>'—','after'=>mp_role_label($role)],['field'=>'Gebruikersnaam','before'=>'—','after'=>$username !== '' ? $username : 'e-mailadres']],
        ]]); } catch (Throwable $e) {}
        user_json(['ok'=>true,'user'=>user_public_admin($newUser)]);
    }

    if ($action === 'update-user') {
        $userId = trim((string)($body['userId'] ?? ''));
        $index = user_find_index($users, $userId);
        if ($index < 0) throw new RuntimeException('Gebruiker niet gevonden.');
        $target = $users[$index];
        $before = $target;
        user_assert_target_manageable($currentUser, $target);

        $target['firstName'] = trim((string)($body['firstName'] ?? ($target['firstName'] ?? '')));
        $target['lastName'] = trim((string)($body['lastName'] ?? ($target['lastName'] ?? '')));
        if (strlen((string)$target['firstName']) > 100 || strlen((string)$target['lastName']) > 100) throw new RuntimeException('Naam is te lang.');

        $newEmail = strtolower(trim((string)($body['email'] ?? ($target['email'] ?? ''))));
        if ($newEmail !== '' && !filter_var($newEmail, FILTER_VALIDATE_EMAIL)) throw new RuntimeException('Vul een geldig e-mailadres in.');
        if (empty($target['isOwner']) && $newEmail === '') throw new RuntimeException('Een gewone gebruiker moet een e-mailadres hebben.');
        $newUsername = user_normalize_username($body['username'] ?? ($target['username'] ?? ''));
        if (!empty($target['isOwner'])) $newUsername = 'admin'; else user_validate_username($newUsername);
        user_assert_unique($users, $newEmail, $newUsername, $userId);
        $target['email'] = $newEmail;
        $target['username'] = $newUsername;

        if (!empty($target['isOwner'])) {
            $target['role'] = 'beheerder';
            $target['disabled'] = false;
        } else {
            $role = mp_role_sanitize_id($body['role'] ?? ($target['role'] ?? 'gebruiker'));
            user_assert_role_assignable($currentUser, $role);
            if ((string)($target['id'] ?? '') === (string)($currentUser['id'] ?? '') && $role !== (string)($target['role'] ?? 'gebruiker') && empty($currentUser['isOwner'])) {
                throw new RuntimeException('Je kunt je eigen rol niet wijzigen. Laat dit door de hoofdbeheerder doen.');
            }
            $target['role'] = $role;
        }

        $newPassword = (string)($body['password'] ?? '');
        if ($newPassword !== '') {
            if (strlen($newPassword) < 10) throw new RuntimeException('Een nieuw wachtwoord moet minstens 10 tekens bevatten.');
            $target['passwordHash'] = password_hash($newPassword, PASSWORD_DEFAULT);
            $target['importedReference'] = false;
        }

        $users[$index] = $target;
        mp_auth_write_users($users);
        user_unlock($lock); unset($lock);

        $fields = [];
        if ((string)($before['firstName'] ?? '') !== (string)$target['firstName']) $fields[] = ['field'=>'Voornaam','before'=>(string)($before['firstName'] ?? '—'),'after'=>(string)$target['firstName']];
        if ((string)($before['lastName'] ?? '') !== (string)$target['lastName']) $fields[] = ['field'=>'Achternaam','before'=>(string)($before['lastName'] ?? '—'),'after'=>(string)$target['lastName']];
        if ((string)($before['email'] ?? '') !== (string)$target['email']) $fields[] = ['field'=>'E-mailadres','before'=>(string)($before['email'] ?? '—'),'after'=>(string)($target['email'] ?: '—')];
        if ((string)($before['username'] ?? '') !== (string)$target['username']) $fields[] = ['field'=>'Gebruikersnaam','before'=>(string)($before['username'] ?? '—'),'after'=>(string)($target['username'] ?: '—')];
        if ((string)($before['role'] ?? '') !== (string)$target['role']) $fields[] = ['field'=>'Rol','before'=>mp_role_label((string)($before['role'] ?? 'gebruiker')),'after'=>mp_role_label((string)$target['role'])];
        if ($newPassword !== '') $fields[] = ['field'=>'Wachtwoord','before'=>'••••••••••','after'=>'gewijzigd'];
        if (!$fields) $fields[] = ['field'=>'Gebruiker','before'=>'ongewijzigd','after'=>'opgeslagen'];
        try { mp_audit_append($currentUser, [[
            'entityType'=>'Gebruikersbeheer','entityId'=>$userId,
            'entityLabel'=>(string)($target['email'] ?: ($target['username'] ?? 'Gebruiker')),
            'action'=>'aangepast','fields'=>$fields,
        ]]); } catch (Throwable $e) {}
        user_json(['ok'=>true,'user'=>user_public_admin($target)]);
    }

    if ($action === 'toggle-user') {
        $userId = trim((string)($body['userId'] ?? ''));
        $disabled = !empty($body['disabled']);
        $index = user_find_index($users, $userId);
        if ($index < 0) throw new RuntimeException('Gebruiker niet gevonden.');
        $target = $users[$index];
        if (!empty($target['isOwner'])) throw new RuntimeException('De vaste hoofdbeheerder kan niet worden geblokkeerd.');
        if ($disabled && (string)($target['id'] ?? '') === (string)($currentUser['id'] ?? '')) throw new RuntimeException('Je kunt je eigen actieve account niet blokkeren.');
        user_assert_target_manageable($currentUser, $target);
        if (!$disabled && trim((string)($target['passwordHash'] ?? '')) === '') {
            throw new RuntimeException('Stel eerst via Bewerken een lokaal wachtwoord in voordat je deze gebruiker activeert.');
        }
        $beforeDisabled = !empty($target['disabled']);
        $target['disabled'] = $disabled;
        $users[$index] = $target;
        mp_auth_write_users($users);
        user_unlock($lock); unset($lock);
        if ($beforeDisabled !== $disabled) {
            try { mp_audit_append($currentUser, [[
                'entityType'=>'Gebruikersbeheer','entityId'=>$userId,
                'entityLabel'=>(string)($target['email'] ?: ($target['username'] ?? 'Gebruiker')),
                'action'=>$disabled ? 'geblokkeerd' : 'geactiveerd',
                'fields'=>[['field'=>'Toegang','before'=>$beforeDisabled ? 'Geblokkeerd' : 'Actief','after'=>$disabled ? 'Geblokkeerd' : 'Actief']],
            ]]); } catch (Throwable $e) {}
        }
        user_json(['ok'=>true,'user'=>user_public_admin($target)]);
    }

    user_unlock($lock); unset($lock);
    user_json(['error'=>'Onbekende gebruikersactie.'], 400);
} catch (Throwable $e) {
    if (isset($lock)) user_unlock($lock);
    $message = $e->getMessage();
    $status = strpos($message, 'niet gevonden') !== false ? 404 : 400;
    user_json(['error'=>$message], $status);
}
