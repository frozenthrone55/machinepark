<?php
declare(strict_types=1);

define('MP_PHOTO_ROOT', '/volume1/MachineparkData/photos');

function mp_photo_json(array $body, int $status = 200): void {
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
    header('X-Content-Type-Options: nosniff');
    http_response_code($status);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function mp_photo_safe_id($value, int $max = 100): string {
    $id = preg_replace('/[^A-Za-z0-9_-]+/', '_', trim((string)$value));
    return substr((string)$id, 0, $max);
}

function mp_photo_safe_token($value): string {
    $token = preg_replace('/[^A-Za-z0-9_-]+/', '', trim((string)$value));
    return substr((string)$token, 0, 100);
}

function mp_photo_ensure_dir(string $dir): void {
    if (!is_dir($dir) && !@mkdir($dir, 0770, true) && !is_dir($dir)) {
        throw new RuntimeException('Fotomap kon niet worden aangemaakt.');
    }
    if (!is_writable($dir)) throw new RuntimeException('Fotomap is niet schrijfbaar.');
}

function mp_photo_parse_data_image($value, int $maxBytes): array {
    $raw = (string)$value;
    if (!preg_match('#^data:(image/[A-Za-z0-9.+-]+);base64,([A-Za-z0-9+/=\r\n]+)$#', $raw, $match)) {
        throw new RuntimeException('De afbeelding bevat ongeldige gegevens.');
    }
    $bytes = base64_decode(preg_replace('/\s+/', '', $match[2]), true);
    if ($bytes === false || strlen($bytes) === 0) throw new RuntimeException('De afbeelding bevat ongeldige gegevens.');
    if (strlen($bytes) > $maxBytes) throw new RuntimeException('De afbeelding is te groot.');
    $type = strtolower((string)$match[1]);
    $allowed = ['image/jpeg','image/png','image/webp','image/gif'];
    if (!in_array($type, $allowed, true)) throw new RuntimeException('Dit afbeeldingsformaat wordt niet ondersteund.');
    return ['bytes'=>$bytes,'contentType'=>$type];
}

function mp_photo_write_blob(string $basePath, array $parsed): void {
    $tmp = $basePath . '.tmp-' . bin2hex(random_bytes(5));
    if (@file_put_contents($tmp, $parsed['bytes'], LOCK_EX) === false) {
        throw new RuntimeException('Foto kon niet worden geschreven.');
    }
    if (!@rename($tmp, $basePath . '.bin')) {
        @unlink($tmp);
        throw new RuntimeException('Foto kon niet atomair worden opgeslagen.');
    }
    $meta = json_encode(['contentType'=>$parsed['contentType'],'updatedAt'=>date(DATE_ATOM)], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($meta === false || @file_put_contents($basePath . '.meta.json', $meta, LOCK_EX) === false) {
        @unlink($basePath . '.bin');
        throw new RuntimeException('Fotometadata kon niet worden opgeslagen.');
    }
}

function mp_photo_exists(string $basePath): bool {
    return is_file($basePath . '.bin');
}

function mp_photo_delete_blob(string $basePath): void {
    @unlink($basePath . '.bin');
    @unlink($basePath . '.meta.json');
    @unlink($basePath . '.thumb.bin');
    @unlink($basePath . '.thumb.meta.json');
}

function mp_photo_write_thumb(string $basePath, array $parsed): void {
    $tmp = $basePath . '.thumb.tmp-' . bin2hex(random_bytes(5));
    if (@file_put_contents($tmp, $parsed['bytes'], LOCK_EX) === false) throw new RuntimeException('Thumbnail kon niet worden geschreven.');
    if (!@rename($tmp, $basePath . '.thumb.bin')) {
        @unlink($tmp);
        throw new RuntimeException('Thumbnail kon niet atomair worden opgeslagen.');
    }
    $meta = json_encode(['contentType'=>$parsed['contentType'],'updatedAt'=>date(DATE_ATOM)], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($meta === false || @file_put_contents($basePath . '.thumb.meta.json', $meta, LOCK_EX) === false) {
        @unlink($basePath . '.thumb.bin');
        throw new RuntimeException('Thumbnailmetadata kon niet worden opgeslagen.');
    }
}

function mp_photo_content_type(string $metaPath): string {
    if (!is_file($metaPath)) return 'image/jpeg';
    $raw = @file_get_contents($metaPath);
    $data = $raw !== false ? json_decode($raw, true) : null;
    $type = is_array($data) ? (string)($data['contentType'] ?? '') : '';
    return strpos($type, 'image/') === 0 ? $type : 'image/jpeg';
}

function mp_photo_serve(string $basePath, bool $thumb, bool $headOnly): void {
    $thumbPath = $basePath . '.thumb.bin';
    $useThumb = $thumb && is_file($thumbPath);
    if ($thumb && $headOnly && !$useThumb) {
        http_response_code(404);
        header('Cache-Control: no-store');
        header('X-Machinepark-Thumbnail: missing');
        exit;
    }

    $file = $useThumb ? $thumbPath : $basePath . '.bin';
    if (!is_file($file)) {
        http_response_code(404);
        header('Content-Type: text/plain; charset=utf-8');
        echo 'Foto niet gevonden.';
        exit;
    }

    $meta = $useThumb ? $basePath . '.thumb.meta.json' : $basePath . '.meta.json';
    header('Content-Type: ' . mp_photo_content_type($meta));
    header('Cache-Control: private, max-age=' . ($useThumb ? '604800' : '86400'));
    header('X-Content-Type-Options: nosniff');
    header('X-Machinepark-Thumbnail: ' . ($useThumb ? 'exact' : ($thumb ? 'fallback' : 'full')));
    header('Content-Length: ' . filesize($file));
    if ($headOnly) exit;
    readfile($file);
    exit;
}

function mp_photo_ref(string $endpoint, string $key, bool $thumb = false): string {
    return './synology/api/' . $endpoint . '?key=' . rawurlencode($key) . ($thumb ? '&variant=thumb' : '');
}

function mp_photo_key_from_ref($value, string $endpoint, string $prefix): string {
    $text = trim((string)$value);
    if ($text === '') return '';
    $query = parse_url($text, PHP_URL_QUERY);
    $path = (string)(parse_url($text, PHP_URL_PATH) ?? '');
    $accepted = [
        './synology/api/' . $endpoint,
        '/machinepark/synology/api/' . $endpoint,
        'synology/api/' . $endpoint,
    ];
    $pathOk = false;
    foreach ($accepted as $candidate) {
        if ($path === $candidate || ltrim($path, '/') === ltrim($candidate, '/')) { $pathOk = true; break; }
    }
    if (!$pathOk || $query === null || $query === false) return '';
    parse_str($query, $params);
    $key = rawurldecode((string)($params['key'] ?? ''));
    return strpos($key, $prefix) === 0 ? $key : '';
}

function mp_photo_is_legacy_ref($value, string $endpoint): bool {
    return strpos((string)$value, '/.netlify/functions/' . preg_replace('/\.php$/', '', $endpoint) . '?') !== false;
}

function mp_photo_remove_directory(string $dir): int {
    if (!is_dir($dir)) return 0;
    $count = 0;
    foreach ((array)glob($dir . '/*') as $path) {
        if (is_dir($path)) $count += mp_photo_remove_directory($path);
        elseif (is_file($path)) { if (@unlink($path)) $count++; }
    }
    @rmdir($dir);
    return $count;
}

function mp_photo_cleanup_bases(string $dir, array $keepTokens): void {
    if (!is_dir($dir)) return;
    $keep = array_fill_keys($keepTokens, true);
    foreach ((array)glob($dir . '/*.bin') as $path) {
        if (substr($path, -10) === '.thumb.bin') continue;
        $name = basename($path, '.bin');
        if (isset($keep[$name])) continue;
        mp_photo_delete_blob($dir . '/' . $name);
    }
}

function mp_photo_require_local_user(): array {
    if (!mp_auth_is_local_ip(mp_auth_client_ip())) mp_photo_json(['error'=>'Lokale foto-opslag is voorlopig alleen via het lokale netwerk bereikbaar.'],403);
    try { return mp_auth_require_user(); }
    catch (Throwable $e) { mp_photo_json(['error'=>'Niet aangemeld.'],401); }
}

function mp_photo_can(array $user, array $permissions): bool {
    if (!empty($user['isOwner'])) return true;
    $granted = mp_role_permissions((string)($user['role'] ?? 'gebruiker'));
    foreach ($permissions as $permission) if (!empty($granted[$permission])) return true;
    return false;
}
