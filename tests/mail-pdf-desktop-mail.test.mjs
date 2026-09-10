import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const builder = readFileSync(new URL('../build-mail-pdf-desktop-mail.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('desktop Mail PDF opent standaard mailprogramma en slaat systeemdelen over', () => {
  assert.match(builder,/machinepark-desktop-mail-client-v1/);
  assert.match(builder,/function machineparkMailUsesNativeShare\(\)/);
  assert.match(builder,/navigator\.userAgentData\?\.mobile === true/);
  assert.match(builder,/if \(useNativeShare && canShareFile\)/);
  assert.match(builder,/window\.location\.href = mailto/);
  assert.match(builder,/Je standaard mailprogramma wordt geopend/);
  assert.match(builder,/Mail openen…/);
});

test('mobiele Mail PDF blijft de bestaande native deelroute gebruiken', () => {
  assert.match(builder,/Android\|iPhone\|iPod/);
  assert.match(builder,/navigator\.share\(shareData\)/);
  assert.match(builder,/navigator\.platform === 'MacIntel'/);
});

test('desktop mail patch draait direct na de bestaande Mail PDF builders', () => {
  assert.match(pkg.scripts.build,/build-mail-pdf-print-parity\.py && python3 build-mail-pdf-desktop-mail\.py/);
});
