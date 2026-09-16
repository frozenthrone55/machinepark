from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
index = INDEX.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="mobile-device-photo-save-reliability-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    index = index.replace(old, new, 1)


if MARKER not in index:
    old = r'''    if (input) input.addEventListener('change', async () => {
      if (!canManage) return;
      const files = [...(input.files || [])];
      const available = DEVICE_PHOTO_LIMIT - photos.length;
      if (files.length > available) {
        alert(`Je kunt nog maximaal ${available} foto${available === 1 ? '' : '’s'} toevoegen. Een toestel kan maximaal ${DEVICE_PHOTO_LIMIT} foto’s bevatten.`);
        input.value = '';
        return;
      }
      if (!files.length) return;
      input.disabled = true;
      if (status) status.textContent = 'Foto’s worden verwerkt…';
      try {
        const wasEmpty = photos.length === 0;
        for (const file of files) {
          const compressed = await compressDevicePhoto(file);
          if (compressed) photos.push(compressed);
        }
        photos = photos.slice(0, DEVICE_PHOTO_LIMIT);
        if (wasEmpty && photos.length) selected = 0;
      } catch (error) {
        console.error(error);
        alert('Een van de foto’s kon niet worden verwerkt.');
      } finally {
        input.value = '';
        render();
      }
    });

    render();'''

    new = r'''    let photoProcessingPromise = null;
    let queuedPhotoSubmit = false;

    function setDevicePhotoSubmitBusy(busy) {
      const submit = document.querySelector('#modalForm button[type="submit"]');
      if (!submit) return;
      if (busy) {
        if (!submit.dataset.devicePhotoOriginalText) submit.dataset.devicePhotoOriginalText = submit.textContent || 'Opslaan';
        submit.disabled = true;
        submit.dataset.devicePhotoWaiting = '1';
        submit.textContent = 'Foto verwerken…';
      } else if (submit.dataset.devicePhotoWaiting === '1') {
        submit.disabled = false;
        submit.textContent = submit.dataset.devicePhotoOriginalText || 'Opslaan';
        delete submit.dataset.devicePhotoWaiting;
      }
    }

    if (input) input.addEventListener('change', () => {
      if (!canManage) return;
      const files = [...(input.files || [])];
      const available = DEVICE_PHOTO_LIMIT - photos.length;
      if (files.length > available) {
        alert(`Je kunt nog maximaal ${available} foto${available === 1 ? '' : '’s'} toevoegen. Een toestel kan maximaal ${DEVICE_PHOTO_LIMIT} foto’s bevatten.`);
        input.value = '';
        return;
      }
      if (!files.length) return;
      input.disabled = true;
      if (status) status.textContent = 'Foto’s worden verwerkt…';

      const task = (async () => {
        try {
          const wasEmpty = photos.length === 0;
          for (const file of files) {
            const compressed = await compressDevicePhoto(file);
            if (compressed) photos.push(compressed);
          }
          photos = photos.slice(0, DEVICE_PHOTO_LIMIT);
          if (wasEmpty && photos.length) selected = 0;
        } finally {
          // Belangrijk op mobiel: werk de hidden velden bij vóór de promise klaar is.
          // Een eerder ingedrukte Opslaan-knop mag pas daarna opnieuw submitten.
          input.value = '';
          render();
        }
      })();

      photoProcessingPromise = task;
      task.then(
        () => {},
        (error) => {
          console.error(error);
          alert('Een van de foto’s kon niet worden verwerkt. Probeer de foto opnieuw toe te voegen.');
        },
      ).finally(() => {
        if (photoProcessingPromise === task) photoProcessingPromise = null;
      });
    });

    const deviceFormElement = document.getElementById('modalForm');
    if (deviceFormElement) deviceFormElement.addEventListener('submit', (event) => {
      if (!photoProcessingPromise) return;

      // De eerste mobiele tik op Opslaan wordt niet verloren. Wacht op FileReader,
      // image-decode en canvascompressie en submit daarna exact één keer opnieuw.
      event.preventDefault();
      event.stopImmediatePropagation();
      if (queuedPhotoSubmit) return;
      queuedPhotoSubmit = true;
      const pending = photoProcessingPromise;
      const submitter = event.submitter;
      setDevicePhotoSubmitBusy(true);
      if (status) status.textContent = 'Foto wordt verwerkt · toestel wordt daarna automatisch opgeslagen…';

      pending.then(() => {
        queuedPhotoSubmit = false;
        setDevicePhotoSubmitBusy(false);
        if (!deviceFormElement.isConnected) return;
        if (typeof deviceFormElement.requestSubmit === 'function') {
          const usableSubmitter = submitter && submitter.isConnected && !submitter.disabled ? submitter : undefined;
          deviceFormElement.requestSubmit(usableSubmitter);
        } else {
          const fallback = deviceFormElement.querySelector('button[type="submit"]');
          if (fallback) fallback.click();
        }
      }).catch(() => {
        queuedPhotoSubmit = false;
        setDevicePhotoSubmitBusy(false);
        if (status) status.textContent = 'Foto kon niet worden verwerkt · toestel is nog niet opgeslagen.';
      });
    }, true);

    render();'''

    replace_once(old, new, 'mobiele toestelfoto verwerking en submit-wachtrij')
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
for needle in [
    MARKER,
    'let photoProcessingPromise = null;',
    'event.stopImmediatePropagation();',
    "deviceFormElement.requestSubmit(usableSubmitter);",
    'toestel wordt daarna automatisch opgeslagen',
    'toestel is nog niet opgeslagen',
]:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: mobiele toestelfoto-save ontbreekt ({needle})')

print('[Machinepark] mobiele toestelfoto-save wacht betrouwbaar op fotoverwerking en gebruikt één submit')
