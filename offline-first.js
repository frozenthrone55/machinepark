'use strict';

(() => {
  const OFFLINE_DB = 'MachineparkOfflineSyncDB';
  const OFFLINE_DB_VERSION = 1;
  const OFFLINE_STORE = 'meta';
  const OFFLINE_META_ID = 'central';
  const OFFLINE_ACCESS_KEY = 'machinepark-offline-access-v1';
  let metaDbPromise = null;
  let installed = false;

  function installStyle() {
    if (document.getElementById('machineparkOfflineStyle')) return;
    const style = document.createElement('style');
    style.id = 'machineparkOfflineStyle';
    style.textContent = `
      html.machinepark-offline-session #authGate{display:none!important}
      html.machinepark-offline-session #appShell{display:block!important}
      .sync-status.offline{color:#8b5d18;background:#fff4dd;border-color:#ead09e}
    `;
    document.head.appendChild(style);
  }

  function openMetaDb() {
    if (metaDbPromise) return metaDbPromise;
    metaDbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(OFFLINE_DB, OFFLINE_DB_VERSION);
      request.onupgradeneeded = () => {
        const d = request.result;
        if (!d.objectStoreNames.contains(OFFLINE_STORE)) d.createObjectStore(OFFLINE_STORE, { keyPath: 'id' });
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    return metaDbPromise;
  }

  async function readMeta() {
    try {
      const d = await openMetaDb();
      return await new Promise((resolve, reject) => {
        const request = d.transaction(OFFLINE_STORE).objectStore(OFFLINE_STORE).get(OFFLINE_META_ID);
        request.onsuccess = () => resolve(request.result || { id: OFFLINE_META_ID, etag: null, base: null, dirty: false });
        request.onerror = () => reject(request.error);
      });
    } catch (error) {
      console.warn('Offline syncmeta lezen', error);
      return { id: OFFLINE_META_ID, etag: null, base: null, dirty: false };
    }
  }

  async function writeMeta(patch) {
    try {
      const d = await openMetaDb();
      const current = await readMeta();
      const next = { ...current, ...patch, id: OFFLINE_META_ID, savedAt: new Date().toISOString() };
      await new Promise((resolve, reject) => {
        const tr = d.transaction(OFFLINE_STORE, 'readwrite');
        const request = tr.objectStore(OFFLINE_STORE).put(next);
        request.onerror = () => reject(request.error);
        tr.oncomplete = resolve;
        tr.onerror = () => reject(tr.error);
        tr.onabort = () => reject(tr.error || new Error('Offline syncmeta opslaan afgebroken'));
      });
      return next;
    } catch (error) {
      console.warn('Offline syncmeta opslaan', error);
      return null;
    }
  }

  function readCachedAccess() {
    try {
      const value = JSON.parse(localStorage.getItem(OFFLINE_ACCESS_KEY) || 'null');
      return value && value.permissions && typeof value.permissions === 'object' ? value : null;
    } catch (_) {
      return null;
    }
  }

  function cacheAccess(body) {
    if (!body || typeof body !== 'object' || !body.permissions) return;
    try {
      const user = window.Clerk?.user;
      const email = String(user?.primaryEmailAddress?.emailAddress || user?.emailAddresses?.[0]?.emailAddress || '').trim().toLowerCase();
      const name = String(user?.fullName || [user?.firstName, user?.lastName].filter(Boolean).join(' ') || user?.username || email || 'Gebruiker').trim();
      localStorage.setItem(OFFLINE_ACCESS_KEY, JSON.stringify({
        role: String(body.role || window.machineparkRole || 'gebruiker'),
        roleLabel: String(body.roleLabel || window.machineparkCurrentRoleLabel || body.role || 'Gebruiker'),
        permissions: { ...body.permissions },
        userName: name,
        userEmail: email,
        cachedAt: new Date().toISOString(),
      }));
    } catch (_) {}
  }

  function restoreAccess() {
    const cached = readCachedAccess();
    if (!cached) return false;
    window.machineparkPermissions = { ...cached.permissions };
    window.machineparkRole = String(cached.role || 'gebruiker');
    window.machineparkCurrentRoleLabel = String(cached.roleLabel || cached.role || 'Gebruiker');
    window.machineparkAccessReady = true;
    window.machineparkIsAdmin = Boolean(window.machineparkPermissions['view.settings']);
    const nameEl = document.getElementById('accountDisplayName');
    const roleEl = document.getElementById('accountDisplayRole');
    if (nameEl) nameEl.textContent = cached.userName || cached.userEmail || 'Offline gebruiker';
    if (roleEl) roleEl.textContent = window.machineparkCurrentRoleLabel;
    if (typeof window.applyMachineparkRoleAccess === 'function') window.applyMachineparkRoleAccess();
    if (typeof window.applyOperationalPermissions === 'function') window.applyOperationalPermissions();
    return true;
  }

  function isNetworkFailure(error) {
    if (!navigator.onLine) return true;
    if (error instanceof TypeError) return true;
    return /network|fetch|offline|internet|failed to fetch|load failed|connection/i.test(String(error?.message || error || ''));
  }

  function setOfflineStatus() {
    if (typeof setCentralSyncStatus === 'function') setCentralSyncStatus('☁ Offline · wijzigingen lokaal bewaard', 'offline');
  }

  async function markDirty() {
    if (typeof centralSync !== 'undefined') {
      centralSync.offlineDirty = true;
      centralSync.pending = true;
    }
    const meta = await readMeta();
    await writeMeta({ dirty: true, etag: meta.etag || (typeof centralSync !== 'undefined' ? centralSync.etag : null) || null, base: meta.base || null });
  }

  function sameValue(a, b) {
    return JSON.stringify(a) === JSON.stringify(b);
  }

  // machinepark-offline-stock-delta-merge-v1
  function serviceSyncTime(item) {
    const parsed = Date.parse(String(item?.updatedAt || item?.createdAt || ''));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function preferRemoteServiceConflict(storeName, local, remote) {
    if (storeName !== 'maintenance' && storeName !== 'breakdowns') return false;
    const localTime = serviceSyncTime(local);
    const remoteTime = serviceSyncTime(remote);
    if (localTime && remoteTime) return remoteTime >= localTime;
    if (remoteTime) return true;
    if (localTime) return false;
    return true;
  }

  function mergeEntity(base, local, remote, stats, storeName = '') {
    if (base === undefined) {
      if (local === undefined) return remote;
      if (remote === undefined) return local;
    } else {
      if (local === undefined) {
        if (remote === undefined || sameValue(remote, base)) return undefined;
        stats.conflicts += 1;
        return undefined;
      }
      if (remote === undefined) {
        if (sameValue(local, base)) return undefined;
        stats.conflicts += 1;
        return local;
      }
    }

    const result = {};
    const keys = new Set([...Object.keys(base || {}), ...Object.keys(local || {}), ...Object.keys(remote || {})]);
    for (const key of keys) {
      const bHas = Boolean(base && Object.prototype.hasOwnProperty.call(base, key));
      const lHas = Boolean(local && Object.prototype.hasOwnProperty.call(local, key));
      const rHas = Boolean(remote && Object.prototype.hasOwnProperty.call(remote, key));
      const b = bHas ? base[key] : undefined;
      const l = lHas ? local[key] : undefined;
      const r = rHas ? remote[key] : undefined;
      const localChanged = lHas !== bHas || !sameValue(l, b);
      const remoteChanged = rHas !== bHas || !sameValue(r, b);

      // Voorraad is een teller. Als offline en online sinds dezelfde basis allebei
      // voorraad wijzigen, moeten beide delta's worden toegepast in plaats van
      // één absolute voorraadwaarde te laten winnen.
      if (storeName === 'parts' && key === 'stock' && localChanged && remoteChanged && bHas && lHas && rHas) {
        const baseStock = Number(b), localStock = Number(l), remoteStock = Number(r);
        if ([baseStock, localStock, remoteStock].every(Number.isFinite)) {
          result[key] = baseStock + (localStock - baseStock) + (remoteStock - baseStock);
          continue;
        }
      }

      if (!localChanged && remoteChanged) {
        if (rHas) result[key] = r;
      } else if (localChanged && !remoteChanged) {
        if (lHas) result[key] = l;
      } else if (!localChanged && !remoteChanged) {
        if (lHas) result[key] = l;
        else if (rHas) result[key] = r;
      } else if (lHas === rHas && sameValue(l, r)) {
        if (lHas) result[key] = l;
      } else {
        stats.conflicts += 1;
        if (preferRemoteServiceConflict(storeName, local, remote)) {
          if (rHas) result[key] = r;
        } else if (lHas) {
          result[key] = l;
        }
      }
    }
    return result;
  }

  function mergeStore(baseList, localList, remoteList, stats, storeName = '') {
    const base = new Map((Array.isArray(baseList) ? baseList : []).map((x) => [x.id, x]));
    const local = new Map((Array.isArray(localList) ? localList : []).map((x) => [x.id, x]));
    const remote = new Map((Array.isArray(remoteList) ? remoteList : []).map((x) => [x.id, x]));
    const ids = new Set([...base.keys(), ...local.keys(), ...remote.keys()]);
    const result = [];
    for (const id of ids) {
      const item = mergeEntity(base.get(id), local.get(id), remote.get(id), stats, storeName);
      if (item !== undefined) result.push(item);
    }
    return result;
  }

  function mergeOfflineSnapshots(base, local, remote) {
    const stats = { conflicts: 0 };
    const merged = {
      ...(remote || {}),
      ...(local || {}),
      app: 'Machinepark',
      schema: Math.max(Number(remote?.schema || 1), Number(local?.schema || 1)),
      updatedAt: new Date().toISOString(),
    };
    for (const storeName of stores) merged[storeName] = mergeStore(base?.[storeName], local?.[storeName], remote?.[storeName], stats, storeName);
    return { data: merged, conflicts: stats.conflicts };
  }
  window.machineparkMergeOfflineSnapshots = mergeOfflineSnapshots;

  // machinepark-sync-drift-recovery-v1
  const LOCAL_WRITE_HINT_KEY = 'machinepark-local-write-pending-v1';

  function sortedSyncStore(list) {
    return [...(Array.isArray(list) ? list : [])].sort((a, b) => String(a?.id || '').localeCompare(String(b?.id || '')));
  }

  function snapshotStoresEqual(a, b) {
    if (!a || !b) return false;
    return stores.every((storeName) => sameValue(sortedSyncStore(a?.[storeName]), sortedSyncStore(b?.[storeName])));
  }

  function markPendingLocalWriteHint() {
    try { localStorage.setItem(LOCAL_WRITE_HINT_KEY, new Date().toISOString()); } catch (_) {}
  }

  function hasPendingLocalWriteHint() {
    try { return Boolean(localStorage.getItem(LOCAL_WRITE_HINT_KEY)); } catch (_) { return false; }
  }

  function clearPendingLocalWriteHint() {
    try { localStorage.removeItem(LOCAL_WRITE_HINT_KEY); } catch (_) {}
  }

  async function writeDirect(storeName, item) {
    return new Promise((resolve, reject) => {
      const tr = db.transaction(storeName, 'readwrite');
      const request = tr.objectStore(storeName).put(item);
      request.onerror = () => reject(request.error);
      tr.oncomplete = () => resolve(item);
      tr.onerror = () => reject(tr.error);
      tr.onabort = () => reject(tr.error || new Error('Lokale opslag afgebroken'));
    });
  }

  function isRawPhoto(value) {
    return String(value || '').startsWith('data:image/');
  }

  // machinepark-synology-fresh-central-get-v1
  // Een oudere service worker cachete op Synology onbedoeld ook API-GETs.
  // Gebruik daarom voor centrale data altijd een unieke same-origin URL.
  // Zo kan de herstel-GET na HTTP 409 nooit een verouderde ETag teruggeven,
  // zelfs niet terwijl een oude service worker de huidige pagina nog bestuurt.
  function centralFreshUrl() {
    const url = new URL(CENTRAL_SYNC_URL, window.location.href);
    url.searchParams.set('machineparkSync', String(Date.now()) + '-' + String(Math.random()).slice(2));
    return url.toString();
  }

  async function fetchRemoteCurrent() {
    const headers = await centralHeaders(false);
    const res = await fetch(centralFreshUrl(), { method: 'GET', headers, cache: 'no-store', credentials: 'same-origin' });
    const text = await res.text();
    let body = {};
    try { body = text ? JSON.parse(text) : {}; } catch (_) {}
    if (!res.ok) throw new Error(body.error || text || `Cloud ophalen mislukt (${res.status})`);
    if (typeof window.applyMachineparkServerAccess === 'function') window.applyMachineparkServerAccess(body);
    return body;
  }

  async function gzipSyncPayload(payload) {
    if (typeof CompressionStream !== 'function') return null;
    try {
      const source = new Blob([payload]);
      const stream = source.stream().pipeThrough(new CompressionStream('gzip'));
      return await new Response(stream).blob();
    } catch (error) {
      console.warn('Gzip synchronisatie niet beschikbaar; gewone JSON wordt gebruikt', error);
      return null;
    }
  }

  function syncUploadId() {
    try {
      if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID().replace(/-/g, '');
      }
      if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
        const bytes = new Uint8Array(16);
        crypto.getRandomValues(bytes);
        return Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('');
      }
    } catch (_) {}
    return String(Date.now()) + String(Math.random()).slice(2);
  }

  async function putSnapshotChunked(blob, encoding, payloadBytes) {
    const chunkSize = 256 * 1024;
    const count = Math.ceil(blob.size / chunkSize);
    if (!count || count > 256) {
      const error = new Error('Centrale synchronisatie is te groot om veilig in delen te verzenden.');
      error.status = 413;
      error.payloadBytes = payloadBytes;
      error.compressedBytes = encoding === 'gzip' ? blob.size : 0;
      throw error;
    }

    const uploadId = syncUploadId();
    let lastResult = null;
    for (let index = 0; index < count; index += 1) {
      const headers = await centralHeaders(false);
      headers['Content-Type'] = 'application/octet-stream';
      headers['X-Machinepark-Chunked'] = '1';
      headers['X-Machinepark-Upload-Id'] = uploadId;
      headers['X-Machinepark-Chunk-Index'] = String(index);
      headers['X-Machinepark-Chunk-Count'] = String(count);
      headers['X-Machinepark-Payload-Encoding'] = encoding;

      const res = await fetch(CENTRAL_SYNC_URL, {
        method: 'PUT',
        headers,
        body: blob.slice(index * chunkSize, Math.min(blob.size, (index + 1) * chunkSize)),
        cache: 'no-store',
        credentials: 'same-origin',
      });
      const text = await res.text();
      let body = {};
      try { body = text ? JSON.parse(text) : {}; } catch (_) {}
      lastResult = {
        res,
        body,
        text,
        payloadBytes,
        compressedBytes: encoding === 'gzip' ? blob.size : 0,
        chunked: true,
      };
      if (!res.ok) return lastResult;
    }
    return lastResult;
  }

  async function putSnapshot(data, etag) {
    const headers = await centralHeaders(true);
    const payload = JSON.stringify({ data, etag: etag || null });
    const payloadBytes = new Blob([payload]).size;
    let requestBody = payload;
    let compressedBytes = 0;

    // Grote snapshots comprimeren. Dit houdt externe Synology-sync sneller en
    // voorkomt dat Web Station/nginx een onnodig grote JSON-PUT weigert.
    if (payloadBytes >= 128 * 1024) {
      const gzipped = await gzipSyncPayload(payload);
      if (gzipped && gzipped.size > 0 && gzipped.size < payloadBytes) {
        requestBody = gzipped;
        compressedBytes = gzipped.size;
        headers['Content-Encoding'] = 'gzip';
      }
    }

    const requestBlob = requestBody instanceof Blob ? requestBody : new Blob([requestBody]);
    const payloadEncoding = headers['Content-Encoding'] === 'gzip' ? 'gzip' : 'identity';

    // Synology Web Station/reverse proxy kan grote request bodies blokkeren
    // voordat PHP ze ziet. Vanaf 512 KiB verzenden we daarom rechtstreeks in
    // stukken van 256 KiB. Een onverwachte 413 op een kleinere PUT valt ook
    // automatisch terug op exact dezelfde chunkroute.
    if (requestBlob.size >= 512 * 1024) {
      return await putSnapshotChunked(requestBlob, payloadEncoding, payloadBytes);
    }

    const res = await fetch(CENTRAL_SYNC_URL, {
      method: 'PUT',
      headers,
      body: requestBody,
      cache: 'no-store',
      credentials: 'same-origin',
    });
    const text = await res.text();
    let body = {};
    try { body = text ? JSON.parse(text) : {}; } catch (_) {}
    const result = { res, body, text, payloadBytes, compressedBytes, chunked: false };
    if (res.status === 413 && requestBlob.size > 0) {
      return await putSnapshotChunked(requestBlob, payloadEncoding, payloadBytes);
    }
    return result;
  }

  function syncHttpError(result, fallback = 'Centrale synchronisatie mislukt') {
    const raw = String(result?.body?.error || result?.text || fallback);
    const message = raw
      .replace(/<[^>]*>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 220);
    const status = Number(result?.res?.status || 0);
    const error = new Error(message || fallback);
    error.status = status;
    error.payloadBytes = Number(result?.payloadBytes || 0);
    error.compressedBytes = Number(result?.compressedBytes || 0);
    error.chunked = Boolean(result?.chunked);
    error.syncCode = String(result?.body?.code || '');
    return error;
  }

  function syncErrorStatus(error) {
    const status = Number(error?.status || 0);
    const message = String(error?.message || 'Onbekende synchronisatiefout')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 180);
    const size = Number(error?.payloadBytes || 0);
    const compressed = Number(error?.compressedBytes || 0);
    const sizeText = size > 0 ? ' · ' + (size / 1024 / 1024).toFixed(2) + ' MB' : '';
    const transferText = compressed > 0 ? ' → ' + (compressed / 1024 / 1024).toFixed(2) + ' MB' : '';
    const chunkText = error?.chunked ? ' · in delen' : '';
    return '☁ Synchronisatie mislukt' + (status ? ' · HTTP ' + status : '') + sizeText + transferText + chunkText + ' · ' + message;
  }

  function installOfflineLayer() {
    if (installed) return;
    installed = true;
    installStyle();

    const baseAccess = window.applyMachineparkServerAccess;
    if (typeof baseAccess === 'function') {
      window.applyMachineparkServerAccess = function(body) {
        const result = baseAccess(body);
        cacheAccess(body);
        return result;
      };
    }

    const baseHeaders = typeof centralHeaders === 'function' ? centralHeaders : null;
    if (baseHeaders) {
      // machinepark-central-auth-retry-v1
      centralHeaders = async function(json = false) {
        if (!navigator.onLine && !window.Clerk?.isSignedIn) return json ? { 'Content-Type': 'application/json' } : {};
        let lastError = null;
        for (let attempt = 0; attempt < 5; attempt += 1) {
          try { return await baseHeaders(json); }
          catch (error) {
            lastError = error;
            if (isNetworkFailure(error)) return json ? { 'Content-Type': 'application/json' } : {};
            const message = String(error?.message || error || '');
            const tokenNotReady = /geen actieve clerk-sessie/i.test(message);
            if (!tokenNotReady || attempt >= 4 || !navigator.onLine) throw error;
            await new Promise((resolve) => setTimeout(resolve, 180 + attempt * 220));
          }
        }
        throw lastError || new Error('Clerk-sessie is nog niet beschikbaar.');
      };
      window.centralHeaders = centralHeaders;
    }

    const onlineDevicePhotos = window.machineparkPersistDevicePhotoList;
    if (typeof onlineDevicePhotos === 'function') {
      window.machineparkPersistDevicePhotoList = async function(deviceId, photos, options = {}) {
        const list = (Array.isArray(photos) ? photos : []).filter((x) => typeof x === 'string' && x.trim()).slice(0, 5);
        if (!navigator.onLine) { await markDirty(); return list; }
        try { return await onlineDevicePhotos(deviceId, list, options); }
        catch (error) {
          if (isNetworkFailure(error)) { await markDirty(); setOfflineStatus(); return list; }
          throw error;
        }
      };
    }

    const onlinePartPhoto = window.machineparkPersistPartPhoto;
    if (typeof onlinePartPhoto === 'function') {
      window.machineparkPersistPartPhoto = async function(partId, photo) {
        const value = String(photo || '').trim();
        if (!navigator.onLine) { await markDirty(); return value; }
        try { return await onlinePartPhoto(partId, value); }
        catch (error) {
          if (isNetworkFailure(error)) { await markDirty(); setOfflineStatus(); return value; }
          throw error;
        }
      };
    }

    const onlineServicePhotos = window.machineparkPersistServicePhotos;
    if (typeof onlineServicePhotos === 'function') {
      window.machineparkPersistServicePhotos = async function(storeName, entityId, photos) {
        const list = (Array.isArray(photos) ? photos : []).filter((x) => typeof x === 'string' && x.trim()).slice(0, 5);
        if (!navigator.onLine) { await markDirty(); return list; }
        try { return await onlineServicePhotos(storeName, entityId, list); }
        catch (error) {
          if (isNetworkFailure(error)) { await markDirty(); setOfflineStatus(); return list; }
          throw error;
        }
      };
    }

    async function flushOfflinePhotos() {
      if (!navigator.onLine) return 0;
      let changed = 0;

      if (typeof window.machineparkPersistDevicePhotoList === 'function') {
        for (const device of await getAll('devices')) {
          const photos = Array.isArray(device.devicePhotos) ? device.devicePhotos : [];
          if (!photos.some(isRawPhoto)) continue;
          const refs = await window.machineparkPersistDevicePhotoList(device.id, photos, { force: true });
          if (!sameValue(refs, photos)) {
            await writeDirect('devices', { ...device, devicePhotos: refs, updatedAt: new Date().toISOString() });
            changed += 1;
          }
        }
      }

      if (typeof window.machineparkPersistPartPhoto === 'function') {
        for (const part of await getAll('parts')) {
          if (!isRawPhoto(part?.photo)) continue;
          const ref = await window.machineparkPersistPartPhoto(part.id, part.photo);
          if (ref !== part.photo) {
            await writeDirect('parts', { ...part, photo: ref, updatedAt: new Date().toISOString() });
            changed += 1;
          }
        }
      }

      if (window.machineparkServiceBlobWritesEnabled !== false && typeof window.machineparkPersistServicePhotos === 'function') {
        for (const storeName of ['maintenance', 'breakdowns']) {
          for (const record of await getAll(storeName)) {
            const photos = Array.isArray(record.photos) ? record.photos : [];
            if (!photos.some(isRawPhoto)) continue;
            const refs = await window.machineparkPersistServicePhotos(storeName, record.id, photos);
            if (!sameValue(refs, photos)) {
              await writeDirect(storeName, { ...record, photos: refs, updatedAt: new Date().toISOString() });
              changed += 1;
            }
          }
        }
      }
      return changed;
    }
    window.machineparkFlushOfflinePhotos = flushOfflinePhotos;

    centralPush = async function({ initial = false } = {}) {
      if ((!centralSync.enabled && !initial) || centralSync.applying) return;
      if (!navigator.onLine || !window.Clerk?.isSignedIn) {
        await markDirty();
        setOfflineStatus();
        return { offline: true };
      }
      if (centralSync.pushing) {
        centralSync.pending = true;
        return centralSync.pushPromise || { queued: true };
      }

      centralSync.pushing = true;
      centralSync.pending = false;
      let pushFailed = false;
      setCentralSyncStatus('☁ Wijzigingen synchroniseren…', 'busy');
      const run = (async () => {
        try {
          const migratedPhotos = await flushOfflinePhotos();
          let local = await localSnapshot();
          let meta = await readMeta();
          let expectedEtag = meta.etag || centralSync.etag || null;
          let conflicts = 0;
          let reconciledRemote = false;

          for (let attempt = 0; attempt < 3; attempt += 1) {
            const result = await putSnapshot(local, expectedEtag);
            if (result.res.ok) {
              if (typeof window.applyMachineparkServerAccess === 'function') window.applyMachineparkServerAccess(result.body || {});
              centralSync.etag = result.body?.etag || expectedEtag || centralSync.etag;
              centralSync.lastRemoteAt = local.updatedAt || '';
              centralSync.offlineDirty = false;
              centralSync.pending = false;
              window.machineparkLastSyncError = null;
              await writeMeta({ etag: centralSync.etag || null, base: local, dirty: false });
              clearPendingLocalWriteHint();
              if (reconciledRemote || migratedPhotos) {
                await replaceLocalSnapshot(local);
                if (window.__koffieServiceStarted && document.getElementById('view-dashboard')) await refresh();
              }
              setCentralSyncStatus(conflicts ? `☁ Gesynchroniseerd · ${conflicts} conflict(en) veilig samengevoegd` : '☁ Alles centraal opgeslagen', 'ok');
              return { ok: true, conflicts };
            }

            if (result.res.status !== 409) throw syncHttpError(result, `Centraal opslaan mislukt (HTTP ${result.res.status})`);
            const remote = await fetchRemoteCurrent();
            if (!remote?.exists || !remote?.data) {
              expectedEtag = remote?.etag || null;
              continue;
            }
            const merged = mergeOfflineSnapshots(meta.base, local, remote.data);
            local = merged.data;
            reconciledRemote = true;
            conflicts += merged.conflicts;
            expectedEtag = remote.etag || null;
            meta = { ...meta, etag: expectedEtag };
          }
          throw new Error('De centrale gegevens wijzigden meerdere keren tegelijk. Lokale wijzigingen blijven bewaard en worden opnieuw geprobeerd.');
        } catch (error) {
          pushFailed = true;
          await markDirty();
          if (isNetworkFailure(error)) {
            setOfflineStatus();
            return { offline: true, error };
          }
          // Bij een server-/rechtenfout niet elke 250 ms opnieuw pushen.
          // De wijziging blijft als dirty lokaal bewaard en de normale polling
          // probeert later opnieuw. Zo blijft de status stabiel en ontstaat er
          // geen eindeloze sync-flikkerlus.
          window.machineparkLastSyncError = {
            at: new Date().toISOString(),
            status: Number(error?.status || 0),
            code: String(error?.syncCode || ''),
            message: String(error?.message || error || ''),
            payloadBytes: Number(error?.payloadBytes || 0),
            compressedBytes: Number(error?.compressedBytes || 0),
            chunked: Boolean(error?.chunked),
          };
          setCentralSyncStatus(syncErrorStatus(error), 'error');
          console.error('Offline synchronisatie', error);
          throw error;
        }
      })();

      centralSync.pushPromise = run;
      try { return await run; }
      finally {
        centralSync.pushing = false;
        centralSync.pushPromise = null;
        if (!pushFailed && centralSync.pending && centralSync.enabled && navigator.onLine) {
          clearTimeout(centralSync.pushTimer);
          centralSync.pushTimer = setTimeout(() => {
            centralSync.pushTimer = null;
            centralPush().catch(() => {});
          }, 250);
        }
      }
    };
    window.centralPush = centralPush;

    centralPull = async function({ apply = true, quiet = false } = {}) {
      if (!navigator.onLine || !window.Clerk?.isSignedIn) {
        if (!quiet) setOfflineStatus();
        return { exists: false, offline: true };
      }

      let meta = await readMeta();
      const localBeforePull = await localSnapshot();
      const localDrift = Boolean(meta.base) && !snapshotStoresEqual(meta.base, localBeforePull);
      let pendingHint = hasPendingLocalWriteHint();

      // Een lokale write kan op mobiel nog bestaan terwijl de asynchrone dirty-marker
      // door slaapstand/tabwissel niet duurzaam werd weggeschreven. Vergelijk daarom
      // ook de echte IndexedDB-inhoud met de laatst bevestigde centrale basis.
      if (localDrift && !meta.dirty) {
        centralSync.offlineDirty = true;
        const marked = await writeMeta({
          dirty: true,
          etag: meta.etag || centralSync.etag || null,
          base: meta.base || null,
        });
        meta = marked || { ...meta, dirty: true };
      }
      if (pendingHint && !localDrift && !meta.dirty && !centralSync.offlineDirty) {
        clearPendingLocalWriteHint();
        pendingHint = false;
      }

      if (meta.dirty || centralSync.offlineDirty || localDrift || pendingHint) {
        const pushed = await centralPush({ initial: true });
        if (pushed?.offline) return { exists: false, offline: true };
        meta = await readMeta();
        if (meta.dirty) return { exists: false, pending: true };
      }

      const headers = await centralHeaders(false);
      const etag = meta.etag || centralSync.etag || null;
      // machinepark-central-access-etag-v1
      // Gebruik geen standaard If-None-Match: browsers/CDN's kunnen dan zelf een 304
      // zonder JSON-body produceren, waardoor nieuwe rollen/rechten niet worden toegepast.
      // De server gebruikt deze eigen header alleen voor de Blob-ETag-vergelijking en
      // retourneert altijd JSON met de actuele toegangsrechten.
      if (etag) headers['X-Machinepark-If-None-Match'] = etag;
      const res = await fetch(CENTRAL_SYNC_URL, { method: 'GET', headers, cache: 'no-store' });
      // machinepark-central-304-not-modified-v1
      // 304 betekent dat de ETag nog actueel is. Dit is een geslaagde synchronisatie,
      // geen foutrespons. Laat de bestaande lokale snapshot onaangeroerd.
      if (res.status === 304) {
        centralSync.etag = etag || centralSync.etag || null;
        await writeMeta({ etag: centralSync.etag || null, dirty: false });
        if (!quiet) setCentralSyncStatus('☁ Centraal gesynchroniseerd · geen wijzigingen', 'ok');
        return { exists: true, unchanged: true, data: null, etag: centralSync.etag };
      }
      const text = await res.text();
      let body = {};
      try { body = text ? JSON.parse(text) : {}; } catch (_) {}
      if (!res.ok) throw new Error(body.error || text || `Cloud ophalen mislukt (${res.status})`);
      if (typeof window.applyMachineparkServerAccess === 'function') window.applyMachineparkServerAccess(body);

      if (!body.exists) {
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
      return { exists: true, unchanged: Boolean(body.unchanged || !body.data), data: body.data || null, etag: centralSync.etag };
    };
    window.centralPull = centralPull;

    scheduleCentralSync = function() {
      if (!centralSync.enabled || centralSync.applying) return;
      centralSync.pending = true;
      // Deze lokaleStorage-hint wordt synchroon gezet en overleeft het sneller sluiten
      // of slapen van mobiele browsers. De IndexedDB dirty-marker blijft de hoofdbron.
      markPendingLocalWriteHint();
      markDirty().catch(() => {});
      clearTimeout(centralSync.pushTimer);
      if (!navigator.onLine || !window.Clerk?.isSignedIn) {
        setOfflineStatus();
        return;
      }
      setCentralSyncStatus('☁ Lokale wijziging · synchronisatie gepland', 'busy');
      centralSync.pushTimer = setTimeout(() => {
        centralSync.pushTimer = null;
        centralPush().catch(() => {});
      }, 650);
    };
    window.scheduleCentralSync = scheduleCentralSync;

    startCentralPolling = function() {
      clearInterval(centralSync.pollTimer);
      centralSync.pollTimer = setInterval(async () => {
        if (centralSync.pushing || centralSync.pushTimer || document.visibilityState === 'hidden') return;
        if (!navigator.onLine) { setOfflineStatus(); return; }
        try {
          const meta = await readMeta();
          if (meta.dirty || centralSync.offlineDirty) await centralPush({ initial: true });
          else await centralPull({ apply: true, quiet: true });
          if (!centralSync.offlineDirty) setCentralSyncStatus('☁ Centraal gesynchroniseerd', 'ok');
        } catch (error) {
          console.warn('Centrale polling', error);
          if (isNetworkFailure(error)) setOfflineStatus();
          else setCentralSyncStatus(syncErrorStatus(error), 'error');
        }
      }, 20000);
    };
    window.startCentralPolling = startCentralPolling;

    async function refreshOnlineExtras() {
      if (!navigator.onLine || !window.Clerk?.isSignedIn) return;
      const tasks = [];
      if (typeof window.machineparkLoadWorkOrderTemplates === 'function') {
        tasks.push(window.machineparkLoadWorkOrderTemplates(true));
      }
      if (typeof window.machineparkLoadFaultLibrary === 'function') {
        tasks.push(window.machineparkLoadFaultLibrary(true).then(() => {
          if (typeof window.machineparkRenderFaultLibrary === 'function') window.machineparkRenderFaultLibrary();
        }));
      }
      if (tasks.length) await Promise.allSettled(tasks);
    }
    window.machineparkRefreshOnlineExtras = refreshOnlineExtras;

    function primeOfflineExtras() {
      if (!navigator.onLine) return;
      refreshOnlineExtras().catch((error) => console.warn('Extra centrale gegevens verversen', error));
    }

    startKoffieServiceApp = async function() {
      if (window.__koffieServiceStarted) return;
      window.__koffieServiceStarted = true;
      try {
        await openDB();
        const meta = await readMeta();
        centralSync.etag = meta.etag || centralSync.etag || null;
        centralSync.offlineDirty = Boolean(meta.dirty);
        restoreAccess();

        if (!navigator.onLine || !window.Clerk?.isSignedIn) {
          bind();
          await refresh();
          centralSync.enabled = true;
          startCentralPolling();
          setOfflineStatus();
          return;
        }

        if (meta.dirty) {
          // machinepark-sync-status-stability-v1
          // Lokale wijzigingen mogen de appstart nooit blokkeren. Open eerst
          // de lokale gegevens en probeer de centrale push daarna best-effort.
          bind();
          await refresh();
          centralSync.enabled = true;
          startCentralPolling();
          setCentralSyncStatus('☁ Lokale wijzigingen wachten op synchronisatie', 'busy');
          try {
            const pushed = await centralPush({ initial: true });
            if (!pushed?.offline) {
              await centralPull({ apply: true, quiet: true });
              await refreshOnlineExtras();
            } else {
              setOfflineStatus();
            }
          } catch (error) {
            console.warn('Opstartsynchronisatie mislukt; lokale gegevens blijven actief', error);
            const message = String(error?.message || error || '').replace(/\s+/g, ' ').trim().slice(0, 140);
            setCentralSyncStatus(
              message ? '☁ Synchronisatie wacht op controle · ' + message : '☁ Synchronisatie wacht op controle',
              'error'
            );
          }
          return;
        }

        let imported = 0;
        let statusChanged = 0;
        let remote = null;
        try {
          setCentralSyncStatus('☁ Centrale gegevens ophalen…', 'busy');
          remote = await centralPull({ apply: false, quiet: true });
        } catch (error) {
          // machinepark-startup-central-fallback-v1
          // Een centrale API-fout (ook 401/403/409/500) mag de lokale app niet blokkeren.
          // Bewaar de bestaande IndexedDB-data onaangeroerd, start lokaal en laat polling/reconnect later opnieuw proberen.
          console.warn('Centrale gegevens tijdelijk niet beschikbaar; Machinepark start met lokale gegevens', error);
          const startupError = String(error?.message || error || 'onbekende centrale fout').replace(/\s+/g, ' ').trim().slice(0, 180);
          window.machineparkLastCentralStartupError = startupError;
          remote = { exists: false, offline: true, startupError };
          setCentralSyncStatus(`☁ Centrale synchronisatie niet beschikbaar · ${startupError} · lokale gegevens actief`, 'error');
        }

        if (remote?.exists && remote.data) {
          await replaceLocalSnapshot(remote.data);
        } else if (remote?.exists === false && !remote?.offline) {
          imported = await ensureInventory2025();
          statusChanged = await ensureRedInventoryStatuses();
          try { await centralPush({ initial: true }); } catch (error) { console.warn('Eerste cloudopslag mislukt', error); }
        }

        bind();
        await refresh();
        centralSync.enabled = true;
        startCentralPolling();
        if (remote?.exists) setCentralSyncStatus('☁ Centraal gesynchroniseerd', 'ok');
        else if (!navigator.onLine) setOfflineStatus();
        primeOfflineExtras();
        if (imported) setTimeout(() => toast(imported + ' toestellen uit inventaris 2025 geïmporteerd'), 250);
        else if (statusChanged) setTimeout(() => toast(statusChanged + ' rood gemarkeerde toestellen op Buiten dienst gezet'), 250);
      } catch (error) {
        if (isNetworkFailure(error)) {
          try {
            bind();
            await refresh();
            centralSync.enabled = true;
            startCentralPolling();
            setOfflineStatus();
            return;
          } catch (_) {}
        }
        window.__koffieServiceStarted = false;
        console.error(error);
        const startupMessage = String(error?.message || error || '').replace(/\s+/g, ' ').trim().slice(0, 180);
        alert(
          startupMessage
            ? 'Machinepark kon niet worden gestart: ' + startupMessage
            : 'Machinepark kon niet worden gestart. De lokale gegevens zijn niet aangepast.'
        );
      }
    };
    window.startKoffieServiceApp = startKoffieServiceApp;

    window.machineparkTryOfflineSession = async function({ force = false } = {}) {
      if (!force && navigator.onLine) return false;
      if (!restoreAccess()) return false;
      document.documentElement.classList.add('machinepark-offline-session');
      const gate = document.getElementById('authGate');
      const shell = document.getElementById('appShell');
      if (gate) gate.classList.add('hidden');
      if (shell) shell.style.display = 'block';
      await startKoffieServiceApp();
      setOfflineStatus();
      return true;
    };

    window.addEventListener('offline', () => {
      setOfflineStatus();
      if (typeof toast === 'function') toast('Geen internet · je kunt verder werken. Wijzigingen blijven lokaal bewaard.');
    });

    // machinepark-online-sync-consistency-v1
    let immediateOnlineSyncPromise = null;
    let immediateOnlineSyncTimer = null;

    async function syncOnlineNow({ quiet = true } = {}) {
      if (!navigator.onLine || !window.__koffieServiceStarted || !window.Clerk?.isSignedIn) return { offline: !navigator.onLine };
      if (immediateOnlineSyncPromise) return immediateOnlineSyncPromise;
      immediateOnlineSyncPromise = (async () => {
        const meta = await readMeta();
        if (meta.dirty || centralSync.offlineDirty) {
          const pushed = await centralPush({ initial: true });
          if (pushed?.offline) return pushed;
        }
        const pulled = await centralPull({ apply: true, quiet: true });
        await refreshOnlineExtras();
        if (!quiet) setCentralSyncStatus('☁ Alles centraal gesynchroniseerd', 'ok');
        return pulled;
      })();
      try { return await immediateOnlineSyncPromise; }
      finally { immediateOnlineSyncPromise = null; }
    }
    window.machineparkSyncOnlineNow = syncOnlineNow;

    // Onderhoud en depannages zijn operationele registraties. Geef writes naar deze
    // stores een korte, aparte sync-trigger zodat iOS/Android de 650ms algemene
    // debounce niet hoeft af te wachten voordat de gebruiker de app verlaat.
    let serviceWriteSyncTimer = null;
    function queueServiceWriteSync(storeName) {
      if (storeName !== 'maintenance' && storeName !== 'breakdowns') return;
      markPendingLocalWriteHint();
      clearTimeout(serviceWriteSyncTimer);
      serviceWriteSyncTimer = setTimeout(async () => {
        serviceWriteSyncTimer = null;
        if (!navigator.onLine || !window.Clerk?.isSignedIn) return;
        if (centralSync.pushTimer) {
          clearTimeout(centralSync.pushTimer);
          centralSync.pushTimer = null;
        }
        try {
          setCentralSyncStatus('☁ Registratie centraal bevestigen…', 'busy');
          await syncOnlineNow({ quiet: false });
        } catch (error) {
          console.warn('Directe service-synchronisatie', error);
          if (isNetworkFailure(error)) setOfflineStatus();
          else setCentralSyncStatus('☁ Synchronisatie wacht op controle', 'error');
        }
      }, 90);
    }
    window.machineparkQueueServiceWriteSync = queueServiceWriteSync;

    const baseServicePut = typeof put === 'function' ? put : null;
    if (baseServicePut) {
      put = async function(storeName, item) {
        const result = await baseServicePut(storeName, item);
        queueServiceWriteSync(storeName);
        return result;
      };
      window.put = put;
    }

    const baseServicePutMany = typeof putMany === 'function' ? putMany : null;
    if (baseServicePutMany) {
      putMany = async function(storeName, items) {
        const result = await baseServicePutMany(storeName, items);
        queueServiceWriteSync(storeName);
        return result;
      };
      window.putMany = putMany;
    }

    const baseDeleteServiceRecordAtomic = typeof deleteServiceRecordAtomic === 'function' ? deleteServiceRecordAtomic : null;
    if (baseDeleteServiceRecordAtomic) {
      deleteServiceRecordAtomic = async function(storeName, record) {
        const result = await baseDeleteServiceRecordAtomic(storeName, record);
        queueServiceWriteSync(storeName);
        return result;
      };
      window.deleteServiceRecordAtomic = deleteServiceRecordAtomic;
    }

    function scheduleImmediateOnlineSync() {
      if (!navigator.onLine || !window.__koffieServiceStarted || !window.Clerk?.isSignedIn) return;
      clearTimeout(immediateOnlineSyncTimer);
      immediateOnlineSyncTimer = setTimeout(() => {
        immediateOnlineSyncTimer = null;
        syncOnlineNow({ quiet: true }).catch((error) => {
          console.warn('Directe online synchronisatie', error);
          if (isNetworkFailure(error)) setOfflineStatus();
          else setCentralSyncStatus('☁ Synchronisatie wacht op controle', 'error');
        });
      }, 120);
    }

    window.addEventListener('online', async () => {
      setCentralSyncStatus('☁ Verbinding hersteld · synchroniseren…', 'busy');
      if (document.documentElement.classList.contains('machinepark-offline-session') && !window.Clerk?.isSignedIn) {
        location.reload();
        return;
      }
      if (!window.__koffieServiceStarted || !window.Clerk?.isSignedIn) return;
      try {
        await syncOnlineNow({ quiet: false });
        if (typeof toast === 'function') toast('Verbinding hersteld · alles is centraal gesynchroniseerd.');
      } catch (error) {
        console.warn('Automatische reconnect-sync', error);
        if (isNetworkFailure(error)) setOfflineStatus();
        else setCentralSyncStatus('☁ Synchronisatie wacht op controle', 'error');
      }
    });

    window.addEventListener('focus', scheduleImmediateOnlineSync);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') scheduleImmediateOnlineSync();
    });

    // Trek offline toegang in zodra Clerk online bevestigt dat er geen sessie meer is.
    let clerkListenerInstalled = false;
    const attachClerkListener = () => {
      if (clerkListenerInstalled || !window.Clerk?.addListener) return false;
      clerkListenerInstalled = true;
      let wasSignedIn = Boolean(window.Clerk.isSignedIn);
      if (navigator.onLine && window.Clerk.loaded && !wasSignedIn) {
        try { localStorage.removeItem(OFFLINE_ACCESS_KEY); } catch (_) {}
      }
      window.Clerk.addListener(() => {
        const signedIn = Boolean(window.Clerk?.isSignedIn);
        if (wasSignedIn && !signedIn) {
          try { localStorage.removeItem(OFFLINE_ACCESS_KEY); } catch (_) {}
          document.documentElement.classList.remove('machinepark-offline-session');
        }
        wasSignedIn = signedIn;
      });
      return true;
    };
    if (!attachClerkListener()) {
      let checks = 0;
      const timer = setInterval(() => {
        checks += 1;
        if (attachClerkListener() || checks > 60) clearInterval(timer);
      }, 500);
    }

    if (!navigator.onLine) {
      window.machineparkTryOfflineSession().catch((error) => console.warn('Offline opstart', error));
    } else {
      primeOfflineExtras();
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', installOfflineLayer, { once: true });
  else setTimeout(installOfflineLayer, 0);
})();
