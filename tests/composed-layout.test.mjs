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

test('nieuw samengesteld document heeft apart zoekveld en apart naamveld naast elkaar', () => {
  const search = layoutPatch.indexOf('<label for="composedDeviceSearch">Naam toestel / firma voor nieuw document</label>');
  const name = layoutPatch.indexOf('<label for="composedDocumentName">Naam nieuw document</label>', search);
  const table = layoutPatch.indexOf('<div class="table-wrap composed-device-list-wrap">', name);
  assert.ok(search >= 0, 'zoekveld voor toestel / firma ontbreekt');
  assert.ok(name > search, 'naamveld voor nieuw document staat niet naast/na het zoekveld');
  assert.ok(table > name, 'toestellentabel staat niet onder beide velden');
  assert.match(searchPatch, /const composedDeviceSearch=document\.getElementById\('composedDeviceSearch'\)/);
  assert.match(searchPatch, /composedDeviceSearch\?\.addEventListener\('input',syncComposedDeviceSearch\)/);
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
