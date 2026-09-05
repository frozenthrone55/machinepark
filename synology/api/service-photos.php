<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';
require_once __DIR__ . '/_photo-lib.php';

define('MP_SERVICE_PHOTO_PREFIX', 'service-photos/');

function service_photo_store($value): string {
    $store = trim((string)$value);
    return in_array($store, ['maintenance','breakdowns'], true) ? $store : '';
}

function service_photo_location(string $key): array {
    if (strpos($key, MP_SERVICE_PHOTO_PREFIX) !== 0) return ['', '', '', ''];
    $rest = substr($key, strlen(MP_SERVICE_PHOTO_PREFIX));
    $parts = explode('/', $rest);
    if (count($parts) !== 3) return ['', '', '', ''];
    $store = service_photo_store($parts[0]);
    $entityId = mp_photo_safe_id($parts[1], 120);
    $token = mp_photo_safe_token($parts[2]);
    if ($store === '' || $entityId === '' || $token === '') return ['', '', '', ''];
    $dir = MP_PHOTO_ROOT . '/service/' . $store . '/' . $entityId;
    return [$dir, $dir . '/' . $token, $store, $entityId];
}

function service_photo_key_from_ref($value): string {
    return mp_photo_key_from_ref($value, 'service-photos.php', MP_SERVICE_PHOTO_PREFIX);
}

$user = mp_photo_require_local_user();
$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));

if ($method === 'GET' || $method === 'HEAD') {
    $key = rawurldecode((string)($_GET['key'] ?? ''));
    list($dir, $base, $store, $entityId) = service_photo_location($key);
    if ($base === '') mp_photo_json(['error'=>'Ongeldige fotoreferentie.'],400);
    mp_photo_serve($base, (string)($_GET['variant'] ?? '') === 'thumb', $method === 'HEAD');
}

if ($method !== 'POST') mp_photo_json(['error'=>'Methode niet toegestaan.'],405);

$raw = file_get_contents('php://input');
$body = json_decode($raw === false ? '' : $raw, true);
if (!is_array($body)) mp_photo_json(['error'=>'Ongeldige aanvraag.'],400);

$action = (string)($body['action'] ?? 'save');
$store = service_photo_store($body['storeName'] ?? '');
$entityId = mp_photo_safe_id($body['entityId'] ?? '',120);
if ($store === '' || $entityId === '') mp_photo_json(['error'=>'Ongeldig onderhouds- of depannagedossier.'],400);
$permissionPrefix = $store === 'maintenance' ? 'maintenance' : 'breakdowns';
$dir = MP_PHOTO_ROOT . '/service/' . $store . '/' . $entityId;
$prefix = MP_SERVICE_PHOTO_PREFIX . $store . '/' . $entityId . '/';
mp_photo_ensure_dir($dir);

if ($action === 'thumbnail') {
    $key = service_photo_key_from_ref($body['photoRef'] ?? '');
    if ($key === '' || strpos($key,$prefix) !== 0) mp_photo_json(['error'=>'De fotoreferentie hoort niet bij dit dossier.'],400);
    list($_dir,$base) = service_photo_location($key);
    if (!mp_photo_exists($base)) mp_photo_json(['error'=>'De originele verslagfoto bestaat niet meer.'],404);
    mp_photo_write_thumb($base,mp_photo_parse_data_image($body['thumbnail'] ?? '',180000));
    mp_photo_json(['ok'=>true,'thumbnail'=>mp_photo_ref('service-photos.php',$key,true)]);
}

if (!mp_photo_can($user, [$permissionPrefix.'.edit',$permissionPrefix.'.add'])) {
    mp_photo_json(['error'=>'Deze rol mag verslagfoto’s niet wijzigen.'],403);
}

$photos = isset($body['photos']) && is_array($body['photos']) ? array_values($body['photos']) : [];
$thumbnails = isset($body['thumbnails']) && is_array($body['thumbnails']) ? array_values($body['thumbnails']) : [];
if (count($photos)>5) mp_photo_json(['error'=>'Een onderhouds- of depannageverslag kan maximaal 5 foto’s bevatten.'],400);

$refs=[];$keepTokens=[];$totalBytes=0;
foreach($photos as $index=>$photoValue){
    $photo=trim((string)$photoValue);
    $thumbnail=trim((string)($thumbnails[$index]??''));
    $existingKey=service_photo_key_from_ref($photo);

    if($existingKey!==''){
        if(strpos($existingKey,$prefix)!==0)mp_photo_json(['error'=>'Een fotoreferentie hoort niet bij dit dossier.'],400);
        list($_dir,$base)=service_photo_location($existingKey);
        if(!mp_photo_exists($base))mp_photo_json(['error'=>'Een bestaande verslagfoto ontbreekt op de NAS.'],404);
        $token=basename($base);
        $keepTokens[]=$token;
        $refs[]=mp_photo_ref('service-photos.php',$existingKey,false);
        if($thumbnail!=='')mp_photo_write_thumb($base,mp_photo_parse_data_image($thumbnail,180000));
        continue;
    }

    if(mp_photo_is_legacy_ref($photo,'service-photos.php')){
        $refs[]=$photo;
        continue;
    }

    try{$parsed=mp_photo_parse_data_image($photo,1200000);}
    catch(Throwable $e){mp_photo_json(['error'=>$e->getMessage()],strpos($e->getMessage(),'te groot')!==false?413:400);}
    $totalBytes+=strlen($parsed['bytes']);
    if($totalBytes>4000000)mp_photo_json(['error'=>'De geselecteerde verslagfoto’s zijn samen te groot.'],413);
    $token=bin2hex(random_bytes(16));
    $base=$dir.'/'.$token;
    mp_photo_write_blob($base,$parsed);
    $keepTokens[]=$token;
    $key=$prefix.$token;
    $refs[]=mp_photo_ref('service-photos.php',$key,false);
    if($thumbnail!=='')mp_photo_write_thumb($base,mp_photo_parse_data_image($thumbnail,180000));
}
mp_photo_cleanup_bases($dir,$keepTokens);
mp_photo_json(['ok'=>true,'photos'=>$refs,'mode'=>'synology-local']);
