<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('X-Content-Type-Options: nosniff');

function action_users_json(array $body, int $status = 200): void {
    http_response_code($status);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

try {
    mp_auth_require_request_access();
} catch (Throwable $e) {
    action_users_json(mp_auth_access_error_payload($e), 403);
}

try {
    $currentUser = mp_auth_require_user();
} catch (Throwable $e) {
    action_users_json(['error'=>'Niet aangemeld.'], 401);
}

if (strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET')) !== 'GET') {
    action_users_json(['error'=>'Methode niet toegestaan.'], 405);
}

$users = [];
foreach (mp_auth_read_users() as $user) {
    if (!is_array($user) || !empty($user['disabled'])) continue;
    $public = mp_auth_public_user($user);
    $role = !empty($user['isOwner']) ? 'beheerder' : (string)($user['role'] ?? 'gebruiker');
    $users[] = [
        'id'=>(string)($public['id'] ?? ''),
        'email'=>(string)($public['email'] ?? ''),
        'firstName'=>(string)($public['firstName'] ?? ''),
        'lastName'=>(string)($public['lastName'] ?? ''),
        'fullName'=>(string)($public['fullName'] ?? ''),
        'role'=>$role,
        'roleLabel'=>mp_role_label($role, !empty($user['isOwner'])),
    ];
}

usort($users, function ($a, $b) {
    return strcasecmp((string)($a['fullName'] ?: $a['email']), (string)($b['fullName'] ?: $b['email']));
});

action_users_json([
    'users'=>$users,
    'currentUserId'=>(string)($currentUser['id'] ?? ''),
    'mode'=>'synology-local',
]);
