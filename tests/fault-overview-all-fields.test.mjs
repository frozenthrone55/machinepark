import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const frontend = readFileSync(new URL('../fault-library.js', import.meta.url), 'utf8');
const css = readFileSync(new URL('../fault-library.css', import.meta.url), 'utf8');
const sw = readFileSync(new URL('../sw.js', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('storingenoverzicht gebruikt alle detailwaarden correct en cacheveilig', () => {
  const tableStart = index.indexOf('<table class="table fault-table">');
  assert.ok(tableStart >= 0, 'storingenoverzicht-tabel ontbreekt');
  const tableEnd = index.indexOf('</table>', tableStart);
  assert.ok(tableEnd > tableStart, 'einde van storingenoverzicht-tabel ontbreekt');
  const faultTable = index.slice(tableStart, tableEnd);

  const headers = [
    'Code', 'Storing', 'Categorie', 'Merk', 'Model', 'Gedetailleerde omschrijving',
    'Melding', 'Symptomen', 'Mogelijke oorzaken', 'Oplossing 1', 'Oplossing 2',
    'Extra controle / oplossingen', 'Interne opmerkingen', 'Actief',
  ];
  for (const header of headers) assert.match(faultTable, new RegExp(`<th>${header.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}</th>`));
  assert.doesNotMatch(faultTable, /<th>Oplossing<\/th>/);

  const marker = '// machinepark-fault-overview-all-fields-v1';
  const markerPos = frontend.indexOf(marker);
  assert.ok(markerPos >= 0, 'marker van het volledige storingenoverzicht ontbreekt');
  const endPos = frontend.indexOf("    }).join('');", markerPos);
  assert.ok(endPos > markerPos, 'einde van het storingenoverzicht kon niet worden bepaald');
  const overviewBlock = frontend.slice(markerPos, endPos);

  const orderedValues = [
    'fault.code',
    'fault.name',
    'fault.category',
    'fault.brand',
    'fault.model',
    'overviewText(fault.description)',
    'overviewText(fault.message)',
    'overviewList(fault.symptoms)',
    'overviewList(fault.causes)',
    'overviewText(fault.solution1)',
    'overviewText(fault.solution2)',
    'overviewList(fault.solutions)',
    'overviewText(fault.notes)',
    'fault.active',
  ];
  let previous = -1;
  for (const value of orderedValues) {
    const position = overviewBlock.indexOf(value, previous + 1);
    assert.ok(position > previous, `${value} ontbreekt of staat in de verkeerde overzichtskolom`);
    previous = position;
  }
  assert.match(frontend, /colspan="15"/);

  assert.match(css, /\.fault-table\{min-width:2600px\}/);
  assert.match(css, /\.fault-overview-cell\{/);
  const build = pkg.scripts.build;
  assert.ok(build.includes('python3 build-fault-overview-all-fields.py'));
  assert.ok(build.indexOf('build-fault-excel-fields-seed.py') < build.indexOf('build-fault-overview-all-fields.py'));
  assert.ok(build.indexOf('build-fault-overview-all-fields.py') < build.indexOf('build-manual-library.py'));
  assert.equal(pkg.version, '1.68.9');

  assert.match(sw, /const CACHE='machinepark-v1\.68\.9-assets-[a-f0-9]{12}'/);
  assert.match(sw, /'\/fault-library\.js'/);
  assert.doesNotMatch(sw, /machinepark-v1\.65-offline-first/);
  assert.match(sw, /keys\.filter\(k=>k!==CACHE\).*caches\.delete\(k\)/);
});
