import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-auto-live-sync.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('zichtbare online clients controleren automatisch om de paar seconden', () => {
  assert.match(build, /auto-live-sync-v1/);
  assert.match(build, /LIVE_SYNC_INTERVAL_MS = 3000/);
  assert.match(build, /setInterval\(machineparkLiveSyncNow, LIVE_SYNC_INTERVAL_MS\)/);
  assert.match(build, /document\.visibilityState === 'hidden'/);
});

test('live sync ververst hoofddata storingen en handleidingen', () => {
  assert.match(build, /machineparkSyncOnlineNow\(\{ quiet: true \}\)/);
  assert.match(build, /machineparkLoadFaultLibrary\(true\)/);
  assert.match(build, /machineparkRenderFaultLibrary\(\)/);
  assert.match(build, /machineparkLoadManualLibrary\(true\)/);
  assert.match(build, /machineparkRenderManualLibrary\(\)/);
});

test('reconnect focus en terugkeren naar tab verversen onmiddellijk', () => {
  assert.match(build, /window\.addEventListener\('online'/);
  assert.match(build, /window\.addEventListener\('focus'/);
  assert.match(build, /document\.addEventListener\('visibilitychange'/);
});

test('versie 1.68.9 bouwt live sync na drift recovery', () => {
  assert.equal(packageJson.version, '1.68.9');
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-auto-live-sync\.py/);
  assert.ok(chain.indexOf('build-sync-drift-recovery.py') < chain.indexOf('build-auto-live-sync.py'));
  assert.ok(chain.indexOf('build-auto-live-sync.py') < chain.indexOf('scripts/extract-build-assets.py'));
});
