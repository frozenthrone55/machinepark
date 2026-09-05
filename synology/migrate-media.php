<?php
declare(strict_types=1);

require_once __DIR__ . '/api/_auth-lib.php';
require_once __DIR__ . '/api/_photo-lib.php';

define('MP_MEDIA_STATE', '/volume1/MachineparkData/data/state-v1.json');
define('MP_MEDIA_LOCK', '/volume1/MachineparkData/data/state-v1.lock');
define('MP_MEDIA_BACKUPS', '/volume1/MachineparkData/backups');
define('MP_MEDIA_SESSION_DIR', '/volume1/MachineparkData/data');

function media_json(array $body, int $status = 200): void {
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
    header('X-Content-Type-Options: nosniff');
    http_response_code($status);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function media_h($value): string {
    return htmlspecialchars((string)$value, ENT_QUOTES, 'UTF-8');
}

function media_state_read(): array {
    if (!is_file(MP_MEDIA_STATE)) throw new RuntimeException('De lokale Machinepark-database is nog niet aanwezig.');
    $raw = @file_get_contents(MP_MEDIA_STATE);
    if ($raw === false) throw new RuntimeException('De lokale Machinepark-database kon niet worden gelezen.');
    $data = json_decode($raw, true);
    if (!is_array($data)) throw new RuntimeException('De lokale Machinepark-database bevat ongeldige JSON.');
    return $data;
}

function media_state_write(array $state): void {
    $json = json_encode($state, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false) throw new RuntimeException('De aangepaste database kon niet naar JSON worden omgezet.');
    $tmp = MP_MEDIA_STATE . '.media-' . bin2hex(random_bytes(5));
    if (@file_put_contents($tmp, $json, LOCK_EX) === false) {
        throw new RuntimeException('De aangepaste database kon niet tijdelijk worden opgeslagen.');
    }
    if (!@rename($tmp, MP_MEDIA_STATE)) {
        @unlink($tmp);
        throw new RuntimeException('De aangepaste database kon niet atomair worden opgeslagen.');
    }
}

function media_legacy_ref_info($value): ?array {
    $ref = trim((string)$value);
    if ($ref === '') return null;
    $path = (string)(parse_url($ref, PHP_URL_PATH) ?? '');
    $query = (string)(parse_url($ref, PHP_URL_QUERY) ?? '');
    if ($query === '') return null;

    $map = [
        '/.netlify/functions/device-photos' => 'device',
        '/.netlify/functions/part-photos' => 'part',
        '/.netlify/functions/service-photos' => 'service',
    ];
    if (!isset($map[$path])) return null;

    parse_str($query, $params);
    $key = rawurldecode((string)($params['key'] ?? ''));
    if ($key === '') return null;

    $valid = false;
    if ($map[$path] === 'device') $valid = strpos($key, 'device-photos/') === 0;
    if ($map[$path] === 'part') $valid = strpos($key, 'part-photos/') === 0;
    if ($map[$path] === 'service') $valid = strpos($key, 'service-photos/') === 0;
    if (!$valid) return null;

    return ['ref'=>$ref,'path'=>$path,'query'=>$query,'key'=>$key,'type'=>$map[$path]];
}

function media_entity_label(string $kind, array $item): string {
    if ($kind === 'device') return trim((string)($item['assetCode'] ?? $item['model'] ?? $item['id'] ?? 'Toestel'));
    if ($kind === 'part') return trim((string)($item['artNr'] ?? $item['description'] ?? $item['id'] ?? 'Onderdeel'));
    if ($kind === 'maintenance') return trim((string)($item['title'] ?? $item['type'] ?? $item['id'] ?? 'Onderhoud'));
    if ($kind === 'breakdown') return trim((string)($item['issue'] ?? $item['title'] ?? $item['id'] ?? 'Depannage'));
    return (string)($item['id'] ?? 'Item');
}

function media_scan(array $state): array {
    $refs = [];

    foreach ((array)($state['devices'] ?? []) as $item) {
        if (!is_array($item) || empty($item['id'])) continue;
        foreach ((array)($item['devicePhotos'] ?? []) as $index => $ref) {
            $info = media_legacy_ref_info($ref);
            if (!$info || $info['type'] !== 'device') continue;
            $id = hash('sha256', 'device|' . $item['id'] . '|' . $index . '|' . $info['ref']);
            $refs[] = [
                'refId'=>$id,'kind'=>'device','entityId'=>(string)$item['id'],'index'=>(int)$index,
                'label'=>media_entity_label('device',$item),'ref'=>$info['ref'],'key'=>$info['key'],
            ];
        }
    }

    foreach ((array)($state['parts'] ?? []) as $item) {
        if (!is_array($item) || empty($item['id'])) continue;
        $info = media_legacy_ref_info($item['photo'] ?? '');
        if (!$info || $info['type'] !== 'part') continue;
        $id = hash('sha256', 'part|' . $item['id'] . '|' . $info['ref']);
        $refs[] = [
            'refId'=>$id,'kind'=>'part','entityId'=>(string)$item['id'],'index'=>0,
            'label'=>media_entity_label('part',$item),'ref'=>$info['ref'],'key'=>$info['key'],
        ];
    }

    foreach (['maintenance','breakdowns'] as $store) {
        $kind = $store === 'maintenance' ? 'maintenance' : 'breakdown';
        foreach ((array)($state[$store] ?? []) as $item) {
            if (!is_array($item) || empty($item['id'])) continue;
            foreach ((array)($item['photos'] ?? []) as $index => $ref) {
                $info = media_legacy_ref_info($ref);
                if (!$info || $info['type'] !== 'service') continue;
                $id = hash('sha256', $kind . '|' . $item['id'] . '|' . $index . '|' . $info['ref']);
                $refs[] = [
                    'refId'=>$id,'kind'=>$kind,'entityId'=>(string)$item['id'],'index'=>(int)$index,
                    'label'=>media_entity_label($kind,$item),'ref'=>$info['ref'],'key'=>$info['key'],
                ];
            }
        }
    }

    return $refs;
}

function media_counts(array $refs): array {
    $counts = ['device'=>0,'part'=>0,'maintenance'=>0,'breakdown'=>0,'total'=>count($refs)];
    foreach ($refs as $ref) {
        $kind = (string)($ref['kind'] ?? '');
        if (isset($counts[$kind])) $counts[$kind]++;
    }
    return $counts;
}

function media_public_source($value): string {
    $text = trim((string)$value);
    if ($text === '') throw new RuntimeException('Vul het huidige online Machinepark-adres in.');
    $parts = parse_url($text);
    if (!is_array($parts) || strtolower((string)($parts['scheme'] ?? '')) !== 'https' || empty($parts['host'])) {
        throw new RuntimeException('Gebruik een geldig HTTPS-adres van de huidige online Machinepark-app.');
    }
    if (!empty($parts['user']) || !empty($parts['pass']) || !empty($parts['port'])) {
        throw new RuntimeException('Gebruik alleen het gewone HTTPS-hoofdadres, zonder gebruikersnaam of afwijkende poort.');
    }
    $host = strtolower((string)$parts['host']);

    if (filter_var($host, FILTER_VALIDATE_IP)) {
        if (!filter_var($host, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE)) {
            throw new RuntimeException('Een lokaal of gereserveerd bronadres is niet toegestaan.');
        }
    } else {
        $ips = @gethostbynamel($host);
        if (!is_array($ips) || !$ips) throw new RuntimeException('Het online bronadres kon niet via DNS worden gevonden.');
        foreach ($ips as $ip) {
            if (!filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE)) {
                throw new RuntimeException('Het online bronadres verwijst naar een lokaal of gereserveerd netwerk.');
            }
        }
    }

    return 'https://' . $host;
}

