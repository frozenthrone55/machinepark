<?php
declare(strict_types=1);

define('MP_ROLE_FILE', '/volume1/MachineparkData/data/role-config-v1.json');

function mp_role_catalog(): array {
    return [
        ['group'=>'Weergave','key'=>'view.dashboard','label'=>'Dashboard bekijken'],
        ['group'=>'Weergave','key'=>'view.devices','label'=>'Toestellen bekijken'],
        ['group'=>'Weergave','key'=>'view.maintenance','label'=>'Onderhoud bekijken'],
        ['group'=>'Weergave','key'=>'view.breakdowns','label'=>'Depannages bekijken'],
        ['group'=>'Weergave','key'=>'view.faults','label'=>'Storingen bekijken'],
        ['group'=>'Weergave','key'=>'view.manuals','label'=>'Handleidingen bekijken'],
        ['group'=>'Weergave','key'=>'view.parts','label'=>'Onderdelen bekijken'],
        ['group'=>'Weergave','key'=>'view.settings','label'=>'Beheer bekijken'],
        ['group'=>'Toestellen','key'=>'devices.add','label'=>'Toestellen toevoegen'],
        ['group'=>'Toestellen','key'=>'devices.edit','label'=>'Toestellen volledig wijzigen'],
        ['group'=>'Toestellen','key'=>'devices.statusNotes','label'=>'Alleen status en notities wijzigen'],
        ['group'=>'Toestellen','key'=>'devices.delete','label'=>'Toestellen verwijderen'],
        ['group'=>'Toestellen','key'=>'devices.import','label'=>'Toestellen synchroniseren via Excel'],
        ['group'=>'Onderhoud','key'=>'maintenance.add','label'=>'Onderhoud registreren'],
        ['group'=>'Onderhoud','key'=>'maintenance.edit','label'=>'Onderhoud wijzigen'],
        ['group'=>'Onderhoud','key'=>'maintenance.delete','label'=>'Onderhoud verwijderen'],
        ['group'=>'Depannages','key'=>'breakdowns.add','label'=>'Depannages registreren'],
        ['group'=>'Depannages','key'=>'breakdowns.edit','label'=>'Depannages wijzigen'],
        ['group'=>'Depannages','key'=>'breakdowns.delete','label'=>'Depannages verwijderen'],
        ['group'=>'Storingen','key'=>'faults.manage','label'=>'Storingsbibliotheek beheren'],
        ['group'=>'Handleidingen','key'=>'manuals.manage','label'=>'Handleidingen beheren'],
        ['group'=>'Onderdelen','key'=>'parts.add','label'=>'Onderdelen toevoegen'],
        ['group'=>'Onderdelen','key'=>'parts.edit','label'=>'Onderdeelgegevens wijzigen'],
        ['group'=>'Onderdelen','key'=>'parts.stock','label'=>'Voorraad aanpassen'],
        ['group'=>'Onderdelen','key'=>'parts.delete','label'=>'Onderdelen verwijderen'],
        ['group'=>'Onderdelen','key'=>'parts.export','label'=>'Onderdelen exporteren naar Excel'],
        ['group'=>'Onderdelen','key'=>'parts.import','label'=>'Stocktelling importeren via Excel'],
        ['group'=>'Algemeen','key'=>'print','label'=>'Pagina’s en verslagen afdrukken'],
        ['group'=>'Beheer','key'=>'backup.export','label'=>'Back-up maken'],
        ['group'=>'Beheer','key'=>'backup.import','label'=>'Back-up terugzetten'],
        ['group'=>'Beheer','key'=>'users.manage','label'=>'Gebruikers beheren'],
        ['group'=>'Beheer','key'=>'audit.view','label'=>'Wijzigingslogboek bekijken'],
        ['group'=>'Beheer','key'=>'audit.undo','label'=>'Wijzigingen ongedaan maken'],
        ['group'=>'Beheer','key'=>'roles.manage','label'=>'Rollen en rechten beheren'],
    ];
}

function mp_role_permission_keys(): array {
    return array_map(function ($item) { return $item['key']; }, mp_role_catalog());
}

function mp_role_permission_set($values): array {
    $all = array_fill_keys(mp_role_permission_keys(), false);
    if ($values === 'all') {
        foreach ($all as $key => $_) $all[$key] = true;
        return $all;
    }
    foreach ((array)$values as $key) if (array_key_exists($key, $all)) $all[$key] = true;
    return $all;
}

function mp_role_defaults(): array {
    return ['version'=>1,'roles'=>[
        ['id'=>'beheerder','label'=>'Beheerder','builtIn'=>true,'permissions'=>mp_role_permission_set('all')],
        ['id'=>'gebruiker','label'=>'Gebruiker','builtIn'=>true,'permissions'=>mp_role_permission_set([
            'view.dashboard','view.devices','view.maintenance','view.breakdowns','view.faults','view.manuals','view.parts',
            'devices.add','devices.edit','devices.delete',
            'maintenance.add','maintenance.edit','maintenance.delete',
            'breakdowns.add','breakdowns.edit','breakdowns.delete',
            'parts.add','parts.edit','parts.stock','parts.delete','parts.export','print'
        ])],
        ['id'=>'technieker','label'=>'Technieker','builtIn'=>true,'permissions'=>mp_role_permission_set([
            'view.dashboard','view.devices','view.maintenance','view.breakdowns','view.faults','view.manuals','view.parts',
            'devices.statusNotes','maintenance.add','maintenance.edit','maintenance.delete',
            'breakdowns.add','breakdowns.edit','breakdowns.delete','print'
        ])],
        ['id'=>'magazijnier','label'=>'Magazijnier','builtIn'=>true,'permissions'=>mp_role_permission_set([
            'view.dashboard','view.parts','parts.add','parts.edit','parts.stock','parts.delete','parts.export','print'
        ])],
    ]];
}

