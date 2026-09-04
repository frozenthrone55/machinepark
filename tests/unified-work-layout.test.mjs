import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-unified-work-layout.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('uniforme werkverslag-layout draait als laatste visuele buildlaag', () => {
  const unified=pkg.scripts.build.indexOf('python3 build-unified-work-layout.py');
  const other=pkg.scripts.build.indexOf('python3 build-other-works.py');
  const nav=pkg.scripts.build.indexOf('python3 build-navigation-bootstrap.py');
  const checks=pkg.scripts.build.indexOf('python3 scripts/check-inline-scripts.py');
  assert.ok(unified>other);
  assert.ok(unified>nav);
  assert.ok(checks>unified);
});

test('onderhoud depannage andere werken en gecombineerd overzicht krijgen servicepanelen', () => {
  assert.ok(build.includes("['view-maintenance','Onderhoudsverslagen'"));
  assert.ok(build.includes("['view-breakdowns','Depannageverslagen'"));
  assert.ok(build.includes("['view-otherworks','Andere werken'"));
  assert.ok(build.includes("['view-work','Werkzaamhedenoverzicht'"));
  assert.ok(build.includes("panel.className = 'work-overview-panel service-visit-panel'"));
  assert.ok(build.includes('service-visit-panel-head'));
});

test('individuele afdruk gebruikt servicekop infokaders en één werksoort bovenaan', () => {
  assert.ok(build.includes('work-report-print-head'));
  assert.ok(build.includes('work-report-print-kind'));
  assert.ok(build.includes('work-report-print-meta'));
  assert.ok(build.includes("summaryLabel = record?.serviceVisitId ? 'Servicetijd volledig verslag / toestellen' : 'Datum / werkminuten'"));
  assert.ok(build.includes("kindLabel = maintenance ? 'Onderhoud' : (other ? (record.workTypeName || 'Andere werken') : 'Depannage')"));
});

test('alle werkafdrukken gebruiken onderdeel omschrijving aantal met dynamische codekolom', () => {
  assert.ok(build.includes('Onderdelen voor deze werkzaamheid'));
  assert.ok(build.includes('work-part-code'));
  assert.ok(build.includes('work-part-description'));
  assert.ok(build.includes('work-part-qty'));
  assert.ok(build.includes('padding-right:calc(3ch + 10px)'));
  assert.ok(build.includes('text-align:right'));
});

test('dynamisch Andere werken-overzicht krijgt ook Afdrukken en Mail PDF', () => {
  assert.ok(build.includes('ensurePageActions'));
  assert.ok(build.includes('page-print-btn'));
  assert.ok(build.includes('page-mail-btn'));
  assert.ok(build.includes('window.printMachineparkView'));
});
