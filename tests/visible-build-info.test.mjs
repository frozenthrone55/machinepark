import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const index = readFileSync('index.html', 'utf8');
const builder = readFileSync('build-visible-build-info.py', 'utf8');
const packageJson = JSON.parse(readFileSync('package.json', 'utf8'));

test('zichtbare versie volgt package.json en toont Synology buildmetadata', () => {
  assert.equal(packageJson.version, '1.68.11');
  assert.match(index, /data-machinepark-build-info="visible-build-info-v1"/);
  assert.match(index, /id="machineparkVersion">v1\.68\.11</);
  assert.match(index, /id="machineparkBuildMeta"/);
  assert.match(index, /deploy-meta\.json\?machineparkBuildInfo=/);
  assert.match(index, /meta\.app_version/);
  assert.match(index, /meta\.built_at/);
  assert.match(index, /meta\.source_sha/);
  assert.doesNotMatch(index, /<br><br>v1\.64 • Export inclusief afbeeldingen/);
});

test('build-info builder draait vóór inline scripts worden gecontroleerd en uitgepakt', () => {
  const chain = packageJson.scripts.build;
  assert.match(chain, /python3 build-visible-build-info\.py/);
  assert.ok(chain.indexOf('python3 build-visible-build-info.py') < chain.indexOf('python3 scripts/check-inline-scripts.py'));
  assert.match(builder, /OLD_FOOTER/);
  assert.match(builder, /deploy-meta\.json\?machineparkBuildInfo=/);
});