function media_fetch_url(string $url, int $maxBytes): array {
    $bytes = false;
    $status = 0;
    $type = '';
    $error = '';

    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, false);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 6);
        curl_setopt($ch, CURLOPT_TIMEOUT, 25);
        curl_setopt($ch, CURLOPT_USERAGENT, 'Machinepark-Synology-Migration/1');
        curl_setopt($ch, CURLOPT_FAILONERROR, false);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);
        $bytes = curl_exec($ch);
        $error = curl_error($ch);
        $status = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $type = strtolower(trim((string)curl_getinfo($ch, CURLINFO_CONTENT_TYPE)));
        curl_close($ch);
    } elseif (ini_get('allow_url_fopen')) {
        $context = stream_context_create([
            'http' => [
                'method' => 'GET',
                'timeout' => 25,
                'follow_location' => 0,
                'max_redirects' => 0,
                'user_agent' => 'Machinepark-Synology-Migration/1',
                'ignore_errors' => true,
            ],
            'ssl' => [
                'verify_peer' => true,
                'verify_peer_name' => true,
            ],
        ]);
        $bytes = @file_get_contents($url, false, $context, 0, $maxBytes + 1);
        $headers = isset($http_response_header) && is_array($http_response_header) ? $http_response_header : [];
        foreach ($headers as $header) {
            if (preg_match('#^HTTP/\\S+\\s+(\\d{3})#i', $header, $match)) $status = (int)$match[1];
            if (stripos($header, 'Content-Type:') === 0) $type = strtolower(trim(substr($header, 13)));
        }
        if ($bytes === false) $error = 'PHP kon de HTTPS-bron niet openen';
    } else {
        throw new RuntimeException('Voor de eenmalige cloudmigratie moet PHP cURL of allow_url_fopen beschikbaar zijn.');
    }

    if ($bytes === false) throw new RuntimeException('Download mislukt: ' . ($error ?: 'onbekende netwerkfout'));
    if ($status !== 200) throw new RuntimeException('De oude online foto gaf HTTP ' . $status . '.');
    if (strlen($bytes) < 1) throw new RuntimeException('De oude online foto is leeg.');
    if (strlen($bytes) > $maxBytes) throw new RuntimeException('De oude online foto is groter dan de toegestane migratielimiet.');
    if (strpos($type, 'image/') !== 0) throw new RuntimeException('De bron gaf geen afbeelding terug (' . ($type ?: 'onbekend type') . ').');

    $typeParts = explode(';', $type, 2);
    $type = $typeParts[0];
    return ['bytes'=>$bytes,'contentType'=>$type];
}

