<?php
declare(strict_types=1);

header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');

define('MP_DATA_DIR', '/volume1/MachineparkData/data');
define('MP_BACKUP_DIR', '/volume1/MachineparkData/backups');
define('MP_STATE_FILE', MP_DATA_DIR . '/state-v1.json');
define('MP_LOCK_FILE', MP_DATA_DIR . '/state-v1.lock');

function client_ip(): string {
    return (string)($_SERVER['REMOTE_ADDR'] ?? '');
}

function is_local_ip(string $ip): bool {
    if ($ip === '127.0.0.1' || $ip === '::1') return true;
    if (strpos($ip, '10.') === 0 || strpos($ip, '192.168.') === 0) return true;
    $lower = strtolower($ip);
    if (strpos($lower, 'fc') === 0 || strpos($lower, 'fd') === 0 || strpos($lower, 'fe80:') === 0) return true;

    if (filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4)) {
        $long = ip2long($ip);
        $start = ip2long('172.16.0.0');
        $end = ip2long('172.31.255.255');
        if ($long !== false && $start !== false && $end !== false && $long >= $start && $long <= $end) return true;
    }
    return false;
}

function h(string $value): string {
    return htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
}

function valid_snapshot($data): bool {
    return is_array($data)
        && ($data['app'] ?? '') === 'Machinepark'
        && (int)($data['schema'] ?? 0) === 1
        && isset($data['parts']) && is_array($data['parts'])
        && isset($data['devices']) && is_array($data['devices'])
        && isset($data['maintenance']) && is_array($data['maintenance'])
        && isset($data['breakdowns']) && is_array($data['breakdowns']);
}

function atomic_write(array $data): void {
    $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false) throw new RuntimeException('Back-up kon niet naar JSON worden omgezet.');

    $tmp = MP_STATE_FILE . '.migration-' . bin2hex(random_bytes(6));
    if (@file_put_contents($tmp, $json, LOCK_EX) === false) {
        throw new RuntimeException('Tijdelijke lokale database kon niet worden geschreven.');
    }
    if (!@rename($tmp, MP_STATE_FILE)) {
        @unlink($tmp);
        throw new RuntimeException('Lokale database kon niet atomair worden opgeslagen.');
    }
}

$local = is_local_ip(client_ip());
$message = '';
$error = '';
$summary = null;

if (!$local) {
    http_response_code(403);
    $error = 'Deze migratiepagina is alleen toegankelijk via het lokale IP-adres van de Synology.';
} elseif ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        if (is_file(MP_STATE_FILE)) {
            throw new RuntimeException('De lokale database is al geïnitialiseerd. Migratie is daarom geblokkeerd om bestaande Synology-data niet te overschrijven.');
        }

        if (!isset($_FILES['backup']) || !is_array($_FILES['backup'])) {
            throw new RuntimeException('Kies eerst een Machinepark back-upbestand.');
        }

        $upload = $_FILES['backup'];
        if (($upload['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
            throw new RuntimeException('Uploaden van het back-upbestand is mislukt.');
        }

        $size = (int)($upload['size'] ?? 0);
        if ($size <= 0) throw new RuntimeException('Het gekozen bestand is leeg.');
        if ($size > 100 * 1024 * 1024) throw new RuntimeException('Het gekozen bestand is groter dan 100 MB.');

        $raw = @file_get_contents((string)$upload['tmp_name']);
        if ($raw === false) throw new RuntimeException('Het geüploade bestand kon niet worden gelezen.');

        $data = json_decode($raw, true);
        if (!valid_snapshot($data)) {
            throw new RuntimeException('Dit is geen geldige Machinepark back-up (app/schema/stores kloppen niet).');
        }

        if (!is_dir(MP_DATA_DIR) || !is_writable(MP_DATA_DIR)) {
            throw new RuntimeException('MachineparkData/data is niet schrijfbaar.');
        }
        if (!is_dir(MP_BACKUP_DIR) || !is_writable(MP_BACKUP_DIR)) {
            throw new RuntimeException('MachineparkData/backups is niet schrijfbaar.');
        }

        $lock = @fopen(MP_LOCK_FILE, 'c+');
        if ($lock === false) throw new RuntimeException('Migratielock kon niet worden geopend.');
        if (!flock($lock, LOCK_EX)) {
            fclose($lock);
            throw new RuntimeException('Migratielock kon niet worden verkregen.');
        }

        if (is_file(MP_STATE_FILE)) {
            flock($lock, LOCK_UN);
            fclose($lock);
            throw new RuntimeException('De lokale database werd intussen geïnitialiseerd. Niets is overschreven.');
        }

        $stamp = date('Ymd-His');
        $original = MP_BACKUP_DIR . '/migration-original-' . $stamp . '.json';
        if (@file_put_contents($original, $raw, LOCK_EX) === false) {
            flock($lock, LOCK_UN);
            fclose($lock);
            throw new RuntimeException('Originele migratieback-up kon niet worden bewaard.');
        }

        $data['updatedAt'] = date(DATE_ATOM);
        $data['migratedToSynologyAt'] = date(DATE_ATOM);
        atomic_write($data);

        flock($lock, LOCK_UN);
        fclose($lock);

        $summary = [
            'devices' => count($data['devices']),
            'parts' => count($data['parts']),
            'maintenance' => count($data['maintenance']),
            'breakdowns' => count($data['breakdowns']),
        ];
        $message = 'De lokale Machinepark-database is succesvol geïnitialiseerd.';
    } catch (Throwable $e) {
        $error = $e->getMessage();
    }
}

