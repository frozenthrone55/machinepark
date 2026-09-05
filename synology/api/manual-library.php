<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';
require_once __DIR__ . '/_audit-lib.php';

header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('X-Content-Type-Options: nosniff');

define('MP_MANUAL_CONFIG', '/volume1/MachineparkData/data/manual-library-v1.json');
define('MP_MANUAL_LOCK', '/volume1/MachineparkData/data/manual-library-v1.lock');
define('MP_MANUAL_DIR', '/volume1/MachineparkData/manuals');
define('MP_MANUAL_UPLOAD_DIR', '/volume1/MachineparkData/uploads');
define('MP_MANUAL_MAX_BYTES', 12000000);
define('MP_MANUAL_MAX_ITEMS', 1000);

function manual_json(array $body, int $status = 200, array $headers = []): void {
    header('Content-Type: application/json; charset=utf-8');
    http_response_code($status);
    foreach ($headers as $name=>$value) header($name . ': ' . $value);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function manual_text($value, int $max = 500): string {
    $text=trim((string)$value);
    return function_exists('mb_substr')?mb_substr($text,0,$max,'UTF-8'):substr($text,0,$max);
}

function manual_id($value): string {
    $id=strtolower(trim((string)$value));
    $id=preg_replace('/[^a-z0-9_-]+/','-',$id);
    $id=trim((string)$id,'-');
    return substr($id,0,90);
}

function manual_file_key($value): string {
    $key=trim((string)$value);
    return preg_match('#^manual-files/[A-Za-z0-9._-]+\.pdf$#',$key)?$key:'';
}

function manual_file_path(string $key): string {
    $safe=manual_file_key($key);
    return $safe===''?'':MP_MANUAL_DIR . '/' . basename($safe);
}

function manual_sanitize(array $raw, ?array $existing=null): array {
    $title=manual_text($raw['title']??'',180);
    if($title==='')throw new RuntimeException('Geef de handleiding een titel.');
    $fileKey=manual_file_key($raw['fileKey']??($existing['fileKey']??''));
    if($fileKey==='')throw new RuntimeException('Kies een geldig PDF-bestand voor deze handleiding.');
    $brand=manual_text($raw['brand']??'',100);
    $model=$brand!==''?manual_text($raw['model']??'',140):'';
    $now=date(DATE_ATOM);
    $id=manual_id($raw['id']??($existing['id']??($brand.'-'.$model.'-'.$title)));
    if($id==='')$id='manual-'.bin2hex(random_bytes(8));
    return [
        'id'=>$id,
        'title'=>$title,
        'type'=>manual_text($raw['type']??'',100)?:'Overig',
        'brand'=>$brand,
        'model'=>$model,
        'deviceId'=>manual_text($raw['deviceId']??'',120),
        'versionLabel'=>manual_text($raw['versionLabel']??'',80),
        'language'=>manual_text($raw['language']??'',60)?:'Nederlands',
        'notes'=>manual_text($raw['notes']??'',2000),
        'fileKey'=>$fileKey,
        'fileName'=>manual_text($raw['fileName']??($existing['fileName']??''),220)?:'handleiding.pdf',
        'fileSize'=>max(0,(int)($raw['fileSize']??($existing['fileSize']??0))),
        'active'=>array_key_exists('active',$raw)?(bool)$raw['active']:true,
        'version'=>$existing?max(1,(int)($existing['version']??1))+1:max(1,(int)($raw['version']??1)),
        'createdAt'=>$existing['createdAt']??($raw['createdAt']??$now),
        'updatedAt'=>$now,
    ];
}

function manual_normalize(array $data): array {
    $manuals=[];$seen=[];
    foreach(array_slice(isset($data['manuals'])&&is_array($data['manuals'])?$data['manuals']:[],0,MP_MANUAL_MAX_ITEMS) as $item){
        if(!is_array($item))continue;
        try{
            $m=manual_sanitize($item,$item);
            if(isset($seen[$m['id']]))continue;
            $seen[$m['id']]=true;
            $m['version']=max(1,(int)($item['version']??1));
            $m['createdAt']=(string)($item['createdAt']??$m['createdAt']);
            $m['updatedAt']=(string)($item['updatedAt']??$m['updatedAt']);
            $manuals[]=$m;
        }catch(Throwable $e){}
    }
    return ['version'=>1,'manuals'=>$manuals];
}

function manual_read(): array {
    if(!is_file(MP_MANUAL_CONFIG))return ['version'=>1,'manuals'=>[]];
    $raw=@file_get_contents(MP_MANUAL_CONFIG);
    $data=$raw!==false?json_decode($raw,true):null;
    return is_array($data)?manual_normalize($data):['version'=>1,'manuals'=>[]];
}

function manual_etag(): ?string {
    if(!is_file(MP_MANUAL_CONFIG))return null;
    $hash=@hash_file('sha256',MP_MANUAL_CONFIG);
    return $hash?'"'.$hash.'"':null;
}

function manual_write(array $data, ?string $expected): string {
    $current=manual_etag();
    if($current!==null&&($expected===null||trim($expected)!==$current))throw new RuntimeException('CONFLICT');
    $json=json_encode(manual_normalize($data),JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
    if($json===false)throw new RuntimeException('Handleidingen konden niet naar JSON worden omgezet.');
    $tmp=MP_MANUAL_CONFIG.'.tmp-'.bin2hex(random_bytes(5));
    if(@file_put_contents($tmp,$json,LOCK_EX)===false)throw new RuntimeException('Handleidingenconfiguratie kon niet worden geschreven.');
    if(!@rename($tmp,MP_MANUAL_CONFIG)){@unlink($tmp);throw new RuntimeException('Handleidingenconfiguratie kon niet atomair worden opgeslagen.');}
    return manual_etag()?:'';
}

function manual_upload_id($value): string {
    $id=preg_replace('/[^A-Za-z0-9_-]/','',(string)$value);
    return substr((string)$id,0,100);
}

function manual_upload_path(string $uploadId): string {
    return MP_MANUAL_UPLOAD_DIR . '/manual-' . $uploadId;
}

function manual_remove_tree(string $dir): void {
    if(!is_dir($dir))return;
    foreach((array)glob($dir.'/*') as $file)if(is_file($file))@unlink($file);
    @rmdir($dir);
}

function manual_can_read(array $p, array $user): bool {
    return !empty($user['isOwner']) || !empty($p['view.manuals']);
}
function manual_can_manage(array $p, array $user): bool {
    return !empty($user['isOwner']) || !empty($p['manuals.manage']);
}

function manual_serve_pdf(array $config, string $key): void {
    $safe=manual_file_key($key);
    if($safe==='')manual_json(['error'=>'Ongeldige PDF-referentie.'],400);
    $found=null;
    foreach($config['manuals'] as $m)if($m['fileKey']===$safe&&!empty($m['active'])){$found=$m;break;}
    if(!$found)manual_json(['error'=>'Handleiding niet gevonden.'],404);
    $path=manual_file_path($safe);
    if(!is_file($path))manual_json(['error'=>'PDF-bestand niet gevonden.'],404);
    $name=str_replace(["\r","\n",'"'],'_',basename((string)($found['fileName']??'handleiding.pdf')));
    header('Content-Type: application/pdf');
    header('Content-Disposition: inline; filename="'.$name.'"');
    header('Content-Length: '.filesize($path));
    header('Cache-Control: private, no-store, max-age=0');
    readfile($path);
    exit;
}

if(!mp_auth_is_local_ip(mp_auth_client_ip()))manual_json(['error'=>'Lokale handleidingen zijn voorlopig alleen via het lokale netwerk bereikbaar.'],403);
try{$user=mp_auth_require_user();}catch(Throwable $e){manual_json(['error'=>'Niet aangemeld.'],401);}
$permissions=mp_role_permissions((string)($user['role']??'gebruiker'),!empty($user['isOwner']));
$canRead=manual_can_read($permissions,$user);$canManage=manual_can_manage($permissions,$user);
if(!$canRead&&!$canManage)manual_json(['error'=>'Deze rol mag geen handleidingen bekijken.'],403);

if(!is_dir(MP_MANUAL_DIR)&&!@mkdir(MP_MANUAL_DIR,0770,true)&&!is_dir(MP_MANUAL_DIR))manual_json(['error'=>'Handleidingenmap kon niet worden aangemaakt.'],500);
if(!is_dir(MP_MANUAL_UPLOAD_DIR)&&!@mkdir(MP_MANUAL_UPLOAD_DIR,0770,true)&&!is_dir(MP_MANUAL_UPLOAD_DIR))manual_json(['error'=>'Uploadmap kon niet worden aangemaakt.'],500);

$method=strtoupper((string)($_SERVER['REQUEST_METHOD']??'GET'));
$config=manual_read();$etag=manual_etag();

if($method==='GET'){
    if(isset($_GET['file'])&&$_GET['file']!=='')manual_serve_pdf($config,(string)$_GET['file']);
    $client=trim((string)($_SERVER['HTTP_X_MACHINEPARK_IF_NONE_MATCH']??''));
    if($etag&&$client!==''&&$client===$etag)manual_json(['unchanged'=>true,'etag'=>$etag,'canManage'=>$canManage,'mode'=>'synology-local']);
    manual_json(['manuals'=>$config['manuals'],'etag'=>$etag,'canManage'=>$canManage,'mode'=>'synology-local'],200,$etag?['ETag'=>$etag]:[]);
}

if($method==='PUT'){
    if(!$canManage)manual_json(['error'=>'Alleen een beheerder kan handleidingen uploaden.'],403);
    $action=(string)($_GET['action']??'');
    $uploadId=manual_upload_id($_GET['uploadId']??'');
    if($uploadId==='')manual_json(['error'=>'Ongeldige upload-ID.'],400);
    $dir=manual_upload_path($uploadId);

    if($action==='abort-upload'){
        manual_remove_tree($dir);
        manual_json(['ok'=>true]);
    }

    $total=(int)($_GET['total']??0);
    if($total<1||$total>8)manual_json(['error'=>'Ongeldig aantal PDF-blokken.'],400);
    $fileSize=(int)($_GET['fileSize']??0);
    if($fileSize<1||$fileSize>MP_MANUAL_MAX_BYTES)manual_json(['error'=>'De PDF is groter dan 12 MB of leeg.'],413);

    if($action==='upload-chunk'){
        $index=(int)($_GET['index']??-1);
        if($index<0||$index>=$total)manual_json(['error'=>'Ongeldig PDF-blok.'],400);
        if(!is_dir($dir)&&!@mkdir($dir,0770,true)&&!is_dir($dir))manual_json(['error'=>'Tijdelijke uploadmap kon niet worden aangemaakt.'],500);
        $raw=file_get_contents('php://input');
        if($raw===false||strlen($raw)===0)manual_json(['error'=>'PDF-blok is leeg.'],400);
        if(strlen($raw)>4000000)manual_json(['error'=>'PDF-blok is te groot.'],413);
        if(@file_put_contents($dir.'/'.sprintf('%03d',$index).'.part',$raw,LOCK_EX)===false)manual_json(['error'=>'PDF-blok kon niet worden opgeslagen.'],500);
        manual_json(['ok'=>true,'index'=>$index]);
    }

    if($action==='finalize-upload'){
        if(!is_dir($dir))manual_json(['error'=>'Uploadblokken niet gevonden.'],400);
        $tmp=MP_MANUAL_DIR.'/upload-'.bin2hex(random_bytes(8)).'.tmp';
        $out=@fopen($tmp,'wb');
        if($out===false)manual_json(['error'=>'PDF kon niet worden samengesteld.'],500);
        $written=0;
        for($i=0;$i<$total;$i++){
            $part=$dir.'/'.sprintf('%03d',$i).'.part';
            if(!is_file($part)){fclose($out);@unlink($tmp);manual_json(['error'=>'Een PDF-blok ontbreekt.'],400);}
            $in=@fopen($part,'rb');
            if($in===false){fclose($out);@unlink($tmp);manual_json(['error'=>'Een PDF-blok kon niet worden gelezen.'],500);}
            $written+=stream_copy_to_stream($in,$out);
            fclose($in);
            if($written>MP_MANUAL_MAX_BYTES){fclose($out);@unlink($tmp);manual_remove_tree($dir);manual_json(['error'=>'De PDF is groter dan 12 MB.'],413);}
        }
        fclose($out);
        if($written!==$fileSize){@unlink($tmp);manual_remove_tree($dir);manual_json(['error'=>'De PDF-grootte klopt niet met de upload.'],400);}
        $head=@file_get_contents($tmp,false,null,0,5);
        if($head!=='%PDF-'){@unlink($tmp);manual_remove_tree($dir);manual_json(['error'=>'Het gekozen bestand is geen geldige PDF.'],400);}
        $basename=bin2hex(random_bytes(16)).'.pdf';
        $final=MP_MANUAL_DIR.'/'.$basename;
        if(!@rename($tmp,$final)){@unlink($tmp);manual_remove_tree($dir);manual_json(['error'=>'PDF kon niet definitief worden opgeslagen.'],500);}
        manual_remove_tree($dir);
        $name=manual_text($_GET['fileName']??'handleiding.pdf',220);
        if(strtolower(substr($name,-4))!=='.pdf')$name.='.pdf';
        manual_json(['ok'=>true,'fileKey'=>'manual-files/'.$basename,'fileName'=>$name,'fileSize'=>$written]);
    }
    manual_json(['error'=>'Ongeldige uploadactie.'],400);
}

if($method!=='POST')manual_json(['error'=>'Methode niet toegestaan.'],405);
if(!$canManage)manual_json(['error'=>'Alleen een beheerder kan handleidingen wijzigen.'],403);
$raw=file_get_contents('php://input');$body=json_decode($raw===false?'':$raw,true);if(!is_array($body))$body=[];
$action=(string)($body['action']??'save-manual');$expected=isset($body['etag'])&&$body['etag']!==''?(string)$body['etag']:null;
$lock=@fopen(MP_MANUAL_LOCK,'c+');if($lock===false||!flock($lock,LOCK_EX))manual_json(['error'=>'Handleidingenlock kon niet worden verkregen.'],500);

try{
    $config=manual_read();$etag=manual_etag();
    if($action==='save-manual'){
        $incoming=isset($body['manual'])&&is_array($body['manual'])?$body['manual']:[];
        $requested=manual_id($incoming['id']??'');$existing=null;$index=-1;
        if($requested!=='')foreach($config['manuals'] as $i=>$m)if($m['id']===$requested){$existing=$m;$index=(int)$i;break;}
        if(!$existing&&count($config['manuals'])>=MP_MANUAL_MAX_ITEMS)throw new RuntimeException('Maximaal '.MP_MANUAL_MAX_ITEMS.' handleidingen toegestaan.');
        $manual=manual_sanitize($incoming,$existing);
        $path=manual_file_path($manual['fileKey']);
        if($path===''||!is_file($path))throw new RuntimeException('Het geüploade PDF-bestand bestaat niet meer. Upload het opnieuw.');
        if($index>=0)$config['manuals'][$index]=$manual;else$config['manuals'][]=$manual;
        $newEtag=manual_write($config,$etag===null?null:$expected);
        if($existing&&!empty($existing['fileKey'])&&$existing['fileKey']!==$manual['fileKey']){
            $old=manual_file_path((string)$existing['fileKey']);if($old&&is_file($old))@unlink($old);
        }
        try{mp_audit_append($user,[['entityType'=>'Handleidingen','entityId'=>$manual['id'],'entityLabel'=>$manual['title'],'action'=>$existing?'bijgewerkt':'toegevoegd','fields'=>[['field'=>'Titel','before'=>$existing['title']??'—','after'=>$manual['title']],['field'=>'PDF','before'=>$existing['fileName']??'—','after'=>$manual['fileName']]]]]);}catch(Throwable $e){}
        flock($lock,LOCK_UN);fclose($lock);
        manual_json(['ok'=>true,'manual'=>$manual,'manuals'=>manual_read()['manuals'],'etag'=>$newEtag],200,['ETag'=>$newEtag]);
    }
    if($action==='delete-manual'){
        $id=manual_id($body['id']??'');$existing=null;
        foreach($config['manuals'] as $m)if($m['id']===$id){$existing=$m;break;}
        if(!$existing){flock($lock,LOCK_UN);fclose($lock);manual_json(['error'=>'Handleiding niet gevonden.'],404);}
        $config['manuals']=array_values(array_filter($config['manuals'],function($m)use($id){return$m['id']!==$id;}));
        $newEtag=manual_write($config,$etag===null?null:$expected);
        $old=manual_file_path((string)$existing['fileKey']);if($old&&is_file($old))@unlink($old);
        try{mp_audit_append($user,[['entityType'=>'Handleidingen','entityId'=>$id,'entityLabel'=>$existing['title'],'action'=>'verwijderd','fields'=>[['field'=>'Titel','before'=>$existing['title'],'after'=>'—']]]]);}catch(Throwable $e){}
        flock($lock,LOCK_UN);fclose($lock);
        manual_json(['ok'=>true,'manuals'=>manual_read()['manuals'],'etag'=>$newEtag],200,['ETag'=>$newEtag]);
    }
    throw new RuntimeException('Onbekende handleidingenactie.');
}catch(Throwable $e){
    if(isset($lock)&&is_resource($lock)){@flock($lock,LOCK_UN);@fclose($lock);}
    if($e->getMessage()==='CONFLICT')manual_json(['error'=>'De handleidingenbibliotheek is intussen op een ander toestel gewijzigd. Vernieuw en probeer opnieuw.','etag'=>manual_etag()],409);
    manual_json(['error'=>$e->getMessage()],400);
}