function mp_role_sanitize_id($value): string {
    $id = strtolower(trim((string)$value));
    $id = preg_replace('/[^a-z0-9_-]+/', '-', $id);
    $id = trim((string)$id, '-');
    return substr($id, 0, 50);
}

function mp_role_normalize(array $config): array {
    $defaults = mp_role_defaults();
    $byId = [];
    foreach ($defaults['roles'] as $role) $byId[$role['id']] = $role;
    $input = isset($config['roles']) && is_array($config['roles']) ? $config['roles'] : [];
    $keys = mp_role_permission_keys();

    foreach ($input as $item) {
        if (!is_array($item)) continue;
        $id = mp_role_sanitize_id($item['id'] ?? '');
        if ($id === '') continue;
        $existing = $byId[$id] ?? null;
        $label = trim((string)($item['label'] ?? ($existing['label'] ?? $id)));
        if ($label === '') $label = $id;
        $label = function_exists('mb_substr') ? mb_substr($label, 0, 80, 'UTF-8') : substr($label, 0, 80);
        $source = isset($item['permissions']) && is_array($item['permissions']) ? $item['permissions'] : [];
        $permissions = array_fill_keys($keys, false);
        foreach ($keys as $key) {
            if (array_key_exists($key, $source)) {
                $permissions[$key] = (bool)$source[$key];
            } elseif ($key === 'view.manuals') {
                // Compatibiliteit met rollen die bestonden vóór Handleidingen
                // een expliciet recht werd: dezelfde afleiding behouden.
                $permissions[$key] = !empty($source['view.devices'])
                    || !empty($source['view.breakdowns'])
                    || !empty($source['view.settings'])
                    || ($existing && !empty($existing['builtIn']) && !empty($existing['permissions'][$key]));
            } elseif ($key === 'manuals.manage') {
                $permissions[$key] = !empty($source['view.settings'])
                    || ($existing && !empty($existing['builtIn']) && !empty($existing['permissions'][$key]));
            } elseif ($existing && !empty($existing['builtIn'])) {
                $permissions[$key] = !empty($existing['permissions'][$key]);
            }
        }
        $byId[$id] = [
            'id'=>$id,
            'label'=>$existing && !empty($existing['builtIn']) ? $existing['label'] : $label,
            'builtIn'=>$existing ? !empty($existing['builtIn']) : false,
            'permissions'=>$permissions,
        ];
    }

    return ['version'=>1,'roles'=>array_values($byId)];
}

function mp_role_read_config(): array {
    if (!is_file(MP_ROLE_FILE)) return mp_role_defaults();
    $raw = @file_get_contents(MP_ROLE_FILE);
    if ($raw === false || trim($raw) === '') return mp_role_defaults();
    $data = json_decode($raw, true);
    return is_array($data) ? mp_role_normalize($data) : mp_role_defaults();
}

function mp_role_etag(): ?string {
    if (!is_file(MP_ROLE_FILE)) return null;
    $hash = @hash_file('sha256', MP_ROLE_FILE);
    return $hash ? '"' . $hash . '"' : null;
}

function mp_role_write_config(array $config, ?string $expectedEtag = null): string {
    $dir = dirname(MP_ROLE_FILE);
    if (!is_dir($dir) || !is_writable($dir)) throw new RuntimeException('Rollenmap is niet schrijfbaar.');
    $current = mp_role_etag();
    if ($current !== null && $expectedEtag !== null && trim($expectedEtag) !== $current) {
        throw new RuntimeException('ROLE_CONFLICT');
    }
    if ($current !== null && $expectedEtag === null) throw new RuntimeException('ROLE_CONFLICT');

    $normalized = mp_role_normalize($config);
    $json = json_encode($normalized, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false) throw new RuntimeException('Rollen konden niet naar JSON worden omgezet.');
    $tmp = MP_ROLE_FILE . '.tmp-' . bin2hex(random_bytes(5));
    if (@file_put_contents($tmp, $json, LOCK_EX) === false) throw new RuntimeException('Tijdelijk rollenbestand kon niet worden geschreven.');
    if (!@rename($tmp, MP_ROLE_FILE)) {
        @unlink($tmp);
        throw new RuntimeException('Rollenbestand kon niet atomair worden opgeslagen.');
    }
    $etag = mp_role_etag();
    if ($etag === null) throw new RuntimeException('Rollenbestand kon niet worden gecontroleerd.');
    return $etag;
}

function mp_role_definition(string $roleId): array {
    $config = mp_role_read_config();
    $id = mp_role_sanitize_id($roleId);
    foreach ($config['roles'] as $role) if ($role['id'] === $id) return $role;
    foreach ($config['roles'] as $role) if ($role['id'] === 'gebruiker') return $role;
    return mp_role_defaults()['roles'][1];
}

function mp_role_permissions(string $roleId, bool $owner = false): array {
    if ($owner) return mp_role_permission_set('all');
    return mp_role_definition($roleId)['permissions'];
}

function mp_role_label(string $roleId, bool $owner = false): string {
    if ($owner) return 'Beheerder';
    return (string)(mp_role_definition($roleId)['label'] ?? 'Gebruiker');
}

function mp_role_exists(string $roleId): bool {
    $id = mp_role_sanitize_id($roleId);
    foreach (mp_role_read_config()['roles'] as $role) if ($role['id'] === $id) return true;
    return false;
}
