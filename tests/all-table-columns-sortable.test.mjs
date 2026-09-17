import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const html = () => fs.readFileSync(path.join(root, 'index.html'), 'utf8');

test('elke kolom van elke Machinepark-tabel is sorteerbaar in beide richtingen', () => {
  const source = html();
  const marker = 'data-machinepark-build-fix="all-table-columns-sortable-v1"';
  assert.match(source, new RegExp(marker));
  assert.match(source, /data-machinepark-table-sort-style="v1"/);

  const start = source.indexOf(`<script ${marker}>`);
  const end = source.indexOf('</script>', start);
  assert.ok(start >= 0 && end > start, 'los universeel sorteerscript ontbreekt');
  const block = source.slice(start, end);

  // Alle .table-tabellen en letterlijk iedere th worden geregistreerd.
  assert.match(block, /root\?\.matches\?\.\('\.table'\)/);
  assert.match(block, /root\.querySelectorAll\('\.table'\)/);
  assert.match(block, /table\.querySelectorAll\('thead th'\)/);
  assert.match(block, /th\.classList\.add\('machinepark-universal-sortable'\)/);
  assert.match(block, /th\.removeAttribute\('data-device-sort'\)/);
  assert.match(block, /th\.dataset\.machineparkSortIndex = String\(column\)/);

  // Interactieve en visuele cellen krijgen een echte sorteerwaarde.
  assert.match(block, /input\[type="checkbox"\],input\[type="radio"\]/);
  assert.match(block, /cell\.querySelector\('select'\)/);
  assert.match(block, /input:not\(\[type="hidden"\]\),textarea/);
  assert.match(block, /image\?\.alt \|\| image\?\.title/);

  // Datum, getal en beide sorteerrichtingen worden ondersteund.
  assert.match(block, /const dateTime = raw\.match/);
  assert.match(block, /const iso = raw\.match/);
  assert.match(block, /dir === 'desc' \? -result : result/);
  assert.match(block, /machineparkSortDir === 'asc' \? 'desc' : 'asc'/);

  // De losse laag onderschept de oude tabelhandlers zonder bestaande modules te herschrijven.
  assert.match(block, /document\.addEventListener\('click'/);
  assert.match(block, /event\.stopImmediatePropagation\(\)/);
  assert.match(block, /}, true\);/);

  // Dynamische tabellen en her-renders worden automatisch opnieuw verwerkt,
  // terwijl de observer tijdens het fysiek hersorteren gepauzeerd wordt.
  assert.match(block, /new MutationObserver\(queueRefresh\)/);
  assert.match(block, /observer\.disconnect\(\)/);
  assert.match(block, /tables\(document\)\.forEach\(applyCurrent\)/);
  assert.match(block, /window\.machineparkUniversalTableSorting/);

  // Geen uitzonderingslijst voor lege/action/device-kolommen in de nieuwe laag.
  assert.doesNotMatch(block, /details/i);
  assert.doesNotMatch(block, /bewerk/i);
  assert.doesNotMatch(block, /no-sort/);
  assert.doesNotMatch(block, /table:not\(\.device-table\)/);
});
