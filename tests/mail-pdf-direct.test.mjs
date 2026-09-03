import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-mail-pdf-direct.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('Mail PDF gebruikt directe jsPDF-opbouw in plaats van html2canvas voor de actieve klikroute', () => {
  assert.ok(build.includes('jspdf/2.5.1/jspdf.umd.min.js'));
  assert.ok(build.includes("doc.output('blob')"));
  assert.equal(build.includes('html2canvas'), false);
  assert.ok(build.includes("document.addEventListener('click'"));
  assert.ok(build.includes('event.stopImmediatePropagation()'));
});

test('directe Mail PDF haalt echte scherminhoud uit details, tabellen en formuliervelden', () => {
  assert.ok(build.includes('labelledDetailLines(context.source)'));
  assert.ok(build.includes('tableLines(context.source)'));
  assert.ok(build.includes('genericLines(context.source)'));
  assert.ok(build.includes("source.querySelectorAll('[class*=\"detail-field\"]')"));
  assert.ok(build.includes("source.querySelectorAll('table tr')"));
});

test('mobiele Mail PDF kan niet onbeperkt op PDF maken blijven hangen', () => {
  assert.ok(build.includes('withTimeout('));
  assert.ok(build.includes("12000, 'PDF-bibliotheek reageert niet. Probeer opnieuw.'"));
  assert.ok(build.includes("button.textContent = 'PDF maken…'"));
  assert.ok(build.includes("button.textContent = 'Delen…'"));
  assert.ok(build.includes('finally'));
  assert.ok(build.includes("button.dataset.directPdfBusy = '0'"));
});

test('lege of ongeldige PDF wordt niet gedeeld', () => {
  assert.ok(build.includes("useful.length < 5"));
  assert.ok(build.includes('blob.size < 1000'));
  assert.ok(build.includes("throw new Error('De PDF bevat geen geldige inhoud. Probeer opnieuw.')"));
});

test('directe Mail PDF draait na de bestaande mail-renderfix', () => {
  const basePos = pkg.scripts.build.indexOf('python3 build-mail-pdf.py');
  const renderPos = pkg.scripts.build.indexOf('python3 build-mail-pdf-render-fix.py');
  const directPos = pkg.scripts.build.indexOf('python3 build-mail-pdf-direct.py');
  assert.ok(basePos >= 0);
  assert.ok(renderPos > basePos);
  assert.ok(directPos > renderPos);
});
