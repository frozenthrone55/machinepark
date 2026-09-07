from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="device-photo-folder-import-v1"'

if MARKER not in index:
    style = f'''
<style {MARKER}>
.device-folder-import-actions{{display:flex;gap:9px;flex-wrap:wrap;margin-top:12px}}
.device-folder-import-status{{margin-top:10px;font-size:12px;line-height:1.5;color:var(--muted)}}
.device-folder-import-summary{{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}}
.device-folder-import-summary .badge{{font-size:11px}}
.device-folder-import-results{{max-height:360px;overflow:auto;border:1px solid var(--line);border-radius:11px;margin-top:10px;background:#fff}}
.device-folder-import-results table{{width:100%;border-collapse:collapse;min-width:660px}}
.device-folder-import-results th,.device-folder-import-results td{{padding:8px 9px;border-bottom:1px solid #edf1ef;font-size:11.5px;text-align:left;vertical-align:middle}}
.device-folder-import-results th{{position:sticky;top:0;background:#f8faf9;z-index:1;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.03em}}
.device-folder-import-results tr:last-child td{{border-bottom:0}}
.device-folder-import-results .ok{{color:var(--success);font-weight:700}}
.device-folder-import-results .skip{{color:var(--muted)}}
.device-folder-import-results .warn{{color:var(--warning);font-weight:700}}
.device-folder-import-progress{{height:8px;border-radius:999px;background:#edf1ef;overflow:hidden;margin-top:9px;display:none}}
.device-folder-import-progress > span{{display:block;height:100%;width:0;background:var(--brand2);transition:width .2s}}
@media(max-width:700px){{.device-folder-import-actions .btn{{width:100%}}}}
</style>
'''

    script = r'''
<script data-machinepark-build-fix="device-photo-folder-import-v1">
(() => {
  const MAX_DEVICE_IMPORT_PHOTOS = 5;
  const IMPORT_CARD_ID = 'devicePhotoFolderImportCard';
  let scanRows = [];

  function canImportDevicePhotoFolders() {
    if (window.machineparkAccessReady && typeof window.machineparkHasPermission === 'function') {
      return window.machineparkHasPermission('devices.import') && window.machineparkHasPermission('devices.edit');
    }
    return false;
  }

  function strictKey(value) {
    return String(value || '').trim().toLocaleUpperCase('nl-BE');
  }

  function looseKey(value) {
    return strictKey(value).normalize('NFKD').replace(/[^A-Z0-9]/g, '');
  }

  function imageFile(file) {
    if (!file || !file.name) return false;
    return String(file.type || '').startsWith('image/') || /\.(?:jpe?g|png|webp|gif|bmp|avif)$/i.test(file.name);
  }

  function devicePhotos(device) {
    return (Array.isArray(device?.devicePhotos) ? device.devicePhotos : []).filter(src => typeof src === 'string' && src.trim()).slice(0, MAX_DEVICE_IMPORT_PHOTOS);
  }

  function naturalFiles(files) {
    return [...files].filter(imageFile).sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'nl-BE', { numeric: true, sensitivity: 'base' }));
  }

  function buildDeviceLookup() {
    const strictAsset = new Map(), strictSerial = new Map(), looseAsset = new Map(), looseSerial = new Map();
    const add = (map, key, device) => {
      if (!key) return;
      const list = map.get(key) || [];
      if (!list.some(item => item.id === device.id)) list.push(device);
      map.set(key, list);
    };
    (Array.isArray(state?.devices) ? state.devices : []).forEach(device => {
      add(strictAsset, strictKey(device.assetCode), device);
      add(strictSerial, strictKey(device.serial), device);
      add(looseAsset, looseKey(device.assetCode), device);
      add(looseSerial, looseKey(device.serial), device);
    });
    return { strictAsset, strictSerial, looseAsset, looseSerial };
  }

  function uniqueMatch(map, key) {
    if (!key) return { device: null, ambiguous: false };
    const list = map.get(key) || [];
    return list.length === 1 ? { device: list[0], ambiguous: false } : { device: null, ambiguous: list.length > 1 };
  }

  function matchFolder(folderName, lookup) {
    const strict = strictKey(folderName), loose = looseKey(folderName);
    const attempts = [
      ['toestelnummer', lookup.strictAsset, strict],
      ['serienummer', lookup.strictSerial, strict],
      ['toestelnummer', lookup.looseAsset, loose],
      ['serienummer', lookup.looseSerial, loose],
    ];
    for (const [basis, map, key] of attempts) {
      const result = uniqueMatch(map, key);
      if (result.ambiguous) return { device: null, basis, ambiguous: true };
      if (result.device) return { device: result.device, basis, ambiguous: false };
    }
    return { device: null, basis: '', ambiguous: false };
  }

  async function filesBelowDirectory(handle, out = []) {
    for await (const [, entry] of handle.entries()) {
      if (entry.kind === 'file') {
        const file = await entry.getFile();
        if (imageFile(file)) out.push(file);
      } else if (entry.kind === 'directory') {
        await filesBelowDirectory(entry, out);
      }
    }
    return out;
  }

  async function scanDirectoryHandle(rootHandle) {
    const folders = [];
    for await (const [name, entry] of rootHandle.entries()) {
      if (entry.kind !== 'directory') continue;
      const files = naturalFiles(await filesBelowDirectory(entry, []));
      folders.push({ name, files });
    }
    return folders.sort((a, b) => a.name.localeCompare(b.name, 'nl-BE', { numeric: true, sensitivity: 'base' }));
  }

  function foldersFromWebkitFiles(fileList) {
    const groups = new Map();
    [...fileList].forEach(file => {
      if (!imageFile(file)) return;
      const rel = String(file.webkitRelativePath || file.name || '').split('/').filter(Boolean);
      if (!rel.length) return;
      const folder = rel.length >= 3 ? rel[1] : rel[0];
      if (!groups.has(folder)) groups.set(folder, []);
      groups.get(folder).push(file);
    });
    return [...groups.entries()].map(([name, files]) => ({ name, files: naturalFiles(files) }))
      .sort((a, b) => a.name.localeCompare(b.name, 'nl-BE', { numeric: true, sensitivity: 'base' }));
  }

  function analyzeFolders(folders) {
    const lookup = buildDeviceLookup();
    return folders.map((folder, index) => {
      const match = matchFolder(folder.name, lookup);
      const photos = match.device ? devicePhotos(match.device) : [];
      let status = 'unmatched';
      if (match.ambiguous) status = 'ambiguous';
      else if (match.device && photos.length) status = 'existing';
      else if (match.device && folder.files.length) status = 'ready';
      else if (match.device) status = 'empty-folder';
      return {
        index,
        folderName: folder.name,
        files: folder.files,
        deviceId: match.device?.id || '',
        assetCode: match.device?.assetCode || '',
        serial: match.device?.serial || '',
        basis: match.basis,
        status,
      };
    });
  }

  function escText(value) {
    return typeof esc === 'function' ? esc(value) : String(value || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  }

  function statusHtml(row) {
    if (row.status === 'ready') return `<span class="ok">Klaar · via ${escText(row.basis)}</span>`;
    if (row.status === 'existing') return '<span class="skip">Overgeslagen · toestel heeft al foto’s</span>';
    if (row.status === 'ambiguous') return '<span class="warn">Niet gekoppeld · meerdere mogelijke toestellen</span>';
    if (row.status === 'empty-folder') return '<span class="skip">Overgeslagen · geen ondersteunde foto’s</span>';
    return '<span class="skip">Geen toestel gevonden</span>';
  }

  function renderScan() {
    const host = document.getElementById('deviceFolderImportResult');
    const importBtn = document.getElementById('deviceFolderImportRun');
    if (!host || !importBtn) return;
    const ready = scanRows.filter(row => row.status === 'ready');
    const existing = scanRows.filter(row => row.status === 'existing').length;
    const unmatched = scanRows.filter(row => row.status === 'unmatched').length;
    const ambiguous = scanRows.filter(row => row.status === 'ambiguous').length;
    host.innerHTML = `<div class="device-folder-import-summary">
      <span class="badge success">${ready.length} klaar</span>
      <span class="badge gray">${existing} al voorzien</span>
      <span class="badge gray">${unmatched} niet gevonden</span>
      ${ambiguous ? `<span class="badge warn">${ambiguous} twijfelgeval${ambiguous === 1 ? '' : 'len'}</span>` : ''}
    </div>
    <div class="device-folder-import-results"><table><thead><tr><th></th><th>Map</th><th>Toestel</th><th>Serienummer</th><th>Foto’s</th><th>Resultaat</th></tr></thead><tbody>${scanRows.map(row => `<tr>
      <td>${row.status === 'ready' ? `<input type="checkbox" data-device-folder-import="${row.index}" checked aria-label="Importeer foto’s uit ${escText(row.folderName)}">` : ''}</td>
      <td><strong>${escText(row.folderName)}</strong></td>
      <td>${escText(row.assetCode || '—')}</td>
      <td>${escText(row.serial || '—')}</td>
      <td>${row.files.length}${row.files.length > MAX_DEVICE_IMPORT_PHOTOS ? ` · eerste ${MAX_DEVICE_IMPORT_PHOTOS}` : ''}</td>
      <td>${statusHtml(row)}</td>
    </tr>`).join('')}</tbody></table></div>`;
    importBtn.disabled = ready.length === 0;
  }

  function setStatus(text) {
    const node = document.getElementById('deviceFolderImportStatus');
    if (node) node.textContent = text || '';
  }

  function setProgress(done, total) {
    const box = document.getElementById('deviceFolderImportProgress');
    const bar = box?.querySelector('span');
    if (!box || !bar) return;
    box.style.display = total ? '' : 'none';
    bar.style.width = total ? `${Math.max(0, Math.min(100, Math.round(done / total * 100)))}%` : '0%';
  }

  async function chooseAndScan() {
    if (!canImportDevicePhotoFolders()) {
      alert('Je hebt zowel Toestellen importeren als Toestellen bewerken nodig voor deze foto-import.');
      return;
    }
    setStatus('Map wordt gecontroleerd…');
    scanRows = [];
    renderScan();
    try {
      let folders = [];
      if (typeof window.showDirectoryPicker === 'function') {
        const handle = await window.showDirectoryPicker({ mode: 'read' });
        folders = await scanDirectoryHandle(handle);
      } else {
        const input = document.getElementById('deviceFolderImportFallback');
        if (!input) throw new Error('Mapselectie wordt niet ondersteund door deze browser.');
        const files = await new Promise((resolve) => {
          input.value = '';
          input.onchange = () => resolve([...(input.files || [])]);
          input.click();
        });
        folders = foldersFromWebkitFiles(files);
      }
      scanRows = analyzeFolders(folders);
      renderScan();
      setStatus(`${folders.length} toestelmap${folders.length === 1 ? '' : 'pen'} gecontroleerd. Er is nog niets gewijzigd.`);
    } catch (error) {
      if (error?.name === 'AbortError') {
        setStatus('Mapselectie geannuleerd.');
        return;
      }
      console.error('Toestelfoto-mapscan', error);
      setStatus(`Map kon niet worden gecontroleerd: ${error?.message || error}`);
    }
  }

  function compressImportPhoto(file) {
    if (!file || !file.size) return Promise.resolve('');
    return new Promise((resolve, reject) => {
      const img = new Image();
      const reader = new FileReader();
      reader.onerror = () => reject(reader.error || new Error('Foto kon niet worden gelezen.'));
      reader.onload = event => { img.src = String(event.target?.result || ''); };
      img.onerror = () => reject(new Error(`Foto ${file.name} kon niet worden geopend.`));
      img.onload = () => {
        try {
          const max = 720;
          const scale = Math.min(1, max / Math.max(img.width || 1, img.height || 1));
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
        } catch (error) { reject(error); }
      };
      reader.readAsDataURL(file);
    });
  }

  function writeDeviceDirect(device) {
    return new Promise((resolve, reject) => {
      const tr = db.transaction('devices', 'readwrite');
      const request = tr.objectStore('devices').put(device);
      request.onerror = () => reject(request.error);
      tr.oncomplete = () => resolve(device);
      tr.onerror = () => reject(tr.error);
      tr.onabort = () => reject(tr.error || new Error('Lokale toestelupdate afgebroken.'));
    });
  }

  async function syncBulkImport() {
    if (typeof centralSync === 'undefined' || !centralSync.enabled || typeof centralPush !== 'function') return;
    clearTimeout(centralSync.pushTimer);
    centralSync.pushTimer = null;
    centralSync.pending = true;
    await centralPush();
  }

  async function runImport() {
    if (!canImportDevicePhotoFolders()) {
      alert('Je hebt onvoldoende rechten voor deze foto-import.');
      return;
    }
    const selectedIndexes = [...document.querySelectorAll('[data-device-folder-import]:checked')]
      .map(el => Number(el.dataset.deviceFolderImport)).filter(Number.isInteger);
    const selected = selectedIndexes.map(index => scanRows.find(row => row.index === index)).filter(Boolean);
    if (!selected.length) {
      alert('Selecteer minstens één toestelmap om te importeren.');
      return;
    }
    if (!confirm(`Foto’s importeren voor ${selected.length} toestel${selected.length === 1 ? '' : 'len'}? Bestaande toestelfoto’s worden niet vervangen.`)) return;

    const scanBtn = document.getElementById('deviceFolderImportScan');
    const importBtn = document.getElementById('deviceFolderImportRun');
    if (scanBtn) scanBtn.disabled = true;
    if (importBtn) importBtn.disabled = true;
    setProgress(0, selected.length);
    setStatus('Nieuwste centrale gegevens controleren…');

    let imported = 0, skipped = 0, failed = 0;
    const errors = [];
    try {
      if (typeof centralPull === 'function' && typeof centralSync !== 'undefined' && centralSync.enabled) {
        try { await centralPull({ apply: true, quiet: true }); } catch (_) {}
      }

      for (let i = 0; i < selected.length; i += 1) {
        const row = selected[i];
        const device = (Array.isArray(state?.devices) ? state.devices : []).find(item => item.id === row.deviceId);
        setStatus(`${i + 1}/${selected.length} · ${row.folderName} verwerken…`);
        if (!device || devicePhotos(device).length) {
          skipped += 1;
          setProgress(i + 1, selected.length);
          continue;
        }
        try {
          const files = naturalFiles(row.files).slice(0, MAX_DEVICE_IMPORT_PHOTOS);
          const compressed = [];
          for (const file of files) {
            const photo = await compressImportPhoto(file);
            if (photo) compressed.push(photo);
          }
          if (!compressed.length) throw new Error('Geen bruikbare foto’s gevonden.');
          if (typeof window.machineparkPersistDevicePhotoList !== 'function') throw new Error('Toestelfoto-opslag is niet beschikbaar.');
          const refs = await window.machineparkPersistDevicePhotoList(device.id, compressed, { force: true });
          if (!Array.isArray(refs) || !refs.length) throw new Error('Foto-opslag gaf geen afbeeldingsverwijzingen terug.');
          const updated = { ...device, devicePhotos: refs.slice(0, MAX_DEVICE_IMPORT_PHOTOS), deviceOverviewPhotoIndex: 0, updatedAt: new Date().toISOString() };
          Object.assign(device, updated);
          await writeDeviceDirect(updated);
          imported += 1;
        } catch (error) {
          failed += 1;
          errors.push(`${row.folderName}: ${error?.message || error}`);
          console.error('Toestelfoto-import', row.folderName, error);
        }
        setProgress(i + 1, selected.length);
      }

      if (imported) {
        setStatus('Foto’s zijn opgeslagen. Centrale gegevens synchroniseren…');
        await syncBulkImport();
        if (typeof refresh === 'function') await refresh();
      }
      const pieces = [`${imported} toestel${imported === 1 ? '' : 'len'} voorzien van foto’s`];
      if (skipped) pieces.push(`${skipped} overgeslagen`);
      if (failed) pieces.push(`${failed} mislukt`);
      setStatus(pieces.join(' · ') + (errors.length ? ` · ${errors.slice(0, 3).join(' | ')}` : ''));
      scanRows = scanRows.map(row => {
        const device = (Array.isArray(state?.devices) ? state.devices : []).find(item => item.id === row.deviceId);
        return row.status === 'ready' && devicePhotos(device).length ? { ...row, status: 'existing' } : row;
      });
      renderScan();
      if (imported && typeof toast === 'function') toast(`${imported} toestel${imported === 1 ? '' : 'len'} voorzien van foto’s`);
    } catch (error) {
      console.error('Bulk toestel-fotoimport', error);
      setStatus(`Import niet volledig afgerond: ${error?.message || error}`);
    } finally {
      if (scanBtn) scanBtn.disabled = false;
      if (importBtn) importBtn.disabled = scanRows.filter(row => row.status === 'ready').length === 0;
    }
  }

  function ensureImportCard() {
    const settings = document.querySelector('#view-settings .settings-grid') || document.getElementById('view-settings');
    if (!settings || document.getElementById(IMPORT_CARD_ID)) return;
    const card = document.createElement('div');
    card.id = IMPORT_CARD_ID;
    card.className = 'settings-card';
    card.style.display = 'none';
    card.innerHTML = `<h4>Toestelfoto’s uit lokale mappen</h4>
      <p>Voor toestellen zonder foto’s. Kies de hoofdmap <strong>toestelnummers</strong>; submapnamen worden gekoppeld aan toestelnummer of serienummer. Bestaande foto’s worden nooit overschreven.</p>
      <div class="device-folder-import-actions">
        <button type="button" class="btn" id="deviceFolderImportScan">📁 Map kiezen en controleren</button>
        <button type="button" class="btn primary" id="deviceFolderImportRun" disabled>Foto’s importeren</button>
      </div>
      <input type="file" id="deviceFolderImportFallback" webkitdirectory directory multiple accept="image/*" hidden>
      <div class="device-folder-import-progress" id="deviceFolderImportProgress"><span></span></div>
      <div class="device-folder-import-status" id="deviceFolderImportStatus">Er is nog niets geïmporteerd. De browser vraagt zelf toestemming voor de lokale map.</div>
      <div id="deviceFolderImportResult"></div>`;
    settings.appendChild(card);
    document.getElementById('deviceFolderImportScan')?.addEventListener('click', chooseAndScan);
    document.getElementById('deviceFolderImportRun')?.addEventListener('click', runImport);
  }

  function updateImportAccess() {
    ensureImportCard();
    const card = document.getElementById(IMPORT_CARD_ID);
    if (card) card.style.display = canImportDevicePhotoFolders() ? '' : 'none';
  }

  updateImportAccess();
  let checks = 0;
  const accessTimer = setInterval(() => {
    updateImportAccess();
    checks += 1;
    if (window.machineparkAccessReady || checks >= 20) clearInterval(accessTimer);
  }, 500);
})();
</script>
'''

    if '</head>' not in index or '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-afsluiters ontbreken voor toestelmap-fotoimport')
    index = index.replace('</head>', style + '</head>', 1)
    body_pos = index.rfind('</body>')
    index = index[:body_pos] + script + index[body_pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'devicePhotoFolderImportCard',
    'showDirectoryPicker',
    'webkitdirectory',
    "window.machineparkHasPermission('devices.import')",
    "window.machineparkHasPermission('devices.edit')",
    'matchFolder(folder.name, lookup)',
    "['toestelnummer', lookup.strictAsset, strict]",
    "['serienummer', lookup.strictSerial, strict]",
    'Bestaande foto’s worden nooit overschreven.',
    'window.machineparkPersistDevicePhotoList',
    'await syncBulkImport()',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: toestelmap-fotoimport ontbreekt ({needle})')

print('[Machinepark] veilige lokale toestelmap-fotoimport actief')
