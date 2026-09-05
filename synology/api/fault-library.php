<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('X-Content-Type-Options: nosniff');

define('MP_FAULT_FILE', '/volume1/MachineparkData/data/fault-library-v1.json');
define('MP_FAULT_LOCK', '/volume1/MachineparkData/data/fault-library-v1.lock');
define('MP_FAULT_BACKUPS', '/volume1/MachineparkData/backups');
define('MP_FAULT_SEED', dirname(__DIR__) . '/fault-seed.json');
define('MP_FAULT_MAX', 5000);
define('MP_FAULT_IMPORT_UNDO', '/volume1/MachineparkData/data/fault-import-undo-v1.json');

function fault_json(array $body, int $status = 200, array $headers = []): void {
    http_response_code($status);
    foreach ($headers as $name => $value) header($name . ': ' . $value);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function fault_text($value, int $max = 500): string {
    $text = trim((string)$value);
    return function_exists('mb_substr') ? mb_substr($text, 0, $max, 'UTF-8') : substr($text, 0, $max);
}

function fault_lines($value, int $maxItems = 30, int $maxLength = 500): array {
    $items = is_array($value) ? $value : preg_split('/\r?\n/', (string)$value);
    $out = [];
    foreach ((array)$items as $item) {
        $line = fault_text($item, $maxLength);
        if ($line === '') continue;
        $out[] = $line;
        if (count($out) >= $maxItems) break;
    }
    return $out;
}

function fault_id($value = ''): string {
    $raw = strtolower(trim((string)$value));
    $raw = preg_replace('/[^a-z0-9_-]+/', '-', $raw);
    $raw = trim((string)$raw, '-');
    if ($raw !== '') return substr($raw, 0, 90);
    return 'fault-' . bin2hex(random_bytes(10));
}

function fault_sanitize(array $fault, ?array $existing = null): array {
    $name = fault_text($fault['name'] ?? '', 160);
    if ($name === '') throw new RuntimeException('Geef de storing een naam of korte omschrijving.');

    $brand = fault_text($fault['brand'] ?? '', 100);
    $model = $brand !== '' ? fault_text($fault['model'] ?? '', 140) : '';
    $now = date(DATE_ATOM);
    $id = fault_id($fault['id'] ?? ($existing['id'] ?? ''));

    return [
        'id' => $id,
        'code' => fault_text($fault['code'] ?? '', 80),
        'name' => $name,
        'category' => fault_text($fault['category'] ?? '', 100),
        'brand' => $brand,
        'model' => $model,
        'scope' => ($brand !== '' && $model !== '') ? 'model' : ($brand !== '' ? 'brand' : 'general'),
        'description' => fault_text($fault['description'] ?? '', 1600),
        'message' => fault_text($fault['message'] ?? '', 1600),
        'solution1' => fault_text($fault['solution1'] ?? '', 1200),
        'solution2' => fault_text($fault['solution2'] ?? '', 1200),
        'symptoms' => fault_lines($fault['symptoms'] ?? [], 30, 500),
        'causes' => fault_lines($fault['causes'] ?? [], 30, 500),
        'solutions' => fault_lines($fault['solutions'] ?? [], 40, 800),
        'notes' => fault_text($fault['notes'] ?? '', 2000),
        'active' => array_key_exists('active', $fault) ? (bool)$fault['active'] : true,
        'version' => $existing ? max(1, (int)($existing['version'] ?? 1)) + 1 : max(1, (int)($fault['version'] ?? 1)),
        'createdAt' => $existing['createdAt'] ?? fault_text($fault['createdAt'] ?? '', 80) ?: $now,
        'updatedAt' => $now,
    ];
}

function fault_normalize(array $data): array {
    $out = [];
    $seen = [];
    $source = isset($data['faults']) && is_array($data['faults']) ? $data['faults'] : [];
    foreach (array_slice($source, 0, MP_FAULT_MAX) as $item) {
        if (!is_array($item)) continue;
        try {
            $normalized = fault_sanitize($item, $item);
            $id = $normalized['id'];
            if (isset($seen[$id])) continue;
            $seen[$id] = true;
            $normalized['version'] = max(1, (int)($item['version'] ?? 1));
            if (!empty($item['createdAt'])) $normalized['createdAt'] = fault_text($item['createdAt'], 80);
            if (!empty($item['updatedAt'])) $normalized['updatedAt'] = fault_text($item['updatedAt'], 80);
            $out[] = $normalized;
        } catch (Throwable $e) {
        }
    }
    return ['version' => 1, 'faults' => $out];
}

function fault_etag(): ?string {
    if (!is_file(MP_FAULT_FILE)) return null;
    $hash = @hash_file('sha256', MP_FAULT_FILE);
    return $hash ? '"' . $hash . '"' : null;
}

function fault_atomic_write(array $data): string {
    $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false) throw new RuntimeException('Storingsbibliotheek kon niet naar JSON worden omgezet.');
    $tmp = MP_FAULT_FILE . '.tmp-' . bin2hex(random_bytes(6));
    if (@file_put_contents($tmp, $json, LOCK_EX) === false) {
        throw new RuntimeException('Tijdelijke storingsbibliotheek kon niet worden geschreven.');
    }
    if (!@rename($tmp, MP_FAULT_FILE)) {
        @unlink($tmp);
        throw new RuntimeException('Storingsbibliotheek kon niet atomair worden opgeslagen.');
    }
    $etag = fault_etag();
    if ($etag === null) throw new RuntimeException('Nieuwe storingsbibliotheek kon niet worden gecontroleerd.');
    return $etag;
}

