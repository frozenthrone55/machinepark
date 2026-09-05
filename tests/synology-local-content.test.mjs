import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const manual = readFileSync(new URL('../synology/api/manual-library.php', import.meta.url), 'utf8');
const work = readFileSync(new URL('../synology/api/work-order-templates.php', import.meta.url), 'utf8');
const fault = readFileSync(new URL('../synology/api/fault-library.php', import.meta.url), 'utf8');
const builder = readFileSync(new URL('../build-synology-local-content.py', import.meta.url), 'utf8');

test('handleidingen slaan PDF en metadata lokaal op', () => {
  assert.match(manual, /\/volume1\/MachineparkData\/manuals/);
  assert.match(manual, /manual-library-v1\.json/);
  assert.match(manual, /upload-chunk/);
  assert.match(manual, /finalize-upload/);
  assert.match(manual, /%PDF-/);
  assert.match(manual, /delete-manual/);
});

test('werkbonsjablonen worden lokaal beheerd', () => {
  assert.match(work, /work-order-templates-v1\.json/);
  assert.match(work, /save-template/);
  assert.match(work, /delete-template/);
  assert.match(work, /MP_WORK_ORDER_LOCK/);
});

test('storingen ondersteunen lokale Excel-import en veilige undo', () => {
  assert.match(fault, /import-faults/);
  assert.match(fault, /undo-last-import/);
  assert.match(fault, /MP_FAULT_IMPORT_UNDO/);
  assert.match(fault, /afterEtag/);
});

test('content builder verwijst niet meer naar Netlify endpoints', () => {
  assert.match(builder, /synology\/api\/manual-library\.php/);
  assert.match(builder, /synology\/api\/work-order-templates\.php/);
  assert.match(builder, /synology\/api\/fault-library\.php/);
});


test('Handleidingen krijgen expliciete lokale rolrechten', () => {
  const roleLib = readFileSync(new URL('../synology/api/_role-lib.php', import.meta.url), 'utf8');
  assert.match(roleLib, /view\.manuals/);
  assert.match(roleLib, /manuals\.manage/);
  assert.match(manual, /view\.manuals/);
  assert.match(manual, /manuals\.manage/);
});
