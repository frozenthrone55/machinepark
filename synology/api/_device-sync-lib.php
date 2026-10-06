<?php
declare(strict_types=1);
if (!defined('MP_DATA_LIBRARY_ONLY')) define('MP_DATA_LIBRARY_ONLY', true);
require_once __DIR__ . '/machinepark-data.php';

function mp_sync_node_path(): string {
    foreach (['/var/packages/Node.js_v22/target/usr/local/bin/node','/var/packages/Node.js_v20/target/usr/local/bin/node','/var/packages/Node.js_v18/target/usr/local/bin/node','/var/packages/Node.js_v16/target/usr/local/bin/node','/usr/local/bin/node','/usr/bin/node'] as $path) if (is_executable($path)) return $path;
    return '';
}
function mp_sync_local(array $c): bool { return ($c['source_mode'] ?? '') === 'local'; }
function mp_sync_local_bytes(array $c): string {
    $path = $c['local_path'] ?? '';
    if (!is_file($path) || !is_readable($path)) throw new RuntimeException('De lokale Excelkopie is niet leesbaar op de NAS.');
    if (strtolower(pathinfo($path, PATHINFO_EXTENSION)) !== 'xlsx') throw new RuntimeException('De lokale bron moet een .xlsx-bestand zijn.');
    $handle = fopen($path, 'rb');
    if (!$handle) throw new RuntimeException('De lokale Excelkopie kon niet worden geopend.');
    try { $bytes = stream_get_contents($handle, 32*1024*1024+1); }
    finally { fclose($handle); }
    if ($bytes === false || strlen($bytes) > 32*1024*1024 || strlen($bytes) === 0) throw new RuntimeException('De lokale Excelkopie is leeg of te groot.');
    return $bytes;
}
function mp_sync_config(): array {
    $path = defined('MP_SYNC_CONFIG_FILE') ? MP_SYNC_CONFIG_FILE : '/volume1/MachineparkData/config/sharepoint-sync.php';
    if (!is_file($path)) return ['source_mode'=>'local','local_path'=>'/volume1/MachineparkData/toestelsynchronisatie/koffiemachines inventaris 2025.xlsx','node_path'=>mp_sync_node_path()];
    $config = require $path;
    return is_array($config) ? $config : [];
}
function mp_sync_setup(array $c): string {
    if (mp_sync_local($c)) {
        if (empty($c['local_path']) || !is_readable($c['local_path'])) return 'Plaats de Excelkopie in de map toestelsynchronisatie op de NAS.';
    } else {
        foreach (['tenant_id','client_id','client_secret','drive_id','item_id'] as $key) if (empty($c[$key])) return 'Microsoft-koppeling moet nog worden ingesteld.';
        if (!function_exists('curl_init')) return 'PHP-extensie curl is vereist voor Microsoft.';
    }
    if (empty($c['node_path']) || !is_executable($c['node_path']) || !function_exists('proc_open')) return 'Installeer Node.js (16 of hoger) op de NAS; proc_open moet beschikbaar zijn.';
    if (!class_exists('ZipArchive') || !class_exists('DOMDocument')) return 'PHP-extensies zip en dom zijn vereist.';
    return '';
}
function mp_sync_locked(callable $fn) {
    mp_ensure_storage();
    $lock = fopen(MP_LOCK_FILE, 'c+');
    if (!$lock || !flock($lock, LOCK_EX)) throw new RuntimeException('Datalock niet beschikbaar.');
    try { return $fn(); } finally { flock($lock, LOCK_UN); fclose($lock); }
}
function mp_sync_state(): array {
    $state = mp_read_state();
    if (!mp_valid_snapshot($state)) throw new RuntimeException('Machinepark is nog niet geïnitialiseerd.');
    return $state;
}
function mp_sync_http(string $url, array $headers = [], ?string $post = null): string {
    $parts = parse_url($url);
    $host = strtolower((string)($parts['host'] ?? ''));
    if (($parts['scheme'] ?? '') !== 'https' || isset($parts['user']) || isset($parts['pass']) || !($host === 'login.microsoftonline.com' || $host === 'graph.microsoft.com' || preg_match('/(^|\.)sharepoint\.com$/', $host))) throw new RuntimeException('Onverwachte downloadhost.');
    $ch = curl_init($url); $size = 0; $body = '';
    curl_setopt_array($ch, [CURLOPT_FOLLOWLOCATION=>false, CURLOPT_CONNECTTIMEOUT=>15, CURLOPT_TIMEOUT=>90, CURLOPT_HTTPHEADER=>$headers, CURLOPT_SSL_VERIFYPEER=>true, CURLOPT_SSL_VERIFYHOST=>2, CURLOPT_WRITEFUNCTION=>function ($ch, $data) use (&$size, &$body) { $size += strlen($data); if ($size > 32*1024*1024) return 0; $body .= $data; return strlen($data); }]);
    if ($post !== null) { curl_setopt($ch, CURLOPT_POST, true); curl_setopt($ch, CURLOPT_POSTFIELDS, $post); }
    $ok = curl_exec($ch); $status = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
    if ($ok === false || $status < 200 || $status >= 300) throw new RuntimeException('Microsoft-aanvraag mislukt (HTTP ' . $status . '). Controleer toegang, sleutel en bestands-ID.');
    return $body;
}
function mp_sync_metadata(array $c, string $token): array {
    $url = 'https://graph.microsoft.com/v1.0/drives/' . rawurlencode($c['drive_id']) . '/items/' . rawurlencode($c['item_id']);
    $data = json_decode(mp_sync_http($url, ['Authorization: Bearer '.$token]), true);
    if (!is_array($data) || empty($data['eTag']) || empty($data['file']) || empty($data['name'])) throw new RuntimeException('Geen geldig SharePointbestand gevonden.');
    if (strtolower(pathinfo($data['name'], PATHINFO_EXTENSION)) !== 'xlsx') throw new RuntimeException('De bron moet hetzelfde .xlsx-bestand zijn als bij de handmatige synchronisatie.');
    return $data;
}
function mp_sync_xml(string $raw): DOMDocument {
    if (stripos($raw, '<!DOCTYPE') !== false || stripos($raw, '<!ENTITY') !== false) throw new RuntimeException('Ongeldige Excel-XML.');
    $doc = new DOMDocument(); $previous = libxml_use_internal_errors(true);
    try { if (!$doc->loadXML($raw, LIBXML_NONET)) throw new RuntimeException('Excel-XML kon niet worden gelezen.'); }
    finally { libxml_clear_errors(); libxml_use_internal_errors($previous); }
    return $doc;
}
function mp_sync_matrix(string $bytes): array {
    $tmp = tempnam(MP_DATA_DIR, '.xlsx-sync-');
    if ($tmp === false) throw new RuntimeException('Tijdelijk bestand niet beschikbaar.');
    $zip = new ZipArchive(); $opened = false;
    try {
        if (file_put_contents($tmp, $bytes) !== strlen($bytes) || $zip->open($tmp) !== true) throw new RuntimeException('Geen geldig Excelbestand ontvangen.');
        $opened = true;
        $files = []; $total = 0;
        for ($i=0; $i<$zip->numFiles; $i++) { $entry=$zip->statIndex($i); $total+=(int)$entry['size']; if ($total>64*1024*1024 || $zip->numFiles>10000) throw new RuntimeException('Excelbestand is te groot.'); $files[]=$entry['name']; }
        $shared = [];
        $raw = $zip->getFromName('xl/sharedStrings.xml');
        if ($raw !== false) foreach (mp_sync_xml($raw)->getElementsByTagName('si') as $si) { $text=''; foreach ($si->getElementsByTagName('t') as $t) $text.=$t->textContent; $shared[]=$text; }
        $redStyles=[]; $raw=$zip->getFromName('xl/styles.xml');
        if ($raw !== false) {
            $doc=mp_sync_xml($raw); $redFills=[];
            foreach ($doc->getElementsByTagName('fill') as $i=>$fill) foreach (['fgColor','bgColor'] as $tag) foreach ($fill->getElementsByTagName($tag) as $color) {
                $rgb=substr(ltrim($color->getAttribute('rgb'),'#'),-6);
                if (!preg_match('/^[0-9a-f]{6}$/i',$rgb)) continue;
                $r=hexdec(substr($rgb,0,2));$g=hexdec(substr($rgb,2,2));$b=hexdec(substr($rgb,4,2));
                if ($r>=185 && $g<=155 && $b<=155 && $r>=$g+45 && $r>=$b+45) $redFills[$i]=true;
            }
            $xfs=$doc->getElementsByTagName('cellXfs')->item(0); $i=0;
            if ($xfs) foreach ($xfs->childNodes as $xf) if ($xf instanceof DOMElement) { if (isset($redFills[(int)$xf->getAttribute('fillId')])) $redStyles[$i]=true; $i++; }
        }
        $sheets=array_values(array_filter($files,function($f){return preg_match('#^xl/worksheets/sheet\d+\.xml$#i',$f);})); natsort($sheets);
        if (!$sheets) throw new RuntimeException('Geen Excelwerkblad gevonden.');
        $rows=[];$redRows=[];
        foreach (mp_sync_xml($zip->getFromName(reset($sheets)))->getElementsByTagName('row') as $row) {
            $arr=[];$red=false;
            foreach ($row->getElementsByTagName('c') as $cell) {
                preg_match('/^([A-Z]+)/i',$cell->getAttribute('r'),$m); if (!$m) throw new RuntimeException('Ongeldige Excelcel.');
                $col=0;foreach(str_split(strtoupper($m[1])) as $letter)$col=$col*26+ord($letter)-64; $col--;
                if ($col>16383) throw new RuntimeException('Ongeldige Excelkolom.');
                if(isset($redStyles[(int)$cell->getAttribute('s')]))$red=true;
                $type=$cell->getAttribute('t');$value='';
                if($type==='inlineStr'){foreach($cell->getElementsByTagName('t') as $t)$value.=$t->textContent;}
                else{$v=$cell->getElementsByTagName('v')->item(0);$raw=$v?$v->textContent:'';$value=$type==='s'?($shared[(int)$raw]??''):($type==='b'?($raw==='1'?'TRUE':'FALSE'):$raw);}
                while(count($arr)<=$col)$arr[]='';$arr[$col]=$value;
            }
            if($red)$redRows[]=count($rows);$rows[]=$arr;
        }
        return ['matrix'=>$rows,'redRows'=>$redRows];
    } finally { if ($opened) $zip->close(); @unlink($tmp); }
}
function mp_sync_worker(array $config, array $input): array {
    $cmd = escapeshellarg($config['node_path']).' '.escapeshellarg(dirname(__DIR__).'/device-sync-worker.cjs');
    $inputFile=tempnam(MP_DATA_DIR,'.sync-input-');$outFile=tempnam(MP_DATA_DIR,'.sync-output-');$errFile=tempnam(MP_DATA_DIR,'.sync-error-');
    if(!$inputFile || !$outFile || !$errFile)throw new RuntimeException('Tijdelijke verwerkerbestanden niet beschikbaar.');
    try {
        $json=json_encode($input,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
        if($json===false || file_put_contents($inputFile,$json)!==strlen($json))throw new RuntimeException('Synchronisatie-invoer kon niet worden opgeslagen.');
        $pipes=[];$process=proc_open($cmd,[0=>['file',$inputFile,'r'],1=>['file',$outFile,'w'],2=>['file',$errFile,'w']],$pipes);
        if(!is_resource($process))throw new RuntimeException('Synchronisatieverwerker kon niet starten.');
        $deadline=microtime(true)+60;
        do {
            $status=proc_get_status($process);
            if(!$status['running'])break;
            if(microtime(true)>$deadline){proc_terminate($process);proc_close($process);throw new RuntimeException('Synchronisatieverwerker duurde langer dan 60 seconden.');}
            usleep(100000);
        } while(true);
        $exit=$status['exitcode'];proc_close($process);
        $result=json_decode(file_get_contents($outFile),true);$err=file_get_contents($errFile);
        if($exit!==0 || !is_array($result) || !isset($result['devices'],$result['changes']))throw new RuntimeException('Synchronisatie geweigerd: '.substr(trim($err),0,500));
    } finally {@unlink($inputFile);@unlink($outFile);@unlink($errFile);}

    return $result;
}
function mp_sync_save_run(array $state, array $run): void {
    $sync=$state['deviceSync']??[];
    $sync['lastRun']=$run; $sync['lastCheckAt']=$run['at'];
    if($run['status']==='success')$sync['lastSuccessAt']=$run['at'];
    $sync['history'][]=$run;
    // Full history is kept in the server-owned snapshot and its backups.
    $state['deviceSync']=$sync;
    $state['updatedAt']=date(DATE_ATOM);
    mp_backup_current();mp_write_state($state);
}
function mp_sync_run(bool $manual=false): array {
    mp_ensure_storage();
    $lock=fopen(MP_DATA_DIR.'/sharepoint-sync.lock','c+');
    if(!$lock || !flock($lock,LOCK_EX|LOCK_NB))throw new RuntimeException('Een synchronisatie is al bezig.');
    try {
        $state=mp_sync_locked(function(){return mp_sync_state();});$sync=$state['deviceSync']??[];
        if(!$manual && empty($sync['enabled']))return ['status'=>'disabled'];
        if(!$manual && !empty($sync['lastCheckAt']) && time()-strtotime($sync['lastCheckAt'])<14*60)return ['status'=>'not_due'];
        $at=date(DATE_ATOM);$config=mp_sync_config();$setup=mp_sync_setup($config);
        $run=['id'=>bin2hex(random_bytes(12)),'at'=>$at,'status'=>'error','message'=>'','changes'=>[],'source'=>mp_sync_local($config)?'Lokale OneDrive-kopie':'SharePoint','trigger'=>$manual?'manual':'scheduled'];
        try {
            if($setup!=='')throw new RuntimeException($setup);
            if (mp_sync_local($config)) {
                $bytes=mp_sync_local_bytes($config);
                $hash=hash('sha256',$bytes);$version='local/'.$config['local_path'].'/'.$hash;
                $meta=['name'=>basename($config['local_path']),'eTag'=>$hash,'lastModifiedDateTime'=>date(DATE_ATOM,filemtime($config['local_path']))];
            } else {
            $tokenData=json_decode(mp_sync_http('https://login.microsoftonline.com/'.rawurlencode($config['tenant_id']).'/oauth2/v2.0/token',['Content-Type: application/x-www-form-urlencoded'],http_build_query(['client_id'=>$config['client_id'],'client_secret'=>$config['client_secret'],'scope'=>'https://graph.microsoft.com/.default','grant_type'=>'client_credentials'])),true);
            if(empty($tokenData['access_token']))throw new RuntimeException('Microsoft gaf geen toegangstoken terug.');
            $token=$tokenData['access_token'];$meta=mp_sync_metadata($config,$token);
            $version=$config['drive_id'].'/'.$config['item_id'].'/'.$meta['eTag'];
            }
            $run['version']=$meta['eTag'];$run['fileName']=$meta['name'];$run['fileModifiedAt']=$meta['lastModifiedDateTime']??'';
            if(($sync['appliedVersion']??'')===$version){
                return mp_sync_locked(function()use($at,$meta){$state=mp_sync_state();$state['deviceSync']['lastCheckAt']=$at;$state['deviceSync']['lastCheckStatus']='unchanged';$state['deviceSync']['fileModifiedAt']=$meta['lastModifiedDateTime']??'';mp_write_state($state);return ['status'=>'unchanged','message'=>'Bestand ongewijzigd.'];});
            }
            if (mp_sync_local($config)) {
                $matrix=mp_sync_matrix($bytes);
                if (hash('sha256',mp_sync_local_bytes($config)) !== $hash) throw new RuntimeException('De Excelkopie veranderde tijdens het lezen. Volgende controle probeert opnieuw.');
            } else {
            $download=$meta['@microsoft.graph.downloadUrl']??'';if(!$download)throw new RuntimeException('Geen downloadadres beschikbaar.');
            // No authorization header is sent to the preauthenticated download URL.
            $matrix=mp_sync_matrix(mp_sync_http($download));
            $after=mp_sync_metadata($config,$token);if($after['eTag']!==$meta['eTag'])throw new RuntimeException('Het Excelbestand veranderde tijdens het lezen. Volgende controle probeert opnieuw.');
            }
            return mp_sync_locked(function()use($config,$matrix,$run,$version,$meta,$at,$manual){
                $state=mp_sync_state();if(!$manual && empty($state['deviceSync']['enabled']))return ['status'=>'disabled'];date_default_timezone_set('Europe/Brussels');
                $result=mp_sync_worker($config,array_merge($matrix,['devices'=>$state['devices'],'fileName'=>$meta['name'],'syncMoment'=>date('Y-m-d\TH:i'),'loggedAt'=>$at]));
                $map=[];foreach($result['devices'] as $d)$map[$d['id']]=$d;
                foreach($state['devices'] as &$d){if(isset($map[$d['id']])){$d=$map[$d['id']];unset($map[$d['id']]);}}unset($d);
                foreach($map as $d)$state['devices'][]=$d;
                $state['deviceSync']['appliedVersion']=$version;$state['deviceSync']['lastCheckStatus']='success';$state['deviceSync']['fileModifiedAt']=$meta['lastModifiedDateTime']??'';
                unset($result['devices']);$run=array_merge($run,$result,['status'=>'success','message'=>$result['added'].' nieuw · '.$result['updated'].' bijgewerkt']);
                mp_sync_save_run($state,$run);return $run;
            });
        } catch(Throwable $e) {
            $run['message']=$e->getMessage();
            mp_sync_locked(function()use($run){$state=mp_sync_state();$state['deviceSync']['lastCheckStatus']='error';mp_sync_save_run($state,$run);});
            return $run;
        }
    } finally {flock($lock,LOCK_UN);fclose($lock);}
}
