from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="photo-storage-optimization-v2"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    replace_once(
        "await put('parts',obj);closeModal();await refresh();toast('Onderdeel opgeslagen')",
        "if(typeof window.machineparkPersistPartPhoto==='function')obj.photo=await window.machineparkPersistPartPhoto(obj.id,obj.photo||'');await put('parts',obj);closeModal();await refresh();toast('Onderdeel opgeslagen')",
        'onderdeelfoto apart opslaan',
    )

    replace_once(
        'const photoCell = photo ? `<img class="device-overview-photo" src="${esc(photo)}" alt="Overzichtsfoto ${esc(d.assetCode || d.model || \'toestel\')}">`',
        'const photoCell = photo ? `<img class="device-overview-photo" src="${esc(window.machineparkThumbnailRef?window.machineparkThumbnailRef(photo):photo)}" data-full-src="${esc(photo)}" loading="lazy" decoding="async" fetchpriority="low" alt="Overzichtsfoto ${esc(d.assetCode || d.model || \'toestel\')}">`',
        'toestellenoverzicht thumbnail en lazy loading',
    )

    replace_once(
        '${p.photo?`<img class="thumb" src="${p.photo}" alt="">`:\'<div class="thumb placeholder">▣</div>\'}',
        '${p.photo?`<img class="thumb" src="${esc(window.machineparkThumbnailRef?window.machineparkThumbnailRef(p.photo):p.photo)}" data-full-src="${esc(p.photo)}" loading="lazy" decoding="async" fetchpriority="low" alt="">`:\'<div class="thumb placeholder">▣</div>\'}',
        'onderdelenoverzicht thumbnail en lazy loading',
    )

    index = index.replace(
        '<div class="device-detail-photo"><img src="${esc(src)}" alt="Toestelfoto ${index + 1}">',
        '<div class="device-detail-photo"><img src="${esc(src)}" loading="lazy" decoding="async" alt="Toestelfoto ${index + 1}">',
    )

    replace_once(
        "  async function normalizePartImageForExcel(dataUrl) {\n    const image = dataUrlExportImage(dataUrl);",
        "  async function normalizePartImageForExcel(dataUrl) {\n    if (dataUrl && !String(dataUrl).startsWith('data:')) {\n      try {\n        const response = await fetch(String(dataUrl), { cache: 'no-store' });\n        if (response.ok) {\n          const blob = await response.blob();\n          dataUrl = await new Promise((resolve, reject) => {\n            const reader = new FileReader();\n            reader.onload = () => resolve(String(reader.result || ''));\n            reader.onerror = () => reject(reader.error);\n            reader.readAsDataURL(blob);\n          });\n        }\n      } catch (_) {}\n    }\n    const image = dataUrlExportImage(dataUrl);",
        'Excel export Blob-onderdeelfoto',
    )

    replace_once(
        "      width: img.style.width,\n      height: img.style.height,\n    }));",
        "      width: img.style.width,\n      height: img.style.height,\n      src: img.getAttribute('src'),\n      loading: img.getAttribute('loading'),\n    }));",
        'print originele bron bewaren',
    )
    replace_once(
        "    photos.forEach(img => {\n      const rect = img.getBoundingClientRect();",
        "    photos.forEach(img => {\n      if (img.dataset.fullSrc) img.setAttribute('src', img.dataset.fullSrc);\n      img.setAttribute('loading', 'eager');\n      const rect = img.getBoundingClientRect();",
        'print volledige onderdeelafbeelding',
    )
    replace_once(
        "    return () => original.forEach(({img,width,height}) => {\n      img.style.width = width;\n      img.style.height = height;\n      img.classList.remove('parts-print-photo');\n    });",
        "    return () => original.forEach(({img,width,height,src,loading}) => {\n      img.style.width = width;\n      img.style.height = height;\n      if (src === null) img.removeAttribute('src'); else img.setAttribute('src', src);\n      if (loading === null) img.removeAttribute('loading'); else img.setAttribute('loading', loading);\n      img.classList.remove('parts-print-photo');\n    });",
        'print thumbnail herstellen',
    )

    style = f'''
<style {MARKER}>
.device-overview-photo,.thumb{{content-visibility:auto}}
.photo-optimization-note{{font-size:11px;color:var(--muted)}}
</style>
'''
    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: echte </head> ontbreekt voor foto-optimalisatie')
    index = index.replace('</head>', style + '</head>', 1)

    script = r'''
<script data-machinepark-build-fix="photo-storage-optimization-v2">
(() => {
  const DEVICE_PHOTO_URL = '/.netlify/functions/device-photos';
  const PART_PHOTO_URL = '/.netlify/functions/part-photos';
  const LEGACY_MIGRATION_KEY = 'machinepark-photo-thumbnails-v1';
  let photoSaveBusy = 0;
  let migrationTimer = null;

  function ownPhotoEndpoint(src) {
    const value = String(src || '');
    if (value.includes('/.netlify/functions/device-photos?')) return DEVICE_PHOTO_URL;
    if (value.includes('/.netlify/functions/part-photos?')) return PART_PHOTO_URL;
    return '';
  }

  window.machineparkThumbnailRef = function(src) {
    const value = String(src || '').trim();
    if (!value || !ownPhotoEndpoint(value)) return value;
    try {
      const url = new URL(value, location.origin);
      url.searchParams.set('variant', 'thumb');
      return url.pathname + '?' + url.searchParams.toString();
    } catch (_) {
      return value;
    }
  };

  function thumbnailDataFromSource(src, max = 180, quality = .62) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        try {
          const scale = Math.min(1, max / Math.max(img.naturalWidth || img.width || 1, img.naturalHeight || img.height || 1));
          const canvas = document.createElement('canvas');
          canvas.width = Math.max(1, Math.round((img.naturalWidth || img.width || 1) * scale));
          canvas.height = Math.max(1, Math.round((img.naturalHeight || img.height || 1) * scale));
          const ctx = canvas.getContext('2d');
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          resolve(canvas.toDataURL('image/jpeg', quality));
        } catch (error) {
          reject(error);
        }
      };
      img.onerror = () => reject(new Error('Foto kon niet voor thumbnail worden geladen.'));
      img.src = String(src || '');
    });
  }

  function isRawPhoto(src) {
    return String(src || '').startsWith('data:image/');
  }

  function canManagePartPhotosClient() {
    if (window.machineparkAccessReady && typeof window.machineparkHasPermission === 'function') {
      return window.machineparkHasPermission('parts.edit') || window.machineparkHasPermission('parts.add');
    }
    return Boolean(window.machineparkCanEdit?.parts);
  }

  function afterUserWork(task, delay = 1400) {
    const run = () => {
      if (photoSaveBusy > 0) {
        setTimeout(() => afterUserWork(task, 900), 900);
        return;
      }
      Promise.resolve().then(task).catch((error) => console.warn('Foto-optimalisatie achtergrondtaak', error));
    };
    setTimeout(() => {
      if ('requestIdleCallback' in window) requestIdleCallback(run, { timeout: 4000 });
      else run();
    }, delay);
  }

  window.machineparkPersistDevicePhotoList = async function(deviceId, photos, { force = false } = {}) {
    const list = (Array.isArray(photos) ? photos : []).filter((src) => typeof src === 'string' && src.trim()).slice(0, 5);
    if (!force && !list.some(isRawPhoto)) return list;
    const rawIndexes = list.map((src, index) => isRawPhoto(src) ? index : -1).filter((index) => index >= 0);
    photoSaveBusy += 1;
    try {
      const headers = await centralHeaders(true);
      const res = await fetch(DEVICE_PHOTO_URL, {
        method: 'POST',
        headers,
        body: JSON.stringify({ deviceId, photos: list }),
        cache: 'no-store',
      });
      const text = await res.text();
      let body = {};
      try { body = text ? JSON.parse(text) : {}; } catch (_) {}
      if (!res.ok) throw new Error(body.error || text || `Toestelfoto’s opslaan mislukt (${res.status})`);
      const refs = Array.isArray(body.photos) ? body.photos.slice(0, 5) : list;
      rawIndexes.forEach((index) => {
        const ref = refs[index];
        if (ref) afterUserWork(() => ensureStoredThumbnail('device', deviceId, ref), 1800 + index * 300);
      });
      return refs;
    } finally {
      photoSaveBusy = Math.max(0, photoSaveBusy - 1);
    }
  };

  window.machineparkPersistPartPhoto = async function(partId, photo) {
    const value = String(photo || '').trim();
    if (!value) return '';
    if (value.includes('/.netlify/functions/part-photos?')) return value;
    if (!isRawPhoto(value)) return value;
    photoSaveBusy += 1;
    try {
      const headers = await centralHeaders(true);
      const res = await fetch(PART_PHOTO_URL, {
        method: 'POST',
        headers,
        body: JSON.stringify({ partId, photo: value }),
        cache: 'no-store',
      });
      const text = await res.text();
      let body = {};
      try { body = text ? JSON.parse(text) : {}; } catch (_) {}
      if (!res.ok) throw new Error(body.error || text || `Onderdeelfoto opslaan mislukt (${res.status})`);
      const ref = String(body.photo || value);
      if (ref) afterUserWork(() => ensureStoredThumbnail('part', partId, ref), 1800);
      return ref;
    } finally {
      photoSaveBusy = Math.max(0, photoSaveBusy - 1);
    }
  };

  function writePartDirect(part) {
    return new Promise((resolve, reject) => {
      const tr = db.transaction('parts', 'readwrite');
      const request = tr.objectStore('parts').put(part);
      request.onerror = () => reject(request.error);
      tr.oncomplete = () => resolve(part);
      tr.onerror = () => reject(tr.error);
      tr.onabort = () => reject(tr.error || new Error('Lokale onderdeelfotomigratie afgebroken'));
    });
  }

  const baseLocalSnapshotForPartPhotos = localSnapshot;
  localSnapshot = async function() {
    const data = await baseLocalSnapshotForPartPhotos();
    if (!Array.isArray(data.parts) || !canManagePartPhotosClient() || photoSaveBusy > 0) return data;
    for (let index = 0; index < data.parts.length; index += 1) {
      const part = data.parts[index];
      if (!isRawPhoto(part?.photo)) continue;
      const photo = await window.machineparkPersistPartPhoto(part.id, part.photo);
      const updated = { ...part, photo };
      data.parts[index] = updated;
      await writePartDirect(updated);
    }
    return data;
  };

  async function ensureStoredThumbnail(kind, id, photoRef) {
    const endpoint = kind === 'device' ? DEVICE_PHOTO_URL : PART_PHOTO_URL;
    if (!String(photoRef || '').includes(endpoint + '?')) return false;
    const thumb = window.machineparkThumbnailRef(photoRef);
    try {
      const probe = await fetch(thumb, { method: 'HEAD', cache: 'no-store' });
      if (probe.ok) return true;
      const thumbnail = await thumbnailDataFromSource(photoRef);
      const headers = await centralHeaders(true);
      const body = kind === 'device'
        ? { action: 'thumbnail', deviceId: id, photoRef, thumbnail }
        : { action: 'thumbnail', partId: id, photoRef, thumbnail };
      const res = await fetch(endpoint, { method: 'POST', headers, body: JSON.stringify(body), cache: 'no-store' });
      return res.ok;
    } catch (error) {
      console.warn('Thumbnail kon niet worden voorbereid', error);
      return false;
    }
  }

  async function migrateExistingPartPhotos() {
    if (photoSaveBusy > 0 || !canManagePartPhotosClient() || !Array.isArray(state?.parts)) return 0;
    let migrated = 0;
    for (const part of state.parts) {
      if (photoSaveBusy > 0) break;
      if (!isRawPhoto(part?.photo)) continue;
      try {
        const photo = await window.machineparkPersistPartPhoto(part.id, part.photo);
        part.photo = photo;
        await writePartDirect(part);
        migrated += 1;
        await new Promise((resolve) => setTimeout(resolve, 120));
      } catch (error) {
        console.warn('Bestaande onderdeelfoto kon niet worden gemigreerd', part?.artNr, error);
      }
    }
    if (migrated && photoSaveBusy === 0) {
      renderParts();
      try {
        if (centralSync?.enabled) {
          centralSync.pending = true;
          await centralPush();
        }
      } catch (error) {
        console.warn('Centrale opslag na onderdeelfotomigratie', error);
      }
    }
    return migrated;
  }

  async function optimizeExistingThumbnailLibrary() {
    if (photoSaveBusy > 0 || document.visibilityState !== 'visible') return false;
    const migratedParts = await migrateExistingPartPhotos();
    let optimized = 0;
    const shouldScanLegacy = localStorage.getItem(LEGACY_MIGRATION_KEY) !== 'done';
    if (shouldScanLegacy && photoSaveBusy === 0) {
      for (const device of (Array.isArray(state?.devices) ? state.devices : [])) {
        if (photoSaveBusy > 0) break;
        for (const photo of (Array.isArray(device?.devicePhotos) ? device.devicePhotos : []).slice(0, 5)) {
          if (photoSaveBusy > 0) break;
          if (await ensureStoredThumbnail('device', device.id, photo)) optimized += 1;
          await new Promise((resolve) => setTimeout(resolve, 120));
        }
      }
      for (const part of (Array.isArray(state?.parts) ? state.parts : [])) {
        if (photoSaveBusy > 0) break;
        if (part?.photo && await ensureStoredThumbnail('part', part.id, part.photo)) optimized += 1;
        await new Promise((resolve) => setTimeout(resolve, 120));
      }
      if (photoSaveBusy === 0) localStorage.setItem(LEGACY_MIGRATION_KEY, 'done');
    }
    if (migratedParts || optimized) console.info(`[Machinepark] foto-optimalisatie: ${migratedParts} onderdelen gemigreerd, ${optimized} thumbnails gecontroleerd`);
    return true;
  }

  function scheduleLibraryOptimization(delay = 15000) {
    clearTimeout(migrationTimer);
    migrationTimer = setTimeout(() => {
      const run = async () => {
        if (photoSaveBusy > 0) {
          scheduleLibraryOptimization(8000);
          return;
        }
        const completed = await optimizeExistingThumbnailLibrary().catch((error) => {
          console.warn('Foto-optimalisatie', error);
          return false;
        });
        if (!completed) scheduleLibraryOptimization(10000);
      };
      if ('requestIdleCallback' in window) requestIdleCallback(run, { timeout: 6000 });
      else run();
    }, delay);
  }

  scheduleLibraryOptimization();
})();
</script>
'''

    if '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor foto-optimalisatie')
    before, after = index.rsplit('</body>', 1)
    index = before + script + '</body>' + after
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'machineparkThumbnailRef',
    'loading="lazy"',
    'machineparkPersistPartPhoto',
    'part-photos',
    'ensureStoredThumbnail',
    'requestIdleCallback',
    "method: 'HEAD'",
    'data-full-src',
    "const response = await fetch(String(dataUrl), { cache: 'no-store' });",
    'photoSaveBusy',
    'afterUserWork',
    'scheduleLibraryOptimization',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: foto-optimalisatie ontbreekt ({needle})')

print('[Machinepark] snelle foto-opslag met thumbnails op achtergrond, lazy loading en bestaande foto-optimalisatie actief')