function fault_backup(): void {
    if (!is_file(MP_FAULT_FILE) || !is_dir(MP_FAULT_BACKUPS)) return;
    $dest = MP_FAULT_BACKUPS . '/fault-library-v1-' . date('Ymd-His') . '.json';
    @copy(MP_FAULT_FILE, $dest);
    $files = glob(MP_FAULT_BACKUPS . '/fault-library-v1-*.json');
    if (!is_array($files)) return;
    usort($files, function ($a, $b) { return (int)@filemtime($a) <=> (int)@filemtime($b); });
    while (count($files) > 30) {
        $old = array_shift($files);
        if ($old) @unlink($old);
    }
}

function fault_initialize_if_needed(): void {
    if (is_file(MP_FAULT_FILE)) return;
    if (!is_file(MP_FAULT_SEED)) throw new RuntimeException('Lokale storingsseed ontbreekt.');
    $raw = @file_get_contents(MP_FAULT_SEED);
    if ($raw === false) throw new RuntimeException('Lokale storingsseed kan niet worden gelezen.');
    $seed = json_decode($raw, true);
    if (!is_array($seed) || !isset($seed['faults']) || !is_array($seed['faults'])) {
        throw new RuntimeException('Lokale storingsseed bevat ongeldige gegevens.');
    }
    $normalized = fault_normalize($seed);
    if (count($normalized['faults']) === 0) throw new RuntimeException('Lokale storingsseed bevat geen geldige storingen.');
    fault_atomic_write($normalized);
}

function fault_read(): array {
    fault_initialize_if_needed();
    $raw = @file_get_contents(MP_FAULT_FILE);
    if ($raw === false) throw new RuntimeException('Lokale storingsbibliotheek kan niet worden gelezen.');
    $data = json_decode($raw, true);
    if (!is_array($data)) throw new RuntimeException('Lokale storingsbibliotheek bevat ongeldige JSON.');
    return fault_normalize($data);
}

function fault_has_permission(array $user, string $permission): bool {
    $role = (string)($user['role'] ?? 'gebruiker');
    $permissions = mp_auth_permissions_for_role($role);
    return !empty($permissions[$permission]);
}

if (!mp_auth_is_local_ip(mp_auth_client_ip())) {
    fault_json(['error' => 'Lokale storingsbibliotheek is tijdens de opbouw alleen via het lokale netwerk bereikbaar.'], 403);
}

try {
    $authUser = mp_auth_require_user();
} catch (Throwable $e) {
    fault_json(['error' => 'Niet aangemeld.', 'code' => 'not_authenticated'], 401);
}

if (!fault_has_permission($authUser, 'view.faults') && !fault_has_permission($authUser, 'faults.manage')) {
    fault_json(['error' => 'Deze rol heeft geen toegang tot de storingsbibliotheek.'], 403);
}

try {
    fault_initialize_if_needed();
} catch (Throwable $e) {
    fault_json(['error' => $e->getMessage()], 500);
}

$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));

