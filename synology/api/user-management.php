<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';
require_once __DIR__ . '/_audit-lib.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('X-Content-Type-Options: nosniff');

define('MP_USERS_LOCK_FILE', '/volume1/MachineparkData/data/users.lock');

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
    $lock = @fopen(MP_USERS_LOCK_FILE, 'c+');
    if ($lock === false) throw new RuntimeException('Gebruikerslock kon niet worden geopend.');
    if (!flock($lock, LOCK_EX)) {
        fclose($lock);
        throw new RuntimeException('Gebruikerslock kon niet worden verkregen.');
    }
    return $lock;
}

if (!mp_auth_is_local_ip(mp_auth_client_ip())) {
    user_json(['error'=>'Lokaal gebruikersbeheer is tijdens de opbouw alleen via het lokale netwerk bereikbaar.'], 403);
}

try {
    $currentUser = mp_auth_require_user();
} catch (Throwable $e) {
    user_json(['error'=>'Niet aangemeld.'], 401);
}

if (!user_can_manage($currentUser)) {
    user_json(['error'=>'Deze rol mag gebruikers niet beheren.'], 403);
}

$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));

if ($method === 'GET') {
    $users = mp_auth_read_users();
    usort($users, function ($a, $b) {
        if (!empty($a['isOwner']) !== !empty($b['isOwner'])) return !empty($a['isOwner']) ? -1 : 1;
        return strcasecmp((string)($a['email'] ?? ''), (string)($b['email'] ?? ''));
    });
    user_json([
        'users'=>array_map('user_public_admin', $users),
        'invitations'=>[],
        'currentUserId'=>(string)($currentUser['id'] ?? ''),
        'adminEmail'=>user_owner_email($users),
        'roles'=>array_map(function ($role) { return ['value'=>$role['id'],'label'=>$role['label']]; }, mp_role_read_config()['roles']),
        'mode'=>'synology-local',
    ]);
}

