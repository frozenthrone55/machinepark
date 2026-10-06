<?php
declare(strict_types=1);
require_once __DIR__ . '/_device-sync-lib.php';
try {
    mp_auth_require_request_access();
    $user=mp_auth_require_user();
    if (empty($user['isOwner']) && ($user['role']??'')!=='beheerder') mp_json(['error'=>'Alleen beheerders hebben toegang.'],403);
    $method=strtoupper($_SERVER['REQUEST_METHOD']??'GET');
    if($method==='GET'){
        $state=mp_sync_locked(function(){return mp_sync_state();});
        $sync=$state['deviceSync']??[];$history=array_reverse($sync['history']??[]);unset($sync['history']);
        $offset=max(0,(int)($_GET['offset']??0));$page=array_slice($history,$offset,25);
        $setup=mp_sync_setup(mp_sync_config());
        mp_json(['ready'=>$setup==='','setupMessage'=>$setup,'sync'=>$sync,'history'=>$page,'nextOffset'=>count($history)>$offset+25?$offset+25:null]);
    }
    if($method==='POST'){
        // JSON-only mutation plus same-origin check protects the session endpoint.
        if(stripos($_SERVER['CONTENT_TYPE']??'','application/json')!==0)mp_json(['error'=>'JSON vereist.'],415);
        $origin=$_SERVER['HTTP_ORIGIN']??'';
        if($origin!=='' && (parse_url($origin,PHP_URL_HOST)!==preg_replace('/:\d+$/','',$_SERVER['HTTP_HOST']??'') || parse_url($origin,PHP_URL_SCHEME)!==(mp_auth_request_is_https()?'https':'http')))mp_json(['error'=>'Ongeldige aanvraagbron.'],403);
        $body=json_decode(file_get_contents('php://input'),true);
        if(($body['action']??'')==='enable'){
            if(!is_bool($body['enabled']??null))mp_json(['error'=>'Ongeldige instelling.'],400);
            if($body['enabled'] && mp_sync_setup(mp_sync_config())!=='')mp_json(['error'=>'Stel eerst de Microsoft-koppeling en NAS-verwerker in.'],409);
            mp_sync_locked(function()use($body){$state=mp_sync_state();$state['deviceSync']['enabled']=$body['enabled'];mp_backup_current();mp_write_state($state);});
            mp_json(['ok'=>true]);
        }
        if(($body['action']??'')==='run'){
            $result=mp_sync_run(true);mp_json(['ok'=>$result['status']!=='error','result'=>$result,'error'=>$result['status']==='error'?$result['message']:null],$result['status']==='error'?502:200);
        }
        mp_json(['error'=>'Onbekende actie.'],400);
    }
    mp_json(['error'=>'Methode niet toegestaan.'],405,['Allow'=>'GET, POST']);
} catch(Throwable $e){mp_json(['error'=>$e->getMessage()],400);}
