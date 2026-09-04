import test from 'node:test';
import assert from 'node:assert/strict';
import {
  cleanupRemovedEntityPhotos,
  removedPhotoOwners,
  withoutPermanentPhotoRefs,
} from '../netlify/functions/_shared/photo-cleanup.mjs';

function fakeStore(keys) {
  const existing = new Set(keys);
  return {
    existing,
    async list({ prefix }) {
      return { blobs: [...existing].filter((key) => key.startsWith(prefix)).map((key) => ({ key })) };
    },
    async delete(key) {
      existing.delete(key);
    },
  };
}

test('detecteert verwijderde foto-eigenaars in alle hoofdcollecties', () => {
  const before = {
    devices: [{ id: 'dev-1' }, { id: 'dev-2' }],
    parts: [{ id: 'part-1' }, { id: 'part-2' }],
    maintenance: [{ id: 'mnt-1' }, { id: 'mnt-2' }],
    breakdowns: [{ id: 'brk-1' }, { id: 'brk-2' }],
  };
  const after = {
    devices: [{ id: 'dev-2' }],
    parts: [{ id: 'part-2' }],
    maintenance: [{ id: 'mnt-2' }],
    breakdowns: [{ id: 'brk-2' }],
  };
  assert.deepEqual(removedPhotoOwners(before, after), {
    devices: ['dev-1'],
    parts: ['part-1'],
    maintenance: ['mnt-1'],
    breakdowns: ['brk-1'],
  });
});

test('verwijdert originelen en thumbnails van volledig verwijderde entiteiten', async () => {
  const store = fakeStore([
    'device-photos/dev-1/a',
    'device-photos/dev-1/a.thumb',
    'device-photos/dev-2/keep',
    'device-photos/dev-2/keep.thumb',
    'part-photos/part-1/photo',
    'part-photos/part-1/photo.thumb',
    'part-photos/part-2/photo',
    'part-photos/part-2/photo.thumb',
    'service-photos/maintenance/mnt-1/a',
    'service-photos/maintenance/mnt-1/a.thumb',
    'service-photos/maintenance/mnt-2/keep',
    'service-photos/maintenance/mnt-2/keep.thumb',
    'service-photos/breakdowns/brk-1/a',
    'service-photos/breakdowns/brk-1/a.thumb',
    'service-photos/breakdowns/brk-2/keep',
    'service-photos/breakdowns/brk-2/keep.thumb',
  ]);
  const before = {
    devices: [{ id: 'dev-1' }, { id: 'dev-2' }],
    parts: [{ id: 'part-1' }, { id: 'part-2' }],
    maintenance: [{ id: 'mnt-1' }, { id: 'mnt-2' }],
    breakdowns: [{ id: 'brk-1' }, { id: 'brk-2' }],
  };
  const after = {
    devices: [{ id: 'dev-2' }],
    parts: [{ id: 'part-2' }],
    maintenance: [{ id: 'mnt-2' }],
    breakdowns: [{ id: 'brk-2' }],
  };

  const result = await cleanupRemovedEntityPhotos(store, before, after);
  assert.deepEqual(result, { devices: 1, parts: 1, maintenance: 1, breakdowns: 1, blobs: 8 });
  assert.deepEqual([...store.existing].sort(), [
    'device-photos/dev-2/keep',
    'device-photos/dev-2/keep.thumb',
    'part-photos/part-2/photo',
    'part-photos/part-2/photo.thumb',
    'service-photos/breakdowns/brk-2/keep',
    'service-photos/breakdowns/brk-2/keep.thumb',
    'service-photos/maintenance/mnt-2/keep',
    'service-photos/maintenance/mnt-2/keep.thumb',
  ]);
});

test('logboekherstel zet definitief verwijderde fotoreferenties niet terug', () => {
  assert.deepEqual(
    withoutPermanentPhotoRefs('devices', { id: 'dev-1', devicePhotos: ['oude-foto'], deviceOverviewPhotoIndex: 0, model: 'X' }),
    { id: 'dev-1', devicePhotos: [], deviceOverviewPhotoIndex: 0, model: 'X' },
  );
  assert.deepEqual(
    withoutPermanentPhotoRefs('parts', { id: 'part-1', photo: 'oude-foto', artNr: 'A1' }),
    { id: 'part-1', photo: '', artNr: 'A1' },
  );
  assert.deepEqual(
    withoutPermanentPhotoRefs('maintenance', { id: 'mnt-1', photos: ['oude-foto'], type: 'Jaarlijks' }),
    { id: 'mnt-1', photos: [], type: 'Jaarlijks' },
  );
  assert.deepEqual(
    withoutPermanentPhotoRefs('breakdowns', { id: 'brk-1', photos: ['oude-foto'], issue: 'Lek' }),
    { id: 'brk-1', photos: [], issue: 'Lek' },
  );
});
