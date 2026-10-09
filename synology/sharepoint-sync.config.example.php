<?php
// Copy to /volume1/MachineparkData/config/sharepoint-sync.php (outside the webroot).
// Restrict this file to the PHP worker and the NAS task account. Never commit real keys.
return [
    'tenant_id' => '',
    'client_id' => '',
    'client_secret' => '',
    'drive_id' => '',
    'item_id' => '',
    // Absolute path to an installed Node.js >= 16 executable, confirmed on your NAS.
    'node_path' => '',
];
