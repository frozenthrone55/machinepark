<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';
require_once __DIR__ . '/_photo-lib.php';

define('MP_DEVICE_PHOTO_PREFIX', 'device-photos/');

function device_photo_location(string $key): array {
    if (strpos($key, MP_DEVICE_PHOTO_PREFIX) !== 0) return ['', '', ''];
    $rest = substr($key, strlen(MP_DEVICE_PHOTO_PREFIX));
    $parts = explode('/', $rest);
    if (count($parts) !== 2) return ['', '', ''];
    $deviceId = mp_photo_safe_id($parts[0]);
    $token = mp_photo_safe_token($parts[1]);
    if ($deviceId === '' || $token === '') return ['', '', ''];
    $dir = MP_PHOTO_ROOT . '/devices/' . $deviceId;
    return [$dir, $dir . '/' . $token, $deviceId];
}

function device_photo_key_from_ref($value): string {
    return mp_photo_key_from_ref($value, 'device-photos.php', MP_DEVICE_PHOTO_PREFIX);
}

$user = mp_photo_require_local_user();
$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));

if ($method === 'GET' || $method === 'HEAD') {
    $key = rawurldecode((string)($_GET['key'] ?? ''));
    list($dir, $base, $deviceId) = device_photo_location($key);
    if ($base === '') mp_photo_json(['error'=>'Ongeldige fotoreferentie.'],400);
    mp_photo_serve($base, (string)($_GET['variant'] ?? '') === 'thumb', $method === 'HEAD');
}

if ($method !== 'POST') mp_photo_json(['error'=>'Methode niet toegestaan.'],405);

$raw = file_get_contents('php://input');
$body = json_decode($raw === false ? '' : $raw, true);
if (!is_array($body)) mp_photo_json(['error'=>'Ongeldige aanvraag.'],400);

$action = (string)($body['action'] ?? 'save');
$deviceId = mp_photo_safe_id($body['deviceId'] ?? '');
if ($deviceId === '') mp_photo_json(['error'=>'Ongeldig toestel.'],400);
$dir = MP_PHOTO_ROOT . '/devices/' . $deviceId;
mp_photo_ensure_dir($dir);
$prefix = MP_DEVICE_PHOTO_PREFIX . $deviceId . '/';

if ($action === 'thumbnail') {
    $key = device_photo_key_from_ref($body['photoRef'] ?? '');
    if ($key === '' || strpos($key, $prefix) !== 0) mp_photo_json(['error'=>'Een fotoreferentie hoort niet bij dit toestel.'],400);
    list($_dir, $base) = device_photo_location($key);
    if (!mp_photo_exists($base)) mp_photo_json(['error'=>'De originele toestelfoto bestaat niet meer.'],404);
    $thumb = mp_photo_parse_data_image($body['thumbnail'] ?? '', 180000);
    mp_photo_write_thumb($base, $thumb);
    mp_photo_json(['ok'=>true,'thumbnail'=>mp_photo_ref('device-photos.php',$key,true)]);
}

if (!mp_photo_can($user, ['devices.edit','devices.add'])) mp_photo_json(['error'=>'Deze rol mag toestelfoto’s niet wijzigen.'],403);

$photos = isset($body['photos']) && is_array($body['photos']) ? array_values($body['photos']) : [];
$thumbnails = isset($body['thumbnails']) && is_array($body['thumbnails']) ? array_values($body['thumbnails']) : [];
if (count($photos) > 5) mp_photo_json(['error'=>'Een toestel kan maximaal 5 foto’s bevatten.'],400);

$refs = [];
$keepTokens = [];
$totalBytes = 0;

foreach ($photos as $index => $photoValue) {
    $photo = trim((string)$photoValue);
    $thumbnail = trim((string)($thumbnails[$index] ?? ''));
    $existingKey = device_photo_key_from_ref($photo);

    if ($existingKey !== '') {
        if (strpos($existingKey, $prefix) !== 0) mp_photo_json(['error'=>'Een fotoreferentie hoort niet bij dit toestel.'],400);
        list($_dir, $base) = device_photo_location($existingKey);
        if (!mp_photo_exists($base)) mp_photo_json(['error'=>'Een bestaande toestelfoto ontbreekt op de NAS.'],404);
        $token = basename($base);
        $keepTokens[] = $token;
        $refs[] = mp_photo_ref('device-photos.php',$existingKey,false);
        if ($thumbnail !== '') mp_photo_write_thumb($base, mp_photo_parse_data_image($thumbnail,180000));
        continue;
    }

    if (mp_photo_is_legacy_ref($photo,'device-photos.php')) {
        $refs[] = $photo;
        continue;
    }

    try { $parsed = mp_photo_parse_data_image($photo,1200000); }
    catch (Throwable $e) { mp_photo_json(['error'=>$e->getMessage()], strpos($e->getMessage(),'te groot')!==false?413:400); }
    $totalBytes += strlen($parsed['bytes']);
    if ($totalBytes > 4000000) mp_photo_json(['error'=>'De geselecteerde toestelfoto’s zijn samen te groot.'],413);
    $token = bin2hex(random_bytes(16));
    $base = $dir . '/' . $token;
    mp_photo_write_blob($base,$parsed);
    $keepTokens[] = $token;
    $key = $prefix . $token;
    $refs[] = mp_photo_ref('device-photos.php',$key,false);
    if ($thumbnail !== '') mp_photo_write_thumb($base, mp_photo_parse_data_image($thumbnail,180000));
}

mp_photo_cleanup_bases($dir,$keepTokens);
mp_photo_json(['ok'=>true,'photos'=>$refs,'mode'=>'synology-local']);
