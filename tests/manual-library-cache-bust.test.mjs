import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

const client = readFileSync(new URL('../manual-library.js', import.meta.url));
const clientText = client.toString('utf8');
const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const sw = readFileSync(new URL('../sw.js', import.meta.url), 'utf8');
const expectedHash = createHash('sha256').update(client).digest('hex').slice(0, 12);

test('handleidingenlimiet is 40 MB in de gebouwde client', () => {
  assert.match(clientText, /file\.size > 40_000_000/);
  assert.match(clientText, /De PDF is groter dan 40 MB\./);
  assert.match(clientText, /Maximaal 40 MB\./);
  assert.doesNotMatch(clientText, /12 MB/);
});

test('manual-library.js gebruikt een inhoudshash zodat oude PWA-cache niet kan blijven hangen', () => {
  assert.match(index, new RegExp(`manual-library\\.js\\?v=${expectedHash}`));
});

test('service worker haalt handleidingenassets online network-first op', () => {
  assert.match(sw, /machinepark-manual-assets-network-first-v1/);
  assert.match(sw, /url\.pathname\.endsWith\('\/manual-library\.js'\)/);
  assert.match(sw, /url\.pathname\.endsWith\('\/manual-library\.css'\)/);
  assert.match(sw, /fetch\(e\.request,\{cache:'no-store'\}\)/);
});
