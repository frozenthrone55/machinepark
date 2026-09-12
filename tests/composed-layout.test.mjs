import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = path => fs.readFileSync(path, 'utf8');
const html = read('index.html');
const buildJs = read('assets/machinepark-build.js');
const built = `${html}\n${buildJs}`.replaceAll('\\"', '"');
const layoutPatch = read('build-composed-layout.py');
const searchPatch = read('build-composed-search-filter.py');

test('lange toestellenlijst bij nieuw samengesteld document is verticaal scrollbaar', () => {
  assert.ok(built.includes('composed-layout-v1'));
  assert.ok(built.includes('table-wrap composed-device-list-wrap'));
  assert.match(built, /\.composed-device-list-wrap\{max-height:min\(52vh,520px\);overflow:auto/);
  assert.match(layoutPatch, /overscroll-behavior:contain/);
});

test('zoekbalk voor toestellen staat direct vóór de juiste toestellentabel', () => {
  const search = built.indexOf('<label for="composedDeviceSearch">Zoek firma, locatie of toestel</label>');
  const table = built.indexOf('<div class="table-wrap composed-device-list-wrap">');
  assert.ok(search >= 0, 'toestelzoekbalk ontbreekt');
  assert.ok(table > search, 'toestelzoekbalk staat niet vóór de toestellentabel');
});

test('zoekbalk voor opgeslagen documenten staat boven de tabel met samengestelde documenten', () => {
  const search = built.indexOf('<label for="composedSavedSearch">Zoek in opgeslagen documenten</label>');
  const savedSection = built.indexOf('<h3>Samengestelde documenten</h3>');
  const table = built.indexOf('<table class="table" style="min-width:900px">', savedSection);
  assert.ok(savedSection >= 0, 'sectie Samengestelde documenten ontbreekt');
  assert.ok(search > savedSection, 'documentzoekbalk staat niet in de documentsectie');
  assert.ok(table > search, 'documentzoekbalk staat niet vóór de documententabel');
});

test('layout bouwt automatisch na de live zoekfilter zonder extra losse buildstap', () => {
  assert.match(searchPatch, /build-composed-layout\.py/);
  assert.match(searchPatch, /runpy\.run_path/);
});
