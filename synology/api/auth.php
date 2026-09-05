<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('X-Content-Type-Options: nosniff');

function auth_json(array $body, int $status = 200): void {
    http_response_code($status);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

try {
    mp_auth_require_request_access();
} catch (Throwable $e) {
    auth_json(mp_auth_access_error_payload($e), 403);
}

mp_auth_start_session();
$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));
$users = mp_auth_read_users();

if ($method === 'GET') {
    $user = mp_auth_current_user();
    auth_json([
        'initialized' => count($users) > 0,
        'signedIn' => $user !== null,
        'session' => $user ? mp_auth_access_payload($user) : null,
    ]);
}

if ($method !== 'POST') auth_json(['error' => 'Methode niet toegestaan.'], 405);

$raw = file_get_contents('php://input');
$body = json_decode($raw === false ? '' : $raw, true);
$action = is_array($body) ? (string)($body['action'] ?? '') : '';

if ($action === 'setup') {
    if (count($users) > 0) auth_json(['error' => 'De lokale gebruikers zijn al ingesteld.'], 409);

    $email = strtolower(trim((string)($body['email'] ?? '')));
    $password = (string)($body['password'] ?? '');
    $firstName = trim((string)($body['firstName'] ?? ''));
    $lastName = trim((string)($body['lastName'] ?? ''));

    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) auth_json(['error' => 'Vul een geldig e-mailadres in.'], 400);
    if (strlen($password) < 10) auth_json(['error' => 'Gebruik een wachtwoord van minstens 10 tekens.'], 400);

    $id = 'usr_' . bin2hex(random_bytes(10));
    $user = [
        'id' => $id,
        'email' => $email,
        'firstName' => $firstName,
        'lastName' => $lastName,
        'passwordHash' => password_hash($password, PASSWORD_DEFAULT),
        'role' => 'beheerder',
        'isOwner' => true,
        'createdAt' => date(DATE_ATOM),
        'lastSignInAt' => date(DATE_ATOM),
        'disabled' => false,
    ];
    mp_auth_write_users([$user]);
    session_regenerate_id(true);
    $_SESSION['machinepark_user_id'] = $id;
    auth_json(['ok' => true, 'signedIn' => true, 'session' => mp_auth_access_payload($user)]);
}

if ($action === 'login') {
    $email = strtolower(trim((string)($body['email'] ?? '')));
    $password = (string)($body['password'] ?? '');
    $found = null;

    foreach ($users as $idx => $user) {
        if (strtolower((string)($user['email'] ?? '')) !== $email) continue;
        if (!empty($user['disabled'])) break;
        $hash = (string)($user['passwordHash'] ?? '');
        if ($hash !== '' && password_verify($password, $hash)) {
            $found = $user;
            $users[$idx]['lastSignInAt'] = date(DATE_ATOM);
            $found = $users[$idx];
            mp_auth_write_users($users);
        }
        break;
    }

    if (!$found) {
        usleep(350000);
        auth_json(['error' => 'E-mailadres of wachtwoord is onjuist.'], 401);
    }

    session_regenerate_id(true);
    $_SESSION['machinepark_user_id'] = (string)$found['id'];
    auth_json(['ok' => true, 'signedIn' => true, 'session' => mp_auth_access_payload($found)]);
}

if ($action === 'logout') {
    unset($_SESSION['machinepark_user_id']);
    session_regenerate_id(true);
    auth_json(['ok' => true, 'signedIn' => false]);
}

auth_json(['error' => 'Onbekende actie.'], 400);
