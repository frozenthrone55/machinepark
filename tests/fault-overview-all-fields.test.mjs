import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const frontend = readFileSync(new URL('../fault-library.js', import.meta.url), 'utf8');
const buildJs = readFileSync(new URL('../assets/machinepark-build.js', import.meta.url), 'utf8');
const builtSource = `${index}\n${buildJs}`;
const css = readFileSync(new URL('../fault-library.css', import.meta.url), 'utf8');
const sw = readFileSync(new URL('../sw.js', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('storingenoverzicht gebruikt alle actuele centrale detailwaarden correct en cacheveilig', () => {
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

  const orderedSourceValues = [
    'code: overviewText(fault.code)',
    'name: overviewText(fault.name)',
    'category: overviewText(fault.category)',
    'brand: overviewText(fault.brand)',
    'model: overviewText(fault.model)',
    'description: overviewText(fault.description)',
    'message: overviewText(fault.message)',
    'symptoms: overviewList(fault.symptoms)',
    'causes: overviewList(fault.causes)',
    'solution1: overviewText(fault.solution1)',
    'solution2: overviewText(fault.solution2)',
    'solutions: overviewList(fault.solutions)',
    'notes: overviewText(fault.notes)',
    'active: fault.active !== false',
  ];
  let previous = -1;
  for (const value of orderedSourceValues) {
    const position = overviewBlock.indexOf(value, previous + 1);
    assert.ok(position > previous, `${value} ontbreekt of staat in de verkeerde overzichtsmapping`);
    previous = position;
  }

  const orderedRenderedValues = [
    'overview.code', 'overview.name', 'overview.category', 'overview.brand', 'overview.model',
    'overview.description', 'overview.message', 'overview.symptoms', 'overview.causes',
    'overview.solution1', 'overview.solution2', 'overview.solutions', 'overview.notes', 'overview.active',
  ];
  previous = -1;
  for (const value of orderedRenderedValues) {
    const position = overviewBlock.indexOf(value, previous + 1);
    assert.ok(position > previous, `${value} ontbreekt of staat in de verkeerde overzichtskolom`);
    previous = position;
  }
  assert.match(frontend, /colspan="15"/);

  assert.match(frontend, /machinepark-fault-overview-live-sync-v1/);
  assert.match(frontend, /window\.machineparkSyncFaultOverview = syncFaultOverviewFromCentral/);
  assert.match(frontend, /faultOverviewSyncing = loadFaultLibrary\(true\)/);
  assert.match(frontend, /if \(state\.view === 'faults'\) \{\s*renderFaultLibrary\(\);\s*syncFaultOverviewFromCentral\(\)\.catch\(\(\) => \{\}\);/s);
  assert.match(frontend, /refresh\.onclick = async \(\) => \{ await syncFaultOverviewFromCentral\(\); \}/);

  // De globale live-sync blijft dezelfde centrale storingenlijst continu verversen.
  assert.match(builtSource, /LIVE_SYNC_INTERVAL_MS = 3000/);
  assert.match(builtSource, /window\.machineparkLoadFaultLibrary\(true\)/);
  assert.match(builtSource, /window\.machineparkRenderFaultLibrary\(\)/);

  assert.match(css, /\.fault-table\{min-width:2600px\}/);
  assert.match(css, /\.fault-overview-cell\{/);
  const build = pkg.scripts.build;
  assert.ok(build.includes('python3 build-fault-overview-all-fields.py'));
  assert.ok(build.indexOf('build-fault-excel-fields-seed.py') < build.indexOf('build-fault-overview-all-fields.py'));
  assert.ok(build.indexOf('build-fault-overview-all-fields.py') < build.indexOf('build-auto-live-sync.py'));
  assert.equal(pkg.version, '1.68.9');

  // De definitieve Storingen-JS/CSS krijgen na alle buildstappen een inhoudshash.
  // Hierdoor kan een oude service worker nooit meer de oude 6-koloms JS combineren met nieuwe HTML.
  const faultJsUrl = /\/fault-library\.js\?v=1\.68\.9-[a-f0-9]{12}/;
  const faultCssUrl = /\/fault-library\.css\?v=1\.68\.9-[a-f0-9]{12}/;
  assert.match(index, faultJsUrl);
  assert.match(index, faultCssUrl);
  assert.doesNotMatch(index, /src="\/fault-library\.js"/);
  assert.doesNotMatch(index, /href="\/fault-library\.css"/);

  assert.match(sw, /const CACHE='machinepark-v1\.68\.9-assets-[a-f0-9]{12}'/);
  assert.match(sw, /'\/fault-library\.js\?v=1\.68\.9-[a-f0-9]{12}'/);
  assert.match(sw, /'\/fault-library\.css\?v=1\.68\.9-[a-f0-9]{12}'/);
  assert.doesNotMatch(sw, /machinepark-v1\.65-offline-first/);
  assert.match(sw, /keys\.filter\(k=>k!==CACHE\).*caches\.delete\(k\)/);
});