if ($method !== 'POST' && $method !== 'DELETE') {
    user_json(['error'=>'Methode niet toegestaan.'], 405);
}

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

        array_splice($users, $index, 1);
        mp_auth_write_users($users);
        flock($lock, LOCK_UN);
        fclose($lock);

        try {
            mp_audit_append($currentUser, [[
                'entityType'=>'Gebruikersbeheer',
                'entityId'=>$userId,
                'entityLabel'=>(string)($target['email'] ?? 'Gebruiker'),
                'action'=>'verwijderd',
                'fields'=>[['field'=>'Rol','before'=>mp_role_label((string)($target['role'] ?? 'gebruiker')),'after'=>'—']],
            ]]);
        } catch (Throwable $e) {}
        user_json(['ok'=>true]);
    }

    $action = (string)($body['action'] ?? '');

    if ($action === 'create-user') {
        $email = strtolower(trim((string)($body['email'] ?? '')));
        $password = (string)($body['password'] ?? '');
        $role = mp_role_sanitize_id($body['role'] ?? 'gebruiker');
        $firstName = trim((string)($body['firstName'] ?? ''));
        $lastName = trim((string)($body['lastName'] ?? ''));

        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) throw new RuntimeException('Vul een geldig e-mailadres in.');
        if (strlen($password) < 10) throw new RuntimeException('Gebruik een eerste wachtwoord van minstens 10 tekens.');
        if (!mp_role_exists($role)) throw new RuntimeException('De gekozen rol bestaat niet.');

        foreach ($users as $user) {
            if (strtolower((string)($user['email'] ?? '')) === $email) throw new RuntimeException('Er bestaat al een gebruiker met dit e-mailadres.');
        }

        $newUser = [
            'id'=>'usr_' . bin2hex(random_bytes(10)),
            'email'=>$email,
            'firstName'=>$firstName,
            'lastName'=>$lastName,
            'passwordHash'=>password_hash($password, PASSWORD_DEFAULT),
            'role'=>$role,
            'isOwner'=>false,
            'createdAt'=>date(DATE_ATOM),
            'lastSignInAt'=>null,
            'disabled'=>false,
        ];
        $users[] = $newUser;
        mp_auth_write_users($users);
        flock($lock, LOCK_UN);
        fclose($lock);

        try {
            mp_audit_append($currentUser, [[
                'entityType'=>'Gebruikersbeheer',
                'entityId'=>$newUser['id'],
                'entityLabel'=>$email,
                'action'=>'toegevoegd',
                'fields'=>[['field'=>'Rol','before'=>'—','after'=>mp_role_label($role)]],
            ]]);
        } catch (Throwable $e) {}
        user_json(['ok'=>true,'user'=>user_public_admin($newUser)]);
    }

    if ($action === 'update-user') {
        $userId = trim((string)($body['userId'] ?? ''));
        $index = user_find_index($users, $userId);
        if ($index < 0) throw new RuntimeException('Gebruiker niet gevonden.');
        $target = $users[$index];
        $before = $target;

        $target['firstName'] = trim((string)($body['firstName'] ?? ($target['firstName'] ?? '')));
        $target['lastName'] = trim((string)($body['lastName'] ?? ($target['lastName'] ?? '')));

        if (!empty($target['isOwner'])) {
            $target['role'] = 'beheerder';
        } else {
            $role = mp_role_sanitize_id($body['role'] ?? ($target['role'] ?? 'gebruiker'));
            if (!mp_role_exists($role)) throw new RuntimeException('De gekozen rol bestaat niet.');
            $target['role'] = $role;
        }

        $newPassword = (string)($body['password'] ?? '');
        if ($newPassword !== '') {
            if (strlen($newPassword) < 10) throw new RuntimeException('Een nieuw wachtwoord moet minstens 10 tekens bevatten.');
            $target['passwordHash'] = password_hash($newPassword, PASSWORD_DEFAULT);
        }

        $users[$index] = $target;
        mp_auth_write_users($users);
        flock($lock, LOCK_UN);
        fclose($lock);

        $fields = [];
        if ((string)($before['firstName'] ?? '') !== (string)$target['firstName']) $fields[] = ['field'=>'Voornaam','before'=>(string)($before['firstName'] ?? '—'),'after'=>(string)$target['firstName']];
        if ((string)($before['lastName'] ?? '') !== (string)$target['lastName']) $fields[] = ['field'=>'Achternaam','before'=>(string)($before['lastName'] ?? '—'),'after'=>(string)$target['lastName']];
        if ((string)($before['role'] ?? '') !== (string)$target['role']) $fields[] = ['field'=>'Rol','before'=>mp_role_label((string)($before['role'] ?? 'gebruiker')),'after'=>mp_role_label((string)$target['role'])];
        if ($newPassword !== '') $fields[] = ['field'=>'Wachtwoord','before'=>'••••••••••','after'=>'gewijzigd'];
        if (!$fields) $fields[] = ['field'=>'Gebruiker','before'=>'ongewijzigd','after'=>'opgeslagen'];
        try {
            mp_audit_append($currentUser, [[
                'entityType'=>'Gebruikersbeheer',
                'entityId'=>$userId,
                'entityLabel'=>(string)($target['email'] ?? 'Gebruiker'),
                'action'=>'aangepast',
                'fields'=>$fields,
            ]]);
        } catch (Throwable $e) {}
        user_json(['ok'=>true,'user'=>user_public_admin($target)]);
    }

    flock($lock, LOCK_UN);
    fclose($lock);
    user_json(['error'=>'Onbekende gebruikersactie.'], 400);
} catch (Throwable $e) {
    if (isset($lock) && is_resource($lock)) {
        @flock($lock, LOCK_UN);
        @fclose($lock);
    }
    $message = $e->getMessage();
    $status = strpos($message, 'niet gevonden') !== false ? 404 : 400;
    user_json(['error'=>$message], $status);
}
