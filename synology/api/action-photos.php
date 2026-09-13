<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';
require_once __DIR__ . '/_photo-lib.php';

define('MP_ACTION_PHOTO_PREFIX', 'action-photos/');

function action_photo_location(string $key): array {
    if (strpos($key, MP_ACTION_PHOTO_PREFIX) !== 0) return ['', '', ''];
    $rest = substr($key, strlen(MP_ACTION_PHOTO_PREFIX));
    $parts = explode('/', $rest);
    if (count($parts) !== 2) return ['', '', ''];
    $actionId = mp_photo_safe_id($parts[0], 120);
    $token = mp_photo_safe_token($parts[1]);
    if ($actionId === '' || $token === '') return ['', '', ''];
    $dir = MP_PHOTO_ROOT . '/actions/' . $actionId;
    return [$dir, $dir . '/' . $token, $actionId];
}

function action_photo_key_from_ref($value): string {
    return mp_photo_key_from_ref($value, 'action-photos.php', MP_ACTION_PHOTO_PREFIX);
}

$user = mp_photo_require_local_user();
$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));

if ($method === 'GET' || $method === 'HEAD') {
    $key = rawurldecode((string)($_GET['key'] ?? ''));
    list($dir, $base, $actionId) = action_photo_location($key);
    if ($base === '') mp_photo_json(['error'=>'Ongeldige ToDo-fotoreferentie.'],400);
    mp_photo_serve($base, (string)($_GET['variant'] ?? '') === 'thumb', $method === 'HEAD');
}

if ($method !== 'POST') mp_photo_json(['error'=>'Methode niet toegestaan.'],405);
if (!mp_photo_can($user, ['actions.add','actions.edit','actions.delete'])) mp_photo_json(['error'=>'Deze rol mag ToDo-media niet wijzigen.'],403);

$raw = file_get_contents('php://input');
$body = json_decode($raw === false ? '' : $raw, true);
if (!is_array($body)) mp_photo_json(['error'=>'Ongeldige aanvraag.'],400);

$actionId = mp_photo_safe_id($body['actionId'] ?? '',120);
if ($actionId === '') mp_photo_json(['error'=>'Ongeldige ToDo.'],400);

$dir = MP_PHOTO_ROOT . '/actions/' . $actionId;
$prefix = MP_ACTION_PHOTO_PREFIX . $actionId . '/';
mp_photo_ensure_dir($dir);

$photos = isset($body['photos']) && is_array($body['photos']) ? array_values($body['photos']) : [];
$completeList = !empty($body['completeList']);
if (count($photos)>10) mp_photo_json(['error'=>'Een ToDo kan maximaal 10 foto’s en video’s samen bevatten.'],400);

$refs=[];$keepTokens=[];$seenHashes=[];$totalBytes=0;
foreach($photos as $photoValue){
    $photo=trim((string)$photoValue);
    if($photo==='')continue;
    $existingKey=action_photo_key_from_ref($photo);
    if($existingKey!==''){
        if(strpos($existingKey,$prefix)!==0)mp_photo_json(['error'=>'Een ToDo-fotoreferentie hoort niet bij deze ToDo.'],400);
        list($_dir,$base)=action_photo_location($existingKey);
        if(!mp_photo_exists($base))continue;
        $hash=@hash_file('sha256',$base.'.bin');
        if(is_string($hash)&&$hash!==''){
            if(isset($seenHashes[$hash]))continue;
            $seenHashes[$hash]=true;
        }
        $token=basename($base);
        $keepTokens[]=$token;
        $refs[]=mp_photo_ref_for_base('action-photos.php',$existingKey,$base,false);
        continue;
    }

    try{$parsed=mp_photo_parse_data_media($photo,1200000,20000000);}
    catch(Throwable $e){mp_photo_json(['error'=>$e->getMessage()],strpos($e->getMessage(),'te groot')!==false?413:400);}

    $hash=hash('sha256',$parsed['bytes']);
    if(isset($seenHashes[$hash]))continue;
    $seenHashes[$hash]=true;
    $totalBytes+=strlen($parsed['bytes']);
    if($totalBytes>24000000)mp_photo_json(['error'=>'De geselecteerde ToDo-media zijn samen te groot.'],413);

    $token=bin2hex(random_bytes(16));
    $base=$dir.'/'.$token;
    mp_photo_write_blob($base,$parsed);
    $keepTokens[]=$token;
    $key=$prefix.$token;
    $refs[]=mp_photo_ref_for_base('action-photos.php',$key,$base,false);
}
if($completeList)mp_photo_cleanup_bases($dir,$keepTokens);
mp_photo_json(['ok'=>true,'photos'=>array_slice($refs,0,10),'mode'=>'synology-local-action-photos']);

// machinepark-complete-role-permissions-v1
