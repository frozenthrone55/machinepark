import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const page = readFileSync(new URL('../synology/import-cloud.php', import.meta.url), 'utf8');
const builder = readFileSync(new URL('../build-synology-cloud-import.py', import.meta.url), 'utf8');

test('cloudimport accepteert alleen het expliciete Machinepark exportformaat', () => {
  assert.match(page, /synology-cloud-config-v1/);
  assert.match(page, /Machinepark/);
  assert.match(page, /schema/);
});

test('cloudimport werkt met blokupload om PHP uploadlimieten te ontwijken', () => {
  assert.match(page, /action === 'begin'/);
  assert.match(page, /action === 'chunk'/);
  assert.match(page, /action === 'finalize'/);
  assert.match(page, /MP_CLOUD_CHUNK_MAX/);
  assert.match(page, /file\.slice/);
});

test('lokale configuratie en handleidingen krijgen eerst een veiligheidsback-up', () => {
  assert.match(page, /cloud-import-before-/);
  assert.match(page, /cloud_copy_file_if_exists/);
  assert.match(page, /cloud_copy_dir\(MP_CLOUD_MANUAL_DIR/);
});

test('Clerk-gebruikers overschrijven geen lokale wachtwoorden', () => {
  assert.match(page, /cloud-users-v1\.json/);
  assert.match(page, /passwordHash/);
  assert.doesNotMatch(page, /\['passwordHash'\]\s*=/);
  assert.match(page, /matchedLocal/);
  assert.match(page, /unmatched/);
});

test('handleiding-PDFs worden gevalideerd en lokaal opgeslagen', () => {
  assert.match(page, /%PDF-/);
  assert.match(page, /manual-files\//);
  assert.match(page, /MP_CLOUD_MANUAL_DIR/);
  assert.match(page, /base64_decode/);
});

test('oude auditregels worden niet-reversibel geïmporteerd', () => {
  assert.match(page, /reversibleSchema.*0/s);
  assert.match(page, /importedFromCloud/);
  assert.match(page, /unset\(\$change\['undo'\]\)/);
});

test('Beheer linkt naar de lokale cloudimportpagina', () => {
  assert.match(builder, /synology\/import-cloud\.php/);
  assert.match(builder, /Resterende cloudgegevens importeren/);
});
