import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const patch = readFileSync(new URL('../build-manual-native-sync.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('handleidingen krijgen native kijk- en beheerrechten zoals storingen', () => {
  assert.match(patch, /key: 'view\.manuals'/);
  assert.match(patch, /key: 'manuals\.manage'/);
  assert.match(patch, /view\.faults','view\.manuals','view\.parts/);
  assert.match(patch, /access\?\.permissions\?\.\['view\.manuals'\]/);
  assert.match(patch, /access\?\.permissions\?\.\['manuals\.manage'\]/);
});

test('online handleidingen verversen centraal terwijl offline cache bruikbaar blijft', () => {
  assert.match(patch, /manualLibraryLoaded && navigator\.onLine === false/);
  assert.match(patch, /window\.addEventListener\('online'/);
  assert.match(patch, /loadManualLibrary\(true\)/);
  assert.match(patch, /writeManualCache/);
});

test('handleidingen staan in normale schermvolgorde en runtime krijgt cache-busting', () => {
  assert.match(patch, /'faults','manuals','parts'/);
  assert.match(patch, /hashlib\.sha256/);
  assert.match(patch, /manual-library\\\.js\(\?:\\\?v=/);
});

test('native handleidingensync bouwt na bibliotheek en voor offline-first', () => {
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-manual-native-sync\.py/);
  assert.ok(chain.indexOf('build-manual-library.py') < chain.indexOf('build-manual-native-sync.py'));
  assert.ok(chain.indexOf('build-manual-native-sync.py') < chain.indexOf('build-offline-first.py'));
});
