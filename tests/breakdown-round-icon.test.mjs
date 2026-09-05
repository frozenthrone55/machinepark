import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const patch = readFileSync(new URL('../build-breakdown-round-icon.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('Depannages-menu gebruikt een ronde contour met uitroepteken', () => {
  assert.match(patch, /breakdown-nav-icon-svg/);
  assert.match(patch, /<circle cx=\"12\" cy=\"12\" r=\"8\.5\"><\/circle>/);
  assert.match(patch, /<path d=\"M12 7\.5v6\"><\/path>/);
  assert.match(patch, /<path d=\"M12 16\.5h\.01\"><\/path>/);
  assert.match(patch, /driehoekicoon staat nog in Depannages-menu/);
});

test('rond depannage-icoon wordt vóór assetextractie gebouwd', () => {
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-breakdown-round-icon\.py/);
  assert.ok(chain.indexOf('build-breakdown-round-icon.py') < chain.indexOf('scripts/extract-build-assets.py'));
});
