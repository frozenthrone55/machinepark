import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const endpoint = readFileSync(new URL('../netlify/functions/fault-library.mjs', import.meta.url), 'utf8');
const build = readFileSync(new URL('../build-fault-excel-import.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('Beheer bevat Excel-import en sjabloon voor storingen', () => {
  assert.match(build, /faultExcelImportCard/);
  assert.match(build, /Storingen uit Excel importeren/);
  assert.match(build, /Excel-sjabloon downloaden/);
  assert.match(build, /faultExcelFile/);
});

test('storingsimport ondersteunt de afgesproken kolommen en optionele storingscode', () => {
  for (const column of ['Storingscode','Storing','Categorie','Merk','Model','Omschrijving','Symptomen','Mogelijke oorzaken','Oplossingen','Opmerkingen','Actief']) {
    assert.ok(build.includes(column), `Ontbrekende Excel-kolom: ${column}`);
  }
  assert.match(build, /if \(name >= 0\)/);
  assert.match(build, /code: faultExcelColumn/);
  assert.match(build, /split\(\/\[;\\r\\n\]\+\//);
});

test('importpreview is niet-destructief en onderscheidt nieuw bijwerken ongewijzigd en fouten', () => {
  assert.match(build, /Niet-destructieve import/);
  assert.match(build, /Storingen die niet in dit bestand staan worden niet verwijderd/);
  assert.match(build, /action: 'add'/);
  assert.match(build, /action: 'update'/);
  assert.match(build, /action: 'same'/);
  assert.match(build, /errors\.push/);
});

test('server verwerkt een Excel-import atomair in één bibliotheekwrite', () => {
  assert.match(endpoint, /if \(action === 'import-faults'\)/);
  assert.match(endpoint, /const merged = \[\.\.\.config\.faults\]/);
  assert.match(endpoint, /faultImportKey/);
  assert.match(endpoint, /merged\.push\(fault\)/);
  assert.match(endpoint, /saveConfig\(store, \{ version: 1, faults: merged \}/);
  assert.match(endpoint, /writeImportAudit/);
});

test('versie 1.68.1 bouwt de storingsimport mee', () => {
  assert.equal(packageJson.version, '1.68.1');
  assert.match(packageJson.scripts.build, /build-fault-excel-import\.py/);
});
