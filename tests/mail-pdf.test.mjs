import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-mail-pdf.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('Mail PDF staat naast de bestaande afdrukknoppen', () => {
  assert.ok(build.includes('✉ Mail PDF'));
  assert.ok(build.includes("document.querySelectorAll('.page-print-row')"));
  assert.ok(build.includes("document.querySelectorAll('.service-detail-print-btn')"));
  assert.ok(build.includes("document.getElementById('printDeviceDetails')"));
});

test('Mail PDF maakt een echt PDF-bestand en gebruikt bestandsdeling waar mogelijk', () => {
  assert.ok(build.includes('html2pdf.js/0.14.0/html2pdf.bundle.min.js'));
  assert.ok(build.includes("outputPdf('blob')"));
  assert.ok(build.includes('new File([blob]'));
  assert.ok(build.includes("typeof navigator.share === 'function'"));
  assert.ok(build.includes('navigator.canShare'));
  assert.ok(build.includes('navigator.share(shareData)'));
});

test('Mail PDF heeft een desktopfallback zonder te doen alsof mailto een bijlage kan toevoegen', () => {
  assert.ok(build.includes('downloadPdfFile(file)'));
  assert.ok(build.includes('mailto:?subject='));
  assert.ok(build.includes('voeg de gedownloade PDF toe als bijlage'));
});

test('Mail PDF wordt in de normale build uitgevoerd', () => {
  assert.ok(pkg.scripts.build.includes('python3 build-mail-pdf.py'));
});
