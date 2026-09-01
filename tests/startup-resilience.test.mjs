import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const offline = readFileSync(new URL('../offline-first.js', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('centrale fout tijdens eerste ophaling blokkeert lokale Machinepark-data niet', () => {
  assert.match(offline, /machinepark-startup-central-fallback-v1/);
  assert.match(offline, /remote = \{ exists: false, offline: true/);

  const start = offline.indexOf("setCentralSyncStatus('☁ Centrale gegevens ophalen…', 'busy');");
  const end = offline.indexOf('if (remote?.exists && remote.data)', start);
  assert.ok(start >= 0 && end > start, 'centrale opstartsectie ontbreekt');
  const section = offline.slice(start, end);
  assert.doesNotMatch(section, /if \(!isNetworkFailure\(error\)\) throw error/);
});

test('fallback behoudt normale lokale opstart en latere synchronisatie', () => {
  assert.match(offline, /bind\(\);\s*await refresh\(\);\s*centralSync\.enabled = true;\s*startCentralPolling\(\);/);
  assert.match(offline, /window\.addEventListener\('online'/);
});

test('Clerk-token wordt bij online opstart kort herprobeerd', () => {
  assert.match(offline, /machinepark-central-auth-retry-v1/);
  assert.match(offline, /attempt < 5/);
  assert.match(offline, /geen actieve clerk-sessie/i);
  assert.match(offline, /180 \+ attempt \* 220/);
});

test('echte centrale foutoorzaak wordt zichtbaar zonder lokale data te wissen', () => {
  assert.match(offline, /machineparkLastCentralStartupError/);
  assert.match(offline, /lokale gegevens actief/);
  assert.match(offline, /startupError/);
});

test('startup-resilience en auth-retry blijven aanwezig in versie 1.68.5', () => {
  assert.equal(packageJson.version, '1.68.5');
  assert.match(packageJson.scripts.build, /build-startup-resilience\.py/);
  assert.match(packageJson.scripts.build, /build-central-auth-retry\.py/);
  assert.match(packageJson.scripts.build, /build-central-access-etag\.py/);
});
