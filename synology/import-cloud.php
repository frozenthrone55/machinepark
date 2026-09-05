<?php
declare(strict_types=1);

require_once __DIR__ . '/api/_auth-lib.php';
require_once __DIR__ . '/api/_role-lib.php';
require_once __DIR__ . '/api/_audit-lib.php';

@ini_set('memory_limit', '384M');

define('MP_CLOUD_UPLOAD_ROOT', '/volume1/MachineparkData/uploads');
define('MP_CLOUD_DATA_DIR', '/volume1/MachineparkData/data');
define('MP_CLOUD_MANUAL_DIR', '/volume1/MachineparkData/manuals');
define('MP_CLOUD_BACKUP_DIR', '/volume1/MachineparkData/backups');
define('MP_CLOUD_MAX_BYTES', 150 * 1024 * 1024);
define('MP_CLOUD_CHUNK_MAX', 2 * 1024 * 1024);

function cloud_json(array $body, int $status = 200): void {
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
    header('X-Content-Type-Options: nosniff');
    http_response_code($status);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function cloud_h($value): string {
    return htmlspecialchars((string)$value, ENT_QUOTES, 'UTF-8');
}

function cloud_safe_id($value): string {
    $id = preg_replace('/[^A-Za-z0-9_-]/', '', (string)$value);
    return substr((string)$id, 0, 80);
}

function cloud_ensure_dir(string $dir): void {
    if (!is_dir($dir) && !@mkdir($dir, 0770, true) && !is_dir($dir)) {
        throw new RuntimeException('Map kon niet worden aangemaakt: ' . $dir);
    }
    if (!is_writable($dir)) throw new RuntimeException('Map is niet schrijfbaar: ' . $dir);
}

function cloud_atomic_json(string $path, array $data): void {
    $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false) throw new RuntimeException('JSON kon niet worden opgebouwd.');
    $tmp = $path . '.tmp-' . bin2hex(random_bytes(5));
    if (@file_put_contents($tmp, $json, LOCK_EX) === false) throw new RuntimeException('Tijdelijk bestand kon niet worden geschreven.');
    if (!@rename($tmp, $path)) {
        @unlink($tmp);
        throw new RuntimeException('Bestand kon niet atomair worden opgeslagen.');
    }
}

function cloud_copy_file_if_exists(string $source, string $dest): void {
    if (!is_file($source)) return;
    cloud_ensure_dir(dirname($dest));
    if (!@copy($source, $dest)) throw new RuntimeException('Back-up kon niet worden gemaakt van ' . basename($source));
}

function cloud_copy_dir(string $source, string $dest): void {
    if (!is_dir($source)) return;
    cloud_ensure_dir($dest);
    foreach ((array)scandir($source) as $name) {
        if ($name === '.' || $name === '..') continue;
        $src = $source . '/' . $name;
        $dst = $dest . '/' . $name;
        if (is_dir($src)) cloud_copy_dir($src, $dst);
        elseif (is_file($src) && !@copy($src, $dst)) throw new RuntimeException('Back-up van mapbestand mislukt: ' . $name);
    }
}

function cloud_remove_dir(string $dir): void {
    if (!is_dir($dir)) return;
    foreach ((array)scandir($dir) as $name) {
        if ($name === '.' || $name === '..') continue;
        $path = $dir . '/' . $name;
        if (is_dir($path)) cloud_remove_dir($path);
        else @unlink($path);
    }
    @rmdir($dir);
}

function cloud_session_path(string $id): string {
    return MP_CLOUD_UPLOAD_ROOT . '/cloud-import-' . $id;
}

function cloud_manifest_path(string $id): string {
    return cloud_session_path($id) . '/manifest.json';
}

function cloud_package_path(string $id): string {
    return cloud_session_path($id) . '/package.json';
}

function cloud_read_manifest(string $id, array $user): array {
    $id = cloud_safe_id($id);
    if ($id === '') throw new RuntimeException('Ongeldige importsessie.');
    $path = cloud_manifest_path($id);
    if (!is_file($path)) throw new RuntimeException('Importsessie niet gevonden.');
    $raw = @file_get_contents($path);
    $data = $raw !== false ? json_decode($raw, true) : null;
    if (!is_array($data)) throw new RuntimeException('Importsessie is beschadigd.');
    if ((string)($data['userId'] ?? '') !== (string)($user['id'] ?? '')) throw new RuntimeException('Deze importsessie hoort bij een andere gebruiker.');
    return $data;
}

