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

function mp_auth_request_host(): string {
    $raw = strtolower(trim((string)($_SERVER['HTTP_HOST'] ?? '')));
    if ($raw === '') return '';
    if ($raw[0] === '[') {
        $end = strpos($raw, ']');
        if ($end !== false) return substr($raw, 1, $end - 1);
    }
    $parts = explode(':', $raw, 2);
    return rtrim($parts[0], '.');
}

function mp_auth_public_hosts(): array {
    // Voorlopig bewust slechts één extern adres. DuckDNS kan later veilig
    // worden toegevoegd zodra de Synology-migratie volledig is afgerond.
    return ['krisooms.synology.me'];
}

function mp_auth_is_public_host(string $host): bool {
    return in_array(strtolower(rtrim($host, '.')), mp_auth_public_hosts(), true);
}

function mp_auth_is_private_host(string $host): bool {
    $host = strtolower(trim($host));
    if ($host === 'localhost' || $host === '127.0.0.1' || $host === '::1') return true;
    if (mp_auth_is_local_ip($host)) return true;
    // Eenvoudige lokale NAS-hostnamen zonder publiek domein zijn alleen
    // toegestaan wanneer de client zelf ook op het lokale netwerk zit.
    return $host !== '' && strpos($host, '.') === false;
}

function mp_auth_request_is_https(): bool {
    if (!empty($_SERVER['HTTPS']) && strtolower((string)$_SERVER['HTTPS']) !== 'off') return true;
    if ((string)($_SERVER['SERVER_PORT'] ?? '') === '443') return true;

    // Alleen een lokale reverse proxy mag X-Forwarded-Proto vertrouwen.
    if (mp_auth_is_local_ip(mp_auth_client_ip())) {
        $forwarded = strtolower(trim((string)($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '')));
        if ($forwarded === 'https') return true;
    }
    return false;
}

function mp_auth_request_allowed(): bool {
    $host = mp_auth_request_host();
    $clientIp = mp_auth_client_ip();

    // Een publiek Machinepark-adres is ALTIJD HTTPS-only, ook als een
    // Synology reverse proxy de aanvraag intern vanaf 127.0.0.1 doorstuurt.
    if (mp_auth_is_public_host($host)) return mp_auth_request_is_https();

    // Lokale HTTP-toegang blijft werken via het interne IP/NAS-hostnaam.
    if (mp_auth_is_private_host($host) && mp_auth_is_local_ip($clientIp)) return true;

    return false;
}

function mp_auth_request_mode(): string {
    $host = mp_auth_request_host();
    if (mp_auth_is_public_host($host)) return mp_auth_request_is_https() ? 'external-https' : 'external-http-blocked';
    if (mp_auth_request_allowed()) return 'local';
    return 'blocked';
}

function mp_auth_mutation_origin_valid(): bool {
    $host = mp_auth_request_host();
    if (!mp_auth_is_public_host($host)) return true;

    $origin = trim((string)($_SERVER['HTTP_ORIGIN'] ?? ''));
    if ($origin === '') {
        $origin = trim((string)($_SERVER['HTTP_REFERER'] ?? ''));
    }
    if ($origin === '') return false;

    $parts = parse_url($origin);
    if (!is_array($parts)) return false;
    $scheme = strtolower((string)($parts['scheme'] ?? ''));
    $originHost = strtolower(rtrim((string)($parts['host'] ?? ''), '.'));
    return $scheme === 'https' && $originHost === $host;
}

function mp_auth_require_request_access(): void {
    if (!mp_auth_request_allowed()) {
        throw new RuntimeException('SECURE_ACCESS_REQUIRED');
    }
    $method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));
    if (!in_array($method, ['GET','HEAD','OPTIONS'], true) && !mp_auth_mutation_origin_valid()) {
        throw new RuntimeException('INVALID_ORIGIN');
    }
}

function mp_auth_access_error_payload(Throwable $e): array {
    if ($e->getMessage() === 'SECURE_ACCESS_REQUIRED') {
        return [
            'error' => mp_auth_is_public_host(mp_auth_request_host())
                ? 'Externe Machinepark-toegang is alleen toegestaan via HTTPS.'
                : 'Dit Machinepark-adres is niet toegestaan.',
            'code' => 'secure_access_required',
            'host' => mp_auth_request_host(),
            'https' => mp_auth_request_is_https(),
        ];
    }
    if ($e->getMessage() === 'INVALID_ORIGIN') {
        return [
            'error' => 'Deze wijziging werd geblokkeerd omdat de aanvraag niet van het actieve Machinepark-adres kwam.',
            'code' => 'invalid_origin',
        ];
    }
    return ['error' => $e->getMessage()];
}

function mp_auth_start_session(): void {
    if (session_status() === PHP_SESSION_ACTIVE) return;
    session_name('MACHINEPARKSESSID');
    @ini_set('session.use_only_cookies', '1');
    @ini_set('session.use_strict_mode', '1');
    @ini_set('session.cookie_httponly', '1');
    $secure = mp_auth_request_is_https();
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
