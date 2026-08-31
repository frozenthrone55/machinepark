import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-print-service-details.py', import.meta.url), 'utf8');

test('depannage-afdruk zet elk gebruikt onderdeel op een eigen regel', () => {
  assert.ok(build.includes("serviceRecordParts(record, true)"));
  assert.ok(build.includes("usedPartsText([part])"));
  assert.ok(build.includes("lines.join('\\n')"));
  assert.ok(build.includes('white-space:pre-wrap'));
});

test('onderhoudsafdruk behoudt de bestaande onderdelenweergave', () => {
  assert.ok(build.includes("servicePrintField('Gebruikte onderdelen', serviceRecordParts(record), true)"));
});
