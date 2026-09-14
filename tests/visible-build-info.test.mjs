import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const index = readFileSync('index.html', 'utf8');
const builder = readFileSync('build-visible-build-info.py', 'utf8');
const workflow = readFileSync('.github/workflows/synology-deploy.yml', 'utf8');
const serviceWorker = readFileSync('sw.js', 'utf8');
const packageJson = JSON.parse(readFileSync('package.json', 'utf8'));
const escapedVersion = packageJson.version.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

test('zichtbare versie volgt package.json en toont Synology buildmetadata', () => {
  assert.match(packageJson.version, /^\d+\.\d+\.\d+$/);
  assert.match(index, /data-machinepark-build-info="visible-build-info-v1"/);
  assert.match(index, new RegExp(`id="machineparkVersion">v${escapedVersion}<`));
  assert.match(index, /id="machineparkBuildMeta"/);
  assert.match(index, /deploy-meta\.json\?machineparkBuildInfo=/);
  assert.match(index, /meta\.app_version/);
  assert.match(index, /meta\.built_at/);
  assert.match(index, /meta\.source_sha/);
  assert.doesNotMatch(index, /<br><br>v1\.64 • Export inclusief afbeeldingen/);
});

test('buildinformatie toont Belgische lokale datum en tijd tot op de seconde en ververst zonder versiebump', () => {
  assert.match(builder, /new Intl\.DateTimeFormat\('nl-BE'/);
  assert.match(builder, /timeZone: 'Europe\/Brussels'/);
  assert.match(builder, /hour: '2-digit', minute: '2-digit', second: '2-digit'/);
  assert.match(builder, /toLocaleString\('nl-BE', \{ timeZone: 'Europe\/Brussels' \}\)/);
  assert.match(builder, /fetch\('\.\/deploy-meta\.json\?machineparkBuildInfo=' \+ Date\.now\(\), \{ cache: 'no-store' \}\)/);
  assert.match(builder, /SCRIPT_MARKER/);
  assert.match(builder, /script_pattern\.subn\(script, text, count=1\)/);
  assert.match(workflow, /"built_at": datetime\.now\(timezone\.utc\)\.isoformat\(\)/);
  assert.match(workflow, /"source_sha": os\.environ\["SOURCE_SHA"\]/);
  assert.match(serviceWorker, /url\.pathname==='\/deploy-meta\.json'\|\|url\.pathname\.endsWith\('\/deploy-meta\.json'\)/);
  assert.match(serviceWorker, /fetch\(e\.request,\{cache:'no-store'\}\)/);
});

test('build-info builder draait vóór inline scripts worden gecontroleerd en uitgepakt', () => {
  const chain = packageJson.scripts.build;
  assert.match(chain, /python3 build-visible-build-info\.py/);
  assert.ok(chain.indexOf('python3 build-visible-build-info.py') < chain.indexOf('python3 scripts/check-inline-scripts.py'));
  assert.match(builder, /LOCAL_FOOTER/);
  assert.match(builder, /CENTRAL_FOOTER/);
  assert.match(builder, /deploy-meta\.json\?machineparkBuildInfo=/);
});