$alreadyInitialized = is_file(MP_STATE_FILE);
?><!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Machinepark · Migratie naar Synology</title>
<style>
body{font-family:Arial,sans-serif;background:#f5f7f6;color:#17211e;margin:0;padding:28px}
.card{max-width:760px;margin:0 auto;background:#fff;border:1px solid #d7dfdc;border-radius:18px;padding:24px;box-shadow:0 8px 30px rgba(0,0,0,.06)}
h1{margin:0 0 8px;font-size:26px}
p{line-height:1.55}
.note,.ok,.error{border-radius:12px;padding:12px 14px;margin:14px 0}
.note{background:#f0f4f2;border:1px solid #d8e1dd}
.ok{background:#e9f7ef;border:1px solid #abd5bb}
.error{background:#fff0f0;border:1px solid #e2aaaa}
label{display:block;font-weight:700;margin:18px 0 7px}
input[type=file]{display:block;width:100%;box-sizing:border-box;padding:12px;border:1px solid #ccd6d2;border-radius:10px;background:#fff}
button{margin-top:16px;background:#183f35;color:white;border:0;border-radius:10px;padding:11px 16px;font-weight:700;cursor:pointer}
button[disabled]{opacity:.45;cursor:not-allowed}
code{background:#eef2f0;border-radius:5px;padding:2px 5px}
.stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:14px}
.stat{border:1px solid #d8e0dd;border-radius:12px;padding:12px}
.stat strong{display:block;font-size:22px}
</style>
</head>
<body>
<div class="card">
<h1>Machinepark · migratie naar Synology</h1>
<p>Hiermee zet je éénmalig de huidige Machinepark-back-up over naar de lokale database op <code>/volume1/MachineparkData/data/state-v1.json</code>.</p>

<div class="note"><strong>Veiligheid:</strong> deze pagina werkt alleen via het lokale netwerk en weigert een tweede initialisatie zodra er al lokale data bestaat.</div>

<?php if ($error): ?><div class="error"><?=h($error)?></div><?php endif; ?>
<?php if ($message): ?><div class="ok"><strong><?=h($message)?></strong>
<?php if ($summary): ?><div class="stats">
<div class="stat"><strong><?=h((string)$summary['devices'])?></strong>toestellen</div>
<div class="stat"><strong><?=h((string)$summary['parts'])?></strong>onderdelen</div>
<div class="stat"><strong><?=h((string)$summary['maintenance'])?></strong>onderhoudsregels</div>
<div class="stat"><strong><?=h((string)$summary['breakdowns'])?></strong>depannages / andere werken</div>
</div><?php endif; ?>
</div><?php endif; ?>

<?php if ($alreadyInitialized): ?>
<div class="ok"><strong>Lokale database aanwezig.</strong><br>De eerste migratie is al uitgevoerd. Deze pagina zal de bestaande database niet overschrijven.</div>
<?php elseif ($local): ?>
<form method="post" enctype="multipart/form-data">
<label for="backup">Machinepark back-upbestand (.json)</label>
<input id="backup" name="backup" type="file" accept=".json,application/json" required>
<button type="submit">Back-up naar Synology migreren</button>
</form>
<?php endif; ?>

<p style="margin-top:22px;font-size:13px;color:#66736e">Na een succesvolle migratie controleren we eerst aantallen en centrale synchronisatie voordat foto's, handleidingen en overige bibliotheken worden verhuisd.</p>
</div>
</body>
</html>
