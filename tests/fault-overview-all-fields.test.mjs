import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const frontend = readFileSync(new URL('../fault-library.js', import.meta.url), 'utf8');
const css = readFileSync(new URL('../fault-library.css', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('storingenoverzicht toont alle invulbare velden als kolommen', () => {
  const headers = [
    'Code', 'Storing', 'Categorie', 'Merk', 'Model', 'Gedetailleerde omschrijving',
    'Melding', 'Symptomen', 'Mogelijke oorzaken', 'Oplossing 1', 'Oplossing 2',
    'Extra controle / oplossingen', 'Interne opmerkingen', 'Actief',
  ];
  for (const header of headers) assert.match(index, new RegExp(`<th>${header.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}</th>`));
  assert.doesNotMatch(index, /<th>Oplossing<\/th>/);
});

test('overzichtsrij gebruikt alle bijhorende storingswaarden', () => {
  for (const value of [
    'fault.description', 'fault.message', 'fault.symptoms', 'fault.causes',
    'fault.solution1', 'fault.solution2', 'fault.solutions', 'fault.notes', 'fault.active',
  ]) assert.match(frontend, new RegExp(value.replace('.', '\\.')));
  assert.match(frontend, /machinepark-fault-overview-all-fields-v1/);
  assert.match(frontend, /colspan="15"/);
});

test('brede tabel blijft horizontaal bruikbaar en buildvolgorde is correct', () => {
  assert.match(css, /\.fault-table\{min-width:2600px\}/);
  assert.match(css, /\.fault-overview-cell\{/);
  const build = pkg.scripts.build;
  assert.ok(build.includes('python3 build-fault-overview-all-fields.py'));
  assert.ok(build.indexOf('build-fault-excel-fields-seed.py') < build.indexOf('build-fault-overview-all-fields.py'));
  assert.ok(build.indexOf('build-fault-overview-all-fields.py') < build.indexOf('build-manual-library.py'));
  assert.equal(pkg.version, '1.68.9');
});
