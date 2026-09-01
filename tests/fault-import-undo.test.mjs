import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const endpoint = readFileSync(new URL('../netlify/functions/fault-library.mjs', import.meta.url), 'utf8');
const build = readFileSync(new URL('../build-fault-import-undo.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('Beheer heeft een knop om de laatste storingsimport ongedaan te maken', () => {
  assert.match(build, /undoFaultExcelImportBtn/);
  assert.match(build, /Laatste import ongedaan maken/);
  assert.match(build, /action: 'undo-last-import'/);
});

test('voor iedere import wordt de toestand vóór de import als servermomentopname bewaard', () => {
  assert.match(endpoint, /FAULT_IMPORT_UNDO_KEY/);
  assert.match(endpoint, /stageFaultImportUndo/);
  assert.match(endpoint, /before: normalizeConfig\(config\)/);
  assert.match(endpoint, /finalizeFaultImportUndo/);
  assert.match(endpoint, /afterEtag: saved\?\.etag/);
});

test('undo weigert wanneer na de import nog andere storingswijzigingen zijn gebeurd', () => {
  assert.match(endpoint, /snapshot\.afterEtag !== etag/);
  assert.match(endpoint, /na deze import nog gewijzigd/);
});

test('undo herstelt exact de pre-importbibliotheek en kan niet dubbel worden uitgevoerd', () => {
  assert.match(endpoint, /saveConfig\(store, snapshot\.before, etag, etag\)/);
  assert.match(endpoint, /status: 'undone'/);
  assert.match(endpoint, /writeImportUndoAudit/);
  assert.match(endpoint, /snapshot\.status !== 'ready'/);
});

test('versie 1.68.9 bouwt storingsimport-undo mee', () => {
  assert.equal(packageJson.version, '1.68.9');
  assert.match(packageJson.scripts.build, /build-fault-import-undo\.py/);
  assert.match(html, /Storingsbibliotheek/);
});
