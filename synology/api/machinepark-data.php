<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('X-Content-Type-Options: nosniff');

define('MP_DATA_DIR', '/volume1/MachineparkData/data');
define('MP_BACKUP_DIR', '/volume1/MachineparkData/backups');
define('MP_STATE_FILE', MP_DATA_DIR . '/state-v1.json');
define('MP_LOCK_FILE', MP_DATA_DIR . '/state-v1.lock');

function mp_json(array $body, int $status = 200, array $headers = []): void {
    http_response_code($status);
    foreach ($headers as $name => $value) {
        header($name . ': ' . $value);
    }
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function mp_access_payload(array $user): array {
    return array_merge([
        'mode' => 'synology-local',
    ], mp_auth_access_payload($user));
}

function mp_ensure_storage(): void {
    foreach ([MP_DATA_DIR, MP_BACKUP_DIR] as $dir) {
        if (!is_dir($dir)) {
            mp_json(['error' => 'Benodigde map ontbreekt: ' . $dir], 500);
        }
        if (!is_readable($dir) || !is_writable($dir)) {
            mp_json(['error' => 'Onvoldoende lees/schrijfrechten op: ' . $dir], 500);
        }
    }
}

function mp_current_etag(): ?string {
    if (!is_file(MP_STATE_FILE)) return null;
    $hash = @hash_file('sha256', MP_STATE_FILE);
    return $hash ? '"' . $hash . '"' : null;
}

function mp_read_state(): ?array {
    if (!is_file(MP_STATE_FILE)) return null;
    $raw = @file_get_contents(MP_STATE_FILE);
    if ($raw === false || trim($raw) === '') {
        mp_json(['error' => 'Lokale Machinepark-database kan niet worden gelezen.'], 500);
    }
    $data = json_decode($raw, true);
    if (!is_array($data)) {
        mp_json(['error' => 'Lokale Machinepark-database bevat ongeldige JSON.'], 500);
    }
    return $data;
}

function mp_valid_snapshot($data): bool {
    return is_array($data)
        && ($data['app'] ?? '') === 'Machinepark'
        && (int)($data['schema'] ?? 0) === 1
        && isset($data['parts']) && is_array($data['parts'])
        && isset($data['devices']) && is_array($data['devices'])
        && isset($data['maintenance']) && is_array($data['maintenance'])
        && isset($data['breakdowns']) && is_array($data['breakdowns']);
}

function mp_normalize_etag($etag): ?string {
    if (!is_string($etag)) return null;
    $etag = trim($etag);
    return $etag === '' ? null : $etag;
}

function mp_backup_current(): void {
    if (!is_file(MP_STATE_FILE)) return;

    $stamp = date('Ymd-His');
    $dest = MP_BACKUP_DIR . '/state-v1-' . $stamp . '.json';
    if (!@copy(MP_STATE_FILE, $dest)) {
        mp_json(['error' => 'Veiligheidsback-up van de huidige lokale database kon niet worden gemaakt.'], 500);
    }

    $files = glob(MP_BACKUP_DIR . '/state-v1-*.json');
    if (!is_array($files)) return;

    usort($files, function ($a, $b) {
        return (int)@filemtime($a) <=> (int)@filemtime($b);
    });

    while (count($files) > 30) {
        $oldest = array_shift($files);
        if ($oldest) @unlink($oldest);
    }
}

function mp_write_state(array $data): string {
    $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false) {
        mp_json(['error' => 'Machinepark-data kon niet naar JSON worden omgezet.'], 500);
    }

    $tmp = MP_STATE_FILE . '.tmp-' . bin2hex(random_bytes(6));
    if (@file_put_contents($tmp, $json, LOCK_EX) === false) {
        mp_json(['error' => 'Tijdelijke lokale database kon niet worden geschreven.'], 500);
    }

    if (!@rename($tmp, MP_STATE_FILE)) {
        @unlink($tmp);
        mp_json(['error' => 'Lokale database kon niet atomair worden vervangen.'], 500);
    }

    $etag = mp_current_etag();
    if ($etag === null) {
        mp_json(['error' => 'Nieuwe lokale database kon niet worden gecontroleerd.'], 500);
    }
    return $etag;
}

