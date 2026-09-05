<?php
declare(strict_types=1);

require_once __DIR__ . '/_role-lib.php';

define('MP_USERS_FILE', '/volume1/MachineparkData/data/users.json');

function mp_auth_client_ip(): string {
    return (string)($_SERVER['REMOTE_ADDR'] ?? '');
}

function mp_auth_is_local_ip(string $ip): bool {
    if ($ip === '127.0.0.1' || $ip === '::1') return true;
    if (strpos($ip, '10.') === 0 || strpos($ip, '192.168.') === 0) return true;
    $lower = strtolower($ip);
    if (strpos($lower, 'fc') === 0 || strpos($lower, 'fd') === 0 || strpos($lower, 'fe80:') === 0) return true;
    if (filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4)) {
        $long = ip2long($ip);
        $start = ip2long('172.16.0.0');
        $end = ip2long('172.31.255.255');
        if ($long !== false && $start !== false && $end !== false && $long >= $start && $long <= $end) return true;
    }
    return false;
}

function mp_auth_start_session(): void {
    if (session_status() === PHP_SESSION_ACTIVE) return;
    session_name('MACHINEPARKSESSID');
    $secure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off');
    // PHP 7.2-compatibel: gebruik de positionele signatuur.
    session_set_cookie_params(0, '/machinepark/', '', $secure, true);
    session_start();
}

function mp_auth_read_users(): array {
    if (!is_file(MP_USERS_FILE)) return [];
    $raw = @file_get_contents(MP_USERS_FILE);
    if ($raw === false || trim($raw) === '') return [];
    $data = json_decode($raw, true);
    return is_array($data) ? array_values(array_filter($data, 'is_array')) : [];
}

function mp_auth_write_users(array $users): void {
    $dir = dirname(MP_USERS_FILE);
    if (!is_dir($dir) || !is_writable($dir)) {
        throw new RuntimeException('Machinepark gebruikersmap is niet schrijfbaar.');
    }
    $json = json_encode(array_values($users), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false) throw new RuntimeException('Gebruikersbestand kon niet naar JSON worden omgezet.');
    $tmp = MP_USERS_FILE . '.tmp-' . bin2hex(random_bytes(5));
    if (@file_put_contents($tmp, $json, LOCK_EX) === false) {
        throw new RuntimeException('Tijdelijk gebruikersbestand kon niet worden geschreven.');
    }
    if (!@rename($tmp, MP_USERS_FILE)) {
        @unlink($tmp);
        throw new RuntimeException('Gebruikersbestand kon niet atomair worden vervangen.');
    }
}

function mp_auth_permission_keys(): array {
    return mp_role_permission_keys();
}

function mp_auth_permissions_for_role(string $role, bool $owner = false): array {
    return mp_role_permissions($role, $owner);
}

function mp_auth_public_user(array $user): array {
    return [
        'id' => (string)($user['id'] ?? ''),
        'email' => (string)($user['email'] ?? ''),
        'firstName' => (string)($user['firstName'] ?? ''),
        'lastName' => (string)($user['lastName'] ?? ''),
        'fullName' => trim(((string)($user['firstName'] ?? '')) . ' ' . ((string)($user['lastName'] ?? ''))),
        'role' => (string)($user['role'] ?? 'gebruiker'),
        'isOwner' => !empty($user['isOwner']),
    ];
}

function mp_auth_current_user(): ?array {
    mp_auth_start_session();
    $id = (string)($_SESSION['machinepark_user_id'] ?? '');
    if ($id === '') return null;
    foreach (mp_auth_read_users() as $user) {
        if ((string)($user['id'] ?? '') === $id && empty($user['disabled'])) return $user;
    }
    unset($_SESSION['machinepark_user_id']);
    return null;
}

function mp_auth_require_user(): array {
    $user = mp_auth_current_user();
    if (!$user) {
        throw new RuntimeException('Niet aangemeld.');
    }
    return $user;
}

function mp_auth_access_payload(array $user): array {
    $public = mp_auth_public_user($user);
    $owner = !empty($public['isOwner']);
    $role = $owner ? 'beheerder' : (string)$public['role'];
    $public['role'] = $role;
    return [
        'authMode' => 'synology-local',
        'role' => $role,
        'roleLabel' => mp_role_label($role, $owner),
        'permissions' => mp_auth_permissions_for_role($role, $owner),
        'user' => $public,
    ];
}
