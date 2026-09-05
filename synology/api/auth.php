<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('X-Content-Type-Options: nosniff');

define('MP_LOGIN_RATE_FILE', '/volume1/MachineparkData/data/login-rate-limit-v1.json');
define('MP_LOGIN_RATE_LOCK', '/volume1/MachineparkData/data/login-rate-limit-v1.lock');

function auth_json(array $body, int $status = 200): void {
    http_response_code($status);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function auth_rate_key(string $email): string {
    return hash('sha256', strtolower(trim($email)) . '|' . mp_auth_effective_client_ip());
}

function auth_rate_load(): array {
    if (!is_file(MP_LOGIN_RATE_FILE)) return [];
    $raw = @file_get_contents(MP_LOGIN_RATE_FILE);
    $data = $raw !== false ? json_decode($raw, true) : null;
    return is_array($data) ? $data : [];
}

function auth_rate_write(array $data): void {
    $dir = dirname(MP_LOGIN_RATE_FILE);
    if (!is_dir($dir) || !is_writable($dir)) return;
    $tmp = MP_LOGIN_RATE_FILE . '.tmp-' . bin2hex(random_bytes(4));
    $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false) return;
    if (@file_put_contents($tmp, $json, LOCK_EX) === false) return;
    if (!@rename($tmp, MP_LOGIN_RATE_FILE)) @unlink($tmp);
}

function auth_rate_with_lock(callable $callback) {
    $lock = @fopen(MP_LOGIN_RATE_LOCK, 'c+');
    if ($lock === false || !flock($lock, LOCK_EX)) {
        if (is_resource($lock)) fclose($lock);
        return $callback([]);
    }
    $data = auth_rate_load();
    $result = $callback($data);
    if (is_array($result) && array_key_exists('data', $result)) auth_rate_write($result['data']);
    flock($lock, LOCK_UN);
    fclose($lock);
    return $result;
}

function auth_rate_status(string $email): array {
    $key = auth_rate_key($email);
    $now = time();
    $window = 15 * 60;
    $limit = 8;
    $result = auth_rate_with_lock(function ($data) use ($key, $now, $window, $limit) {
        $events = [];
        foreach ((array)($data[$key] ?? []) as $ts) {
            $ts = (int)$ts;
            if ($ts > $now - $window && $ts <= $now + 5) $events[] = $ts;
        }
        if ($events) $data[$key] = array_values($events);
        else unset($data[$key]);
        $blocked = count($events) >= $limit;
        $retryAfter = $blocked ? max(1, ($events[0] + $window) - $now) : 0;
        return ['data'=>$data,'blocked'=>$blocked,'retryAfter'=>$retryAfter];
    });
    return is_array($result) ? $result : ['blocked'=>false,'retryAfter'=>0];
}

function auth_rate_fail(string $email): void {
    $key = auth_rate_key($email);
    $now = time();
    auth_rate_with_lock(function ($data) use ($key, $now) {
        $events = isset($data[$key]) && is_array($data[$key]) ? $data[$key] : [];
        $events[] = $now;
        $data[$key] = array_slice($events, -12);
        return ['data'=>$data];
    });
}

function auth_rate_success(string $email): void {
    $key = auth_rate_key($email);
    auth_rate_with_lock(function ($data) use ($key) {
        unset($data[$key]);
        return ['data'=>$data];
    });
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
        'access' => [
            'mode' => mp_auth_request_mode(),
            'host' => mp_auth_request_host(),
            'https' => mp_auth_request_is_https(),
            'publicHost' => mp_auth_is_public_host(mp_auth_request_host()),
        ],
    ]);
}

if ($method !== 'POST') auth_json(['error' => 'Methode niet toegestaan.'], 405);

$raw = file_get_contents('php://input');
$body = json_decode($raw === false ? '' : $raw, true);
$action = is_array($body) ? (string)($body['action'] ?? '') : '';

if ($action === 'setup') {
    if (count($users) > 0) auth_json(['error' => 'De lokale gebruikers zijn al ingesteld.'], 409);

    $username = 'admin';
    $email = strtolower(trim((string)($body['email'] ?? '')));
    $password = (string)($body['password'] ?? '');
    $firstName = trim((string)($body['firstName'] ?? ''));
    $lastName = trim((string)($body['lastName'] ?? ''));

    if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) auth_json(['error' => 'Vul een geldig e-mailadres in of laat het veld leeg.'], 400);
    if (strlen($password) < 10) auth_json(['error' => 'Gebruik een wachtwoord van minstens 10 tekens.'], 400);

    $id = 'usr_' . bin2hex(random_bytes(10));
    $user = [
        'id' => $id,
        'username' => $username,
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
    $identifier = strtolower(trim((string)($body['login'] ?? ($body['email'] ?? ''))));
    $password = (string)($body['password'] ?? '');
    if ($identifier === '') auth_json(['error'=>'Vul een gebruikersnaam of e-mailadres in.'],400);

    $rate = auth_rate_status($identifier);
    if (!empty($rate['blocked'])) {
        $retry = (int)($rate['retryAfter'] ?? 60);
        header('Retry-After: ' . $retry);
        auth_json(['error'=>'Te veel mislukte aanmeldpogingen. Probeer over enkele minuten opnieuw.','code'=>'login_rate_limited','retryAfter'=>$retry], 429);
    }

    $found = null;

    foreach ($users as $idx => $user) {
        $username = strtolower(trim((string)($user['username'] ?? '')));
        $email = strtolower(trim((string)($user['email'] ?? '')));
        $ownerAlias = $identifier === 'admin' && !empty($user['isOwner']);
        $usernameMatch = $username !== '' && hash_equals($username, $identifier);
        $emailMatch = $email !== '' && hash_equals($email, $identifier);
        if (!$ownerAlias && !$usernameMatch && !$emailMatch) continue;
        if (!empty($user['disabled'])) break;
        $hash = (string)($user['passwordHash'] ?? '');
        if ($hash !== '' && password_verify($password, $hash)) {
            if (!empty($user['isOwner']) && $username === '') {
                $users[$idx]['username'] = 'admin';
            }
            $users[$idx]['lastSignInAt'] = date(DATE_ATOM);
            $found = $users[$idx];
            mp_auth_write_users($users);
        }
        break;
    }

    if (!$found) {
        auth_rate_fail($identifier);
        usleep(350000);
        auth_json(['error' => 'Gebruikersnaam of wachtwoord is onjuist.'], 401);
    }

    auth_rate_success($identifier);
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