function cloud_load_package(string $path): array {
    if (!is_file($path)) throw new RuntimeException('Exportpakket niet gevonden.');
    $size = filesize($path);
    if ($size === false || $size < 10 || $size > MP_CLOUD_MAX_BYTES) throw new RuntimeException('Exportpakket heeft een ongeldige grootte.');
    $raw = @file_get_contents($path);
    if ($raw === false) throw new RuntimeException('Exportpakket kon niet worden gelezen.');
    $data = json_decode($raw, true);
    if (!is_array($data)) throw new RuntimeException('Exportpakket bevat ongeldige JSON.');
    if (($data['app'] ?? '') !== 'Machinepark' || (int)($data['schema'] ?? 0) !== 1 || ($data['exportKind'] ?? '') !== 'synology-cloud-config-v1') {
        throw new RuntimeException('Dit is geen geldig Machinepark Synology-cloudexportpakket.');
    }
    foreach (['roles','faults','workOrders','manuals','users','audit'] as $key) {
        if (!isset($data[$key]) || !is_array($data[$key])) throw new RuntimeException('Cloudexport mist onderdeel: ' . $key);
    }
    return $data;
}

function cloud_counts(array $pkg): array {
    return [
        'roles' => count((array)($pkg['roles']['roles'] ?? [])),
        'faults' => count((array)($pkg['faults']['faults'] ?? [])),
        'workOrders' => count((array)($pkg['workOrders']['templates'] ?? [])),
        'manuals' => count((array)($pkg['manuals']['items'] ?? [])),
        'users' => count((array)($pkg['users']['users'] ?? [])),
        'auditEntries' => count((array)($pkg['audit']['entries'] ?? [])),
    ];
}

function cloud_prepare_manuals(array $pkg, string $sessionDir): array {
    $items = isset($pkg['manuals']['items']) && is_array($pkg['manuals']['items']) ? $pkg['manuals']['items'] : [];
    $files = isset($pkg['manuals']['files']) && is_array($pkg['manuals']['files']) ? $pkg['manuals']['files'] : [];
    $stageDir = $sessionDir . '/manual-stage';
    cloud_remove_dir($stageDir);
    cloud_ensure_dir($stageDir);

    $out = [];
    $totalBytes = 0;
    foreach ($items as $item) {
        if (!is_array($item)) continue;
        $oldKey = trim((string)($item['fileKey'] ?? ''));
        if ($oldKey === '' || !isset($files[$oldKey]) || !is_array($files[$oldKey])) {
            throw new RuntimeException('PDF ontbreekt voor handleiding: ' . (string)($item['title'] ?? $oldKey));
        }
        $file = $files[$oldKey];
        $base64 = preg_replace('/\s+/', '', (string)($file['base64'] ?? ''));
        $bytes = base64_decode($base64, true);
        if ($bytes === false || strlen($bytes) < 5 || substr($bytes, 0, 5) !== '%PDF-') {
            throw new RuntimeException('Ongeldige PDF voor handleiding: ' . (string)($item['title'] ?? $oldKey));
        }
        if (strlen($bytes) > 12 * 1024 * 1024) throw new RuntimeException('Een handleiding-PDF is groter dan 12 MB.');
        $totalBytes += strlen($bytes);
        if ($totalBytes > 120 * 1024 * 1024) throw new RuntimeException('Alle handleidingen samen zijn te groot voor één import.');

        $basename = bin2hex(random_bytes(16)) . '.pdf';
        $stage = $stageDir . '/' . $basename;
        if (@file_put_contents($stage, $bytes, LOCK_EX) === false) throw new RuntimeException('Handleiding-PDF kon niet worden klaargezet.');

        $next = $item;
        $next['fileKey'] = 'manual-files/' . $basename;
        $next['fileName'] = trim((string)($file['fileName'] ?? ($item['fileName'] ?? 'handleiding.pdf')));
        $next['fileSize'] = strlen($bytes);
        $out[] = $next;
    }
    return ['items'=>$out,'stageDir'=>$stageDir,'totalBytes'=>$totalBytes];
}

function cloud_import_roles(array $pkg): int {
    $roles = isset($pkg['roles']['roles']) && is_array($pkg['roles']['roles']) ? $pkg['roles']['roles'] : [];
    $config = mp_role_normalize(['version'=>1,'roles'=>$roles]);
    cloud_atomic_json(MP_ROLE_FILE, $config);
    return count($config['roles']);
}

