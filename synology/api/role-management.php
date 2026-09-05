<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';
require_once __DIR__ . '/_audit-lib.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('X-Content-Type-Options: nosniff');

function role_json(array $body, int $status = 200, array $headers = []): void {
    http_response_code($status);
    foreach ($headers as $name => $value) header($name . ': ' . $value);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function role_can_manage(array $user): bool {
    if (!empty($user['isOwner'])) return true;
    $permissions = mp_role_permissions((string)($user['role'] ?? 'gebruiker'));
    return !empty($permissions['roles.manage']);
}

function role_public_config(array $config): array {
    return array_map(function ($role) {
        return [
            'id'=>(string)$role['id'],
            'label'=>(string)$role['label'],
            'builtIn'=>!empty($role['builtIn']),
            'permissions'=>$role['permissions'],
        ];
    }, $config['roles']);
}

function role_usage_count(string $roleId): int {
    $count = 0;
    foreach (mp_auth_read_users() as $user) {
        if (!empty($user['isOwner'])) continue;
        if (mp_role_sanitize_id($user['role'] ?? 'gebruiker') === $roleId) $count++;
    }
    return $count;
}

if (!mp_auth_is_local_ip(mp_auth_client_ip())) {
    role_json(['error'=>'Lokaal rollenbeheer is tijdens de opbouw alleen via het lokale netwerk bereikbaar.'], 403);
}

try {
    $currentUser = mp_auth_require_user();
} catch (Throwable $e) {
    role_json(['error'=>'Niet aangemeld.'], 401);
}

if (!role_can_manage($currentUser)) {
    role_json(['error'=>'Deze rol mag rollen en rechten niet beheren.'], 403);
}

$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));
$config = mp_role_read_config();
$etag = mp_role_etag();

if ($method === 'GET') {
    role_json([
        'roles'=>role_public_config($config),
        'permissionCatalog'=>mp_role_catalog(),
        'etag'=>$etag,
        'ownerProtected'=>true,
        'mode'=>'synology-local',
    ], 200, $etag ? ['ETag'=>$etag] : []);
}

if ($method !== 'POST') role_json(['error'=>'Methode niet toegestaan.'], 405);

$raw = file_get_contents('php://input');
$body = json_decode($raw === false ? '' : $raw, true);
if (!is_array($body)) role_json(['error'=>'Ongeldige aanvraag.'], 400);
$action = (string)($body['action'] ?? 'save-role');
$expected = isset($body['etag']) && $body['etag'] !== '' ? trim((string)$body['etag']) : null;

try {
    if ($action === 'save-role') {
        $incoming = isset($body['role']) && is_array($body['role']) ? $body['role'] : [];
        $requestedId = mp_role_sanitize_id($incoming['id'] ?? ($incoming['label'] ?? ''));
        $label = trim((string)($incoming['label'] ?? ''));
        if ($requestedId === '' || $label === '') throw new RuntimeException('Vul een geldige rolnaam in.');

        $index = -1;
        $existing = null;
        foreach ($config['roles'] as $i => $role) {
            if ($role['id'] === $requestedId) {
                $index = (int)$i;
                $existing = $role;
                break;
            }
        }
        if ($existing === null && count($config['roles']) >= 30) throw new RuntimeException('Maximaal 30 rollen toegestaan.');

        $permissions = array_fill_keys(mp_role_permission_keys(), false);
        $sourcePermissions = isset($incoming['permissions']) && is_array($incoming['permissions']) ? $incoming['permissions'] : [];
        foreach ($permissions as $key => $_) $permissions[$key] = !empty($sourcePermissions[$key]);

        $nextRole = [
            'id'=>$requestedId,
            'label'=>$existing && !empty($existing['builtIn']) ? $existing['label'] : $label,
            'builtIn'=>$existing ? !empty($existing['builtIn']) : false,
            'permissions'=>$permissions,
        ];
        if ($index >= 0) $config['roles'][$index] = $nextRole;
        else $config['roles'][] = $nextRole;

        $newEtag = mp_role_write_config($config, $etag === null ? null : $expected);
        $saved = mp_role_read_config();

        try {
            mp_audit_append($currentUser, [[
                'entityType'=>'Rollenbeheer',
                'entityId'=>$nextRole['id'],
                'entityLabel'=>$nextRole['label'],
                'action'=>$existing ? 'aangepast' : 'toegevoegd',
                'fields'=>[
                    ['field'=>'Rol','before'=>$existing ? $existing['label'] : '—','after'=>$nextRole['label']],
                    ['field'=>'Toegestane handelingen','before'=>$existing ? (string)count(array_filter($existing['permissions'])) : '0','after'=>(string)count(array_filter($nextRole['permissions']))],
                ],
            ]]);
        } catch (Throwable $e) {}

        role_json(['ok'=>true,'roles'=>role_public_config($saved),'etag'=>$newEtag], 200, ['ETag'=>$newEtag]);
    }

    if ($action === 'delete-role') {
        $roleId = mp_role_sanitize_id($body['roleId'] ?? '');
        $target = null;
        foreach ($config['roles'] as $role) if ($role['id'] === $roleId) { $target = $role; break; }
        if (!$target) role_json(['error'=>'Rol niet gevonden.'], 404);
        if (!empty($target['builtIn'])) throw new RuntimeException('Een standaardrol kan niet worden verwijderd; de rechten ervan kunnen wel worden aangepast.');
        $inUse = role_usage_count($roleId);
        if ($inUse > 0) role_json(['error'=>'Deze rol is nog toegewezen aan ' . $inUse . ' gebruiker(s). Wijs eerst een andere rol toe.'], 409);

        $config['roles'] = array_values(array_filter($config['roles'], function ($role) use ($roleId) { return $role['id'] !== $roleId; }));
        $newEtag = mp_role_write_config($config, $etag === null ? null : $expected);
        $saved = mp_role_read_config();

        try {
            mp_audit_append($currentUser, [[
                'entityType'=>'Rollenbeheer',
                'entityId'=>$roleId,
                'entityLabel'=>$target['label'],
                'action'=>'verwijderd',
                'fields'=>[['field'=>'Rol','before'=>$target['label'],'after'=>'—']],
            ]]);
        } catch (Throwable $e) {}

        role_json(['ok'=>true,'roles'=>role_public_config($saved),'etag'=>$newEtag], 200, ['ETag'=>$newEtag]);
    }

    role_json(['error'=>'Onbekende rollenactie.'], 400);
} catch (Throwable $e) {
    if ($e->getMessage() === 'ROLE_CONFLICT') {
        role_json(['error'=>'De rollen zijn intussen door iemand anders gewijzigd. Vernieuw en probeer opnieuw.','etag'=>mp_role_etag()], 409);
    }
    role_json(['error'=>$e->getMessage()], 400);
}
