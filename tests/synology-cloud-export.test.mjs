import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-synology-cloud-export.py', import.meta.url), 'utf8');

test('cloudexport haalt alle resterende centrale configuratie op', () => {
  for (const endpoint of [
    'role-management',
    'fault-library',
    'work-order-templates',
    'manual-library',
    'user-management',
    'audit-log',
  ]) {
    assert.ok(build.includes(endpoint), endpoint + ' ontbreekt');
  }
});

test('cloudexport neemt handleiding-PDFs mee als base64', () => {
  assert.match(build, /cloudGetPdf/);
  assert.match(build, /arrayBuffer/);
  assert.match(build, /btoa\(binary\)/);
  assert.match(build, /files\[manual\.fileKey\]/);
});

test('historisch logboek wordt alleen niet-reversibel geëxporteerd', () => {
  assert.match(build, /cleanAuditEntries/);
  assert.match(build, /reversible: false/);
  assert.match(build, /const \{ undo, reversible, linkedUndoCount/);
});

test('exportbestand is herkenbaar voor Synology-import', () => {
  assert.match(build, /synology-cloud-config-v1/);
  assert.match(build, /Machinepark_Synology_CloudExport_/);
});