function cloud_import_faults(array $pkg): int {
    $faults = isset($pkg['faults']['faults']) && is_array($pkg['faults']['faults']) ? array_slice($pkg['faults']['faults'],0,5000) : [];
    $valid = [];
    foreach ($faults as $fault) {
        if (!is_array($fault) || trim((string)($fault['name'] ?? '')) === '') continue;
        $valid[] = $fault;
    }
    cloud_atomic_json(MP_CLOUD_DATA_DIR . '/fault-library-v1.json', ['version'=>1,'faults'=>$valid]);
    return count($valid);
}

function cloud_import_work_orders(array $pkg): int {
    $templates = isset($pkg['workOrders']['templates']) && is_array($pkg['workOrders']['templates']) ? array_slice($pkg['workOrders']['templates'],0,60) : [];
    $valid = [];
    foreach ($templates as $template) {
        if (!is_array($template) || trim((string)($template['name'] ?? '')) === '') continue;
        $valid[] = $template;
    }
    cloud_atomic_json(MP_CLOUD_DATA_DIR . '/work-order-templates-v1.json', ['version'=>1,'templates'=>$valid]);
    return count($valid);
}

function cloud_import_manuals(array $prepared): int {
    cloud_ensure_dir(MP_CLOUD_MANUAL_DIR);
    $newFiles = [];
    foreach ((array)$prepared['items'] as $item) {
        $basename = basename((string)($item['fileKey'] ?? ''));
        $source = $prepared['stageDir'] . '/' . $basename;
        $dest = MP_CLOUD_MANUAL_DIR . '/' . $basename;
        if (!is_file($source) || !@rename($source, $dest)) {
            foreach ($newFiles as $file) @unlink($file);
            throw new RuntimeException('Een handleiding-PDF kon niet naar de definitieve map worden verplaatst.');
        }
        $newFiles[] = $dest;
    }
    try {
        cloud_atomic_json(MP_CLOUD_DATA_DIR . '/manual-library-v1.json', ['version'=>1,'manuals'=>array_values($prepared['items'])]);
    } catch (Throwable $e) {
        foreach ($newFiles as $file) @unlink($file);
        throw $e;
    }
    return count((array)$prepared['items']);
}

