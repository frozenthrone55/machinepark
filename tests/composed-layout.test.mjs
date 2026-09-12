import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = path => fs.readFileSync(path, 'utf8');
const layoutPatch = read('build-composed-layout.py');
const searchPatch = read('build-composed-search-filter.py');

test('lange toestellenlijst bij nieuw samengesteld document is verticaal scrollbaar', () => {
  assert.match(layoutPatch, /table-wrap composed-device-list-wrap/);
  assert.match(layoutPatch, /\.composed-device-list-wrap\{max-height:min\(52vh,520px\);overflow:auto;overscroll-behavior:contain\}/);
  assert.match(layoutPatch, /@media\(max-width:760px\)\{\.composed-device-list-wrap\{max-height:55vh\}/);
});

test('zoekbalk voor toestellen staat direct vóór de juiste toestellentabel', () => {
  const search = layoutPatch.indexOf('<label for="composedDeviceSearch">Zoek firma, locatie of toestel</label>');
  const table = layoutPatch.indexOf('<div class="table-wrap composed-device-list-wrap">', search);
  assert.ok(search >= 0, 'toestelzoekbalk ontbreekt');
  assert.ok(table > search, 'toestelzoekbalk staat niet vóór de toestellentabel');
});

test('zoekbalk voor opgeslagen documenten staat boven de tabel met samengestelde documenten', () => {
  const section = layoutPatch.indexOf('<h3>Samengestelde documenten</h3>');
  const search = layoutPatch.indexOf('<label for="composedSavedSearch">Zoek in opgeslagen documenten</label>', section);
  const table = layoutPatch.indexOf('<table class="table" style="min-width:900px">', search);
  assert.ok(section >= 0, 'sectie Samengestelde documenten ontbreekt');
  assert.ok(search > section, 'documentzoekbalk staat niet in de documentsectie');
  assert.ok(table > search, 'documentzoekbalk staat niet vóór de documententabel');
});

test('layout heeft eigen buildvalidatie en bouwt automatisch na live zoekfilter', () => {
  assert.match(layoutPatch, /MARKER = 'data-machinepark-build-fix="composed-layout-v1"'/);
  assert.match(layoutPatch, /for needle in required:/);
  assert.match(searchPatch, /build-composed-layout\.py/);
  assert.match(searchPatch, /runpy\.run_path/);
});
