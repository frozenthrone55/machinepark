import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-navigation-runtime.py', import.meta.url), 'utf8');
const bootstrap = readFileSync(new URL('../build-navigation-bootstrap.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('navigatie-runtime houdt alle hoofdtabbladen bruikbaar', () => {
  for (const view of ['dashboard', 'devices', 'maintenance', 'breakdowns', 'parts', 'faults', 'manuals', 'settings']) {
    assert.ok(build.includes(`${view}: [`), `metadata ontbreekt voor ${view}`);
  }
  assert.ok(build.includes('window.switchView = activateView'));
  assert.ok(build.includes('window.machineparkNavigate = activateView'));
  assert.ok(build.includes("document.querySelectorAll('.nav [data-view]')"));
});

test('zichtbare tab wisselt ook als basis-JavaScript niet beschikbaar is', () => {
  const domSwitch = build.indexOf("document.querySelectorAll('.view').forEach");
  const stateSwitch = build.indexOf('setStateView(nextView)');
  assert.ok(domSwitch >= 0, 'DOM-viewwissel ontbreekt');
  assert.ok(stateSwitch > domSwitch, 'DOM moet vóór state worden gewisseld');
  assert.ok(build.includes("if (typeof state !== 'undefined' && state) state.view = view"));
  assert.ok(build.includes("if (typeof renderAll === 'function') renderAll()"));
});

test('capture-handler omzeilt oude of kapotte navigatielisteners', () => {
  assert.ok(build.includes("document.addEventListener('click', handleNavigationEvent, true)"));
  assert.ok(build.includes("document.addEventListener('touchend', handleNavigationEvent, { capture: true, passive: false })"));
  assert.ok(build.includes('event.preventDefault()'));
  assert.ok(build.includes('event.stopPropagation()'));
  assert.ok(build.includes('event.stopImmediatePropagation()'));
  assert.ok(build.includes('activateView(button.dataset.view)'));
});

test('een ontbrekende of kapotte feature blokkeert de navigatie niet', () => {
  assert.ok(build.includes("if (!target)"));
  assert.ok(build.includes("return false;"));
  assert.ok(build.includes("safeCall('tabblad renderen'"));
  assert.ok(build.includes('window.machineparkRenderFaultLibrary'));
  assert.ok(build.includes('window.machineparkRenderManualLibrary'));
});

test('inline onclick en navigatiebridge gebruiken dezelfde switchView', () => {
  assert.ok(build.includes('try { switchView = activateView; }'));
});

test('inline fallback blijft onafhankelijk van de externe featurebundel', () => {
  assert.ok(bootstrap.includes('machinepark-navigation-bootstrap-v1'));
  assert.ok(bootstrap.includes('data-machinepark-navigation-bootstrap="v1"'));
  assert.ok(bootstrap.includes("document.querySelectorAll('.view').forEach"));
  assert.ok(bootstrap.includes("target.classList.add('active')"));
  assert.ok(bootstrap.includes("document.addEventListener('click', interceptNavigation, true)"));
  assert.ok(bootstrap.includes('event.stopImmediatePropagation()'));
  assert.ok(bootstrap.includes('window.machineparkInlineNavigate = navigate'));
  assert.ok(bootstrap.includes("if 'data-machinepark-build-fix=' in bootstrap_block"));
});

test('navigatie-runtime en inline fallback worden voor asset-extractie gebouwd', () => {
  const command = pkg.scripts.build;
  const navigationPos = command.indexOf('python3 build-navigation-runtime.py');
  const bootstrapPos = command.indexOf('python3 build-navigation-bootstrap.py');
  const extractionPos = command.indexOf('python3 scripts/extract-build-assets.py');
  assert.ok(navigationPos >= 0, 'build-navigation-runtime.py ontbreekt in npm build');
  assert.ok(bootstrapPos > navigationPos, 'inline fallback moet na de volledige navigatie-runtime worden toegevoegd');
  assert.ok(extractionPos > bootstrapPos, 'inline fallback moet vóór asset-extractie worden toegevoegd');
  assert.ok(command.includes('node --check assets/machinepark-build.js'));
});
