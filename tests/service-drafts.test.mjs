import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assertSnapshotWriteAllowed } from '../netlify/functions/_shared/permissions.mjs';

const patch = readFileSync(new URL('../build-service-drafts.py', import.meta.url), 'utf8');
const server = readFileSync(new URL('../netlify/functions/machinepark-data.mjs', import.meta.url), 'utf8');
const permissions = readFileSync(new URL('../netlify/functions/_shared/permissions.mjs', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

function snapshot({ maintenance = [], breakdowns = [], stock = 10 } = {}) {
  return {
    app: 'Machinepark', schema: 1,
    devices: [{ id: 'dev-1', assetCode: 'WCL-1', status: 'Actief' }],
    parts: [{ id: 'part-1', artNr: 'P1', stock }],
    maintenance,
    breakdowns,
  };
}

const roleConfig = {
  version: 1,
  roles: [{
    id: 'concepttoevoeger', label: 'Concepttoevoeger',
    permissions: {
      'maintenance.add': true,
      'breakdowns.add': true,
    },
  }],
};

const maintenanceHeader = { id:'mh', isDraft:true, draftRole:'header', draftKind:'maintenance', draftBatchId:'mh', locationLabel:'Test', updatedAt:'2026-09-01T10:00:00Z' };
const maintenanceItem = { id:'mi', isDraft:true, draftRole:'item', draftKind:'maintenance', draftBatchId:'mh', draftSelected:true, deviceId:'dev-1', type:'Jaarlijks', usedParts:[{ partId:'part-1', qty:1 }], updatedAt:'2026-09-01T10:00:00Z' };

test('concepten zitten alleen op onderhoud en depannages en worden apart gerenderd', () => {
  assert.match(patch, /SERVICE_KINDS = new Set\(\['maintenance','breakdowns'\]\)/);
  assert.match(patch, /Concept bewaren/);
  assert.match(patch, /AUTOSAVE_DELAY = 1400/);
  assert.match(patch, /draftRole:'header'/);
  assert.match(patch, /draftRole:'item'/);
  assert.match(patch, /withRegularServiceState/);
  assert.match(patch, /Concepten \(\$\{headers\.length\}\)/);
});

test('concept bewaart volledige service-invoer maar boekt voorraad pas atomair af bij afronden', () => {
  assert.match(patch, /machineparkPersistServicePhotos/);
  assert.match(patch, /collectWorkOrderLoose/);
  assert.match(patch, /fault-inline-tools/);
  assert.match(patch, /machineparkCollectServiceOneOff/);
  assert.match(patch, /service-work-session-row/);
  assert.match(patch, /db\.transaction\(\[info\.store,'parts'\], 'readwrite'\)/);
  assert.match(patch, /stock:Number\(part\.stock \|\| 0\) - qty/);
  assert.match(patch, /Concept: onderdelen worden nog niet van de voorraad afgeboekt/);
});

test('concepten gebruiken centrale/offline snapshot-sync en worden voor offline fotoflush herkenbaar opgeslagen', () => {
  assert.match(patch, /scheduleCentralSync\(\)/);
  assert.match(patch, /isDraft:true, draftRole:'item'/);
  assert.match(patch, /photos, createdAt/);
  assert.match(patch, /synchroniseert zodra internet beschikbaar is/);
});

test('concept autosaves veroorzaken geen wijzigingslogboekspam', () => {
  assert.match(server, /function auditVisibleList/);
  assert.match(server, /item\?\.isDraft !== true/);
  assert.match(server, /auditVisibleList\(before, storeName\)/);
  assert.match(server, /auditVisibleList\(after, storeName\)/);
});

test('alleen toevoegen volstaat voor concept maken, bijwerken en verwijderen', () => {
  const base = snapshot();
  const added = snapshot({ maintenance:[maintenanceHeader, maintenanceItem] });
  assert.doesNotThrow(() => assertSnapshotWriteAllowed(base, added, 'concepttoevoeger', roleConfig));

  const changed = snapshot({ maintenance:[maintenanceHeader, { ...maintenanceItem, type:'Halfjaarlijks' }] });
  assert.doesNotThrow(() => assertSnapshotWriteAllowed(added, changed, 'concepttoevoeger', roleConfig));
  assert.doesNotThrow(() => assertSnapshotWriteAllowed(changed, base, 'concepttoevoeger', roleConfig));
});

test('een concept-autosave geeft geen verborgen recht om voorraad te wijzigen', () => {
  const base = snapshot();
  const malicious = snapshot({ maintenance:[maintenanceHeader, maintenanceItem], stock:9 });
  assert.throws(
    () => assertSnapshotWriteAllowed(base, malicious, 'concepttoevoeger', roleConfig),
    /onderdeelgegevens|voorraad/i,
  );
  assert.match(permissions, /if \(item\?\.isDraft !== true\) allowsStockMutation = true/);
});

test('concept naar definitieve registratie mag gebruikte voorraad in dezelfde sync afboeken', () => {
  const before = snapshot({ maintenance:[maintenanceHeader, maintenanceItem] });
  const regular = {
    id:'mi', deviceId:'dev-1', type:'Jaarlijks', date:'2026-09-01', time:'10:00', technician:'Tech',
    batchId:'mntbatch-1', usedParts:[{ partId:'part-1', qty:1 }], createdAt:'2026-09-01T10:00:00Z', updatedAt:'2026-09-01T10:10:00Z',
  };
  const after = snapshot({ maintenance:[regular], stock:9 });
  assert.doesNotThrow(() => assertSnapshotWriteAllowed(before, after, 'concepttoevoeger', roleConfig));
  assert.match(permissions, /beforeDraft && !afterDraft/);
  assert.match(permissions, /allowsStockMutation = true/);
});

test('serviceconcept patch bouwt na alle servicefuncties en vóór offline-first', () => {
  const chain = packageJson.scripts.build;
  assert.equal(packageJson.version, '1.68.9');
  assert.ok(chain.includes('build-service-drafts.py'));
  assert.ok(chain.indexOf('build-manual-native-sync.py') < chain.indexOf('build-service-drafts.py'));
  assert.ok(chain.indexOf('build-service-drafts.py') < chain.indexOf('build-offline-first.py'));
});
