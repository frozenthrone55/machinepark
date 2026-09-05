<?php
declare(strict_types=1);

require_once __DIR__ . '/_auth-lib.php';
require_once __DIR__ . '/_audit-lib.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('X-Content-Type-Options: nosniff');

define('MP_WORK_ORDER_FILE', '/volume1/MachineparkData/data/work-order-templates-v1.json');
define('MP_WORK_ORDER_LOCK', '/volume1/MachineparkData/data/work-order-templates-v1.lock');

function work_json(array $body, int $status = 200, array $headers = []): void {
    http_response_code($status);
    foreach ($headers as $name=>$value) header($name . ': ' . $value);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function work_text($value, int $max = 500): string {
    $text = trim((string)$value);
    return function_exists('mb_substr') ? mb_substr($text, 0, $max, 'UTF-8') : substr($text, 0, $max);
}

function work_list($value, int $maxItems = 20): array {
    $items = is_array($value) ? $value : explode(',', (string)$value);
    $out = [];
    foreach ($items as $item) {
        $text = work_text($item, 120);
        if ($text === '' || in_array($text, $out, true)) continue;
        $out[] = $text;
        if (count($out) >= $maxItems) break;
    }
    return $out;
}

function work_id($value): string {
    $id = strtolower(trim((string)$value));
    $id = preg_replace('/[^a-z0-9_-]+/', '-', $id);
    $id = trim((string)$id, '-');
    return substr($id, 0, 80);
}

function work_field(array $field, int $index): ?array {
    $label = work_text($field['label'] ?? '', 120);
    if ($label === '') return null;
    $allowed = ['text','textarea','number','checkbox','select','date'];
    $type = in_array((string)($field['type'] ?? 'text'), $allowed, true) ? (string)$field['type'] : 'text';
    $id = work_id($field['id'] ?? ('veld-' . ($index + 1)));
    if ($id === '') $id = 'veld-' . ($index + 1);
    return [
        'id'=>$id,
        'label'=>$label,
        'type'=>$type,
        'required'=>!empty($field['required']),
        'options'=>$type === 'select' ? work_list($field['options'] ?? [], 40) : [],
    ];
}

function work_sanitize(array $template, ?array $existing = null): array {
    $name = work_text($template['name'] ?? '', 120);
    if ($name === '') throw new RuntimeException('Geef de werkbon een naam.');
    $fields = [];
    foreach (array_slice(isset($template['fields']) && is_array($template['fields']) ? $template['fields'] : [], 0, 60) as $index=>$field) {
        if (!is_array($field)) continue;
        $clean = work_field($field, (int)$index);
        if ($clean) $fields[] = $clean;
    }
    if (!$fields) throw new RuntimeException('Voeg minstens één veld aan de werkbon toe.');
    $id = work_id($template['id'] ?? ($existing['id'] ?? $name));
    if ($id === '') $id = 'wo-' . bin2hex(random_bytes(8));
    $now = date(DATE_ATOM);
    return [
        'id'=>$id,
        'name'=>$name,
        'description'=>work_text($template['description'] ?? '', 500),
        'active'=>array_key_exists('active', $template) ? (bool)$template['active'] : true,
        'brands'=>work_list($template['brands'] ?? [], 20),
        'models'=>work_list($template['models'] ?? [], 30),
        'version'=>$existing ? max(1,(int)($existing['version'] ?? 1))+1 : max(1,(int)($template['version'] ?? 1)),
        'fields'=>$fields,
        'createdAt'=>$existing['createdAt'] ?? ($template['createdAt'] ?? $now),
        'updatedAt'=>$now,
    ];
}

function work_normalize(array $data): array {
    $out = [];
    foreach (array_slice(isset($data['templates']) && is_array($data['templates']) ? $data['templates'] : [], 0, 60) as $item) {
        if (!is_array($item)) continue;
        try {
            $clean = work_sanitize($item, $item);
            $clean['version'] = max(1,(int)($item['version'] ?? 1));
            $clean['createdAt'] = (string)($item['createdAt'] ?? $clean['createdAt']);
            $clean['updatedAt'] = (string)($item['updatedAt'] ?? $clean['updatedAt']);
            $out[] = $clean;
        } catch (Throwable $e) {}
    }
    return ['version'=>1,'templates'=>$out];
}

function work_read(): array {
    if (!is_file(MP_WORK_ORDER_FILE)) return ['version'=>1,'templates'=>[]];
    $raw = @file_get_contents(MP_WORK_ORDER_FILE);
    $data = $raw !== false ? json_decode($raw, true) : null;
    return is_array($data) ? work_normalize($data) : ['version'=>1,'templates'=>[]];
}

function work_etag(): ?string {
    if (!is_file(MP_WORK_ORDER_FILE)) return null;
    $hash = @hash_file('sha256', MP_WORK_ORDER_FILE);
    return $hash ? '"' . $hash . '"' : null;
}

function work_write(array $data, ?string $expected): string {
    $current = work_etag();
    if ($current !== null && ($expected === null || trim($expected) !== $current)) throw new RuntimeException('CONFLICT');
    $json = json_encode(work_normalize($data), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false) throw new RuntimeException('Werkbonnen konden niet naar JSON worden omgezet.');
    $tmp = MP_WORK_ORDER_FILE . '.tmp-' . bin2hex(random_bytes(5));
    if (@file_put_contents($tmp, $json, LOCK_EX) === false) throw new RuntimeException('Werkbonnen konden niet worden geschreven.');
    if (!@rename($tmp, MP_WORK_ORDER_FILE)) { @unlink($tmp); throw new RuntimeException('Werkbonnen konden niet atomair worden opgeslagen.'); }
    return work_etag() ?: '';
}

if (!mp_auth_is_local_ip(mp_auth_client_ip())) work_json(['error'=>'Lokale werkbonnen zijn voorlopig alleen via het lokale netwerk bereikbaar.'],403);
try { $user = mp_auth_require_user(); } catch (Throwable $e) { work_json(['error'=>'Niet aangemeld.'],401); }
$permissions = mp_role_permissions((string)($user['role'] ?? 'gebruiker'), !empty($user['isOwner']));
$canRead = !empty($permissions['view.maintenance']) || !empty($permissions['maintenance.add']) || !empty($permissions['maintenance.edit']);
$canManage = !empty($user['isOwner']) || (string)($user['role'] ?? '') === 'beheerder';
if (!$canRead && !$canManage) work_json(['error'=>'Deze rol heeft geen toegang tot werkbonnen.'],403);

$method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));
$config = work_read();
$etag = work_etag();

