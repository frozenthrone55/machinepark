<?php
declare(strict_types=1);

require_once __DIR__ . '/../synology/api/_auth-lib.php';

function t_reset(array $values): void {
    $_SERVER = array_merge([
        'REQUEST_METHOD' => 'GET',
        'REMOTE_ADDR' => '192.168.0.50',
        'HTTP_HOST' => '192.168.0.200',
        'SERVER_PORT' => '80',
    ], $values);
    unset($_SERVER['HTTPS'], $_SERVER['HTTP_X_FORWARDED_PROTO'], $_SERVER['HTTP_ORIGIN'], $_SERVER['HTTP_REFERER'], $_SERVER['HTTP_X_FORWARDED_FOR']);
    foreach ($values as $key => $value) $_SERVER[$key] = $value;
}

function t_assert($condition, string $message): void {
    if (!$condition) {
        fwrite(STDERR, "FAIL: " . $message . PHP_EOL);
        exit(1);
    }
}

t_reset([]);
t_assert(mp_auth_request_allowed() === true, 'lokale IP-toegang via HTTP moet blijven werken');
t_assert(mp_auth_request_mode() === 'local', 'lokale modus verwacht');

t_reset([
    'REMOTE_ADDR'=>'198.51.100.20',
    'HTTP_HOST'=>'krisooms.synology.me',
    'SERVER_PORT'=>'80',
]);
t_assert(mp_auth_request_allowed() === false, 'publiek HTTP moet geblokkeerd zijn');
t_assert(mp_auth_request_mode() === 'external-http-blocked', 'HTTP-blokmodus verwacht');

t_reset([
    'REMOTE_ADDR'=>'198.51.100.20',
    'HTTP_HOST'=>'krisooms.synology.me',
    'SERVER_PORT'=>'443',
    'HTTPS'=>'on',
]);
t_assert(mp_auth_request_allowed() === true, 'publiek HTTPS moet toegestaan zijn');
t_assert(mp_auth_request_mode() === 'external-https', 'externe HTTPS-modus verwacht');

t_reset([
    'REMOTE_ADDR'=>'127.0.0.1',
    'HTTP_HOST'=>'krisooms.synology.me',
    'HTTP_X_FORWARDED_PROTO'=>'https',
]);
t_assert(mp_auth_request_allowed() === true, 'lokale reverse proxy met HTTPS moet toegestaan zijn');

t_reset([
    'REMOTE_ADDR'=>'127.0.0.1',
    'HTTP_HOST'=>'evil.example',
    'HTTP_X_FORWARDED_PROTO'=>'https',
]);
t_assert(mp_auth_request_allowed() === false, 'onbekende publieke host moet geblokkeerd blijven');

t_reset([
    'REQUEST_METHOD'=>'POST',
    'REMOTE_ADDR'=>'127.0.0.1',
    'HTTP_HOST'=>'krisooms.synology.me',
    'HTTP_X_FORWARDED_PROTO'=>'https',
    'HTTP_ORIGIN'=>'https://krisooms.synology.me',
]);
t_assert(mp_auth_mutation_origin_valid() === true, 'same-origin HTTPS-mutatie moet geldig zijn');

t_reset([
    'REQUEST_METHOD'=>'POST',
    'REMOTE_ADDR'=>'127.0.0.1',
    'HTTP_HOST'=>'krisooms.synology.me',
    'HTTP_X_FORWARDED_PROTO'=>'https',
    'HTTP_ORIGIN'=>'https://evil.example',
]);
t_assert(mp_auth_mutation_origin_valid() === false, 'cross-origin mutatie moet geblokkeerd zijn');

t_reset([
    'REMOTE_ADDR'=>'127.0.0.1',
    'HTTP_HOST'=>'krisooms.synology.me',
    'HTTP_X_FORWARDED_PROTO'=>'https',
    'HTTP_X_FORWARDED_FOR'=>'203.0.113.8, 198.51.100.77',
]);
t_assert(mp_auth_effective_client_ip() === '198.51.100.77', 'laatste forwarded client-IP verwacht');

echo "Synology secure access policy: OK" . PHP_EOL;
