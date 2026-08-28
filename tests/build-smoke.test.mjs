import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const sw = readFileSync(new URL('../sw.js', import.meta.url), 'utf8');

test('kritieke UI bouwstenen zijn aanwezig', () => {
  for (const needle of [
    '<title>Machinepark</title>',
    'data-view="maintenance"',
    'id="maintenanceLocation"',
    'maintenance-machine-card',
    'maintenanceBatchSelectedItems',
    'data-view="breakdowns"',
    'data-view="parts"',
    'usage-autocomplete',
    'device-autocomplete',
    'data-undo-audit',
    'id="auditPartsLogBody"',
    'Overige wijzigingen',
    'dashboardProfessional',
    'downloadStockImportReport',
    'Machinepark_Veiligheidsbackup_',
    'Prijs excl. BTW',
    'Op afroep',
    'Maandelijks',
    'technieker',
    'magazijnier',
  ]) assert.ok(html.includes(needle), `Ontbreekt in broncode: ${needle}`);
});

test('inline app-JavaScript bevat geen syntaxfouten', () => {
  const scripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => m[1]);
  assert.ok(scripts.length > 0, 'Geen inline scripts gevonden');
  scripts.forEach((code, index) => {
    try {
      new vm.Script(code, { filename: `index-inline-${index + 1}.js` });
    } catch (error) {
      assert.fail(`Syntaxfout in inline script ${index + 1}:\n${error.stack || error.message}`);
    }
  });
});

test('Clerk profielknop is uniek en gevaarlijke alles-wissen actie is weg', () => {
  assert.equal((html.match(/id="clerkUserButton"/g) || []).length, 1);
  assert.equal(html.includes('id="clearAll"'), false);
});

test('service worker forceert nieuwe cache na locatiegericht onderhoud', () => {
  assert.ok(sw.includes('machinepark-v1.55-location-maintenance'));
});

test('tijdelijke buildpatches zijn uit de repository verdwenen', () => {
  const scripts = readdirSync(new URL('../scripts/', import.meta.url)).sort();
  assert.deepEqual(scripts, ['build-machinepark.py']);
});
