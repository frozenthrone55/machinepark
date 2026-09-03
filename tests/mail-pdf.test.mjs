import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-mail-pdf.py', import.meta.url), 'utf8');
const renderFix = readFileSync(new URL('../build-mail-pdf-render-fix.py', import.meta.url), 'utf8');
const devicePrintBuild = readFileSync(new URL('../build-print-device-details.py', import.meta.url), 'utf8');
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

test('Mail PDF en renderfix worden in de normale build uitgevoerd', () => {
  const basePos = pkg.scripts.build.indexOf('python3 build-mail-pdf.py');
  const fixPos = pkg.scripts.build.indexOf('python3 build-mail-pdf-render-fix.py');
  assert.ok(basePos >= 0);
  assert.ok(fixPos > basePos);
});

test('Mail PDF wordt altijd aan de echte document-body toegevoegd', () => {
  assert.ok(build.includes('body_pos = index.rfind("</body>")'));
  assert.ok(build.includes('index = index[:body_pos] + script + index[body_pos:]'));
});

test('Mail PDF bron blijft gemount en html2canvas zet alleen de clone in het capturevlak', () => {
  assert.ok(renderFix.includes('left:-12000px'));
  assert.ok(renderFix.includes('document.body.appendChild(stage);'));
  assert.ok(renderFix.includes('onclone: (clonedDoc) =>'));
  assert.ok(renderFix.includes("clonedDoc.querySelector('.machinepark-pdf-stage')"));
  assert.ok(renderFix.includes("clonedStage.style.position = 'static'"));
  assert.ok(renderFix.includes("clonedStage.style.left = '0'"));
  assert.ok(renderFix.includes("clonedStage.style.top = '0'"));
  assert.ok(renderFix.includes("clonedStage.style.zIndex = 'auto'"));
});

test('toesteldetail-print bevat geen verborgen body-afsluiter die feature-injectie kan kapen', () => {
  assert.equal(devicePrintBuild.includes('</main></body></html>'), false);
  assert.ok(devicePrintBuild.includes('popup.document.close()'));
  assert.ok(devicePrintBuild.includes("if index.count('</body>') != 1:"));
});
