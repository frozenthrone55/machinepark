import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const client = readFileSync(new URL('../manual-library.js', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('handleidingen sorteren stabiel op merk model type en titel', () => {
  assert.match(client, /machinepark-manual-library-sorting-v1/);
  assert.match(client, /manualCompareText\(a\.brand, b\.brand\)/);
  assert.match(client, /manualCompareText\(a\.model, b\.model\)/);
  assert.match(client, /manualCompareText\(a\.type, b\.type\)/);
  assert.match(client, /manualCompareText\(a\.title, b\.title\)/);
  const visibleSort = client.match(/const visible = manualLibrary[\s\S]*?status\.textContent/);
  assert.ok(visibleSort, 'zichtbare handleidingen-sortering ontbreekt');
  assert.doesNotMatch(visibleSort[0], /manualSpecificity\(a\) - manualSpecificity\(b\)/);
});

test('handleidingfilters vergelijken genormaliseerd en tonen geen bijna-dubbele waarden', () => {
  assert.match(client, /function manualValueEquals\(a, b\)/);
  assert.match(client, /manualNorm\(a\) === manualNorm\(b\)/);
  assert.match(client, /const unique = new Map\(\)/);
  assert.match(client, /manualValueEquals\(manual\.brand, selectedBrand\)/);
  assert.match(client, /manualValueEquals\(manual\.model, selectedModel\)/);
  assert.match(client, /manualValueEquals\(manual\.type, selectedType\)/);
});

test('sorteerfix draait voor de 20 MB hash zodat browsers de gewijzigde module ophalen', () => {
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-manual-library-sorting\.py/);
  assert.ok(chain.indexOf('build-manual-native-sync.py') < chain.indexOf('build-manual-library-sorting.py'));
  assert.ok(chain.indexOf('build-manual-library-sorting.py') < chain.indexOf('build-manual-pdf-20mb.py'));
});
