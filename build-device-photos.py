from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="device-photos-v2"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    replace_once(
        '<thead><tr><th class="sortable" data-device-sort="assetCode">Toestelcode',
        '<thead><tr><th>Foto</th><th class="sortable" data-device-sort="assetCode">Toestelcode',
        'fotokolom toestellenoverzicht',
    )

    replace_once(
        "notes:val(fd,'notes'),createdAt:old.createdAt||now",
        "notes:val(fd,'notes'),devicePhotos:(typeof window.machineparkDevicePhotosFromForm==='function'?window.machineparkDevicePhotosFromForm(fd,old):(Array.isArray(old.devicePhotos)?old.devicePhotos.slice(0,5):[])),deviceOverviewPhotoIndex:(typeof window.machineparkDeviceOverviewIndexFromForm==='function'?window.machineparkDeviceOverviewIndexFromForm(fd,old):Number(old.deviceOverviewPhotoIndex||0)),createdAt:old.createdAt||now",
        'toestelfoto opslag',
    )

    style = f'''
<style {MARKER}>
.device-table{{min-width:1200px}}
.device-overview-photo-cell{{width:82px}}
.device-overview-photo{{width:64px;height:64px;display:block;object-fit:cover;border:1px solid var(--line);border-radius:11px;background:#f2f5f3}}
.device-overview-photo-placeholder{{width:64px;height:64px;border:1px dashed #c9d4cf;border-radius:11px;background:#f7f9f8;color:#9aa7a1;display:grid;place-items:center;font-size:18px}}
.device-photo-field{{border-top:1px solid var(--line);padding-top:15px;margin-top:2px}}
.device-photo-toolbar{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;margin-bottom:11px}}
.device-photo-toolbar strong{{display:block;font-size:13px}}
.device-photo-toolbar small{{display:block;color:var(--muted);font-size:11px;line-height:1.45;margin-top:3px}}
.device-photo-add.disabled{{opacity:.48;cursor:not-allowed}}
.device-photo-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}
.device-photo-card{{border:1px solid var(--line);border-radius:13px;background:#fbfcfb;overflow:hidden;display:grid;grid-template-rows:150px auto}}
.device-photo-image-wrap{{position:relative;background:#eef2f0;overflow:hidden}}
.device-photo-card img{{width:100%;height:100%;object-fit:cover;display:block;cursor:zoom-in}}
.device-photo-number{{position:absolute;left:8px;top:8px;background:rgba(20,45,38,.82);color:#fff;border-radius:999px;padding:4px 7px;font-size:10px;font-weight:800}}
.device-photo-card-foot{{padding:9px;display:grid;gap:8px}}
.device-photo-overview{{display:flex;align-items:center;gap:7px;font-size:11.5px;font-weight:700;color:#36443e;cursor:pointer}}
.device-photo-overview input{{width:16px;height:16px;margin:0;accent-color:var(--brand2)}}
.device-photo-remove{{border:0;background:#fff0f0;color:var(--danger);border-radius:8px;padding:7px 9px;font-size:11px;font-weight:700;cursor:pointer}}
.device-photo-readonly{{font-size:10.5px;color:var(--muted)}}
.device-detail-photo-section{{border:1px solid var(--line);border-radius:14px;padding:13px;background:#fbfcfb}}
.device-detail-photo-head{{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px}}
.device-detail-photo-head strong{{font-size:13px}}
.device-detail-photo-gallery{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}}
.device-detail-photo{{position:relative;aspect-ratio:4/3;border-radius:11px;overflow:hidden;border:1px solid var(--line);background:#eef2f0}}
.device-detail-photo img{{width:100%;height:100%;object-fit:cover;display:block;cursor:zoom-in}}
.device-detail-photo .badge{{position:absolute;left:7px;bottom:7px;box-shadow:0 2px 8px rgba(0,0,0,.12)}}
@media(max-width:700px){{
  .device-photo-grid,.device-detail-photo-gallery{{grid-template-columns:1fr}}
  .device-photo-card{{grid-template-rows:190px auto}}
  .device-photo-toolbar .btn{{width:100%}}
}}
</style>
'''
    replace_once('</head>', style + '</head>', 'toestelfoto stylesheet')

    script = r'''
<script data-machinepark-build-fix="device-photos-v2">
(() => {
  const DEVICE_PHOTO_LIMIT = 5;

  function normalizedDevicePhotos(device) {
    return (Array.isArray(device?.devicePhotos) ? device.devicePhotos : [])
      .filter((src) => typeof src === 'string' && src.trim())
      .slice(0, DEVICE_PHOTO_LIMIT);
  }

  function compressDevicePhoto(file) {
    if (!file || !file.size) return Promise.resolve('');
    return new Promise((resolve, reject) => {
      const img = new Image();
      const reader = new FileReader();
      reader.onerror = reject;
      reader.onload = (event) => { img.src = event.target.result; };
      img.onerror = reject;
      img.onload = () => {
        const max = 720;
        const scale = Math.min(1, max / Math.max(img.width, img.height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(img.width * scale));
        canvas.height = Math.max(1, Math.round(img.height * scale));
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        let quality = .68;
        let data = canvas.toDataURL('image/jpeg', quality);
        while (data.length > 260000 && quality > .44) {
          quality -= .08;
          data = canvas.toDataURL('image/jpeg', quality);
        }
        resolve(data);
      };
      reader.readAsDataURL(file);
    });
  }

  function overviewIndex(device, photos = normalizedDevicePhotos(device)) {
    if (!photos.length) return 0;
    const raw = Number(device?.deviceOverviewPhotoIndex ?? 0);
    return Number.isInteger(raw) && raw >= 0 && raw < photos.length ? raw : 0;
  }

  window.machineparkDeviceOverviewPhoto = function(device) {
    const photos = normalizedDevicePhotos(device);
    return photos[overviewIndex(device, photos)] || photos[0] || '';
  };

  window.machineparkDevicePhotosFromForm = function(fd, old = {}) {
    const raw = String(fd.get('devicePhotosJson') || '');
    if (!raw) return normalizedDevicePhotos(old);
    try {
      const parsed = JSON.parse(raw);
      return (Array.isArray(parsed) ? parsed : []).filter((src) => typeof src === 'string' && src.trim()).slice(0, DEVICE_PHOTO_LIMIT);
    } catch (_) {
      return normalizedDevicePhotos(old);
    }
  };

  window.machineparkDeviceOverviewIndexFromForm = function(fd, old = {}) {
    const photos = window.machineparkDevicePhotosFromForm(fd, old);
    if (!photos.length) return 0;
    const raw = Number(fd.get('deviceOverviewPhotoIndex'));
    if (Number.isInteger(raw) && raw >= 0 && raw < photos.length) return raw;
    return overviewIndex(old, photos);
  };

  const baseDeviceFormForPhotos = deviceForm;
  deviceForm = function(d = {}) {
    const html = baseDeviceFormForPhotos(d);
    const section = `<div class="field full device-photo-field">
      <div class="device-photo-toolbar">
        <div><strong>Foto’s toestel</strong><small>Maximaal ${DEVICE_PHOTO_LIMIT} foto’s. Kies één foto als overzichtsfoto voor de toestellenlijst.</small></div>
        <label class="btn small device-photo-add" id="devicePhotoAddLabel">+ Foto’s toevoegen<input type="file" id="devicePhotoFiles" accept="image/*" multiple hidden></label>
      </div>
      <div id="devicePhotoGrid" class="device-photo-grid"></div>
      <input type="hidden" name="devicePhotosJson" id="devicePhotosJson" value="">
      <input type="hidden" name="deviceOverviewPhotoIndex" id="deviceOverviewPhotoIndex" value="0">
      <div id="devicePhotoStatus" class="muted" style="font-size:11px;margin-top:8px"></div>
    </div>`;
    return html.endsWith('</div>') ? html.slice(0, -6) + section + '</div>' : html + section;
  };

  function canManageDevicePhotos(existing) {
    if (window.machineparkAccessReady && typeof window.machineparkHasPermission === 'function') {
      return window.machineparkHasPermission(existing ? 'devices.edit' : 'devices.add');
    }
    return Boolean(window.machineparkCanEdit?.devices || !existing);
  }

  function previewPhoto(src) {
    return typeof window.machineparkThumbnailRef === 'function' ? window.machineparkThumbnailRef(src) : src;
  }

  function initDevicePhotoPicker(deviceId = '') {
    const device = state.devices.find((item) => item.id === deviceId) || {};
    const existing = Boolean(device.id);
    const canManage = canManageDevicePhotos(existing);
    let photos = normalizedDevicePhotos(device);
    let selected = overviewIndex(device, photos);
    const grid = document.getElementById('devicePhotoGrid');
    const input = document.getElementById('devicePhotoFiles');
    const hiddenPhotos = document.getElementById('devicePhotosJson');
    const hiddenOverview = document.getElementById('deviceOverviewPhotoIndex');
    const status = document.getElementById('devicePhotoStatus');
    const addLabel = document.getElementById('devicePhotoAddLabel');
    if (!grid || !hiddenPhotos || !hiddenOverview) return;

    function syncHidden() {
      if (!photos.length) selected = 0;
      else selected = Math.max(0, Math.min(selected, photos.length - 1));
      hiddenPhotos.value = JSON.stringify(photos);
      hiddenOverview.value = String(selected);
    }

    function render() {
      syncHidden();
      grid.innerHTML = photos.length ? photos.map((src, index) => `<div class="device-photo-card" data-device-photo-index="${index}">
        <div class="device-photo-image-wrap"><img src="${esc(previewPhoto(src))}" data-full-src="${esc(src)}" data-photo-lightbox loading="lazy" decoding="async" alt="Toestelfoto ${index + 1}"><span class="device-photo-number">Foto ${index + 1}</span></div>
        <div class="device-photo-card-foot">
          <label class="device-photo-overview"><input type="radio" name="devicePhotoOverviewChoice" value="${index}" ${index === selected ? 'checked' : ''} ${canManage ? '' : 'disabled'}><span>Op overzicht</span></label>
          ${canManage ? `<button type="button" class="device-photo-remove" data-device-photo-remove="${index}">Foto verwijderen</button>` : '<div class="device-photo-readonly">Alleen bekijken</div>'}
        </div>
      </div>`).join('') : '<div class="empty" style="grid-column:1/-1;padding:22px 12px">Nog geen foto’s toegevoegd.</div>';
      if (status) status.textContent = `${photos.length} van maximaal ${DEVICE_PHOTO_LIMIT} foto’s${canManage ? ' · selecteer één foto voor het overzicht' : ' · deze rol kan toestelgegevens niet volledig wijzigen'}`;
      if (input) input.disabled = !canManage || photos.length >= DEVICE_PHOTO_LIMIT;
      if (addLabel) {
        addLabel.style.display = canManage ? '' : 'none';
        addLabel.classList.toggle('disabled', photos.length >= DEVICE_PHOTO_LIMIT);
      }
    }

    grid.addEventListener('change', (event) => {
      const radio = event.target.closest('input[name="devicePhotoOverviewChoice"]');
      if (!radio || !canManage) return;
      selected = Number(radio.value) || 0;
      render();
    });

    grid.addEventListener('click', (event) => {
      const remove = event.target.closest('[data-device-photo-remove]');
      if (!remove || !canManage) return;
      const index = Number(remove.dataset.devicePhotoRemove);
      if (!Number.isInteger(index) || index < 0 || index >= photos.length) return;
      photos.splice(index, 1);
      if (!photos.length) selected = 0;
      else if (index === selected) selected = 0;
      else if (index < selected) selected -= 1;
      render();
    });

    if (input) input.addEventListener('change', async () => {
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

    render();
  }

  const baseOpenDeviceForPhotos = openDevice;
  openDevice = function(id) {
    baseOpenDeviceForPhotos(id);
    setTimeout(() => initDevicePhotoPicker(id || ''), 0);
  };
  window.openDevice = openDevice;

  renderDevices = function() {
    const f = $('#deviceStatusFilter').value;
    let list = state.devices.filter(d => (!f || d.status === f) && deviceMatchesQuery(d));
    const sort = state.deviceSort || { key: 'location', dir: 'asc' };
    list.sort((a, b) => compareDeviceValues(a, b, sort.key, sort.dir));
    const c = $('#deviceCards');
    updateDeviceSortHeaders();
    if (!list.length) {
      c.innerHTML = '<tr><td colspan="10"><div class="empty"><div class="big">☕</div>Nog geen toestellen gevonden.</div></td></tr>';
      return;
    }
    c.innerHTML = list.map(d => {
      const loc = deviceLocationAt(d) || 'Geen locatie';
      const nextLoc = nextLocationChange(d);
      const machine = [d.brand, d.model].filter(Boolean).join(' ') || '—';
      const photo = window.machineparkDeviceOverviewPhoto(d);
      const photoCell = photo ? `<img class="device-overview-photo" src="${esc(photo)}" alt="Overzichtsfoto ${esc(d.assetCode || d.model || 'toestel')}">` : '<div class="device-overview-photo-placeholder">▣</div>';
      return `<tr data-device-history="${d.id}"><td class="device-overview-photo-cell">${photoCell}</td><td><strong>${esc(d.assetCode || '—')}</strong></td><td>${esc(loc)}${nextLoc ? `<br><span class="muted" style="font-size:11px">Vanaf ${dateTimeFmt(nextLoc.effectiveFrom)} → ${esc(nextLoc.location)}</span>` : ''}</td><td>${esc(machine)}</td><td>${esc(d.serial || '—')}</td><td class="nowrap">${dateFmt(d.installDate)}</td><td>${statusBadge(d.status || 'Actief')}</td><td class="nowrap"><strong>${dateFmt(d.nextHalf)}</strong>${d.nextHalf ? `<br>${dueBadge(d.nextHalf)}` : ''}</td><td class="nowrap"><strong>${dateFmt(d.nextAnnual)}</strong>${d.nextAnnual ? `<br>${dueBadge(d.nextAnnual)}` : ''}</td><td><button class="btn small" data-device-details="${d.id}">Details</button></td></tr>`;
    }).join('');
  };
  window.renderDevices = renderDevices;

  const baseShowDeviceHistoryForPhotos = showDeviceHistory;
  showDeviceHistory = function(id) {
    baseShowDeviceHistoryForPhotos(id);
    setTimeout(() => {
      const device = state.devices.find((item) => item.id === id);
      const photos = normalizedDevicePhotos(device);
      if (!photos.length) return;
      const selected = overviewIndex(device, photos);
      const grid = document.querySelector('#modal .modal-body .form-grid');
      if (!grid) return;
      const block = document.createElement('div');
      block.className = 'field full';
      block.innerHTML = `<div class="device-detail-photo-section"><div class="device-detail-photo-head"><strong>Foto’s toestel</strong><span class="muted" style="font-size:11px">${photos.length} van ${DEVICE_PHOTO_LIMIT}</span></div><div class="device-detail-photo-gallery">${photos.map((src, index) => `<div class="device-detail-photo"><img src="${esc(src)}" data-full-src="${esc(src)}" data-photo-lightbox loading="lazy" decoding="async" alt="Toestelfoto ${index + 1}">${index === selected ? '<span class="badge success">Overzichtsfoto</span>' : ''}</div>`).join('')}</div></div>`;
      const first = grid.firstElementChild;
      if (first) first.after(block); else grid.appendChild(block);
    }, 0);
  };
  window.showDeviceHistory = showDeviceHistory;
})();
</script>
'''
    replace_once('</body>', script + '</body>', 'toestelfoto script')

    index_path.write_text(index, encoding="utf-8")

required = [
    MARKER,
    'const DEVICE_PHOTO_LIMIT = 5;',
    'function compressDevicePhoto(file)',
    'const max = 720;',
    'data-photo-lightbox',
    'maximaal ${DEVICE_PHOTO_LIMIT} foto’s',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: geconsolideerde toestelfoto-code ontbreekt ({needle})')

print('[Machinepark] maximaal 5 compacte toestelfoto’s met overzichtsfoto actief')
