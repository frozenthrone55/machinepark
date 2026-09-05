<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';
require_once __DIR__ . '/_audit-lib.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('X-Content-Type-Options: nosniff');

define('MP_AUDIT_STATE_FILE', '/volume1/MachineparkData/data/state-v1.json');
define('MP_AUDIT_STATE_LOCK', '/volume1/MachineparkData/data/state-v1.lock');
define('MP_AUDIT_UNDO_DIR', '/volume1/MachineparkData/data/audit-undo');

function audit_json(array $body, int $status = 200): void {
    http_response_code($status);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function audit_permissions(array $user): array {
    return mp_role_permissions((string)($user['role'] ?? 'gebruiker'), !empty($user['isOwner']));
}

function audit_marker_path(string $auditKey, int $changeIndex): string {
    if (!is_dir(MP_AUDIT_UNDO_DIR) && !@mkdir(MP_AUDIT_UNDO_DIR, 0770, true) && !is_dir(MP_AUDIT_UNDO_DIR)) {
        throw new RuntimeException('Undo-map kon niet worden aangemaakt.');
    }
    return MP_AUDIT_UNDO_DIR . '/' . hash('sha256', $auditKey . '|' . $changeIndex) . '.json';
}

function audit_equal($a, $b): bool {
    return json_encode($a) === json_encode($b);
}

function audit_state_read(): array {
    if (!is_file(MP_AUDIT_STATE_FILE)) throw new RuntimeException('Lokale Machinepark-database niet gevonden.');
    $raw = @file_get_contents(MP_AUDIT_STATE_FILE);
    if ($raw === false) throw new RuntimeException('Lokale Machinepark-database kon niet worden gelezen.');
    $data = json_decode($raw, true);
    if (!is_array($data)) throw new RuntimeException('Lokale Machinepark-database bevat ongeldige JSON.');
    return $data;
}

function audit_state_write(array $data): void {
    $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false) throw new RuntimeException('Herstelde database kon niet naar JSON worden omgezet.');
    $tmp = MP_AUDIT_STATE_FILE . '.undo-' . bin2hex(random_bytes(5));
    if (@file_put_contents($tmp, $json, LOCK_EX) === false) throw new RuntimeException('Tijdelijke herstelde database kon niet worden geschreven.');
    if (!@rename($tmp, MP_AUDIT_STATE_FILE)) {
        @unlink($tmp);
        throw new RuntimeException('Herstelde database kon niet atomair worden opgeslagen.');
    }
}

function audit_find_index(array $list, string $id): int {
    foreach ($list as $index => $item) {
        if (is_array($item) && (string)($item['id'] ?? '') === $id) return (int)$index;
    }
    return -1;
}

function audit_apply_undo(array $snapshot, array $change): array {
    $undo = isset($change['undo']) && is_array($change['undo']) ? $change['undo'] : null;
    if (!$undo) throw new RuntimeException('Deze logboekregel bevat geen hersteldata.');
    $store = (string)($undo['storeName'] ?? '');
    $id = (string)($undo['entityId'] ?? '');
    if (!in_array($store, ['devices','parts','maintenance','breakdowns'], true) || $id === '') {
        throw new RuntimeException('Deze logboekregel bevat ongeldige hersteldata.');
    }

    $list = isset($snapshot[$store]) && is_array($snapshot[$store]) ? array_values($snapshot[$store]) : [];
    $index = audit_find_index($list, $id);
    $kind = (string)($undo['kind'] ?? '');

    if ($kind === 'restore-fields') {
        if ($index < 0) throw new RuntimeException('Dit item bestaat niet meer. Herstellen is geblokkeerd.');
        $current = $list[$index];
        foreach ((array)($undo['fields'] ?? []) as $field) {
            if (!is_array($field)) continue;
            $key = (string)($field['key'] ?? '');
            if ($key === '') continue;
            $afterExists = !empty($field['afterExists']);
            $currentExists = array_key_exists($key, $current);
            if ($currentExists !== $afterExists) throw new RuntimeException('Dit item is intussen opnieuw gewijzigd. Herstellen is geblokkeerd.');
            if ($afterExists && !audit_equal($current[$key], $field['afterRaw'] ?? null)) {
                throw new RuntimeException('Dit item is intussen opnieuw gewijzigd. Herstellen is geblokkeerd.');
            }
        }
        foreach ((array)($undo['fields'] ?? []) as $field) {
            if (!is_array($field)) continue;
            $key = (string)($field['key'] ?? '');
            if ($key === '') continue;
            if (!empty($field['beforeExists'])) $current[$key] = $field['beforeRaw'] ?? null;
            else unset($current[$key]);
        }
        $current['updatedAt'] = date(DATE_ATOM);
        $list[$index] = $current;
    } elseif ($kind === 'remove-added') {
        if ($index < 0) throw new RuntimeException('Dit toegevoegde item is al verwijderd.');
        $expected = $undo['expectedAfter'] ?? null;
        if (!is_array($expected) || !audit_equal($list[$index], $expected)) {
            throw new RuntimeException('Dit item is na de toevoeging opnieuw gewijzigd. Herstellen is geblokkeerd.');
        }
        array_splice($list, $index, 1);
    } elseif ($kind === 'restore-deleted') {
        if ($index >= 0) throw new RuntimeException('Er bestaat intussen opnieuw een item met hetzelfde ID. Herstellen is geblokkeerd.');
        $beforeItem = $undo['beforeItem'] ?? null;
        if (!is_array($beforeItem)) throw new RuntimeException('De oorspronkelijke gegevens ontbreken.');
        $list[] = $beforeItem;
    } else {
        throw new RuntimeException('Dit type wijziging kan niet worden hersteld.');
    }

    $snapshot[$store] = array_values($list);
    return $snapshot;
}

