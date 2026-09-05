import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const api = readFileSync(new URL('../synology/api/fault-library.php', import.meta.url), 'utf8');
const builder = readFileSync(new URL('../build-synology-local-faults.py', import.meta.url), 'utf8');
const exporter = readFileSync(new URL('../scripts/export-synology-fault-seed.mjs', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('lokale storingen worden buiten webroot opgeslagen met lock en backups', () => {
  assert.match(api, /\/volume1\/MachineparkData\/data\/fault-library-v1\.json/);
  assert.match(api, /fault-library-v1\.lock/);
  assert.match(api, /MP_FAULT_BACKUPS/);
  assert.match(api, /LOCK_EX/);
});

test('lokale storings-API vereist Synology sessie en rechten', () => {
  assert.match(api, /mp_auth_require_user/);
  assert.match(api, /view\.faults/);
  assert.match(api, /faults\.manage/);
  assert.match(api, /mp_auth_is_local_ip/);
});

test('lokale storingen ondersteunen GET save delete en etag conflictcontrole', () => {
  assert.match(api, /save-fault/);
  assert.match(api, /delete-fault/);
  assert.match(api, /409/);
  assert.match(api, /fault_etag/);
});

test('storingsseed bevat exact de bestaande Lattiz 2 dataset', () => {
  assert.match(exporter, /LATTIZ2_FAULT_SEED_2026_09_02/);
  assert.match(exporter, /length !== 191/);
  assert.match(exporter, /fault-seed\.json/);
});

test('Synology build koppelt fault library lokaal en exporteert seed', () => {
  assert.match(builder, /synology\/api\/fault-library\.php/);
  assert.match(builder, /machinepark-synology-local-faults-v1/);
  const cmd = pkg.scripts.build;
  assert.ok(cmd.includes('node scripts/export-synology-fault-seed.mjs'));
  assert.ok(cmd.includes('python3 build-synology-local-faults.py'));
  assert.ok(cmd.indexOf('python3 build-synology-local-faults.py') < cmd.indexOf('python3 scripts/extract-build-assets.py'));
});
