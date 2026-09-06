import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const service = readFileSync(new URL('../service-visits.js', import.meta.url), 'utf8');
const builder = readFileSync(new URL('../build-decimal-part-usage.py', import.meta.url), 'utf8');

test('onderhoud en depannage aanvaarden fractionele voorraadonderdelen', () => {
  assert.match(index, /class="usage-qty" type="number" min="0\.001" step="0\.001" inputmode="decimal"/);
  assert.match(index, /function normalizePartQuantity\(value,fallback=0\)/);
  assert.match(index, /function formatPartQuantity\(value\)/);
  assert.match(index, /formatPartQuantity\(i\.qty\)/);
  assert.doesNotMatch(index, /class="usage-qty" type="number" min="1" step="1"/);
});

test('eenmalige onderdelen zijn fractioneel in onderhoud en depannage', () => {
  assert.match(index, /class="service-oneoff-qty" type="number" min="0\.001" step="0\.001" inputmode="decimal"/);
  assert.doesNotMatch(index, /class="service-oneoff-qty" type="number" min="1" step="1" inputmode="numeric"/);
});

test('serviceverslag gebruikt dezelfde decimale hoeveelheden en voorraadprecisie', () => {
  assert.match(service, /machinepark-decimal-part-usage-v1/);
  assert.match(service, /class="sv-oneoff-qty" type="number" min="0\.001" step="0\.001" inputmode="decimal"/);
  assert.match(service, /qty:normalizePartQuantity\(r\.querySelector\('\.usage-qty'\)\?\.value,1\)/);
  assert.match(service, /stock:normalizePartQuantity\(Number\(p\.stock\|\|0\)-qty\)/);
  assert.doesNotMatch(service, /Math\.round\(Number\(r\.querySelector\('\.sv-oneoff-qty'\)/);
});

test('buildketen toont hoeveelheden met Belgische kommanotatie', () => {
  assert.match(builder, /maximumFractionDigits:3/);
  assert.match(builder, /toLocaleString\('nl-BE'/);
  assert.match(builder, /inputmode="decimal"/);
});