function cloud_import_audit(array $pkg): int {
    mp_audit_ensure_dir();
    $entries = isset($pkg['audit']['entries']) && is_array($pkg['audit']['entries']) ? array_slice($pkg['audit']['entries'],0,500) : [];
    $written = 0;
    foreach ($entries as $entry) {
        if (!is_array($entry)) continue;
        $clean = $entry;
        $safeChanges = [];
        foreach ((array)($clean['changes'] ?? []) as $change) {
            if (!is_array($change)) continue;
            unset($change['undo']);
            $change['reversible'] = false;
            $change['undone'] = false;
            $change['linkedUndoCount'] = 0;
            $safeChanges[] = $change;
        }
        $clean['changes'] = $safeChanges;
        $clean['reversibleSchema'] = 0;
        $clean['importedFromCloud'] = true;
        $clean['importedAt'] = date(DATE_ATOM);
        $id = preg_replace('/[^A-Za-z0-9_-]/','_', (string)($clean['id'] ?? bin2hex(random_bytes(8))));
        $stamp = preg_replace('/[^0-9]/','', (string)($clean['at'] ?? ''));
        $stamp = substr($stamp ?: date('YmdHis'),0,14);
        $path = MP_AUDIT_DIR . '/cloud-' . $stamp . '-' . substr($id,0,80) . '-' . bin2hex(random_bytes(3)) . '.json';
        $json = json_encode($clean, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        if ($json !== false && @file_put_contents($path,$json,LOCK_EX) !== false) $written++;
    }
    return $written;
}

function cloud_import_users_reference(array $pkg): array {
    $cloudUsers = isset($pkg['users']['users']) && is_array($pkg['users']['users']) ? array_slice($pkg['users']['users'],0,200) : [];
    $invitations = isset($pkg['users']['invitations']) && is_array($pkg['users']['invitations']) ? array_slice($pkg['users']['invitations'],0,200) : [];
    cloud_atomic_json(MP_CLOUD_DATA_DIR . '/cloud-users-v1.json', [
        'version'=>1,
        'importedAt'=>date(DATE_ATOM),
        'users'=>$cloudUsers,
        'invitations'=>$invitations,
    ]);

    $local = mp_auth_read_users();
    $byEmail = [];
    foreach ($cloudUsers as $user) {
        if (!is_array($user)) continue;
        $email = strtolower(trim((string)($user['email'] ?? '')));
        if ($email !== '') $byEmail[$email] = $user;
    }
    $updated = 0;
    $matched = 0;
    foreach ($local as &$localUser) {
        $email = strtolower(trim((string)($localUser['email'] ?? '')));
        if ($email === '' || !isset($byEmail[$email])) continue;
        $matched++;
        $source = $byEmail[$email];
        if (trim((string)($source['firstName'] ?? '')) !== '') $localUser['firstName'] = trim((string)$source['firstName']);
        if (trim((string)($source['lastName'] ?? '')) !== '') $localUser['lastName'] = trim((string)$source['lastName']);
        if (empty($localUser['isOwner'])) {
            $role = mp_role_sanitize_id($source['role'] ?? 'gebruiker');
            if (mp_role_exists($role)) $localUser['role'] = $role;
        }
        $updated++;
    }
    unset($localUser);
    if ($updated) mp_auth_write_users($local);

    return [
        'cloudUsers'=>count($cloudUsers),
        'matchedLocal'=>$matched,
        'updatedLocal'=>$updated,
        'unmatched'=>max(0,count($cloudUsers)-$matched),
        'invitations'=>count($invitations),
    ];
}

if (!mp_auth_is_local_ip(mp_auth_client_ip())) {
    http_response_code(403);
    echo 'Deze importpagina is alleen via het lokale netwerk bereikbaar.';
    exit;
}
try { $currentUser = mp_auth_require_user(); }
catch (Throwable $e) { http_response_code(401); echo 'Meld je eerst lokaal aan in Machinepark.'; exit; }
if (empty($currentUser['isOwner'])) {
    http_response_code(403);
    echo 'Alleen de lokale hoofdbeheerder kan een cloudexport importeren.';
    exit;
}

cloud_ensure_dir(MP_CLOUD_UPLOAD_ROOT);
cloud_ensure_dir(MP_CLOUD_DATA_DIR);
cloud_ensure_dir(MP_CLOUD_BACKUP_DIR);

$action = (string)($_GET['action'] ?? '');

if ($action === 'begin' && strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET')) === 'POST') {
    $body = json_decode((string)file_get_contents('php://input'), true);
    if (!is_array($body)) $body = [];
    $totalBytes = (int)($body['totalBytes'] ?? 0);
    $totalChunks = (int)($body['totalChunks'] ?? 0);
    if ($totalBytes < 10 || $totalBytes > MP_CLOUD_MAX_BYTES) cloud_json(['error'=>'Exportbestand is leeg of groter dan 150 MB.'],400);
    if ($totalChunks < 1 || $totalChunks > 200) cloud_json(['error'=>'Ongeldig aantal uploadblokken.'],400);
    $id = bin2hex(random_bytes(12));
    $dir = cloud_session_path($id);
    cloud_ensure_dir($dir . '/chunks');
    cloud_atomic_json(cloud_manifest_path($id), [
        'id'=>$id,
        'userId'=>(string)($currentUser['id'] ?? ''),
        'fileName'=>basename((string)($body['fileName'] ?? 'cloudexport.json')),
        'totalBytes'=>$totalBytes,
        'totalChunks'=>$totalChunks,
        'createdAt'=>date(DATE_ATOM),
        'finalized'=>false,
        'imported'=>false,
    ]);
    cloud_json(['ok'=>true,'id'=>$id]);
}

if ($action === 'chunk' && strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET')) === 'PUT') {
    try {
        $id = cloud_safe_id($_GET['id'] ?? '');
        $manifest = cloud_read_manifest($id,$currentUser);
        $index = (int)($_GET['index'] ?? -1);
        if ($index < 0 || $index >= (int)$manifest['totalChunks']) throw new RuntimeException('Ongeldig uploadblok.');
        $bytes = file_get_contents('php://input');
        if ($bytes === false || strlen($bytes) < 1 || strlen($bytes) > MP_CLOUD_CHUNK_MAX) throw new RuntimeException('Uploadblok is leeg of te groot.');
        $path = cloud_session_path($id) . '/chunks/' . sprintf('%03d',$index) . '.part';
        if (@file_put_contents($path,$bytes,LOCK_EX) === false) throw new RuntimeException('Uploadblok kon niet worden opgeslagen.');
        cloud_json(['ok'=>true,'index'=>$index]);
    } catch (Throwable $e) { cloud_json(['error'=>$e->getMessage()],400); }
}

if ($action === 'finalize' && strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET')) === 'POST') {
    try {
        $body = json_decode((string)file_get_contents('php://input'), true);
        if (!is_array($body)) $body = [];
        $id = cloud_safe_id($body['id'] ?? '');
        $manifest = cloud_read_manifest($id,$currentUser);
        $target = cloud_package_path($id);
        $out = @fopen($target,'wb');
        if ($out === false) throw new RuntimeException('Exportpakket kon niet worden samengesteld.');
        $written = 0;
        for ($i=0;$i<(int)$manifest['totalChunks'];$i++) {
            $part = cloud_session_path($id) . '/chunks/' . sprintf('%03d',$i) . '.part';
            if (!is_file($part)) { fclose($out); @unlink($target); throw new RuntimeException('Uploadblok ' . ($i+1) . ' ontbreekt.'); }
            $in = @fopen($part,'rb');
            if ($in === false) { fclose($out); @unlink($target); throw new RuntimeException('Uploadblok kon niet worden gelezen.'); }
            $written += stream_copy_to_stream($in,$out);
            fclose($in);
        }
        fclose($out);
        if ($written !== (int)$manifest['totalBytes']) { @unlink($target); throw new RuntimeException('Bestandsgrootte na upload klopt niet.'); }
        $pkg = cloud_load_package($target);
        $manifest['finalized'] = true;
        $manifest['counts'] = cloud_counts($pkg);
        cloud_atomic_json(cloud_manifest_path($id),$manifest);
        cloud_json(['ok'=>true,'id'=>$id,'counts'=>$manifest['counts'],'source'=>$pkg['source'] ?? []]);
    } catch (Throwable $e) { cloud_json(['error'=>$e->getMessage()],400); }
}

if ($action === 'import' && strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET')) === 'POST') {
    try {
        $body = json_decode((string)file_get_contents('php://input'), true);
        if (!is_array($body)) $body = [];
        $id = cloud_safe_id($body['id'] ?? '');
        $manifest = cloud_read_manifest($id,$currentUser);
        if (empty($manifest['finalized'])) throw new RuntimeException('Upload is nog niet afgerond.');
        if (!empty($manifest['imported'])) throw new RuntimeException('Dit exportpakket is al geïmporteerd.');

        $pkg = cloud_load_package(cloud_package_path($id));
        $preparedManuals = cloud_prepare_manuals($pkg, cloud_session_path($id));

        $backup = MP_CLOUD_BACKUP_DIR . '/cloud-import-before-' . date('Ymd-His');
        cloud_ensure_dir($backup);
        foreach ([
            'role-config-v1.json',
            'fault-library-v1.json',
            'work-order-templates-v1.json',
            'manual-library-v1.json',
            'users.json',
            'cloud-users-v1.json',
        ] as $name) {
            cloud_copy_file_if_exists(MP_CLOUD_DATA_DIR . '/' . $name, $backup . '/data/' . $name);
        }
        cloud_copy_dir(MP_CLOUD_MANUAL_DIR, $backup . '/manuals');

        $rolesCount = cloud_import_roles($pkg);
        $faultCount = cloud_import_faults($pkg);
        $workCount = cloud_import_work_orders($pkg);
        $manualCount = cloud_import_manuals($preparedManuals);
        $userResult = cloud_import_users_reference($pkg);
        $auditCount = cloud_import_audit($pkg);

        $manifest['imported'] = true;
        $manifest['importedAt'] = date(DATE_ATOM);
        $manifest['backup'] = $backup;
        cloud_atomic_json(cloud_manifest_path($id),$manifest);

        try {
            mp_audit_append($currentUser,[[
                'entityType'=>'Cloudmigratie',
                'entityId'=>$id,
                'entityLabel'=>'Resterende Netlify-gegevens',
                'action'=>'geïmporteerd',
                'fields'=>[
                    ['field'=>'Rollen','before'=>'—','after'=>(string)$rolesCount],
                    ['field'=>'Storingen','before'=>'—','after'=>(string)$faultCount],
                    ['field'=>'Werkbonnen','before'=>'—','after'=>(string)$workCount],
                    ['field'=>'Handleidingen','before'=>'—','after'=>(string)$manualCount],
                    ['field'=>'Historische logboekregels','before'=>'—','after'=>(string)$auditCount],
                ],
            ]]);
        } catch (Throwable $e) {}

        cloud_json([
            'ok'=>true,
            'backup'=>basename($backup),
            'counts'=>[
                'roles'=>$rolesCount,
                'faults'=>$faultCount,
                'workOrders'=>$workCount,
                'manuals'=>$manualCount,
                'auditEntries'=>$auditCount,
            ],
            'users'=>$userResult,
        ]);
    } catch (Throwable $e) { cloud_json(['error'=>$e->getMessage()],400); }
}

?><!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Machinepark · cloudexport importeren</title>
<style>
:root{font-family:Verdana,Arial,sans-serif;color:#1c2a26;background:#edf3f1}*{box-sizing:border-box}body{margin:0;padding:24px}.wrap{max-width:900px;margin:auto}.card{background:#fff;border:1px solid #d6e0dd;border-radius:18px;padding:22px;box-shadow:0 12px 30px rgba(25,55,47,.08);margin-bottom:16px}h1{margin:0 0 8px;font-size:28px}h2{font-size:18px;margin:0 0 12px}.muted{color:#667773;font-size:13px;line-height:1.55}.warn{background:#fff8e9;border:1px solid #eed9a1;border-radius:12px;padding:12px;font-size:13px;line-height:1.5}.field{display:grid;gap:7px;margin:15px 0}.field input{padding:12px;border:1px solid #cbd8d4;border-radius:11px;font:inherit}.btn{border:0;border-radius:11px;padding:11px 15px;font-weight:700;cursor:pointer;background:#164a3c;color:#fff}.btn:disabled{opacity:.55;cursor:not-allowed}.progress{height:12px;background:#e4ece9;border-radius:999px;overflow:hidden;margin:14px 0}.bar{height:100%;width:0;background:#2f8068;transition:width .15s}.grid{display:grid;grid-template-columns:repeat(6,1fr);gap:9px;margin:16px 0}.stat{border:1px solid #dce5e2;border-radius:12px;padding:11px;text-align:center}.stat strong{display:block;font-size:20px}.log{margin-top:14px;border:1px solid #e0e7e5;border-radius:12px;padding:10px;font-size:12px;line-height:1.5;max-height:260px;overflow:auto;background:#fafcfc}.ok{color:#247458}.err{color:#a13b3b}@media(max-width:800px){.grid{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>Resterende cloudgegevens importeren</h1>
    <p class="muted">Gebruik hier het bestand <strong>Machinepark_Synology_CloudExport_….json</strong> uit de online Netlify-preview. Voor lokale configuratie en handleidingen wordt automatisch een veiligheidsback-up gemaakt.</p>
    <div class="warn"><strong>Gebruikers:</strong> Clerk-wachtwoorden zitten niet in het exportbestand. Bestaande lokale accounts worden daarom nooit vervangen. Bij eenzelfde e-mailadres worden alleen naam en geldige rol bijgewerkt; overige cloudgebruikers worden als referentie bewaard.</div>
    <div class="field"><label for="cloudFile">Cloudexportbestand</label><input id="cloudFile" type="file" accept="application/json,.json"></div>
    <button class="btn" id="uploadBtn" type="button">Exportbestand controleren</button>
    <div class="progress" id="progressWrap" style="display:none"><div class="bar" id="bar"></div></div>
    <div class="muted" id="status">Nog geen bestand gekozen.</div>
  </div>

  <div class="card" id="previewCard" style="display:none">
    <h2>Gevonden gegevens</h2>
    <div class="grid">
      <div class="stat"><strong id="rRoles">0</strong><span>Rollen</span></div>
      <div class="stat"><strong id="rFaults">0</strong><span>Storingen</span></div>
      <div class="stat"><strong id="rWork">0</strong><span>Werkbonnen</span></div>
      <div class="stat"><strong id="rManuals">0</strong><span>Handleidingen</span></div>
      <div class="stat"><strong id="rUsers">0</strong><span>Gebruikers</span></div>
      <div class="stat"><strong id="rAudit">0</strong><span>Logboek</span></div>
    </div>
    <button class="btn" id="importBtn" type="button">Nu veilig naar Synology importeren</button>
    <div class="log" id="log"></div>
  </div>
</div>
<script>
const fileInput=document.getElementById('cloudFile');
const uploadBtn=document.getElementById('uploadBtn');
const importBtn=document.getElementById('importBtn');
const statusEl=document.getElementById('status');
const preview=document.getElementById('previewCard');
const bar=document.getElementById('bar');
const wrap=document.getElementById('progressWrap');
const log=document.getElementById('log');
let sessionId='';

function line(msg,cls=''){const d=document.createElement('div');if(cls)d.className=cls;d.textContent=msg;log.appendChild(d);log.scrollTop=log.scrollHeight}
async function jsonApi(action,payload){
  const res=await fetch('?action='+encodeURIComponent(action),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload||{}),cache:'no-store'});
  const body=await res.json().catch(()=>({}));
  if(!res.ok)throw new Error(body.error||('HTTP '+res.status));
  return body;
}
async function putChunk(id,index,blob){
  const res=await fetch('?action=chunk&id='+encodeURIComponent(id)+'&index='+index,{method:'PUT',body:blob,cache:'no-store'});
  const body=await res.json().catch(()=>({}));
  if(!res.ok)throw new Error(body.error||('Uploadblok '+(index+1)+' mislukt'));
  return body;
}
function setCounts(c){document.getElementById('rRoles').textContent=c.roles||0;document.getElementById('rFaults').textContent=c.faults||0;document.getElementById('rWork').textContent=c.workOrders||0;document.getElementById('rManuals').textContent=c.manuals||0;document.getElementById('rUsers').textContent=c.users||0;document.getElementById('rAudit').textContent=c.auditEntries||0}

