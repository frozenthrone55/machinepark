import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const builder = readFileSync(new URL('../build-synology-runtime-paths.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('Synology runtime path builder corrigeert alle belangrijke root-assets', () => {
  for (const name of [
    'machinepark-logo.svg',
    'fault-library',
    'manual-library',
    'service-visits',
    'offline-first.js',
    'assets/machinepark-build',
  ]) {
    assert.ok(builder.includes(name));
  }
  assert.match(builder, /\\.\\/index\\.html/);
  assert.match(builder, /start_url/);
  assert.match(builder, /scope/);
});

test('runtime path builder draait na asset-extractie', () => {
  const cmd = pkg.scripts.build;
  assert.ok(cmd.includes('python3 scripts/extract-build-assets.py'));
  assert.ok(cmd.includes('python3 build-synology-runtime-paths.py'));
  assert.ok(cmd.indexOf('python3 build-synology-runtime-paths.py') > cmd.indexOf('python3 scripts/extract-build-assets.py'));
  assert.ok(cmd.indexOf('node --check assets/machinepark-build.js') > cmd.indexOf('python3 build-synology-runtime-paths.py'));
});
