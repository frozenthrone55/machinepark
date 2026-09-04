import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const js = readFileSync(new URL('../service-visits.js', import.meta.url), 'utf8');
const css = readFileSync(new URL('../service-visits.css', import.meta.url), 'utf8');

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


test('detailpagina toont datum met werkduur in plaats van kloktijd', () => {
  assert.match(js, /Datum \/ werkuren/);
  assert.match(js, /function recordWorkMinutesForDate/);
  assert.match(js, /function formatWorkDuration/);
  assert.match(js, /workMinutes=recordWorkMinutesForDate\(item,workDate\)/);
  assert.match(js, /formatWorkDuration\(workMinutes\)/);
  const start=js.indexOf('function printRecordPageHtml');
  const end=js.indexOf('function reportHtml',start);
  const detail=js.slice(start,end);
  assert.doesNotMatch(detail, /Datum \/ uur/);
  assert.doesNotMatch(detail, /item\.time\|\|visit\.time\|\|report\.time/);
});


test('werkminuten worden per afzonderlijke servicewerkzaamheid zonder omzetting bewaard en afgedrukt', () => {
  assert.match(js, /sv-maintenance-hours/);
  assert.match(js, /sv-breakdown-hours/);
  assert.match(js, /sv-other-hours/);
  assert.match(js, /Werkminuten op dit onderhoud/);
  assert.match(js, /Werkminuten op deze depannage/);
  assert.match(js, /Werkminuten op deze werkzaamheid/);
  assert.match(js, /serviceItemMinutes:Math\.max\(0,Math\.round\(Number\(panel\?\.querySelector\('\.sv-maintenance-hours'\)\?\.value\|\|0\)\)\)/);
  assert.match(js, /serviceItemMinutes:Math\.max\(0,Math\.round\(Number\(panel\?\.querySelector\('\.sv-breakdown-hours'\)\?\.value\|\|0\)\)\)/);
  assert.match(js, /serviceItemMinutes:Math\.max\(0,Math\.round\(Number\(panel\?\.querySelector\('\.sv-other-hours'\)\?\.value\|\|0\)\)\)/);
  assert.match(js, /serviceItemMinutesUnit:'minutes'/);
  assert.match(js, /const itemMinutes=serviceItemMinutesValue\(item\)/);
  assert.match(js, /hours:\(itemMinutes>0\?itemMinutes:totalMinutes\)\/60/);
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


test('werkduur op detailpagina wordt altijd in minuten getoond zonder nieuwe omzetting', () => {
  assert.match(js, /function serviceItemMinutesValue/);
  assert.match(js, /if\(item\?\.serviceItemMinutesUnit==='minutes'\)return Math\.round\(raw\)/);
  assert.match(js, /return Math\.round\(raw\/60\)/);
  assert.match(js, /const storedMinutes=Number\(item\?\.hours\|\|0\)/);
  assert.match(js, /return storedMinutes>0\?Math\.round\(storedMinutes\):0/);
  assert.match(js, /return total>0\?\`\$\{total\} min\`:'—'/);
  const start=js.indexOf('function formatWorkDuration');
  const end=js.indexOf('function printRecordPageHtml',start);
  const formatter=js.slice(start,end);
  assert.doesNotMatch(formatter, /\bu\b/);
  assert.doesNotMatch(formatter, /\*60/);
});


test('totaaloverzicht blijft workSessions gebruiken en wordt niet herberekend uit serviceItemMinutes', () => {
  const start=js.indexOf('function visitWorkSessions');
  const end=js.indexOf('function visitReportHtml',start);
  const totals=js.slice(start,end);
  assert.match(totals, /record\.item\?\.workSessions/);
  assert.match(totals, /Number\(session\?\.minutes\)/);
  assert.doesNotMatch(totals, /serviceItemMinutesValue/);
  assert.doesNotMatch(totals, /serviceItemMinutes/);
});
