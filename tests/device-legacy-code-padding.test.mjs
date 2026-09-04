import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const builder = fs.readFileSync(new URL('../build-device-legacy-code-padding.py', import.meta.url), 'utf8');
const pkg = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('alle bestaande toestelcodes met exact drie cijfers worden eenmalig naar vier cijfers gecorrigeerd', () => {
  assert.doesNotMatch(html, /\"assetCode\":\"[A-Za-z]+\d{3}\"/);
  for (const [oldCode, newCode] of [['WCL501','WCL0501'], ['WCL510','WCL0510'], ['WCL559','WCL0559']]) {
    assert.equal(html.includes(`\"assetCode\":\"${oldCode}\"`), false, `${oldCode} mag niet meer als assetCode voorkomen`);
    assert.equal(html.includes(`\"assetCode\":\"${newCode}\"`), true, `${newCode} moet als gecorrigeerde assetCode voorkomen`);
  }
  assert.match(html, /const LEGACY_DEVICE_CODE_PATTERN=\/\^\(\[A-Z\]\+\)\(\\d\{3\}\)\$\//);
  assert.match(html, /const corrected=`\$\{match\[1\]\}0\$\{match\[2\]\}`/);
  assert.match(html, /await ensureLegacyDeviceCodeFixes\(\)/);
});

test('toekomstige toestelcodes blijven vrij invoerbaar zonder automatische padding', () => {
  assert.match(html, /assetCode:val\(fd,'assetCode'\)/);
  assert.doesNotMatch(html, /assetCode[^\n]{0,120}padStart\(/);
  assert.match(builder, /Dit is bewust GEEN algemene formatteringsregel/);
  assert.match(builder, /LEGACY_CUTOFF/);
  assert.ok(pkg.scripts.build.includes('python3 build-device-legacy-code-padding.py'));
});
