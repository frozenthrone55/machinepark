import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const prep = readFileSync(new URL('../scripts/prepare-synology-vendor.mjs', import.meta.url), 'utf8');
const builder = readFileSync(new URL('../build-synology-local-vendor.py', import.meta.url), 'utf8');

test('Synology vendor build kopieert html2pdf en jsPDF lokaal', () => {
  assert.match(prep, /html2pdf\.bundle\.min\.js/);
  assert.match(prep, /jspdf\.umd\.min\.js/);
  assert.match(prep, /node_modules/);
});

test('Synology runtime vervangt cdnjs door lokale vendorbestanden', () => {
  assert.match(builder, /cdnjs\.cloudflare\.com/);
  assert.match(builder, /\.\/vendor\/html2pdf\.bundle\.min\.js/);
  assert.match(builder, /\.\/vendor\/jspdf\.umd\.min\.js/);
});
