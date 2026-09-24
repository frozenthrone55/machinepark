<?php
declare(strict_types=1);

require_once __DIR__ . '/api/_auth-lib.php';

header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');

define('MP_RECOVERY_CODE_FILE', '/volume1/MachineparkData/admin-recovery-code.txt');
define('MP_RECOVERY_LOCK_FILE', '/volume1/MachineparkData/data/admin-recovery.lock');

function recovery_h($value): string {
    return htmlspecialchars((string)$value, ENT_QUOTES, 'UTF-8');
}

function recovery_local_only(): void {
    $host = mp_auth_request_host();
    $client = mp_auth_client_ip();

    if (!mp_auth_is_local_ip($client) || !mp_auth_is_private_host($host) || mp_auth_is_public_host($host)) {
        http_response_code(403);
        echo 'Adminherstel is uitsluitend via het interne NAS-adres beschikbaar.';
        exit;
    }
}

function recovery_code(): string {
    $dir = dirname(MP_RECOVERY_CODE_FILE);
    if (!is_dir($dir) || !is_writable($dir)) {
        throw new RuntimeException('De lokale datamap is niet schrijfbaar.');
    }

    if (is_file(MP_RECOVERY_CODE_FILE)) {
        $existing = trim((string)@file_get_contents(MP_RECOVERY_CODE_FILE));
        if (preg_match('/^[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}$/', $existing)) return $existing;
    }

    $alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    $parts = [];
    for ($p = 0; $p < 3; $p++) {
        $part = '';
        for ($i = 0; $i < 6; $i++) {
            $part .= $alphabet[random_int(0, strlen($alphabet) - 1)];
        }
        $parts[] = $part;
    }
    $code = implode('-', $parts);

    if (@file_put_contents(MP_RECOVERY_CODE_FILE, $code . PHP_EOL, LOCK_EX) === false) {
        throw new RuntimeException('De herstelcode kon niet op de NAS worden opgeslagen.');
    }
    @chmod(MP_RECOVERY_CODE_FILE, 0644);
    return $code;
}

function recovery_admin_candidates(array $users): array {
    $candidates = [];
    foreach ($users as $index => $user) {
        if (!is_array($user) || !empty($user['disabled'])) continue;
        $hasPassword = trim((string)($user['passwordHash'] ?? '')) !== '';
        $isOwner = !empty($user['isOwner']);
        $isAdmin = strtolower(trim((string)($user['role'] ?? ''))) === 'beheerder';
        $username = strtolower(trim((string)($user['username'] ?? '')));
        if ($hasPassword && ($isOwner || $isAdmin || $username === 'admin')) {
            $candidates[] = ['index'=>(int)$index,'user'=>$user];
        }
    }
    return $candidates;
}

function recovery_select_admin(array $users): array {
    $candidates = recovery_admin_candidates($users);

    foreach ($candidates as $candidate) {
        if (!empty($candidate['user']['isOwner'])) return $candidate;
    }
    foreach ($candidates as $candidate) {
        if (strtolower(trim((string)($candidate['user']['username'] ?? ''))) === 'admin') return $candidate;
    }
    if (count($candidates) === 1) return $candidates[0];

    if (!$candidates) {
        throw new RuntimeException('Er is geen bestaand lokaal beheeraccount met wachtwoord gevonden.');
    }
    throw new RuntimeException('Er zijn meerdere mogelijke beheeraccounts gevonden. Herstel is geblokkeerd om het verkeerde account niet te wijzigen.');
}

function recovery_reset(string $submittedCode, string $newPassword): array {
    $expected = recovery_code();
    $submittedCode = strtoupper(trim($submittedCode));

    if (!hash_equals($expected, $submittedCode)) {
        usleep(400000);
        throw new RuntimeException('De herstelcode is onjuist.');
    }
    if (strlen($newPassword) < 10) {
        throw new RuntimeException('Gebruik een nieuw wachtwoord van minstens 10 tekens.');
    }

    $lock = @fopen(MP_RECOVERY_LOCK_FILE, 'c+');
    if ($lock === false || !flock($lock, LOCK_EX)) {
        if (is_resource($lock)) fclose($lock);
        throw new RuntimeException('De herstelvergrendeling kon niet worden verkregen.');
    }

    try {
        $users = mp_auth_read_users();
        $selected = recovery_select_admin($users);
        $idx = (int)$selected['index'];

        $users[$idx]['username'] = 'admin';
        $users[$idx]['isOwner'] = true;
        $users[$idx]['role'] = 'beheerder';
        $users[$idx]['passwordHash'] = password_hash($newPassword, PASSWORD_DEFAULT);
        $users[$idx]['disabled'] = false;
        $users[$idx]['adminRecoveredAt'] = date(DATE_ATOM);

        mp_auth_write_users($users);

        // Herstelcode na geslaagd gebruik vernietigen; bij een volgende
        // herstelpoging wordt automatisch een nieuwe code aangemaakt.
        @unlink(MP_RECOVERY_CODE_FILE);

        flock($lock, LOCK_UN);
        fclose($lock);

        return mp_auth_public_user($users[$idx]);
    } catch (Throwable $e) {
        @flock($lock, LOCK_UN);
        @fclose($lock);
        throw $e;
    }
}

