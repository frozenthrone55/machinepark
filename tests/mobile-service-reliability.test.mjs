import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const builder = readFileSync(new URL('../build-mobile-service-reliability.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

const build = pkg.scripts.build;

test('touchbediening voorkomt hover-first-tap gedrag op gsm', () => {
  assert.match(builder, /touch-action:manipulation/);
  assert.match(builder, /@media \(hover:none\), \(pointer:coarse\)/);
  assert.match(builder, /\.btn:hover\{transform:none !important/);
  assert.match(builder, /\.device-card:hover\{transform:none !important/);
});

test('serviceconcept herstelt gekoppelde ToDos uit header en werkelijk opgeslagen koppelingen', () => {
  assert.match(builder, /window\.machineparkLinkedActionIdsForService\(report\?\.id\|\|header\?\.draftReportId\|\|''\)/);
  assert.match(builder, /linkedActionIds:\[\.\.\.new Set\(\[/);
});

test('servicefinalisatie verliest geen ToDo door verouderde mobiele autosave', () => {
  assert.match(builder, /const requestedIds=/);
  assert.match(builder, /const storedIds=typeof linkedActionsForService==='function'/);
  assert.match(builder, /const ids=\[\.\.\.new Set\(\[\.\.\.requestedIds,\.\.\.storedIds\]\)\]/);
});

test('mobiele betrouwbaarheidspatch draait voor de centrale service-ToDo state-machine', () => {
  const mobileAt = build.indexOf('python3 build-mobile-service-reliability.py');
  const stateAt = build.indexOf('python3 build-service-todo-state-machine.py');
  assert.ok(mobileAt >= 0, 'mobiele servicepatch ontbreekt uit build');
  assert.ok(stateAt > mobileAt, 'centrale state-machine moet na mobiele koppelherstelpatch draaien');
});
