import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const timeline = readFileSync(new URL('../build-action-machine-timeline.py', import.meta.url), 'utf8');

test('ToDo met specifiek toestel blijft beperkt tot dat toestel', () => {
  assert.match(timeline, /const actionDeviceId=String\(a\?\.deviceId\|\|''\)/);
  assert.match(timeline, /if\(actionDeviceId\)return actionDeviceId===currentDeviceId/);
});

test('alleen toestel-loze ToDo gebruikt servicekoppeling voor alle betrokken machines', () => {
  assert.match(timeline, /Alleen toestel-loze ToDo's mogen via een gekoppelde service/);
  assert.match(timeline, /serviceReportIds/);
  assert.match(timeline, /serviceReportId\|\|item\?\.serviceVisitId/);
});
