import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const html = () => fs.readFileSync(path.join(root, 'index.html'), 'utf8');

test('elke kolom van elke Machinepark-tabel is sorteerbaar in beide richtingen', () => {
  const source = html();

  assert.match(source, /data-machinepark-build-fix="all-table-columns-sortable-v1"/);
  assert.match(source, /function allMachineparkTables\(root=document\)/);
  assert.match(source, /root\?\.matches\?\.\('\.table'\)/);
  assert.match(source, /root\.querySelectorAll\('\.table'\)/);
  assert.match(source, /th\.classList\.add\('table-sortable'\)/);
  assert.match(source, /th\.removeAttribute\('data-device-sort'\)/);
  assert.match(source, /th\.dataset\.tableSortIndex=String\(column\)/);

  // Ook interactieve/lege/action-kolommen moeten een echte sorteerwaarde krijgen.
  assert.match(source, /input\[type="checkbox"\]/);
  assert.match(source, /cell\.querySelector\('select'\)/);
  assert.match(source, /input:not\(\[type="hidden"\]\),textarea/);
  assert.match(source, /image\?\.alt\|\|image\?\.title/);

  // Richting moet bij iedere volgende klik omkeren en numeriek/datum-bewust blijven.
  assert.match(source, /previous==='asc'\?'desc':'asc'/);
  assert.match(source, /return dir==='desc'\?-cmp:cmp/);
  assert.match(source, /dateTime=raw\.match/);
  assert.match(source, /if\(\/\^-\?\\d\+/);

  // Dynamische tabellen en her-renders moeten dezelfde gekozen sortering behouden.
  assert.match(source, /new MutationObserver\(refreshSortableTables\)/);
  assert.match(source, /reapplyGenericTableSorts\(document\)/);
  assert.match(source, /const genericSortHead=e\.target\.closest\('\.table th\.table-sortable'\)/);

  // Oude uitzonderingen zijn niet meer toegestaan.
  assert.doesNotMatch(source, /root\.querySelectorAll\('\.table:not\(\.device-table\)'\)/);
  assert.doesNotMatch(source, /text==='details'/);
  assert.doesNotMatch(source, /text==='bewerk'/);
  assert.doesNotMatch(source, /th\.classList\.contains\('no-sort'\)/);
  assert.doesNotMatch(source, /const genericSortHead=e\.target\.closest\('\.table:not\(\.device-table\) th\.table-sortable'\)/);
});