function media_source_url(string $sourceBase, string $legacyRef, bool $thumb = false): string {
    $path = (string)(parse_url($legacyRef, PHP_URL_PATH) ?? '');
    $query = (string)(parse_url($legacyRef, PHP_URL_QUERY) ?? '');
    if (strpos($path, '/.netlify/functions/') !== 0 || $query === '') throw new RuntimeException('Ongeldige oude fotoreferentie.');
    parse_str($query, $params);
    if ($thumb) $params['variant'] = 'thumb';
    else unset($params['variant']);
    return $sourceBase . $path . '?' . http_build_query($params, '', '&', PHP_QUERY_RFC3986);
}

function media_local_target(array $descriptor): array {
    $kind = (string)$descriptor['kind'];
    $entityId = mp_photo_safe_id($descriptor['entityId'] ?? '', 120);
    $legacyKey = (string)($descriptor['key'] ?? '');
    if ($entityId === '') throw new RuntimeException('Ongeldig lokaal item-ID.');

    if ($kind === 'device') {
        $token = mp_photo_safe_token(basename($legacyKey));
        if ($token === '') $token = bin2hex(random_bytes(16));
        $dir = MP_PHOTO_ROOT . '/devices/' . $entityId;
        return [
            'dir'=>$dir,'base'=>$dir . '/' . $token,
            'ref'=>mp_photo_ref('device-photos.php','device-photos/' . $entityId . '/' . $token,false),
        ];
    }
    if ($kind === 'part') {
        $dir = MP_PHOTO_ROOT . '/parts/' . $entityId;
        return [
            'dir'=>$dir,'base'=>$dir . '/photo',
            'ref'=>mp_photo_ref('part-photos.php','part-photos/' . $entityId . '/photo',false),
        ];
    }
    if ($kind === 'maintenance' || $kind === 'breakdown') {
        $store = $kind === 'maintenance' ? 'maintenance' : 'breakdowns';
        $token = mp_photo_safe_token(basename($legacyKey));
        if ($token === '') $token = bin2hex(random_bytes(16));
        $dir = MP_PHOTO_ROOT . '/service/' . $store . '/' . $entityId;
        return [
            'dir'=>$dir,'base'=>$dir . '/' . $token,
            'ref'=>mp_photo_ref('service-photos.php','service-photos/' . $store . '/' . $entityId . '/' . $token,false),
        ];
    }
    throw new RuntimeException('Onbekend fototype.');
}

