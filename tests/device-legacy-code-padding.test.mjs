import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const builder = fs.readFileSync(new URL('../build-device-legacy-code-padding.py', import.meta.url), 'utf8');
const pkg = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('bestaande WCL501-WCL559 codes worden eenmalig naar vier cijfers gecorrigeerd', () => {
  for (let n = 501; n <= 559; n += 1) {
    assert.equal(html.includes(`\"assetCode\":\"WCL${n}\"`), false, `WCL${n} mag niet meer als assetCode voorkomen`);
    assert.equal(html.includes(`\"assetCode\":\"WCL0${n}\"`), true, `WCL0${n} moet als gecorrigeerde assetCode voorkomen`);
  }
  assert.match(html, /const LEGACY_DEVICE_CODE_FIXES=Object\.freeze\(/);
  assert.match(html, /const corrected=LEGACY_DEVICE_CODE_FIXES\[current\]/);
  assert.match(html, /await ensureLegacyDeviceCodeFixes\(\)/);
});

test('toekomstige toestelcodes blijven vrij invoerbaar zonder automatische padding', () => {
  assert.match(html, /assetCode:val\(fd,'assetCode'\)/);
  assert.doesNotMatch(html, /assetCode[^\n]{0,120}padStart\(/);
  assert.match(builder, /Dit is bewust GEEN algemene formatteringsregel/);
  assert.ok(pkg.scripts.build.includes('python3 build-device-legacy-code-padding.py'));
});
