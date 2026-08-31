import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const offline = readFileSync(new URL('../offline-first.js', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('centrale fout tijdens eerste ophaling blokkeert lokale Machinepark-data niet', () => {
  assert.match(offline, /machinepark-startup-central-fallback-v1/);
  assert.match(offline, /Centrale synchronisatie tijdelijk niet beschikbaar · lokaal gestart/);
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

test('startup-resilience buildstap is onderdeel van versie 1.67.1', () => {
  assert.equal(packageJson.version, '1.67.1');
  assert.match(packageJson.scripts.build, /build-startup-resilience\.py/);
});