if ($method === 'GET') work_json(['templates'=>$config['templates'],'etag'=>$etag,'canManage'=>$canManage,'mode'=>'synology-local'],200,$etag?['ETag'=>$etag]:[]);
if ($method !== 'POST') work_json(['error'=>'Methode niet toegestaan.'],405);
if (!$canManage) work_json(['error'=>'Alleen een beheerder kan werkbonnen configureren.'],403);

$raw=file_get_contents('php://input'); $body=json_decode($raw===false?'':$raw,true); if(!is_array($body))$body=[];
$action=(string)($body['action']??'save-template'); $expected=isset($body['etag'])&&$body['etag']!==''?(string)$body['etag']:null;
$lock=@fopen(MP_WORK_ORDER_LOCK,'c+'); if($lock===false||!flock($lock,LOCK_EX))work_json(['error'=>'Werkbonlock kon niet worden verkregen.'],500);

try {
    $config=work_read(); $etag=work_etag();
    if($action==='save-template'){
        $incoming=isset($body['template'])&&is_array($body['template'])?$body['template']:[];
        $requested=work_id($incoming['id']??($incoming['name']??''));
        $existing=null;$index=-1;
        foreach($config['templates'] as $i=>$item){if($item['id']===$requested){$existing=$item;$index=(int)$i;break;}}
        if(!$existing&&count($config['templates'])>=60)throw new RuntimeException('Maximaal 60 werkbontemplates toegestaan.');
        $template=work_sanitize(array_merge($incoming,['id'=>$requested]),$existing);
        if($index>=0)$config['templates'][$index]=$template;else$config['templates'][]=$template;
        $newEtag=work_write($config,$etag===null?null:$expected);
        try{mp_audit_append($user,[['entityType'=>'Werkbonnen','entityId'=>$template['id'],'entityLabel'=>$template['name'],'action'=>$existing?'aangepast':'toegevoegd','fields'=>[['field'=>'Werkbon','before'=>$existing['name']??'—','after'=>$template['name']],['field'=>'Velden','before'=>$existing?(string)count($existing['fields']):'0','after'=>(string)count($template['fields'])]]]]);}catch(Throwable $e){}
        flock($lock,LOCK_UN);fclose($lock);
        work_json(['ok'=>true,'templates'=>work_read()['templates'],'etag'=>$newEtag],200,['ETag'=>$newEtag]);
    }
    if($action==='delete-template'){
        $id=work_id($body['templateId']??'');$existing=null;
        foreach($config['templates'] as $item)if($item['id']===$id){$existing=$item;break;}
        if(!$existing){flock($lock,LOCK_UN);fclose($lock);work_json(['error'=>'Werkbon niet gevonden.'],404);}
        $config['templates']=array_values(array_filter($config['templates'],function($x)use($id){return$x['id']!==$id;}));
        $newEtag=work_write($config,$etag===null?null:$expected);
        try{mp_audit_append($user,[['entityType'=>'Werkbonnen','entityId'=>$id,'entityLabel'=>$existing['name'],'action'=>'verwijderd','fields'=>[['field'=>'Werkbon','before'=>$existing['name'],'after'=>'—']]]]);}catch(Throwable $e){}
        flock($lock,LOCK_UN);fclose($lock);
        work_json(['ok'=>true,'templates'=>work_read()['templates'],'etag'=>$newEtag],200,['ETag'=>$newEtag]);
    }
    throw new RuntimeException('Onbekende werkbonactie.');
} catch(Throwable $e){
    if(isset($lock)&&is_resource($lock)){@flock($lock,LOCK_UN);@fclose($lock);}
    if($e->getMessage()==='CONFLICT')work_json(['error'=>'De werkbonnen zijn intussen door iemand anders gewijzigd. Vernieuw en probeer opnieuw.','etag'=>work_etag()],409);
    work_json(['error'=>$e->getMessage()],400);
}
