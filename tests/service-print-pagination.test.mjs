import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const js = readFileSync(new URL('../service-visits.js', import.meta.url), 'utf8');
const css = readFileSync(new URL('../service-visits.css', import.meta.url), 'utf8');
const sessionsBuild = readFileSync(new URL('../build-service-work-sessions.py', import.meta.url), 'utf8');
const minutesBuild = readFileSync(new URL('../build-work-minutes.py', import.meta.url), 'utf8');

test('afdruk heeft een apart totaaloverzicht en aparte detailpagina’s', () => {
  assert.match(js, /service-report-print-summary/);
  assert.match(js, /service-report-print-location-summary/);
  assert.match(js, /Totaaloverzicht werkzaamheden/);
  assert.match(js, /service-report-print-details/);
  assert.match(js, /function printRecordPageHtml/);
  assert.match(js, /service-report-print-record-page/);
});

test('schermweergave behoudt locatie-details en print-only inhoud blijft verborgen', () => {
  assert.match(js, /service-report-screen-locations/);
  assert.match(js, /service-report-screen-total/);
  assert.match(css, /\.service-report-print-only,\.service-report-print-details,\.service-report-print-location-summary\{display:none\}/);
  assert.match(css, /\.service-report-screen-locations,\.service-report-screen-total\{display:none!important\}/);
});

test('elk onderhoud depannage of andere werken start op een nieuwe afdrukpagina', () => {
  assert.match(css, /\.service-report-print-record-page\{[^}]*break-before:page;page-break-before:always/);
  assert.match(css, /\.service-report-print-summary\{break-after:page;page-break-after:always\}/);
  assert.match(js, /svKindLabel\(row\.kind,item\)/);
});

test('afdruk gebruikt donkere tekst kaders tabellen en werksoortlabels', () => {
  assert.match(css, /body\.service-visit-printing\{background:#fff!important;color:#111!important\}/);
  assert.match(css, /border:1\.4px solid #555!important/);
  assert.match(css, /background:#dededb!important/);
  assert.match(css, /background:#183f35!important;color:#fff!important/);
  assert.match(css, /background:#24485d!important/);
  assert.match(css, /background:#6b2d2d!important/);
  assert.match(css, /background:#4b3c67!important/);
});

test('totaaloverzicht toont aantallen per locatie zonder detailblokken erin', () => {
  const start=js.indexOf('function reportHtml(report)');
  const end=js.indexOf('function workOrderText',start);
  const report=js.slice(start,end);
  assert.match(report, /<th>Onderhoud<\/th><th>Depannage<\/th><th>Andere werken<\/th>/);
  assert.match(report, /visit\.maintenanceCount/);
  assert.match(report, /visit\.breakdownCount/);
  assert.match(report, /visit\.otherWorkCount/);
  const summaryEnd=report.indexOf('<div class="service-report-screen-locations">');
  const summary=report.slice(0,summaryEnd);
  assert.doesNotMatch(summary, /recordSummary\(row\.kind/);
});


test('detailpagina toont volledige servicetijd en uniek toestelaantal', () => {
  assert.match(js, /Servicetijd \/ toestellen/);
  assert.match(js, /sessions=visitWorkSessions\(visit\)/);
  assert.match(js, /serviceMinutes=sessions\.reduce/);
  assert.match(js, /deviceCount=Math\.max\(1,Number\(visit\.deviceCount\)/);
  assert.match(js, /formatWorkDuration\(serviceMinutes\)/);
  const detail=js.slice(js.indexOf('function printRecordPageHtml'),js.indexOf('function reportHtml'));
  assert.doesNotMatch(detail, /Datum \/ werkuren/);
  assert.doesNotMatch(detail, /serviceItemMinutes/);
});

test('serviceverslag heeft geen aparte tijdinvoer meer per toestel', () => {
  assert.match(js, /Servicetijd voor volledige actieve locatie/);
  assert.match(js, /Per locatie voer je de servicetijd één keer in/);
  assert.doesNotMatch(js, /sv-maintenance-hours/);
  assert.doesNotMatch(js, /sv-breakdown-hours/);
  assert.doesNotMatch(js, /sv-other-hours/);
  assert.doesNotMatch(js, /Werkminuten op dit onderhoud/);
  assert.doesNotMatch(js, /Werkminuten op deze depannage/);
  assert.doesNotMatch(js, /Werkminuten op deze werkzaamheid/);
  assert.match(js, /serviceVisitDeviceCount:deviceCount\|\|batchSize/);
  assert.match(js, /serviceVisitTotalMinutes:totalMinutes/);
  assert.match(js, /hours:totalMinutes\/60/);
});

test('onderdelen staan in details in een eigen kader binnen de werkzaamhedenkaart', () => {
  assert.match(js, /function recordPartsBoxHtml/);
  assert.match(js, /service-record-parts-box/);
  assert.match(js, /Onderdelen voor deze werkzaamheid/);
  assert.match(js, /Geen onderdelen gebruikt\./);
  assert.match(js, /Eenmalig \/ leverancier/);
  assert.match(js, /\$\{recordPartsBoxHtml\(item\)\}/);
});

test('onderdelenkader krijgt ook duidelijke printopmaak', () => {
  assert.match(css, /\.service-record-parts-box\{/);
  assert.match(css, /\.service-record-parts-title\{/);
  assert.match(css, /\.service-record-parts-table\{/);
  assert.match(css, /\.service-visit-print-sheet \.service-record-parts-box\{/);
  assert.match(css, /\.service-visit-print-sheet \.service-record-parts-title\{/);
});


test('gedeelde servicetijd blijft in minuten en totalen blijven uit workSessions komen', () => {
  assert.match(js, /return total>0\?\`\$\{total\} min\`:'—'/);
  const totals=js.slice(js.indexOf('function visitWorkSessions'),js.indexOf('function visitReportHtml'));
  assert.match(totals, /record\.item\?\.workSessions/);
  assert.match(totals, /Number\(session\?\.minutes\)/);
  assert.doesNotMatch(totals, /serviceItemMinutes/);
});

test('los Onderhoud Depannage en Andere werken behouden hun eigen tijdregistratie', () => {
  assert.match(sessionsBuild, /kind!=='servicevisit'/);
  assert.match(sessionsBuild, /if\(record\?\.serviceVisitId && kind!=='servicevisit'\)/);
  assert.match(sessionsBuild, /return \`<div class="field full service-work-sessions" data-service-work-sessions><label>Werkdagen en tijd<\/label>/);
  assert.match(minutesBuild, /Werkminuten depannage \*/);
  assert.match(minutesBuild, /Werkminuten onderhoud \*/);
});