if ($method === 'GET') {
    try {
        $config = fault_read();
        $etag = fault_etag();
        fault_json([
            'faults' => $config['faults'],
            'etag' => $etag,
            'canManage' => fault_has_permission($authUser, 'faults.manage'),
            'mode' => 'synology-local',
        ], 200, $etag ? ['ETag' => $etag] : []);
    } catch (Throwable $e) {
        fault_json(['error' => $e->getMessage()], 500);
    }
}

if ($method !== 'POST') {
    fault_json(['error' => 'Methode niet toegestaan.'], 405, ['Allow' => 'GET, POST']);
}

if (!fault_has_permission($authUser, 'faults.manage')) {
    fault_json(['error' => 'Deze rol mag de storingsbibliotheek niet beheren.'], 403);
}

$raw = file_get_contents('php://input');
$body = json_decode($raw === false ? '' : $raw, true);
if (!is_array($body)) fault_json(['error' => 'Ongeldige aanvraag.'], 400);

$lock = @fopen(MP_FAULT_LOCK, 'c+');
if ($lock === false) fault_json(['error' => 'Storingslock kan niet worden geopend.'], 500);
if (!flock($lock, LOCK_EX)) {
    fclose($lock);
    fault_json(['error' => 'Storingslock kan niet worden verkregen.'], 500);
}