function media_replace_ref(array &$state, array $descriptor, string $newRef): bool {
    $kind = (string)$descriptor['kind'];
    $entityId = (string)$descriptor['entityId'];
    $index = (int)$descriptor['index'];
    $oldRef = (string)$descriptor['ref'];

    if ($kind === 'device') {
        foreach ($state['devices'] as &$item) {
            if ((string)($item['id'] ?? '') !== $entityId) continue;
            if (!isset($item['devicePhotos'][$index]) || (string)$item['devicePhotos'][$index] !== $oldRef) return false;
            $item['devicePhotos'][$index] = $newRef;
            return true;
        }
        unset($item);
    } elseif ($kind === 'part') {
        foreach ($state['parts'] as &$item) {
            if ((string)($item['id'] ?? '') !== $entityId) continue;
            if ((string)($item['photo'] ?? '') !== $oldRef) return false;
            $item['photo'] = $newRef;
            return true;
        }
        unset($item);
    } else {
        $store = $kind === 'maintenance' ? 'maintenance' : 'breakdowns';
        foreach ($state[$store] as &$item) {
            if ((string)($item['id'] ?? '') !== $entityId) continue;
            if (!isset($item['photos'][$index]) || (string)$item['photos'][$index] !== $oldRef) return false;
            $item['photos'][$index] = $newRef;
            return true;
        }
        unset($item);
    }
    return false;
}

function media_session_path(string $id): string {
    return MP_MEDIA_SESSION_DIR . '/media-migration-' . $id . '.json';
}

function media_read_session(string $id, array $user): array {
    if (!preg_match('/^[a-f0-9]{24}$/', $id)) throw new RuntimeException('Ongeldige migratiesessie.');
    $path = media_session_path($id);
    if (!is_file($path)) throw new RuntimeException('Migratiesessie niet gevonden of al afgerond.');
    $raw = @file_get_contents($path);
    $data = $raw !== false ? json_decode($raw, true) : null;
    if (!is_array($data)) throw new RuntimeException('Migratiesessie is beschadigd.');
    if ((string)($data['userId'] ?? '') !== (string)($user['id'] ?? '')) throw new RuntimeException('Deze migratiesessie hoort bij een andere gebruiker.');
    return $data;
}

if (!mp_auth_is_local_ip(mp_auth_client_ip())) {
    http_response_code(403);
    echo 'Deze migratiepagina is alleen via het lokale netwerk bereikbaar.';
    exit;
}
try { $currentUser = mp_auth_require_user(); }
catch (Throwable $e) { http_response_code(401); echo 'Meld je eerst lokaal aan in Machinepark.'; exit; }
if (empty($currentUser['isOwner'])) {
    http_response_code(403);
    echo 'Alleen de lokale hoofdbeheerder kan oude cloudbestanden migreren.';
    exit;
}

$action = (string)($_GET['action'] ?? '');

if ($action === 'scan') {
    try {
        $refs = media_scan(media_state_read());
        media_json(['ok'=>true,'counts'=>media_counts($refs),'refs'=>$refs]);
    } catch (Throwable $e) {
        media_json(['error'=>$e->getMessage()],500);
    }
}

