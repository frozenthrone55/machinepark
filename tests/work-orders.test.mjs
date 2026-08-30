import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-work-orders.py', import.meta.url), 'utf8');
const endpoint = readFileSync(new URL('../netlify/functions/work-order-templates.mjs', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('werkbontemplates zijn centraal en alleen door beheerder wijzigbaar', () => {
  assert.ok(endpoint.includes("const CONFIG_KEY = 'work-order-templates-v1'"));
  assert.ok(endpoint.includes("access?.role === 'beheerder'"));
  assert.ok(endpoint.includes("Alleen een beheerder kan werkbonnen configureren."));
  assert.ok(endpoint.includes("onlyIfMatch"));
  assert.ok(endpoint.includes("templateVersion") === false, 'template endpoint bewaart templates, geen ingevulde records');
});

test('werkbontemplates ondersteunen professionele veldtypes en versiebeheer', () => {
  for (const needle of ["'text'", "'textarea'", "'number'", "'checkbox'", "'select'", "'date'"]) {
    assert.ok(endpoint.includes(needle), `Veldtype ontbreekt: ${needle}`);
  }
  assert.ok(endpoint.includes('Math.max(1, Number(existing.version || 1)) + 1'));
  assert.ok(endpoint.includes('brands:'));
  assert.ok(endpoint.includes('models:'));
});

test('beheerder krijgt werkbonconfiguratie en nieuwe werkbonactie', () => {
  assert.ok(build.includes('workOrderSettingsCard'));
  assert.ok(build.includes('Werkbonnen configureren'));
  assert.ok(build.includes('+ Nieuwe werkbon'));
  assert.ok(build.includes('Configureren'));
  assert.ok(build.includes('Kopiëren'));
  assert.ok(build.includes('Verwijderen'));
});

test('onderhoud kiest per machine exact een werkbon en bewaart snapshot', () => {
  assert.ok(build.includes('Kies de exacte bon voor deze machine'));
  assert.ok(build.includes('maintenance-machine-card'));
  assert.ok(build.includes("storeName === 'maintenance'"));
  assert.ok(build.includes('templateId:'));
  assert.ok(build.includes('templateName:'));
  assert.ok(build.includes('templateVersion:'));
  assert.ok(build.includes('capturedAt:'));
  assert.ok(build.includes('Bewaarde werkbon'));
});

test('werkbon komt mee in details tijdlijn en afdruk', () => {
  assert.ok(build.includes('workOrderDetailsHtml'));
  assert.ok(build.includes('workOrderTimelineHtml'));
  assert.ok(build.includes('servicePrintWorkOrder'));
  assert.ok(build.includes('${fields}${servicePrintWorkOrder(record)}${servicePrintPhotos(record)}'));
  assert.ok(build.includes("${workOrderTimelineHtml(m.workOrder)}${deviceTimelinePhotosHtml(m.photos,'Onderhoudsfoto')}"));
});

test('werkbonmodule zit in build en server syntaxcheck', () => {
  assert.ok(packageJson.scripts.build.includes('python3 build-work-orders.py'));
  assert.ok(packageJson.scripts['check:functions'].includes('netlify/functions/work-order-templates.mjs'));
});
