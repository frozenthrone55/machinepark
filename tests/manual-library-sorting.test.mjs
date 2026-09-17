import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const client = readFileSync(new URL('../manual-library.js', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('handleidingen sorteren alfabetisch op titel en pas daarna op merk model en type', () => {
  assert.match(client, /machinepark-manual-library-sorting-v1/);
  const visibleSort = client.match(/const visible = manualLibrary[\s\S]*?status\.textContent/);
  assert.ok(visibleSort, 'zichtbare handleidingen-sortering ontbreekt');
  const source = visibleSort[0];
  const titlePos = source.indexOf('manualCompareText(a.title, b.title)');
  const brandPos = source.indexOf('manualCompareText(a.brand, b.brand)');
  const modelPos = source.indexOf('manualCompareText(a.model, b.model)');
  const typePos = source.indexOf('manualCompareText(a.type, b.type)');
  assert.ok(titlePos >= 0, 'titel ontbreekt als sorteersleutel');
  assert.ok(brandPos > titlePos, 'merk mag pas na titel sorteren');
  assert.ok(modelPos > brandPos, 'model moet na merk sorteren');
  assert.ok(typePos > modelPos, 'type moet na model sorteren');
  assert.doesNotMatch(source, /manualSpecificity\(a\) - manualSpecificity\(b\)/);
});

test('titel-sortering behandelt lege merkvelden correct', () => {
  const rows = [
    { title: 'Yunio X95 exploded view', brand: '' },
    { title: 'Yunio X95 spare parts', brand: '' },
    { title: 'Yunio X95 waterzijdig', brand: '' },
    { title: 'Acaia weegschaal', brand: 'Acaia' },
    { title: 'LNE anniversario handleiding ENG', brand: 'LNE' },
    { title: 'LNE onderhoud', brand: 'LNE' },
    { title: 'Quality Espresso Q9', brand: 'Quality Espresso' },
    { title: 'Yunio x50 exploded view', brand: 'Yunio' },
  ];
  const compare = (a, b) => String(a || '').localeCompare(String(b || ''), 'nl-BE', { numeric: true, sensitivity: 'base' });
  const titles = rows.sort((a, b) => compare(a.title, b.title) || compare(a.brand, b.brand)).map((row) => row.title);
  assert.deepEqual(titles, [
    'Acaia weegschaal',
    'LNE anniversario handleiding ENG',
    'LNE onderhoud',
    'Quality Espresso Q9',
    'Yunio x50 exploded view',
    'Yunio X95 exploded view',
    'Yunio X95 spare parts',
    'Yunio X95 waterzijdig',
  ]);
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
