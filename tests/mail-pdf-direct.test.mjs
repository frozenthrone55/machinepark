import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-mail-pdf-direct.py', import.meta.url), 'utf8');
const parity = readFileSync(new URL('../build-mail-pdf-print-parity.py', import.meta.url), 'utf8');
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

test('depannage-PDF volgt de afdrukvelden en volgorde', () => {
  assert.ok(build.includes("{ label:'Datum', value:serviceDate(record) }"));
  assert.ok(build.includes("{ label:'Toestel', value:serviceDevice(record) }"));
  assert.ok(build.includes("{ label:'Prioriteit', value:record.priority || '—' }"));
  assert.ok(build.includes("{ label:'Status', value:record.status || '—' }"));
  assert.ok(build.includes("{ label:'Technieker', value:record.technician || '—' }"));
  assert.ok(build.includes("serviceWorkSummary('breakdowns', record)"));
  assert.ok(build.includes("{ label:'Probleem / melding'"));
  assert.ok(build.includes("{ label:'Diagnose'"));
  assert.ok(build.includes("{ label:'Oplossing / uitgevoerde werken'"));
  assert.ok(build.includes("serviceParts(record, true)"));
});

test('onderhoud-PDF volgt de afdrukvelden en bevat werkminuten', () => {
  assert.ok(build.includes("{ label:'Type onderhoud', value:record.type || '—' }"));
  assert.ok(build.includes("serviceWorkSummary('maintenance', record)"));
  assert.ok(build.includes("{ label:'Uitgevoerde werkzaamheden / notitie'"));
  assert.ok((build.match(/label:'Werkminuten \/ toestellen'/g) || []).length >= 2);
});

test('eenmalige onderdelen bevatten leverancier, code, omschrijving en aantal', () => {
  assert.ok(build.includes('function serviceOneOffParts(record)'));
  assert.ok(build.includes('cleanText(item?.supplier)'));
  assert.ok(build.includes('cleanText(item?.supplierCode)'));
  assert.ok(build.includes('cleanText(item?.description)'));
  assert.ok(build.includes("`${qty} x ${text}`"));
  assert.ok(build.includes("label:'Eenmalige onderdelen'"));
});

test('Mail PDF gebruikt PDF-veilige scheidingstekens zonder vierkantjes', () => {
  assert.ok(build.includes(".replace(/[·•]/g, '.')"));
  assert.ok(build.includes(".replace(/[×✕✖]/g, 'x')"));
  assert.ok(build.includes(".replace(/…/g, '...')"));
  assert.ok(build.includes('Machinepark . ${title}'));
});

test('verslagfotos gebruiken dezelfde opslagreferenties als de app', () => {
  assert.ok(build.includes('function servicePhotos(record)'));
  assert.ok(build.includes("typeof src === 'string' && src.trim()"));
  assert.ok(build.includes("photoTitle: 'Foto’s bij verslag'"));
  assert.ok(build.includes('photoColumns: 2'));
  assert.ok(build.includes('await addPhotos(doc, model'));
  assert.ok(build.includes('doc.addImage('));
});

test('PDF-layout volgt afdrukopbouw met header, twee kolommen, fotos en footer', () => {
  assert.ok(build.includes("doc.setFontSize(20)"));
  assert.ok(build.includes('const colWidth = 86'));
  assert.ok(build.includes('const gap = 8'));
  assert.ok(build.includes('Afgedrukt vanuit Machinepark'));
  assert.ok(build.includes('addFields(doc, model'));
  assert.ok(build.includes('await addPhotos(doc, model'));
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
  assert.ok(build.includes('blob.size < 1200'));
  assert.ok(build.includes("throw new Error('De PDF bevat geen geldige inhoud. Probeer opnieuw.')"));
});

test('print-pariteitscontrole bewaakt depannage en onderhoud', () => {
  assert.ok(parity.includes('mail-pdf-direct-v4'));
  assert.ok(parity.includes("label:'Werkminuten / toestellen'"));
  assert.ok(parity.includes('cleanText(item?.supplier)'));
  assert.ok(parity.includes('photoColumns: 2'));
  assert.ok(parity.includes('Afgedrukt vanuit Machinepark'));
});

test('directe Mail PDF en print-pariteit draaien na de bestaande mail-renderfix', () => {
  const basePos = pkg.scripts.build.indexOf('python3 build-mail-pdf.py');
  const renderPos = pkg.scripts.build.indexOf('python3 build-mail-pdf-render-fix.py');
  const directPos = pkg.scripts.build.indexOf('python3 build-mail-pdf-direct.py');
  const parityPos = pkg.scripts.build.indexOf('python3 build-mail-pdf-print-parity.py');
  assert.ok(basePos >= 0);
  assert.ok(renderPos > basePos);
  assert.ok(directPos > renderPos);
  assert.ok(parityPos > directPos);
});
