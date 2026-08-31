import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-breakdown-details.py', import.meta.url), 'utf8');
const js = readFileSync(new URL('../assets/machinepark-build.js', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('depannage details openen niet rechtstreeks het bewerkformulier', () => {
  assert.ok(build.includes('machineparkShowBreakdownDetails'));
  assert.ok(build.includes("window.machineparkShowBreakdownDetails(b.dataset.editBreakdown)"));
  assert.ok(build.includes("window.machineparkShowBreakdownDetails(gb.dataset.globalBreakdown)"));
});

test('depannagedetails hebben een aparte bewerkknop met rechtencontrole', () => {
  assert.ok(js.includes('Depannagedetails'));
  assert.ok(js.includes('editBreakdownFromDetails'));
  assert.ok(js.includes('canEditBreakdown'));
  assert.ok(js.includes("edit.textContent = 'Bewerken'"));
  assert.ok(js.includes('closeModal(); openBreakdown(id);'));
});

test('depannagedetails tonen de operationele verslaginformatie', () => {
  for (const needle of ['Werkdagen en tijd','Probleem / melding','Diagnose','Oplossing / uitgevoerde werken','Gebruikte onderdelen','Foto’s bij verslag']) {
    assert.ok(js.includes(needle), `ontbreekt: ${needle}`);
  }
  assert.ok(js.includes('machineparkServiceWorkSessionsText'));
  assert.ok(js.includes('data-photo-lightbox'));
});

test('gebruikte onderdelen staan in depannagedetails elk op een eigen regel', () => {
  assert.ok(build.includes('breakdown-detail-parts'));
  assert.ok(build.includes('breakdown-detail-part'));
  assert.ok(build.includes('usedPartsText([part])'));
  assert.ok(js.includes('breakdown-detail-parts'));
  assert.ok(js.includes('breakdown-detail-part'));
});

test('depannagedetails draaien na de werktijdensessies in de build', () => {
  const script = packageJson.scripts.build;
  assert.ok(script.includes('python3 build-breakdown-details.py'));
  assert.ok(script.indexOf('build-service-work-sessions.py') < script.indexOf('build-breakdown-details.py'));
  assert.ok(script.indexOf('build-breakdown-details.py') < script.indexOf('scripts/extract-build-assets.py'));
});
