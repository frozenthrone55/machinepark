import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');

test('afdrukken vereist altijd een expliciete gebruikersklik', () => {
  const html = read('index.html');
  const service = read('service-visits.js');

  assert.match(html, /data-machinepark-build-fix="safe-explicit-print-v1"/);
  assert.match(html, /data-machinepark-explicit-print-guard="v1"/);
  assert.match(html, /event\.isTrusted/);
  assert.match(html, /window\.machineparkGrantPrintIntent/);
  assert.match(html, /automatische printopdracht geblokkeerd/);

  assert.doesNotMatch(html, /window\.onload\s*=\s*\(\)\s*=>\s*setTimeout\(\(\)\s*=>\s*window\.print\(\)/);
  assert.doesNotMatch(html, /setTimeout\(triggerPrint\s*,\s*80\)/);
  assert.doesNotMatch(html, /setTimeout\(triggerPrint\s*,\s*1500\)/);

  const serviceRecordStart = html.indexOf('function printServiceRecordIsolated(kind, record)');
  const serviceRecordEnd = html.indexOf('function printServiceRecord(kind, id)', serviceRecordStart);
  assert.ok(serviceRecordStart >= 0 && serviceRecordEnd > serviceRecordStart, 'veilige service-afdrukfunctie ontbreekt');
  const serviceRecordBlock = html.slice(serviceRecordStart, serviceRecordEnd);
  assert.doesNotMatch(serviceRecordBlock, /triggerPrint/);
  assert.doesNotMatch(serviceRecordBlock, /setTimeout\([^)]*print/i);
  assert.match(serviceRecordBlock, /servicePrintNow/);
  assert.match(serviceRecordBlock, /addEventListener\('click'/);

  const reportStart = service.indexOf('function printServiceReportIsolated(report)');
  const reportEnd = service.indexOf('async function printServiceReport(id)', reportStart);
  assert.ok(reportStart >= 0 && reportEnd > reportStart, 'veilige serviceverslag-afdrukfunctie ontbreekt');
  const reportBlock = service.slice(reportStart, reportEnd);
  assert.doesNotMatch(reportBlock, /triggerPrint/);
  assert.doesNotMatch(reportBlock, /setTimeout\([^)]*print/i);
  assert.match(reportBlock, /serviceReportPrintNow/);
  assert.match(reportBlock, /addEventListener\('click'/);

  const composedStart = html.indexOf('function printComposedDocument(doc)');
  const composedEnd = html.indexOf('function loadJsPdf()', composedStart);
  assert.ok(composedStart >= 0 && composedEnd > composedStart, 'veilige samengestelde afdrukfunctie ontbreekt');
  const composedBlock = html.slice(composedStart, composedEnd);
  assert.match(composedBlock, /machineparkComposedPrintNow/);
  assert.doesNotMatch(composedBlock, /window\.onload[^\n]*window\.print/);
  assert.match(composedBlock, /addEventListener\('click'.*window\.print/s);
});
