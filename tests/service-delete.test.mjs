import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const buildJs = readFileSync(new URL('../assets/machinepark-build.js', import.meta.url), 'utf8');
const builtSource = `${html}\n${buildJs}`;
const breakdownDetails = readFileSync(new URL('../build-breakdown-details.py', import.meta.url), 'utf8');
const cleanup = readFileSync(new URL('../netlify/functions/_shared/photo-cleanup.mjs', import.meta.url), 'utf8');

test('depannagedetails hebben net als onderhoud een verwijderknop', () => {
  assert.match(breakdownDetails, /deleteBreakdownFromDetails/);
  assert.match(breakdownDetails, /breakdowns\.delete/);
  assert.match(breakdownDetails, /deleteServiceRecord\('breakdowns', id\)/);
});

test('verwijderen van onderhoud of depannage herstelt voorraad atomair', () => {
  assert.match(builtSource, /if\(!\['maintenance','breakdowns'\]\.includes\(storeName\)\)/);
  assert.match(builtSource, /db\.transaction\(\[storeName,'parts'\],'readwrite'\)/);
  assert.match(builtSource, /stock:Number\(part\.stock\|\|0\)\+qty/);
  assert.match(builtSource, /records\.delete\(record\.id\)/);
});

test('verwijdering benoemt en verwerkt alle gekoppelde depannagegegevens', () => {
  for (const needle of [
    'record?.oneOffParts',
    'record?.workSessions',
    'record?.workOrder',
    'record?.photos',
    'automatisch terug op voorraad gezet',
    'alle gekoppelde gegevens worden samen gesynchroniseerd',
  ]) assert.ok(builtSource.includes(needle), `Ontbreekt bij serviceverwijdering: ${needle}`);
});

test('centrale foto-opruiming verwijdert ook depannagefoto’s', () => {
  assert.match(cleanup, /collections = \['devices', 'parts', 'maintenance', 'breakdowns'\]/);
  assert.match(cleanup, /SERVICE_PHOTO_PREFIX\}breakdowns/);
});
