import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = path => fs.readFileSync(path, 'utf8');
const html = read('index.html');
const buildJs = read('assets/machinepark-build.js');
const builtUiSource = `${html}\n${buildJs}`;

test('samengestelde documenten staan alleen via Beheer in een apart overzichtsvenster', () => {
  assert.match(builtUiSource, /id="openComposedDocuments"[^>]*>Samengesteld overzicht maken</);
  assert.match(builtUiSource, /windowEl\.id=['"]composedDocumentsWindow['"]/);
  assert.match(builtUiSource, />Samengestelde documenten</);
  assert.match(builtUiSource, /Naam \/ firma van het document/);
  assert.match(builtUiSource, /Zoek firma, locatie of toestel/);
  assert.match(builtUiSource, /data-composed-device/);
});

test('opgeslagen samengestelde documenten hebben alle gevraagde acties', () => {
  for (const action of ['view', 'mail', 'print', 'pdf', 'delete']) {
    assert.match(builtUiSource, new RegExp(`data-composed-action="${action}"`));
  }
  for (const label of ['Bekijken', 'E-mailen', 'Afdrukken', 'PDF opslaan', 'Wissen']) {
    assert.ok(builtUiSource.includes(label), `${label} ontbreekt`);
  }
});

test('samengesteld document bewaart een momentopname met historiek en onderdelen', () => {
  for (const needle of [
    'composedSnapshot',
    'locationHistory',
    'Serviceverslagen / servicebezoeken',
    'Onderhoud, depannages en andere services',
    'Alle ooit gebruikte onderdelen voor dit toestel',
    'Totaal gebruikte onderdelen',
    'usedParts',
    'oneOffParts',
  ]) assert.ok(builtUiSource.includes(needle), `${needle} ontbreekt`);
});

test('samengestelde documenten synchroniseren veilig en oudere clients wissen ze niet', () => {
  const permissions = read('netlify/functions/_shared/permissions.mjs');
  const netlifyData = read('netlify/functions/machinepark-data.mjs');
  const synologyData = read('synology/api/machinepark-data.php');
  assert.ok(permissions.includes("composedDocuments"));
  assert.ok(permissions.includes("view.settings"));
  assert.ok(netlifyData.includes('previousData?.composedDocuments'));
  assert.ok(synologyData.includes("$data['composedDocuments']"));
  assert.ok(synologyData.includes("$before['composedDocuments']"));
});

test('Synology gebruikt voor samengestelde PDF een lokale jsPDF-library', () => {
  assert.ok(html.includes('./vendor/jspdf.umd.min.js'));
  assert.ok(!html.includes('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js'));
});
