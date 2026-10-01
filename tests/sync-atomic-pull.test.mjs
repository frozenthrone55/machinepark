import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { IDBFactory } from 'fake-indexeddb';

const source = readFileSync(new URL('../offline-first.js', import.meta.url), 'utf8');
const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const stores = ['parts', 'devices', 'maintenance', 'breakdowns', 'actions'];
const copy = value => JSON.parse(JSON.stringify(value));
const snapshot = label => ({ app: 'Machinepark', ...Object.fromEntries(stores.map(s => [s, [{ id: 1, label }]])) });

async function harness(t, { response, onFetch, onSnapshot, onMeta } = {}) {
  const indexedDB = new IDBFactory();
  const db = await new Promise((resolve, reject) => {
    const request = indexedDB.open('test-data', 1);
    request.onupgradeneeded = () => stores.forEach(s => request.result.createObjectStore(s, { keyPath: 'id' }));
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  t.after(() => db.close());
  const base = snapshot('base');
  const remote = snapshot('server');
  const storage = new Map();
  let reads = 0;
  let hooksEnabled = false;
  const context = vm.createContext({
    indexedDB, db, stores, console, Date, URL,
    navigator: { onLine: true },
    window: { Clerk: { isSignedIn: true }, location: { href: 'https://example.test/' } },
    document: { getElementById: () => null },
    centralSync: { enabled: true, etag: 'base', pending: false, offlineDirty: false },
    CENTRAL_SYNC_URL: '/data',
    localStorage: { getItem: k => storage.get(k), setItem: (k, v) => storage.set(k, v), removeItem: k => storage.delete(k) },
    centralHeaders: async () => ({}),
    centralPush: async () => { throw new Error('Unexpected push'); },
    centralPull: null,
    setCentralSyncStatus: () => {},
    refresh: async () => {},
    metaHook: async patch => { if (hooksEnabled) await onMeta?.(api, patch); },
    fetch: async () => {
      await onFetch?.(api);
      return response || { ok: true, status: 200, text: async () => JSON.stringify({ exists: true, etag: 'remote', data: remote }) };
    },
    getAll: name => new Promise((resolve, reject) => {
      const request = db.transaction(name).objectStore(name).getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    }),
  });
  // Run the actual built helpers and centralPull, leaving DOM installation out.
  const prefix = source.slice(0, source.indexOf('  async function writeDirect('))
    .replace('async function writeMeta(patch) {', 'async function persistMeta(patch) {');
  const pull = source.slice(source.indexOf('    centralPull = async function'), source.indexOf('    window.centralPull = centralPull;'));
  vm.runInContext(prefix + `
    async function writeMeta(patch) { await metaHook(patch); return persistMeta(patch); }
    ${pull}
    window.testSync = { readMeta, writeMeta, noteLocalWrite };
  })();`, context);
  for (const name of ['localSnapshot', 'replaceLocalSnapshot']) {
    const start = index.indexOf(`async function ${name}(`);
    assert.ok(start >= 0);
    vm.runInContext(index.slice(start, index.indexOf('\n', start)), context);
  }
  const originalSnapshot = context.localSnapshot;
  context.localSnapshot = async () => {
    const result = await originalSnapshot();
    if (hooksEnabled) await onSnapshot?.(api, ++reads);
    return result;
  };
  const api = {
    context, base, remote,
    pull: options => context.centralPull(options),
    meta: () => context.window.testSync.readMeta(),
    data: async () => copy(await originalSnapshot()),
    async edit(name = 'devices', tracked = false) {
      await new Promise((resolve, reject) => {
        const tr = db.transaction(name, 'readwrite');
        tr.objectStore(name).put({ id: 1, label: 'new-local' });
        tr.oncomplete = resolve;
        tr.onerror = () => reject(tr.error);
      });
      if (tracked) {
        context.window.testSync.noteLocalWrite();
        context.centralSync.pending = true;
        context.centralSync.offlineDirty = true;
      }
    },
  };
  await context.replaceLocalSnapshot(base);
  await context.window.testSync.writeMeta({ etag: 'base', base, dirty: false });
  hooksEnabled = true;
  return api;
}

test('unchanged local stores accept a new server snapshot and its merge base', async t => {
  const api = await harness(t);
  await api.pull();
  assert.equal((await api.data()).devices[0].label, 'server');
  assert.equal((await api.meta()).etag, 'remote');
  assert.equal((await api.meta()).dirty, false);
});

for (const name of stores) {
  test(`direct ${name} write after final snapshot read survives the pull`, async t => {
    const api = await harness(t, { onSnapshot: async (app, count) => { if (count === 3) await app.edit(name); } });
    const result = await api.pull();
    assert.equal((await api.data())[name][0].label, 'new-local');
    assert.equal(result.pending, true);
    const meta = await api.meta();
    assert.equal(meta.dirty, true);
    assert.equal(meta.etag, 'base');
    assert.equal(meta.base[name][0].label, 'base');
  });
}

test('a tracked write during meta storage survives and retains the applied merge base', async t => {
  let edited = false;
  const api = await harness(t, { onMeta: async (app, patch) => {
    if (!edited && patch.etag === 'remote' && patch.dirty === false) {
      edited = true;
      await app.edit('maintenance', true);
    }
  } });
  const result = await api.pull();
  assert.equal((await api.data()).maintenance[0].label, 'new-local');
  assert.equal(result.pending, true);
  assert.equal((await api.meta()).dirty, true);
  assert.equal((await api.meta()).base.maintenance[0].label, 'server');
});

test('a write during the GET is still protected', async t => {
  const api = await harness(t, { onFetch: app => app.edit('actions', true) });
  assert.equal((await api.pull()).pending, true);
  assert.equal((await api.data()).actions[0].label, 'new-local');
  assert.equal((await api.meta()).etag, 'base');
});

test('an untracked write during meta storage remains dirty for the next sync', async t => {
  let edited = false;
  const api = await harness(t, { onMeta: async (app, patch) => {
    if (!edited && patch.etag === 'remote' && patch.dirty === false) {
      edited = true;
      await app.edit('breakdowns');
    }
  } });
  assert.equal((await api.pull()).pending, true);
  assert.equal((await api.data()).breakdowns[0].label, 'new-local');
  assert.equal((await api.meta()).dirty, true);
  assert.equal((await api.meta()).base.breakdowns[0].label, 'server');
});

test('HTTP 304 does not acknowledge a concurrent direct IndexedDB write', async t => {
  const api = await harness(t, { response: { status: 304 }, onFetch: app => app.edit('parts') });
  assert.equal((await api.pull()).pending, true);
  assert.equal((await api.meta()).dirty, true);
  assert.equal((await api.data()).parts[0].label, 'new-local');
});

test('read-only pull leaves the local merge base and ETag unchanged', async t => {
  const api = await harness(t);
  const result = await api.pull({ apply: false });
  assert.equal(result.etag, 'remote');
  assert.equal((await api.meta()).etag, 'base');
  assert.equal((await api.data()).devices[0].label, 'base');
});

test('invalid remote record aborts every store and leaves sync metadata unchanged', async t => {
  const api = await harness(t);
  api.remote.actions = [{ label: 'missing-key' }];
  await assert.rejects(api.pull());
  assert.equal((await api.data()).parts[0].label, 'base');
  assert.equal((await api.data()).actions[0].label, 'base');
  assert.equal((await api.meta()).etag, 'base');
});

test('startup uses the guarded pull without a second unchecked replacement', () => {
  assert.match(source, /remote = await centralPull\(\{ apply: true, quiet: true \}\)/);
  assert.doesNotMatch(source, /await replaceLocalSnapshot\(remote\.data\)/);
});
