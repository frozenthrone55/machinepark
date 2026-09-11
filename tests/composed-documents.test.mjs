import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = path => fs.readFileSync(path, 'utf8');

test('samengestelde documenten staan alleen via Beheer in een apart overzichtsvenster', () => {
  const html = read('index.html');
  assert.match(html, /id="openComposedDocuments"[^>]*>Samengesteld overzicht maken</);
  assert.match(html, /id="composedDocumentsWindow"/);
  assert.match(html, />Samengestelde documenten</);
  assert.match(html, /Naam \/ firma van het document/);
  assert.match(html, /Zoek firma, locatie of toestel/);
  assert.match(html, /data-composed-device/);
});

test('opgeslagen samengestelde documenten hebben alle gevraagde acties', () => {
  const html = read('index.html');
  for (const action of ['view', 'mail', 'print', 'pdf', 'delete']) {
    assert.match(html, new RegExp(`data-composed-action="${action}"`));
  }
  for (const label of ['Bekijken', 'E-mailen', 'Afdrukken', 'PDF opslaan', 'Wissen']) {
    assert.ok(html.includes(label), `${label} ontbreekt`);
  }
});

test('samengesteld document bewaart een momentopname met historiek en onderdelen', () => {
  const html = read('index.html');
  for (const needle of [
    'composedSnapshot',
    'locationHistory',
    'Serviceverslagen / servicebezoeken',
    'Onderhoud, depannages en andere services',
    'Alle ooit gebruikte onderdelen voor dit toestel',
    'Totaal gebruikte onderdelen',
    'usedParts',
    'oneOffParts',
  ]) assert.ok(html.includes(needle), `${needle} ontbreekt`);
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
  const html = read('index.html');
  assert.ok(html.includes('./vendor/jspdf.umd.min.js'));
  assert.ok(!html.includes('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js'));
});
