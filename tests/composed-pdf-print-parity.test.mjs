import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = path => fs.readFileSync(path, 'utf8');
const patch = read('build-composed-pdf-print-parity.py');
const pkg = JSON.parse(read('package.json'));

test('PDF opslaan gebruikt exact dezelfde afdrukfunctie als Afdrukken', () => {
  assert.match(patch, /composed-pdf-print-parity-v1/);
  assert.match(patch, /saveComposedPdf=async function\(doc,button\)/);
  assert.match(patch, /printComposedDocument\(doc\);/);
  assert.match(patch, /Opslaan als PDF/);
  assert.doesNotMatch(patch, /createComposedPdfFile\(doc\)/);
});

test('PDF print-pariteit wordt na alle samengestelde document patches gebouwd', () => {
  assert.ok(pkg.scripts.build.includes('python3 build-composed-pdf-print-parity.py'));
  assert.ok(pkg.scripts.build.indexOf('build-composed-pdf-print-parity.py') > pkg.scripts.build.indexOf('build-composed-device-selection-save-fix.py'));
});
