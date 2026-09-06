<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';
require_once __DIR__ . '/_photo-lib.php';

define('MP_PART_PHOTO_PREFIX', 'part-photos/');

function part_photo_location(string $key): array {
    if (strpos($key, MP_PART_PHOTO_PREFIX) !== 0) return ['', '', ''];
    $rest = substr($key, strlen(MP_PART_PHOTO_PREFIX));
    $parts = explode('/', $rest);
    if (count($parts) !== 2 || $parts[1] !== 'photo') return ['', '', ''];
    $partId = mp_photo_safe_id($parts[0]);
    if ($partId === '') return ['', '', ''];
    $dir = MP_PHOTO_ROOT . '/parts/' . $partId;
    return [$dir, $dir . '/photo', $partId];
}

function part_photo_key_from_ref($value): string {
    return mp_photo_key_from_ref($value, 'part-photos.php', MP_PART_PHOTO_PREFIX);
}

$user = mp_photo_require_local_user();
$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));

if ($method === 'GET' || $method === 'HEAD') {
    $key = rawurldecode((string)($_GET['key'] ?? ''));
    list($dir, $base, $partId) = part_photo_location($key);
    if ($base === '') mp_photo_json(['error'=>'Ongeldige fotoreferentie.'],400);
    mp_photo_serve($base, (string)($_GET['variant'] ?? '') === 'thumb', $method === 'HEAD');
}

if ($method !== 'POST') mp_photo_json(['error'=>'Methode niet toegestaan.'],405);

$raw = file_get_contents('php://input');
$body = json_decode($raw === false ? '' : $raw, true);
if (!is_array($body)) mp_photo_json(['error'=>'Ongeldige aanvraag.'],400);

$action = (string)($body['action'] ?? 'save');
$partId = mp_photo_safe_id($body['partId'] ?? '');
if ($partId === '') mp_photo_json(['error'=>'Ongeldig onderdeel.'],400);
$key = MP_PART_PHOTO_PREFIX . $partId . '/photo';
$dir = MP_PHOTO_ROOT . '/parts/' . $partId;
$base = $dir . '/photo';
mp_photo_ensure_dir($dir);

if ($action === 'thumbnail') {
    $refKey = part_photo_key_from_ref($body['photoRef'] ?? '');
    if ($refKey !== $key) mp_photo_json(['error'=>'De fotoreferentie hoort niet bij dit onderdeel.'],400);
    if (!mp_photo_exists($base)) mp_photo_json(['error'=>'De originele onderdeelfoto bestaat niet meer.'],404);
    mp_photo_write_thumb($base, mp_photo_parse_data_image($body['thumbnail'] ?? '',180000));
    mp_photo_json(['ok'=>true,'thumbnail'=>mp_photo_ref('part-photos.php',$key,true)]);
}

if (!mp_photo_can($user, ['parts.edit','parts.add'])) mp_photo_json(['error'=>'Deze rol mag onderdeelfoto’s niet wijzigen.'],403);

$photo = trim((string)($body['photo'] ?? ''));
$thumbnail = trim((string)($body['thumbnail'] ?? ''));

if ($photo === '') {
    mp_photo_delete_blob($base);
    mp_photo_json(['ok'=>true,'photo'=>'','mode'=>'synology-local']);
}

$existingKey = part_photo_key_from_ref($photo);
if ($existingKey !== '') {
    if ($existingKey !== $key) mp_photo_json(['error'=>'De fotoreferentie hoort niet bij dit onderdeel.'],400);
    if (!mp_photo_exists($base)) mp_photo_json(['error'=>'De bestaande onderdeelfoto ontbreekt op de NAS.'],404);
    if ($thumbnail !== '') mp_photo_write_thumb($base, mp_photo_parse_data_image($thumbnail,180000));
    mp_photo_json(['ok'=>true,'photo'=>mp_photo_ref('part-photos.php',$key,false),'mode'=>'synology-local']);
}

if (mp_photo_is_legacy_ref($photo,'part-photos.php')) {
    mp_photo_json(['ok'=>true,'photo'=>$photo,'legacy'=>true,'mode'=>'synology-local']);
}

try { $parsed = mp_photo_parse_data_image($photo,1500000); }
catch (Throwable $e) { mp_photo_json(['error'=>$e->getMessage()], strpos($e->getMessage(),'te groot')!==false?413:400); }
mp_photo_write_blob($base,$parsed);
if ($thumbnail !== '') mp_photo_write_thumb($base, mp_photo_parse_data_image($thumbnail,180000));
mp_photo_json(['ok'=>true,'photo'=>mp_photo_ref('part-photos.php',$key,false),'mode'=>'synology-local']);
