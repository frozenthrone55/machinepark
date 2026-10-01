from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'offline-first.js'
source = path.read_text(encoding='utf-8')
MARKER = '// machinepark-atomic-pull-v1'


def replace_once(old, new):
    global source
    if source.count(old) != 1:
        raise SystemExit(f'Atomic pull: expected one anchor: {old[:100]}')
    source = source.replace(old, new, 1)


if MARKER not in source:
    helper = r'''
  // machinepark-atomic-pull-v1
  // Compare and replace inside ONE transaction covering every synced store.
  // Writes queued before it are observed; writes queued after it run afterwards.
  // Direct IndexedDB writes need no dirty flag to be protected here.
  function applyPulledSnapshot(data, baseline, sequence) {
    if (!data || data.app !== 'Machinepark') throw new Error('Ongeldige centrale Machinepark-gegevens.');
    return new Promise((resolve, reject) => {
      const tr = db.transaction(stores, 'readwrite');
      const current = {};
      let remaining = stores.length;
      let applied = false;
      tr.oncomplete = () => resolve(applied);
      tr.onerror = () => reject(tr.error);
      tr.onabort = () => reject(tr.error || new Error('Lokale synchronisatie afgebroken'));
      for (const name of stores) {
        const request = tr.objectStore(name).getAll();
        request.onsuccess = () => {
          current[name] = request.result;
          if (--remaining) return;
          if (localWriteSequence() !== sequence || centralSync.pending || centralSync.offlineDirty
              || hasPendingLocalWriteHint() || !snapshotStoresEqual(baseline, current)) return;
          // No await between the comparison and the writes: keep the lock.
          try {
            for (const storeName of stores) {
              const target = tr.objectStore(storeName);
              target.clear();
              for (const item of (Array.isArray(data[storeName]) ? data[storeName] : [])) target.put(item);
            }
            applied = true;
          } catch (error) {
            tr.abort();
            reject(error);
          }
        };
      }
    });
  }

  async function keepPullPending(meta) {
    centralSync.offlineDirty = true;
    centralSync.pending = true;
    markPendingLocalWriteHint();
    await writeMeta({ dirty: true, etag: meta.etag || null, base: meta.base || null });
    setCentralSyncStatus('☁ Nieuwe invoer lokaal bewaard · synchronisatie volgt…', 'busy');
    return { exists: true, pending: true, skippedApply: true };
  }

'''
    replace_once('  async function writeDirect(storeName, item) {', helper + '  async function writeDirect(storeName, item) {')

    # An unchanged response acknowledges no local write, and must not clear dirty.
    replace_once("        await writeMeta({ etag: centralSync.etag || null, dirty: false });\n        if (!quiet) setCentralSyncStatus('☁ Centraal gesynchroniseerd · geen wijzigingen', 'ok');",
                 "        if (localWriteSequence() !== pullWriteSequence || !snapshotStoresEqual(pullLocalBaseline, await localSnapshot())) return keepPullPending(meta);\n        if (!quiet) setCentralSyncStatus('☁ Centraal gesynchroniseerd · geen wijzigingen', 'ok');")

    old = '''      if (!body.exists) {
        centralSync.etag = null;
        await writeMeta({ etag: null, base: null, dirty: false });
        return { exists: false };
      }

      centralSync.etag = body.etag || etag;
      if (body.data) {
        centralSync.lastRemoteAt = body.data.updatedAt || '';
        await writeMeta({ etag: centralSync.etag || null, base: body.data, dirty: false });
        if (apply) {
          await replaceLocalSnapshot(body.data);
          if (window.__koffieServiceStarted && document.getElementById('view-dashboard')) await refresh();
        }
      } else {
        await writeMeta({ etag: centralSync.etag || null, dirty: false });
      }
      if (!quiet) setCentralSyncStatus('☁ Centraal gesynchroniseerd', 'ok');
      return { exists: true, unchanged: Boolean(body.unchanged || !body.data), data: body.data || null, etag: centralSync.etag };'''
    new = '''      if (!body.exists) return { exists: false };

      const confirmedEtag = body.etag || etag;
      // A read-only pull must not acknowledge data that has not been applied.
      if (!apply) return { exists: true, data: body.data || null, etag: confirmedEtag };
      if (body.data) {
        const applied = await applyPulledSnapshot(body.data, pullLocalBaseline, pullWriteSequence);
        if (!applied) return keepPullPending(meta);
        centralSync.etag = confirmedEtag;
        centralSync.lastRemoteAt = body.data.updatedAt || '';
        const confirmed = { etag: confirmedEtag || null, base: body.data };
        await writeMeta({ ...confirmed, dirty: false });
        // A write queued behind the data transaction can finish during meta storage.
        // Keep the applied server version as the merge base, and retain that write.
        const afterApply = await localSnapshot();
        if (localWriteSequence() !== pullWriteSequence || centralSync.pending || centralSync.offlineDirty
            || hasPendingLocalWriteHint() || !snapshotStoresEqual(body.data, afterApply)) {
          return keepPullPending(confirmed);
        }
        if (window.__koffieServiceStarted && document.getElementById('view-dashboard')) await refresh();
      }
      if (!quiet) setCentralSyncStatus('☁ Centraal gesynchroniseerd', 'ok');
      return { exists: true, unchanged: Boolean(body.unchanged || !body.data), data: body.data || null, etag: centralSync.etag };'''
    replace_once(old, new)

    # Startup must use the same guarded apply, without a later unchecked overwrite.
    replace_once('remote = await centralPull({ apply: false, quiet: true });',
                 'remote = await centralPull({ apply: true, quiet: true });')
    replace_once('''        if (remote?.exists && remote.data) {
          await replaceLocalSnapshot(remote.data);
        } else if (remote?.exists === false && !remote?.offline) {''',
                 '''        if (remote?.exists === false && !remote?.offline && !remote?.pending) {''')
    replace_once("        if (remote?.exists) setCentralSyncStatus('☁ Centraal gesynchroniseerd', 'ok');",
                 "        if (remote?.exists && !remote?.pending) setCentralSyncStatus('☁ Centraal gesynchroniseerd', 'ok');")
    path.write_text(source, encoding='utf-8')

print('[Machinepark] live pulls vergelijken en vervangen atomair; nieuwere lokale invoer blijft bewaard')
