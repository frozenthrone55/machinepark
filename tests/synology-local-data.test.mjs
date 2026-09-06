import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const api = readFileSync(new URL('../synology/api/machinepark-data.php', import.meta.url), 'utf8');
const authLib = readFileSync(new URL('../synology/api/_auth-lib.php', import.meta.url), 'utf8');
const builder = readFileSync(new URL('../build-synology-local-data.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('lokale data API schrijft buiten de webroot', () => {
  assert.match(api, /\/volume1\/MachineparkData\/data/);
  assert.match(api, /state-v1\.json/);
  assert.match(api, /state-v1\.lock/);
});

test('data API gebruikt de centrale veilige toegangslaag', () => {
  assert.match(api, /mp_auth_require_request_access/);
  assert.match(api, /mp_auth_access_error_payload/);
  assert.match(authLib, /192\.168\./);
  assert.match(authLib, /172\.16\.0\.0/);
  assert.match(authLib, /krisooms\.synology\.me/);
  assert.match(authLib, /mp_auth_request_is_https/);
});

test('lokale data API gebruikt etag locking en automatische backups', () => {
  assert.match(api, /hash_file\('sha256', MP_STATE_FILE\)/);
  assert.match(api, /flock\(\$lock, LOCK_EX\)/);
  assert.match(api, /mp_backup_current\(\)/);
  assert.match(api, /while \(count\(\$files\) > 30\)/);
  assert.match(api, /De centrale gegevens zijn intussen gewijzigd/);
});

test('lege lokale database kan niet per ongeluk via gewone sync worden geïnitialiseerd', () => {
  assert.match(api, /not_initialized/);
  assert.match(api, /Zet eerst de bestaande Machinepark-database volledig over/);
});

test('Synology build wijst alleen centrale data naar PHP API', () => {
  assert.match(builder, /machinepark-data\.php/);
  assert.match(builder, /synology-local-data-v1/);
  const cmd = pkg.scripts.build;
  assert.ok(cmd.includes('python3 build-synology-local-data.py'));
  assert.ok(cmd.indexOf('python3 build-synology-local-data.py') > cmd.indexOf('python3 build-unified-work-layout.py'));
  assert.ok(cmd.indexOf('python3 scripts/check-inline-scripts.py') > cmd.indexOf('python3 build-synology-local-data.py'));
});


test('Synology data API accepteert gzip-gecomprimeerde centrale snapshots', () => {
  assert.match(api, /HTTP_CONTENT_ENCODING/);
  assert.match(api, /gzdecode/);
  assert.match(api, /gzip_unavailable/);
  assert.match(api, /payload_too_large/);
});
