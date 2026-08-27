import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const sw = readFileSync(new URL('../sw.js', import.meta.url), 'utf8');

test('kritieke UI bouwstenen zijn aanwezig', () => {
  for (const needle of [
    '<title>Machinepark</title>',
    'usage-autocomplete',
    'device-autocomplete',
    'data-undo-audit',
    'Prijs excl. BTW',
    'Op afroep',
    'Maandelijks',
  ]) assert.ok(html.includes(needle), `Ontbreekt in build: ${needle}`);
});

test('Clerk profielknop is uniek en gevaarlijke alles-wissen actie is weg', () => {
  assert.equal((html.match(/id="clerkUserButton"/g) || []).length, 1);
  assert.equal(html.includes('id="clearAll"'), false);
});

test('service worker heeft een versiegebonden cache', () => {
  assert.match(sw, /machinepark-v1\./);
});
