import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const builder = fs.readFileSync(new URL('../build-negative-stock-allowed.py', import.meta.url), 'utf8');
const buildJs = fs.readFileSync(new URL('../assets/machinepark-build.js', import.meta.url), 'utf8');
const serviceVisits = fs.readFileSync(new URL('../service-visits.js', import.meta.url), 'utf8');
const builtSource = `${html}\n${buildJs}\n${serviceVisits}`;
const pkg = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('onderhoud en depannage worden niet geblokkeerd door onvoldoende voorraad', () => {
  assert.doesNotMatch(builtSource, /const usage=collectUsage\(\),err=checkUsage\(usage,old\.usedParts\|\|\[\]\);if\(err\)\{alert\(err\);return\}/);
  assert.doesNotMatch(builtSource, /const err=checkMaintenanceBatchUsage\(items\);if\(err\)\{alert\(err\);return\}/);
  assert.doesNotMatch(builtSource, /const err=checkBreakdownBatchUsage\(items\);if\(err\)\{alert\(err\);return\}/);
  assert.match(builtSource, /stock:Number\(p\.stock\|\|0\)-q/);
  assert.match(builtSource, /stock:Number\(p\.stock\|\|0\)-qty/);
});

test('serviceconcepten mogen onderdelen onder nul brengen', () => {
  assert.doesNotMatch(builtSource, /if \(Number\(part\.stock \|\| 0\) < qty\) throw new Error\(`Onvoldoende voorraad/);
  assert.match(builtSource, /stock:Number\((?:part|p)\.stock\s*\|\|\s*0\)\s*-\s*qty/);
  assert.doesNotMatch(serviceVisits, /if\(Number\(p\.stock\|\|0\)<qty\)throw new Error/);
});

test('negatieve voorraad kan manueel en via Excel worden opgeslagen', () => {
  assert.match(builtSource, /<input name="stock" type="number" step="1" value="\$\{p\.stock\?\?0\}">/);
  assert.doesNotMatch(builtSource, /<input name="stock" type="number" step="1" min="0"/);
  assert.doesNotMatch(builtSource, /Negatieve voorraad bij nieuw onderdeel/);
  assert.match(builtSource, /const stock=stockNum===null\?\(old\?Number\(old\.stock\|\|0\):0\):Math\.round\(stockNum\);/);
  assert.match(builtSource, /\(f==='zero'&&stock<=0\)/);
});

test('negatieve-voorraad buildstap blijft onderdeel van de build', () => {
  assert.match(builder, /negatieve voorraad toegestaan bij onderhoud, depannage, concepten, manuele stock en Excel-stocktelling/);
  assert.match(builder, /voorraadblokkade bij serviceconcept afronden/);
  assert.ok(pkg.scripts.build.includes('python3 build-negative-stock-allowed.py'));
});
