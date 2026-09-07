import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const js = readFileSync(new URL('../assets/machinepark-build.js', import.meta.url), 'utf8');

test('nieuwe locatiebeurt krijgt geen algemene werkbon buiten de machines', () => {
  assert.match(js, /if \(!existingId\) return;/);
});

test('dynamisch getoonde onderhoudsmachines krijgen ieder een eigen werkbon', () => {
  assert.match(js, /new MutationObserver\(\(\) => attachMaintenanceWorkOrders\(id \|\| ''\)\)/);
  assert.match(js, /card\.querySelector\('\.maintenance-machine-fields'\)/);
  assert.match(js, /fields\.insertBefore\(editor, photoEditor\)/);
});

test('werkbon wordt per machine gekoppeld bij opslaan van meerdere onderhouden', () => {
  assert.match(js, /candidate\.dataset\?\.maintenanceDevice === item\.deviceId/);
  assert.match(js, /return editor \? \{ \.\.\.item, workOrder: collectWorkOrder\(editor\) \} : item/);
});