uploadBtn.addEventListener('click',async()=>{
  const file=fileInput.files?.[0];
  if(!file){alert('Kies eerst het Synology-cloudexportbestand.');return}
  uploadBtn.disabled=true;preview.style.display='none';wrap.style.display='block';bar.style.width='0%';statusEl.textContent='Upload voorbereiden…';log.innerHTML='';
  try{
    const chunkSize=1024*1024;
    const totalChunks=Math.ceil(file.size/chunkSize);
    const begin=await jsonApi('begin',{fileName:file.name,totalBytes:file.size,totalChunks});
    sessionId=begin.id;
    for(let i=0;i<totalChunks;i++){
      statusEl.textContent='Upload '+(i+1)+' van '+totalChunks;
      await putChunk(sessionId,i,file.slice(i*chunkSize,Math.min(file.size,(i+1)*chunkSize)));
      bar.style.width=Math.round(((i+1)/totalChunks)*85)+'%';
    }
    statusEl.textContent='Bestand controleren…';
    const final=await jsonApi('finalize',{id:sessionId});
    bar.style.width='100%';setCounts(final.counts||{});preview.style.display='block';
    statusEl.textContent='Exportbestand is geldig en klaar om te importeren.';
    line('✓ Exportpakket gecontroleerd.','ok');
    if(final.source?.origin)line('Bron: '+final.source.origin);
  }catch(error){
    sessionId='';statusEl.textContent=error.message;line('✗ '+error.message,'err');
  }finally{uploadBtn.disabled=false}
});

