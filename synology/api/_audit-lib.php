<?php
declare(strict_types=1);

define('MP_AUDIT_DIR', '/volume1/MachineparkData/data/audit');

function mp_audit_ensure_dir(): void {
    if (!is_dir(MP_AUDIT_DIR) && !@mkdir(MP_AUDIT_DIR, 0770, true) && !is_dir(MP_AUDIT_DIR)) {
        throw new RuntimeException('Lokale logboekmap kon niet worden aangemaakt.');
    }
}

function mp_audit_safe_value($value): string {
    if ($value === null || $value === '') return '—';
    if (is_bool($value)) return $value ? 'Ja' : 'Nee';
    if (is_scalar($value)) {
        $text = (string)$value;
    } else {
        $text = json_encode($value, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        if ($text === false) $text = '[gegevens]';
    }
    if (function_exists('mb_substr')) return mb_substr($text, 0, 500, 'UTF-8');
    return substr($text, 0, 500);
}

function mp_audit_user_payload(array $user): array {
    $public = function_exists('mp_auth_public_user') ? mp_auth_public_user($user) : $user;
    return [
        'userId' => (string)($public['id'] ?? ''),
        'userEmail' => (string)($public['email'] ?? ''),
        'userName' => (string)($public['fullName'] ?? trim(((string)($public['firstName'] ?? '')) . ' ' . ((string)($public['lastName'] ?? '')))),
        'userRole' => (string)($public['role'] ?? 'gebruiker'),
    ];
}

function mp_audit_append(array $user, array $changes, array $extra = []): array {
    mp_audit_ensure_dir();
    $at = date(DATE_ATOM);
    $id = 'audit_' . date('YmdHis') . '_' . bin2hex(random_bytes(6));
    $entry = array_merge([
        'id' => $id,
        'at' => $at,
        'changeCount' => count($changes),
        'changes' => array_values($changes),
        'truncated' => false,
        'reversibleSchema' => 1,
    ], mp_audit_user_payload($user), $extra);
    $filename = date('YmdHis') . '-' . bin2hex(random_bytes(4)) . '-' . $id . '.json';
    $path = MP_AUDIT_DIR . '/' . $filename;
    $json = json_encode($entry, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false || @file_put_contents($path, $json, LOCK_EX) === false) {
        throw new RuntimeException('Wijzigingslogboek kon niet worden opgeslagen.');
    }
    $entry['auditKey'] = $filename;
    return $entry;
}

function mp_audit_list(int $limit = 250): array {
    mp_audit_ensure_dir();
    $files = glob(MP_AUDIT_DIR . '/*.json');
    if (!is_array($files)) return [];
    rsort($files, SORT_STRING);
    $entries = [];
    foreach (array_slice($files, 0, max(1, min(500, $limit))) as $path) {
        $raw = @file_get_contents($path);
        if ($raw === false) continue;
        $data = json_decode($raw, true);
        if (!is_array($data)) continue;
        $data['auditKey'] = basename($path);
        $entries[] = $data;
    }
    return $entries;
}

function mp_audit_read_entry(string $auditKey): ?array {
    $name = basename($auditKey);
    if ($name !== $auditKey || !preg_match('/^[A-Za-z0-9._-]+\.json$/', $name)) return null;
    $path = MP_AUDIT_DIR . '/' . $name;
    if (!is_file($path)) return null;
    $raw = @file_get_contents($path);
    if ($raw === false) return null;
    $data = json_decode($raw, true);
    return is_array($data) ? $data : null;
}

function mp_audit_entity_label(string $store, array $item): string {
    if ($store === 'devices') return trim((string)($item['assetCode'] ?? $item['model'] ?? $item['serial'] ?? 'Toestel'));
    if ($store === 'parts') return trim((string)($item['artNr'] ?? $item['description'] ?? 'Onderdeel'));
    if ($store === 'maintenance') return trim((string)($item['title'] ?? $item['type'] ?? 'Onderhoud'));
    if ($store === 'breakdowns') return trim((string)($item['issue'] ?? $item['title'] ?? 'Depannage'));
    return ucfirst($store);
}

function mp_audit_entity_type(string $store): string {
    return [
        'devices' => 'Toestellen',
        'parts' => 'Onderdelen',
        'maintenance' => 'Onderhoud',
        'breakdowns' => 'Depannages',
    ][$store] ?? ucfirst($store);
}

function mp_audit_index_by_id(array $items): array {
    $map = [];
    foreach ($items as $item) {
        if (!is_array($item) || empty($item['id'])) continue;
        $map[(string)$item['id']] = $item;
    }
    return $map;
}

function mp_audit_snapshot_changes(array $before, array $after): array {
    $changes = [];
    foreach (['devices','parts','maintenance','breakdowns'] as $store) {
        $a = mp_audit_index_by_id(isset($before[$store]) && is_array($before[$store]) ? $before[$store] : []);
        $b = mp_audit_index_by_id(isset($after[$store]) && is_array($after[$store]) ? $after[$store] : []);

        foreach ($b as $id => $item) {
            if (!isset($a[$id])) {
                $changes[] = [
                    'entityType' => mp_audit_entity_type($store),
                    'entityId' => $id,
                    'entityLabel' => mp_audit_entity_label($store, $item),
                    'action' => 'toegevoegd',
                    'fields' => [['field'=>'Item','before'=>'—','after'=>mp_audit_entity_label($store, $item)]],
                    'undo' => ['kind'=>'remove-added','storeName'=>$store,'entityId'=>$id,'expectedAfter'=>$item],
                ];
                continue;
            }
            $old = $a[$id];
            $keys = array_unique(array_merge(array_keys($old), array_keys($item)));
            $fields = [];
            $undoFields = [];
            foreach ($keys as $key) {
                if ($key === 'updatedAt') continue;
                $oldExists = array_key_exists($key, $old);
                $newExists = array_key_exists($key, $item);
                $oldValue = $oldExists ? $old[$key] : null;
                $newValue = $newExists ? $item[$key] : null;
                if (json_encode($oldValue) === json_encode($newValue)) continue;
                $fields[] = ['field'=>$key,'before'=>mp_audit_safe_value($oldValue),'after'=>mp_audit_safe_value($newValue)];
                $undoFields[] = [
                    'key'=>$key,
                    'beforeExists'=>$oldExists,
                    'afterExists'=>$newExists,
                    'beforeRaw'=>$oldValue,
                    'afterRaw'=>$newValue,
                ];
            }
            if ($fields) {
                $changes[] = [
                    'entityType' => mp_audit_entity_type($store),
                    'entityId' => $id,
                    'entityLabel' => mp_audit_entity_label($store, $item),
                    'action' => 'aangepast',
                    'fields' => array_slice($fields, 0, 40),
                    'undo' => ['kind'=>'restore-fields','storeName'=>$store,'entityId'=>$id,'fields'=>$undoFields],
                ];
            }
        }

        foreach ($a as $id => $item) {
            if (isset($b[$id])) continue;
            $changes[] = [
                'entityType' => mp_audit_entity_type($store),
                'entityId' => $id,
                'entityLabel' => mp_audit_entity_label($store, $item),
                'action' => 'verwijderd',
                'fields' => [['field'=>'Item','before'=>mp_audit_entity_label($store, $item),'after'=>'—']],
                'undo' => ['kind'=>'restore-deleted','storeName'=>$store,'entityId'=>$id,'beforeItem'=>$item],
            ];
        }
    }
    return $changes;
}
