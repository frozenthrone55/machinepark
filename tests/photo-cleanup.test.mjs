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

test('detecteert verwijderde toestellen en onderdelen', () => {
  const before = {
    devices: [{ id: 'dev-1' }, { id: 'dev-2' }],
    parts: [{ id: 'part-1' }, { id: 'part-2' }],
  };
  const after = {
    devices: [{ id: 'dev-2' }],
    parts: [{ id: 'part-2' }],
  };
  assert.deepEqual(removedPhotoOwners(before, after), { devices: ['dev-1'], parts: ['part-1'] });
});

test('verwijdert origineel en thumbnails van volledig verwijderd toestel en onderdeel', async () => {
  const store = fakeStore([
    'device-photos/dev-1/a',
    'device-photos/dev-1/a.thumb',
    'device-photos/dev-1/b',
    'device-photos/dev-1/b.thumb',
    'device-photos/dev-2/keep',
    'device-photos/dev-2/keep.thumb',
    'part-photos/part-1/photo',
    'part-photos/part-1/photo.thumb',
    'part-photos/part-2/photo',
    'part-photos/part-2/photo.thumb',
  ]);
  const before = {
    devices: [{ id: 'dev-1' }, { id: 'dev-2' }],
    parts: [{ id: 'part-1' }, { id: 'part-2' }],
  };
  const after = {
    devices: [{ id: 'dev-2' }],
    parts: [{ id: 'part-2' }],
  };

  const result = await cleanupRemovedEntityPhotos(store, before, after);
  assert.deepEqual(result, { devices: 1, parts: 1, blobs: 6 });
  assert.deepEqual([...store.existing].sort(), [
    'device-photos/dev-2/keep',
    'device-photos/dev-2/keep.thumb',
    'part-photos/part-2/photo',
    'part-photos/part-2/photo.thumb',
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
});