if (!mp_auth_is_local_ip(mp_auth_client_ip())) {
    mp_json([
        'error' => 'Lokale Synology API is tijdens de opbouw alleen bereikbaar vanaf het lokale netwerk.',
        'mode' => 'synology-local-only'
    ], 403);
}

try {
    $authUser = mp_auth_require_user();
} catch (Throwable $e) {
    mp_json(['error' => 'Niet aangemeld.', 'code' => 'not_authenticated'], 401);
}

mp_ensure_storage();

$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));

if ($method === 'OPTIONS') {
    http_response_code(204);
    exit;
}

if ($method === 'GET') {
    $etag = mp_current_etag();
    if ($etag === null) {
        mp_json(array_merge([
            'exists' => false,
            'etag' => null,
            'initialized' => false
        ], mp_access_payload($authUser)));
    }

    $ifNoneMatch = mp_normalize_etag($_SERVER['HTTP_IF_NONE_MATCH'] ?? null);
    if ($ifNoneMatch !== null && $ifNoneMatch === $etag) {
        mp_json(array_merge([
            'exists' => true,
            'unchanged' => true,
            'etag' => $etag,
            'data' => null,
            'initialized' => true
        ], mp_access_payload($authUser)), 200, ['ETag' => $etag]);
    }

    mp_json(array_merge([
        'exists' => true,
        'etag' => $etag,
        'data' => mp_read_state(),
        'initialized' => true
    ], mp_access_payload($authUser)), 200, ['ETag' => $etag]);
}

if ($method === 'PUT') {
    if (!is_file(MP_STATE_FILE)) {
        mp_json([
            'error' => 'De lokale database is nog niet geïnitialiseerd. Zet eerst de bestaande Machinepark-database volledig over.',
            'code' => 'not_initialized'
        ], 409);
    }

    $raw = file_get_contents('php://input');
    $body = json_decode($raw === false ? '' : $raw, true);
    $data = is_array($body) ? ($body['data'] ?? null) : null;
    $expected = is_array($body) ? mp_normalize_etag($body['etag'] ?? null) : null;

    if (!mp_valid_snapshot($data)) {
        mp_json(['error' => 'Ongeldige Machinepark-gegevens.'], 400);
    }

    $lock = @fopen(MP_LOCK_FILE, 'c+');
    if ($lock === false) {
        mp_json(['error' => 'Lokale datalock kan niet worden geopend.'], 500);
    }

    if (!flock($lock, LOCK_EX)) {
        fclose($lock);
        mp_json(['error' => 'Lokale datalock kan niet worden verkregen.'], 500);
    }

    $current = mp_current_etag();
    if ($current === null) {
        flock($lock, LOCK_UN);
        fclose($lock);
        mp_json(['error' => 'Lokale database is niet meer beschikbaar.', 'code' => 'not_initialized'], 409);
    }

    if ($expected === null || $expected !== $current) {
        flock($lock, LOCK_UN);
        fclose($lock);
        mp_json([
            'error' => 'De centrale gegevens zijn intussen gewijzigd.',
            'etag' => $current
        ], 409);
    }

    mp_backup_current();
    $data['updatedAt'] = date(DATE_ATOM);
    $etag = mp_write_state($data);

    flock($lock, LOCK_UN);
    fclose($lock);

    mp_json(array_merge([
        'ok' => true,
        'etag' => $etag,
        'updatedAt' => $data['updatedAt']
    ], mp_access_payload($authUser)), 200, ['ETag' => $etag]);
}

mp_json(['error' => 'Methode niet toegestaan.'], 405, ['Allow' => 'GET, PUT, OPTIONS']);
