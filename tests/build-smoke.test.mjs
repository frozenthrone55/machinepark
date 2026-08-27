import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const sw = readFileSync(new URL('../sw.js', import.meta.url), 'utf8');

test('kritieke UI bouwstenen zijn aanwezig', () => {
  for (const needle of [
    '<title>Machinepark</title>',
    'usage-autocomplete',
    'device-autocomplete',
    'data-undo-audit',
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

test('Clerk profielknop is uniek en gevaarlijke alles-wissen actie is weg', () => {
  assert.equal((html.match(/id="clerkUserButton"/g) || []).length, 1);
  assert.equal(html.includes('id="clearAll"'), false);
});

test('service worker heeft de professionele cacheversie', () => {
  assert.ok(sw.includes('machinepark-v1.52-professional-foundation'));
});

test('tijdelijke buildpatches zijn uit de repository verdwenen', () => {
  const scripts = readdirSync(new URL('../scripts/', import.meta.url)).sort();
  assert.deepEqual(scripts, ['build-machinepark.py']);
});