try {
    $config = fault_read();
    $currentEtag = fault_etag();
    $expected = isset($body['etag']) ? trim((string)$body['etag']) : '';
    if (!$currentEtag || $expected === '' || $expected !== $currentEtag) {
        throw new RuntimeException('CONFLICT');
    }

    $action = (string)($body['action'] ?? 'save-fault');

    if ($action === 'undo-last-import') {
        if (!is_file(MP_FAULT_IMPORT_UNDO)) {
            flock($lock, LOCK_UN);
            fclose($lock);
            fault_json(['error' => 'Er is geen recente storingsimport beschikbaar om terug te draaien.'], 409);
        }
        $undoRaw = @file_get_contents(MP_FAULT_IMPORT_UNDO);
        $undo = $undoRaw !== false ? json_decode($undoRaw, true) : null;
        if (!is_array($undo) || !isset($undo['before']) || !is_array($undo['before'])) {
            flock($lock, LOCK_UN);
            fclose($lock);
            fault_json(['error' => 'De herstelkopie van de laatste storingsimport is ongeldig.'], 409);
        }
        $expectedAfter = trim((string)($undo['afterEtag'] ?? ''));
        if ($expectedAfter === '' || $expectedAfter !== (string)$currentEtag) {
            flock($lock, LOCK_UN);
            fclose($lock);
            fault_json(['error' => 'De storingsbibliotheek is na de import nog gewijzigd. Terugdraaien is daarom geblokkeerd.'], 409);
        }
        fault_backup();
        $restored = fault_normalize($undo['before']);
        $newEtag = fault_atomic_write($restored);
        @unlink(MP_FAULT_IMPORT_UNDO);
        flock($lock, LOCK_UN);
        fclose($lock);
        try {
            require_once __DIR__ . '/_audit-lib.php';
            mp_audit_append($authUser, [[
                'entityType'=>'Storingen',
                'entityId'=>'excel-import',
                'entityLabel'=>'Storingen Excel-import',
                'action'=>'ongedaan gemaakt',
                'fields'=>[['field'=>'Aantal storingen','before'=>(string)count($config['faults']),'after'=>(string)count($restored['faults'])]],
            ]]);
        } catch (Throwable $e) {}
        fault_json(['ok'=>true,'faults'=>$restored['faults'],'etag'=>$newEtag,'canManage'=>true,'restoredCount'=>count($restored['faults'])], 200, ['ETag'=>$newEtag]);
    }

    if ($action === 'import-faults') {
        $incomingFaults = isset($body['faults']) && is_array($body['faults']) ? array_slice($body['faults'], 0, MP_FAULT_MAX) : [];
        if (!$incomingFaults) {
            flock($lock, LOCK_UN);
            fclose($lock);
            fault_json(['error'=>'Geen storingen gevonden om te importeren.'], 400);
        }
        $beforeImport = $config;
        $added = 0;
        $updated = 0;

        foreach ($incomingFaults as $incoming) {
            if (!is_array($incoming)) continue;
            $requestedId = !empty($incoming['id']) ? fault_id($incoming['id']) : '';
            $existing = null;
            $existingIndex = -1;
            if ($requestedId !== '') {
                foreach ($config['faults'] as $idx => $item) {
                    if ((string)$item['id'] === $requestedId) {
                        $existing = $item;
                        $existingIndex = (int)$idx;
                        break;
                    }
                }
            }
            $fault = fault_sanitize($incoming, $existing);
            if ($existingIndex >= 0) {
                $config['faults'][$existingIndex] = $fault;
                $updated++;
            } else {
                if (count($config['faults']) >= MP_FAULT_MAX) {
                    flock($lock, LOCK_UN);
                    fclose($lock);
                    fault_json(['error'=>'Maximaal ' . MP_FAULT_MAX . ' storingen toegestaan.'], 400);
                }
                $config['faults'][] = $fault;
                $added++;
            }
        }

        fault_backup();
        $newEtag = fault_atomic_write(['version'=>1,'faults'=>$config['faults']]);
        @file_put_contents(MP_FAULT_IMPORT_UNDO, json_encode([
            'at'=>date(DATE_ATOM),
            'before'=>$beforeImport,
            'afterEtag'=>$newEtag,
            'added'=>$added,
            'updated'=>$updated,
        ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), LOCK_EX);

        flock($lock, LOCK_UN);
        fclose($lock);
        try {
            require_once __DIR__ . '/_audit-lib.php';
            mp_audit_append($authUser, [[
                'entityType'=>'Storingen',
                'entityId'=>'excel-import',
                'entityLabel'=>'Storingen Excel-import',
                'action'=>'geïmporteerd',
                'fields'=>[
                    ['field'=>'Nieuwe storingen','before'=>'—','after'=>(string)$added],
                    ['field'=>'Bijgewerkte storingen','before'=>'—','after'=>(string)$updated],
                ],
            ]]);
        } catch (Throwable $e) {}
        fault_json(['ok'=>true,'faults'=>$config['faults'],'etag'=>$newEtag,'canManage'=>true,'added'=>$added,'updated'=>$updated], 200, ['ETag'=>$newEtag]);
    }

    if ($action === 'save-fault') {
        $incoming = isset($body['fault']) && is_array($body['fault']) ? $body['fault'] : [];
        $requestedId = !empty($incoming['id']) ? fault_id($incoming['id']) : '';
        $existing = null;
        $existingIndex = -1;
        foreach ($config['faults'] as $idx => $item) {
            if ($requestedId !== '' && (string)$item['id'] === $requestedId) {
                $existing = $item;
                $existingIndex = $idx;
                break;
            }
        }
        if ($existing === null && count($config['faults']) >= MP_FAULT_MAX) {
            fault_json(['error' => 'Maximaal ' . MP_FAULT_MAX . ' storingen toegestaan.'], 400);
        }
        if ($requestedId !== '') $incoming['id'] = $requestedId;
        $fault = fault_sanitize($incoming, $existing);
        if ($existingIndex >= 0) $config['faults'][$existingIndex] = $fault;
        else $config['faults'][] = $fault;
    } elseif ($action === 'delete-fault') {
        $faultId = fault_id($body['faultId'] ?? '');
        $found = false;
        $next = [];
        foreach ($config['faults'] as $item) {
            if ((string)$item['id'] === $faultId) {
                $found = true;
                continue;
            }
            $next[] = $item;
        }
        if (!$found) fault_json(['error' => 'Storing niet gevonden.'], 404);
        $config['faults'] = $next;
    } else {
        fault_json(['error' => 'Onbekende storingsactie.'], 400);
    }

    fault_backup();
    $etag = fault_atomic_write(['version' => 1, 'faults' => $config['faults']]);

    flock($lock, LOCK_UN);
    fclose($lock);

    fault_json([
        'ok' => true,
        'faults' => $config['faults'],
        'etag' => $etag,
        'canManage' => true,
        'mode' => 'synology-local',
    ], 200, ['ETag' => $etag]);
} catch (Throwable $e) {
    flock($lock, LOCK_UN);
    fclose($lock);
    if ($e->getMessage() === 'CONFLICT') {
        fault_json([
            'error' => 'De storingsbibliotheek is intussen door iemand anders gewijzigd. Vernieuw en probeer opnieuw.',
            'etag' => fault_etag(),
        ], 409);
    }
    fault_json(['error' => $e->getMessage()], 400);
}
