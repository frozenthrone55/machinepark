<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';
require_once __DIR__ . '/_audit-lib.php';

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

function mp_list_map(array $items): array {
    $map = [];
    foreach ($items as $item) {
        if (is_array($item) && !empty($item['id'])) $map[(string)$item['id']] = $item;
    }
    return $map;
}

function mp_changed_keys(array $before, array $after): array {
    $keys = array_unique(array_merge(array_keys($before), array_keys($after)));
    $changed = [];
    foreach ($keys as $key) {
        if ($key === 'updatedAt') continue;
        $a = array_key_exists($key, $before) ? $before[$key] : null;
        $b = array_key_exists($key, $after) ? $after[$key] : null;
        if (json_encode($a) !== json_encode($b)) $changed[] = $key;
    }
    return $changed;
}

function mp_store_diff(array $before, array $after, string $store): array {
    $a = mp_list_map(isset($before[$store]) && is_array($before[$store]) ? $before[$store] : []);
    $b = mp_list_map(isset($after[$store]) && is_array($after[$store]) ? $after[$store] : []);
    $added = []; $removed = []; $changed = [];
    foreach ($b as $id => $item) {
        if (!isset($a[$id])) $added[] = $item;
        else {
            $keys = mp_changed_keys($a[$id], $item);
            if ($keys) $changed[] = ['before'=>$a[$id], 'after'=>$item, 'keys'=>$keys];
        }
    }
    foreach ($a as $id => $item) if (!isset($b[$id])) $removed[] = $item;
    return ['added'=>$added,'removed'=>$removed,'changed'=>$changed];
}

function mp_require_permission(array $permissions, string $key, string $message): void {
    if (empty($permissions[$key])) mp_json(['error'=>$message], 403);
}

function mp_validate_write_permissions(array $before, array $after, array $user): void {
    $permissions = mp_role_permissions((string)($user['role'] ?? 'gebruiker'), !empty($user['isOwner']));
    $devices = mp_store_diff($before, $after, 'devices');
    $maintenance = mp_store_diff($before, $after, 'maintenance');
    $breakdowns = mp_store_diff($before, $after, 'breakdowns');
    $parts = mp_store_diff($before, $after, 'parts');

    if ($devices['added']) mp_require_permission($permissions, 'devices.add', 'Deze rol mag geen toestellen toevoegen.');
    if ($devices['removed']) mp_require_permission($permissions, 'devices.delete', 'Deze rol mag geen toestellen verwijderen.');
    foreach ($devices['changed'] as $change) {
        $statusNotesOnly = count(array_diff($change['keys'], ['status','notes'])) === 0;
        if ($statusNotesOnly && (!empty($permissions['devices.statusNotes']) || !empty($permissions['devices.edit']))) continue;
        mp_require_permission($permissions, 'devices.edit', 'Deze rol mag toestelgegevens niet volledig wijzigen.');
    }

    if ($maintenance['added']) mp_require_permission($permissions, 'maintenance.add', 'Deze rol mag geen onderhoud registreren.');
    if ($maintenance['removed']) mp_require_permission($permissions, 'maintenance.delete', 'Deze rol mag geen onderhoud verwijderen.');
    if ($maintenance['changed']) mp_require_permission($permissions, 'maintenance.edit', 'Deze rol mag onderhoud niet wijzigen.');

    if ($breakdowns['added']) mp_require_permission($permissions, 'breakdowns.add', 'Deze rol mag geen depannages registreren.');
    if ($breakdowns['removed']) mp_require_permission($permissions, 'breakdowns.delete', 'Deze rol mag geen depannages verwijderen.');
    if ($breakdowns['changed']) mp_require_permission($permissions, 'breakdowns.edit', 'Deze rol mag depannages niet wijzigen.');

    if ($parts['added']) mp_require_permission($permissions, 'parts.add', 'Deze rol mag geen onderdelen toevoegen.');
    if ($parts['removed']) mp_require_permission($permissions, 'parts.delete', 'Deze rol mag geen onderdelen verwijderen.');

    $serviceMutationAllowed = false;
    if ($maintenance['added'] || $maintenance['removed'] || $maintenance['changed'] || $breakdowns['added'] || $breakdowns['removed'] || $breakdowns['changed']) {
        $serviceMutationAllowed = true;
    }
    foreach ($parts['changed'] as $change) {
        $stockOnly = count(array_diff($change['keys'], ['stock'])) === 0;
        if ($stockOnly && (!empty($permissions['parts.stock']) || !empty($permissions['parts.edit']) || $serviceMutationAllowed)) continue;
        mp_require_permission($permissions, 'parts.edit', 'Deze rol mag onderdeelgegevens niet wijzigen.');
    }
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

try {
    mp_auth_require_request_access();
} catch (Throwable $e) {
    mp_json(mp_auth_access_error_payload($e), 403);
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

    $before = mp_read_state();
    if (!is_array($before)) {
        flock($lock, LOCK_UN);
        fclose($lock);
        mp_json(['error'=>'Lokale database kon niet worden gelezen.'], 500);
    }

    mp_validate_write_permissions($before, $data, $authUser);
    $changes = mp_audit_snapshot_changes($before, $data);

    mp_backup_current();
    $data['updatedAt'] = date(DATE_ATOM);
    $data['updatedBy'] = (string)($authUser['id'] ?? '');
    $data['updatedByEmail'] = (string)($authUser['email'] ?? '');
    $etag = mp_write_state($data);

    flock($lock, LOCK_UN);
    fclose($lock);

    if ($changes) {
        try { mp_audit_append($authUser, $changes); } catch (Throwable $auditError) {}
    }

    mp_json(array_merge([
        'ok' => true,
        'etag' => $etag,
        'updatedAt' => $data['updatedAt']
    ], mp_access_payload($authUser)), 200, ['ETag' => $etag]);
}

mp_json(['error' => 'Methode niet toegestaan.'], 405, ['Allow' => 'GET, PUT, OPTIONS']);
