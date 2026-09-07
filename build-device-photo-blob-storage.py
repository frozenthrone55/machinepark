from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="device-photo-blob-storage-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    old_save = "await put('devices',obj);if(centralSync.enabled){clearTimeout(centralSync.pushTimer);centralSync.pushTimer=null;centralSync.pending=true;await centralPush()}closeModal();await refresh();toast(editing&&val(fd,'newLocation')?'Toestel en locatiewijziging centraal opgeslagen':'Toestel centraal opgeslagen')"
    new_save = "if(typeof window.machineparkPersistDevicePhotoList==='function'){const canManagePhotos=!window.machineparkAccessReady||typeof window.machineparkHasPermission!=='function'||window.machineparkHasPermission(editing?'devices.edit':'devices.add');obj.devicePhotos=await window.machineparkPersistDevicePhotoList(obj.id,Array.isArray(obj.devicePhotos)?obj.devicePhotos:[],{force:canManagePhotos})}await put('devices',obj);if(centralSync.enabled){clearTimeout(centralSync.pushTimer);centralSync.pushTimer=null;centralSync.pending=true;await centralPush()}closeModal();await refresh();toast(editing&&val(fd,'newLocation')?'Toestel en locatiewijziging centraal opgeslagen':'Toestel centraal opgeslagen')"
    replace_once(old_save, new_save, 'toestelfoto’s apart opslaan voor centrale sync')

    script = r'''
<script data-machinepark-build-fix="device-photo-blob-storage-v1">
(() => {
  const DEVICE_PHOTO_STORAGE_URL = '/.netlify/functions/device-photos';

  function hasRawDevicePhoto(photos) {
    return (Array.isArray(photos) ? photos : []).some((src) => String(src || '').startsWith('data:image/'));
  }

  window.machineparkPersistDevicePhotoList = async function(deviceId, photos, { force = false } = {}) {
    const list = (Array.isArray(photos) ? photos : []).filter((src) => typeof src === 'string' && src.trim()).slice(0, 5);
    if (!force && !hasRawDevicePhoto(list)) return list;
    const headers = await centralHeaders(true);
    const res = await fetch(DEVICE_PHOTO_STORAGE_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify({ deviceId, photos: list }),
      cache: 'no-store',
    });
    const text = await res.text();
    let body = {};
    try { body = text ? JSON.parse(text) : {}; } catch (_) {}
    if (!res.ok) throw new Error(body.error || text || `Toestelfoto’s opslaan mislukt (${res.status})`);
    return Array.isArray(body.photos) ? body.photos.slice(0, 5) : list;
  };

  function writeDeviceDirect(device) {
    return new Promise((resolve, reject) => {
      const tr = db.transaction('devices', 'readwrite');
      const request = tr.objectStore('devices').put(device);
      request.onerror = () => reject(request.error);
      tr.oncomplete = () => resolve(device);
      tr.onerror = () => reject(tr.error);
      tr.onabort = () => reject(tr.error || new Error('Lokale fotomigratie afgebroken'));
    });
  }

  const baseLocalSnapshotForDevicePhotos = localSnapshot;
  localSnapshot = async function() {
    const data = await baseLocalSnapshotForDevicePhotos();
    if (!Array.isArray(data.devices)) return data;
    const migrated = [];
    for (const device of data.devices) {
      const photos = Array.isArray(device.devicePhotos) ? device.devicePhotos : [];
      if (!hasRawDevicePhoto(photos)) {
        migrated.push(device);
        continue;
      }
      const refs = await window.machineparkPersistDevicePhotoList(device.id, photos, { force: false });
      const updated = { ...device, devicePhotos: refs };
      migrated.push(updated);
      await writeDeviceDirect(updated);
    }
    data.devices = migrated;
    return data;
  };

  indexPhotoRefs = function(device) {
    return (Array.isArray(device?.devicePhotos) ? device.devicePhotos : []).filter((src) => typeof src === 'string' && src.trim()).slice(0, 5);
  };
})();
</script>
'''
    replace_once('</body>', script + '</body>', 'Blob-opslag script toestelfoto’s')
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    index_path.write_text(index, encoding='utf-8')
    print('[Machinepark] toestelfoto’s worden apart in Netlify Blobs opgeslagen')
else:
    print('[Machinepark] aparte Blob-opslag voor toestelfoto’s reeds actief')
