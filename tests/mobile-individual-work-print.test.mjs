import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../build-print-service-details.py', import.meta.url), 'utf8');
const pagePrint = readFileSync(new URL('../build-print-pages.py', import.meta.url), 'utf8');

test('gsm gebruikt een volledig apart document voor individuele werkzaamheid', () => {
  assert.match(source, /function serviceShouldUseIsolatedPrint/);
  assert.match(source, /window\.matchMedia\('\(max-width: 900px\)'\)/);
  assert.match(source, /window\.matchMedia\('\(pointer: coarse\)'\)/);
  assert.match(source, /function printServiceRecordIsolated/);
  assert.match(source, /window\.open\('', '_blank'\)/);
  assert.match(source, /serviceIsolatedPrintDocument/);
  assert.match(source, /servicePrintNow/);
  assert.match(source, /printWindow\.print\(\)/);
  assert.match(source, /if \(serviceShouldUseIsolatedPrint\(\) && printServiceRecordIsolated\(kind, record\)\) return/);
});

test('detailknop kan geen onderliggende overzichtsafdruk meer activeren', () => {
  assert.match(source, /event\.preventDefault\(\)/);
  assert.match(source, /event\.stopPropagation\(\)/);
  assert.match(source, /event\.stopImmediatePropagation\(\)/);
  assert.match(source, /window\.machineparkSuppressOverviewPrintUntil = Date\.now\(\) \+ 10000/);
  assert.match(pagePrint, /Date\.now\(\) < Number\(window\.machineparkSuppressOverviewPrintUntil \|\| 0\)/);
});

test('desktop fallback blijft actief tot echte printmodus eindigt', () => {
  const start = source.indexOf('function printServiceRecord(kind, id)');
  const end = source.indexOf('function addServicePrintButton', start);
  const block = source.slice(start, end);
  assert.match(block, /window\.addEventListener\('afterprint', restore\)/);
  assert.match(block, /window\.matchMedia\('print'\)/);
  assert.match(block, /printMediaStarted/);
  assert.match(block, /printMedia\.addEventListener\('change', onPrintMediaChange\)/);
  assert.match(block, /document\.body\.classList\.add\('service-record-printing'\)/);
  assert.doesNotMatch(block, /1800/);
});

test('mobiele printpagina bevat alleen detailinhoud en geen Machinepark app views', () => {
  const start = source.indexOf('function serviceIsolatedPrintDocument');
  const end = source.indexOf('function printServiceRecordIsolated', start);
  const block = source.slice(start, end);
  assert.match(block, /<main class="service-print-sheet">/);
  assert.match(block, /servicePrintHtml\(kind, record\)/);
  assert.doesNotMatch(block, /class="app"/);
  assert.doesNotMatch(block, /class="view/);
  assert.doesNotMatch(block, /Machinepark-overzicht/);
});
