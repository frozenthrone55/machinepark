import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const builder = readFileSync(new URL('../build-mail-pdf-desktop-mail.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
const packager = readFileSync(new URL('../scripts/package-synology-runtime.py', import.meta.url), 'utf8');

test('Windows Mail PDF gebruikt Outlook Classic bridge met automatische PDF-bijlage', () => {
  assert.match(builder,/machinepark-outlook-classic-bridge-v2/);
  assert.match(builder,/function machineparkIsWindowsDesktop\(\)/);
  assert.match(builder,/function machineparkOpenOutlookClassic\(file, title\)/);
  assert.match(builder,/machinepark-outlook:\/\/compose\?file=/);
  assert.match(builder,/downloadFile\(attachment\)/);
  assert.match(builder,/Outlook openen…/);
});

test('Outlook Classic setup registreert lokaal protocol en voegt alleen recente Machinepark PDF toe', () => {
  assert.match(builder,/HKCU:\\\\Software\\\\Classes\\\\machinepark-outlook/);
  assert.match(builder,/MachineparkOutlookBridge\.ps1/);
  assert.match(builder,/New-Object -ComObject Outlook\.Application/);
  assert.match(builder,/\$mail\.Attachments\.Add\(\$pdf\.FullName\)/);
  assert.match(builder,/StartsWith\('Machinepark_'/);
  assert.match(builder,/NameSpace\('shell:Downloads'\)/);
  assert.match(builder,/LastWriteTimeUtc/);
});

test('Beheer toont eenmalige Outlook Classic koppelknop op Windows desktop', () => {
  assert.match(builder,/machineparkOutlookClassicSetupCard/);
  assert.match(builder,/Outlook Classic koppelen/);
  assert.match(builder,/machinepark-outlook-classic-setup\.cmd/);
  assert.match(builder,/geen administratorrechten nodig/i);
});

test('mobiele Mail PDF blijft de bestaande native deelroute gebruiken', () => {
  assert.match(builder,/Android\|iPhone\|iPod/);
  assert.match(builder,/navigator\.share\(shareData\)/);
  assert.match(builder,/navigator\.platform === 'MacIntel'/);
  assert.match(builder,/if \(useNativeShare && canShareFile\)/);
});

test('Outlook setupbestand wordt in Synology runtime verpakt', () => {
  assert.match(packager,/machinepark-outlook-classic-setup\.cmd/);
});

test('desktop mail patch draait direct na de bestaande Mail PDF builders', () => {
  assert.match(pkg.scripts.build,/build-mail-pdf-print-parity\.py && python3 build-mail-pdf-desktop-mail\.py/);
});