if ($action === 'begin' && strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET')) === 'POST') {
    $raw = file_get_contents('php://input');
    $body = json_decode($raw === false ? '' : $raw, true);
    if (!is_array($body)) $body = [];
    try {
        $sourceBase = media_public_source($body['sourceBase'] ?? '');
        $state = media_state_read();
        $refs = media_scan($state);
        if (!$refs) media_json(['ok'=>true,'done'=>true,'counts'=>media_counts($refs)]);

        if (!is_dir(MP_MEDIA_BACKUPS) || !is_writable(MP_MEDIA_BACKUPS)) {
            throw new RuntimeException('De back-upmap is niet schrijfbaar.');
        }
        $stamp = date('Ymd-His');
        $backup = MP_MEDIA_BACKUPS . '/media-migration-before-' . $stamp . '.json';
        $rawState = @file_get_contents(MP_MEDIA_STATE);
        if ($rawState === false || @file_put_contents($backup, $rawState, LOCK_EX) === false) {
            throw new RuntimeException('Voor de migratie kon geen veiligheidsback-up worden gemaakt.');
        }

        $id = bin2hex(random_bytes(12));
        $session = [
            'id'=>$id,
            'userId'=>(string)($currentUser['id'] ?? ''),
            'sourceBase'=>$sourceBase,
            'backup'=>$backup,
            'createdAt'=>date(DATE_ATOM),
        ];
        $json = json_encode($session, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        if ($json === false || @file_put_contents(media_session_path($id), $json, LOCK_EX) === false) {
            throw new RuntimeException('Migratiesessie kon niet worden opgeslagen.');
        }

        media_json(['ok'=>true,'migrationId'=>$id,'counts'=>media_counts($refs),'refs'=>$refs,'sourceBase'=>$sourceBase]);
    } catch (Throwable $e) {
        media_json(['error'=>$e->getMessage()],400);
    }
}

if ($action === 'migrate-one' && strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET')) === 'POST') {
    $raw = file_get_contents('php://input');
    $body = json_decode($raw === false ? '' : $raw, true);
    if (!is_array($body)) $body = [];
    try {
        $session = media_read_session((string)($body['migrationId'] ?? ''), $currentUser);
        $refId = (string)($body['refId'] ?? '');
        if (!preg_match('/^[a-f0-9]{64}$/', $refId)) throw new RuntimeException('Ongeldige fotoreferentie.');

        $lock = @fopen(MP_MEDIA_LOCK, 'c+');
        if ($lock === false || !flock($lock, LOCK_EX)) throw new RuntimeException('Databaselock kon niet worden verkregen.');

        $state = media_state_read();
        $refs = media_scan($state);
        $descriptor = null;
        foreach ($refs as $ref) if ((string)$ref['refId'] === $refId) { $descriptor = $ref; break; }

        if (!$descriptor) {
            flock($lock, LOCK_UN); fclose($lock);
            media_json(['ok'=>true,'skipped'=>true,'message'=>'Deze foto was al gemigreerd of is intussen gewijzigd.']);
        }

        $full = media_fetch_url(media_source_url((string)$session['sourceBase'], (string)$descriptor['ref'], false), 1600000);
        $target = media_local_target($descriptor);
        mp_photo_ensure_dir($target['dir']);
        mp_photo_write_blob($target['base'], $full);

        try {
            $thumb = media_fetch_url(media_source_url((string)$session['sourceBase'], (string)$descriptor['ref'], true), 180000);
            mp_photo_write_thumb($target['base'], $thumb);
        } catch (Throwable $thumbError) {
            // Geen geldige thumbnail is niet fataal; de app kan later lokaal een thumbnail maken.
        }

        if (!media_replace_ref($state, $descriptor, $target['ref'])) {
            mp_photo_delete_blob($target['base']);
            throw new RuntimeException('De fotoreferentie is tijdens de migratie gewijzigd. Er is niets vervangen.');
        }

        $state['updatedAt'] = date(DATE_ATOM);
        $state['mediaMigratedAt'] = $state['updatedAt'];
        $state['updatedBy'] = (string)($currentUser['id'] ?? '');
        $state['updatedByEmail'] = (string)($currentUser['email'] ?? '');
        media_state_write($state);

        flock($lock, LOCK_UN);
        fclose($lock);

        media_json([
            'ok'=>true,
            'kind'=>$descriptor['kind'],
            'label'=>$descriptor['label'],
            'newRef'=>$target['ref'],
            'remaining'=>count(media_scan($state)),
        ]);
    } catch (Throwable $e) {
        if (isset($lock) && is_resource($lock)) { @flock($lock, LOCK_UN); @fclose($lock); }
        media_json(['error'=>$e->getMessage()],400);
    }
}

if ($action === 'finish' && strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET')) === 'POST') {
    $raw = file_get_contents('php://input');
    $body = json_decode($raw === false ? '' : $raw, true);
    if (!is_array($body)) $body = [];
    try {
        $id = (string)($body['migrationId'] ?? '');
        $session = media_read_session($id, $currentUser);
        $refs = media_scan(media_state_read());
        if (!$refs) @unlink(media_session_path($id));
        media_json([
            'ok'=>true,
            'remaining'=>count($refs),
            'counts'=>media_counts($refs),
            'backup'=>basename((string)($session['backup'] ?? '')),
        ]);
    } catch (Throwable $e) {
        media_json(['error'=>$e->getMessage()],400);
    }
}

try {
    $initialRefs = media_scan(media_state_read());
    $initialCounts = media_counts($initialRefs);
} catch (Throwable $e) {
    $initialRefs = [];
    $initialCounts = ['device'=>0,'part'=>0,'maintenance'=>0,'breakdown'=>0,'total'=>0];
    $pageError = $e->getMessage();
}
?><!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Machinepark · oude foto's migreren</title>
<style>
:root{font-family:Verdana,Arial,sans-serif;color:#1c2a26;background:#edf3f1}*{box-sizing:border-box}body{margin:0;padding:24px}.wrap{max-width:920px;margin:auto}.card{background:#fff;border:1px solid #d6e0dd;border-radius:18px;padding:22px;box-shadow:0 12px 30px rgba(25,55,47,.08);margin-bottom:16px}h1{margin:0 0 8px;font-size:28px}h2{font-size:18px;margin:0 0 12px}.muted{color:#667773;font-size:13px;line-height:1.55}.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:16px 0}.stat{border:1px solid #dce5e2;border-radius:12px;padding:12px;text-align:center}.stat strong{display:block;font-size:22px}.field{display:grid;gap:6px;margin:14px 0}.field input{padding:11px 12px;border:1px solid #cbd8d4;border-radius:10px;font:inherit}.btn{border:0;border-radius:11px;padding:11px 15px;font-weight:700;cursor:pointer;background:#164a3c;color:#fff}.btn:disabled{opacity:.55;cursor:not-allowed}.progress{height:12px;background:#e4ece9;border-radius:999px;overflow:hidden;margin:14px 0}.bar{height:100%;width:0;background:#2f8068;transition:width .2s}.log{max-height:320px;overflow:auto;border:1px solid #e0e7e5;border-radius:12px;padding:10px;font-size:12px;line-height:1.5;background:#fafcfc}.ok{color:#247458}.err{color:#a13b3b}.warn{background:#fff8e9;border:1px solid #eed9a1;border-radius:12px;padding:12px;font-size:13px;line-height:1.5}@media(max-width:720px){.grid{grid-template-columns:1fr 1fr}.grid .stat:last-child{grid-column:1/-1}}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>Oude foto's naar Synology</h1>
    <p class="muted">Deze stap kopieert alleen foto's die nog naar de vroegere Netlify-opslag verwijzen. Voor de eerste wijziging wordt automatisch een veiligheidskopie van <code>state-v1.json</code> gemaakt. Reeds lokale foto's worden niet aangeraakt.</p>
    <?php if (!empty($pageError)): ?><div class="warn"><?=media_h($pageError)?></div><?php endif; ?>
    <div class="grid">
      <div class="stat"><strong id="cDevice"><?=$initialCounts['device']?></strong><span>Toestel</span></div>
      <div class="stat"><strong id="cPart"><?=$initialCounts['part']?></strong><span>Onderdeel</span></div>
      <div class="stat"><strong id="cMaintenance"><?=$initialCounts['maintenance']?></strong><span>Onderhoud</span></div>
      <div class="stat"><strong id="cBreakdown"><?=$initialCounts['breakdown']?></strong><span>Depannage</span></div>
      <div class="stat"><strong id="cTotal"><?=$initialCounts['total']?></strong><span>Totaal oud</span></div>
    </div>
  </div>

  <div class="card">
    <h2>Bron van de huidige online app</h2>
    <p class="muted">Vul het HTTPS-hoofdadres in waarmee je de oude online Machinepark-versie opent, bijvoorbeeld <code>https://jouw-site.netlify.app</code>. Het adres wordt alleen gebruikt om de nog ontbrekende oude foto's te downloaden.</p>
    <div class="field"><label for="sourceBase">Online Machinepark-adres</label><input id="sourceBase" type="url" placeholder="https://...netlify.app" autocomplete="off"></div>
    <button class="btn" id="startBtn" type="button" <?=$initialCounts['total'] ? '' : 'disabled'?>>Migratie starten</button>
    <?php if (!$initialCounts['total']): ?><p class="ok" style="font-size:13px">Er zijn geen oude Netlify-fotoreferenties meer in de lokale database.</p><?php endif; ?>
  </div>

  <div class="card" id="progressCard" style="display:none">
    <h2>Voortgang</h2>
    <div class="progress"><div class="bar" id="bar"></div></div>
    <div class="muted" id="progressText">Voorbereiden…</div>
    <div class="log" id="log"></div>
  </div>
</div>
<script>
const startBtn=document.getElementById('startBtn');
const sourceInput=document.getElementById('sourceBase');
const card=document.getElementById('progressCard');
const bar=document.getElementById('bar');
const text=document.getElementById('progressText');
const log=document.getElementById('log');

try{sourceInput.value=localStorage.getItem('machinepark-old-online-url')||''}catch(_){}

function line(message,cls=''){const div=document.createElement('div');if(cls)div.className=cls;div.textContent=message;log.appendChild(div);log.scrollTop=log.scrollHeight}
async function api(action,payload=null){
  const options={cache:'no-store'};
  if(payload){options.method='POST';options.headers={'Content-Type':'application/json'};options.body=JSON.stringify(payload)}
  const res=await fetch('?action='+encodeURIComponent(action),options);
  const body=await res.json().catch(()=>({}));
  if(!res.ok)throw new Error(body.error||('HTTP '+res.status));
  return body;
}
function setCounts(c){document.getElementById('cDevice').textContent=c.device||0;document.getElementById('cPart').textContent=c.part||0;document.getElementById('cMaintenance').textContent=c.maintenance||0;document.getElementById('cBreakdown').textContent=c.breakdown||0;document.getElementById('cTotal').textContent=c.total||0}

startBtn?.addEventListener('click',async()=>{
  const sourceBase=String(sourceInput.value||'').trim();
  if(!sourceBase){alert('Vul eerst het huidige online Machinepark-adres in.');return}
  startBtn.disabled=true;card.style.display='block';log.innerHTML='';bar.style.width='0%';text.textContent='Veiligheidsback-up maken…';
  try{
    try{localStorage.setItem('machinepark-old-online-url',sourceBase)}catch(_){}
    const begin=await api('begin',{sourceBase});
    if(begin.done){line('Geen oude foto’s meer gevonden.','ok');text.textContent='Klaar';bar.style.width='100%';return}
    const refs=Array.isArray(begin.refs)?begin.refs:[];
    const total=refs.length;let done=0,failed=0;
    line('Veiligheidsback-up gemaakt. '+total+' oude foto(\'s) gevonden.','ok');

    for(const ref of refs){
      text.textContent='Kopiëren '+(done+failed+1)+' van '+total+' · '+(ref.label||ref.kind);
      try{
        const result=await api('migrate-one',{migrationId:begin.migrationId,refId:ref.refId});
        done++;
        line('✓ '+(ref.label||ref.kind),'ok');
      }catch(error){
        failed++;
        line('✗ '+(ref.label||ref.kind)+' · '+error.message,'err');
      }
      bar.style.width=Math.round(((done+failed)/Math.max(1,total))*100)+'%';
    }

    const finish=await api('finish',{migrationId:begin.migrationId});
    setCounts(finish.counts||{});
    text.textContent=failed?('Afgerond · '+done+' gekopieerd · '+failed+' niet gelukt · '+finish.remaining+' nog oud'):('Klaar · '+done+' foto’s lokaal opgeslagen');
    if(finish.backup)line('Veiligheidsback-up: '+finish.backup,'ok');
    if(finish.remaining===0)line('Alle gevonden oude fotoreferenties zijn nu lokaal.','ok');
    else line('Je kunt de migratie later opnieuw starten; alleen de resterende foto’s worden dan aangeboden.','err');
  }catch(error){
    text.textContent='Migratie kon niet starten';
    line(error.message,'err');
  }finally{
    startBtn.disabled=false;
  }
});
</script>
</body>
</html>
