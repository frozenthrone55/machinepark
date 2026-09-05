import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../synology/migrate-data.php', import.meta.url), 'utf8');

test('migratiepagina is alleen lokaal beschikbaar', () => {
  assert.match(source, /is_local_ip/);
  assert.match(source, /alleen toegankelijk via het lokale IP-adres/);
});

test('migratiepagina overschrijft geen bestaande lokale database', () => {
  assert.match(source, /is_file\(MP_STATE_FILE\)/);
  assert.match(source, /Migratie is daarom geblokkeerd/);
  assert.match(source, /Niets is overschreven/);
});

test('migratie valideert Machinepark snapshot stores', () => {
  for (const field of ['parts','devices','maintenance','breakdowns']) {
    assert.match(source, new RegExp(field));
  }
  assert.match(source, /schema/);
  assert.match(source, /Machinepark/);
});

test('originele migratieback-up wordt apart bewaard', () => {
  assert.match(source, /migration-original-/);
  assert.match(source, /MP_BACKUP_DIR/);
});

test('database wordt atomair geschreven', () => {
  assert.match(source, /LOCK_EX/);
  assert.match(source, /rename\(\$tmp, MP_STATE_FILE\)/);
});
