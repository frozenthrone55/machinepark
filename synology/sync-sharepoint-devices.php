<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
require_once __DIR__ . '/api/_device-sync-lib.php';
date_default_timezone_set('Europe/Brussels');
try { $result=mp_sync_run(); echo json_encode($result,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES).PHP_EOL;exit(($result['status']??'')==='error'?1:0); }
catch(Throwable $e){fwrite(STDERR,$e->getMessage().PHP_EOL);exit(1);}
