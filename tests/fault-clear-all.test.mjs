import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-fault-clear-all.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('storingsbibliotheek wordt eenmalig volledig leeggemaakt', () => {
  assert.match(build, /fault-clear-all-v1/);
  assert.match(build, /applyOneTimeClearAllFaults/);
  assert.match(build, /\{ version: 1, faults: \[\] \}/);
  assert.match(build, /remainingCount: 0/);
  assert.match(build, /volledig leeggemaakt/);
});

test('de lege centrale lijst wordt ook naar de offline storingscache geschreven', () => {
  assert.match(build, /machinepark-fault-cache-reconnect-sync-v1/);
  assert.match(build, /window\.addEventListener\('online'/);
  assert.match(build, /loadFaultLibrary\(true\)/);
  assert.match(build, /writeFaultCache/);
});

test('definitieve leegmaak draait na eerdere gerichte opschoningen', () => {
  assert.equal(packageJson.version, '1.68.7');
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-fault-clear-all\.py/);
  assert.ok(chain.indexOf('build-fault-keep-only-waterselector.py') < chain.indexOf('build-fault-clear-all.py'));
  assert.ok(chain.indexOf('build-fault-clear-all.py') < chain.indexOf('build-offline-first.py'));
});
