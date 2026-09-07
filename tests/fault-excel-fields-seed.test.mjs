import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { LATTIZ2_FAULT_SEED_2026_09_02 } from '../netlify/functions/_shared/lattiz2-fault-seed.mjs';

const patch = await readFile(new URL('../build-fault-excel-fields-seed.py', import.meta.url), 'utf8');
const pkg = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'));

test('aangeleverde Excel bevat 191 storingsregels in de ingebouwde seed', () => {
  assert.equal(LATTIZ2_FAULT_SEED_2026_09_02.length, 191);
  const first = LATTIZ2_FAULT_SEED_2026_09_02[0];
  assert.equal(first.code, '1200 // No error code');
  assert.equal(first.category, 'Activation');
  assert.equal(first.brand, 'lattiz 2');
  assert.equal(first.name, 'Trial period expired');
  assert.match(first.message, /trial period is expired/i);
  assert.equal(first.solution1, '- None');
  assert.equal(first.solution2, '- Activate machine');
});

test('dubbele code 4170 uit verschillende categorieën blijft als twee Excel-regels behouden', () => {
  const rows = LATTIZ2_FAULT_SEED_2026_09_02.filter((fault) => fault.code === '4170 // No error code' && fault.name === 'LMI state changed');
  assert.equal(rows.length, 2);
  assert.deepEqual(new Set(rows.map((fault) => fault.category)), new Set(['General', 'BiB / RFID']));
});

test('Storingen krijgt aparte velden Melding, Oplossing 1 en Oplossing 2', () => {
  assert.match(patch, /name=\\"message\\"/);
  assert.match(patch, /name=\\"solution1\\"/);
  assert.match(patch, /name=\\"solution2\\"/);
  assert.match(patch, /message: cleanText\(fault\?\.message/);
  assert.match(patch, /solution1: cleanText\(fault\?\.solution1/);
  assert.match(patch, /solution2: cleanText\(fault\?\.solution2/);
  assert.match(patch, /proposedSolutions/);
});

test('Excel-indeling herkent Algemene omschrijving, gedetailleerde omschrijving en Merk model', () => {
  assert.match(patch, /Algemene omschrijving/);
  assert.match(patch, /gedetailleerde omschrijving/);
  assert.match(patch, /Merk \/ model/);
  assert.match(patch, /Excel UI sleutel inclusief categorie/);
  assert.match(patch, /Excel-import sleutel inclusief categorie/);
});

test('centrale seed draait na de eerdere leegmaak en vóór handleidingen/offline modules', () => {
  const build = pkg.scripts.build;
  const clearAll = build.indexOf('build-fault-clear-all.py');
  const seed = build.indexOf('build-fault-excel-fields-seed.py');
  const manuals = build.indexOf('build-manual-library.py');
  const offline = build.indexOf('build-offline-first.py');
  assert.ok(clearAll >= 0 && seed > clearAll && manuals > seed && offline > seed);
  assert.equal(build.split('build-fault-excel-fields-seed.py').length - 1, 1);
  assert.match(pkg.scripts['check:functions'], /lattiz2-fault-seed\.mjs/);
  assert.equal(pkg.version, '1.68.9');
});
