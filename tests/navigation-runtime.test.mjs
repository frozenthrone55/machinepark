import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-navigation-runtime.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('navigatie-runtime houdt alle hoofdtabbladen bruikbaar', () => {
  for (const view of ['dashboard', 'devices', 'maintenance', 'breakdowns', 'parts', 'faults', 'manuals', 'settings']) {
    assert.ok(build.includes(`${view}: [`), `metadata ontbreekt voor ${view}`);
  }
  assert.ok(build.includes('window.switchView = function(view)'));
  assert.ok(build.includes("document.querySelectorAll('.nav [data-view]')"));
});

test('een ontbrekende of kapotte feature blokkeert de navigatie niet', () => {
  assert.ok(build.includes("if (!target)"));
  assert.ok(build.includes("return false;"));
  assert.ok(build.includes("safeCall('tabblad renderen'"));
  assert.ok(build.includes('window.machineparkRenderFaultLibrary'));
  assert.ok(build.includes('window.machineparkRenderManualLibrary'));
});

test('inline onclick en navigatiebridge gebruiken dezelfde switchView', () => {
  assert.ok(build.includes('try { switchView = window.switchView; }'));
});

test('navigatie-runtime wordt voor asset-extractie gebouwd', () => {
  const command = pkg.scripts.build;
  const navigationPos = command.indexOf('python3 build-navigation-runtime.py');
  const extractionPos = command.indexOf('python3 scripts/extract-build-assets.py');
  assert.ok(navigationPos >= 0, 'build-navigation-runtime.py ontbreekt in npm build');
  assert.ok(extractionPos > navigationPos, 'navigatie-runtime moet vóór asset-extractie draaien');
  assert.ok(command.includes('node --check assets/machinepark-build.js'));
});
