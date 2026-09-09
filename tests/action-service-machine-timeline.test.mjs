import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const timeline = readFileSync(new URL('../build-action-machine-timeline.py', import.meta.url), 'utf8');

test('servicegekoppelde ToDo verschijnt op alle machines uit het serviceverslag', () => {
  assert.match(timeline, /actionBelongsToDevice/);
  assert.match(timeline, /serviceReportIds/);
  assert.match(timeline, /state\.maintenance/);
  assert.match(timeline, /state\.breakdowns/);
  assert.match(timeline, /item\?\.deviceId/);
  assert.match(timeline, /serviceReportId\|\|item\?\.serviceVisitId/);
});

test('machinetijdlijn volgt servicewijzigingen dynamisch en negeert conceptregels', () => {
  assert.match(timeline, /item\?\.isDraft===true/);
  assert.match(timeline, /linkedServiceIds\.has\(reportId\)/);
  assert.doesNotMatch(timeline, /put\(['"]timeline/);
});
