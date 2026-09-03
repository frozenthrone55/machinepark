import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const builder = fs.readFileSync(new URL('../build-negative-stock-allowed.py', import.meta.url), 'utf8');
const pkg = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('onderhoud en depannage worden niet geblokkeerd door onvoldoende voorraad', () => {
  assert.doesNotMatch(html, /const usage=collectUsage\(\),err=checkUsage\(usage,old\.usedParts\|\|\[\]\);if\(err\)\{alert\(err\);return\}/);
  assert.doesNotMatch(html, /const err=checkMaintenanceBatchUsage\(items\);if\(err\)\{alert\(err\);return\}/);
  assert.doesNotMatch(html, /const err=checkBreakdownBatchUsage\(items\);if\(err\)\{alert\(err\);return\}/);
  assert.match(html, /stock:Number\(p\.stock\|\|0\)-q/);
  assert.match(html, /stock:Number\(p\.stock\|\|0\)-qty/);
});

test('negatieve voorraad kan manueel en via Excel worden opgeslagen', () => {
  assert.match(html, /<input name="stock" type="number" step="1" value="\$\{p\.stock\?\?0\}">/);
  assert.doesNotMatch(html, /<input name="stock" type="number" step="1" min="0"/);
  assert.doesNotMatch(html, /Negatieve voorraad bij nieuw onderdeel/);
  assert.match(html, /const stock=stockNum===null\?\(old\?Number\(old\.stock\|\|0\):0\):Math\.round\(stockNum\);/);
  assert.match(html, /\(f==='zero'&&stock<=0\)/);
});

test('negatieve-voorraad buildstap blijft onderdeel van de build', () => {
  assert.match(builder, /negatieve voorraad toegestaan bij onderhoud, depannage, manuele stock en Excel-stocktelling/);
  assert.ok(pkg.scripts.build.includes('python3 build-negative-stock-allowed.py'));
});
