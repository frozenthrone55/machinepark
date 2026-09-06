<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';
require_once __DIR__ . '/_audit-lib.php';
require_once __DIR__ . '/_photo-lib.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('X-Content-Type-Options: nosniff');

function purge_json(array $body, int $status=200): void {
    http_response_code($status);
    echo json_encode($body,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
    exit;
}

function purge_store($value): string {
    $store=trim((string)$value);
    return in_array($store,['maintenance','breakdowns'],true)?$store:'';
}

function purge_without_photos($item) {
    if(!is_array($item))return $item;
    $copy=$item;
    unset($copy['photos']);
    return $copy;
}

function purge_sanitize_undo($undo,string $store,string $entityId): array {
    if(!is_array($undo)||(string)($undo['storeName']??'')!==$store||(string)($undo['entityId']??'')!==$entityId){
        return ['undo'=>$undo,'changed'=>false,'removed'=>0];
    }
    $kind=(string)($undo['kind']??'');
    if($kind==='restore-deleted'&&isset($undo['beforeItem'])&&is_array($undo['beforeItem'])){
        $removed=isset($undo['beforeItem']['photos'])&&is_array($undo['beforeItem']['photos'])?count($undo['beforeItem']['photos']):0;
        if(!array_key_exists('photos',$undo['beforeItem']))return ['undo'=>$undo,'changed'=>false,'removed'=>0];
        $undo['beforeItem']=purge_without_photos($undo['beforeItem']);
        return ['undo'=>$undo,'changed'=>true,'removed'=>$removed];
    }
    if($kind==='remove-added'&&isset($undo['expectedAfter'])&&is_array($undo['expectedAfter'])){
        $removed=isset($undo['expectedAfter']['photos'])&&is_array($undo['expectedAfter']['photos'])?count($undo['expectedAfter']['photos']):0;
        if(!array_key_exists('photos',$undo['expectedAfter']))return ['undo'=>$undo,'changed'=>false,'removed'=>0];
        $undo['expectedAfter']=purge_without_photos($undo['expectedAfter']);
        return ['undo'=>$undo,'changed'=>true,'removed'=>$removed];
    }
    if($kind==='restore-fields'&&isset($undo['fields'])&&is_array($undo['fields'])){
        $fields=[];$changed=false;$removed=0;
        foreach($undo['fields'] as $field){
            if(is_array($field)&&(string)($field['key']??'')==='photos'){
                $changed=true;
                if(isset($field['beforeRaw'])&&is_array($field['beforeRaw']))$removed+=count($field['beforeRaw']);
                if(isset($field['afterRaw'])&&is_array($field['afterRaw']))$removed+=count($field['afterRaw']);
                continue;
            }
            $fields[]=$field;
        }
        if(!$changed)return ['undo'=>$undo,'changed'=>false,'removed'=>0];
        if($fields)$undo['fields']=$fields;else$undo=null;
        return ['undo'=>$undo,'changed'=>true,'removed'=>$removed];
    }
    return ['undo'=>$undo,'changed'=>false,'removed'=>0];
}

$user=mp_photo_require_local_user();
$method=strtoupper((string)($_SERVER['REQUEST_METHOD']??'GET'));
if($method!=='POST')purge_json(['error'=>'Methode niet toegestaan.'],405);
$raw=file_get_contents('php://input');$body=json_decode($raw===false?'':$raw,true);if(!is_array($body))$body=[];
$store=purge_store($body['storeName']??'');$entityId=mp_photo_safe_id($body['entityId']??'',120);
if($store===''||$entityId==='')purge_json(['error'=>'Ongeldig dossier.'],400);
$permission=$store==='maintenance'?'maintenance.delete':'breakdowns.delete';
if(!mp_photo_can($user,[$permission]))purge_json(['error'=>'Deze rol mag dit dossier niet verwijderen.'],403);

$photoDir=MP_PHOTO_ROOT.'/service/'.$store.'/'.$entityId;
$removedFiles=mp_photo_remove_directory($photoDir);
$updatedEntries=0;$removedPhotoPayloads=0;

try{
    mp_audit_ensure_dir();
    foreach((array)glob(MP_AUDIT_DIR.'/*.json') as $path){
        $rawEntry=@file_get_contents($path);
        $entry=$rawEntry!==false?json_decode($rawEntry,true):null;
        if(!is_array($entry)||!isset($entry['changes'])||!is_array($entry['changes']))continue;
        $changed=false;$changes=[];
        foreach($entry['changes'] as $change){
            if(!is_array($change)){ $changes[]=$change; continue; }
            $result=purge_sanitize_undo($change['undo']??null,$store,$entityId);
            if(!$result['changed']){$changes[]=$change;continue;}
            $changed=true;$removedPhotoPayloads+=(int)$result['removed'];
            if($result['undo']!==null)$change['undo']=$result['undo'];else unset($change['undo']);
            $changes[]=$change;
        }
        if(!$changed)continue;
        $entry['changes']=$changes;
        $json=json_encode($entry,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
        if($json!==false&&@file_put_contents($path,$json,LOCK_EX)!==false)$updatedEntries++;
    }
}catch(Throwable $e){
    purge_json(['error'=>'Foto’s zijn verwijderd, maar het lokale logboek kon niet volledig worden opgeschoond: '.$e->getMessage()],500);
}

purge_json([
    'ok'=>true,
    'updatedEntries'=>$updatedEntries,
    'removedPhotoPayloads'=>$removedPhotoPayloads,
    'removedFiles'=>$removedFiles,
    'mode'=>'synology-local'
]);
