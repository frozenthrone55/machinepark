import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const patch = readFileSync(new URL('../build-breakdown-work-orders.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('depannage krijgt dezelfde werkboneditor per toestel als onderhoud', () => {
  assert.match(patch, /attachBreakdownWorkOrders/);
  assert.match(patch, /machineparkMakeWorkOrderEditor/);
  assert.match(patch, /data-breakdown-device|breakdownDevice/);
  assert.match(patch, /breakdown-machine-card/);
  assert.match(patch, /baseSetBreakdownMachineEnabledForWorkOrders/);
});

test('werkbon wordt bij enkelvoudige en meervoudige depannage opgeslagen', () => {
  assert.match(patch, /basePutBreakdownForWorkOrders/);
  assert.match(patch, /basePutManyBreakdownForWorkOrders/);
  assert.match(patch, /storeName === 'breakdowns'/);
  assert.match(patch, /workOrder: window\.machineparkCollectWorkOrder\(editor\)/);
});

test('verplichte werkbonvelden worden voor voorraadmutatie gecontroleerd', () => {
  assert.match(patch, /installBreakdownWorkOrderValidation/);
  assert.match(patch, /addEventListener\('submit'/);
  assert.match(patch, /stopImmediatePropagation/);
  assert.match(patch, /validateBreakdownWorkOrders/);
});

test('depannagewerkbon verschijnt in details tijdlijn en bestaande serviceprint', () => {
  assert.match(patch, /baseShowBreakdownDetailsForWorkOrders/);
  assert.match(patch, /Werkbon<\/label>/);
  assert.match(patch, /workOrderTimelineHtml\(b\.workOrder\)/);
  assert.match(patch, /machineparkWorkOrderDetailsHtml/);
});

test('depannageconcept bewaart herstelt en valideert werkbon', () => {
  assert.match(patch, /record\.workOrder = collectWorkOrderLoose/);
  assert.match(patch, /restoreWorkOrder\(card, item\.workOrder, enabled\); restoreFaultRef/);
  assert.match(patch, /selected\.forEach\(item => validateWorkOrder\(item\.workOrder\)\)/);
});

test('depannagewerkbon bouwt na serviceconcepten en voor samengestelde werkzaamheden', () => {
  const chain = packageJson.scripts.build;
  assert.equal(packageJson.version, '1.68.9');
  assert.ok(chain.includes('build-breakdown-work-orders.py'));
  assert.ok(chain.indexOf('build-service-draft-cross-device.py') < chain.indexOf('build-breakdown-work-orders.py'));
  assert.ok(chain.indexOf('build-breakdown-work-orders.py') < chain.indexOf('build-work-activities.py'));
});
