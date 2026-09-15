<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

$baseDir = getenv('MACHINEPARK_DATA_DIR');
if (!$baseDir) {
    $baseDir = '/volume1/MachineparkData';
}

$requiredDirs = [
    'data',
    'photos',
    'photos/devices',
    'photos/service',
    'manuals',
    'uploads',
    'backups',
];

$result = [
    'ok' => true,
    'app' => 'Machinepark',
    'mode' => 'synology-storage-test',
    'baseDir' => $baseDir,
    'baseDirExists' => is_dir($baseDir),
    'baseDirReadable' => is_readable($baseDir),
    'baseDirWritable' => is_writable($baseDir),
    'directories' => [],
    'writeTest' => [
        'attempted' => false,
        'written' => false,
        'readBack' => false,
        'deleted' => false,
        'error' => null,
    ],
];

foreach ($requiredDirs as $relative) {
    $path = $baseDir . '/' . $relative;
    $result['directories'][$relative] = [
        'exists' => is_dir($path),
        'readable' => is_readable($path),
        'writable' => is_writable($path),
    ];

    if (!is_dir($path) || !is_readable($path)) {
        $result['ok'] = false;
    }
}

$dataDir = $baseDir . '/data';
if (is_dir($dataDir)) {
    $result['writeTest']['attempted'] = true;
    $testFile = $dataDir . '/_machinepark_write_test.json';
    $payload = [
        'app' => 'Machinepark',
        'test' => true,
        'time' => date(DATE_ATOM),
        'random' => bin2hex(random_bytes(8)),
    ];

    try {
        $json = json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
        if ($json === false) {
            throw new RuntimeException('JSON kon niet worden aangemaakt.');
        }

        $bytes = @file_put_contents($testFile, $json, LOCK_EX);
        $result['writeTest']['written'] = $bytes !== false;

        if ($bytes === false) {
            throw new RuntimeException('PHP heeft geen schrijfrechten in ' . $dataDir);
        }

        $read = @file_get_contents($testFile);
        $decoded = $read !== false ? json_decode($read, true) : null;
        $result['writeTest']['readBack'] = is_array($decoded)
            && isset($decoded['random'])
            && $decoded['random'] === $payload['random'];

        $result['writeTest']['deleted'] = @unlink($testFile);

        if (!$result['writeTest']['readBack'] || !$result['writeTest']['deleted']) {
            $result['ok'] = false;
        }
    } catch (Throwable $e) {
        $result['ok'] = false;
        $result['writeTest']['error'] = $e->getMessage();
        if (isset($testFile) && is_file($testFile)) {
            @unlink($testFile);
        }
    }
} else {
    $result['ok'] = false;
    $result['writeTest']['error'] = 'De map data bestaat niet: ' . $dataDir;
}

echo json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
