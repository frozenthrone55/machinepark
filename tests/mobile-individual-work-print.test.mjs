import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../build-print-service-details.py', import.meta.url), 'utf8');

test('individuele werkzaamheid blijft actief tijdens mobiele afdrukpreview', () => {
  const start = source.indexOf('function printServiceRecord');
  const end = source.indexOf('function addServicePrintButton', start);
  const block = source.slice(start, end);
  assert.match(block, /window\.addEventListener\('afterprint', restore\)/);
  assert.match(block, /window\.matchMedia\('print'\)/);
  assert.match(block, /printMediaStarted/);
  assert.match(block, /printMedia\.addEventListener\('change', onPrintMediaChange\)/);
  assert.match(block, /document\.body\.classList\.add\('service-record-printing'\)/);
  assert.doesNotMatch(block, /1800/);
});

test('detailafdruk wordt pas hersteld na einde van echte printmodus', () => {
  const start = source.indexOf('function printServiceRecord');
  const end = source.indexOf('function addServicePrintButton', start);
  const block = source.slice(start, end);
  assert.match(block, /if \(event\.matches\)/);
  assert.match(block, /if \(printMediaStarted\) restore\(\)/);
  assert.match(block, /window\.removeEventListener\('afterprint', restore\)/);
  assert.match(block, /printMedia\.removeEventListener\('change', onPrintMediaChange\)/);
});
