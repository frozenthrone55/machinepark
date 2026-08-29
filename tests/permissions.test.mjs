import test from 'node:test';
import assert from 'node:assert/strict';
import {
  assertSnapshotWriteAllowed,
  normalizeRole,
  roleLabel,
  validSnapshot,
} from '../netlify/functions/_shared/permissions.mjs';

function snapshot(overrides = {}) {
  return {
    app: 'Machinepark',
    schema: 1,
    devices: [{ id: 'd1', assetCode: 'WCL1', status: 'Actief', notes: '', updatedAt: 'a' }],
    parts: [{ id: 'p1', artNr: 'HE1', description: 'Filter', price: 10, stock: 5, updatedAt: 'a' }],
    maintenance: [],
    breakdowns: [],
    ...overrides,
  };
}

test('rollen worden veilig genormaliseerd', () => {
  assert.equal(normalizeRole('BEHEERDER'), 'beheerder');
  assert.equal(normalizeRole('technieker'), 'technieker');
  assert.equal(normalizeRole('magazijnier'), 'magazijnier');
  assert.equal(normalizeRole('onbekend'), 'gebruiker');
  assert.equal(normalizeRole('gebruiker', { owner: true }), 'beheerder');
  assert.equal(roleLabel('magazijnier'), 'Magazijnier');
});

test('snapshot schema wordt gevalideerd', () => {
  assert.equal(validSnapshot(snapshot()), true);
  assert.equal(validSnapshot({ app: 'Machinepark', schema: 1 }), false);
  assert.equal(validSnapshot({ ...snapshot(), schema: 2 }), false);
});

test('bestaande gebruiker behoudt operationele schrijfrechten', () => {
  const before = snapshot();
  const after = snapshot({ devices: [{ ...before.devices[0], assetCode: 'WCL2' }] });
  assert.doesNotThrow(() => assertSnapshotWriteAllowed(before, after, 'gebruiker'));
});

test('magazijnier mag onderdelen wijzigen maar geen toestellen', () => {
  const before = snapshot();
  const partAfter = snapshot({ parts: [{ ...before.parts[0], price: 12 }] });
  assert.doesNotThrow(() => assertSnapshotWriteAllowed(before, partAfter, 'magazijnier'));

  const deviceAfter = snapshot({ devices: [{ ...before.devices[0], notes: 'test' }] });
  assert.throws(() => assertSnapshotWriteAllowed(before, deviceAfter, 'magazijnier'), /alleen onderdelen/i);
});

test('technieker mag onderhoud en voorraadverbruik registreren', () => {
  const before = snapshot();
  const after = snapshot({
    parts: [{ ...before.parts[0], stock: 4, updatedAt: 'b' }],
    maintenance: [{ id: 'm1', deviceId: 'd1', type: 'Jaarlijks', date: '2026-08-27', usedParts: [{ partId: 'p1', qty: 1 }] }],
  });
  assert.doesNotThrow(() => assertSnapshotWriteAllowed(before, after, 'technieker'));
});

test('technieker kan geen onderdeelprijs aanpassen', () => {
  const before = snapshot();
  const after = snapshot({ parts: [{ ...before.parts[0], price: 99 }] });
  assert.throws(() => assertSnapshotWriteAllowed(before, after, 'technieker'), /alleen de voorraad/i);
});

test('technieker kan toestelstatus maar geen toestelcode wijzigen', () => {
  const before = snapshot();
  const statusAfter = snapshot({ devices: [{ ...before.devices[0], status: 'In herstelling' }] });
  assert.doesNotThrow(() => assertSnapshotWriteAllowed(before, statusAfter, 'technieker'));

  const codeAfter = snapshot({ devices: [{ ...before.devices[0], assetCode: 'WCL999' }] });
  assert.throws(() => assertSnapshotWriteAllowed(before, codeAfter, 'technieker'), /status en notities/i);
});

test('toestel ondersteunt maximaal drie fotos en een geldige overzichtsfoto', () => {
  const before = snapshot();
  const threePhotos = snapshot({
    devices: [{ ...before.devices[0], devicePhotos: ['foto-1', 'foto-2', 'foto-3'], deviceOverviewPhotoIndex: 2 }],
  });
  assert.doesNotThrow(() => assertSnapshotWriteAllowed(before, threePhotos, 'gebruiker'));

  const fourPhotos = snapshot({
    devices: [{ ...before.devices[0], devicePhotos: ['foto-1', 'foto-2', 'foto-3', 'foto-4'], deviceOverviewPhotoIndex: 0 }],
  });
  assert.throws(() => assertSnapshotWriteAllowed(before, fourPhotos, 'gebruiker'), /maximaal 3 foto/i);

  const invalidOverview = snapshot({
    devices: [{ ...before.devices[0], devicePhotos: ['foto-1', 'foto-2'], deviceOverviewPhotoIndex: 2 }],
  });
  assert.throws(() => assertSnapshotWriteAllowed(before, invalidOverview, 'gebruiker'), /overzichtsfoto/i);
});

test('technieker met alleen status en notities kan toestelfotos niet wijzigen', () => {
  const before = snapshot();
  const after = snapshot({
    devices: [{ ...before.devices[0], devicePhotos: ['foto-1'], deviceOverviewPhotoIndex: 0 }],
  });
  assert.throws(() => assertSnapshotWriteAllowed(before, after, 'technieker'), /status en notities/i);
});