importBtn.addEventListener('click',async()=>{
  if(!sessionId)return;
  if(!confirm('Deze import vervangt de lokale cloudconfiguratie door de gegevens uit het exportpakket. Er wordt eerst automatisch een veiligheidsback-up gemaakt. Doorgaan?'))return;
  importBtn.disabled=true;line('Import gestart…');
  try{
    const result=await jsonApi('import',{id:sessionId});
    line('✓ Rollen: '+(result.counts?.roles||0),'ok');
    line('✓ Storingen: '+(result.counts?.faults||0),'ok');
    line('✓ Werkbonnen: '+(result.counts?.workOrders||0),'ok');
    line('✓ Handleidingen: '+(result.counts?.manuals||0),'ok');
    line('✓ Historische logboekregels: '+(result.counts?.auditEntries||0),'ok');
    line('✓ Lokale gebruikers gematcht: '+(result.users?.matchedLocal||0)+' · nog handmatig aan te maken: '+(result.users?.unmatched||0),'ok');
    line('Veiligheidsback-up: '+(result.backup||'gemaakt'),'ok');
    statusEl.textContent='Cloudgegevens zijn naar Synology geïmporteerd. Open Machinepark opnieuw met Ctrl+F5.';
    bar.style.width='100%';
  }catch(error){line('✗ '+error.message,'err');statusEl.textContent=error.message}
  finally{importBtn.disabled=false}
});
</script>
</body>
</html>
