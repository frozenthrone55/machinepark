import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const client = readFileSync(new URL('../manual-library.js', import.meta.url), 'utf8');
const endpoint = readFileSync(new URL('../netlify/functions/manual-library.mjs', import.meta.url), 'utf8');
const synology = readFileSync(new URL('../synology/api/manual-library.php', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('PDF-handleidingen laten maximaal 40 MB toe op alle actieve lagen', () => {
  assert.match(client, /file\.size > 40_000_000/);
  assert.match(client, /Maximaal 40 MB\./);
  assert.doesNotMatch(client, /12 MB/);

  assert.match(endpoint, /const MAX_FILE_BYTES = 40_000_000;/);
  assert.doesNotMatch(endpoint, /12 MB/);

  assert.match(synology, /define\('MP_MANUAL_MAX_BYTES', 40000000\);/);
  assert.doesNotMatch(synology, /12 MB/);
});

test('40 MB limiet wordt na de handleidingen- en Synology-buildlagen toegepast', () => {
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-manual-pdf-40mb\.py/);
  assert.ok(chain.indexOf('build-manual-chunk-upload.py') < chain.indexOf('build-manual-pdf-40mb.py'));
  assert.ok(chain.indexOf('build-synology-local-content.py') < chain.indexOf('build-manual-pdf-40mb.py'));
});
