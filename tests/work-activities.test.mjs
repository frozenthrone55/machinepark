import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const patch = readFileSync(new URL('../build-work-activities.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('Onderhoud en Depannages worden één navigatietab Werkzaamheden', () => {
  assert.match(patch, /maintenanceNav\.dataset\.view = 'work'/);
  assert.match(patch, /Werkzaamheden/);
  assert.match(patch, /breakdownNav\.style\.display = 'none'/);
  assert.match(patch, /workView\.id = 'view-work'/);
  assert.match(patch, /if \(view === 'maintenance' \|\| view === 'breakdowns' \|\| view === 'work'\)/);
});

test('Werkzaamheden heeft twee aparte registratieknoppen', () => {
  assert.match(patch, /id=\"workAddMaintenance\"/);
  assert.match(patch, /\+ Onderhoud registreren/);
  assert.match(patch, /id=\"workAddBreakdown\"/);
  assert.match(patch, /\+ Depannage toevoegen/);
  assert.match(patch, /openMaintenance\(\)/);
  assert.match(patch, /openBreakdown\(\)/);
});

test('historiek combineert onderhoud en depannages chronologisch met extra Type-kolom', () => {
  assert.match(patch, /<th>Type<\/th>/);
  assert.match(patch, /badge blue\">Onderhoud/);
  assert.match(patch, /badge danger\">Depannage/);
  assert.match(patch, /state\.maintenance/);
  assert.match(patch, /state\.breakdowns/);
  assert.match(patch, /\.sort\(\(a,b\) => String\(b\.moment/);
  assert.match(patch, /data-maintenance-details/);
  assert.match(patch, /data-edit-breakdown/);
});

test('concepten blijven apart herkenbaar maar staan in Werkzaamheden', () => {
  assert.match(patch, /workDraftPanels/);
  assert.match(patch, /Onderhoudsconcepten/);
  assert.match(patch, /Depannageconcepten/);
  assert.match(patch, /item\?\.isDraft === true/);
});

test('Werkzaamheden respecteert bestaande afzonderlijke rechten', () => {
  assert.match(patch, /view\.maintenance/);
  assert.match(patch, /view\.breakdowns/);
  assert.match(patch, /maintenance\.add/);
  assert.match(patch, /breakdowns\.add/);
});

test('Werkzaamheden bouwt na cross-device concepten en vóór offline-first', () => {
  const chain = packageJson.scripts.build;
  assert.equal(packageJson.version, '1.68.9');
  assert.ok(chain.indexOf('build-service-draft-cross-device.py') < chain.indexOf('build-work-activities.py'));
  assert.ok(chain.indexOf('build-work-activities.py') < chain.indexOf('build-offline-first.py'));
});
