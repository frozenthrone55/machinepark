import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-mail-pdf-direct.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('Mail PDF gebruikt directe jsPDF-opbouw voor de actieve klikroute', () => {
  assert.ok(build.includes('jspdf/2.5.1/jspdf.umd.min.js'));
  assert.ok(build.includes("doc.output('blob')"));
  assert.equal(build.includes('html2pdf.bundle.min.js'), false);
  assert.ok(build.includes("document.addEventListener('click'"));
  assert.ok(build.includes('event.stopImmediatePropagation()'));
});

test('Mail PDF gebruikt dezelfde recordcontext als de afdrukknoppen', () => {
  assert.ok(build.includes('servicePrintKind'));
  assert.ok(build.includes('servicePrintId'));
  assert.ok(build.includes('devicePrintId'));
  assert.ok(build.includes('serviceModel(context)'));
  assert.ok(build.includes('deviceModel(context)'));
});

test('Mail PDF volgt de afdrukopbouw met velden, tijdlijn en fotos', () => {
  assert.ok(build.includes('addFields(doc, model'));
  assert.ok(build.includes('addTimeline(doc, model'));
  assert.ok(build.includes('await addPhotos(doc, model'));
  assert.ok(build.includes("photoTitle: 'Foto’s bij verslag'"));
  assert.ok(build.includes("photoTitle: 'Foto’s toestel'"));
  assert.ok(build.includes('photoColumns: 2'));
  assert.ok(build.includes('photoColumns: 3'));
  assert.ok(build.includes('doc.addImage('));
  assert.ok(build.includes("context.source.querySelectorAll('.device-detail-photo img')"));
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
  assert.ok(build.includes('blob.size < 1200'));
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