recovery_local_only();

$message = '';
$error = '';
$success = false;

try {
    $code = recovery_code();
} catch (Throwable $e) {
    $code = '';
    $error = $e->getMessage();
}

if (strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET')) === 'POST' && $error === '') {
    $submitted = (string)($_POST['recovery_code'] ?? '');
    $password = (string)($_POST['new_password'] ?? '');
    $confirm = (string)($_POST['confirm_password'] ?? '');

    if ($password !== $confirm) {
        $error = 'De twee nieuwe wachtwoorden zijn niet gelijk.';
    } else {
        try {
            $user = recovery_reset($submitted, $password);
            $success = true;
            $message = 'Admin-account hersteld. Je kunt nu aanmelden met gebruikersnaam admin en je nieuwe wachtwoord.';
        } catch (Throwable $e) {
            $error = $e->getMessage();
        }
    }
}
?><!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Machinepark · admin herstellen</title>
<style>
:root{font-family:Verdana,Arial,sans-serif;color:#1c2a26;background:#edf3f1}*{box-sizing:border-box}body{margin:0;padding:24px}.wrap{max-width:720px;margin:30px auto}.card{background:#fff;border:1px solid #d6e0dd;border-radius:18px;padding:24px;box-shadow:0 12px 30px rgba(25,55,47,.08)}h1{margin:0 0 10px;font-size:26px}.muted{color:#667773;font-size:13px;line-height:1.55}.info{background:#f5faf8;border:1px solid #cfe0da;border-radius:12px;padding:13px;margin:16px 0;font-size:13px;line-height:1.55}.error{background:#fff2f2;border:1px solid #efc3c3;color:#9b3232;border-radius:12px;padding:13px;margin:14px 0;font-size:13px}.ok{background:#eef9f4;border:1px solid #bcdccc;color:#226b52;border-radius:12px;padding:13px;margin:14px 0;font-size:13px}.field{display:grid;gap:6px;margin:14px 0}.field input{padding:12px;border:1px solid #cbd8d4;border-radius:10px;font:inherit}.btn{border:0;border-radius:11px;padding:12px 16px;font-weight:700;cursor:pointer;background:#164a3c;color:#fff}.path{font-family:Consolas,monospace;background:#f3f5f4;border-radius:6px;padding:3px 6px;word-break:break-all}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>Lokale admin herstellen</h1>
    <p class="muted">Deze pagina werkt alleen via het interne NAS-adres. Machinepark-data, foto's, handleidingen, Storingen en rollen worden niet gewist.</p>

    <?php if ($success): ?>
      <div class="ok"><?=recovery_h($message)?></div>
      <p><a class="btn" style="display:inline-block;text-decoration:none" href="../">Terug naar Machinepark</a></p>
    <?php else: ?>
      <div class="info">
        Open in Synology <strong>File Station</strong> het bestand:<br><br>
        <span class="path">/volume1/MachineparkData/admin-recovery-code.txt</span><br><br>
        Kopieer de code uit dat bestand en vul hem hieronder in. De code wordt na een geslaagde reset automatisch verwijderd.
      </div>

      <?php if ($error !== ''): ?><div class="error"><?=recovery_h($error)?></div><?php endif; ?>

      <form method="post" autocomplete="off">
        <div class="field">
          <label>Herstelcode</label>
          <input name="recovery_code" type="text" required autocomplete="off" spellcheck="false" placeholder="XXXXXX-XXXXXX-XXXXXX">
        </div>
        <div class="field">
          <label>Nieuw admin-wachtwoord</label>
          <input name="new_password" type="password" minlength="10" required autocomplete="new-password">
        </div>
        <div class="field">
          <label>Nieuw wachtwoord herhalen</label>
          <input name="confirm_password" type="password" minlength="10" required autocomplete="new-password">
        </div>
        <button class="btn" type="submit">Admin herstellen</button>
      </form>
    <?php endif; ?>
  </div>
</div>
</body>
</html>
