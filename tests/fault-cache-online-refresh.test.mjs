import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const faultJs = readFileSync(new URL('../fault-library.js', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('online storingscache wordt altijd centraal ververst', () => {
  assert.match(faultJs, /machinepark-fault-cache-online-refresh-v1/);
  assert.doesNotMatch(faultJs, /if \(!force && faultLibraryLoaded\) return faultLibrary;/);
  assert.match(faultJs, /if \(!force && faultLibraryLoaded && navigator\.onLine === false\) return faultLibrary;/);
  assert.match(faultJs, /await faultLibraryRequest\(\);/);
});

test('centrale lege lijst vervangt ook de offline storingscache', () => {
  assert.match(faultJs, /if \(Array\.isArray\(data\.faults\)\) faultLibrary = data\.faults;/);
  assert.match(faultJs, /await writeFaultCache\(\);/);
  assert.match(faultJs, /MachineparkFaultLibraryDB/);
});

test('online cache-refresh draait na de eenmalige leegmaak en voor offline-first', () => {
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-fault-cache-online-refresh\.py/);
  assert.ok(chain.indexOf('build-fault-clear-all.py') < chain.indexOf('build-fault-cache-online-refresh.py'));
  assert.ok(chain.indexOf('build-fault-cache-online-refresh.py') < chain.indexOf('build-offline-first.py'));
});