function audit_reverse_fields(array $fields): array {
    return array_map(function ($field) {
        return [
            'field'=>(string)($field['field'] ?? ''),
            'before'=>(string)($field['after'] ?? '—'),
            'after'=>(string)($field['before'] ?? '—'),
        ];
    }, $fields);
}

if (!mp_auth_is_local_ip(mp_auth_client_ip())) {
    audit_json(['error'=>'Het lokale wijzigingslogboek is tijdens de opbouw alleen via het lokale netwerk bereikbaar.'], 403);
}

try {
    $currentUser = mp_auth_require_user();
} catch (Throwable $e) {
    audit_json(['error'=>'Niet aangemeld.'], 401);
}

$permissions = audit_permissions($currentUser);
$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));

if ($method === 'GET') {
    if (empty($permissions['audit.view'])) audit_json(['error'=>'Deze rol mag het wijzigingslogboek niet bekijken.'], 403);
    $entries = mp_audit_list(250);
    foreach ($entries as &$entry) {
        $auditKey = (string)($entry['auditKey'] ?? '');
        $safeChanges = [];
        foreach ((array)($entry['changes'] ?? []) as $index => $change) {
            if (!is_array($change)) continue;
            $marker = audit_marker_path($auditKey, (int)$index);
            $undone = is_file($marker);
            $hasUndo = isset($change['undo']) && is_array($change['undo']);
            unset($change['undo']);
            $change['reversible'] = $hasUndo && !$undone;
            $change['undone'] = $undone;
            $change['linkedUndoCount'] = 0;
            $safeChanges[] = $change;
        }
        $entry['changes'] = $safeChanges;
    }
    unset($entry);
    audit_json(['entries'=>$entries,'mode'=>'synology-local']);
}

if ($method !== 'POST') audit_json(['error'=>'Methode niet toegestaan.'], 405);
if (empty($permissions['audit.undo'])) audit_json(['error'=>'Deze rol mag wijzigingen niet ongedaan maken.'], 403);

$raw = file_get_contents('php://input');
$body = json_decode($raw === false ? '' : $raw, true);
if (!is_array($body)) audit_json(['error'=>'Ongeldige aanvraag.'], 400);
$auditKey = (string)($body['auditKey'] ?? '');
$changeIndex = filter_var($body['changeIndex'] ?? null, FILTER_VALIDATE_INT, ['options'=>['min_range'=>0]]);
if ($auditKey === '' || $changeIndex === false) audit_json(['error'=>'Ongeldige wijzigingsregel.'], 400);

$entry = mp_audit_read_entry($auditKey);
if (!$entry) audit_json(['error'=>'Logboekregel niet gevonden.'], 404);
$changes = isset($entry['changes']) && is_array($entry['changes']) ? $entry['changes'] : [];
if (!isset($changes[$changeIndex]) || !is_array($changes[$changeIndex])) audit_json(['error'=>'Wijziging niet gevonden in deze logboekregel.'], 404);
$change = $changes[$changeIndex];
if (empty($change['undo'])) audit_json(['error'=>'Deze logboekregel bevat geen hersteldata.'], 409);

try {
    $markerPath = audit_marker_path($auditKey, (int)$changeIndex);
    if (is_file($markerPath)) audit_json(['error'=>'Deze wijziging is al ongedaan gemaakt.'], 409);

    $lock = @fopen(MP_AUDIT_STATE_LOCK, 'c+');
    if ($lock === false || !flock($lock, LOCK_EX)) throw new RuntimeException('Databaselock kon niet worden verkregen.');

    $before = audit_state_read();
    $after = audit_apply_undo($before, $change);
    $after['updatedAt'] = date(DATE_ATOM);
    $after['updatedBy'] = (string)($currentUser['id'] ?? '');
    $after['updatedByEmail'] = (string)($currentUser['email'] ?? '');
    audit_state_write($after);

    @file_put_contents($markerPath, json_encode([
        'at'=>$after['updatedAt'],
        'by'=>(string)($currentUser['email'] ?? $currentUser['id'] ?? ''),
        'auditKey'=>$auditKey,
        'changeIndex'=>(int)$changeIndex,
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), LOCK_EX);

    flock($lock, LOCK_UN);
    fclose($lock);

    try {
        mp_audit_append($currentUser, [[
            'entityType'=>(string)($change['entityType'] ?? 'Item'),
            'entityId'=>(string)($change['entityId'] ?? ''),
            'entityLabel'=>(string)($change['entityLabel'] ?? 'Wijziging'),
            'action'=>'ongedaan gemaakt',
            'fields'=>audit_reverse_fields((array)($change['fields'] ?? [])),
        ]], ['operation'=>'undo']);
    } catch (Throwable $e) {}

    audit_json(['ok'=>true,'updatedAt'=>$after['updatedAt'],'revertedCount'=>1,'linkedCount'=>0]);
} catch (Throwable $e) {
    if (isset($lock) && is_resource($lock)) {
        @flock($lock, LOCK_UN);
        @fclose($lock);
    }
    audit_json(['error'=>$e->getMessage()], 409);
}
