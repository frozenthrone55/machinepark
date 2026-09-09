from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
API = ROOT / "synology" / "api" / "photo-library.php"
MARKER = 'data-machinepark-readable-photo-library="v1"'

index = INDEX.read_text(encoding="utf-8")

if MARKER not in index:
    script = r'''
<script data-machinepark-readable-photo-library="v1">
(() => {
  const ENDPOINT = './synology/api/photo-library.php';
  let timer = 0;
  let busy = false;
  let rerun = false;

  function deviceCode(device) {
    const raw = String(device?.assetCode || device?.code || device?.id || '').trim();
    return raw ? raw.toUpperCase() : '';
  }

  function photoLibraryPayload() {
    const devices = (state.devices || []).map(deviceCode).filter(Boolean);
    const byId = new Map((state.devices || []).map(device => [String(device.id || ''), device]));
    const items = [];

    for (const device of (state.devices || [])) {
      const code = deviceCode(device);
      if (!code) continue;
      items.push({
        deviceCode: code,
        category: 'Toestel',
        recordId: 'toestel',
        date: '',
        photos: Array.isArray(device.devicePhotos) ? device.devicePhotos.slice(0,10) : [],
      });
    }

    const addRecords = (storeName, records) => {
      for (const record of (records || [])) {
        const device = byId.get(String(record?.deviceId || ''));
        const code = deviceCode(device);
        if (!code) continue;
        const isService = Boolean(record?.serviceReportId || record?.serviceVisitId || (record?.isDraft === true && record?.draftKind === 'serviceVisit'));
        const category = isService ? 'Service' : (storeName === 'maintenance' ? 'Onderhoud' : 'Depannage');
        items.push({
          deviceCode: code,
          category,
          recordId: String(record?.id || 'record'),
          date: String(record?.date || record?.serviceReportDate || record?.serviceVisitDate || '').slice(0,10),
          photos: Array.isArray(record?.photos) ? record.photos.slice(0,10) : [],
        });
      }
    };

    addRecords('maintenance', state.maintenance);
    addRecords('breakdowns', state.breakdowns);
    return { devices:[...new Set(devices)], items };
  }

  async function syncReadablePhotoLibrary() {
    if (busy) { rerun = true; return; }
    if (!Array.isArray(state?.devices) || !state.devices.length) return;
    busy = true;
    try {
      const headers = typeof centralHeaders === 'function'
        ? await centralHeaders(true)
        : {'Content-Type':'application/json'};
      if (!headers['Content-Type']) headers['Content-Type'] = 'application/json';
      const response = await fetch(ENDPOINT, {
        method:'POST',
        headers,
        body:JSON.stringify(photoLibraryPayload()),
        cache:'no-store',
      });
      if (!response.ok && response.status !== 404) {
        const text = await response.text();
        throw new Error(text || ('Fotobibliotheek synchroniseren mislukt (' + response.status + ')'));
      }
    } catch (error) {
      console.warn('[Machinepark] leesbare Synology-fotobibliotheek', error);
    } finally {
      busy = false;
      if (rerun) { rerun = false; scheduleReadablePhotoLibrary(1200); }
    }
  }

  function scheduleReadablePhotoLibrary(delay = 2200) {
    clearTimeout(timer);
    timer = setTimeout(syncReadablePhotoLibrary, delay);
  }

  window.machineparkSyncReadablePhotoLibrary = syncReadablePhotoLibrary;
  window.machineparkScheduleReadablePhotoLibrary = scheduleReadablePhotoLibrary;

  const baseDevicePersist = window.machineparkPersistDevicePhotoList;
  if (typeof baseDevicePersist === 'function') {
    window.machineparkPersistDevicePhotoList = async function(...args) {
      const result = await baseDevicePersist.apply(this,args);
      scheduleReadablePhotoLibrary();
      return result;
    };
  }

  const baseServicePersist = window.machineparkPersistServicePhotos;
  if (typeof baseServicePersist === 'function') {
    window.machineparkPersistServicePhotos = async function(...args) {
      const result = await baseServicePersist.apply(this,args);
      scheduleReadablePhotoLibrary();
      return result;
    };
  }

  window.addEventListener('online', () => scheduleReadablePhotoLibrary(1200));
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') scheduleReadablePhotoLibrary(1800);
  });
  setInterval(() => {
    if (document.visibilityState === 'visible' && navigator.onLine !== false) scheduleReadablePhotoLibrary(100);
  }, 300000);
  scheduleReadablePhotoLibrary(6000);
})();
</script>
'''
    if '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor leesbare fotobibliotheek')
    index = index.replace('</body>', script + '</body>', 1)

required = [
    MARKER,
    "category: 'Toestel'",
    "'Onderhoud' : 'Depannage'",
    "const category = isService ? 'Service'",
    'machineparkSyncReadablePhotoLibrary',
    'machineparkPersistDevicePhotoList',
    'machineparkPersistServicePhotos',
    'photo-library.php',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: leesbare fotobibliotheek ontbreekt ({needle})')

api = API.read_text(encoding='utf-8')
for needle in [
    "MP_READABLE_PHOTO_ROOT",
    "/volume1/MachineparkData/Fotos",
    "['Toestel','Onderhoud','Depannage','Service']",
    "MP_*",
    "readable-photo-library",
]:
    if needle not in api:
        raise SystemExit(f'Buildvalidatie mislukt: photo-library API ontbreekt ({needle})')

INDEX.write_text(index, encoding='utf-8')
print('[Machinepark] leesbare Synology-fotobibliotheek per toestel actief')
