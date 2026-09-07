import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const client = readFileSync(new URL('../manual-library.js', import.meta.url), 'utf8');
const endpoint = readFileSync(new URL('../netlify/functions/manual-library.mjs', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('PDF uploadt in blokken ruim onder de Netlify functionlimiet', () => {
  assert.match(client, /machinepark-manual-chunk-upload-v1/);
  assert.match(client, /chunkBytes = 3_500_000/);
  assert.match(client, /action: 'upload-chunk'/);
  assert.match(client, /action: 'finalize-upload'/);
  assert.match(client, /action: 'abort-upload'/);
  assert.doesNotMatch(client, /body: file\s*\}/);
});

test('server valideert en voegt alle PDF-blokken veilig samen', () => {
  assert.match(endpoint, /machinepark-manual-chunk-upload-server-v1/);
  assert.match(endpoint, /UPLOAD_CHUNK_PREFIX = 'manual-upload-chunks\/'/);
  assert.match(endpoint, /MAX_CHUNK_BYTES = 3_750_000/);
  assert.match(endpoint, /MAX_UPLOAD_CHUNKS = 8/);
  assert.match(endpoint, /entry\.metadata\?\.uploadedBy !== access\.sub/);
  assert.match(endpoint, /receivedBytes !== fileSize/);
  assert.match(endpoint, /Buffer\.concat\(buffers, receivedBytes\)/);
  assert.match(endpoint, /%PDF-/);
  assert.match(endpoint, /cleanupUploadChunks/);
});

test('chunk-upload draait voor native sync zodat cache-hash de nieuwe runtime bevat', () => {
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-manual-chunk-upload\.py/);
  assert.ok(chain.indexOf('build-manual-library.py') < chain.indexOf('build-manual-chunk-upload.py'));
  assert.ok(chain.indexOf('build-manual-chunk-upload.py') < chain.indexOf('build-manual-native-sync.py'));
});
