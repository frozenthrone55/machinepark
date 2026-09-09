<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';
require_once __DIR__ . '/_photo-lib.php';

define('MP_READABLE_PHOTO_ROOT', '/volume1/MachineparkData/Fotos');

function mp_library_safe_segment($value, int $max = 120): string {
    $text = trim((string)$value);
    $text = preg_replace('/[^A-Za-z0-9._-]+/', '_', $text);
    $text = trim((string)$text, '._-');
    return substr((string)$text, 0, $max);
}

function mp_library_category($value): string {
    $allowed = ['Toestel','Onderhoud','Depannage','Service'];
    $text = trim((string)$value);
    return in_array($text, $allowed, true) ? $text : '';
}

function mp_library_source_from_ref($value): array {
    $text = trim((string)$value);
    if ($text === '') return ['', '', ''];

    $path = (string)(parse_url($text, PHP_URL_PATH) ?? '');
    $query = parse_url($text, PHP_URL_QUERY);
    if ($query === null || $query === false) return ['', '', ''];
    parse_str($query, $params);
    $key = rawurldecode((string)($params['key'] ?? ''));
    if ($key === '') return ['', '', ''];

    if (substr($path, -17) === '/device-photos.php' || substr($path, -16) === 'device-photos.php') {
        if (strpos($key, 'device-photos/') !== 0) return ['', '', ''];
        $rest = substr($key, strlen('device-photos/'));
        $parts = explode('/', $rest);
        if (count($parts) !== 2) return ['', '', ''];
        $deviceId = mp_photo_safe_id($parts[0]);
        $token = mp_photo_safe_token($parts[1]);
        if ($deviceId === '' || $token === '') return ['', '', ''];
        $base = MP_PHOTO_ROOT . '/devices/' . $deviceId . '/' . $token;
    } elseif (substr($path, -18) === '/service-photos.php' || substr($path, -17) === 'service-photos.php') {
        if (strpos($key, 'service-photos/') !== 0) return ['', '', ''];
        $rest = substr($key, strlen('service-photos/'));
        $parts = explode('/', $rest);
        if (count($parts) !== 3) return ['', '', ''];
        $store = in_array($parts[0], ['maintenance','breakdowns'], true) ? $parts[0] : '';
        $entityId = mp_photo_safe_id($parts[1],120);
        $token = mp_photo_safe_token($parts[2]);
        if ($store === '' || $entityId === '' || $token === '') return ['', '', ''];
        $base = MP_PHOTO_ROOT . '/service/' . $store . '/' . $entityId . '/' . $token;
    } else {
        return ['', '', ''];
    }

    if (!is_file($base . '.bin')) return ['', '', ''];
    $type = mp_photo_content_type($base . '.meta.json');
    $ext = $type === 'image/png' ? 'png' : ($type === 'image/webp' ? 'webp' : ($type === 'image/gif' ? 'gif' : 'jpg'));
    return [$base . '.bin', $ext, $type];
}

function mp_library_sync_dir(string $dir, array $desired): int {
    mp_photo_ensure_dir($dir);
    $removed = 0;
    foreach ((array)glob($dir . '/MP_*') as $path) {
        if (!is_file($path)) continue;
        if (isset($desired[basename($path)])) continue;
        if (@unlink($path)) $removed++;
    }
    return $removed;
}

$user = mp_photo_require_local_user();
if (!mp_photo_can($user, ['devices.edit','maintenance.edit','breakdowns.edit','devices.add','maintenance.add','breakdowns.add'])) {
    mp_photo_json(['error'=>'Deze rol mag de fotobibliotheek niet synchroniseren.'],403);
}

$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));
if ($method !== 'POST') mp_photo_json(['error'=>'Methode niet toegestaan.'],405);

$raw = file_get_contents('php://input');
$body = json_decode($raw === false ? '' : $raw, true);
if (!is_array($body)) mp_photo_json(['error'=>'Ongeldige aanvraag.'],400);

$devices = isset($body['devices']) && is_array($body['devices']) ? $body['devices'] : [];
$items = isset($body['items']) && is_array($body['items']) ? $body['items'] : [];
if (count($devices) > 5000 || count($items) > 15000) mp_photo_json(['error'=>'Te veel fotobibliotheekgegevens in één aanvraag.'],413);

mp_photo_ensure_dir(MP_READABLE_PHOTO_ROOT);

$categories = ['Toestel','Onderhoud','Depannage','Service'];
$deviceCodes = [];
foreach ($devices as $value) {
    $code = strtoupper(mp_library_safe_segment($value,80));
    if ($code !== '') $deviceCodes[$code] = true;
}

$desiredByDir = [];
$copied = 0;
$skipped = 0;

foreach ($items as $item) {
    if (!is_array($item)) continue;
    $deviceCode = strtoupper(mp_library_safe_segment($item['deviceCode'] ?? '',80));
    $category = mp_library_category($item['category'] ?? '');
    $recordId = mp_library_safe_segment($item['recordId'] ?? 'record',100);
    $date = preg_match('/^\d{4}-\d{2}-\d{2}$/', (string)($item['date'] ?? '')) ? (string)$item['date'] : '';
    $photos = isset($item['photos']) && is_array($item['photos']) ? array_values($item['photos']) : [];
    if ($deviceCode === '' || $category === '' || $recordId === '') continue;

    $deviceCodes[$deviceCode] = true;
    $dir = MP_READABLE_PHOTO_ROOT . '/' . $deviceCode . '/' . $category;
    if (!isset($desiredByDir[$dir])) $desiredByDir[$dir] = [];

    foreach (array_slice($photos,0,10) as $index => $photoRef) {
        list($source,$ext) = mp_library_source_from_ref($photoRef);
        if ($source === '') { $skipped++; continue; }
        $prefix = $date !== '' ? $date . '_' : '';
        $name = 'MP_' . $prefix . $recordId . '_' . str_pad((string)($index + 1),2,'0',STR_PAD_LEFT) . '.' . $ext;
        $desiredByDir[$dir][$name] = true;
        $target = $dir . '/' . $name;
        mp_photo_ensure_dir($dir);
        $needsCopy = !is_file($target) || filesize($target) !== filesize($source) || filemtime($target) < filemtime($source);
        if ($needsCopy) {
            $tmp = $target . '.tmp-' . bin2hex(random_bytes(4));
            if (!@copy($source,$tmp) || !@rename($tmp,$target)) {
                @unlink($tmp);
                throw new RuntimeException('Leesbare fotokopie kon niet worden bijgewerkt.');
            }
            $copied++;
        }
    }
}

$removed = 0;
foreach (array_keys($deviceCodes) as $deviceCode) {
    $deviceRoot = MP_READABLE_PHOTO_ROOT . '/' . $deviceCode;
    mp_photo_ensure_dir($deviceRoot);
    foreach ($categories as $category) {
        $dir = $deviceRoot . '/' . $category;
        $desired = $desiredByDir[$dir] ?? [];
        $removed += mp_library_sync_dir($dir,$desired);
    }
}

mp_photo_json([
    'ok'=>true,
    'root'=>MP_READABLE_PHOTO_ROOT,
    'devices'=>count($deviceCodes),
    'copied'=>$copied,
    'removed'=>$removed,
    'skipped'=>$skipped,
    'mode'=>'readable-photo-library',
]);
