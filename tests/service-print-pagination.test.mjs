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
