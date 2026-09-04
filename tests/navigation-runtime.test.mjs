import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const earlyBridge = readFileSync(new URL('../build-navigation-early-bridge.py', import.meta.url), 'utf8');
const build = readFileSync(new URL('../build-navigation-runtime.py', import.meta.url), 'utf8');
const bootstrap = readFileSync(new URL('../build-navigation-bootstrap.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('vroege bridge wisselt de DOM vóór de app-runtime', () => {
  assert.ok(earlyBridge.includes('Machinepark DOM-first navigation bridge v3'));
  assert.ok(earlyBridge.includes("document.querySelectorAll('.view').forEach"));
  assert.ok(earlyBridge.includes("target.classList.add('active')"));
  assert.ok(earlyBridge.includes('window.machineparkEarlyNavigate=navigate'));
  assert.ok(earlyBridge.includes("e.stopImmediatePropagation()"));
  assert.ok(earlyBridge.includes("},true);"));
  assert.ok(earlyBridge.includes("{capture:true,passive:false}"));
  const visualSwitch = earlyBridge.indexOf("target.classList.add('active')");
  const fullRuntime = earlyBridge.indexOf("window.machineparkNavigate==='function'");
  assert.ok(visualSwitch >= 0 && fullRuntime > visualSwitch, 'zichtbare view moet vóór volledige runtime wisselen');
});

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

test('sync, auth en offline-builds blijven onaangeroerd vóór navigatie-hardening', () => {
  const command = pkg.scripts.build;
  const basePos = command.indexOf('python3 scripts/build-machinepark.py');
  const offlinePos = command.indexOf('python3 build-offline-first.py');
  const startupPos = command.indexOf('python3 build-startup-resilience.py');
  const authRetryPos = command.indexOf('python3 build-central-auth-retry.py');
  const autoLiveSyncPos = command.indexOf('python3 build-auto-live-sync.py');
  const earlyPos = command.indexOf('python3 build-navigation-early-bridge.py');
  const navigationPos = command.indexOf('python3 build-navigation-runtime.py');
  const bootstrapPos = command.indexOf('python3 build-navigation-bootstrap.py');
  const extractionPos = command.indexOf('python3 scripts/extract-build-assets.py');

  assert.ok(basePos >= 0, 'basisbuild ontbreekt');
  assert.ok(offlinePos > basePos, 'offline-build moet na de basisbuild draaien');
  assert.ok(startupPos > offlinePos, 'opstartresilience moet na offline-build draaien');
  assert.ok(authRetryPos > startupPos, 'auth-retry moet na opstartresilience draaien');
  assert.ok(autoLiveSyncPos > authRetryPos, 'live-sync moet na auth-retry draaien');
  assert.ok(earlyPos > autoLiveSyncPos, 'navigatiebridge mag sync/auth-builds niet vooraf wijzigen');
  assert.ok(navigationPos > earlyPos, 'volledige runtime moet na de vroege bridge worden toegevoegd');
  assert.ok(bootstrapPos > navigationPos, 'inline fallback moet na de volledige navigatie-runtime worden toegevoegd');
  assert.ok(extractionPos > bootstrapPos, 'inline fallback moet vóór asset-extractie worden toegevoegd');
  assert.ok(command.includes('node --check assets/machinepark-build.js'));
});
