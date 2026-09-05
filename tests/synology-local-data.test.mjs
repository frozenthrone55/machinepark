import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const api = readFileSync(new URL('../synology/api/machinepark-data.php', import.meta.url), 'utf8');
const builder = readFileSync(new URL('../build-synology-local-data.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('lokale data API schrijft buiten de webroot', () => {
  assert.match(api, /\/volume1\/MachineparkData\/data/);
  assert.match(api, /state-v1\.json/);
  assert.match(api, /state-v1\.lock/);
});

test('lokale data API is tijdens migratie beperkt tot lokale netwerkadressen', () => {
  assert.match(api, /mp_require_local_network\(\)/);
  assert.match(api, /192\.168\./);
  assert.match(api, /172\.16\.0\.0/);
  assert.match(api, /synology-local-only/);
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
