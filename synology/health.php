<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

$baseDir = getenv('MACHINEPARK_DATA_DIR') ?: '';

$response = [
    'ok' => true,
    'app' => 'Machinepark',
    'mode' => 'synology-selfhost-test',
    'php' => PHP_VERSION,
    'time' => date(DATE_ATOM),
    'storage' => [
        'baseDirConfigured' => $baseDir !== '',
        'baseDirExists' => $baseDir !== '' ? is_dir($baseDir) : false,
        'baseDirWritable' => $baseDir !== '' ? is_writable($baseDir) : false,
    ],
];

echo json_encode($response, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
