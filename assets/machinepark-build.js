'use strict';

/* fault-excel-import-v1 */
try {
(() => {
  const endpoint = '/machinepark/synology/api/fault-library.php';

  function excelFaultNorm(value) {
    return String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  }

  function excelFaultKey(fault) {
    return [fault?.code, fault?.category, fault?.name, fault?.brand, fault?.model].map(excelFaultNorm).join('|');
  }

  function excelFaultLines(value) {
    return String(value ?? '').split(/[;\r\n]+/).map(x => x.trim()).filter(Boolean);
  }

  function excelFaultActive(value) {
    const x = excelFaultNorm(value);
    if (!x) return true;
    return !['nee', 'no', 'false', '0', 'inactief', 'inactive', 'uit'].includes(x);
  }

  function excelFaultComparable(fault) {
    return JSON.stringify({
      code: String(fault?.code || '').trim(),
      name: String(fault?.name || '').trim(),
      category: String(fault?.category || '').trim(),
      brand: String(fault?.brand || '').trim(),
      model: String(fault?.brand ? (fault?.model || '') : '').trim(),
      description: String(fault?.description || '').trim(),
      message: String(fault?.message || '').trim(),
      solution1: String(fault?.solution1 || '').trim(),
      solution2: String(fault?.solution2 || '').trim(),
      symptoms: Array.isArray(fault?.symptoms) ? fault.symptoms.map(x => String(x).trim()).filter(Boolean) : [],
      causes: Array.isArray(fault?.causes) ? fault.causes.map(x => String(x).trim()).filter(Boolean) : [],
      solutions: Array.isArray(fault?.solutions) ? fault.solutions.map(x => String(x).trim()).filter(Boolean) : [],
      notes: String(fault?.notes || '').trim(),
      active: fault?.active !== false,
    });
  }

  async function faultExcelRequest(options = {}) {
    const headers = await centralHeaders(options.body !== undefined);
    const res = await fetch(endpoint, { cache: 'no-store', ...options, headers: { ...headers, ...(options.headers || {}) } });
    const text = await res.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch (_) {}
    if (!res.ok) throw new Error(data.error || text || `Storingsimport mislukt (${res.status})`);
    return data;
  }

  function faultExcelColumn(headers, aliases) {
    return findHeaderIndex(headers, aliases);
  }

  function faultExcelPlan(matrix, currentFaults) {
    let headerRow = -1, headers = [];
    for (let h = 0; h < Math.min(matrix.length, 30); h++) {
      const candidate = (matrix[h] || []).map(cleanCell);
      const name = faultExcelColumn(candidate, ['Storing', 'Storing / korte omschrijving', 'Storingsomschrijving', 'Probleem', 'Algemene omschrijving']);
      if (name >= 0) { headerRow = h; headers = candidate; break; }
    }
    if (headerRow < 0) throw new Error('Kolom “Storing” niet gevonden. Download het Machinepark-sjabloon als voorbeeld.');

    const idx = {
      code: faultExcelColumn(headers, ['Storingscode', 'Storingsnummer', 'Foutcode', 'Code', 'Error code']),
      name: faultExcelColumn(headers, ['Storing', 'Storing / korte omschrijving', 'Storingsomschrijving', 'Probleem', 'Algemene omschrijving']),
      category: faultExcelColumn(headers, ['Categorie', 'Category']),
      brand: faultExcelColumn(headers, ['Merk', 'Brand', 'Merk / model', 'Merk/model']),
      model: faultExcelColumn(headers, ['Model', 'Toestelmodel']),
      description: faultExcelColumn(headers, ['Omschrijving', 'Beschrijving', 'Description', 'gedetailleerde omschrijving']),
      message: faultExcelColumn(headers, ['Melding', 'Message']),
      solution1: faultExcelColumn(headers, ['Oplossing 1', 'Solution 1']),
      solution2: faultExcelColumn(headers, ['Oplossing 2', 'Solution 2']),
      symptoms: faultExcelColumn(headers, ['Symptomen', 'Symptoms']),
      causes: faultExcelColumn(headers, ['Mogelijke oorzaken', 'Oorzaken', 'Causes']),
      solutions: faultExcelColumn(headers, ['Oplossingen', 'Oplossing', 'Controle / oplossingen', 'Solution']),
      notes: faultExcelColumn(headers, ['Opmerkingen', 'Interne opmerkingen', 'Notities', 'Notes']),
      active: faultExcelColumn(headers, ['Actief', 'Active']),
    };

    const get = (row, key) => idx[key] >= 0 ? cleanCell(row[idx[key]]) : '';
    const existing = new Map();
    (currentFaults || []).forEach(fault => { const key = excelFaultKey(fault); if (!existing.has(key)) existing.set(key, fault); });
    const seen = new Map();
    const records = [];
    const errors = [];

    for (let ri = headerRow + 1; ri < matrix.length; ri++) {
      const row = matrix[ri] || [];
      if (!row.some(value => cleanCell(value))) continue;
      const name = get(row, 'name');
      if (!name) { errors.push({ row: ri + 1, reason: 'Storing ontbreekt' }); continue; }
      const brand = get(row, 'brand');
      const fault = {
        code: get(row, 'code'),
        name,
        category: get(row, 'category'),
        brand,
        model: brand ? get(row, 'model') : '',
        description: get(row, 'description'),
        message: get(row, 'message'),
        solution1: get(row, 'solution1'),
        solution2: get(row, 'solution2'),
        symptoms: excelFaultLines(get(row, 'symptoms')),
        causes: excelFaultLines(get(row, 'causes')),
        solutions: excelFaultLines(get(row, 'solutions')),
        notes: get(row, 'notes'),
        active: idx.active >= 0 ? excelFaultActive(get(row, 'active')) : true,
      };
      const key = excelFaultKey(fault);
      if (!excelFaultNorm(fault.name)) { errors.push({ row: ri + 1, reason: 'Ongeldige storing' }); continue; }
      if (seen.has(key)) { errors.push({ row: ri + 1, reason: `Dubbele storing in Excel (ook regel ${seen.get(key)})` }); continue; }
      seen.set(key, ri + 1);
      const old = existing.get(key) || null;
      if (!old) records.push({ action: 'add', row: ri + 1, fault });
      else if (excelFaultComparable(old) === excelFaultComparable(fault)) records.push({ action: 'same', row: ri + 1, old, fault: { ...fault, id: old.id } });
      else records.push({ action: 'update', row: ri + 1, old, fault: { ...fault, id: old.id } });
    }
    return { records, errors };
  }

  function faultImportPreview(plan, fileName, etag) {
    const adds = plan.records.filter(r => r.action === 'add');
    const updates = plan.records.filter(r => r.action === 'update');
    const same = plan.records.filter(r => r.action === 'same');
    const changes = [...updates, ...adds];
    const preview = changes.slice(0, 40);
    const rows = preview.map(r => `<tr><td>${r.row}</td><td><span class="badge ${r.action === 'add' ? 'blue' : 'warn'}">${r.action === 'add' ? 'Nieuw' : 'Bijwerken'}</span></td><td><strong>${esc([r.fault.code, r.fault.name].filter(Boolean).join(' — '))}</strong></td><td>${esc(r.fault.brand || 'Alle merken')}${r.fault.model ? ' · ' + esc(r.fault.model) : ''}</td></tr>`).join('');
    const errorRows = plan.errors.slice(0, 12).map(e => `<div class="alert"><strong>Excel-regel ${e.row}</strong>${esc(e.reason)}</div>`).join('');
    const body = `<div class="kpis" style="grid-template-columns:repeat(4,minmax(0,1fr));margin-bottom:14px"><div class="kpi" style="box-shadow:none"><div class="label">Nieuw</div><div class="value">${adds.length}</div></div><div class="kpi" style="box-shadow:none"><div class="label">Bijwerken</div><div class="value">${updates.length}</div></div><div class="kpi" style="box-shadow:none"><div class="label">Ongewijzigd</div><div class="value">${same.length}</div></div><div class="kpi" style="box-shadow:none"><div class="label">Fouten</div><div class="value">${plan.errors.length}</div></div></div><div class="alert"><strong>Niet-destructieve import</strong>Storingen die niet in dit bestand staan worden niet verwijderd. Een bestaande storing wordt herkend op combinatie van storingscode + storing + merk + model.</div><div class="muted" style="margin:12px 0">Bestand: ${esc(fileName)} · ${changes.length} wijziging(en) klaar om te verwerken.</div><div class="table-wrap"><table class="table" style="min-width:720px"><thead><tr><th>Regel</th><th>Actie</th><th>Storing</th><th>Toepassing</th></tr></thead><tbody>${rows || '<tr><td colspan="4"><div class="empty">Geen wijzigingen nodig.</div></td></tr>'}${changes.length > preview.length ? `<tr><td colspan="4" class="muted">… en nog ${changes.length - preview.length} wijziging(en)</td></tr>` : ''}</tbody></table></div>${plan.errors.length ? `<div style="margin-top:14px"><div class="section-title">Regels met fouten</div>${errorRows}${plan.errors.length > 12 ? `<div class="muted">… en nog ${plan.errors.length - 12} fout(en)</div>` : ''}</div>` : ''}`;
    $('#modal').innerHTML = `<div class="modal-head"><h3>Storingen uit Excel importeren</h3><button class="close" type="button">×</button></div><div class="modal-body">${body}</div><div class="modal-foot"><button class="btn" type="button" id="cancelFaultExcelImport">Annuleren</button><button class="btn primary" type="button" id="confirmFaultExcelImport" ${changes.length ? '' : 'disabled'}>${changes.length} wijziging${changes.length === 1 ? '' : 'en'} importeren</button></div>`;
    enhanceSortableTables($('#modal'));
    $('#modalBackdrop').classList.add('show');
    $('.close').onclick = closeModal;
    $('#cancelFaultExcelImport').onclick = closeModal;
    const confirmBtn = $('#confirmFaultExcelImport');
    if (confirmBtn) confirmBtn.onclick = async () => {
      confirmBtn.disabled = true;
      confirmBtn.textContent = 'Importeren…';
      try {
        const result = await faultExcelRequest({ method: 'POST', body: JSON.stringify({ action: 'import-faults', etag, faults: changes.map(r => r.fault) }) });
        closeModal();
        if (typeof window.machineparkLoadFaultLibrary === 'function') await window.machineparkLoadFaultLibrary(true).catch(() => {});
        if (typeof window.machineparkRenderFaultLibrary === 'function') window.machineparkRenderFaultLibrary();
        toast(`Storingsimport klaar · ${result.added || 0} nieuw · ${result.updated || 0} bijgewerkt`);
      } catch (error) {
        console.error('Storingen Excel-import', error);
        alert('Storingsimport mislukt: ' + (error?.message || 'onbekende fout'));
        confirmBtn.disabled = false;
        confirmBtn.textContent = `${changes.length} wijziging${changes.length === 1 ? '' : 'en'} importeren`;
      }
    };
  }

  async function importFaultExcel(file) {
    try {
      if (!file) return;
      const [matrix, current] = await Promise.all([readStockMatrix(file), faultExcelRequest()]);
      const plan = faultExcelPlan(matrix, current.faults || []);
      if (!plan.records.length && !plan.errors.length) throw new Error('Geen storingsregels gevonden in het bestand.');
      faultImportPreview(plan, file.name || 'storingen.xlsx', current.etag || null);
    } catch (error) {
      console.error('Storingen Excel inlezen', error);
      alert('Excel-import mislukt: ' + (error?.message || 'onbekende fout'));
    }
  }

  function faultTemplateXmlEsc(value) {
    return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');
  }

  function faultTemplateCell(ref, value) {
    return `<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${faultTemplateXmlEsc(value)}</t></is></c>`;
  }

  function downloadFaultExcelTemplate() {
    try {
      const headers = ['Storingscode','Storing','Categorie','Merk','Model','Omschrijving','Symptomen','Mogelijke oorzaken','Oplossingen','Opmerkingen','Actief'];
      const letters = 'ABCDEFGHIJK'.split('');
      const cells = headers.map((h, i) => faultTemplateCell(`${letters[i]}1`, h)).join('');
      const sheet = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:K1"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="1" width="16" customWidth="1"/><col min="2" max="2" width="30" customWidth="1"/><col min="3" max="5" width="20" customWidth="1"/><col min="6" max="10" width="34" customWidth="1"/><col min="11" max="11" width="12" customWidth="1"/></cols><sheetData><row r="1">${cells}</row></sheetData><autoFilter ref="A1:K1"/></worksheet>`;
      const enc = new TextEncoder();
      const files = [
        { name: '[Content_Types].xml', bytes: enc.encode('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>') },
        { name: '_rels/.rels', bytes: enc.encode('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>') },
        { name: 'xl/workbook.xml', bytes: enc.encode('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Storingen" sheetId="1" r:id="rId1"/></sheets></workbook>') },
        { name: 'xl/_rels/workbook.xml.rels', bytes: enc.encode('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>') },
        { name: 'xl/worksheets/sheet1.xml', bytes: enc.encode(sheet) },
      ];
      const blob = makeStoreZip(files);
      downloadBlob(`Machinepark_Storingen_Sjabloon_${todayISO()}.xlsx`, new Blob([blob], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
      toast('Excel-sjabloon voor storingen gedownload');
    } catch (error) {
      console.error('Storingen Excel-sjabloon', error);
      alert('Excel-sjabloon maken mislukt: ' + (error?.message || 'onbekende fout'));
    }
  }

  const fileInput = document.getElementById('faultExcelFile');
  const importBtn = document.getElementById('importFaultExcelBtn');
  const templateBtn = document.getElementById('downloadFaultExcelTemplateBtn');
  if (importBtn && fileInput) importBtn.addEventListener('click', () => { fileInput.value = ''; fileInput.click(); });
  if (fileInput) fileInput.addEventListener('change', () => importFaultExcel(fileInput.files?.[0]));
  if (templateBtn) templateBtn.addEventListener('click', downloadFaultExcelTemplate);
})();
} catch (error) {
  console.error('[Machinepark feature fault-excel-import-v1]', error);
}

/* service-report-photos-v2 */
try {
(() => {
  const REPORT_PHOTO_LIMIT = 5;
  const SERVICE_PHOTO_ENDPOINT = '/machinepark/synology/api/service-photos.php?';

  function insertBeforeLastDiv(html, extra) {
    const pos = html.lastIndexOf('</div>');
    return pos < 0 ? html + extra : html.slice(0, pos) + extra + html.slice(pos);
  }

  function insertBeforeFinalDivPair(html, extra) {
    const marker = '</div></div>';
    const pos = html.lastIndexOf(marker);
    return pos < 0 ? insertBeforeLastDiv(html, extra) : html.slice(0, pos) + extra + html.slice(pos);
  }

  function isServicePhoto(value) {
    const src = String(value || '').trim();
    return src.startsWith('data:image/') || src.includes(SERVICE_PHOTO_ENDPOINT);
  }

  function photoArray(value) {
    return Array.isArray(value) ? value.filter(x => typeof x === 'string' && isServicePhoto(x)).slice(0, REPORT_PHOTO_LIMIT) : [];
  }

  function photoPreviewSrc(src) {
    return typeof window.machineparkThumbnailRef === 'function' ? window.machineparkThumbnailRef(src) : src;
  }

  function servicePhotoEditorHtml(existing = [], inputClass = '') {
    const photos = photoArray(existing);
    const current = photos.length
      ? `<div class="service-photo-grid">${photos.map((src, i) => `<div class="service-photo-item"><img src="${esc(photoPreviewSrc(src))}" data-full-src="${esc(src)}" data-photo-lightbox loading="lazy" decoding="async" alt="Verslagfoto ${i + 1}"><label><input type="checkbox" class="service-photo-remove" value="${i}"> Verwijderen</label></div>`).join('')}</div>`
      : '<div class="muted" style="font-size:11px;margin:4px 0 8px">Nog geen foto’s toegevoegd.</div>';
    return `<div class="field full service-photo-editor">
      <label>Foto’s bij verslag</label>
      ${current}
      <input class="service-photo-files ${inputClass}" type="file" accept="image/*" multiple>
      <div class="muted" style="font-size:11px;margin-top:4px">Maximaal ${REPORT_PHOTO_LIMIT} foto’s per verslag. Foto’s worden automatisch verkleind en apart opgeslagen.</div>
      <div class="service-photo-selected muted" style="font-size:11px;margin-top:4px"></div>
    </div>`;
  }

  function servicePhotoDetailsHtml(photos) {
    const list = photoArray(photos);
    if (!list.length) return '<span class="muted">Geen foto’s bij dit verslag.</span>';
    return `<div class="service-photo-details">${list.map((src, i) => `<img src="${esc(photoPreviewSrc(src))}" data-full-src="${esc(src)}" data-photo-lightbox loading="lazy" decoding="async" alt="Verslagfoto ${i + 1}">`).join('')}</div>`;
  }

  async function collectServicePhotos(editor, existing = []) {
    if (!editor) return photoArray(existing);
    const remove = new Set([...editor.querySelectorAll('.service-photo-remove:checked')].map(x => Number(x.value)));
    const kept = photoArray(existing).filter((_, i) => !remove.has(i));
    const input = editor.querySelector('.service-photo-files');
    const files = [...(input?.files || [])].filter(file => file && file.size);
    if (kept.length + files.length > REPORT_PHOTO_LIMIT) {
      throw new Error(`Maximaal ${REPORT_PHOTO_LIMIT} foto’s per onderhouds- of depannageverslag.`);
    }
    const added = [];
    for (const file of files) added.push(await compressImage(file));
    return [...kept, ...added].filter(Boolean).slice(0, REPORT_PHOTO_LIMIT);
  }

  async function persistServicePhotos(storeName, item, photos) {
    if (typeof window.machineparkPersistServicePhotos !== 'function') return photos;
    return window.machineparkPersistServicePhotos(storeName, item.id, photos);
  }

  function editorForRecord(storeName, deviceId) {
    const attr = storeName === 'maintenance' ? 'maintenanceDevice' : 'breakdownDevice';
    return [...document.querySelectorAll('.maintenance-machine-card')]
      .find(card => card.dataset?.[attr] === deviceId)
      ?.querySelector('.service-photo-editor') || null;
  }

  const originalMaintenanceForm = maintenanceForm;
  maintenanceForm = function(m = {}) {
    return insertBeforeLastDiv(originalMaintenanceForm(m), servicePhotoEditorHtml(m.photos || []));
  };

  const originalBreakdownForm = breakdownForm;
  breakdownForm = function(b = {}) {
    return insertBeforeLastDiv(originalBreakdownForm(b), servicePhotoEditorHtml(b.photos || []));
  };

  const originalMaintenanceMachineCardHtml = maintenanceMachineCardHtml;
  maintenanceMachineCardHtml = function(d) {
    return insertBeforeFinalDivPair(
      originalMaintenanceMachineCardHtml(d),
      servicePhotoEditorHtml([], 'maintenance-machine-photos')
    );
  };

  const originalBreakdownMachineCardHtml = breakdownMachineCardHtml;
  breakdownMachineCardHtml = function(d) {
    return insertBeforeFinalDivPair(
      originalBreakdownMachineCardHtml(d),
      servicePhotoEditorHtml([], 'breakdown-machine-photos')
    );
  };

  const originalSetMaintenanceMachineEnabled = setMaintenanceMachineEnabled;
  setMaintenanceMachineEnabled = function(card, enabled) {
    originalSetMaintenanceMachineEnabled(card, enabled);
    card?.querySelectorAll('.maintenance-machine-photos').forEach(el => el.disabled = !enabled);
  };

  const originalSetBreakdownMachineEnabled = setBreakdownMachineEnabled;
  setBreakdownMachineEnabled = function(card, enabled) {
    originalSetBreakdownMachineEnabled(card, enabled);
    card?.querySelectorAll('.breakdown-machine-photos').forEach(el => el.disabled = !enabled);
  };

  const originalPut = put;
  put = async function(storeName, obj) {
    if ((storeName === 'maintenance' || storeName === 'breakdowns') && obj) {
      const editor = document.querySelector('#modalForm .modal-body > .form-grid > .service-photo-editor');
      if (editor && !editor.closest('.maintenance-machine-card')) {
        const photos = await collectServicePhotos(editor, obj.photos || []);
        obj = { ...obj, photos: await persistServicePhotos(storeName, obj, photos) };
      }
    }
    return originalPut(storeName, obj);
  };

  const originalPutMany = putMany;
  putMany = async function(storeName, items) {
    if ((storeName === 'maintenance' || storeName === 'breakdowns') && Array.isArray(items) && items.length) {
      const enriched = [];
      for (const item of items) {
        const editor = editorForRecord(storeName, item.deviceId);
        if (!editor) { enriched.push(item); continue; }
        const photos = await collectServicePhotos(editor, item.photos || []);
        enriched.push({ ...item, photos: await persistServicePhotos(storeName, item, photos) });
      }
      items = enriched;
    }
    return originalPutMany(storeName, items);
  };

  const originalShowMaintenanceDetails = showMaintenanceDetails;
  showMaintenanceDetails = function(id) {
    originalShowMaintenanceDetails(id);
    const m = state.maintenance.find(x => x.id === id);
    const grid = document.querySelector('#modal .modal-body .form-grid');
    if (m && grid) {
      grid.insertAdjacentHTML('beforeend', `<div class="field full"><label>Foto’s bij verslag</label>${servicePhotoDetailsHtml(m.photos)}</div>`);
    }
  };

  document.addEventListener('change', event => {
    const input = event.target.closest?.('.service-photo-files');
    if (!input) return;
    const editor = input.closest('.service-photo-editor');
    const info = editor?.querySelector('.service-photo-selected');
    if (info) {
      const count = input.files?.length || 0;
      info.textContent = count ? `${count} nieuwe foto${count === 1 ? '' : '’s'} geselecteerd` : '';
    }
  });
})();
} catch (error) {
  console.error('[Machinepark feature service-report-photos-v2]', error);
}

/* print-every-page-v2 */
try {
(() => {
  const labels = {
    dashboard: 'Dashboard',
    devices: 'Toestellen',
    maintenance: 'Onderhoud',
    breakdowns: 'Depannages',
    parts: 'Onderdelen',
    settings: 'Beheer'
  };

  function viewName(view) {
    const key = String(view?.id || '').replace(/^view-/, '');
    return labels[key] || document.getElementById('pageTitle')?.textContent?.trim() || 'Machinepark';
  }

  function addPrintButton(view) {
    if (!view || view.querySelector(':scope > .page-print-row')) return;
    const row = document.createElement('div');
    row.className = 'page-print-row';
    row.innerHTML = `<div class="page-print-heading">Machinepark · ${viewName(view)}</div><button type="button" class="btn page-print-btn" aria-label="Deze pagina afdrukken">🖨 Afdrukken</button>`;
    row.querySelector('.page-print-btn').addEventListener('click', () => printMachineparkView(view));
    view.insertAdjacentElement('afterbegin', row);
  }

  function activeView() {
    return document.querySelector('.view.active') || document.querySelector('.view');
  }

  function enlargePartsPrintPhotos(view) {
    if (view?.id !== 'view-parts') return () => {};
    const photos = [...view.querySelectorAll('img.thumb')];
    const original = photos.map(img => ({
      img,
      width: img.style.width,
      height: img.style.height,
      src: img.getAttribute('src'),
      loading: img.getAttribute('loading'),
    }));
    photos.forEach(img => {
      if (img.dataset.fullSrc) img.setAttribute('src', img.dataset.fullSrc);
      img.setAttribute('loading', 'eager');
      const rect = img.getBoundingClientRect();
      if (rect.width > 0) img.style.width = `${Math.round(rect.width * 1.5)}px`;
      if (rect.height > 0) img.style.height = `${Math.round(rect.height * 1.5)}px`;
      img.classList.add('parts-print-photo');
    });
    return () => original.forEach(({img,width,height,src,loading}) => {
      img.style.width = width;
      img.style.height = height;
      if (src === null) img.removeAttribute('src'); else img.setAttribute('src', src);
      if (loading === null) img.removeAttribute('loading'); else img.setAttribute('loading', loading);
      img.classList.remove('parts-print-photo');
    });
  }

  function printMachineparkView(view = activeView()) {
    if (!view) return;
    const name = viewName(view);
    const heading = view.querySelector(':scope > .page-print-row .page-print-heading');
    if (heading) heading.textContent = `Machinepark · ${name}`;
    const restorePhotos = enlargePartsPrintPhotos(view);
    const oldTitle = document.title;
    document.title = `Machinepark - ${name}`;
    let restored = false;
    const restore = () => {
      if (restored) return;
      restored = true;
      restorePhotos();
      document.title = oldTitle;
      window.removeEventListener('afterprint', restore);
    };
    window.addEventListener('afterprint', restore);
    window.print();
    setTimeout(restore, 1800);
  }

  window.printMachineparkView = printMachineparkView;
  document.querySelectorAll('.view').forEach(addPrintButton);
})();
} catch (error) {
  console.error('[Machinepark feature print-every-page-v2]', error);
}

/* print-service-details-v2 */
try {
(() => {
  function servicePrintEsc(value) {
    return esc(String(value ?? ''));
  }

  function serviceRecordDevice(record) {
    return deviceName(record.deviceId, recordMoment(record));
  }

  function serviceRecordDate(record) {
    if (!record?.date) return '—';
    const date = new Date(`${record.date}T00:00:00`);
    return Number.isNaN(date.getTime()) ? String(record.date) : date.toLocaleDateString('nl-BE');
  }

  function serviceRecordParts(record, multiline = false) {
    const parts = Array.isArray(record?.usedParts) ? record.usedParts.filter(Boolean) : [];
    if (!parts.length) return '—';
    if (!multiline) return usedPartsText(parts) || '—';
    const lines = parts
      .map(part => usedPartsText([part]))
      .map(value => String(value || '').trim())
      .filter(Boolean);
    return lines.length ? lines.join(String.fromCharCode(10)) : (usedPartsText(parts) || '—');
  }

  function serviceRecordPhotos(record) {
    return Array.isArray(record?.photos)
      ? record.photos.filter(x => typeof x === 'string' && x.startsWith('data:image/'))
      : [];
  }

  function servicePrintField(label, value, full = false) {
    return `<div class="service-print-field${full ? ' full' : ''}"><div class="service-print-label">${servicePrintEsc(label)}</div><div class="service-print-value">${servicePrintEsc(value || '—')}</div></div>`;
  }

  function servicePrintPhotos(record) {
    const photos = serviceRecordPhotos(record);
    if (!photos.length) return '';
    return `<div class="service-print-section"><h2>Foto’s bij verslag</h2><div class="service-print-photo-grid">${photos.map((src, index) => `<div class="service-print-photo"><img src="${src}" alt="Verslagfoto ${index + 1}"></div>`).join('')}</div></div>`;
  }

  function servicePrintWorkOrder(record) {
    const workOrder = record?.workOrder;
    if (!workOrder || !Array.isArray(workOrder.fields) || !workOrder.fields.length) return '';
    const fields = workOrder.fields.map((field) => {
      const raw = field?.type === 'checkbox' ? (field.value ? 'Ja' : 'Nee') : field?.value;
      return servicePrintField(field?.label || 'Veld', raw === '' || raw === null || raw === undefined ? '—' : raw, field?.type === 'textarea');
    }).join('');
    return `<div class="service-print-section workorder-print-section"><h2>Werkbon · ${servicePrintEsc(workOrder.templateName || 'Werkbon')} <span style="font-weight:400;color:#666">v${servicePrintEsc(workOrder.templateVersion || 1)}</span></h2><div class="workorder-print-grid">${fields}</div></div>`;
  }

  function unifiedWorkPartRows(record) {
    const rows = [];
    (record?.usedParts || []).forEach(usage => {
      const qty = Number(usage?.qty || 0);
      if (!usage?.partId || qty <= 0) return;
      const part = (state.parts || []).find(item => item.id === usage.partId);
      rows.push({
        code:String(part?.artNr || usage.partId || '—').trim() || '—',
        description:String(part?.description || '').trim(),
        qty,
        oneOff:false
      });
    });
    (record?.oneOffParts || []).forEach(part => {
      const supplier = String(part?.supplier || '').trim();
      const supplierCode = String(part?.supplierCode || '').trim();
      const description = String(part?.description || '').trim();
      if (!(supplier || supplierCode || description)) return;
      rows.push({
        code:supplierCode || supplier || 'Eenmalig',
        description:[supplierCode && supplier ? supplier : '', description].filter(Boolean).join(' · '),
        qty:Math.max(0.001, normalizePartQuantity(part?.qty,1)),
        oneOff:true
      });
    });
    return rows;
  }

  function unifiedWorkLocation(record) {
    const device = (state.devices || []).find(item => item.id === record?.deviceId);
    try {
      if (device && typeof deviceLocationAt === 'function') return deviceLocationAt(device, recordMoment(record)) || device.location || '—';
    } catch (_) {}
    return device?.location || record?.serviceVisitLocation || '—';
  }

  function unifiedWorkSummary(kind, record) {
    try {
      if (kind === 'maintenance' && typeof maintenanceWorkSummary === 'function') return maintenanceWorkSummary(record);
      if (typeof breakdownWorkSummary === 'function') return breakdownWorkSummary(record);
    } catch (_) {}
    const sessions = Array.isArray(record?.workSessions) ? record.workSessions : [];
    const minutes = sessions.reduce((sum, row) => sum + Math.max(0, Math.round(Number(row?.minutes) || 0)), 0) || Math.max(0, Math.round(Number(record?.hours || 0) * 60));
    const count = Math.max(1, Math.round(Number(record?.serviceReportDeviceCount || record?.serviceVisitDeviceCount || record?.batchSize) || 1));
    return `${minutes} min / ${count} toestel${count === 1 ? '' : 'len'}`;
  }

  function unifiedWorkPartsHtml(record) {
    const rows = unifiedWorkPartRows(record);
    return `<div class="work-report-parts-box"><div class="work-report-parts-title">Onderdelen voor deze werkzaamheid</div>${rows.length ? `<table class="work-report-parts-table"><thead><tr><th class="work-part-code">Onderdeel</th><th class="work-part-description">Omschrijving</th><th class="work-part-qty">Aantal</th></tr></thead><tbody>${rows.map(row => `<tr><td class="work-part-code">${servicePrintEsc(row.code || '—')}</td><td class="work-part-description">${servicePrintEsc(row.description || '—')}${row.oneOff ? '<small>Eenmalig / leverancier</small>' : ''}</td><td class="work-part-qty"><strong>${servicePrintEsc(formatPartQuantity(row.qty))}</strong></td></tr>`).join('')}</tbody></table>` : '<div class="work-report-parts-empty">Geen onderdelen gebruikt.</div>'}</div>`;
  }

  function servicePrintHtml(kind, record) {
    const maintenance = kind === 'maintenance';
    const other = !maintenance && record?.serviceKind === 'other';
    const kindLabel = maintenance ? 'Onderhoud' : (other ? (record.workTypeName || 'Andere werken') : 'Depannage');
    const title = maintenance ? 'Onderhoudsverslag' : (other ? `${kindLabel} · verslag` : 'Depannageverslag');
    const device = serviceRecordDevice(record);
    const date = serviceRecordDate(record);
    const summary = unifiedWorkSummary(kind, record);
    const summaryLabel = record?.serviceVisitId ? 'Servicetijd volledig verslag / toestellen' : 'Datum / werkminuten';
    const summaryValue = record?.serviceVisitId ? summary : `${date} · ${summary}`;
    const details = maintenance
      ? [
          `Type onderhoud: ${record.type || '—'}`,
          `Uitgevoerde werkzaamheden / notitie: ${record.notes || '—'}`
        ]
      : other
        ? [
            `Prioriteit: ${record.priority || '—'} · Status: ${record.status || '—'}`,
            `Werkzaamheid / omschrijving: ${record.issue || '—'}`,
            `Extra info / diagnose: ${record.diagnosis || '—'}`,
            `Oplossing / uitgevoerde werken: ${record.solution || '—'}`
          ]
        : [
            `Prioriteit: ${record.priority || '—'} · Status: ${record.status || '—'}`,
            `Probleem / melding: ${record.issue || '—'}`,
            `Diagnose: ${record.diagnosis || '—'}`,
            `Oplossing / uitgevoerde werken: ${record.solution || '—'}`
          ];
    const photos = serviceRecordPhotos(record);
    return `<section class="work-report-print-page">
      <div class="work-report-print-head"><div><small>WERKVERSLAG</small><strong>${servicePrintEsc(title)}</strong></div><div class="work-report-print-kind">${servicePrintEsc(kindLabel)}</div></div>
      <div class="work-report-print-title"><h1>${servicePrintEsc(device)}</h1></div>
      <div class="work-report-print-meta">
        <div><small>Locatie</small><strong>${servicePrintEsc(unifiedWorkLocation(record))}</strong></div>
        <div><small>${servicePrintEsc(summaryLabel)}</small><strong>${servicePrintEsc(summaryValue)}</strong></div>
        <div><small>Technieker</small><strong>${servicePrintEsc(record.technician || '—')}</strong></div>
      </div>
      <div class="work-report-print-card">
        <div class="work-report-print-lines">${details.map(line => `<div>${servicePrintEsc(line)}</div>`).join('')}</div>
        ${unifiedWorkPartsHtml(record)}
      </div>
      ${photos.length ? `<div class="work-report-print-photos"><div class="work-report-section-title">Foto’s bij deze werkzaamheid</div><div class="service-print-photo-grid">${photos.map((src, index) => `<div class="service-print-photo"><img src="${src}" alt="Verslagfoto ${index + 1}"></div>`).join('')}</div></div>` : ''}
    </section>`;
  }

  function ensureServicePrintSheet() {
    let sheet = document.getElementById('servicePrintSheet');
    if (!sheet) {
      sheet = document.createElement('div');
      sheet.id = 'servicePrintSheet';
      sheet.className = 'service-print-sheet';
      document.body.appendChild(sheet);
    }
    return sheet;
  }

  function printServiceRecord(kind, id) {
    const list = kind === 'maintenance' ? state.maintenance : state.breakdowns;
    const record = list.find(x => x.id === id);
    if (!record) { toast('Verslag niet gevonden'); return; }
    const sheet = ensureServicePrintSheet();
    sheet.innerHTML = servicePrintHtml(kind, record);
    const oldTitle = document.title;
    const label = kind === 'maintenance' ? 'Onderhoud' : (record?.serviceKind === 'other' ? (record.workTypeName || 'Andere werken') : 'Depannage');
    document.title = `Machinepark - ${label} - ${serviceRecordDevice(record)}`;
    document.body.classList.add('service-record-printing');
    const restore = () => {
      document.body.classList.remove('service-record-printing');
      document.title = oldTitle;
      window.removeEventListener('afterprint', restore);
    };
    window.addEventListener('afterprint', restore);
    window.print();
    setTimeout(() => {
      if (document.body.classList.contains('service-record-printing')) restore();
    }, 1800);
  }

  function addServicePrintButton(kind, id) {
    const foot = document.querySelector('#modal .modal-foot');
    if (!foot || foot.querySelector('.service-detail-print-btn')) return;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn service-detail-print-btn';
    btn.dataset.servicePrintKind = kind;
    btn.dataset.servicePrintId = id;
    btn.textContent = '🖨 Afdrukken';
    btn.onclick = () => printServiceRecord(kind, id);
    foot.insertBefore(btn, foot.querySelector('.btn.primary') || null);
  }

  const previousShowMaintenanceDetails = showMaintenanceDetails;
  showMaintenanceDetails = function(id) {
    const result = previousShowMaintenanceDetails(id);
    setTimeout(() => addServicePrintButton('maintenance', id), 0);
    return result;
  };

  const previousOpenBreakdown = openBreakdown;
  openBreakdown = function(id) {
    const result = previousOpenBreakdown(id);
    if (id) setTimeout(() => addServicePrintButton('breakdowns', id), 0);
    return result;
  };

  window.printMachineparkServiceRecord = printServiceRecord;
  window.machineparkServicePrintHtml = servicePrintHtml;
})();
} catch (error) {
  console.error('[Machinepark feature print-service-details-v2]', error);
}

/* purge-service-photos-on-delete-v1 */
try {
(() => {
  const originalDeleteServiceRecordForPhotoCleanup = deleteServiceRecord;

  async function purgeDeletedServicePhotos(storeName, entityId) {
    const headers = await centralHeaders(true);
    const response = await fetch('/machinepark/synology/api/purge-service-audit-photos.php', {
      method: 'POST',
      headers,
      body: JSON.stringify({ storeName, entityId }),
      cache: 'no-store',
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || 'Opschonen van verslagfoto’s mislukt.');
    return body;
  }

  deleteServiceRecord = async function(storeName, id) {
    const collection = storeName === 'maintenance' ? state.maintenance : storeName === 'breakdowns' ? state.breakdowns : null;
    const existedBefore = Boolean(collection?.some(item => item.id === id));
    const result = await originalDeleteServiceRecordForPhotoCleanup(storeName, id);
    if (!existedBefore) return result;

    const currentCollection = storeName === 'maintenance' ? state.maintenance : state.breakdowns;
    const deleted = !currentCollection.some(item => item.id === id);
    if (!deleted) return result;

    try {
      if (typeof centralSync !== 'undefined' && centralSync.pushTimer) {
        clearTimeout(centralSync.pushTimer);
        centralSync.pushTimer = null;
      }
      if (typeof centralPush === 'function') await centralPush();
      await purgeDeletedServicePhotos(storeName, id);
    } catch (error) {
      console.warn('Verwijderde verslagfoto’s konden niet volledig uit het logboek worden opgeschoond:', error);
    }
    return result;
  };

  window.purgeDeletedServicePhotos = purgeDeletedServicePhotos;
})();
} catch (error) {
  console.error('[Machinepark feature purge-service-photos-on-delete-v1]', error);
}

/* parts-xlsx-export-v1 */
try {
(() => {
  const enc = new TextEncoder();

  function xlsxXmlEsc(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
  }

  function xlsxTextCell(ref, value, style = 0) {
    return `<c r="${ref}" s="${style}" t="inlineStr"><is><t xml:space="preserve">${xlsxXmlEsc(value)}</t></is></c>`;
  }

  function xlsxNumberCell(ref, value, style = 0) {
    const n = Number(value);
    return Number.isFinite(n)
      ? `<c r="${ref}" s="${style}"><v>${n}</v></c>`
      : xlsxTextCell(ref, '', style);
  }

  async function normalizePartImageForExcel(dataUrl) {
    if (dataUrl && !String(dataUrl).startsWith('data:')) {
      try {
        const response = await fetch(String(dataUrl), { cache: 'no-store' });
        if (response.ok) {
          const blob = await response.blob();
          dataUrl = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result || ''));
            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(blob);
          });
        }
      } catch (_) {}
    }
    const image = dataUrlExportImage(dataUrl);
    if (!image) return null;
    if (image.mime === 'image/jpeg' || image.mime === 'image/jpg') return { bytes: image.bytes, ext: 'jpg', mime: 'image/jpeg' };
    if (image.mime === 'image/png') return { bytes: image.bytes, ext: 'png', mime: 'image/png' };

    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        try {
          const canvas = document.createElement('canvas');
          const max = 900;
          const scale = Math.min(1, max / Math.max(img.width || 1, img.height || 1));
          canvas.width = Math.max(1, Math.round((img.width || 1) * scale));
          canvas.height = Math.max(1, Math.round((img.height || 1) * scale));
          const ctx = canvas.getContext('2d');
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          const converted = dataUrlExportImage(canvas.toDataURL('image/jpeg', 0.84));
          resolve(converted ? { bytes: converted.bytes, ext: 'jpg', mime: 'image/jpeg' } : null);
        } catch {
          resolve(null);
        }
      };
      img.onerror = () => resolve(null);
      img.src = dataUrl;
    });
  }

  function xlsxContentTypes(images) {
    const extensions = new Set(images.map(x => x.ext));
    const imageDefaults = [...extensions].map(ext => {
      const mime = ext === 'png' ? 'image/png' : 'image/jpeg';
      return `<Default Extension="${ext}" ContentType="${mime}"/>`;
    }).join('');
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
${imageDefaults}
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
<Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>
</Types>`;
  }

  function xlsxStyles() {
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/><family val="2"/></font>
    <font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/><family val="2"/></font>
  </fonts>
  <fills count="3">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF173F35"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border><left style="thin"><color rgb="FFDDE5E1"/></left><right style="thin"><color rgb="FFDDE5E1"/></right><top style="thin"><color rgb="FFDDE5E1"/></top><bottom style="thin"><color rgb="FFDDE5E1"/></bottom><diagonal/></border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="4">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"><alignment vertical="center"/></xf>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFill="1" applyFont="1"><alignment vertical="center" wrapText="1"/></xf>
    <xf numFmtId="4" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1"><alignment vertical="center"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"><alignment vertical="center" wrapText="1"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>`;
  }

  function xlsxSheet(parts) {
    const headers = ['Foto','Art nr','Omschrijving','Merk toestel','Prijs excl. BTW','Voorraad locatie 1','Code leverancier','Magazijnlocatie','Minimumvoorraad'];
    const letters = ['A','B','C','D','E','F','G','H','I'];
    const headerCells = headers.map((h, i) => xlsxTextCell(`${letters[i]}1`, h, 1)).join('');
    const rows = parts.map((p, index) => {
      const r = index + 2;
      const cells = [
        xlsxTextCell(`A${r}`, p.photo ? 'Foto' : '', 0),
        xlsxTextCell(`B${r}`, p.artNr || '', 0),
        xlsxTextCell(`C${r}`, p.description || '', 3),
        xlsxTextCell(`D${r}`, p.deviceBrand || '', 3),
        p.price === '' || p.price === null || p.price === undefined ? xlsxTextCell(`E${r}`, '', 2) : xlsxNumberCell(`E${r}`, p.price, 2),
        xlsxNumberCell(`F${r}`, Number(p.stock || 0), 0),
        xlsxTextCell(`G${r}`, p.supplierCode || '', 0),
        xlsxTextCell(`H${r}`, p.warehouse || '', 0),
        xlsxNumberCell(`I${r}`, Number(p.minStock || 0), 0),
      ].join('');
      return `<row r="${r}" ht="60" customHeight="1">${cells}</row>`;
    }).join('');
    const lastRow = Math.max(1, parts.length + 1);
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <dimension ref="A1:I${lastRow}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetFormatPr defaultRowHeight="15"/>
  <cols>
    <col min="1" max="1" width="13" customWidth="1"/>
    <col min="2" max="2" width="16" customWidth="1"/>
    <col min="3" max="3" width="38" customWidth="1"/>
    <col min="4" max="4" width="26" customWidth="1"/>
    <col min="5" max="5" width="16" customWidth="1"/>
    <col min="6" max="6" width="19" customWidth="1"/>
    <col min="7" max="7" width="20" customWidth="1"/>
    <col min="8" max="8" width="22" customWidth="1"/>
    <col min="9" max="9" width="18" customWidth="1"/>
  </cols>
  <sheetData><row r="1" ht="24" customHeight="1">${headerCells}</row>${rows}</sheetData>
  <autoFilter ref="A1:I${lastRow}"/>
  <drawing r:id="rId1"/>
</worksheet>`;
  }

  function xlsxDrawing(images) {
    const anchors = images.map((image, index) => {
      const id = index + 1;
      const row = image.partIndex + 1;
      return `<xdr:oneCellAnchor>
  <xdr:from><xdr:col>0</xdr:col><xdr:colOff>47625</xdr:colOff><xdr:row>${row}</xdr:row><xdr:rowOff>47625</xdr:rowOff></xdr:from>
  <xdr:ext cx="666750" cy="666750"/>
  <xdr:pic>
    <xdr:nvPicPr><xdr:cNvPr id="${id}" name="Onderdeel foto ${id}"/><xdr:cNvPicPr/></xdr:nvPicPr>
    <xdr:blipFill><a:blip r:embed="rId${id}"/><a:stretch><a:fillRect/></a:stretch></xdr:blipFill>
    <xdr:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="666750" cy="666750"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr>
  </xdr:pic>
  <xdr:clientData/>
</xdr:oneCellAnchor>`;
    }).join('');
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">${anchors}</xdr:wsDr>`;
  }

  function xlsxDrawingRels(images) {
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${images.map((image, index) => `<Relationship Id="rId${index + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image${index + 1}.${image.ext}"/>`).join('')}</Relationships>`;
  }

  async function exportPartsExcel() {
    const button = document.getElementById('exportPartsCsv');
    const oldText = button?.textContent || 'Excel exporteren';
    if (button) { button.disabled = true; button.textContent = 'Excel maken…'; }
    try {
      const parts = [...state.parts].sort((a, b) => String(a.artNr || '').localeCompare(String(b.artNr || ''), 'nl', { numeric: true, sensitivity: 'base' }));
      const images = [];
      for (let partIndex = 0; partIndex < parts.length; partIndex++) {
        const normalized = await normalizePartImageForExcel(parts[partIndex]?.photo);
        if (normalized) images.push({ ...normalized, partIndex });
      }

      const files = [
        { name: '[Content_Types].xml', bytes: enc.encode(xlsxContentTypes(images)) },
        { name: '_rels/.rels', bytes: enc.encode(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`) },
        { name: 'xl/workbook.xml', bytes: enc.encode(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><bookViews><workbookView/></bookViews><sheets><sheet name="Onderdelen" sheetId="1" r:id="rId1"/></sheets></workbook>`) },
        { name: 'xl/_rels/workbook.xml.rels', bytes: enc.encode(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`) },
        { name: 'xl/styles.xml', bytes: enc.encode(xlsxStyles()) },
        { name: 'xl/worksheets/sheet1.xml', bytes: enc.encode(xlsxSheet(parts)) },
        { name: 'xl/worksheets/_rels/sheet1.xml.rels', bytes: enc.encode(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing1.xml"/></Relationships>`) },
        { name: 'xl/drawings/drawing1.xml', bytes: enc.encode(xlsxDrawing(images)) },
        { name: 'xl/drawings/_rels/drawing1.xml.rels', bytes: enc.encode(xlsxDrawingRels(images)) },
      ];
      images.forEach((image, index) => files.push({ name: `xl/media/image${index + 1}.${image.ext}`, bytes: image.bytes }));

      const blob = makeStoreZip(files);
      const xlsxBlob = new Blob([blob], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      if (!(await saveMachineparkExcelFile(`Machinepark_Onderdelen_${todayISO()}.xlsx`, xlsxBlob))) return;
      toast(`Excel-export gemaakt · ${parts.length} onderdelen · ${images.length} foto${images.length === 1 ? '' : '’s'} ingebed`);
    } catch (error) {
      console.error('Onderdelen Excel-export', error);
      alert('Excel-export mislukt: ' + (error?.message || 'onbekende fout'));
    } finally {
      if (button) { button.disabled = false; button.textContent = 'Excel exporteren'; }
    }
  }

  window.exportPartsExcel = exportPartsExcel;
  try { exportPartsCsv = exportPartsExcel; } catch (_) {}

  function activateExcelExportButton() {
    const button = document.getElementById('exportPartsCsv');
    if (!button) return;
    button.textContent = 'Excel exporteren';
    button.title = 'Exporteer alle onderdelen en foto’s in één Excel-bestand';
    button.onclick = exportPartsExcel;
  }

  activateExcelExportButton();
  document.addEventListener('DOMContentLoaded', activateExcelExportButton, { once: true });
  setTimeout(activateExcelExportButton, 0);
  setTimeout(activateExcelExportButton, 1500);
})();
} catch (error) {
  console.error('[Machinepark feature parts-xlsx-export-v1]', error);
}

/* excel-local-save-v1 */
try {
async function saveMachineparkExcelFile(fileName, blob) {
  if (typeof window.showSaveFilePicker === 'function') {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: fileName,
        types: [{
          description: 'Excel-werkmap',
          accept: {
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
          }
        }]
      });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return true;
    } catch (error) {
      if (error?.name === 'AbortError') return false;
      console.warn('Rechtstreeks Excel opslaan niet beschikbaar, normale download wordt gebruikt.', error);
    }
  }

  downloadBlob(fileName, blob);
  return true;
}
} catch (error) {
  console.error('[Machinepark feature excel-local-save-v1]', error);
}

/* service-work-sessions-v1 */
try {
(() => {
  const escAttr = value => String(value ?? '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const sessionsFor = record => {
    const saved = Array.isArray(record?.workSessions) ? record.workSessions.filter(row=>row && (row.date || Number(row.minutes)>0)) : [];
    if(saved.length) return saved.map(row=>({date:String(row.date||''),minutes:Math.max(0,Math.round(Number(row.minutes)||0))}));
    const legacy=Math.max(0,Math.round(Number(record?.hours||0)*60));
    return [{date:String(record?.date||''),minutes:legacy}];
  };
  const rowHtml = row => `<div class="service-work-session-row"><input type="date" name="workSessionDate" required value="${escAttr(row?.date||'')}"><input type="number" name="workSessionMinutes" min="1" step="1" required value="${Number(row?.minutes)>0?Math.round(Number(row.minutes)):''}" placeholder="minuten"><button type="button" class="remove-line" data-remove-work-session>×</button></div>`;
  const totalOf = rows => rows.reduce((sum,row)=>sum+Math.max(0,Math.round(Number(row.minutes)||0)),0);
  const refresh = root => {if(!root)return;const rows=[...root.querySelectorAll('.service-work-session-row')];const total=rows.reduce((sum,row)=>sum+Math.max(0,Number(row.querySelector('[name="workSessionMinutes"]')?.value||0)),0);const hidden=root.querySelector('[name="hours"]');if(hidden)hidden.value=String(total);const out=root.querySelector('[data-service-work-total]');if(out)out.textContent=`Totaal: ${Math.round(total)} min`;};
  window.machineparkServiceWorkSessionsEditor = (record,kind) => {
    const rows=sessionsFor(record),total=totalOf(rows);
    if(record?.serviceVisitId && kind!=='servicevisit'){
      const reportRows=[...(state.maintenance||[]),...(state.breakdowns||[])].filter(item=>(item?.serviceReportId||item?.serviceVisitId)===(record?.serviceReportId||record?.serviceVisitId)),unique=new Set(reportRows.map(item=>item?.deviceId).filter(Boolean)).size;
      const reportRowsTime=Array.isArray(record?.serviceReportWorkSessions)&&record.serviceReportWorkSessions.length?record.serviceReportWorkSessions:rows;
      const reportTotal=Math.max(0,Math.round(Number(record?.serviceReportTotalMinutes)||totalOf(reportRowsTime)));
      const count=Math.max(1,unique||Math.round(Number(record?.serviceReportDeviceCount||record?.serviceVisitDeviceCount||record?.batchSize)||1));
      const hidden=reportRowsTime.map(row=>`<input type="hidden" name="workSessionDate" value="${escAttr(row?.date||'')}"><input type="hidden" name="workSessionMinutes" value="${Math.max(0,Math.round(Number(row?.minutes)||0))}">`).join('');
      return `<div class="field full service-work-sessions service-shared-time" data-service-work-sessions><label>Servicetijd volledig serviceverslag / toestellen</label><input name="hours" type="hidden" value="${reportTotal}">${hidden}<strong data-service-work-total>Totaal: ${reportTotal} min · ${count} toestel${count===1?'':'len'}</strong><div class="muted" style="font-size:11px;margin-top:5px">Deze tijd komt uit het volledige gekoppelde serviceverslag en geldt voor alle locaties en toestellen daarin. Een eventuele afzonderlijke toesteltijd kun je in de omschrijving van de werken vermelden.</div></div>`;
    }
    return `<div class="field full service-work-sessions" data-service-work-sessions><label>Werkdagen en tijd</label><input name="hours" type="hidden" value="${total}"><div class="service-work-session-list" data-service-work-session-list>${rows.map(rowHtml).join('')}</div><div class="service-work-session-actions"><button type="button" class="btn small" data-add-work-session>+ Dag toevoegen</button><strong data-service-work-total>Totaal: ${total} min</strong></div><div class="muted" style="font-size:11px">De totale tijd geldt voor de volledige ${kind==='breakdown'?'depannage':kind==='servicevisit'?'servicebezoek':'onderhoud'}${record?.batchId?'groep':''}.</div></div>`;
  };
  window.machineparkCollectWorkSessions = fd => {const dates=fd.getAll('workSessionDate'),minutes=fd.getAll('workSessionMinutes');return dates.map((date,i)=>({date:String(date||''),minutes:Math.max(0,Math.round(Number(minutes[i])||0))})).filter(row=>row.date&&row.minutes>0);};
  window.machineparkServiceWorkSessionsText = record => sessionsFor(record).filter(row=>row.minutes>0).map(row=>`${row.date||'—'} · ${row.minutes} min`).join(' | ')||'—';
  document.addEventListener('click',event=>{const add=event.target.closest('[data-add-work-session]');if(add){const root=add.closest('[data-service-work-sessions]'),list=root?.querySelector('[data-service-work-session-list]');if(list){list.insertAdjacentHTML('beforeend',rowHtml({}));list.lastElementChild?.querySelector('input')?.focus();refresh(root);}return;}const remove=event.target.closest('[data-remove-work-session]');if(remove){const root=remove.closest('[data-service-work-sessions]'),rows=root?.querySelectorAll('.service-work-session-row');if(rows&&rows.length>1)remove.closest('.service-work-session-row')?.remove();else remove.closest('.service-work-session-row')?.querySelectorAll('input').forEach(input=>input.value='');refresh(root);}});
  document.addEventListener('input',event=>{const root=event.target.closest?.('[data-service-work-sessions]');if(root)refresh(root);});
})();
} catch (error) {
  console.error('[Machinepark feature service-work-sessions-v1]', error);
}

/* breakdown-details-v2 */
try {
(() => {
  const detailEsc = value => esc(String(value ?? ''));

  function detailDevice(record) {
    try { return deviceName(record.deviceId, recordMoment(record)) || '—'; }
    catch (_) {
      const device = state.devices.find(item => item.id === record?.deviceId);
      return [device?.assetCode, device?.brand, device?.model].filter(Boolean).join(' · ') || '—';
    }
  }

  function detailDate(record) {
    const raw = String(record?.date || '');
    if (!raw) return '—';
    try { return dateFmt(raw) || raw; } catch (_) { return raw; }
  }

  function detailWorkSessions(record) {
    if (typeof window.machineparkServiceWorkSessionsText === 'function') {
      const value = window.machineparkServiceWorkSessionsText(record);
      if (value && value !== '—') return value;
    }
    const minutes = Math.max(0, Math.round(Number(record?.hours || 0) * 60));
    return minutes ? `${minutes} min` : '—';
  }

  function detailField(label, value, full = false) {
    return `<div class="breakdown-detail-field${full ? ' full' : ''}"><label>${detailEsc(label)}</label><div class="value">${detailEsc(value || '—')}</div></div>`;
  }

  function detailParts(record) {
    const parts = Array.isArray(record?.usedParts) ? record.usedParts : [];
    if (!parts.length) return detailField('Gebruikte onderdelen', '—', true);
    const rows = parts.map(part => {
      let text = '—';
      try { text = usedPartsText([part]) || '—'; } catch (_) {}
      return `<div class="breakdown-detail-part">${detailEsc(text)}</div>`;
    }).join('');
    return `<div class="breakdown-detail-field full"><label>Gebruikte onderdelen</label><div class="breakdown-detail-parts">${rows}</div></div>`;
  }

  function detailPhotos(record) {
    const photos = Array.isArray(record?.photos) ? record.photos.filter(src => typeof src === 'string' && src.trim()) : [];
    if (!photos.length) return detailField('Foto’s bij verslag', 'Geen foto’s bij dit verslag.', true);
    const html = photos.map((src, index) => {
      const preview = typeof window.machineparkThumbnailRef === 'function' ? window.machineparkThumbnailRef(src) : src;
      return `<img src="${detailEsc(preview)}" data-full-src="${detailEsc(src)}" data-photo-lightbox loading="lazy" decoding="async" alt="Verslagfoto ${index + 1}">`;
    }).join('');
    return `<div class="breakdown-detail-field full"><label>Foto’s bij verslag</label><div class="breakdown-detail-photos">${html}</div></div>`;
  }

  function canEditBreakdown() {
    if (typeof window.machineparkHasPermission === 'function' && window.machineparkAccessReady) return window.machineparkHasPermission('breakdowns.edit');
    if (window.machineparkCanEdit && typeof window.machineparkCanEdit.breakdowns !== 'undefined') return !!window.machineparkCanEdit.breakdowns;
    return false;
  }

  function canDeleteBreakdown() {
    if (typeof window.machineparkHasPermission === 'function' && window.machineparkAccessReady) return window.machineparkHasPermission('breakdowns.delete');
    if (window.machineparkCanEdit && typeof window.machineparkCanEdit.breakdowns !== 'undefined') return !!window.machineparkCanEdit.breakdowns;
    return false;
  }

  function canPrintBreakdown() {
    if (typeof window.machineparkHasPermission === 'function') return window.machineparkHasPermission('print');
    return true;
  }

  window.machineparkShowBreakdownDetails = function(id) {
    const record = state.breakdowns.find(item => item.id === id);
    if (!record) { toast('Depannage niet gevonden'); return; }

    const body = `<div class="breakdown-detail-summary">
      ${detailField('Datum', detailDate(record))}
      ${detailField('Toestel', detailDevice(record))}
      ${detailField('Prioriteit', record.priority || '—')}
      ${detailField('Status', record.status || '—')}
      ${detailField('Technieker', record.technician || '—')}
      ${detailField('Werkdagen en tijd', detailWorkSessions(record))}
      ${detailField('Probleem / melding', record.issue || '—', true)}
      ${detailField('Diagnose', record.diagnosis || '—', true)}
      ${detailField('Oplossing / uitgevoerde werken', record.solution || '—', true)}
      ${detailParts(record)}
      ${detailPhotos(record)}
    </div>`;

    showModal('Depannagedetails', body, 'Sluiten', async () => closeModal());
    setTimeout(() => {
      const foot = document.querySelector('#modal .modal-foot');
      if (!foot) return;
      const primary = foot.querySelector('.btn.primary');

      if (canPrintBreakdown() && typeof window.printMachineparkServiceRecord === 'function') {
        const print = document.createElement('button');
        print.type = 'button';
        print.className = 'btn service-detail-print-btn';
        print.dataset.servicePrintKind = 'breakdowns';
        print.dataset.servicePrintId = id;
        print.textContent = '🖨 Afdrukken';
        print.onclick = () => window.printMachineparkServiceRecord('breakdowns', id);
        foot.insertBefore(print, primary || null);
      }

      if (canDeleteBreakdown()) {
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'btn danger';
        remove.id = 'deleteBreakdownFromDetails';
        remove.textContent = 'Verwijderen';
        remove.onclick = () => deleteServiceRecord('breakdowns', id);
        foot.insertBefore(remove, primary || null);
      }

      if (canEditBreakdown()) {
        const edit = document.createElement('button');
        edit.type = 'button';
        edit.className = 'btn primary';
        edit.id = 'editBreakdownFromDetails';
        edit.textContent = 'Bewerken';
        edit.onclick = () => { closeModal(); openBreakdown(id); };
        if (primary) primary.classList.remove('primary');
        foot.appendChild(edit);
      }
    }, 0);
  };
})();
} catch (error) {
  console.error('[Machinepark feature breakdown-details-v2]', error);
}

/* service-oneoff-parts-v2 */
try {
(() => {
  const LIMIT = 30;
  const escAttr = value => String(value ?? '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  function normalize(items) {
    return (Array.isArray(items) ? items : []).map(item => ({
      supplier: String(item?.supplier || '').trim().slice(0, 120),
      supplierCode: String(item?.supplierCode || '').trim().slice(0, 120),
      description: String(item?.description || '').trim().slice(0, 300),
      qty: Math.max(0.001, Math.min(999999, normalizePartQuantity(item?.qty, 1))),
    })).filter(item => item.supplier || item.supplierCode || item.description).slice(0, LIMIT);
  }

  function displayLines(record) {
    return normalize(record?.oneOffParts).map(item => {
      const text = [item.supplier, item.supplierCode, item.description].filter(Boolean).join(' · ');
      return `${formatPartQuantity(item.qty)} × ${text}`;
    });
  }

  function rowHtml(item = {}, disabled = false) {
    const normalized = normalize([item])[0] || { supplier:'', supplierCode:'', description:'', qty:1 };
    const off = disabled ? ' disabled' : '';
    return `<div class="service-oneoff-row"><input class="service-oneoff-supplier" type="text" maxlength="120" placeholder="Leverancier" value="${escAttr(normalized.supplier)}"${off}><input class="service-oneoff-code" type="text" maxlength="120" placeholder="Leveranciercode" value="${escAttr(normalized.supplierCode)}"${off}><input class="service-oneoff-description" type="text" maxlength="300" placeholder="Omschrijving" value="${escAttr(normalized.description)}"${off}><input class="service-oneoff-qty" type="number" min="0.001" step="0.001" inputmode="decimal" aria-label="Aantal" value="${normalized.qty}"${off}><button type="button" class="remove-line service-oneoff-remove" data-remove-service-oneoff aria-label="Eenmalig onderdeel verwijderen"${off}>×</button></div>`;
  }

  function editorHtml(items = [], { machine = false, disabled = false, kind = 'service' } = {}) {
    const saved = normalize(items);
    const rows = saved.length ? saved : [{}];
    return `<div class="service-oneoff-parts${machine ? ' service-oneoff-machine' : ''}" data-oneoff-kind="${escAttr(kind)}">
      <div class="section-title">Eenmalige onderdelen</div>
      <div class="muted" style="font-size:11px">Voor onderdelen die niet in de onderdelenlijst staan. Deze regels wijzigen de voorraad niet.</div>
      <div class="service-oneoff-head"><span>Leverancier</span><span>Leveranciercode</span><span>Omschrijving</span><span>Aantal</span><span></span></div>
      <div class="service-oneoff-list">${rows.map(item => rowHtml(item, disabled)).join('')}</div>
      <button type="button" class="btn small service-oneoff-add" data-add-service-oneoff style="margin-top:8px"${disabled ? ' disabled' : ''}>+ Eenmalig onderdeel</button>
    </div>`;
  }

  window.machineparkCollectServiceOneOff = root => {
    if (!root) return [];
    return normalize([...root.querySelectorAll('.service-oneoff-row')].map(row => ({
      supplier: row.querySelector('.service-oneoff-supplier')?.value || '',
      supplierCode: row.querySelector('.service-oneoff-code')?.value || '',
      description: row.querySelector('.service-oneoff-description')?.value || '',
      qty: row.querySelector('.service-oneoff-qty')?.value || 1,
    })));
  };
  window.machineparkCollectBreakdownOneOff = window.machineparkCollectServiceOneOff;

  function insertBeforePhotoEditor(html, block) {
    const photoMarker = '<div class="field full service-photo-editor">';
    const photoPos = html.indexOf(photoMarker);
    if (photoPos >= 0) return html.slice(0, photoPos) + block + html.slice(photoPos);
    const pos = html.lastIndexOf('</div>');
    return pos < 0 ? html + block : html.slice(0, pos) + block + html.slice(pos);
  }

  function insertAfterStockParts(html, block) {
    const marker = '+ Onderdeelregel</button>';
    const markerPos = html.indexOf(marker);
    if (markerPos < 0) return insertBeforePhotoEditor(html, block);
    const closePos = html.indexOf('</div>', markerPos + marker.length);
    if (closePos < 0) return insertBeforePhotoEditor(html, block);
    const insertPos = closePos + 6;
    return html.slice(0, insertPos) + block + html.slice(insertPos);
  }

  const previousBreakdownForm = breakdownForm;
  breakdownForm = function(record = {}) {
    return insertBeforePhotoEditor(previousBreakdownForm(record), `<div class="field full">${editorHtml(record.oneOffParts || [], { kind:'breakdown' })}</div>`);
  };

  const previousMaintenanceForm = maintenanceForm;
  maintenanceForm = function(record = {}) {
    return insertBeforePhotoEditor(previousMaintenanceForm(record), `<div class="field full">${editorHtml(record.oneOffParts || [], { kind:'maintenance' })}</div>`);
  };

  const previousBreakdownMachineCardHtml = breakdownMachineCardHtml;
  breakdownMachineCardHtml = function(device) {
    return insertAfterStockParts(previousBreakdownMachineCardHtml(device), editorHtml([], { machine:true, disabled:true, kind:'breakdown' }));
  };

  const previousMaintenanceMachineCardHtml = maintenanceMachineCardHtml;
  maintenanceMachineCardHtml = function(device) {
    return insertAfterStockParts(previousMaintenanceMachineCardHtml(device), editorHtml([], { machine:true, disabled:true, kind:'maintenance' }));
  };

  const previousSetBreakdownMachineEnabled = setBreakdownMachineEnabled;
  setBreakdownMachineEnabled = function(card, enabled) {
    previousSetBreakdownMachineEnabled(card, enabled);
    card?.querySelectorAll('.service-oneoff-supplier,.service-oneoff-code,.service-oneoff-description,.service-oneoff-qty,.service-oneoff-add,.service-oneoff-remove').forEach(el => el.disabled = !enabled);
  };

  const previousSetMaintenanceMachineEnabled = setMaintenanceMachineEnabled;
  setMaintenanceMachineEnabled = function(card, enabled) {
    previousSetMaintenanceMachineEnabled(card, enabled);
    card?.querySelectorAll('.service-oneoff-supplier,.service-oneoff-code,.service-oneoff-description,.service-oneoff-qty,.service-oneoff-add,.service-oneoff-remove').forEach(el => el.disabled = !enabled);
  };

  function detailRowsHtml(record) {
    const lines = displayLines(record);
    return lines.map(line => `<div class="service-oneoff-detail-row">${escAttr(line)}</div>`).join('');
  }

  window.machineparkOneOffMaintenanceDetailsHtml = record => {
    const rows = detailRowsHtml(record);
    if (!rows) return '';
    return `<div class="field full" data-maintenance-oneoff-details><label>Eenmalige onderdelen</label><div class="service-oneoff-detail-list">${rows}</div></div>`;
  };

  function oneOffBreakdownDetailsHtml(record) {
    const rows = detailRowsHtml(record);
    if (!rows) return '';
    return `<div class="breakdown-detail-field full" data-breakdown-oneoff-details><label>Eenmalige onderdelen</label><div class="service-oneoff-detail-list">${rows}</div></div>`;
  }

  const previousShowBreakdownDetails = window.machineparkShowBreakdownDetails;
  if (typeof previousShowBreakdownDetails === 'function') {
    window.machineparkShowBreakdownDetails = function(id) {
      const result = previousShowBreakdownDetails(id);
      setTimeout(() => {
        const record = state.breakdowns.find(item => item.id === id);
        const html = record ? oneOffBreakdownDetailsHtml(record) : '';
        if (!html) return;
        const summary = document.querySelector('#modal .breakdown-detail-summary');
        if (!summary || summary.querySelector('[data-breakdown-oneoff-details]')) return;
        const usedPartsField = [...summary.querySelectorAll('.breakdown-detail-field')].find(field => field.querySelector('label')?.textContent.trim() === 'Gebruikte onderdelen');
        if (usedPartsField) usedPartsField.insertAdjacentHTML('afterend', html);
        else summary.insertAdjacentHTML('beforeend', html);
      }, 0);
      return result;
    };
  }

  function recordFor(kind, id) {
    const list = kind === 'maintenance' ? state.maintenance : state.breakdowns;
    return list.find(item => item.id === id);
  }

  function injectOneOffPrint(kind, id) {
    const lines = displayLines(recordFor(kind, id));
    if (!lines.length) return;
    const grid = document.querySelector('#servicePrintSheet .service-print-grid');
    if (!grid || grid.querySelector('[data-print-oneoff-parts]')) return;
    const field = document.createElement('div');
    field.className = 'service-print-field full';
    field.dataset.printOneoffParts = '1';
    field.innerHTML = `<div class="service-print-label">Eenmalige onderdelen</div><div class="service-print-value">${escAttr(lines.join(String.fromCharCode(10)))}</div>`;
    const usedPartsField = [...grid.querySelectorAll('.service-print-field')].find(item => item.querySelector('.service-print-label')?.textContent.trim() === 'Gebruikte onderdelen');
    if (usedPartsField) usedPartsField.insertAdjacentElement('afterend', field);
    else grid.appendChild(field);
  }

  const previousPrintServiceRecord = window.printMachineparkServiceRecord;
  if (typeof previousPrintServiceRecord === 'function') {
    window.printMachineparkServiceRecord = function(kind, id) {
      if (kind !== 'breakdowns' && kind !== 'maintenance') return previousPrintServiceRecord(kind, id);
      const nativePrint = window.print;
      window.print = function() {
        try { injectOneOffPrint(kind, id); }
        finally { window.print = nativePrint; }
        return nativePrint.call(window);
      };
      try { return previousPrintServiceRecord(kind, id); }
      finally { if (window.print !== nativePrint) window.print = nativePrint; }
    };
  }

  document.addEventListener('click', event => {
    const add = event.target.closest?.('[data-add-service-oneoff]');
    if (add) {
      const root = add.closest('.service-oneoff-parts');
      const list = root?.querySelector('.service-oneoff-list');
      if (!list) return;
      if (list.querySelectorAll('.service-oneoff-row').length >= LIMIT) {
        const label = root.dataset.oneoffKind === 'maintenance' ? 'onderhoud' : 'depannage';
        toast(`Maximaal ${LIMIT} eenmalige onderdelen per ${label}.`);
        return;
      }
      list.insertAdjacentHTML('beforeend', rowHtml({}, false));
      list.lastElementChild?.querySelector('.service-oneoff-supplier')?.focus();
      return;
    }

    const remove = event.target.closest?.('[data-remove-service-oneoff]');
    if (!remove) return;
    const root = remove.closest('.service-oneoff-parts');
    const rows = root?.querySelectorAll('.service-oneoff-row');
    const row = remove.closest('.service-oneoff-row');
    if (!row) return;
    if (rows && rows.length > 1) row.remove();
    else {
      row.querySelector('.service-oneoff-supplier').value = '';
      row.querySelector('.service-oneoff-code').value = '';
      row.querySelector('.service-oneoff-description').value = '';
      row.querySelector('.service-oneoff-qty').value = '1';
    }
  });
})();
} catch (error) {
  console.error('[Machinepark feature service-oneoff-parts-v2]', error);
}

/* role-management-v1 */
try {
(() => {
  const ROLE_MANAGEMENT_URL = '/machinepark/synology/api/role-management.php';
  window.machineparkPermissions = window.machineparkPermissions || {};
  window.machineparkAvailableRoles = window.machineparkAvailableRoles || [];
  window.machineparkPermissionCatalog = window.machineparkPermissionCatalog || [];
  window.machineparkRoleConfigEtag = window.machineparkRoleConfigEtag || null;
  window.machineparkAccessReady = false;

  function hasPermission(key) {
    if (!window.machineparkAccessReady) return false;
    return Boolean(window.machineparkPermissions?.[key]);
  }
  window.machineparkHasPermission = hasPermission;

  function currentRoleLabel() {
    const role = String(window.machineparkRole || 'gebruiker');
    const found = (window.machineparkAvailableRoles || []).find((x) => (x.value || x.id) === role);
    return found?.label || window.machineparkCurrentRoleLabel || role.charAt(0).toUpperCase() + role.slice(1);
  }

  machineparkRoleLabel = function(role) {
    const id = String(role || 'gebruiker');
    const found = (window.machineparkAvailableRoles || []).find((x) => (x.value || x.id) === id);
    return found?.label || (id === 'beheerder' ? 'Beheerder' : id === 'gebruiker' ? 'Gebruiker' : id === 'technieker' ? 'Technieker' : id === 'magazijnier' ? 'Magazijnier' : id);
  };

  function viewPermission(view) { return `view.${view}`; }
  function firstAllowedView() {
    return ['dashboard','devices','maintenance','breakdowns','faults','manuals','parts','settings'].find((view) => hasPermission(viewPermission(view))) || 'dashboard';
  }

  const originalSwitchViewForRoles = switchView;
  switchView = function(view) {
    if (window.machineparkAccessReady && !hasPermission(viewPermission(view))) view = firstAllowedView();
    return originalSwitchViewForRoles(view);
  };
  window.switchView = switchView;

  function applySettingsCards() {
    const roleCard = document.getElementById('roleManagementCard');
    const usersCard = document.getElementById('userManagementCard');
    const auditCard = document.getElementById('auditLogCard');
    if (roleCard) roleCard.style.display = hasPermission('roles.manage') ? '' : 'none';
    if (usersCard) usersCard.style.display = hasPermission('users.manage') ? '' : 'none';
    if (auditCard) auditCard.style.display = hasPermission('audit.view') ? '' : 'none';
    document.querySelectorAll('[data-undo-audit]').forEach((btn) => {
      if (!hasPermission('audit.undo')) {
        btn.disabled = true;
        btn.title = 'Deze rol mag wijzigingen niet ongedaan maken.';
      }
    });
  }

  applyMachineparkRoleAccess = function() {
    if (!window.machineparkAccessReady) return;
    document.querySelectorAll('.nav button[data-view]').forEach((btn) => {
      btn.style.display = hasPermission(viewPermission(btn.dataset.view)) ? '' : 'none';
    });
    window.machineparkIsAdmin = hasPermission('view.settings');
    const visible = [...document.querySelectorAll('.nav button[data-view]')].filter((btn) => btn.style.display !== 'none').length;
    document.documentElement.style.setProperty('--mobile-nav-count', String(Math.max(1, visible)));
    if (!hasPermission(viewPermission(state.view))) originalSwitchViewForRoles(firstAllowedView());
    applySettingsCards();
  };
  window.applyMachineparkRoleAccess = applyMachineparkRoleAccess;

  machineparkCapabilities = function() {
    return {
      devices: hasPermission('devices.edit') || hasPermission('devices.statusNotes'),
      maintenance: hasPermission('maintenance.edit') || hasPermission('maintenance.delete'),
      breakdowns: hasPermission('breakdowns.edit') || hasPermission('breakdowns.delete'),
      parts: hasPermission('parts.edit') || hasPermission('parts.stock'),
    };
  };

  applyOperationalPermissions = function() {
    if (!window.machineparkAccessReady) return;
    window.machineparkCanEdit = machineparkCapabilities();
    const visibility = [
      ['#addDevice','devices.add'], ['#addMaintenance','maintenance.add'],
      ['#addBreakdown','breakdowns.add'], ['#addPart','parts.add'],
      ['#exportPartsCsv','parts.export'],
    ];
    visibility.forEach(([selector, permission]) => document.querySelectorAll(selector).forEach((el) => el.style.display = hasPermission(permission) ? '' : 'none'));
    document.querySelectorAll('[data-edit-part]').forEach((el) => el.style.display = (hasPermission('parts.edit') || hasPermission('parts.stock')) ? '' : 'none');
    document.querySelectorAll('.page-print-btn,.service-detail-print-btn').forEach((el) => el.style.display = hasPermission('print') ? '' : 'none');
    applySettingsCards();
  };
  window.applyOperationalPermissions = applyOperationalPermissions;

  window.applyMachineparkServerAccess = function(body) {
    if (!body || typeof body !== 'object' || !body.permissions) return;
    window.machineparkPermissions = { ...body.permissions };
    window.machineparkRole = String(body.role || window.machineparkRole || 'gebruiker');
    window.machineparkCurrentRoleLabel = String(body.roleLabel || window.machineparkRole);
    window.machineparkAccessReady = true;
    window.machineparkIsAdmin = Boolean(window.machineparkPermissions['view.settings']);
    const roleEl = document.getElementById('accountDisplayRole');
    if (roleEl) roleEl.textContent = window.machineparkCurrentRoleLabel;
    applyMachineparkRoleAccess();
    applyOperationalPermissions();
  };

  const baseAdminFetch = adminFetch;
  adminFetch = async function(url, options = {}) {
    const data = await baseAdminFetch(url, options);
    const method = String(options?.method || 'GET').toUpperCase();
    if (url === USER_MANAGEMENT_URL && method === 'GET') {
      window.machineparkAvailableRoles = data.roles || [];
      const select = document.getElementById('inviteUserRole');
      if (select) fillRoleSelect(select, select.value || 'gebruiker');
    }
    return data;
  };

  roleBadgeHtml = function(role) {
    const label = machineparkRoleLabel(role);
    const cls = role === 'beheerder' ? 'success' : role === 'technieker' ? 'blue' : role === 'magazijnier' ? 'warn' : 'gray';
    return `<span class="badge ${cls}">${esc(label)}</span>`;
  };

  function fillRoleSelect(select, selected) {
    if (!select) return;
    const roles = window.machineparkAvailableRoles || [];
    select.innerHTML = roles.map((role) => `<option value="${esc(role.value || role.id)}" ${(role.value || role.id) === selected ? 'selected' : ''}>${esc(role.label || role.value || role.id)}</option>`).join('');
  }

  openUserEditor = function(userId) {
    const u = (window.machineparkAdminUsers || []).find((x) => x.id === userId);
    if (!u) { toast('Gebruiker niet gevonden'); return; }
    const options = (window.machineparkAvailableRoles || []).map((role) => `<option value="${esc(role.value || role.id)}" ${(role.value || role.id) === u.role ? 'selected' : ''}>${esc(role.label || role.value || role.id)}</option>`).join('');
    const roleField = u.isOwner
      ? `<div class="field"><label>Rol</label><input value="Beheerder" readonly style="background:#f4f6f5"><input type="hidden" name="role" value="beheerder"><div class="muted" style="font-size:11px;margin-top:4px">Vaste hoofdbeheerder · alle rechten blijven altijd actief.</div></div>`
      : `<div class="field"><label>Rol</label><select name="role">${options}</select></div>`;
    const body = `<div class="form-grid"><div class="field"><label>Voornaam</label><input name="firstName" value="${esc(u.firstName || '')}" maxlength="100"></div><div class="field"><label>Achternaam</label><input name="lastName" value="${esc(u.lastName || '')}" maxlength="100"></div><div class="field full"><label>E-mailadres</label><input value="${esc(u.email || '')}" readonly style="background:#f4f6f5"></div>${roleField}<div class="field full"><label>Nieuw wachtwoord</label><input name="password" type="password" minlength="10" autocomplete="new-password" placeholder="Leeg laten om niet te wijzigen"><div class="muted" style="font-size:11px;margin-top:4px">Minstens 10 tekens wanneer je het wachtwoord wijzigt.</div></div><div class="field full"><div class="alert"><strong>Rollen & rechten</strong>De toegestane handelingen worden bepaald in Beheer → Rollen & rechten.</div></div></div>`;
    showModal('Gebruiker bewerken', body, 'Wijzigingen opslaan', async (fd) => {
      try {
        const newRole = val(fd, 'role') || 'gebruiker';
        await adminFetch(USER_MANAGEMENT_URL, { method: 'POST', body: JSON.stringify({ action: 'update-user', userId: u.id, firstName: val(fd, 'firstName'), lastName: val(fd, 'lastName'), role: newRole, password: val(fd, 'password') }) });
        closeModal();
        toast('Gebruiker en rol aangepast');
        await loadUserManagement();
        centralSync.etag = null;
        await centralPull({ apply: true, quiet: true });
        if (hasPermission('audit.view')) await loadAuditLog();
      } catch (e) { alert(e.message); }
    });
  };

  const baseBindForRoles = bind;
  bind = function() {
    baseBindForRoles();
    const inviteForm = document.getElementById('inviteUserForm');
    if (inviteForm) {
      let roleSelect = document.getElementById('inviteUserRole');
      if (!roleSelect) {
        roleSelect = document.createElement('select');
        roleSelect.id = 'inviteUserRole';
        roleSelect.style.cssText = 'min-width:180px;border:1px solid var(--line);border-radius:10px;padding:10px 11px;background:white';
        inviteForm.insertBefore(roleSelect, inviteForm.querySelector('button[type=submit]'));
      }
      fillRoleSelect(roleSelect, 'gebruiker');
      inviteForm.onsubmit = async (e) => {
        e.preventDefault();
        if (!hasPermission('users.manage')) return;
        const input = document.getElementById('inviteUserEmail');
        const email = String(input?.value || '').trim().toLowerCase();
        if (!email) return;
        const passwordInput = document.getElementById('inviteUserPassword');
        const password = String(passwordInput?.value || '');
        if (password.length < 10) { alert('Gebruik een eerste wachtwoord van minstens 10 tekens.'); return; }
        const role = String(roleSelect.value || 'gebruiker');
        const submit = e.target.querySelector('button[type=submit]');
        if (submit) submit.disabled = true;
        try {
          await adminFetch(USER_MANAGEMENT_URL, { method: 'POST', body: JSON.stringify({ action: 'create-user', email, password, role }) });
          if (input) input.value = '';
          if (passwordInput) passwordInput.value = '';
          toast('Gebruiker toegevoegd');
          await loadUserManagement();
          if (hasPermission('audit.view')) await loadAuditLog();
        } catch (err) { alert(err.message); }
        finally { if (submit) submit.disabled = false; }
      };
    }
    const refreshRoles = document.getElementById('refreshRoles');
    if (refreshRoles) refreshRoles.onclick = () => loadRoleManagement();
    const addRole = document.getElementById('addRole');
    if (addRole) addRole.onclick = () => openRoleEditor();
    applyOperationalPermissions();
  };

  function permissionGroupsHtml(role) {
    const allowed = (window.machineparkPermissionCatalog || []).filter((item) => role.permissions?.[item.key]);
    if (!allowed.length) return '<span class="muted">Geen handelingen toegestaan</span>';
    return `<div class="role-permission-summary">${allowed.slice(0, 8).map((item) => `<span class="badge gray">${esc(item.label)}</span>`).join('')}${allowed.length > 8 ? `<span class="badge gray">+${allowed.length - 8}</span>` : ''}</div>`;
  }

  function renderRoleManagement() {
    const body = document.getElementById('roleManagementBody');
    const status = document.getElementById('roleManagementStatus');
    if (!body) return;
    const roles = window.machineparkRoleDefinitions || [];
    if (status) status.textContent = `${roles.length} rol${roles.length === 1 ? '' : 'len'} · vaste hoofdbeheerder is niet beperkbaar`;
    body.innerHTML = roles.map((role) => {
      const count = Object.values(role.permissions || {}).filter(Boolean).length;
      return `<div class="role-card"><div class="role-card-head"><div><h5>${esc(role.label)}</h5><div class="role-card-meta">${role.builtIn ? 'Standaardrol' : 'Eigen rol'} · ${esc(role.id)}</div></div><div class="role-card-count">${count}</div></div>${permissionGroupsHtml(role)}<div class="role-card-foot"><button class="btn small" type="button" data-role-edit="${esc(role.id)}">Bewerken</button>${role.builtIn ? '' : `<button class="btn small danger" type="button" data-role-delete="${esc(role.id)}">Verwijderen</button>`}</div></div>`;
    }).join('');
    body.querySelectorAll('[data-role-edit]').forEach((btn) => btn.onclick = () => openRoleEditor(btn.dataset.roleEdit));
    body.querySelectorAll('[data-role-delete]').forEach((btn) => btn.onclick = () => deleteRole(btn.dataset.roleDelete));
  }

  async function roleFetch(options = {}) {
    const headers = await centralHeaders(options.body !== undefined);
    const res = await fetch(ROLE_MANAGEMENT_URL, { ...options, headers: { ...headers, ...(options.headers || {}) }, cache: 'no-store' });
    let body = {};
    try { body = await res.json(); } catch (_) {}
    if (!res.ok) throw new Error(body?.error || `Rollenbeheer mislukt (${res.status})`);
    return body;
  }

  async function loadRoleManagement() {
    if (!hasPermission('roles.manage')) return;
    const status = document.getElementById('roleManagementStatus');
    if (status) status.textContent = 'Rollen worden geladen…';
    try {
      const data = await roleFetch();
      window.machineparkRoleDefinitions = data.roles || [];
      window.machineparkPermissionCatalog = data.permissionCatalog || [];
      window.machineparkRoleConfigEtag = data.etag || null;
      window.machineparkAvailableRoles = (data.roles || []).map((role) => ({ value: role.id, label: role.label }));
      renderRoleManagement();
    } catch (error) {
      if (status) status.textContent = 'Rollen konden niet worden geladen: ' + error.message;
    }
  }
  window.loadRoleManagement = loadRoleManagement;

  function groupedCatalog() {
    const groups = new Map();
    (window.machineparkPermissionCatalog || []).forEach((item) => {
      if (!groups.has(item.group)) groups.set(item.group, []);
      groups.get(item.group).push(item);
    });
    return [...groups.entries()];
  }

  function openRoleEditor(roleId = '') {
    const existing = (window.machineparkRoleDefinitions || []).find((role) => role.id === roleId) || null;
    const groups = groupedCatalog();
    const permissionHtml = groups.map(([group, items]) => `<section class="role-editor-group"><div class="role-editor-group-head"><div><h4>${esc(group)}</h4><small>${items.length} ${items.length === 1 ? 'recht' : 'rechten'}</small></div></div><div class="role-editor-rights">${items.map((item) => `<label class="role-editor-right"><span class="role-editor-right-label">${esc(item.label)}</span><input class="role-editor-switch" type="checkbox" name="perm:${esc(item.key)}" ${existing?.permissions?.[item.key] ? 'checked' : ''} aria-label="${esc(item.label)}"></label>`).join('')}</div></section>`).join('');
    const name = existing?.label || '';
    const nameField = `<div class="field full"><label>Naam rol *</label><input name="roleLabel" required maxlength="80" value="${esc(name)}" ${existing?.builtIn ? 'readonly style="background:#f4f6f5"' : ''}><div class="muted" style="font-size:11px;margin-top:4px">${existing?.builtIn ? 'De naam van een standaardrol blijft behouden; de rechten zijn wel aanpasbaar.' : 'Nieuwe rollen kunnen daarna meteen aan gebruikers worden toegewezen.'}</div></div>`;
    const body = `<div class="role-editor-layout"><div class="role-editor-top"><div class="role-editor-name-card">${nameField}</div><div class="role-editor-safety-card"><div class="role-editor-safety-icon">✓</div><div><strong>Veiligheidsregel</strong><p>De vaste hoofdbeheerder behoudt altijd alle rechten, ongeacht deze instellingen.</p></div></div></div><div class="role-editor-section-head"><div><strong>Rechten per onderdeel</strong><span>Zet per handeling de schakelaar aan of uit.</span></div></div><div class="role-editor-groups">${permissionHtml}</div></div>`;
    showModal(existing ? `Rol wijzigen · ${existing.label}` : 'Nieuwe rol', body, 'Rol opslaan', async (fd) => {
      const label = val(fd, 'roleLabel');
      if (!label) return;
      const permissions = {};
      (window.machineparkPermissionCatalog || []).forEach((item) => permissions[item.key] = fd.get(`perm:${item.key}`) === 'on');
      try {
        const data = await roleFetch({ method: 'POST', body: JSON.stringify({ action: 'save-role', etag: window.machineparkRoleConfigEtag, role: { id: existing?.id || '', label, permissions } }) });
        window.machineparkRoleDefinitions = data.roles || [];
        window.machineparkRoleConfigEtag = data.etag || null;
        window.machineparkAvailableRoles = (data.roles || []).map((role) => ({ value: role.id, label: role.label }));
        closeModal();
        renderRoleManagement();
        toast(existing ? 'Rol en rechten aangepast' : 'Nieuwe rol aangemaakt');
        if (hasPermission('users.manage')) await loadUserManagement();
        centralSync.etag = null;
        await centralPull({ apply: true, quiet: true });
      } catch (error) { alert(error.message); }
    });
  }
  window.openMachineparkRoleEditor = openRoleEditor;

  async function deleteRole(roleId) {
    const role = (window.machineparkRoleDefinitions || []).find((x) => x.id === roleId);
    if (!role || role.builtIn) return;
    if (!confirm(`Rol “${role.label}” verwijderen? Dit kan alleen wanneer geen gebruiker deze rol nog gebruikt.`)) return;
    try {
      const data = await roleFetch({ method: 'POST', body: JSON.stringify({ action: 'delete-role', roleId, etag: window.machineparkRoleConfigEtag }) });
      window.machineparkRoleDefinitions = data.roles || [];
      window.machineparkRoleConfigEtag = data.etag || null;
      window.machineparkAvailableRoles = (data.roles || []).map((x) => ({ value: x.id, label: x.label }));
      renderRoleManagement();
      toast('Rol verwijderd');
      if (hasPermission('users.manage')) await loadUserManagement();
    } catch (error) { alert(error.message); }
  }

  const baseLoadAdminPanels = loadAdminPanels;
  loadAdminPanels = async function() {
    if (!hasPermission('view.settings')) return;
    const tasks = [];
    if (hasPermission('roles.manage')) tasks.push(loadRoleManagement());
    if (hasPermission('users.manage')) tasks.push(loadUserManagement());
    if (hasPermission('audit.view')) tasks.push(loadAuditLog());
    await Promise.all(tasks);
    applySettingsCards();
  };

  const baseAuditUndoButton = auditUndoButton;
  auditUndoButton = function(entry, change, changeIndex) {
    if (!hasPermission('audit.undo')) return '<button class="btn small" type="button" disabled title="Deze rol mag niets herstellen.">Geblokkeerd</button>';
    return baseAuditUndoButton(entry, change, changeIndex);
  };

  const baseOpenDeviceForRoles = openDevice;
  openDevice = function(id) {
    if (!id) {
      if (!hasPermission('devices.add')) { toast('Deze rol mag geen toestellen toevoegen'); return; }
      return baseOpenDeviceForRoles(id);
    }
    if (hasPermission('devices.edit')) return baseOpenDeviceForRoles(id);
    if (!hasPermission('devices.statusNotes')) { toast('Deze rol mag toestelgegevens niet wijzigen'); return; }
    const old = state.devices.find((d) => d.id === id);
    if (!old) return;
    const body = `<div class="form-grid"><div class="field"><label>Toestel</label><input value="${esc(old.assetCode || old.model || 'Toestel')}" readonly style="background:#f4f6f5"></div><div class="field"><label>Locatie</label><input value="${esc(deviceLocationAt(old) || old.location || 'Geen locatie')}" readonly style="background:#f4f6f5"></div><div class="field"><label>Status</label><select name="status">${['Actief','In herstelling','Buiten dienst'].map((x) => `<option ${old.status === x ? 'selected' : ''}>${x}</option>`).join('')}</select></div><div class="field full"><label>Notities</label><textarea name="notes">${esc(old.notes || '')}</textarea></div></div>`;
    showModal('Toestelstatus & notities', body, 'Opslaan', async (fd) => {
      await put('devices', { ...old, status: val(fd, 'status') || old.status || 'Actief', notes: val(fd, 'notes'), updatedAt: new Date().toISOString() });
      closeModal(); await refresh(); toast('Toestelstatus en notities opgeslagen');
    });
  };

  const baseOpenPartForRoles = openPart;
  openPart = function(id) {
    if (!id) {
      if (!hasPermission('parts.add')) { toast('Deze rol mag geen onderdelen toevoegen'); return; }
      return baseOpenPartForRoles(id);
    }
    if (hasPermission('parts.edit')) return baseOpenPartForRoles(id);
    if (!hasPermission('parts.stock')) { toast('Deze rol mag onderdelen niet wijzigen'); return; }
    const old = state.parts.find((p) => p.id === id);
    if (!old) return;
    const body = `<div class="form-grid"><div class="field"><label>Art nr</label><input value="${esc(old.artNr || '—')}" readonly style="background:#f4f6f5"></div><div class="field full"><label>Omschrijving</label><input value="${esc(old.description || '—')}" readonly style="background:#f4f6f5"></div><div class="field"><label>Voorraad locatie 1</label><input name="stock" type="number" step="1" value="${Number(old.stock || 0)}"></div></div>`;
    showModal('Voorraad aanpassen', body, 'Voorraad opslaan', async (fd) => {
      await put('parts', { ...old, stock: Number(fd.get('stock') || 0), updatedAt: new Date().toISOString() });
      closeModal(); await refresh(); toast('Voorraad aangepast');
    });
  };

  const baseOpenMaintenanceForRoles = openMaintenance;
  openMaintenance = function(id) {
    if (id && !hasPermission('maintenance.edit')) { toast('Deze rol mag onderhoud niet wijzigen'); return; }
    if (!id && !hasPermission('maintenance.add')) { toast('Deze rol mag geen onderhoud registreren'); return; }
    return baseOpenMaintenanceForRoles(id);
  };

  const baseShowMaintenanceDetailsForRoles = showMaintenanceDetails;
  showMaintenanceDetails = function(id) {
    const result = baseShowMaintenanceDetailsForRoles(id);
    setTimeout(() => {
      const edit = document.getElementById('editMaintenanceFromDetails');
      const del = document.getElementById('deleteMaintenanceFromDetails');
      if (edit) edit.style.display = hasPermission('maintenance.edit') ? '' : 'none';
      if (del) del.style.display = hasPermission('maintenance.delete') ? '' : 'none';
      document.querySelectorAll('#modal .service-detail-print-btn').forEach((btn) => btn.style.display = hasPermission('print') ? '' : 'none');
    }, 0);
    return result;
  };

  function readonlyBreakdown(id) {
    const b = state.breakdowns.find((x) => x.id === id);
    if (!b) return;
    const photos = Array.isArray(b.photos) ? b.photos.filter((src) => typeof src === 'string' && src.trim()) : [];
    const body = `<div class="form-grid"><div class="field"><label>Datum en uur</label><div><strong>${recordDateTimeFmt(b)}</strong></div></div><div class="field"><label>Toestel</label><div><strong>${esc(deviceName(b.deviceId, recordMoment(b)))}</strong></div></div><div class="field"><label>Prioriteit</label><div>${esc(b.priority || '—')}</div></div><div class="field"><label>Status</label><div>${esc(b.status || '—')}</div></div><div class="field"><label>Technieker</label><div>${esc(b.technician || '—')}</div></div><div class="field full"><label>Probleem / melding</label><div style="white-space:pre-wrap">${esc(b.issue || '—')}</div></div><div class="field full"><label>Diagnose</label><div style="white-space:pre-wrap">${esc(b.diagnosis || '—')}</div></div><div class="field full"><label>Oplossing / werken</label><div style="white-space:pre-wrap">${esc(b.solution || '—')}</div></div><div class="field full"><label>Gebruikte onderdelen</label><div>${esc(usedPartsText(b.usedParts || []))}</div></div>${photos.length ? `<div class="field full"><label>Foto’s</label><div class="service-photo-details">${photos.map((src) => `<img src="${esc(window.machineparkThumbnailRef?window.machineparkThumbnailRef(src):src)}" data-full-src="${esc(src)}" data-photo-lightbox loading="lazy" decoding="async" alt="Verslagfoto">`).join('')}</div></div>` : ''}</div>`;
    const actions = `${hasPermission('breakdowns.delete') ? '<button class="btn danger" type="button" id="roleDeleteBreakdown">Verwijderen</button>' : ''}${hasPermission('print') ? '<button class="btn" type="button" id="rolePrintBreakdown">🖨 Afdrukken</button>' : ''}`;
    document.getElementById('modal').innerHTML = `<div class="modal-head"><h3>Depannage details</h3><button class="close" type="button">×</button></div><div class="modal-body">${body}</div><div class="modal-foot"><button class="btn" type="button" id="roleCloseBreakdown">Sluiten</button>${actions}</div>`;
    document.getElementById('modalBackdrop').classList.add('show');
    document.querySelector('#modal .close').onclick = closeModal;
    document.getElementById('roleCloseBreakdown').onclick = closeModal;
    const del = document.getElementById('roleDeleteBreakdown');
    if (del) del.onclick = () => deleteServiceRecord('breakdowns', id);
    const print = document.getElementById('rolePrintBreakdown');
    if (print) print.onclick = () => window.printMachineparkServiceRecord?.('breakdowns', id);
  }

  const baseOpenBreakdownForRoles = openBreakdown;
  openBreakdown = function(id) {
    if (!id) {
      if (!hasPermission('breakdowns.add')) { toast('Deze rol mag geen depannage registreren'); return; }
      return baseOpenBreakdownForRoles(id);
    }
    if (hasPermission('breakdowns.edit')) {
      const result = baseOpenBreakdownForRoles(id);
      setTimeout(() => {
        const del = document.getElementById('deleteBreakdownFromDetails');
        if (del) del.style.display = hasPermission('breakdowns.delete') ? '' : 'none';
        document.querySelectorAll('#modal .service-detail-print-btn').forEach((btn) => btn.style.display = hasPermission('print') ? '' : 'none');
      }, 0);
      return result;
    }
    return readonlyBreakdown(id);
  };

  const baseDeleteServiceRecordForRoles = deleteServiceRecord;
  deleteServiceRecord = function(storeName, id) {
    const permission = storeName === 'maintenance' ? 'maintenance.delete' : storeName === 'breakdowns' ? 'breakdowns.delete' : '';
    if (permission && !hasPermission(permission)) { toast('Deze rol mag dit dossier niet verwijderen'); return; }
    return baseDeleteServiceRecordForRoles(storeName, id);
  };

  const basePrintMachineparkViewForRoles = window.printMachineparkView;
  if (basePrintMachineparkViewForRoles) window.printMachineparkView = function(...args) {
    if (!hasPermission('print')) { toast('Deze rol mag niet afdrukken'); return; }
    return basePrintMachineparkViewForRoles(...args);
  };
  const basePrintServiceForRoles = window.printMachineparkServiceRecord;
  if (basePrintServiceForRoles) window.printMachineparkServiceRecord = function(...args) {
    if (!hasPermission('print')) { toast('Deze rol mag niet afdrukken'); return; }
    return basePrintServiceForRoles(...args);
  };
})();
} catch (error) {
  console.error('[Machinepark feature role-management-v1]', error);
}

/* role-settings-actions-v1 */
try {
(() => {
  const previousApplyOperationalPermissions = applyOperationalPermissions;
  applyOperationalPermissions = function() {
    previousApplyOperationalPermissions();
    const rules = [
      ['#exportBackup', 'backup.export'],
      ['#importBackup', 'backup.import'],
      ['#importStockExcelBtn', 'parts.import'],
      ['#syncDevicesExcelBtn', 'devices.import'],
    ];
    rules.forEach(([selector, permission]) => {
      document.querySelectorAll(selector).forEach((el) => {
        el.style.display = window.machineparkHasPermission?.(permission) ? '' : 'none';
      });
    });
  };
  window.applyOperationalPermissions = applyOperationalPermissions;
  if (window.machineparkAccessReady) applyOperationalPermissions();
})();
} catch (error) {
  console.error('[Machinepark feature role-settings-actions-v1]', error);
}

/* device-photos-v2 */
try {
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
      const photoCell = photo ? `<img class="device-overview-photo" src="${esc(window.machineparkThumbnailRef?window.machineparkThumbnailRef(photo):photo)}" data-full-src="${esc(photo)}" loading="lazy" decoding="async" fetchpriority="low" alt="Overzichtsfoto ${esc(d.assetCode || d.model || 'toestel')}">` : '<div class="device-overview-photo-placeholder">▣</div>';
      return `<tr class="${d.status==='Buiten dienst'?'device-row-out-of-service':''}" data-device-history="${d.id}"><td class="device-overview-photo-cell">${photoCell}</td><td><strong>${esc(d.assetCode || '—')}</strong></td><td>${esc(loc)}${nextLoc ? `<br><span class="muted" style="font-size:11px">Vanaf ${dateTimeFmt(nextLoc.effectiveFrom)} → ${esc(nextLoc.location)}</span>` : ''}</td><td>${esc(machine)}</td><td>${esc(d.serial || '—')}</td><td class="nowrap">${dateFmt(d.installDate)}</td><td>${statusBadge(d.status || 'Actief')}</td><td class="nowrap"><strong>${dateFmt(d.nextHalf)}</strong>${d.nextHalf ? `<br>${dueBadge(d.nextHalf)}` : ''}</td><td class="nowrap"><strong>${dateFmt(d.nextAnnual)}</strong>${d.nextAnnual ? `<br>${dueBadge(d.nextAnnual)}` : ''}</td><td><button class="btn small" data-device-details="${d.id}">Details</button></td></tr>`;
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
} catch (error) {
  console.error('[Machinepark feature device-photos-v2]', error);
}

/* device-photo-blob-storage-v1 */
try {
(() => {
  const DEVICE_PHOTO_STORAGE_URL = '/machinepark/synology/api/device-photos.php';

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
} catch (error) {
  console.error('[Machinepark feature device-photo-blob-storage-v1]', error);
}

/* print-device-details-v2 */
try {
(() => {
  function canPrintDeviceDetails() {
    if (window.machineparkAccessReady && typeof window.machineparkHasPermission === 'function') {
      return window.machineparkHasPermission('print');
    }
    return true;
  }

  function absoluteImageSources(root) {
    root.querySelectorAll('img').forEach((img) => {
      try { img.setAttribute('src', img.dataset.fullSrc || img.src); } catch (_) {}
      img.removeAttribute('loading');
    });
  }

  // machinepark-print-device-photo-ready-v1
  async function waitForPrintImages(doc) {
    const images = [...doc.images];
    if (!images.length) return;

    await Promise.all(images.map(async (img) => {
      if (!img.complete || !img.naturalWidth) {
        await new Promise((resolve) => {
          let finished = false;
          const done = () => {
            if (finished) return;
            finished = true;
            resolve();
          };
          img.addEventListener('load', done, { once: true });
          img.addEventListener('error', done, { once: true });
          setTimeout(done, 7000);
        });
      }

      if (typeof img.decode === 'function' && img.naturalWidth) {
        try {
          await Promise.race([
            img.decode(),
            new Promise((resolve) => setTimeout(resolve, 3500)),
          ]);
        } catch (_) {}
      }
    }));

    await new Promise((resolve) => {
      const view = doc.defaultView;
      if (!view || typeof view.requestAnimationFrame !== 'function') {
        setTimeout(resolve, 120);
        return;
      }
      view.requestAnimationFrame(() => view.requestAnimationFrame(resolve));
    });
  }

  window.printDeviceDetails = async function(id) {
    if (!canPrintDeviceDetails()) {
      alert('Deze rol mag niet afdrukken.');
      return;
    }
    const device = state.devices.find((item) => item.id === id);
    const source = document.querySelector('#modal .modal-body');
    if (!device || !source) return;

    const clone = source.cloneNode(true);
    clone.querySelectorAll('button,.device-photo-remove,.device-photo-overview,.manual-device-section').forEach((el) => el.remove());
    absoluteImageSources(clone);

    const label = [device.assetCode, device.brand, device.model].filter(Boolean).join(' · ') || 'Toestel';
    const popup = window.open('', '_blank', 'width=1050,height=820');
    if (!popup) {
      alert('Het afdrukvenster kon niet worden geopend. Sta pop-ups toe voor Machinepark en probeer opnieuw.');
      return;
    }

    popup.document.open();
    popup.document.write(`<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Machinepark - ${esc(label)}</title><style>
      @page{size:A4;margin:12mm}
      *{box-sizing:border-box}
      html,body{background:#fff;color:#111}
      body{margin:0;font-family:Inter,Arial,sans-serif;font-size:10pt;line-height:1.45}
      .print-head{display:flex;justify-content:space-between;align-items:flex-end;gap:15px;border-bottom:2px solid #173f35;padding-bottom:5mm;margin-bottom:6mm}
      .print-head h1{font-size:20pt;margin:0;color:#173f35}
      .print-head .subtitle{font-size:11pt;font-weight:700;margin-top:2mm}
      .print-date{font-size:8.5pt;color:#555;white-space:nowrap}
      .form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4mm}
      .field{display:grid;gap:2mm}.field.full{grid-column:1/-1}
      .muted{color:#555}
      strong{color:#111}
      button{display:none!important}
      .history-group{margin-top:2mm}.history-group h4{font-size:13pt;margin:0 0 4mm}
      .timeline-legend{display:flex;gap:2mm;flex-wrap:wrap;margin:0 0 4mm}
      .event-label,.badge{display:inline-flex;align-items:center;padding:1.3mm 2.2mm;border-radius:999px;font-size:7.5pt;font-weight:700;border:1px solid #ccc;background:#f3f3f3;color:#222}
      .timeline{border-left:1.5px solid #aaa;margin-left:2mm;padding-left:5mm;display:grid;gap:3mm}
      .timeline-item{position:relative;border:1px solid #ccc;border-radius:2.5mm;padding:3mm;background:#fff;break-inside:avoid}
      .timeline-item:before{content:"";position:absolute;left:-6.6mm;top:4.5mm;width:2.5mm;height:2.5mm;background:#444;border-radius:50%;border:1mm solid #fff}
      .timeline-item .date{font-size:8pt;color:#555}.timeline-item p{margin:1.5mm 0 0;color:#333}
      .device-detail-photo-section{border:1px solid #ccc;border-radius:3mm;padding:3mm;break-inside:avoid}
      .device-detail-photo-head{display:flex;justify-content:space-between;align-items:center;gap:3mm;margin-bottom:3mm}
      .device-detail-photo-gallery{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:3mm}
      .device-detail-photo{position:relative;border:1px solid #ccc;border-radius:2mm;overflow:hidden;break-inside:avoid;background:#fafafa;min-height:35mm}
      .device-detail-photo img{display:block;width:100%;height:48mm;object-fit:contain;background:#fff}
      .device-detail-photo .badge{position:absolute;left:2mm;bottom:2mm;background:#fff}
      .timeline-service-photos{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:3mm;margin-top:3mm}
      .timeline-service-photo{display:block;width:100%!important;height:48mm!important;object-fit:contain!important;background:#fff;border:1px solid #ccc;border-radius:2mm;break-inside:avoid}
      @media print{body{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
    </style></head><body><div class="print-head"><div><h1>Machinepark</h1><div class="subtitle">Toesteldetails · ${esc(label)}</div></div><div class="print-date">Afgedrukt ${new Date().toLocaleString('nl-BE')}</div></div><main>${clone.innerHTML}</main>`);
    popup.document.close();

    await waitForPrintImages(popup.document);
    await new Promise((resolve) => setTimeout(resolve, 120));
    popup.focus();
    popup.onafterprint = () => popup.close();
    popup.print();
  };

  const baseShowDeviceHistoryForPrint = showDeviceHistory;
  showDeviceHistory = function(id) {
    baseShowDeviceHistoryForPrint(id);
    setTimeout(() => {
      if (!canPrintDeviceDetails()) return;
      const foot = document.querySelector('#modal .modal-foot');
      if (!foot || document.getElementById('printDeviceDetails')) return;
      const button = document.createElement('button');
      button.type = 'button';
      button.id = 'printDeviceDetails';
      button.className = 'btn';
      button.dataset.devicePrintId = id;
      button.textContent = '🖨 Afdrukken';
      button.onclick = () => window.printDeviceDetails(id);
      foot.insertBefore(button, foot.firstChild);
    }, 30);
  };
  window.showDeviceHistory = showDeviceHistory;
})();
} catch (error) {
  console.error('[Machinepark feature print-device-details-v2]', error);
}

/* photo-lightbox-v2 */
try {
(() => {
  function ensurePhotoLightbox() {
    let box = document.getElementById('devicePhotoLightbox');
    if (box) return box;
    box = document.createElement('div');
    box.id = 'devicePhotoLightbox';
    box.className = 'device-photo-lightbox';
    box.setAttribute('aria-hidden', 'true');
    box.innerHTML = `<div class="device-photo-lightbox-inner" role="dialog" aria-modal="true" aria-label="Vergrote foto">
      <img alt="Vergrote foto">
      <div class="device-photo-lightbox-caption"></div>
      <button type="button" class="device-photo-lightbox-close" aria-label="Foto sluiten">×</button>
    </div>`;
    document.body.appendChild(box);

    const close = () => {
      box.classList.remove('show');
      box.setAttribute('aria-hidden', 'true');
      const img = box.querySelector('img');
      if (img) img.removeAttribute('src');
    };
    box.querySelector('.device-photo-lightbox-close').onclick = close;
    box.addEventListener('click', (event) => {
      if (event.target === box) close();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && box.classList.contains('show')) close();
    });
    return box;
  }

  function openPhotoLightbox(img) {
    if (!img) return;
    const src = img.dataset.fullSrc || img.currentSrc || img.src;
    if (!src) return;
    const box = ensurePhotoLightbox();
    const large = box.querySelector('img');
    const caption = box.querySelector('.device-photo-lightbox-caption');
    large.src = src;
    large.alt = img.alt || 'Vergrote foto';
    const badge = img.closest('.device-detail-photo')?.querySelector('.badge')?.textContent?.trim();
    caption.textContent = badge || img.alt || 'Foto';
    caption.style.display = caption.textContent ? '' : 'none';
    box.classList.add('show');
    box.setAttribute('aria-hidden', 'false');
    box.querySelector('.device-photo-lightbox-close')?.focus();
  }
  window.machineparkOpenPhotoLightbox = openPhotoLightbox;

  document.addEventListener('click', (event) => {
    const img = event.target.closest('img[data-photo-lightbox]');
    if (!img) return;
    event.preventDefault();
    event.stopPropagation();
    openPhotoLightbox(img);
  });
})();
} catch (error) {
  console.error('[Machinepark feature photo-lightbox-v2]', error);
}

/* photo-storage-optimization-v3 */
try {
(() => {
  const DEVICE_PHOTO_URL = '/machinepark/synology/api/device-photos.php';
  const PART_PHOTO_URL = '/machinepark/synology/api/part-photos.php';
  const SERVICE_PHOTO_URL = '/machinepark/synology/api/service-photos.php';
  const LEGACY_MIGRATION_KEY = 'machinepark-photo-thumbnails-v2';
  let photoSaveBusy = 0;
  let migrationTimer = null;

  function ownPhotoEndpoint(src) {
    const value = String(src || '');
    if (value.includes('/machinepark/synology/api/device-photos.php?')) return DEVICE_PHOTO_URL;
    if (value.includes('/machinepark/synology/api/part-photos.php?')) return PART_PHOTO_URL;
    if (value.includes('/machinepark/synology/api/service-photos.php?')) return SERVICE_PHOTO_URL;
    return '';
  }

  window.machineparkThumbnailRef = function(src) {
    const value = String(src || '').trim();
    const normalized = value
      .replace(/^\.\/synology\/api\//, '/machinepark/synology/api/')
      .replace(/^synology\/api\//, '/machinepark/synology/api/');
    if (!value || !ownPhotoEndpoint(normalized)) return value;
    try {
      const url = new URL(normalized, location.origin);
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

  function canManageServicePhotosClient(storeName) {
    if (window.machineparkAccessReady && typeof window.machineparkHasPermission === 'function') {
      const prefix = storeName === 'maintenance' ? 'maintenance' : 'breakdowns';
      return window.machineparkHasPermission(`${prefix}.edit`) || window.machineparkHasPermission(`${prefix}.add`);
    }
    return true;
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

  async function apiPost(url, body, errorLabel) {
    const headers = await centralHeaders(true);
    const res = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body), cache: 'no-store', credentials: 'same-origin' });
    const text = await res.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch (_) {}
    if (!res.ok) { const raw=String(data.error || text || errorLabel || 'Foto-aanvraag mislukt'); const clean=raw.replace(/<script[\s\S]*?<\/script>/gi,' ').replace(/<style[\s\S]*?<\/style>/gi,' ').replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim().slice(0,180); const message=errorLabel+' · HTTP '+res.status+(clean?' · '+clean:''); const error=new Error(message); error.status=res.status; error.endpoint=res.url||String(url||''); window.machineparkLastPhotoError={at:new Date().toISOString(),status:res.status,endpoint:error.endpoint,message}; throw error; } window.machineparkLastPhotoError=null;
    return data;
  }

  window.machineparkPersistDevicePhotoList = async function(deviceId, photos, { force = false } = {}) {
    const list = (Array.isArray(photos) ? photos : []).filter((src) => typeof src === 'string' && src.trim()).slice(0, 5);
    if (!force && !list.some(isRawPhoto)) return list;
    const rawIndexes = list.map((src, index) => isRawPhoto(src) ? index : -1).filter((index) => index >= 0);
    photoSaveBusy += 1;
    try {
      const body = await apiPost(DEVICE_PHOTO_URL, { deviceId, photos: list }, 'Toestelfoto’s opslaan mislukt');
      const refs = Array.isArray(body.photos) ? body.photos.slice(0, 5) : list;
      rawIndexes.forEach((index) => {
        const ref = refs[index];
        if (ref) afterUserWork(() => ensureStoredThumbnail('device', deviceId, ref), 1800 + index * 250);
      });
      return refs;
    } finally {
      photoSaveBusy = Math.max(0, photoSaveBusy - 1);
    }
  };

  window.machineparkPersistPartPhoto = async function(partId, photo) {
    const value = String(photo || '').trim();
    if (!value) return '';
    if (value.includes('/machinepark/synology/api/part-photos.php?') || value.includes('/machinepark/synology/api/part-photos.php?')) return value;
    if (!isRawPhoto(value)) return value;
    photoSaveBusy += 1;
    try {
      const body = await apiPost(PART_PHOTO_URL, { partId, photo: value }, 'Onderdeelfoto opslaan mislukt');
      const ref = String(body.photo || value);
      if (ref) afterUserWork(() => ensureStoredThumbnail('part', partId, ref), 1800);
      return ref;
    } finally {
      photoSaveBusy = Math.max(0, photoSaveBusy - 1);
    }
  };

  window.machineparkPersistServicePhotos = async function(storeName, entityId, photos) {
    const list = (Array.isArray(photos) ? photos : []).filter((src) => typeof src === 'string' && src.trim()).slice(0, 5);
    const rawIndexes = list.map((src, index) => isRawPhoto(src) ? index : -1).filter((index) => index >= 0);
    photoSaveBusy += 1;
    try {
      const body = await apiPost(SERVICE_PHOTO_URL, { storeName, entityId, photos: list }, 'Verslagfoto’s opslaan mislukt');
      const refs = Array.isArray(body.photos) ? body.photos.slice(0, 5) : list;
      rawIndexes.forEach((index) => {
        const ref = refs[index];
        if (ref) afterUserWork(() => ensureStoredThumbnail('service', entityId, ref, storeName), 1800 + index * 250);
      });
      return refs;
    } finally {
      photoSaveBusy = Math.max(0, photoSaveBusy - 1);
    }
  };

  function writeStoreDirect(storeName, item) {
    return new Promise((resolve, reject) => {
      const tr = db.transaction(storeName, 'readwrite');
      const request = tr.objectStore(storeName).put(item);
      request.onerror = () => reject(request.error);
      tr.oncomplete = () => resolve(item);
      tr.onerror = () => reject(tr.error);
      tr.onabort = () => reject(tr.error || new Error('Lokale fotomigratie afgebroken'));
    });
  }

  async function ensureStoredThumbnail(kind, id, photoRef, storeName = '') {
    let endpoint = '';
    let body = null;
    if (kind === 'device') {
      endpoint = DEVICE_PHOTO_URL;
      body = { action: 'thumbnail', deviceId: id, photoRef };
    } else if (kind === 'part') {
      endpoint = PART_PHOTO_URL;
      body = { action: 'thumbnail', partId: id, photoRef };
    } else if (kind === 'service') {
      endpoint = SERVICE_PHOTO_URL;
      body = { action: 'thumbnail', storeName, entityId: id, photoRef };
    }
    if (!endpoint || !String(photoRef || '').includes(endpoint + '?')) return false;
    const thumb = window.machineparkThumbnailRef(photoRef);
    try {
      const probe = await fetch(thumb, { method: 'HEAD', cache: 'no-store' });
      if (probe.ok) return true;
      body.thumbnail = await thumbnailDataFromSource(photoRef);
      await apiPost(endpoint, body, 'Thumbnail opslaan mislukt');
      return true;
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
        await writeStoreDirect('parts', part);
        migrated += 1;
        await new Promise((resolve) => setTimeout(resolve, 80));
      } catch (error) {
        console.warn('Bestaande onderdeelfoto kon niet worden gemigreerd', part?.artNr, error);
      }
    }
    return migrated;
  }

  async function migrateExistingServicePhotos(storeName) {
    const list = Array.isArray(state?.[storeName]) ? state[storeName] : [];
    if (window.machineparkServiceBlobWritesEnabled === false || photoSaveBusy > 0 || !canManageServicePhotosClient(storeName) || !list.length) return 0;
    let migrated = 0;
    for (const record of list) {
      if (photoSaveBusy > 0) break;
      const photos = Array.isArray(record?.photos) ? record.photos.filter(Boolean).slice(0, 5) : [];
      if (!photos.some(isRawPhoto)) continue;
      try {
        record.photos = await window.machineparkPersistServicePhotos(storeName, record.id, photos);
        await writeStoreDirect(storeName, record);
        migrated += 1;
        await new Promise((resolve) => setTimeout(resolve, 80));
      } catch (error) {
        console.warn('Bestaande verslagfoto kon niet worden gemigreerd', storeName, record?.id, error);
      }
    }
    return migrated;
  }

  async function optimizeExistingThumbnailLibrary() {
    if (photoSaveBusy > 0 || document.visibilityState !== 'visible') return false;
    const migratedParts = await migrateExistingPartPhotos();
    const migratedMaintenance = await migrateExistingServicePhotos('maintenance');
    const migratedBreakdowns = await migrateExistingServicePhotos('breakdowns');
    const migrated = migratedParts + migratedMaintenance + migratedBreakdowns;

    if (migrated && photoSaveBusy === 0) {
      try {
        renderParts?.();
        renderMaintenance?.();
        renderBreakdowns?.();
      } catch (_) {}
      try {
        if (centralSync?.enabled) {
          centralSync.pending = true;
          await centralPush();
        }
      } catch (error) {
        console.warn('Centrale opslag na fotomigratie', error);
      }
    }

    let optimized = 0;
    const shouldScanLegacy = localStorage.getItem(LEGACY_MIGRATION_KEY) !== 'done';
    if (shouldScanLegacy && photoSaveBusy === 0) {
      for (const device of (Array.isArray(state?.devices) ? state.devices : [])) {
        if (photoSaveBusy > 0) break;
        for (const photo of (Array.isArray(device?.devicePhotos) ? device.devicePhotos : []).slice(0, 5)) {
          if (photoSaveBusy > 0) break;
          if (await ensureStoredThumbnail('device', device.id, photo)) optimized += 1;
          await new Promise((resolve) => setTimeout(resolve, 60));
        }
      }
      for (const part of (Array.isArray(state?.parts) ? state.parts : [])) {
        if (photoSaveBusy > 0) break;
        if (part?.photo && await ensureStoredThumbnail('part', part.id, part.photo)) optimized += 1;
        await new Promise((resolve) => setTimeout(resolve, 60));
      }
      for (const storeName of ['maintenance', 'breakdowns']) {
        for (const record of (Array.isArray(state?.[storeName]) ? state[storeName] : [])) {
          if (photoSaveBusy > 0) break;
          for (const photo of (Array.isArray(record?.photos) ? record.photos : []).slice(0, 5)) {
            if (photoSaveBusy > 0) break;
            if (await ensureStoredThumbnail('service', record.id, photo, storeName)) optimized += 1;
            await new Promise((resolve) => setTimeout(resolve, 60));
          }
        }
      }
      if (photoSaveBusy === 0) localStorage.setItem(LEGACY_MIGRATION_KEY, 'done');
    }

    if (migrated || optimized) {
      console.info(`[Machinepark] foto-optimalisatie: ${migratedParts} onderdelen, ${migratedMaintenance} onderhoud, ${migratedBreakdowns} depannages gemigreerd; ${optimized} thumbnails gecontroleerd`);
    }
    return true;
  }

  function scheduleLibraryOptimization(delay = 12000) {
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
} catch (error) {
  console.error('[Machinepark feature photo-storage-optimization-v3]', error);
}

/* mail-pdf-v1 */
try {
(() => {
  const HTML2PDF_SRC = './vendor/html2pdf.bundle.min.js';
  let html2PdfPromise = null;

  function notifyPdf(message) {
    if (typeof toast === 'function') toast(message);
    else alert(message);
  }

  function cleanPdfText(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
  }

  function safePdfFilename(value) {
    return cleanPdfText(value || 'Machinepark')
      .replace(/[\\/:*?"<>|]+/g, '-')
      .replace(/\s+/g, '_')
      .replace(/_+/g, '_')
      .replace(/^[_-]+|[_-]+$/g, '')
      .slice(0, 110) || 'Machinepark';
  }

  function loadHtml2Pdf() {
    if (typeof window.html2pdf === 'function') return Promise.resolve(window.html2pdf);
    if (html2PdfPromise) return html2PdfPromise;

    html2PdfPromise = new Promise((resolve, reject) => {
      let script = document.getElementById('machineparkHtml2PdfScript');
      const ready = () => {
        if (typeof window.html2pdf === 'function') resolve(window.html2pdf);
        else reject(new Error('PDF-bibliotheek is niet beschikbaar.'));
      };
      const failed = () => reject(new Error('PDF-bibliotheek kon niet worden geladen. Controleer je internetverbinding.'));

      if (script) {
        if (script.dataset.loaded === '1') ready();
        else {
          script.addEventListener('load', ready, { once: true });
          script.addEventListener('error', failed, { once: true });
        }
        return;
      }

      script = document.createElement('script');
      script.id = 'machineparkHtml2PdfScript';
      script.src = HTML2PDF_SRC;
      script.async = true;
      script.crossOrigin = 'anonymous';
      script.addEventListener('load', () => {
        script.dataset.loaded = '1';
        ready();
      }, { once: true });
      script.addEventListener('error', failed, { once: true });
      document.head.appendChild(script);
    }).catch((error) => {
      html2PdfPromise = null;
      throw error;
    });

    return html2PdfPromise;
  }

  function activePageLabel(view) {
    const labels = {
      dashboard: 'Dashboard',
      devices: 'Toestellen',
      maintenance: 'Onderhoud',
      breakdowns: 'Depannages',
      parts: 'Onderdelen',
      settings: 'Beheer'
    };
    const key = String(view?.id || '').replace(/^view-/, '');
    return labels[key] || cleanPdfText(document.getElementById('pageTitle')?.textContent) || 'Machinepark';
  }

  function modalLabel() {
    const page = cleanPdfText(document.getElementById('pageTitle')?.textContent);
    const heading = cleanPdfText(
      document.querySelector('#modal .modal-title, #modal .modal-head h1, #modal .modal-head h2, #modal .modal-head h3')?.textContent
    );
    if (page && heading && !heading.toLowerCase().includes(page.toLowerCase())) return `${page} · ${heading}`;
    return heading || page || 'Machinepark';
  }

  function pdfContext(button) {
    const row = button.closest('.page-print-row');
    if (row) {
      const view = button.closest('.view');
      if (!view) return null;
      return { source: view, title: activePageLabel(view), kind: 'page' };
    }

    const body = document.querySelector('#modal .modal-body');
    if (!body) return null;
    return { source: body, title: modalLabel(), kind: 'modal' };
  }

  function syncFormValues(source, clone) {
    const sourceFields = [...source.querySelectorAll('input,textarea,select')];
    const cloneFields = [...clone.querySelectorAll('input,textarea,select')];
    sourceFields.forEach((field, index) => {
      const target = cloneFields[index];
      if (!target) return;
      if (target instanceof HTMLInputElement) {
        target.value = field.value;
        target.checked = field.checked;
      } else if (target instanceof HTMLTextAreaElement) {
        target.value = field.value;
        target.textContent = field.value;
      } else if (target instanceof HTMLSelectElement) {
        target.value = field.value;
      }
    });
  }

  function preparePdfStage(context) {
    const clone = context.source.cloneNode(true);
    syncFormValues(context.source, clone);
    clone.style.display = 'block';
    clone.classList.add('machinepark-pdf-content');
    clone.querySelectorAll('.page-print-row,.toolbar,.modal-foot,button,input[type="file"],.device-photo-remove,.device-photo-overview').forEach(el => el.remove());
    clone.querySelectorAll('img').forEach((img) => {
      try { img.setAttribute('src', img.src); } catch (_) {}
      img.removeAttribute('loading');
    });

    const stage = document.createElement('section');
    stage.className = 'machinepark-pdf-stage';
    stage.setAttribute('aria-hidden', 'true');

    const head = document.createElement('div');
    head.className = 'machinepark-pdf-head';
    const headLeft = document.createElement('div');
    const h1 = document.createElement('h1');
    h1.textContent = 'Machinepark';
    const subtitle = document.createElement('div');
    subtitle.className = 'machinepark-pdf-subtitle';
    subtitle.textContent = context.title;
    headLeft.append(h1, subtitle);
    const date = document.createElement('div');
    date.className = 'machinepark-pdf-date';
    date.textContent = new Date().toLocaleString('nl-BE');
    head.append(headLeft, date);
    stage.append(head, clone);
    document.body.appendChild(stage);
    return stage;
  }

  async function waitForPdfImages(root) {
    const images = [...root.querySelectorAll('img')];
    if (!images.length) return;
    await Promise.all(images.map((img) => {
      if (img.complete) return Promise.resolve();
      return new Promise((resolve) => {
        const done = () => resolve();
        img.addEventListener('load', done, { once: true });
        img.addEventListener('error', done, { once: true });
        setTimeout(done, 3500);
      });
    }));
  }

  async function createPdfFile(context) {
    const html2pdf = await loadHtml2Pdf();
    const stage = preparePdfStage(context);
    const stamp = new Date().toISOString().slice(0, 10);
    const filename = `${safePdfFilename(`Machinepark_${context.title}_${stamp}`)}.pdf`;
    try {
      await waitForPdfImages(stage);
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const worker = html2pdf().set({
        margin: [10, 10, 12, 10],
        filename,
        image: { type: 'jpeg', quality: 0.94 },
        html2canvas: {
          scale: 1.55,
          useCORS: true,
          backgroundColor: '#ffffff',
          logging: false,
          scrollX: 0,
          scrollY: 0,
          onclone: (clonedDoc) => {
            const clonedStage = clonedDoc.querySelector('.machinepark-pdf-stage');
            if (!clonedStage) return;
            clonedStage.style.position = 'static';
            clonedStage.style.left = '0';
            clonedStage.style.top = '0';
            clonedStage.style.zIndex = 'auto';
            clonedStage.style.transform = 'none';
            clonedStage.style.visibility = 'visible';
          }
        },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak: { mode: ['css', 'legacy'] }
      }).from(stage).toPdf();
      const blob = await worker.outputPdf('blob');
      return new File([blob], filename, { type: 'application/pdf', lastModified: Date.now() });
    } finally {
      stage.remove();
    }
  }

  function downloadPdfFile(file) {
    const url = URL.createObjectURL(file);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = file.name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }

  async function sharePdfThroughOwnMail(file, title) {
    const subject = `Machinepark - ${title}`;
    const text = `In bijlage vind je de PDF uit Machinepark: ${title}.`;
    const shareData = { files: [file], title: subject, text };
    const canFileShare = typeof navigator.share === 'function'
      && (typeof navigator.canShare !== 'function' || navigator.canShare(shareData));

    if (canFileShare) {
      try {
        await navigator.share(shareData);
        return;
      } catch (error) {
        if (error?.name === 'AbortError') return;
        console.warn('[Machinepark] PDF delen via systeemmenu mislukt, fallback naar mailto', error);
      }
    }

    downloadPdfFile(file);
    const body = `${text}\n\nDe PDF is op je toestel gedownload. Voeg het bestand ${file.name} toe als bijlage.`;
    const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    notifyPdf('PDF gedownload. Je mailprogramma wordt geopend; voeg de gedownloade PDF toe als bijlage.');
    setTimeout(() => { window.location.href = mailto; }, 120);
  }

  async function mailPdf(button) {
    if (button.dataset.pdfBusy === '1') return;
    const context = pdfContext(button);
    if (!context) {
      notifyPdf('Er is geen afdrukbare inhoud gevonden.');
      return;
    }

    const originalText = button.textContent;
    button.dataset.pdfBusy = '1';
    button.disabled = true;
    button.textContent = 'PDF maken…';
    try {
      const file = await createPdfFile(context);
      button.textContent = 'Mail openen…';
      await sharePdfThroughOwnMail(file, context.title);
    } catch (error) {
      console.error('[Machinepark] Mail PDF mislukt', error);
      notifyPdf(error?.message || 'De PDF kon niet worden gemaakt.');
    } finally {
      button.disabled = false;
      button.dataset.pdfBusy = '0';
      button.textContent = originalText;
    }
  }

  function makeMailButton(className) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `btn ${className}`;
    button.textContent = '✉ Mail PDF';
    button.setAttribute('aria-label', 'Als PDF delen via je eigen mailprogramma');
    button.addEventListener('click', () => mailPdf(button));
    return button;
  }

  function syncMailButtons() {
    document.querySelectorAll('.page-print-row').forEach((row) => {
      const print = row.querySelector('.page-print-btn');
      if (!print || row.querySelector('.page-mail-btn')) return;
      print.insertAdjacentElement('afterend', makeMailButton('page-mail-btn'));
    });

    document.querySelectorAll('.service-detail-print-btn').forEach((print) => {
      const foot = print.closest('.modal-foot') || print.parentElement;
      if (!foot || foot.querySelector('.service-detail-mail-btn')) return;
      print.insertAdjacentElement('afterend', makeMailButton('service-detail-mail-btn'));
    });

    const devicePrint = document.getElementById('printDeviceDetails');
    if (devicePrint) {
      const foot = devicePrint.closest('.modal-foot') || devicePrint.parentElement;
      if (foot && !foot.querySelector('.device-detail-mail-btn')) {
        devicePrint.insertAdjacentElement('afterend', makeMailButton('device-detail-mail-btn'));
      }
    }
  }

  let syncQueued = false;
  function queueMailButtonSync() {
    if (syncQueued) return;
    syncQueued = true;
    queueMicrotask(() => {
      syncQueued = false;
      syncMailButtons();
    });
  }

  const observer = new MutationObserver(queueMailButtonSync);
  observer.observe(document.body, { childList: true, subtree: true });
  syncMailButtons();

  window.machineparkMailPdf = mailPdf;
})();
} catch (error) {
  console.error('[Machinepark feature mail-pdf-v1]', error);
}

/* mail-pdf-direct-v4 */
try {
(() => {
  const JSPDF_SRC = './vendor/jspdf.umd.min.js';
  const MAIL_SELECTOR = '.page-mail-btn,.service-detail-mail-btn,.device-detail-mail-btn,.service-visit-mail-btn';
  const PAGE_BOTTOM = 282;
  let jsPdfPromise = null;

  function cleanText(value) {
    return String(value ?? '')
      .replace(/\u00a0/g, ' ')
      .replace(/[\t\r ]+/g, ' ')
      .replace(/\n\s+/g, '\n')
      .trim();
  }

  function pdfSafeText(value) {
    return cleanText(value)
      .replace(/[–—]/g, '-')
      .replace(/[‘’]/g, "'")
      .replace(/[“”]/g, '"')
      .replace(/[·•]/g, '.')
      .replace(/[×✕✖]/g, 'x')
      .replace(/…/g, '...')
      .replace(/[\u2009\u202f]/g, ' ');
  }

  function safeFilename(value) {
    return cleanText(value || 'Machinepark')
      .replace(/[\\/:*?"<>|]+/g, '-')
      .replace(/\s+/g, '_')
      .replace(/_+/g, '_')
      .replace(/^[_-]+|[_-]+$/g, '')
      .slice(0, 110) || 'Machinepark';
  }

  function notify(message) {
    if (typeof toast === 'function') toast(message);
    else alert(message);
  }

  function withTimeout(promise, ms, message) {
    let timer;
    const timeout = new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(message)), ms);
    });
    return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
  }

  function loadJsPdf() {
    if (window.jspdf?.jsPDF) return Promise.resolve(window.jspdf.jsPDF);
    if (jsPdfPromise) return jsPdfPromise;
    jsPdfPromise = withTimeout(new Promise((resolve, reject) => {
      let script = document.getElementById('machineparkJsPdfScript');
      const ready = () => window.jspdf?.jsPDF ? resolve(window.jspdf.jsPDF) : reject(new Error('PDF-bibliotheek is niet beschikbaar.'));
      const failed = () => reject(new Error('PDF-bibliotheek kon niet worden geladen. Controleer je internetverbinding.'));
      if (script) {
        if (script.dataset.loaded === '1') ready();
        else {
          script.addEventListener('load', ready, { once: true });
          script.addEventListener('error', failed, { once: true });
        }
        return;
      }
      script = document.createElement('script');
      script.id = 'machineparkJsPdfScript';
      script.src = JSPDF_SRC;
      script.async = true;
      script.crossOrigin = 'anonymous';
      script.addEventListener('load', () => { script.dataset.loaded = '1'; ready(); }, { once: true });
      script.addEventListener('error', failed, { once: true });
      document.head.appendChild(script);
    }), 12000, 'PDF-bibliotheek reageert niet. Probeer opnieuw.').catch((error) => {
      jsPdfPromise = null;
      throw error;
    });
    return jsPdfPromise;
  }

  function activePageTitle(view) {
    const labels = { dashboard:'Dashboard', devices:'Toestellen', maintenance:'Onderhoud', breakdowns:'Depannages', parts:'Onderdelen', faults:'Storingen', manuals:'Handleidingen', settings:'Beheer' };
    const key = String(view?.id || '').replace(/^view-/, '');
    return labels[key] || cleanText(document.getElementById('pageTitle')?.textContent) || 'Machinepark';
  }

  function getContext(button) {
    const row = button.closest('.page-print-row');
    if (row) {
      const view = button.closest('.view');
      return view ? { source:view, title:activePageTitle(view), kind:'page' } : null;
    }
    const body = document.querySelector('#modal .modal-body');
    if (!body) return null;
    if (button.matches('.service-visit-mail-btn')) {
      const recordId = button.dataset.serviceVisitMailId || '';
      return { source:body, kind:'serviceVisit', recordId, title:`Serviceverslag ${button.dataset.serviceVisitLabel || recordId}` };
    }
    const foot = button.closest('.modal-foot') || document.querySelector('#modal .modal-foot');
    const servicePrint = foot?.querySelector('.service-detail-print-btn[data-service-print-id]');
    if (servicePrint) {
      return {
        source: body,
        kind: 'service',
        serviceKind: servicePrint.dataset.servicePrintKind || 'breakdowns',
        recordId: servicePrint.dataset.servicePrintId || ''
      };
    }
    const devicePrint = foot?.querySelector('#printDeviceDetails[data-device-print-id]');
    if (devicePrint) return { source:body, kind:'device', recordId:devicePrint.dataset.devicePrintId || '' };
    const heading = cleanText(document.querySelector('#modal .modal-head h3')?.textContent) || 'Machinepark';
    return { source:body, title:heading, kind:'modal' };
  }

  function serviceDevice(record) {
    try { return deviceName(record.deviceId, recordMoment(record)) || '—'; }
    catch (_) {
      const device = state.devices.find(item => item.id === record?.deviceId);
      return [device?.assetCode, device?.brand, device?.model].filter(Boolean).join(' · ') || '—';
    }
  }

  function serviceDate(record) {
    if (!record?.date) return '—';
    const date = new Date(`${record.date}T00:00:00`);
    return Number.isNaN(date.getTime()) ? String(record.date) : date.toLocaleDateString('nl-BE');
  }

  function serviceParts(record, multiline = false) {
    const parts = Array.isArray(record?.usedParts) ? record.usedParts.filter(Boolean) : [];
    if (!parts.length) return '—';
    if (!multiline) {
      try { return usedPartsText(parts) || '—'; } catch (_) { return '—'; }
    }
    const lines = parts.map(part => {
      try { return usedPartsText([part]) || ''; } catch (_) { return ''; }
    }).map(cleanText).filter(Boolean);
    return lines.length ? lines.join('\n') : '—';
  }

  function serviceOneOffParts(record) {
    const items = Array.isArray(record?.oneOffParts) ? record.oneOffParts : [];
    const lines = items.map(item => {
      const qty = Math.max(0.001, normalizePartQuantity(item?.qty, 1));
      const text = [
        cleanText(item?.supplier),
        cleanText(item?.supplierCode),
        cleanText(item?.description)
      ].filter(Boolean).join(' . ');
      return text ? `${formatPartQuantity(qty)} x ${text}` : '';
    }).filter(Boolean);
    return lines.length ? lines.join('\n') : '—';
  }

  function serviceLocation(record) {
    const device = (state.devices || []).find(item => item.id === record?.deviceId);
    try {
      if (device && typeof deviceLocationAt === 'function') return deviceLocationAt(device, recordMoment(record)) || device.location || record?.serviceVisitLocation || '—';
    } catch (_) {}
    return device?.location || record?.serviceVisitLocation || '—';
  }

  function servicePartRows(record) {
    const rows = [];
    (record?.usedParts || []).forEach(usage => {
      const qty = Number(usage?.qty || 0);
      if (!usage?.partId || qty <= 0) return;
      const part = (state.parts || []).find(item => item.id === usage.partId);
      rows.push({
        code:cleanText(part?.artNr || usage.partId || '—') || '—',
        description:cleanText(part?.description || ''),
        qty,
        oneOff:false
      });
    });
    (record?.oneOffParts || []).forEach(part => {
      const supplier=cleanText(part?.supplier),supplierCode=cleanText(part?.supplierCode),description=cleanText(part?.description);
      if (!(supplier || supplierCode || description)) return;
      rows.push({
        code:supplierCode || supplier || 'Eenmalig',
        description:[supplierCode && supplier ? supplier : '', description].filter(Boolean).join(' . '),
        qty:Math.max(0.001,normalizePartQuantity(part?.qty,1)),
        oneOff:true
      });
    });
    return rows;
  }

  function serviceWorkSummary(kind, record) {
    const sessions = Array.isArray(record?.workSessions) ? record.workSessions : [];
    const sessionMinutes = sessions.reduce((sum, row) => sum + Math.max(0, Math.round(Number(row?.minutes) || 0)), 0);
    if (record?.serviceVisitId) {
      const reportSessions = Array.isArray(record?.serviceReportWorkSessions) && record.serviceReportWorkSessions.length ? record.serviceReportWorkSessions : sessions;
      const reportMinutes = reportSessions.reduce((sum, row) => sum + Math.max(0, Math.round(Number(row?.minutes) || 0)), 0);
      const minutes = Math.max(0, Math.round(Number(record?.serviceReportTotalMinutes) || reportMinutes || Number(record?.hours || 0) * 60));
      const linked = [...(state.maintenance || []), ...(state.breakdowns || [])].filter(item => (item?.serviceReportId || item?.serviceVisitId) === (record?.serviceReportId || record?.serviceVisitId));
      const unique = new Set(linked.map(item => item?.deviceId).filter(Boolean)).size;
      const count = Math.max(1, unique || Math.round(Number(record?.serviceReportDeviceCount || record?.serviceVisitDeviceCount || record?.batchSize) || 1));
      return `${minutes} min / ${count} toestel${count === 1 ? '' : 'len'}`;
    }
    const minutes = sessionMinutes || Math.max(0, Math.round(Number(record?.hours || 0) * 60));
    const collection = kind === 'maintenance' ? state.maintenance : state.breakdowns;
    let count = Math.max(1, Math.round(Number(record?.batchSize) || 1));
    if (record?.batchId && Array.isArray(collection)) {
      const grouped = collection.filter(item => item?.batchId === record.batchId).length;
      if (grouped > 0) count = grouped;
    }
    return `${minutes} min / ${count} toestel${count === 1 ? '' : 'len'}`;
  }

  function servicePhotos(record) {
    return (Array.isArray(record?.photos) ? record.photos : [])
      .filter(src => typeof src === 'string' && src.trim());
  }

  function serviceModel(context) {
    const list = context.serviceKind === 'maintenance' ? state.maintenance : state.breakdowns;
    const record = list.find(item => item.id === context.recordId);
    if (!record) return null;
    const maintenance = context.serviceKind === 'maintenance';
    const other = !maintenance && record?.serviceKind === 'other';
    const kind = maintenance ? 'maintenance' : (other ? 'otherworks' : 'breakdowns');
    const kindLabel = maintenance ? 'Onderhoud' : (other ? (record.workTypeName || 'Andere werken') : 'Depannage');
    const title = maintenance ? 'Onderhoudsverslag' : (other ? `${kindLabel} · verslag` : 'Depannageverslag');
    const oneOff = serviceOneOffParts(record);
    const summary = maintenance ? serviceWorkSummary('maintenance', record) : serviceWorkSummary('breakdowns', record);
    const summaryLabel = record?.serviceVisitId ? 'Servicetijd volledig verslag / toestellen' : 'Datum / werkminuten';
    const summaryValue = record?.serviceVisitId ? summary : `${serviceDate(record)} · ${summary}`;
    const detailLines = maintenance
      ? [`Type onderhoud: ${record.type || '—'}`, `Uitgevoerde werkzaamheden / notitie: ${record.notes || '—'}`]
      : other
        ? [`Prioriteit: ${record.priority || '—'} · Status: ${record.status || '—'}`, `Werkzaamheid / omschrijving: ${record.issue || '—'}`, `Extra info / diagnose: ${record.diagnosis || '—'}`, `Oplossing / uitgevoerde werken: ${record.solution || '—'}`]
        : [`Prioriteit: ${record.priority || '—'} · Status: ${record.status || '—'}`, `Probleem / melding: ${record.issue || '—'}`, `Diagnose: ${record.diagnosis || '—'}`, `Oplossing / uitgevoerde werken: ${record.solution || '—'}`];
    const fields = maintenance ? [
      { label:'Datum', value:serviceDate(record) },
      { label:'Type onderhoud', value:record.type || '—' },
      { label:'Toestel', value:serviceDevice(record), full:true },
      { label:'Technieker', value:record.technician || '—' },
      { label:record?.serviceVisitId?'Servicetijd volledig verslag / toestellen':'Werkminuten / toestellen', value:summary },
      { label:'Gebruikte onderdelen', value:serviceParts(record, true), full:true },
      ...(oneOff !== '—' ? [{ label:'Eenmalige onderdelen', value:oneOff, full:true }] : []),
      { label:'Uitgevoerde werkzaamheden / notitie', value:record.notes || '—', full:true },
    ] : [
      { label:'Datum', value:serviceDate(record) },
      { label:'Toestel', value:serviceDevice(record) },
      { label:'Prioriteit', value:record.priority || '—' },
      { label:'Status', value:record.status || '—' },
      { label:'Technieker', value:record.technician || '—' },
      { label:record?.serviceVisitId?'Servicetijd volledig verslag / toestellen':'Werkminuten / toestellen', value:summary },
      { label:'Probleem / melding', value:record.issue || '—', full:true },
      { label:'Diagnose', value:record.diagnosis || '—', full:true },
      { label:'Oplossing / uitgevoerde werken', value:record.solution || '—', full:true },
      { label:'Gebruikte onderdelen', value:serviceParts(record, true), full:true },
      ...(oneOff !== '—' ? [{ label:'Eenmalige onderdelen', value:oneOff, full:true }] : []),
    ];
    const photos = servicePhotos(record);
    const page = {
      index:1,
      documentLabel:'WERKVERSLAG',
      sectionLabel:'WERKZAAMHEID',
      kind,
      kindLabel,
      device:serviceDevice(record),
      location:serviceLocation(record),
      technician:record.technician || '—',
      meta:[
        {label:'Locatie',value:serviceLocation(record)},
        {label:summaryLabel,value:summaryValue},
        {label:'Technieker',value:record.technician || '—'}
      ],
      detailLines,
      parts:servicePartRows(record),
      photos
    };
    return {
      headerTitle: `Machinepark . ${title}`,
      subtitle: serviceDevice(record),
      rightText: serviceDate(record),
      filenameTitle: title,
      fields,
      photos,
      photoTitle: 'Foto’s bij verslag',
      photoColumns: 2,
      photoMaxHeight: 105,
      timelines: [],
      workPrintLayout:{reportLabel:title,page}
    };
  }

  function fieldValueFromNode(node) {
    const clone = node.cloneNode(true);
    clone.querySelectorAll('label,button,img,input[type="file"],.device-photo-remove,.device-photo-overview,.manual-device-section').forEach(el => el.remove());
    const originalFields = [...node.querySelectorAll('input,textarea,select')];
    const cloneFields = [...clone.querySelectorAll('input,textarea,select')];
    cloneFields.forEach((field, index) => {
      const original = originalFields[index] || field;
      let value = original.value || '';
      if (original instanceof HTMLSelectElement) value = original.selectedOptions?.[0]?.textContent || original.value || '';
      if (original instanceof HTMLInputElement && (original.type === 'checkbox' || original.type === 'radio')) value = original.checked ? (original.value || 'Ja') : '';
      field.replaceWith(document.createTextNode(value));
    });
    return cleanText(clone.textContent) || '—';
  }

  function deviceModel(context) {
    const device = state.devices.find(item => item.id === context.recordId);
    if (!device) return null;
    const label = [device.assetCode, device.brand, device.model].filter(Boolean).join(' · ') || 'Toestel';
    const fields = [];
    const grid = context.source.querySelector('.form-grid');
    if (grid) {
      [...grid.children].filter(node => node.classList?.contains('field')).forEach((node) => {
        if (node.querySelector('.device-detail-photo-section') || node.classList.contains('manual-device-section')) return;
        const fieldLabel = cleanText(node.querySelector(':scope > label')?.textContent || node.querySelector('label')?.textContent);
        if (!fieldLabel) return;
        fields.push({ label:fieldLabel, value:fieldValueFromNode(node), full:node.classList.contains('full') });
      });
    }
    const photos = [...context.source.querySelectorAll('.device-detail-photo img')]
      .map(img => img.dataset.fullSrc || img.currentSrc || img.src)
      .filter(Boolean);
    const timelines = [...context.source.querySelectorAll('.history-group')].map(group => ({
      title: cleanText(group.querySelector('h4')?.textContent) || 'Historiek',
      items: [...group.querySelectorAll('.timeline-item')].map(item => ({
        label: cleanText(item.querySelector('.event-label')?.textContent),
        date: cleanText(item.querySelector('.date')?.textContent),
        title: cleanText(item.querySelector('strong')?.textContent),
        text: cleanText(item.querySelector('p')?.textContent)
      }))
    })).filter(group => group.items.length);
    return {
      headerTitle: 'Machinepark',
      subtitle: `Toesteldetails · ${label}`,
      rightText: `Afgedrukt ${new Date().toLocaleString('nl-BE')}`,
      filenameTitle: `Toesteldetails_${label}`,
      fields,
      photos,
      photoTitle: 'Foto’s toestel',
      photoColumns: 3,
      photoMaxHeight: 48,
      timelines
    };
  }

  function genericLines(source) {
    const copy = source.cloneNode(true);
    copy.querySelectorAll(`${MAIL_SELECTOR},.page-print-row,.toolbar,.modal-foot,button,input[type="file"],script,style,img,.device-photo-remove,.device-photo-overview`).forEach(el => el.remove());
    copy.querySelectorAll('br').forEach(el => el.replaceWith(document.createTextNode('\n')));
    copy.querySelectorAll('th,td').forEach(el => el.appendChild(document.createTextNode(' | ')));
    copy.querySelectorAll('tr,h1,h2,h3,h4,h5,p,li,label,.value,.card,.panel').forEach(el => el.appendChild(document.createTextNode('\n')));
    return String(copy.textContent || '').split(/\n+/).map(cleanText).filter(Boolean);
  }

  function addHeader(doc, model) {
    doc.setTextColor(20);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(20);
    doc.text(pdfSafeText(model.headerTitle), 15, 18);
    if (model.subtitle) {
      doc.setFontSize(10.5);
      doc.text(pdfSafeText(model.subtitle), 15, 26);
    }
    doc.setTextColor(70);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    if (model.rightText) doc.text(pdfSafeText(model.rightText), 195, 18, { align:'right' });
    doc.setDrawColor(34);
    doc.setLineWidth(.6);
    doc.line(15, 31, 195, 31);
    doc.setTextColor(20);
  }

  function newModelPage(doc, model) {
    doc.addPage();
    addHeader(doc, model);
    return 39;
  }

  function fieldMetrics(doc, field, width) {
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10.5);
    const lines = doc.splitTextToSize(pdfSafeText(field.value || '—'), width);
    return { lines, height:5 + Math.max(1, lines.length) * 4.8 + 3 };
  }

  function drawField(doc, field, x, y, width, metrics) {
    doc.setTextColor(85);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8.5);
    doc.text(pdfSafeText(field.label).toUpperCase(), x, y + 3);
    doc.setTextColor(20);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10.5);
    doc.text(metrics.lines, x, y + 8);
  }

  function addFields(doc, model, startY) {
    let y = startY;
    const fields = model.fields || [];
    const fullWidth = 180;
    const colWidth = 86;
    const gap = 8;
    for (let i = 0; i < fields.length;) {
      const first = fields[i];
      if (first.full) {
        const m = fieldMetrics(doc, first, fullWidth);
        if (y + m.height > PAGE_BOTTOM) y = newModelPage(doc, model);
        drawField(doc, first, 15, y, fullWidth, m);
        y += m.height + 3;
        i += 1;
        continue;
      }
      const second = fields[i + 1] && !fields[i + 1].full ? fields[i + 1] : null;
      const m1 = fieldMetrics(doc, first, colWidth);
      const m2 = second ? fieldMetrics(doc, second, colWidth) : { lines:[], height:0 };
      const rowHeight = Math.max(m1.height, m2.height);
      if (y + rowHeight > PAGE_BOTTOM) y = newModelPage(doc, model);
      drawField(doc, first, 15, y, colWidth, m1);
      if (second) drawField(doc, second, 15 + colWidth + gap, y, colWidth, m2);
      y += rowHeight + 3;
      i += second ? 2 : 1;
    }
    return y;
  }

  function addTimeline(doc, model, startY) {
    let y = startY;
    for (const group of model.timelines || []) {
      if (y + 12 > PAGE_BOTTOM) y = newModelPage(doc, model);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(13);
      doc.text(pdfSafeText(group.title), 15, y + 5);
      y += 10;
      for (const item of group.items) {
        const header = [item.label, item.date].filter(Boolean).join(' · ');
        const body = [item.title, item.text].filter(Boolean).join('\n');
        doc.setFontSize(9.5);
        const bodyLines = doc.splitTextToSize(pdfSafeText(body || '—'), 168);
        const height = 10 + Math.max(1, bodyLines.length) * 4.6;
        if (y + height > PAGE_BOTTOM) y = newModelPage(doc, model);
        doc.setDrawColor(190);
        doc.roundedRect(18, y, 174, height, 2.5, 2.5);
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(8);
        doc.setTextColor(85);
        if (header) doc.text(pdfSafeText(header), 22, y + 5);
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(9.5);
        doc.setTextColor(30);
        doc.text(bodyLines, 22, y + 10);
        y += height + 4;
      }
      y += 2;
    }
    return y;
  }

  async function imageData(src) {
    if (!src) return null;
    if (src.startsWith('data:image/')) return src;
    try {
      const response = await withTimeout(fetch(src, { credentials:'same-origin', cache:'force-cache' }), 6000, 'Foto laden duurt te lang.');
      if (!response.ok) return null;
      const blob = await response.blob();
      return await withTimeout(new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ''));
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      }), 4000, 'Foto verwerken duurt te lang.');
    } catch (error) {
      console.warn('[Machinepark] Foto overgeslagen in PDF', error);
      return null;
    }
  }

  async function addPhotos(doc, model, startY) {
    const photos = model.photos || [];
    if (!photos.length) return startY;
    let y = startY;
    if (y + 14 > PAGE_BOTTOM) y = newModelPage(doc, model);
    doc.setDrawColor(185);
    doc.line(15, y, 195, y);
    y += 7;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.text(pdfSafeText(model.photoTitle || 'Foto’s'), 15, y);
    y += 6;

    const columns = Math.max(1, Number(model.photoColumns || 2));
    const gap = 5;
    const boxWidth = (180 - gap * (columns - 1)) / columns;
    const maxHeight = Number(model.photoMaxHeight || 80);

    for (let index = 0; index < photos.length; index += columns) {
      const batch = photos.slice(index, index + columns);
      const dataItems = await Promise.all(batch.map(imageData));
      const row = dataItems.map((data) => {
        if (!data) return { data:null, height:35 };
        try {
          const props = doc.getImageProperties(data);
          const ratioHeight = boxWidth * (Number(props.height) / Math.max(1, Number(props.width)));
          return { data, height:Math.min(maxHeight, Math.max(25, ratioHeight)) };
        } catch (_) {
          return { data:null, height:35 };
        }
      });
      const rowHeight = Math.max(...row.map(item => item.height)) + 4;
      if (y + rowHeight > PAGE_BOTTOM) y = newModelPage(doc, model);
      row.forEach((item, col) => {
        const x = 15 + col * (boxWidth + gap);
        doc.setDrawColor(190);
        doc.rect(x, y, boxWidth, rowHeight - 2);
        if (!item.data) {
          doc.setFont('helvetica', 'normal');
          doc.setFontSize(8);
          doc.setTextColor(100);
          doc.text('Foto kon niet worden geladen', x + boxWidth / 2, y + 12, { align:'center' });
          doc.setTextColor(20);
          return;
        }
        try {
          const format = item.data.startsWith('data:image/png') ? 'PNG' : 'JPEG';
          const props = doc.getImageProperties(item.data);
          const naturalHeight = boxWidth * (Number(props.height) / Math.max(1, Number(props.width)));
          const drawHeight = Math.min(item.height, naturalHeight);
          const drawWidth = Math.min(boxWidth - 4, drawHeight * (Number(props.width) / Math.max(1, Number(props.height))));
          const actualHeight = drawWidth * (Number(props.height) / Math.max(1, Number(props.width)));
          doc.addImage(item.data, format, x + (boxWidth - drawWidth) / 2, y + 2, drawWidth, actualHeight, undefined, 'FAST');
        } catch (error) {
          console.warn('[Machinepark] Foto kon niet in PDF worden geplaatst', error);
        }
      });
      y += rowHeight + gap;
    }
    return y;
  }

  function addGenericContent(doc, model, lines) {
    let y = 39;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9.5);
    for (const raw of lines) {
      const wrapped = doc.splitTextToSize(pdfSafeText(raw), 180);
      const needed = Math.max(1, wrapped.length) * 4.8 + 1.5;
      if (y + needed > PAGE_BOTTOM) y = newModelPage(doc, model);
      doc.text(wrapped, 15, y);
      y += needed;
    }
  }

  const SERVICE_PDF = {
    green:[24,63,53],
    ink:[17,17,17],
    muted:[51,51,51],
    border:[85,85,85],
    meta:[236,236,234],
    table:[222,222,219],
    tableLight:[236,236,234],
    maintenance:[36,72,93],
    breakdowns:[107,45,45],
    otherworks:[75,60,103],
  };

  function servicePdfSetText(doc,color=SERVICE_PDF.ink){doc.setTextColor(...color);}
  function servicePdfSetDraw(doc,color=SERVICE_PDF.border){doc.setDrawColor(...color);}
  function servicePdfSetFill(doc,color=SERVICE_PDF.meta){doc.setFillColor(...color);}
  function servicePdfSafe(value){return pdfSafeText(value===undefined||value===null?'—':String(value));}

  function servicePdfFitSingleLine(doc,value,maxWidth,baseSize=8.2,minSize=5.6) {
    const text=servicePdfSafe(value),original=doc.getFontSize?.()||baseSize;
    let size=baseSize;doc.setFontSize(size);
    while(size>minSize&&doc.getTextWidth(text)>maxWidth){size=Math.max(minSize,size-.25);doc.setFontSize(size);}
    doc.setFontSize(original);
    return {text,size};
  }

  function servicePdfCodeColumnWidth(doc,codes,totalWidth,reservedWidth,baseSize=8.2,minDescriptionWidth=30) {
    const original=doc.getFontSize?.()||baseSize;doc.setFontSize(baseSize);
    const values=['ONDERDEEL',...(codes||[]).map(value=>servicePdfSafe(value||'—'))];
    const widest=Math.max(...values.map(value=>doc.getTextWidth(value)),0);
    const threeSpaces=doc.getTextWidth('   ');
    doc.setFontSize(original);
    const wanted=widest+threeSpaces+4;
    return Math.max(12,Math.min(wanted,totalWidth-reservedWidth-minDescriptionWidth));
  }

  function servicePdfSectionTitle(doc,title,y) {
    servicePdfSetText(doc,SERVICE_PDF.ink);
    doc.setFont('helvetica','bold');doc.setFontSize(10.5);
    doc.text(servicePdfSafe(title),8,y);
    servicePdfSetDraw(doc,SERVICE_PDF.border);doc.setLineWidth(.35);doc.line(8,y+2,202,y+2);
    return y+7;
  }

  function servicePdfMetaBoxes(doc,meta,y) {
    const fields=(meta||[]).slice(0,4),count=Math.max(1,fields.length),gap=2.5,width=(194-gap*(count-1))/count,height=17;
    fields.forEach((field,index)=>{
      const x=8+index*(width+gap);
      servicePdfSetFill(doc,SERVICE_PDF.meta);servicePdfSetDraw(doc,SERVICE_PDF.border);doc.setLineWidth(.35);
      doc.roundedRect(x,y,width,height,2.2,2.2,'FD');
      servicePdfSetText(doc,SERVICE_PDF.ink);doc.setFont('helvetica','bold');doc.setFontSize(6.7);
      doc.text(servicePdfSafe(field.label).toUpperCase(),x+2.3,y+4.2);
      doc.setFontSize(8.6);
      const lines=doc.splitTextToSize(servicePdfSafe(field.value),width-4.6).slice(0,2);
      doc.text(lines,x+2.3,y+9.2);
    });
    return y+height+5;
  }

  function servicePdfTable(doc,{headers=[],rows=[],widths=[],y,headerFill=SERVICE_PDF.table,rowFont=8.2,nowrapCols=[],rightCols=[]}) {
    const x=8,total=widths.reduce((sum,w)=>sum+w,0),headerH=8;
    servicePdfSetFill(doc,headerFill);servicePdfSetDraw(doc,SERVICE_PDF.border);doc.setLineWidth(.3);
    doc.rect(x,y,total,headerH,'FD');
    let cx=x;
    doc.setFont('helvetica','bold');doc.setFontSize(6.8);servicePdfSetText(doc,SERVICE_PDF.ink);
    headers.forEach((header,i)=>{const right=rightCols.includes(i);doc.text(servicePdfSafe(header).toUpperCase(),right?cx+(widths[i]||0)-2:cx+2,y+5.1,right?{align:'right'}:undefined);cx+=widths[i]||0;});
    y+=headerH;
    for(const row of rows) {
      const cells=row.map(cell=>servicePdfSafe(cell));
      doc.setFont('helvetica','normal');doc.setFontSize(rowFont);
      const wrapped=cells.map((cell,i)=>nowrapCols.includes(i)?[cell]:doc.splitTextToSize(cell,Math.max(5,(widths[i]||20)-4)));
      const rowH=Math.max(8,...wrapped.map(lines=>Math.max(1,lines.length)*3.8+3));
      servicePdfSetDraw(doc,[120,120,120]);doc.rect(x,y,total,rowH);
      let xx=x;servicePdfSetText(doc,SERVICE_PDF.ink);
      wrapped.forEach((lines,i)=>{
        const right=rightCols.includes(i);
        doc.setFont('helvetica',right?'bold':'normal');
        if(nowrapCols.includes(i)){
          const fit=servicePdfFitSingleLine(doc,lines[0],Math.max(5,(widths[i]||20)-4),rowFont);
          doc.setFontSize(fit.size);doc.text(fit.text,right?xx+(widths[i]||0)-2:xx+2,y+4.8,right?{align:'right'}:undefined);doc.setFontSize(rowFont);
        }else{
          doc.text(lines,right?xx+(widths[i]||0)-2:xx+2,y+4.8,right?{align:'right'}:undefined);
        }
        xx+=widths[i]||0;
      });
      y+=rowH;
    }
    return y;
  }

  function servicePdfSummaryPage(doc,model) {
    const layout=model.servicePrintLayout;
    servicePdfSetText(doc,SERVICE_PDF.ink);
    doc.setFont('helvetica','bold');doc.setFontSize(16);
    doc.text(servicePdfSafe(layout.title),8,13);
    doc.setFont('helvetica','normal');doc.setFontSize(8.5);
    doc.text(servicePdfSafe(layout.subtitle),8,19);
    let y=24;
    y=servicePdfMetaBoxes(doc,layout.meta,y);
    y=servicePdfSectionTitle(doc,'Werkdagen en tijd',y);
    doc.setFont('helvetica','normal');doc.setFontSize(8.3);servicePdfSetText(doc,SERVICE_PDF.ink);
    if(layout.sessions?.length){
      for(const row of layout.sessions){
        doc.text(servicePdfSafe(`${row.date} · ${row.minutes} min`),8,y);
        y+=4.5;
      }
    }else{doc.text('—',8,y);y+=4.5;}
    doc.setFont('helvetica','bold');doc.text(servicePdfSafe(`Totaal: ${layout.totalMinutes||0} min`),8,y);y+=7;

    y=servicePdfSectionTitle(doc,'Totaaloverzicht werkzaamheden',y);
    y=servicePdfTable(doc,{
      headers:['Locatie','Toestellen','Onderhoud','Depannage','Andere werken'],
      rows:(layout.locations||[]).map(row=>[row.location,row.devices,row.maintenance,row.breakdowns,row.otherWorks]),
      widths:[62,30,32,32,38],y
    })+6;

    y=servicePdfSectionTitle(doc,'Totaal gebruikte onderdelen · alle locaties',y);
    const partRows=(layout.parts?.length?layout.parts:[{code:'—',description:'Geen onderdelen gebruikt.',qty:'',devices:[]}]).map(row=>[row.code||'—',row.description||'—',row.qty,(row.devices||[]).join(', ')]);
    const qtyW=18,devicesW=76,totalPartsW=194,codeW=servicePdfCodeColumnWidth(doc,partRows.map(row=>row[0]),totalPartsW,qtyW+devicesW,8.2,34),descriptionW=totalPartsW-codeW-qtyW-devicesW;
    servicePdfTable(doc,{
      headers:['Onderdeel','Omschrijving','Aantal','Locaties / toestellen'],
      rows:partRows,
      widths:[codeW,descriptionW,qtyW,devicesW],y,nowrapCols:[0,2],rightCols:[2]
    });
  }

  function servicePdfKindColor(kind) {
    return kind==='maintenance'?SERVICE_PDF.maintenance:(kind==='otherworks'?SERVICE_PDF.otherworks:SERVICE_PDF.breakdowns);
  }

  function servicePdfWorkHeader(doc,model,page) {
    servicePdfSetText(doc,SERVICE_PDF.ink);
    const layout=model.servicePrintLayout||model.workPrintLayout||{};
    doc.setFont('helvetica','bold');doc.setFontSize(6.8);doc.text(servicePdfSafe(page.documentLabel||'SERVICEVERSLAG'),8,8);
    doc.setFontSize(8.5);doc.text(servicePdfSafe(layout.reportLabel||model.filenameTitle||'Machinepark'),8,14);
    const label=servicePdfSafe(page.kindLabel),pillW=Math.max(24,doc.getTextWidth(label)+10);
    servicePdfSetFill(doc,SERVICE_PDF.green);doc.roundedRect(202-pillW,5,pillW,9,4.5,4.5,'F');
    doc.setTextColor(255,255,255);doc.setFontSize(7.5);doc.text(label,202-pillW/2,10.7,{align:'center'});
    servicePdfSetDraw(doc,SERVICE_PDF.green);doc.setLineWidth(.7);doc.line(8,19,202,19);
    servicePdfSetText(doc,SERVICE_PDF.ink);doc.setFontSize(6.8);doc.text(servicePdfSafe(page.sectionLabel||`WERKZAAMHEID ${page.index}`),8,25);
    doc.setFontSize(14);doc.text(servicePdfSafe(page.device),8,33);
    return 38;
  }

  function servicePdfMeasureDetails(doc,lines,width) {
    let height=0;doc.setFont('helvetica','normal');doc.setFontSize(8.2);
    for(const raw of lines||[]) {
      const chunks=String(raw??'—').split(/\n/);
      for(const chunk of chunks){
        const wrapped=doc.splitTextToSize(servicePdfSafe(chunk||'—'),width);
        height+=Math.max(1,wrapped.length)*3.8+1;
      }
    }
    return height;
  }

  function servicePdfMeasureParts(doc,parts,width) {
    let height=14;
    if(!parts?.length)return height+8;
    const qtyW=18,codeW=servicePdfCodeColumnWidth(doc,parts.map(part=>part.code),width,qtyW,7.8,34),descW=Math.max(30,width-codeW-qtyW);
    doc.setFont('helvetica','normal');doc.setFontSize(7.8);
    for(const part of parts){
      const wrapped=doc.splitTextToSize(servicePdfSafe(part.description||'—'),descW-5);
      height+=Math.max(8,wrapped.length*3.5+(part.oneOff?5:3));
    }
    return height;
  }

  function servicePdfPartsBox(doc,page,x,y,width) {
    const parts=page.parts||[],titleH=7,headH=7,qtyW=18,codeW=servicePdfCodeColumnWidth(doc,parts.map(part=>part.code),width,qtyW,7.8,34),descW=width-codeW-qtyW;
    servicePdfSetDraw(doc,SERVICE_PDF.border);doc.setLineWidth(.35);
    servicePdfSetFill(doc,SERVICE_PDF.table);doc.roundedRect(x,y,width,titleH+headH+(parts.length?0:8),2,2,'S');
    doc.rect(x,y,width,titleH,'F');
    servicePdfSetText(doc,SERVICE_PDF.ink);doc.setFont('helvetica','bold');doc.setFontSize(6.8);
    doc.text('ONDERDELEN VOOR DEZE WERKZAAMHEID',x+2.5,y+4.7);
    y+=titleH;
    servicePdfSetFill(doc,SERVICE_PDF.tableLight);doc.rect(x,y,width,headH,'F');servicePdfSetDraw(doc,SERVICE_PDF.border);doc.rect(x,y,width,headH);
    doc.setFontSize(6.4);
    doc.text('ONDERDEEL',x+2.5,y+4.7);
    doc.text('OMSCHRIJVING',x+codeW+2.5,y+4.7);
    doc.text('AANTAL',x+width-2.5,y+4.7,{align:'right'});
    y+=headH;
    if(!parts.length){
      doc.setFont('helvetica','normal');doc.setFontSize(7.8);doc.text('Geen onderdelen gebruikt.',x+codeW+2.5,y+5);
      servicePdfSetDraw(doc,SERVICE_PDF.border);doc.rect(x,y,width,8);return y+8;
    }
    for(const part of parts){
      doc.setFont('helvetica','normal');doc.setFontSize(7.8);
      const wrapped=doc.splitTextToSize(servicePdfSafe(part.description||'—'),Math.max(12,descW-5));
      const rowH=Math.max(8,wrapped.length*3.5+(part.oneOff?5:3));
      servicePdfSetDraw(doc,[120,120,120]);doc.rect(x,y,width,rowH);
      const fit=servicePdfFitSingleLine(doc,part.code||'—',codeW-5,7.8);
      servicePdfSetText(doc,SERVICE_PDF.ink);doc.setFontSize(fit.size);doc.text(fit.text,x+2.5,y+4.5);
      doc.setFontSize(7.8);doc.setFont('helvetica','normal');doc.text(wrapped,x+codeW+2.5,y+4.5);
      doc.setFont('helvetica','bold');doc.text(servicePdfSafe(part.qty),x+width-2.5,y+4.5,{align:'right'});
      if(part.oneOff){doc.setFontSize(5.7);doc.setFont('helvetica','normal');doc.text('EENMALIG / LEVERANCIER',x+codeW+2.5,y+rowH-2);}
      y+=rowH;
    }
    return y;
  }

  async function servicePdfWorkPhotos(doc,model,page,startY) {
    if(!page.photos?.length)return;
    let y=startY+6;
    if(y>235){doc.addPage();y=servicePdfWorkHeader(doc,model,page)+4;}
    y=servicePdfSectionTitle(doc,'Foto’s bij deze werkzaamheid',y);
    const gap=5,boxW=(194-gap)/2;
    for(let index=0;index<page.photos.length;index+=2){
      if(y+65>278){doc.addPage();y=servicePdfWorkHeader(doc,model,page)+4;y=servicePdfSectionTitle(doc,'Foto’s bij deze werkzaamheid',y);}
      const batch=page.photos.slice(index,index+2),data=await Promise.all(batch.map(imageData));
      data.forEach((img,col)=>{
        const x=8+col*(boxW+gap);servicePdfSetDraw(doc,SERVICE_PDF.border);doc.rect(x,y,boxW,58);
        if(!img)return;
        try{
          const props=doc.getImageProperties(img),ratio=Math.min((boxW-4)/props.width,54/props.height),w=props.width*ratio,h=props.height*ratio;
          doc.addImage(img,img.startsWith('data:image/png')?'PNG':'JPEG',x+(boxW-w)/2,y+2+(54-h)/2,w,h,undefined,'FAST');
        }catch(_){}
      });
      y+=63;
    }
  }

  async function servicePdfWorkPage(doc,model,page,addPage=true) {
    if(addPage)doc.addPage();
    let y=servicePdfWorkHeader(doc,model,page);
    const meta=Array.isArray(page.meta)&&page.meta.length?page.meta:[
      {label:'Locatie',value:page.location},
      {label:'Servicetijd / toestellen',value:`${Math.max(0,Math.round(Number(page.serviceMinutes)||0))} min · ${Math.max(1,Math.round(Number(page.deviceCount)||1))} toestel${Math.max(1,Math.round(Number(page.deviceCount)||1))===1?'':'len'}`},
      {label:'Technieker',value:page.technician},
    ];
    y=servicePdfMetaBoxes(doc,meta,y);

    const detailH=servicePdfMeasureDetails(doc,page.detailLines,178),partsH=servicePdfMeasureParts(doc,page.parts,184);
    const cardX=8,cardW=194,cardY=y,cardH=Math.min(215,12+detailH+5+partsH+5);
    servicePdfSetDraw(doc,SERVICE_PDF.border);doc.setLineWidth(.35);doc.roundedRect(cardX,cardY,cardW,cardH,2.5,2.5,'S');

    let cy=cardY+7;
    servicePdfSetText(doc,SERVICE_PDF.ink);doc.setFont('helvetica','bold');doc.setFontSize(8.8);doc.text(servicePdfSafe(page.device),cardX+3,cy);
    cy+=7;

    doc.setFont('helvetica','normal');doc.setFontSize(8.2);
    for(const raw of page.detailLines||[]){
      for(const chunk of String(raw??'—').split(/\n/)){
        const wrapped=doc.splitTextToSize(servicePdfSafe(chunk||'—'),178);
        servicePdfSetText(doc,SERVICE_PDF.ink);doc.text(wrapped,cardX+3,cy);
        cy+=Math.max(1,wrapped.length)*3.8+1;
      }
    }
    cy+=2;
    cy=servicePdfPartsBox(doc,page,cardX+3,cy,cardW-6);
    await servicePdfWorkPhotos(doc,model,page,Math.max(cardY+cardH,cy));
  }

  async function addServiceVisitPrintLayout(doc,model) {
    servicePdfSummaryPage(doc,model);
    for(const page of model.servicePrintLayout?.workPages||[])await servicePdfWorkPage(doc,model,page);
  }

  async function addWorkRecordPrintLayout(doc,model) {
    if(model.workPrintLayout?.page)await servicePdfWorkPage(doc,model,model.workPrintLayout.page,false);
  }

  function addPageNumbers(doc) {
    const pages = doc.getNumberOfPages();
    for (let page = 1; page <= pages; page += 1) {
      doc.setPage(page);
      doc.setDrawColor(185);
      doc.line(15, 286, 195, 286);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(85);
      doc.text('Afgedrukt vanuit Machinepark', 15, 291);
      doc.text(`Pagina ${page} / ${pages}`, 195, 291, { align:'right' });
    }
  }

  async function createDirectPdf(context) {
    const JsPDF = await loadJsPdf();
    const doc = new JsPDF({ unit:'mm', format:'a4', orientation:'portrait', compress:true });
    let model = null;
    if (context.kind === 'service') model = serviceModel(context);
    if (context.kind === 'serviceVisit' && typeof window.machineparkServiceVisitPdfModel === 'function') model = window.machineparkServiceVisitPdfModel(context.recordId);
    if (context.kind === 'device') model = deviceModel(context);

    if (model) {
      if (!(model.fields?.length || model.timelines?.length || model.photos?.length || model.servicePrintLayout)) throw new Error('Er is geen inhoud gevonden om in de PDF te zetten.');
      if (context.kind === 'serviceVisit' && model.servicePrintLayout) {
        await addServiceVisitPrintLayout(doc, model);
      } else if (context.kind === 'service' && model.workPrintLayout) {
        await addWorkRecordPrintLayout(doc, model);
      } else {
        addHeader(doc, model);
        let y = addFields(doc, model, 39);
        y = addTimeline(doc, model, y);
        await addPhotos(doc, model, y);
      }
    } else {
      const lines = genericLines(context.source);
      const useful = lines.join(' ').replace(/\s+/g, ' ').trim();
      if (useful.length < 5) throw new Error('Er is geen inhoud gevonden om in de PDF te zetten.');
      model = { headerTitle:'Machinepark', subtitle:context.title || 'Machinepark', rightText:new Date().toLocaleString('nl-BE'), filenameTitle:context.title || 'Machinepark' };
      addHeader(doc, model);
      addGenericContent(doc, model, lines);
    }

    if (!((context.kind === 'serviceVisit' && model?.servicePrintLayout) || (context.kind === 'service' && model?.workPrintLayout))) addPageNumbers(doc);
    const blob = doc.output('blob');
    if (!(blob instanceof Blob) || blob.size < 1200) throw new Error('De PDF bevat geen geldige inhoud. Probeer opnieuw.');
    const stamp = new Date().toISOString().slice(0, 10);
    const filename = `${safeFilename(`Machinepark_${model.filenameTitle}_${stamp}`)}.pdf`;
    return new File([blob], filename, { type:'application/pdf', lastModified:Date.now() });
  }

  function downloadFile(file) {
    const url = URL.createObjectURL(file);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = file.name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }

  async function shareFile(file, title) {
    const subject = `Machinepark - ${title}`;
    const text = `In bijlage vind je de PDF uit Machinepark: ${title}.`;
    const shareData = { files:[file], title:subject, text };
    const canShareFile = typeof navigator.share === 'function' && (typeof navigator.canShare !== 'function' || navigator.canShare(shareData));
    if (canShareFile) {
      try { await navigator.share(shareData); return; }
      catch (error) {
        if (error?.name === 'AbortError') return;
        console.warn('[Machinepark] Directe PDF-deling mislukt; desktopfallback wordt gebruikt.', error);
      }
    }
    downloadFile(file);
    const body = `${text}\n\nDe PDF is op je toestel gedownload. Voeg het bestand ${file.name} toe als bijlage.`;
    notify('PDF gedownload. Je mailprogramma wordt geopend; voeg de gedownloade PDF toe als bijlage.');
    setTimeout(() => { window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`; }, 120);
  }

  async function directMailPdf(button) {
    if (!button || button.dataset.directPdfBusy === '1') return;
    const context = getContext(button);
    if (!context) { notify('Er is geen afdrukbare inhoud gevonden.'); return; }
    const original = button.textContent;
    button.dataset.directPdfBusy = '1';
    button.disabled = true;
    button.textContent = 'PDF maken…';
    try {
      const file = await createDirectPdf(context);
      button.textContent = 'Delen…';
      await shareFile(file, context.title || context.kind);
    } catch (error) {
      console.error('[Machinepark] Directe Mail PDF mislukt', error);
      notify(error?.message || 'De PDF kon niet worden gemaakt.');
    } finally {
      button.disabled = false;
      button.dataset.directPdfBusy = '0';
      button.textContent = original;
    }
  }

  document.addEventListener('click', (event) => {
    const target = event.target instanceof Element ? event.target : event.target?.parentElement;
    const button = target?.closest?.(MAIL_SELECTOR);
    if (!button) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    void directMailPdf(button);
  }, true);

  window.machineparkDirectMailPdf = directMailPdf;
})();
} catch (error) {
  console.error('[Machinepark feature mail-pdf-direct-v4]', error);
}

/* work-orders-v1 */
try {
(() => {
  const WORK_ORDER_URL = '/machinepark/synology/api/work-order-templates.php';
  let workOrderTemplates = [];
  let workOrderEtag = null;
  let workOrderLoading = null;

  function canConfigureWorkOrders() {
    return Boolean(window.machineparkAccessReady && String(window.machineparkRole || '') === 'beheerder');
  }

  async function workOrderRequest(options = {}) {
    const headers = await centralHeaders(true);
    const res = await fetch(WORK_ORDER_URL, { cache: 'no-store', ...options, headers: { ...headers, ...(options.headers || {}) } });
    const text = await res.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch (_) {}
    if (!res.ok) throw new Error(data.error || text || `Werkbonactie mislukt (${res.status})`);
    if (Array.isArray(data.templates)) workOrderTemplates = data.templates;
    if (data.etag !== undefined) workOrderEtag = data.etag || null;
    return data;
  }

  async function loadWorkOrderTemplates(force = false) {
    if (!force && workOrderTemplates.length) return workOrderTemplates;
    if (!force && workOrderLoading) return workOrderLoading;
    workOrderLoading = workOrderRequest().then((data) => data.templates || []).finally(() => { workOrderLoading = null; });
    return workOrderLoading;
  }
  window.machineparkLoadWorkOrderTemplates = loadWorkOrderTemplates;

  function normalizeMatch(value) {
    return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase();
  }

  function templateMatchesDevice(template, device) {
    const brands = Array.isArray(template?.brands) ? template.brands.map(normalizeMatch).filter(Boolean) : [];
    const models = Array.isArray(template?.models) ? template.models.map(normalizeMatch).filter(Boolean) : [];
    const brand = normalizeMatch(device?.brand);
    const model = normalizeMatch(device?.model);
    const brandMatch = !brands.length || brands.some((item) => brand === item || brand.includes(item) || item.includes(brand));
    const modelMatch = !models.length || models.some((item) => model === item || model.includes(item) || item.includes(model));
    return brandMatch && modelMatch;
  }

  function activeTemplatesForDevice(device) {
    return workOrderTemplates.filter((template) => template?.active !== false).sort((a, b) => {
      const am = templateMatchesDevice(a, device) ? 0 : 1;
      const bm = templateMatchesDevice(b, device) ? 0 : 1;
      return am - bm || String(a.name || '').localeCompare(String(b.name || ''), 'nl-BE');
    });
  }

  function workOrderValueText(field) {
    if (field?.type === 'checkbox') return field.value ? 'Ja' : 'Nee';
    const value = field?.value;
    return value === '' || value === null || value === undefined ? '—' : String(value);
  }

  function workOrderDetailsHtml(workOrder) {
    if (!workOrder || !Array.isArray(workOrder.fields) || !workOrder.fields.length) return '<span class="muted">Geen werkbon gekoppeld.</span>';
    return `<div class="workorder-details"><div class="workorder-details-head">${esc(workOrder.templateName || 'Werkbon')} · versie ${esc(workOrder.templateVersion || 1)}</div><div class="workorder-details-grid">${workOrder.fields.map((field) => `<div class="workorder-details-field"><span>${esc(field.label || 'Veld')}</span><strong>${esc(workOrderValueText(field))}</strong></div>`).join('')}</div></div>`;
  }
  window.machineparkWorkOrderDetailsHtml = workOrderDetailsHtml;
  window.machineparkMakeWorkOrderEditor = makeWorkOrderEditor;
  window.machineparkCollectWorkOrder = collectWorkOrder;

  function templateOptionHtml(template, device) {
    const recommended = templateMatchesDevice(template, device);
    return `<option value="${esc(template.id)}">${recommended ? '★ ' : ''}${esc(template.name)} · v${esc(template.version || 1)}${recommended ? ' · aanbevolen' : ''}</option>`;
  }

  function fieldInputHtml(field, value, prefix) {
    const id = `${prefix}-${field.id}`;
    const required = field.required ? '<span style="color:var(--danger)"> *</span>' : '';
    if (field.type === 'checkbox') {
      return `<div class="workorder-maintenance-field full"><label class="workorder-checkbox"><input type="checkbox" data-workorder-field="${esc(field.id)}" ${value ? 'checked' : ''}><span>${esc(field.label)}${required}</span></label></div>`;
    }
    if (field.type === 'textarea') {
      return `<div class="workorder-maintenance-field full"><label for="${esc(id)}">${esc(field.label)}${required}</label><textarea id="${esc(id)}" data-workorder-field="${esc(field.id)}">${esc(value ?? '')}</textarea></div>`;
    }
    if (field.type === 'select') {
      const options = (Array.isArray(field.options) ? field.options : []).map((option) => `<option value="${esc(option)}" ${String(value ?? '') === String(option) ? 'selected' : ''}>${esc(option)}</option>`).join('');
      return `<div class="workorder-maintenance-field"><label for="${esc(id)}">${esc(field.label)}${required}</label><select id="${esc(id)}" data-workorder-field="${esc(field.id)}"><option value="">— Kies —</option>${options}</select></div>`;
    }
    if (field.type === 'number') {
      return `<div class="workorder-maintenance-field"><label for="${esc(id)}">${esc(field.label)}${required}</label><input id="${esc(id)}" type="text" inputmode="decimal" autocomplete="off" data-workorder-number="1" data-workorder-field="${esc(field.id)}" value="${esc(value ?? '')}" placeholder="bv. 12,5"></div>`;
    }
    const type = field.type === 'date' ? 'date' : 'text';
    return `<div class="workorder-maintenance-field"><label for="${esc(id)}">${esc(field.label)}${required}</label><input id="${esc(id)}" type="${type}" data-workorder-field="${esc(field.id)}" value="${esc(value ?? '')}"></div>`;
  }

  function renderWorkOrderFields(editor, definition, savedValues = null) {
    const fieldsBox = editor.querySelector('.workorder-maintenance-fields');
    if (!fieldsBox) return;
    if (!definition || !Array.isArray(definition.fields) || !definition.fields.length) {
      fieldsBox.innerHTML = '<div class="muted">Kies een werkbon om de invulvelden te tonen.</div>';
      editor._activeWorkOrderDefinition = null;
      return;
    }
    const values = new Map((Array.isArray(savedValues) ? savedValues : []).map((field) => [field.id, field.value]));
    const prefix = `wo-${Math.random().toString(36).slice(2, 8)}`;
    fieldsBox.innerHTML = definition.fields.map((field) => fieldInputHtml(field, values.has(field.id) ? values.get(field.id) : '', prefix)).join('');
    editor._activeWorkOrderDefinition = definition;
  }

  function makeWorkOrderEditor(device, savedWorkOrder = null) {
    const editor = document.createElement('div');
    editor.className = 'workorder-maintenance-section';
    editor.dataset.workorderEditor = '1';
    editor._savedWorkOrder = savedWorkOrder || null;
    const templates = activeTemplatesForDevice(device);
    const savedOption = savedWorkOrder
      ? `<option value="__saved__" selected>Bewaarde werkbon · ${esc(savedWorkOrder.templateName || 'Werkbon')} · v${esc(savedWorkOrder.templateVersion || 1)}</option>`
      : '';
    editor.innerHTML = `<div class="workorder-maintenance-head"><strong>Werkbon</strong><span class="muted" style="font-size:10px">Kies de exacte bon voor deze machine</span></div><select class="filter workorder-maintenance-select" style="width:100%"><option value="">Geen werkbon</option>${savedOption}${templates.map((template) => templateOptionHtml(template, device)).join('')}</select><div class="workorder-maintenance-fields"></div>`;
    const select = editor.querySelector('.workorder-maintenance-select');
    if (savedWorkOrder) renderWorkOrderFields(editor, { ...savedWorkOrder, fields: savedWorkOrder.fields || [] }, savedWorkOrder.fields || []);
    else renderWorkOrderFields(editor, null);
    select.addEventListener('change', () => {
      if (select.value === '__saved__' && editor._savedWorkOrder) {
        renderWorkOrderFields(editor, { ...editor._savedWorkOrder, fields: editor._savedWorkOrder.fields || [] }, editor._savedWorkOrder.fields || []);
        return;
      }
      const template = workOrderTemplates.find((item) => item.id === select.value) || null;
      renderWorkOrderFields(editor, template);
    });
    return editor;
  }

  function collectWorkOrder(editor) {
    if (!editor) return null;
    const select = editor.querySelector('.workorder-maintenance-select');
    if (!select || !select.value) return null;
    const definition = editor._activeWorkOrderDefinition;
    if (!definition || !Array.isArray(definition.fields)) return null;
    const snapshotFields = definition.fields.map((field) => {
      const input = editor.querySelector(`[data-workorder-field="${field.id}"]`);
      const value = field.type === 'checkbox' ? Boolean(input?.checked) : String(input?.value ?? '').trim();
      if (field.type === 'number' && value !== '' && !/^[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)$/.test(value)) {
        throw new Error(`Gebruik een geldig getal bij “${field.label}”, bijvoorbeeld 12,5 of 12.5.`);
      }
      if (field.required && (field.type === 'checkbox' ? !value : !String(value).trim())) {
        throw new Error(`Vul het verplichte werkbonveld “${field.label}” in.`);
      }
      return { id: field.id, label: field.label, type: field.type, required: Boolean(field.required), options: Array.isArray(field.options) ? [...field.options] : [], value };
    });
    return {
      templateId: definition.templateId || definition.id || editor._savedWorkOrder?.templateId || '',
      templateName: definition.templateName || definition.name || editor._savedWorkOrder?.templateName || 'Werkbon',
      templateVersion: Number(definition.templateVersion || definition.version || editor._savedWorkOrder?.templateVersion || 1),
      fields: snapshotFields,
      capturedAt: new Date().toISOString(),
    };
  }

  function attachMaintenanceWorkOrders(existingId = '') {
    const modal = document.querySelector('#modal .modal-body');
    if (!modal) return;
    const cards = [...modal.querySelectorAll('.maintenance-machine-card')];
    if (cards.length) {
      cards.forEach((card) => {
        if (card.querySelector('[data-workorder-editor]')) return;
        const deviceId = card.dataset?.maintenanceDevice || '';
        const device = state.devices.find((item) => item.id === deviceId) || {};
        const fields = card.querySelector('.maintenance-machine-fields') || card;
        const editor = makeWorkOrderEditor(device, null);
        const photoEditor = fields.querySelector('.service-photo-editor');
        if (photoEditor) fields.insertBefore(editor, photoEditor);
        else fields.appendChild(editor);
        const enabled = card.classList.contains('selected');
        editor.querySelectorAll('input,select,textarea').forEach((el) => { el.disabled = !enabled; });
      });
      return;
    }
    if (!existingId) return;
    if (modal.querySelector('[data-workorder-editor]')) return;
    const record = state.maintenance.find((item) => item.id === existingId) || null;
    const device = state.devices.find((item) => item.id === record?.deviceId) || {};
    const grid = modal.querySelector('.form-grid') || modal;
    grid.appendChild(makeWorkOrderEditor(device, record?.workOrder || null));
  }

  function attachBreakdownWorkOrders(existingId = '') {
    const modal = document.querySelector('#modal .modal-body');
    if (!modal || typeof window.machineparkMakeWorkOrderEditor !== 'function') return;
    const cards = [...modal.querySelectorAll('.breakdown-machine-card')];
    if (cards.length) {
      cards.forEach((card) => {
        if (card.querySelector('[data-workorder-editor]')) return;
        const deviceId = card.dataset?.breakdownDevice || '';
        const device = state.devices.find((item) => item.id === deviceId) || {};
        const fields = card.querySelector('.maintenance-machine-fields') || card;
        const editor = window.machineparkMakeWorkOrderEditor(device, null);
        const photoEditor = fields.querySelector('.service-photo-editor');
        if (photoEditor) fields.insertBefore(editor, photoEditor);
        else fields.appendChild(editor);
        const enabled = card.classList.contains('selected');
        editor.querySelectorAll('input,select,textarea').forEach((el) => { el.disabled = !enabled; });
      });
      return;
    }
    if (!existingId || modal.querySelector('[data-workorder-editor]')) return;
    const record = state.breakdowns.find((item) => item.id === existingId) || null;
    const device = state.devices.find((item) => item.id === record?.deviceId) || {};
    const grid = modal.querySelector('.form-grid') || modal;
    const editor = window.machineparkMakeWorkOrderEditor(device, record?.workOrder || null);
    const photoField = grid.querySelector('.service-photo-editor')?.closest('.field');
    if (photoField) grid.insertBefore(editor, photoField);
    else grid.appendChild(editor);
  }

  function validateBreakdownWorkOrders(existingId = '') {
    if (typeof window.machineparkCollectWorkOrder !== 'function') return;
    if (existingId) {
      const editor = document.querySelector('#modal [data-workorder-editor]');
      if (editor) window.machineparkCollectWorkOrder(editor);
      return;
    }
    [...document.querySelectorAll('#modal .breakdown-machine-card.selected')].forEach((card) => {
      const editor = card.querySelector('[data-workorder-editor]');
      if (editor) window.machineparkCollectWorkOrder(editor);
    });
  }

  function installBreakdownWorkOrderValidation(existingId = '') {
    const form = document.getElementById('modalForm');
    if (!form || form._breakdownWorkOrderValidation) return;
    form.addEventListener('submit', (event) => {
      try { validateBreakdownWorkOrders(existingId); }
      catch (error) {
        event.preventDefault();
        event.stopImmediatePropagation();
        alert(error?.message || 'Controleer de werkbon.');
      }
    }, true);
    form._breakdownWorkOrderValidation = true;
  }

  const baseSetBreakdownMachineEnabledForWorkOrders = setBreakdownMachineEnabled;
  setBreakdownMachineEnabled = function(card, enabled) {
    baseSetBreakdownMachineEnabledForWorkOrders(card, enabled);
    card?.querySelectorAll('[data-workorder-editor] input,[data-workorder-editor] select,[data-workorder-editor] textarea').forEach((el) => { el.disabled = !enabled; });
  };
  window.setBreakdownMachineEnabled = setBreakdownMachineEnabled;

  const baseBreakdownBatchSelectedItemsForWorkOrders = breakdownBatchSelectedItems;
  breakdownBatchSelectedItems = function() {
    const items = baseBreakdownBatchSelectedItemsForWorkOrders();
    return items.map((item) => {
      const card = [...document.querySelectorAll('#modal .breakdown-machine-card')].find((candidate) => candidate.dataset?.breakdownDevice === item.deviceId);
      const editor = card?.querySelector('[data-workorder-editor]');
      return editor && typeof window.machineparkCollectWorkOrder === 'function'
        ? { ...item, workOrder: window.machineparkCollectWorkOrder(editor) }
        : item;
    });
  };
  window.breakdownBatchSelectedItems = breakdownBatchSelectedItems;

  const baseOpenBreakdownForWorkOrders = openBreakdown;
  openBreakdown = function(id) {
    const result = baseOpenBreakdownForWorkOrders(id);
    window.machineparkLoadWorkOrderTemplates?.().then(() => {
      const installWorkOrders = () => {
        attachBreakdownWorkOrders(id || '');
        installBreakdownWorkOrderValidation(id || '');
        const modal = document.querySelector('#modal .modal-body');
        const box = modal?.querySelector('#breakdownLocationDevices');
        if (box && !box._breakdownWorkOrderObserver) {
          const observer = new MutationObserver(() => attachBreakdownWorkOrders(id || ''));
          observer.observe(box, { childList:true });
          box._breakdownWorkOrderObserver = observer;
        }
      };
      setTimeout(installWorkOrders, 0);
      setTimeout(installWorkOrders, 100);
    }).catch((error) => console.warn('Werkbonnen laden voor depannage', error));
    return result;
  };
  window.openBreakdown = openBreakdown;

  const baseOpenMaintenanceForWorkOrders = openMaintenance;
  openMaintenance = function(id) {
    const result = baseOpenMaintenanceForWorkOrders(id);
    loadWorkOrderTemplates().then(() => {
      const installWorkOrders = () => {
        attachMaintenanceWorkOrders(id || '');
        const modal = document.querySelector('#modal .modal-body');
        const box = modal?.querySelector('#maintenanceLocationDevices');
        if (box && !box._workOrderObserver) {
          const observer = new MutationObserver(() => attachMaintenanceWorkOrders(id || ''));
          observer.observe(box, { childList: true });
          box._workOrderObserver = observer;
        }
      };
      setTimeout(installWorkOrders, 0);
      setTimeout(installWorkOrders, 80);
    }).catch((error) => console.warn('Werkbonnen laden', error));
    return result;
  };
  window.openMaintenance = openMaintenance;

  if (typeof setMaintenanceMachineEnabled === 'function') {
    const baseSetMaintenanceMachineEnabledForWorkOrders = setMaintenanceMachineEnabled;
    setMaintenanceMachineEnabled = function(card, enabled) {
      baseSetMaintenanceMachineEnabledForWorkOrders(card, enabled);
      card?.querySelectorAll('[data-workorder-editor] input,[data-workorder-editor] select,[data-workorder-editor] textarea').forEach((el) => { el.disabled = !enabled; });
    };
  }

  const basePutForWorkOrders = put;
  put = async function(storeName, obj) {
    if (storeName === 'maintenance' && obj) {
      const cards = [...document.querySelectorAll('#modal .maintenance-machine-card')];
      if (!cards.length) {
        const editor = document.querySelector('#modal [data-workorder-editor]');
        if (editor) obj = { ...obj, workOrder: collectWorkOrder(editor) };
      }
    }
    return basePutForWorkOrders(storeName, obj);
  };

  const basePutManyForWorkOrders = putMany;
  putMany = async function(storeName, items) {
    if (storeName === 'maintenance' && Array.isArray(items)) {
      items = items.map((item) => {
        const card = [...document.querySelectorAll('#modal .maintenance-machine-card')].find((candidate) => candidate.dataset?.maintenanceDevice === item.deviceId);
        const editor = card?.querySelector('[data-workorder-editor]');
        return editor ? { ...item, workOrder: collectWorkOrder(editor) } : item;
      });
    }
    return basePutManyForWorkOrders(storeName, items);
  };

  const basePutBreakdownForWorkOrders = put;
  put = async function(storeName, obj) {
    if (storeName === 'breakdowns' && obj) {
      const cards = [...document.querySelectorAll('#modal .breakdown-machine-card')];
      if (!cards.length) {
        const editor = document.querySelector('#modal [data-workorder-editor]');
        if (editor && typeof window.machineparkCollectWorkOrder === 'function') obj = { ...obj, workOrder: window.machineparkCollectWorkOrder(editor) };
      }
    }
    return basePutBreakdownForWorkOrders(storeName, obj);
  };
  window.put = put;

  const basePutManyBreakdownForWorkOrders = putMany;
  putMany = async function(storeName, items) {
    if (storeName === 'breakdowns' && Array.isArray(items)) {
      items = items.map((item) => {
        const card = [...document.querySelectorAll('#modal .breakdown-machine-card')].find((candidate) => candidate.dataset?.breakdownDevice === item.deviceId);
        const editor = card?.querySelector('[data-workorder-editor]');
        return editor && typeof window.machineparkCollectWorkOrder === 'function'
          ? { ...item, workOrder: window.machineparkCollectWorkOrder(editor) }
          : item;
      });
    }
    return basePutManyBreakdownForWorkOrders(storeName, items);
  };
  window.putMany = putMany;

  const baseShowMaintenanceDetailsForWorkOrders = showMaintenanceDetails;
  showMaintenanceDetails = function(id) {
    const result = baseShowMaintenanceDetailsForWorkOrders(id);
    setTimeout(() => {
      const record = state.maintenance.find((item) => item.id === id);
      const grid = document.querySelector('#modal .modal-body .form-grid');
      if (!record || !grid || grid.querySelector('.workorder-detail-block')) return;
      const block = document.createElement('div');
      block.className = 'field full workorder-detail-block';
      block.innerHTML = `<label>Werkbon</label>${workOrderDetailsHtml(record.workOrder)}`;
      grid.appendChild(block);
    }, 0);
    return result;
  };
  window.showMaintenanceDetails = showMaintenanceDetails;

  const baseShowBreakdownDetailsForWorkOrders = window.machineparkShowBreakdownDetails;
  if (typeof baseShowBreakdownDetailsForWorkOrders === 'function') {
    window.machineparkShowBreakdownDetails = function(id) {
      const result = baseShowBreakdownDetailsForWorkOrders(id);
      setTimeout(() => {
        const record = state.breakdowns.find((item) => item.id === id);
        const grid = document.querySelector('#modal .breakdown-detail-summary');
        if (!record || !grid || grid.querySelector('.workorder-detail-block')) return;
        const block = document.createElement('div');
        block.className = 'breakdown-detail-field full workorder-detail-block';
        block.innerHTML = `<label>Werkbon</label><div class="value">${window.machineparkWorkOrderDetailsHtml?.(record.workOrder) || '<span class="muted">Geen werkbon gekoppeld.</span>'}</div>`;
        const photos = [...grid.children].find((child) => child.querySelector?.('.breakdown-detail-photos'));
        if (photos) grid.insertBefore(block, photos);
        else grid.appendChild(block);
      }, 0);
      return result;
    };
  }

  function ensureSettingsCard() {
    let card = document.getElementById('workOrderSettingsCard');
    if (!card) {
      const grid = document.querySelector('#view-settings .settings-grid') || document.querySelector('.settings-grid');
      if (!grid) return null;
      card = document.createElement('div');
      card.className = 'settings-card';
      card.id = 'workOrderSettingsCard';
      card.innerHTML = `<div class="workorder-settings-head"><div><h4>Werkbonnen</h4><p>Maak en beheer verschillende werkbonnen per merk of model. De gekozen bon wordt rechtstreeks in Onderhoud ingevuld en afgedrukt.</p></div><button type="button" class="btn primary" id="configureWorkOrders">Configureren</button></div>`;
      grid.appendChild(card);
      card.querySelector('#configureWorkOrders').onclick = () => openWorkOrderConfigPage();
    }
    card.style.display = canConfigureWorkOrders() ? '' : 'none';
    return card;
  }

  function ensureConfigPage() {
    let page = document.getElementById('workOrderConfigPage');
    if (page) return page;
    page = document.createElement('section');
    page.id = 'workOrderConfigPage';
    page.className = 'workorder-config-page';
    page.innerHTML = `<div class="workorder-config-shell"><div class="workorder-config-head"><div><button type="button" class="btn small" id="closeWorkOrderConfig">← Terug naar Beheer</button><h2 style="margin-top:14px">Werkbonnen configureren</h2><p class="muted">Beheer templates. Oude ingevulde onderhoudsbonnen blijven gekoppeld aan hun oorspronkelijke versie.</p></div><div class="workorder-config-actions"><button type="button" class="btn" id="refreshWorkOrders">Vernieuwen</button><button type="button" class="btn primary" id="newWorkOrderTemplate">+ Nieuwe werkbon</button></div></div><div id="workOrderConfigStatus" class="muted" style="margin-bottom:12px"></div><div id="workOrderTemplateList" class="workorder-template-list"></div></div>`;
    document.body.appendChild(page);
    page.querySelector('#closeWorkOrderConfig').onclick = () => { page.classList.remove('show'); document.body.classList.remove('workorder-config-active'); };
    page.querySelector('#refreshWorkOrders').onclick = async () => { await loadWorkOrderTemplates(true); renderWorkOrderTemplateList(); };
    page.querySelector('#newWorkOrderTemplate').onclick = () => openTemplateEditor();
    return page;
  }

  function templateScopeText(template) {
    const parts = [];
    if (template.brands?.length) parts.push(`Merk: ${template.brands.join(', ')}`);
    if (template.models?.length) parts.push(`Model: ${template.models.join(', ')}`);
    return parts.join(' · ') || 'Alle machines';
  }

  function renderWorkOrderTemplateList() {
    const page = ensureConfigPage();
    const list = page.querySelector('#workOrderTemplateList');
    const status = page.querySelector('#workOrderConfigStatus');
    status.textContent = `${workOrderTemplates.length} werkbon${workOrderTemplates.length === 1 ? '' : 'nen'} geconfigureerd`;
    if (!workOrderTemplates.length) {
      list.innerHTML = '<div class="empty"><div class="big">📋</div>Nog geen werkbonnen. Maak de eerste werkbon met “Nieuwe werkbon”.</div>';
      return;
    }
    list.innerHTML = workOrderTemplates.map((template) => `<div class="workorder-template-card"><div><h4>${esc(template.name)}</h4><div class="muted" style="font-size:12px">${esc(template.description || 'Geen omschrijving')}</div><div class="workorder-template-meta"><span class="badge ${template.active !== false ? 'success' : 'gray'}">${template.active !== false ? 'Actief' : 'Inactief'}</span><span class="badge gray">Versie ${esc(template.version || 1)}</span><span class="badge gray">${template.fields?.length || 0} velden</span><span class="badge gray">${esc(templateScopeText(template))}</span></div></div><div class="workorder-template-actions"><button type="button" class="btn small" data-workorder-edit="${esc(template.id)}">Configureren</button><button type="button" class="btn small" data-workorder-copy="${esc(template.id)}">Kopiëren</button><button type="button" class="btn small danger" data-workorder-delete="${esc(template.id)}">Verwijderen</button></div></div>`).join('');
    list.querySelectorAll('[data-workorder-edit]').forEach((button) => button.onclick = () => openTemplateEditor(workOrderTemplates.find((item) => item.id === button.dataset.workorderEdit)));
    list.querySelectorAll('[data-workorder-copy]').forEach((button) => button.onclick = () => {
      const source = workOrderTemplates.find((item) => item.id === button.dataset.workorderCopy);
      if (!source) return;
      openTemplateEditor({ ...source, id: '', name: `${source.name} - kopie`, version: 1, createdAt: '', updatedAt: '' });
    });
    list.querySelectorAll('[data-workorder-delete]').forEach((button) => button.onclick = async () => {
      const template = workOrderTemplates.find((item) => item.id === button.dataset.workorderDelete);
      if (!template || !confirm(`Werkbon “${template.name}” verwijderen? Reeds ingevulde onderhoudsbonnen blijven behouden.`)) return;
      try {
        await workOrderRequest({ method: 'POST', body: JSON.stringify({ action: 'delete-template', templateId: template.id, etag: workOrderEtag }) });
        toast('Werkbon verwijderd');
        renderWorkOrderTemplateList();
      } catch (error) { alert(error.message); }
    });
  }

  async function openWorkOrderConfigPage() {
    if (!canConfigureWorkOrders()) { alert('Alleen een beheerder kan werkbonnen configureren.'); return; }
    const page = ensureConfigPage();
    page.classList.add('show');
    document.body.classList.add('workorder-config-active');
    page.querySelector('#workOrderConfigStatus').textContent = 'Werkbonnen laden…';
    try { await loadWorkOrderTemplates(true); renderWorkOrderTemplateList(); }
    catch (error) { page.querySelector('#workOrderConfigStatus').textContent = error.message; }
  }
  window.openWorkOrderConfigPage = openWorkOrderConfigPage;

  function templateFieldRow(field = {}) {
    const row = document.createElement('div');
    row.className = 'workorder-template-field';
    row.dataset.fieldId = field.id || `veld-${crypto.randomUUID()}`;
    row.innerHTML = `<input class="wo-field-label" placeholder="Naam veld" value="${esc(field.label || '')}"><select class="wo-field-type"><option value="text">Tekst</option><option value="textarea">Lange tekst</option><option value="number">Getal</option><option value="date">Datum</option><option value="checkbox">Ja / nee</option><option value="select">Keuzelijst</option></select><input class="wo-field-options" placeholder="Keuzes, gescheiden door komma’s" value="${esc((field.options || []).join(', '))}"><div><label class="workorder-template-field-check"><input type="checkbox" class="wo-field-required" ${field.required ? 'checked' : ''}> Verplicht</label><div class="workorder-template-field-actions"><button class="btn small" type="button" data-move-up title="Omhoog">↑</button><button class="btn small" type="button" data-move-down title="Omlaag">↓</button><button class="btn small danger" type="button" data-remove-field title="Verwijderen">×</button></div></div>`;
    row.querySelector('.wo-field-type').value = field.type || 'text';
    const syncOptions = () => row.querySelector('.wo-field-options').style.display = row.querySelector('.wo-field-type').value === 'select' ? '' : 'none';
    row.querySelector('.wo-field-type').onchange = syncOptions;
    row.querySelector('[data-remove-field]').onclick = () => row.remove();
    row.querySelector('[data-move-up]').onclick = () => row.previousElementSibling && row.parentNode.insertBefore(row, row.previousElementSibling);
    row.querySelector('[data-move-down]').onclick = () => row.nextElementSibling && row.parentNode.insertBefore(row.nextElementSibling, row);
    syncOptions();
    return row;
  }

  function collectTemplateFields(container) {
    return [...container.querySelectorAll('.workorder-template-field')].map((row) => ({
      id: row.dataset.fieldId,
      label: row.querySelector('.wo-field-label').value.trim(),
      type: row.querySelector('.wo-field-type').value,
      required: row.querySelector('.wo-field-required').checked,
      options: row.querySelector('.wo-field-type').value === 'select' ? row.querySelector('.wo-field-options').value.split(',').map((item) => item.trim()).filter(Boolean) : [],
    })).filter((field) => field.label);
  }

  function openTemplateEditor(template = null) {
    if (!canConfigureWorkOrders()) return;
    const editing = Boolean(template?.id && workOrderTemplates.some((item) => item.id === template.id));
    const body = `<div class="form-grid"><div class="field full"><label>Naam werkbon</label><input name="name" maxlength="120" value="${esc(template?.name || '')}" placeholder="bv. Lattiz jaarlijks onderhoud" required></div><div class="field full"><label>Omschrijving</label><textarea name="description" maxlength="500" placeholder="Waarvoor wordt deze werkbon gebruikt?">${esc(template?.description || '')}</textarea></div><div class="field"><label>Merk(en)</label><input name="brands" value="${esc((template?.brands || []).join(', '))}" placeholder="bv. Lattiz, Franke"></div><div class="field"><label>Model(len)</label><input name="models" value="${esc((template?.models || []).join(', '))}" placeholder="optioneel, komma gescheiden"></div><div class="field full"><label style="display:flex;align-items:center;gap:8px"><input type="checkbox" name="active" ${template?.active === false ? '' : 'checked'} style="width:auto"> Actief en beschikbaar in Onderhoud</label></div><div class="field full"><div style="display:flex;justify-content:space-between;gap:10px;align-items:center"><label>Velden op de werkbon</label><button type="button" class="btn small" id="addWorkOrderField">+ Veld toevoegen</button></div><div id="workOrderTemplateFields" class="workorder-template-fields"></div></div></div>`;
    showModal(editing ? `Werkbon configureren · v${template.version || 1}` : 'Nieuwe werkbon', body, 'Werkbon opslaan', async (fd) => {
      try {
        const fields = collectTemplateFields(document.getElementById('workOrderTemplateFields'));
        if (!fields.length) throw new Error('Voeg minstens één veld aan de werkbon toe.');
        const payload = {
          id: editing ? template.id : '',
          name: val(fd, 'name'),
          description: val(fd, 'description'),
          brands: val(fd, 'brands').split(',').map((item) => item.trim()).filter(Boolean),
          models: val(fd, 'models').split(',').map((item) => item.trim()).filter(Boolean),
          active: Boolean(fd.get('active')),
          fields,
        };
        await workOrderRequest({ method: 'POST', body: JSON.stringify({ action: 'save-template', template: payload, etag: workOrderEtag }) });
        closeModal();
        toast(editing ? 'Werkbon bijgewerkt · nieuwe versie gemaakt' : 'Werkbon aangemaakt');
        renderWorkOrderTemplateList();
      } catch (error) { alert(error.message); }
    });
    setTimeout(() => {
      const fields = document.getElementById('workOrderTemplateFields');
      if (!fields) return;
      (template?.fields || []).forEach((field) => fields.appendChild(templateFieldRow(field)));
      if (!fields.children.length) fields.appendChild(templateFieldRow({ type: 'text' }));
      document.getElementById('addWorkOrderField').onclick = () => fields.appendChild(templateFieldRow({ type: 'text' }));
    }, 0);
  }

  const baseApplyServerAccessForWorkOrders = window.applyMachineparkServerAccess;
  if (typeof baseApplyServerAccessForWorkOrders === 'function') {
    window.applyMachineparkServerAccess = function(body) {
      const result = baseApplyServerAccessForWorkOrders(body);
      setTimeout(() => ensureSettingsCard(), 0);
      return result;
    };
  }

  setTimeout(() => {
    ensureSettingsCard();
    if (window.Clerk?.isSignedIn) loadWorkOrderTemplates().catch(() => {});
  }, 700);
})();
} catch (error) {
  console.error('[Machinepark feature work-orders-v1]', error);
}

/* mill-workorder-times-v1 */
try {
(() => {
  function millNorm(value) {
    return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase().replace(/\s+/g, ' ');
  }

  function isMillWorkOrder(workOrder) {
    const name = millNorm(workOrder?.templateName || workOrder?.name || '');
    return name.includes('molen') || name.includes('grinder');
  }

  function isMillTimeField(field) {
    const label = millNorm(field?.label || '');
    if (!label) return false;
    return /\b(tijd|tijden|timer|time|seconde|seconden|second|seconds|duur)\b/.test(label)
      || /(^|\s)sec(?:\.|\s|$)/.test(label);
  }

  function isMillCountField(field) {
    const label = millNorm(field?.label || '');
    if (!label) return false;
    return /\b(aantal|aantallen|count|counts)\b/.test(label);
  }

  function isMillGrindField(field) {
    const label = millNorm(field?.label || '');
    if (!label) return false;
    return /\b(maalgraad|maalstand|maling|grind|grinder setting|grind setting)\b/.test(label);
  }

  function isMillTrackedField(field) {
    return isMillTimeField(field) || isMillCountField(field) || isMillGrindField(field);
  }

  function millRecordSortKey(record) {
    const captured = String(record?.workOrder?.capturedAt || record?.updatedAt || record?.createdAt || '');
    const date = /^\d{4}-\d{2}-\d{2}$/.test(String(record?.date || ''))
      ? String(record.date)
      : captured.slice(0, 10);
    return `${date}|${captured}`;
  }

  function millRecordedDate(record) {
    const direct = String(record?.date || '');
    if (/^\d{4}-\d{2}-\d{2}$/.test(direct)) {
      try { return typeof dateFmt === 'function' ? dateFmt(direct) : direct; } catch (_) { return direct; }
    }
    const stamp = String(record?.workOrder?.capturedAt || record?.updatedAt || record?.createdAt || '');
    if (!stamp) return '—';
    const d = new Date(stamp);
    return Number.isNaN(d.getTime()) ? stamp.slice(0, 10) : d.toLocaleDateString('nl-BE');
  }

  function latestMillTimesForDevice(deviceId) {
    const records = (Array.isArray(state?.maintenance) ? state.maintenance : [])
      .filter((record) => record?.deviceId === deviceId && isMillWorkOrder(record?.workOrder))
      .sort((a, b) => millRecordSortKey(b).localeCompare(millRecordSortKey(a)));

    const byLabel = new Map();
    const byId = new Map();
    const entries = [];

    records.forEach((record) => {
      (Array.isArray(record?.workOrder?.fields) ? record.workOrder.fields : []).forEach((field) => {
        if (!isMillTrackedField(field)) return;
        const value = String(field?.value ?? '').trim();
        if (!value) return;
        const labelKey = millNorm(field?.label || '');
        const idKey = String(field?.id || '').trim();
        if (!labelKey || byLabel.has(labelKey)) return;
        const entry = {
          id: idKey,
          label: String(field?.label || 'Moleninstelling').trim(),
          labelKey,
          value,
          date: millRecordedDate(record),
          sortKey: millRecordSortKey(record),
          maintenanceId: String(record?.id || ''),
        };
        byLabel.set(labelKey, entry);
        if (idKey && !byId.has(idKey)) byId.set(idKey, entry);
        entries.push(entry);
      });
    });

    return { entries, byLabel, byId };
  }
  window.machineparkLatestMillTimesForDevice = latestMillTimesForDevice;

  function deviceIdForWorkOrderEditor(editor) {
    const card = editor?.closest('.maintenance-machine-card');
    if (card?.dataset?.maintenanceDevice) return card.dataset.maintenanceDevice;
    const modal = editor?.closest('#modal') || document.querySelector('#modal');
    return String(modal?.querySelector('[name="deviceId"]')?.value || '');
  }

  function selectedWorkOrderLooksLikeMill(editor) {
    const select = editor?.querySelector('.workorder-maintenance-select');
    if (!select || !select.value || select.value === '__saved__') return false;
    const text = millNorm(select.selectedOptions?.[0]?.textContent || '');
    return text.includes('molen') || text.includes('grinder');
  }

  function clearMillHints(editor) {
    editor?.querySelectorAll('.workorder-last-value-hint').forEach((node) => node.remove());
  }

  function annotateMillWorkOrderEditor(editor) {
    if (!editor) return;
    clearMillHints(editor);
    if (!selectedWorkOrderLooksLikeMill(editor)) return;
    const deviceId = deviceIdForWorkOrderEditor(editor);
    if (!deviceId) return;
    const latest = latestMillTimesForDevice(deviceId);
    if (!latest.entries.length) return;

    editor.querySelectorAll('.workorder-maintenance-field').forEach((fieldBox) => {
      const input = fieldBox.querySelector('[data-workorder-field]');
      const labelNode = fieldBox.querySelector('label');
      if (!input || !labelNode) return;
      const label = String(labelNode.textContent || '').replace(/\s*\*\s*$/, '').trim();
      if (!isMillTrackedField({ label })) return;
      const id = String(input.dataset.workorderField || '');
      const previous = (id && latest.byId.get(id)) || latest.byLabel.get(millNorm(label));
      if (!previous) return;
      const hint = document.createElement('div');
      hint.className = 'workorder-last-value-hint';
      hint.textContent = `Vorige waarde: ${previous.value} · ${previous.date}`;
      fieldBox.appendChild(hint);
    });
  }

  let hintFrame = 0;
  function annotateVisibleMillWorkOrders() {
    if (hintFrame) cancelAnimationFrame(hintFrame);
    hintFrame = requestAnimationFrame(() => {
      hintFrame = 0;
      document.querySelectorAll('#modal [data-workorder-editor]').forEach(annotateMillWorkOrderEditor);
    });
  }

  document.addEventListener('change', (event) => {
    if (event.target?.classList?.contains('workorder-maintenance-select')) setTimeout(annotateVisibleMillWorkOrders, 0);
  });

  const modalRoot = document.getElementById('modalBackdrop') || document.body;
  const observer = new MutationObserver(() => annotateVisibleMillWorkOrders());
  observer.observe(modalRoot, { childList: true, subtree: true });

  function millLatestTimesHtml(deviceId) {
    const latest = latestMillTimesForDevice(deviceId);
    if (!latest.entries.length) return '';
    const rows = latest.entries
      .sort((a, b) => a.label.localeCompare(b.label, 'nl-BE', { numeric: true, sensitivity: 'base' }))
      .map((entry) => `<div class="mill-latest-time"><span>${esc(entry.label)}</span><strong>${esc(entry.value)}</strong><small>Laatst genoteerd op ${esc(entry.date)}</small></div>`)
      .join('');
    return `<div class="mill-latest-times-panel"><div class="mill-latest-times-head"><strong>Laatste molengegevens</strong><span>Steeds de recentste ingevulde waarde per tijd, aantal en maalgraad</span></div><div class="mill-latest-times-grid">${rows}</div></div>`;
  }
  window.machineparkMillLatestTimesHtml = millLatestTimesHtml;

  window.machineparkInsertMillTimes = function(id) {
    const html = millLatestTimesHtml(id);
    if (!html) return;
    const grid = document.querySelector('#modal .modal-body .form-grid');
    if (!grid || grid.querySelector('.mill-latest-times-block')) return;
    const block = document.createElement('div');
    block.className = 'field full mill-latest-times-block';
    block.innerHTML = html;
    const history = [...grid.children].find((node) => node.querySelector?.('.history-group'));
    if (history) grid.insertBefore(block, history);
    else grid.appendChild(block);
  };
})();
} catch (error) {
  console.error('[Machinepark feature mill-workorder-times-v1]', error);
}

/* device-photo-folder-import-v1 */
try {
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
} catch (error) {
  console.error('[Machinepark feature device-photo-folder-import-v1]', error);
}

/* shared-data-safety-v1 */
try {
(() => {
  const host = String(location.hostname || '').toLowerCase();
  const nonProductionHost =
    host === 'localhost' ||
    host === '127.0.0.1' ||
    host.startsWith('deploy-preview-') ||
    host.startsWith('development--');

  window.machineparkServiceBlobWritesEnabled = !nonProductionHost;

  if (nonProductionHost && typeof window.machineparkPersistServicePhotos === 'function') {
    // Development en production delen de centrale snapshot. Een preview mag daarom
    // bestaande verslagfoto’s niet automatisch naar refs omzetten die de oude main
    // nog niet kan weergeven. Na een expliciete merge activeert dit vanzelf op productie.
    window.machineparkPersistServicePhotos = async function(_storeName, _entityId, photos) {
      return (Array.isArray(photos) ? photos : [])
        .filter((src) => typeof src === 'string' && src.trim())
        .slice(0, 5);
    };
  }
})();
} catch (error) {
  console.error('[Machinepark feature shared-data-safety-v1]', error);
}

/* photo-delete-cleanup-v1 */
try {
(() => {
  const PART_PHOTO_CLEANUP_URL = '/machinepark/synology/api/part-photos.php';
  const partPhotoDeleteRequests = new Set();

  function isStoredPartPhoto(value) {
    return String(value || '').includes('/machinepark/synology/api/part-photos.php?');
  }

  async function deleteStoredPartPhoto(partId) {
    const headers = await centralHeaders(true);
    const res = await fetch(PART_PHOTO_CLEANUP_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify({ partId, photo: '' }),
      cache: 'no-store',
    });
    const text = await res.text();
    let body = {};
    try { body = text ? JSON.parse(text) : {}; } catch (_) {}
    if (!res.ok) throw new Error(body.error || text || `Onderdeelfoto verwijderen mislukt (${res.status})`);
    return true;
  }

  const basePersistPartPhotoForCleanup = window.machineparkPersistPartPhoto;
  window.machineparkPersistPartPhoto = async function(partId, photo) {
    const id = String(partId || '');
    const value = String(photo || '').trim();
    const previous = (Array.isArray(state?.parts) ? state.parts : []).find((part) => String(part.id) === id)?.photo || '';
    const deleteRequested = partPhotoDeleteRequests.delete(id);
    const replacingStoredPhoto = isStoredPartPhoto(previous) && value.startsWith('data:image/');

    if (isStoredPartPhoto(previous) && (deleteRequested || replacingStoredPhoto)) {
      // De server verwijdert hier zowel de volledige foto als de .thumb-variant.
      await deleteStoredPartPhoto(id);
    }
    if (deleteRequested) return '';
    return basePersistPartPhotoForCleanup(id, value);
  };

  const baseOpenPartForPhotoCleanup = openPart;
  openPart = function(id) {
    const partId = String(id || '');
    if (partId) partPhotoDeleteRequests.delete(partId);
    baseOpenPartForPhotoCleanup(id);
    if (!partId) return;

    setTimeout(() => {
      const part = (Array.isArray(state?.parts) ? state.parts : []).find((item) => String(item.id) === partId);
      if (!part?.photo) return;
      if (window.machineparkAccessReady && typeof window.machineparkHasPermission === 'function' && !window.machineparkHasPermission('parts.edit')) return;

      const preview = document.getElementById('photoPreview');
      const fileInput = document.getElementById('photoFile');
      const field = preview?.closest('.field');
      if (!preview || !field || field.querySelector('[data-remove-part-photo]')) return;

      const actions = document.createElement('div');
      actions.style.cssText = 'margin-top:8px;display:flex;align-items:center;gap:9px;flex-wrap:wrap';
      actions.innerHTML = '<button type="button" class="btn small danger" data-remove-part-photo>Foto verwijderen</button><span class="muted" data-remove-part-photo-status style="font-size:11px"></span>';
      field.appendChild(actions);

      const removeButton = actions.querySelector('[data-remove-part-photo]');
      const status = actions.querySelector('[data-remove-part-photo-status]');
      removeButton.onclick = () => {
        partPhotoDeleteRequests.add(partId);
        if (fileInput) fileInput.value = '';
        preview.innerHTML = '<div style="padding:8px">Foto wordt bij <strong>Opslaan</strong> volledig verwijderd.</div>';
        removeButton.disabled = true;
        if (status) status.textContent = 'Volledige foto + thumbnail worden verwijderd.';
      };

      if (fileInput) fileInput.addEventListener('change', () => {
        if (!fileInput.files?.length) return;
        partPhotoDeleteRequests.delete(partId);
        removeButton.disabled = false;
        if (status) status.textContent = 'Nieuwe foto vervangt de oude foto en thumbnail.';
      });
    }, 0);
  };
  window.openPart = openPart;
})();
} catch (error) {
  console.error('[Machinepark feature photo-delete-cleanup-v1]', error);
}

/* fault-import-undo-v1 */
try {
(() => {
  async function undoFaultExcelImport() {
    const button = document.getElementById('undoFaultExcelImportBtn');
    if (!button) return;
    if (!confirm('Laatste storingsimport ongedaan maken? De storingsbibliotheek wordt teruggezet naar exact de toestand van vlak vóór die import. Dit kan alleen als er nadien geen andere storingswijzigingen zijn gebeurd.')) return;

    const oldText = button.textContent;
    button.disabled = true;
    button.textContent = 'Import terugdraaien…';
    try {
      const headers = await centralHeaders(true);
      const res = await fetch('/machinepark/synology/api/fault-library.php', {
        method: 'POST',
        cache: 'no-store',
        headers,
        body: JSON.stringify({ action: 'undo-last-import' }),
      });
      const text = await res.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (_) {}
      if (!res.ok) throw new Error(data.error || text || `Terugdraaien mislukt (${res.status})`);

      if (typeof window.machineparkLoadFaultLibrary === 'function') await window.machineparkLoadFaultLibrary(true).catch(() => {});
      if (typeof window.machineparkRenderFaultLibrary === 'function') window.machineparkRenderFaultLibrary();
      toast(`Storingsimport ongedaan gemaakt · ${data.restoredCount ?? 0} storing${Number(data.restoredCount) === 1 ? '' : 'en'} hersteld`);
    } catch (error) {
      console.error('Storingsimport ongedaan maken', error);
      alert('Import kon niet ongedaan worden gemaakt: ' + (error?.message || 'onbekende fout'));
    } finally {
      button.disabled = false;
      button.textContent = oldText;
    }
  }

  function bindFaultImportUndo() {
    const button = document.getElementById('undoFaultExcelImportBtn');
    if (button) button.onclick = undoFaultExcelImport;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bindFaultImportUndo, { once: true });
  else bindFaultImportUndo();
})();
} catch (error) {
  console.error('[Machinepark feature fault-import-undo-v1]', error);
}

/* service-drafts-v1 */
try {
(() => {
  const AUTOSAVE_DELAY = 1400;
  const SERVICE_KINDS = new Set(['maintenance','breakdowns']);
  let activeDraft = null;
  let autosaveTimer = null;
  let saveChain = Promise.resolve();

  const baseOpenMaintenanceForDrafts = openMaintenance;
  const baseOpenBreakdownForDrafts = openBreakdown;
  const baseCloseModalForDrafts = closeModal;
  const baseRenderAllForDrafts = renderAll;
  const baseRenderGlobalSearchForDrafts = renderGlobalSearchResults;
  const baseDeviceTimelineForDrafts = deviceUnifiedTimelineHtml;

  function kindInfo(kind) {
    return kind === 'maintenance'
      ? { store:'maintenance', singular:'Onderhoud', plural:'onderhoud', prefix:'mnt', headerPrefix:'mntdraft', addPermission:'maintenance.add', view:'maintenance' }
      : { store:'breakdowns', singular:'Depannage', plural:'depannages', prefix:'brk', headerPrefix:'brkdraft', addPermission:'breakdowns.add', view:'breakdowns' };
  }

  function isDraftRecord(item) { return Boolean(item?.isDraft === true); }
  function isDraftHeader(item, kind) { return Boolean(isDraftRecord(item) && item.draftRole === 'header' && item.draftKind === kind); }
  function isDraftItem(item, kind, headerId = '') { return Boolean(isDraftRecord(item) && item.draftRole === 'item' && item.draftKind === kind && (!headerId || item.draftBatchId === headerId)); }
  function draftHeader(kind, id) { return (state[kindInfo(kind).store] || []).find(item => isDraftHeader(item, kind) && item.id === id) || null; }
  function draftItems(kind, headerId) { return (state[kindInfo(kind).store] || []).filter(item => isDraftItem(item, kind, headerId)); }
  function canManageDraft(kind) {
    const permission = kindInfo(kind).addPermission;
    if (window.machineparkAccessReady && typeof window.machineparkHasPermission === 'function') return window.machineparkHasPermission(permission);
    return true;
  }

  function withRegularServiceState(callback) {
    const maintenance = state.maintenance;
    const breakdowns = state.breakdowns;
    state.maintenance = (maintenance || []).filter(item => !isDraftRecord(item));
    state.breakdowns = (breakdowns || []).filter(item => !isDraftRecord(item));
    try { return callback(); }
    finally { state.maintenance = maintenance; state.breakdowns = breakdowns; }
  }

  renderAll = function() {
    withRegularServiceState(() => baseRenderAllForDrafts());
    renderDraftPanels();

    // machinepark-service-visit-draft-rerender-v1
    // baseRenderAllForDrafts bevat ook de serviceverslag-renderer, maar die werd
    // hierboven aangeroepen terwijl alle draftrecords tijdelijk uit state waren.
    // Nu state hersteld is, render de Serviceconcepten opnieuw met de echte data.
    if (typeof window.machineparkRenderServiceVisits === 'function') {
      window.machineparkRenderServiceVisits();
    }
  };
  window.renderAll = renderAll;

  renderGlobalSearchResults = function() {
    return withRegularServiceState(() => baseRenderGlobalSearchForDrafts());
  };
  window.renderGlobalSearchResults = renderGlobalSearchResults;

  deviceUnifiedTimelineHtml = function(device) {
    return withRegularServiceState(() => baseDeviceTimelineForDrafts(device));
  };
  window.deviceUnifiedTimelineHtml = deviceUnifiedTimelineHtml;

  function ensureDraftPanel(kind) {
    const info = kindInfo(kind);
    const view = document.getElementById(`view-${info.view}`);
    if (!view) return null;
    let panel = document.getElementById(`${info.store}DraftPanel`);
    if (panel) return panel;
    panel = document.createElement('div');
    panel.id = `${info.store}DraftPanel`;
    panel.className = 'service-draft-panel';
    const table = view.querySelector('.table-wrap');
    if (table) table.parentNode.insertBefore(panel, table);
    else view.appendChild(panel);
    return panel;
  }

  function draftDateText(value) {
    if (!value) return 'nog niet opgeslagen';
    try { return new Date(value).toLocaleString('nl-BE', { dateStyle:'short', timeStyle:'short' }); }
    catch (_) { return String(value); }
  }

  function draftDeviceText(kind, headerId) {
    const selected = draftItems(kind, headerId).filter(item => item.draftSelected !== false);
    const names = selected.map(item => {
      const device = state.devices.find(candidate => candidate.id === item.deviceId);
      return device?.assetCode || device?.model || '';
    }).filter(Boolean);
    if (!names.length) return 'nog geen toestel geselecteerd';
    const first = names.slice(0, 3).join(', ');
    return `${selected.length} toestel${selected.length === 1 ? '' : 'len'}${first ? ` · ${first}${names.length > 3 ? ' …' : ''}` : ''}`;
  }

  function renderDraftPanel(kind) {
    const panel = ensureDraftPanel(kind);
    if (!panel) return;
    const info = kindInfo(kind);
    const headers = (state[info.store] || []).filter(item => isDraftHeader(item, kind) && !(kind === 'breakdowns' && item.serviceKind === 'other')).sort((a,b) => String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')));
    if (!headers.length) { panel.classList.remove('show'); panel.innerHTML = ''; return; }
    const manageable = canManageDraft(kind);
    panel.classList.add('show');
    panel.innerHTML = `<div class="service-draft-head"><strong>Concepten (${headers.length})</strong><span class="muted" style="font-size:11px">Centraal gesynchroniseerd · verdergaan op pc, tablet of gsm.</span></div><div class="service-draft-list">${headers.map(header => {
      const location = String(header.locationLabel || '').trim() || 'Nog geen locatie';
      const title = `${location}`;
      const actions = manageable ? `<div class="service-draft-actions"><button type="button" class="btn small service-draft-button" data-service-draft-open="${esc(header.id)}" data-service-draft-kind="${kind}">Verdergaan</button><button type="button" class="btn small danger" data-service-draft-delete="${esc(header.id)}" data-service-draft-kind="${kind}">Verwijderen</button></div>` : '';
      return `<div class="service-draft-row"><div><div class="service-draft-row-title"><span class="service-draft-badge">CONCEPT</span>${esc(title)}</div><div class="service-draft-row-meta">${esc(draftDeviceText(kind, header.id))} · laatst aangepast ${esc(draftDateText(header.updatedAt))}</div></div>${actions}</div>`;
    }).join('')}</div>`;
  }

  function renderDraftPanels() { renderDraftPanel('maintenance'); renderDraftPanel('breakdowns'); }

  function setSaveStatus(text, mode = '') {
    const el = document.querySelector('#modal .service-draft-save-status');
    if (!el) return;
    el.className = `service-draft-save-status${mode ? ` ${mode}` : ''}`;
    el.textContent = text || '';
  }

  function existingItemMap(kind, headerId) {
    return new Map(draftItems(kind, headerId).map(item => [item.deviceId, item]));
  }

  function collectUsedParts(card, kind) {
    const selector = kind === 'maintenance' ? '.maintenance-device-usage-list .usage-row' : '.breakdown-device-usage-list .usage-row';
    return [...card.querySelectorAll(selector)].map(row => ({
      partId: row.querySelector('.usage-part')?.value || '',
      qty: Number(row.querySelector('.usage-qty')?.value || 1),
    })).filter(item => item.partId && item.qty > 0);
  }

  function collectOneOff(card) {
    const root = card.querySelector('.service-oneoff-parts');
    if (typeof window.machineparkCollectServiceOneOff === 'function') return window.machineparkCollectServiceOneOff(root);
    return [];
  }

  function collectWorkOrderLoose(card, existing = null) {
    const editor = card?.querySelector('[data-workorder-editor]');
    if (!editor) return existing || null;
    const select = editor.querySelector('.workorder-maintenance-select');
    if (!select || !select.value) return null;
    const definition = editor._activeWorkOrderDefinition || editor._savedWorkOrder || existing;
    if (!definition || !Array.isArray(definition.fields)) return existing || null;
    return {
      templateId: definition.templateId || definition.id || editor._savedWorkOrder?.templateId || existing?.templateId || '',
      templateName: definition.templateName || definition.name || editor._savedWorkOrder?.templateName || existing?.templateName || 'Werkbon',
      templateVersion: Number(definition.templateVersion || definition.version || editor._savedWorkOrder?.templateVersion || existing?.templateVersion || 1),
      fields: definition.fields.map(field => {
        const input = editor.querySelector(`[data-workorder-field="${field.id}"]`);
        const value = field.type === 'checkbox' ? Boolean(input?.checked) : String(input?.value ?? '').trim();
        return { id:field.id, label:field.label, type:field.type, required:Boolean(field.required), options:Array.isArray(field.options) ? [...field.options] : [], value };
      }),
      capturedAt: new Date().toISOString(),
    };
  }

  function validateWorkOrder(workOrder) {
    if (!workOrder || !Array.isArray(workOrder.fields)) return;
    const missing = workOrder.fields.find(field => field.required && (field.type === 'checkbox' ? !field.value : !String(field.value ?? '').trim()));
    if (missing) throw new Error(`Vul het verplichte werkbonveld “${missing.label || 'Werkbon'}” in.`);
  }

  function oneOffRowHtml(item = {}, disabled = false) {
    const off = disabled ? ' disabled' : '';
    const supplier = esc(String(item.supplier || ''));
    const code = esc(String(item.supplierCode || ''));
    const description = esc(String(item.description || ''));
    const qty = Math.max(0.001, normalizePartQuantity(item.qty, 1));
    return `<div class="service-oneoff-row"><input class="service-oneoff-supplier" type="text" maxlength="120" placeholder="Leverancier" value="${supplier}"${off}><input class="service-oneoff-code" type="text" maxlength="120" placeholder="Leveranciercode" value="${code}"${off}><input class="service-oneoff-description" type="text" maxlength="300" placeholder="Omschrijving" value="${description}"${off}><input class="service-oneoff-qty" type="number" min="0.001" step="0.001" inputmode="decimal" aria-label="Aantal" value="${qty}"${off}><button type="button" class="remove-line service-oneoff-remove" data-remove-service-oneoff aria-label="Eenmalig onderdeel verwijderen"${off}>×</button></div>`;
  }

  function restoreOneOff(card, items, enabled) {
    const list = card.querySelector('.service-oneoff-list');
    if (!list) return;
    const rows = Array.isArray(items) && items.length ? items : [{}];
    list.innerHTML = rows.map(item => oneOffRowHtml(item, !enabled)).join('');
  }

  function photoGridHtml(photos) {
    const list = (Array.isArray(photos) ? photos : []).filter(Boolean).slice(0,5);
    if (!list.length) return '<div class="muted" style="font-size:11px;margin:4px 0 8px">Nog geen foto’s toegevoegd.</div>';
    return `<div class="service-photo-grid">${list.map((src,index) => {
      const preview = typeof window.machineparkThumbnailRef === 'function' ? window.machineparkThumbnailRef(src) : src;
      return `<div class="service-photo-item"><img src="${esc(preview)}" data-full-src="${esc(src)}" data-photo-lightbox loading="lazy" decoding="async" alt="Verslagfoto ${index+1}"><label><input type="checkbox" class="service-photo-remove" value="${index}"> Verwijderen</label></div>`;
    }).join('')}</div>`;
  }

  function restorePhotoEditor(card, kind, photos, enabled) {
    const editor = card.querySelector('.service-photo-editor');
    if (!editor) return;
    const inputClass = kind === 'maintenance' ? 'maintenance-machine-photos' : 'breakdown-machine-photos';
    editor.innerHTML = `<label>Foto’s bij verslag</label>${photoGridHtml(photos)}<input class="service-photo-files ${inputClass}" type="file" accept="image/*" multiple ${enabled ? '' : 'disabled'}><div class="muted" style="font-size:11px;margin-top:4px">Maximaal 5 foto’s per verslag. Foto’s worden automatisch verkleind en apart opgeslagen.</div><div class="service-photo-selected muted" style="font-size:11px;margin-top:4px"></div>`;
  }

  async function collectDraftPhotos(card, kind, itemId, existingPhotos) {
    const editor = card.querySelector('.service-photo-editor');
    if (!editor) return Array.isArray(existingPhotos) ? existingPhotos : [];
    const existing = (Array.isArray(existingPhotos) ? existingPhotos : []).filter(Boolean).slice(0,5);
    const remove = new Set([...editor.querySelectorAll('.service-photo-remove:checked')].map(input => Number(input.value)));
    const files = [...(editor.querySelector('.service-photo-files')?.files || [])].filter(file => file && file.size);
    if (!remove.size && !files.length) return existing;
    const kept = existing.filter((_,index) => !remove.has(index));
    if (kept.length + files.length > 5) throw new Error('Maximaal 5 foto’s per onderhouds- of depannageconcept.');
    const added = [];
    for (const file of files) added.push(await compressImage(file));
    let photos = [...kept, ...added].filter(Boolean).slice(0,5);
    if (typeof window.machineparkPersistServicePhotos === 'function') photos = await window.machineparkPersistServicePhotos(kindInfo(kind).store, itemId, photos);
    restorePhotoEditor(card, kind, photos, card.querySelector(kind === 'maintenance' ? '.maintenance-machine-check' : '.breakdown-machine-check')?.checked === true);
    return photos;
  }

  function collectWorkSessionsLoose(form) {
    const rows = [...form.querySelectorAll('.service-work-session-row')].map(row => ({
      date: String(row.querySelector('[name="workSessionDate"]')?.value || ''),
      minutes: Math.max(0, Math.round(Number(row.querySelector('[name="workSessionMinutes"]')?.value || 0))),
    }));
    return rows.filter(row => row.date || row.minutes > 0);
  }

  function collectDraftHeader(kind) {
    const form = document.getElementById('modalForm');
    const info = kindInfo(kind);
    const existing = draftHeader(kind, activeDraft?.id) || activeDraft?.header || null;
    const locationInput = document.getElementById(kind === 'maintenance' ? 'maintenanceLocationSearch' : 'breakdownLocationSearch');
    const locationKey = document.getElementById(kind === 'maintenance' ? 'maintenanceLocationKey' : 'breakdownLocationKey');
    const date = form?.querySelector('[name="date"]')?.value || '';
    const time = form?.querySelector('[name="time"]')?.value || '';
    const technician = form?.querySelector('[name="technician"]')?.value.trim() || '';
    const workSessions = collectWorkSessionsLoose(form);
    const totalMinutes = workSessions.reduce((sum,row) => sum + Number(row.minutes || 0), 0);
    const now = new Date().toISOString();
    return {
      ...(existing || {}), id:activeDraft.id, isDraft:true, draftRole:'header', draftKind:kind, draftBatchId:activeDraft.id,
      locationKey:String(locationKey?.value || ''), locationLabel:String(locationInput?.value || '').trim(),
      date, time, technician, workSessions, hours:totalMinutes / 60,
      serviceKind:String(form?.querySelector('[name="serviceKind"]')?.value || existing?.serviceKind || ''),
      workTypeName:String(form?.querySelector('[name="workTypeName"]')?.value || existing?.workTypeName || '').trim(),
      createdAt:existing?.createdAt || activeDraft.createdAt || now, updatedAt:now,
      draftSchema:1,
    };
  }

  function cardHasContent(card, kind, existing) {
    const checked = card.querySelector(kind === 'maintenance' ? '.maintenance-machine-check' : '.breakdown-machine-check')?.checked === true;
    if (checked || existing) return true;
    if (kind === 'maintenance') return Boolean(card.querySelector('.maintenance-machine-notes')?.value.trim());
    return Boolean(card.querySelector('.breakdown-machine-issue')?.value.trim() || card.querySelector('.breakdown-machine-diagnosis')?.value.trim() || card.querySelector('.breakdown-machine-solution')?.value.trim());
  }

  async function collectDraftItems(kind) {
    const info = kindInfo(kind);
    const existing = activeDraft.itemByDevice;
    const cards = [...document.querySelectorAll('#modal .maintenance-machine-card')].filter(card => kind === 'maintenance' ? Boolean(card.dataset.maintenanceDevice) : Boolean(card.dataset.breakdownDevice));
    const records = [];
    for (const card of cards) {
      const deviceId = kind === 'maintenance' ? card.dataset.maintenanceDevice : card.dataset.breakdownDevice;
      const old = existing.get(deviceId) || null;
      if (!cardHasContent(card, kind, old)) continue;
      const checked = card.querySelector(kind === 'maintenance' ? '.maintenance-machine-check' : '.breakdown-machine-check')?.checked === true;
      const id = old?.id || uid(info.prefix);
      const usedParts = collectUsedParts(card, kind);
      const oneOffParts = collectOneOff(card);
      const photos = await collectDraftPhotos(card, kind, id, old?.photos || []);
      const now = new Date().toISOString();
      let record = {
        ...(old || {}), id, isDraft:true, draftRole:'item', draftKind:kind, draftBatchId:activeDraft.id, draftSelected:checked,
        deviceId, usedParts, oneOffParts, photos, createdAt:old?.createdAt || now, updatedAt:now, draftSchema:1,
      };
      if (kind === 'maintenance') {
        record.type = card.querySelector('.maintenance-machine-type')?.value || 'Halfjaarlijks';
        record.notes = card.querySelector('.maintenance-machine-notes')?.value.trim() || '';
        record.workOrder = collectWorkOrderLoose(card, old?.workOrder || null);
      } else {
        record.priority = card.querySelector('.breakdown-machine-priority')?.value || 'Normaal';
        record.status = card.querySelector('.breakdown-machine-status')?.value || 'Open';
        record.issue = card.querySelector('.breakdown-machine-issue')?.value.trim() || '';
        record.diagnosis = card.querySelector('.breakdown-machine-diagnosis')?.value.trim() || '';
        record.solution = card.querySelector('.breakdown-machine-solution')?.value.trim() || '';
        record.workOrder = collectWorkOrderLoose(card, old?.workOrder || null);
        const holder = card.querySelector('.fault-inline-tools');
        record.faultRef = holder?._machineparkFaultSnapshot || old?.faultRef || null;
      }
      records.push(record);
    }
    return records;
  }

  function writeDraftDirect(kind, header, items) {
    const storeName = kindInfo(kind).store;
    const previousIds = new Set([...activeDraft.itemByDevice.values()].map(item => item.id));
    const keepIds = new Set(items.map(item => item.id));
    return new Promise((resolve,reject) => {
      let tr;
      try { tr = db.transaction(storeName, 'readwrite'); }
      catch (error) { reject(error); return; }
      const store = tr.objectStore(storeName);
      store.put(header);
      items.forEach(item => store.put(item));
      previousIds.forEach(id => { if (!keepIds.has(id)) store.delete(id); });
      tr.oncomplete = () => { scheduleCentralSync(); resolve(); };
      tr.onerror = () => reject(tr.error || new Error('Concept opslaan mislukt.'));
      tr.onabort = () => reject(tr.error || new Error('Concept opslaan afgebroken.'));
    });
  }

  async function refreshDraftState(kind) {
    const storeName = kindInfo(kind).store;
    state[storeName] = await getAll(storeName);
    renderDraftPanels();
  }

  async function syncDraftAcrossDevices(kind, { pullLatest = false } = {}) {
    if (!navigator.onLine || !window.Clerk?.isSignedIn || typeof window.machineparkSyncOnlineNow !== 'function') return false;
    try {
      await window.machineparkSyncOnlineNow({ quiet:true });
      if (pullLatest) await refreshDraftState(kind);
      return true;
    } catch (error) {
      console.warn('Concept synchroniseren tussen toestellen', error);
      return false;
    }
  }
  window.machineparkSyncDraftAcrossDevices = syncDraftAcrossDevices;

  async function saveDraftInternal({ manual = false, force = false } = {}) {
    const current = activeDraft;
    if (!current || !SERVICE_KINDS.has(current.kind)) return null;
    if (!force && !current.touched) return { header:current.header, items:[...current.itemByDevice.values()] };
    setSaveStatus('Concept opslaan…', 'busy');
    const header = collectDraftHeader(current.kind);
    const items = await collectDraftItems(current.kind);
    if (activeDraft !== current) return null;
    await writeDraftDirect(current.kind, header, items);
    current.persisted = true;
    current.touched = false;
    current.header = header;
    current.itemByDevice = new Map(items.map(item => [item.deviceId, item]));
    await refreshDraftState(current.kind);
    const time = new Date().toLocaleTimeString('nl-BE', { hour:'2-digit', minute:'2-digit' });
    setSaveStatus(navigator.onLine ? `Concept opgeslagen om ${time} · automatische synchronisatie actief` : `Lokaal opgeslagen om ${time} · synchroniseert zodra internet beschikbaar is`);
    if (manual) {
      const synced = await syncDraftAcrossDevices(current.kind);
      toast(synced ? `${kindInfo(current.kind).singular}concept bewaard en gesynchroniseerd` : `${kindInfo(current.kind).singular}concept bewaard`);
    }
    return { header, items };
  }

  function queueDraftSave(options = {}) {
    clearTimeout(autosaveTimer);
    const current = activeDraft;
    saveChain = saveChain.catch(() => {}).then(() => {
      if (!current || activeDraft !== current) return null;
      return saveDraftInternal(options);
    });
    return saveChain;
  }

  function scheduleDraftAutosave() {
    if (!activeDraft || activeDraft.finalizing || activeDraft.restoring) return;
    activeDraft.touched = true;
    setSaveStatus('Wijzigingen wachten op autosave…');
    clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(() => queueDraftSave().catch(error => { console.warn('Concept autosave', error); setSaveStatus(error?.message || 'Concept opslaan mislukt', 'error'); }), AUTOSAVE_DELAY);
  }

  function setUsageRows(card, kind, items, enabled) {
    const list = card.querySelector(kind === 'maintenance' ? '.maintenance-device-usage-list' : '.breakdown-device-usage-list');
    if (!list) return;
    const rows = Array.isArray(items) && items.length ? items : [{partId:'',qty:1}];
    list.innerHTML = rows.map(item => usageRowHtml(item, true)).join('');
    list.querySelectorAll('.usage-search,.usage-qty,.remove-line').forEach(el => { el.disabled = !enabled; });
  }

  function restoreWorkOrder(card, saved, enabled) {
    if (!saved) return;
    const editor = card.querySelector('[data-workorder-editor]');
    if (!editor) return;
    const select = editor.querySelector('.workorder-maintenance-select');
    if (!select) return;
    editor._savedWorkOrder = saved;
    let option = [...select.options].find(item => item.value === '__saved__');
    if (!option) {
      option = document.createElement('option');
      option.value = '__saved__';
      select.insertBefore(option, select.options[1] || null);
    }
    option.textContent = `Bewaarde werkbon · ${saved.templateName || 'Werkbon'} · v${saved.templateVersion || 1}`;
    select.value = '__saved__';
    select.dispatchEvent(new Event('change', { bubbles:true }));
    editor.querySelectorAll('input,select,textarea').forEach(el => { el.disabled = !enabled; });
  }

  function restoreFaultRef(card, saved) {
    if (!saved) return;
    const holder = card.querySelector('.fault-inline-tools');
    if (!holder) return;
    holder._machineparkFaultSnapshot = saved;
    const selected = holder.querySelector('.fault-picker-selected');
    if (selected) selected.textContent = `Gekoppeld: ${[saved.code, saved.name].filter(Boolean).join(' — ')}`;
  }

  function restoreCard(kind, card, item) {
    if (!item) return;
    const enabled = item.draftSelected !== false;
    const checkbox = card.querySelector(kind === 'maintenance' ? '.maintenance-machine-check' : '.breakdown-machine-check');
    if (checkbox) checkbox.checked = enabled;
    if (kind === 'maintenance') {
      const type = card.querySelector('.maintenance-machine-type'); if (type) type.value = item.type || 'Halfjaarlijks';
      const notes = card.querySelector('.maintenance-machine-notes'); if (notes) notes.value = item.notes || '';
    } else {
      const priority = card.querySelector('.breakdown-machine-priority'); if (priority) priority.value = item.priority || 'Normaal';
      const status = card.querySelector('.breakdown-machine-status'); if (status) status.value = item.status || 'Open';
      const issue = card.querySelector('.breakdown-machine-issue'); if (issue) issue.value = item.issue || '';
      const diagnosis = card.querySelector('.breakdown-machine-diagnosis'); if (diagnosis) diagnosis.value = item.diagnosis || '';
      const solution = card.querySelector('.breakdown-machine-solution'); if (solution) solution.value = item.solution || '';
    }
    setUsageRows(card, kind, item.usedParts || [], enabled);
    restoreOneOff(card, item.oneOffParts || [], enabled);
    restorePhotoEditor(card, kind, item.photos || [], enabled);
    if (kind === 'maintenance') setMaintenanceMachineEnabled(card, enabled); else setBreakdownMachineEnabled(card, enabled);
  }

  function draftGroup(kind, header, items) {
    const groups = kind === 'maintenance' ? maintenanceLocationGroups() : breakdownLocationGroups();
    let group = groups.find(candidate => candidate.key === header.locationKey);
    if (!group && header.locationLabel) group = groups.find(candidate => normalizeSearch(candidate.label) === normalizeSearch(header.locationLabel));
    if (!group && items.length) {
      const devices = items.map(item => state.devices.find(device => device.id === item.deviceId)).filter(Boolean);
      if (devices.length) group = { key:header.locationKey || normalizeSearch(header.locationLabel), label:header.locationLabel || deviceLocationAt(devices[0]) || 'Concept', devices };
    }
    return group || null;
  }

  function restoreDraftForm(kind, header, items) {
    if (kind === 'breakdowns' && header?.serviceKind === 'other' && typeof window.machineparkPrepareOtherWorkModal === 'function') window.machineparkPrepareOtherWorkModal(header.workTypeName || 'Plaatsing');
    const form = document.getElementById('modalForm');
    if (!form) return;
    activeDraft.restoring = true;
    const date = form.querySelector('[name="date"]'); if (date) date.value = header.date || date.value;
    const time = form.querySelector('[name="time"]'); if (time) time.value = header.time || time.value;
    const technician = form.querySelector('[name="technician"]'); if (technician) technician.value = header.technician || '';
    const workRoot = form.querySelector('[data-service-work-sessions]');
    if (workRoot && typeof window.machineparkServiceWorkSessionsEditor === 'function') workRoot.outerHTML = window.machineparkServiceWorkSessionsEditor(header, kind === 'maintenance' ? 'maintenance' : 'breakdown');

    const inputId = kind === 'maintenance' ? 'maintenanceLocationSearch' : 'breakdownLocationSearch';
    const keyId = kind === 'maintenance' ? 'maintenanceLocationKey' : 'breakdownLocationKey';
    const boxId = kind === 'maintenance' ? 'maintenanceLocationDevices' : 'breakdownLocationDevices';
    const countId = kind === 'maintenance' ? 'maintenanceLocationCount' : 'breakdownLocationCount';
    const selectAllId = kind === 'maintenance' ? 'maintenanceSelectAll' : 'breakdownSelectAll';
    const input = document.getElementById(inputId), key = document.getElementById(keyId), box = document.getElementById(boxId), count = document.getElementById(countId), selectAll = document.getElementById(selectAllId);
    if (input) { input.value = header.locationLabel || ''; input.setCustomValidity(header.locationKey || header.locationLabel ? '' : 'Kies een locatie uit de zoeklijst.'); }
    if (key) key.value = header.locationKey || '';
    const group = draftGroup(kind, header, items);
    if (group && box) {
      box.innerHTML = group.devices.map(device => kind === 'maintenance' ? maintenanceMachineCardHtml(device) : breakdownMachineCardHtml(device)).join('');
      if (count) count.textContent = `${group.devices.length} toestel${group.devices.length===1?'':'len'} in concept op ${group.label}`;
      if (selectAll) { selectAll.style.display = ''; selectAll.textContent = 'Alles selecteren'; }
      const byDevice = new Map(items.map(item => [item.deviceId, item]));
      [...box.querySelectorAll('.maintenance-machine-card')].forEach(card => {
        const deviceId = kind === 'maintenance' ? card.dataset.maintenanceDevice : card.dataset.breakdownDevice;
        const item = byDevice.get(deviceId);
        if (item) restoreCard(kind, card, item);
        else if (kind === 'maintenance') setMaintenanceMachineEnabled(card, false); else setBreakdownMachineEnabled(card, false);
      });
      if (selectAll) {
        const cards = [...box.querySelectorAll('.maintenance-machine-card')];
        selectAll.textContent = cards.length && cards.every(card => card.querySelector(kind === 'maintenance' ? '.maintenance-machine-check' : '.breakdown-machine-check')?.checked) ? 'Alles uitvinken' : 'Alles selecteren';
      }
    }
    const delayedRestore = () => {
      const byDevice = new Map(items.map(item => [item.deviceId, item]));
      document.querySelectorAll('#modal .maintenance-machine-card').forEach(card => {
        const deviceId = kind === 'maintenance' ? card.dataset.maintenanceDevice : card.dataset.breakdownDevice;
        const item = byDevice.get(deviceId);
        if (!item) return;
        const enabled = item.draftSelected !== false;
        if (kind === 'maintenance') restoreWorkOrder(card, item.workOrder, enabled);
        else { restoreWorkOrder(card, item.workOrder, enabled); restoreFaultRef(card, item.faultRef); }
      });
    };
    setTimeout(delayedRestore, 80);
    setTimeout(delayedRestore, 450);
    if (kind === 'maintenance' && typeof window.machineparkLoadWorkOrderTemplates === 'function') Promise.resolve(window.machineparkLoadWorkOrderTemplates()).then(() => setTimeout(delayedRestore,0)).catch(() => {});
    setTimeout(() => { if (activeDraft) { activeDraft.restoring = false; activeDraft.touched = false; } }, 520);
  }

  function decorateDraftModal(kind, header = null) {
    const form = document.getElementById('modalForm');
    const foot = document.querySelector('#modal .modal-foot');
    if (!form || !foot) return false;
    const submit = foot.querySelector('button[type="submit"]');
    const cancel = document.getElementById('cancelModal');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn service-draft-button';
    button.id = 'saveServiceDraft';
    button.textContent = 'Concept bewaren';
    const status = document.createElement('span');
    status.className = 'service-draft-save-status';
    status.textContent = header ? `Concept geladen · laatst aangepast ${draftDateText(header.updatedAt)}` : 'Automatisch opslaan start zodra je iets wijzigt.';
    foot.insertBefore(status, submit || null);
    foot.insertBefore(button, submit || null);
    if (cancel) cancel.textContent = 'Sluiten';
    const note = document.createElement('div');
    note.className = 'service-draft-modal-note';
    note.textContent = 'Concept: onderdelen worden nog niet van de voorraad afgeboekt en deze registratie komt nog niet in de toestelgeschiedenis. Dat gebeurt pas bij definitief registreren.';
    const grid = form.querySelector('.form-grid');
    if (grid) grid.insertBefore(note, grid.firstChild);
    button.onclick = async () => {
      button.disabled = true;
      try {
        activeDraft.touched = true;
        await queueDraftSave({ manual:true, force:true });
        const current = activeDraft;
        activeDraft = null;
        clearTimeout(autosaveTimer);
        baseCloseModalForDrafts();
        if (current) await refreshDraftState(current.kind);
      } catch (error) {
        console.error(error);
        alert(error?.message || 'Concept opslaan mislukt.');
      } finally { if (document.body.contains(button)) button.disabled = false; }
    };
    form.addEventListener('input', scheduleDraftAutosave);
    form.addEventListener('change', scheduleDraftAutosave);
    form.addEventListener('click', event => {
      if (event.target.closest('[data-fault-pick],[data-add-work-session],[data-remove-work-session],[data-add-service-oneoff],[data-remove-service-oneoff],.remove-line,.maintenance-location-suggestion,.usage-suggestion,.fault-inline-toggle')) scheduleDraftAutosave();
    });
    form.onsubmit = event => { event.preventDefault(); finalizeActiveDraft().catch(error => { console.error(error); alert(error?.message || 'Registreren mislukt.'); }); };
    return true;
  }

  function beginDraftMode(kind, header = null) {
    const items = header ? draftItems(kind, header.id) : [];
    activeDraft = {
      kind, id:header?.id || uid(kindInfo(kind).headerPrefix), header:header || null,
      itemByDevice:new Map(items.map(item => [item.deviceId,item])), createdAt:header?.createdAt || new Date().toISOString(),
      persisted:Boolean(header), touched:false, finalizing:false, restoring:false,
    };
    if (!decorateDraftModal(kind, header)) { activeDraft = null; return; }
    if (header) restoreDraftForm(kind, header, items);
  }

  function openNewDraftCapable(kind) {
    const result = kind === 'maintenance' ? baseOpenMaintenanceForDrafts() : baseOpenBreakdownForDrafts();
    setTimeout(() => beginDraftMode(kind, null), 0);
    return result;
  }

  async function openSavedDraft(kind, id) {
    setSaveStatus('Nieuwste concept ophalen…', 'busy');
    await syncDraftAcrossDevices(kind, { pullLatest:true });
    const header = draftHeader(kind, id);
    if (!header) { toast('Concept niet meer gevonden'); return; }
    if (!canManageDraft(kind)) { toast('Deze rol mag dit concept niet verderzetten'); return; }
    const result = kind === 'maintenance' ? baseOpenMaintenanceForDrafts() : baseOpenBreakdownForDrafts();
    setTimeout(() => beginDraftMode(kind, header), 0);
    return result;
  }

  openMaintenance = function(id) {
    if (id && draftHeader('maintenance', id)) return openSavedDraft('maintenance', id);
    if (!id) return openNewDraftCapable('maintenance');
    return baseOpenMaintenanceForDrafts(id);
  };
  window.openMaintenance = openMaintenance;

  openBreakdown = function(id) {
    if (id && draftHeader('breakdowns', id)) return openSavedDraft('breakdowns', id);
    if (!id) return openNewDraftCapable('breakdowns');
    return baseOpenBreakdownForDrafts(id);
  };
  window.openBreakdown = openBreakdown;

  function validateFinalHeader(kind, header, items) {
    const selected = items.filter(item => item.draftSelected !== false);
    if (!header.locationKey && !header.locationLabel) throw new Error('Kies eerst een locatie.');
    if (!selected.length) throw new Error(`Selecteer minstens één toestel voor ${kind === 'maintenance' ? 'het onderhoud' : (header?.serviceKind === 'other' ? 'de werkzaamheden' : 'de depannage')}.`);
    if (kind === 'breakdowns' && header?.serviceKind === 'other' && !String(header.workTypeName || '').trim()) throw new Error('Kies of vul een naam voor Andere werken in.');
    const sessions = (header.workSessions || []).filter(row => row.date || Number(row.minutes) > 0);
    if (!sessions.length || sessions.some(row => !row.date || Number(row.minutes) <= 0)) throw new Error('Vul voor elke werkdag een datum en een geldige werkduur in.');
    if (kind === 'breakdowns') {
      const missing = selected.find(item => !String(item.issue || '').trim());
      if (missing) throw new Error(`Vul het probleem / de melding in voor ${deviceName(missing.deviceId) || 'elk geselecteerd toestel'}.`);
      selected.forEach(item => validateWorkOrder(item.workOrder));
    } else selected.forEach(item => validateWorkOrder(item.workOrder));
    return selected;
  }

  function partUpdatesForFinal(items) {
    const totals = {};
    items.forEach(item => (item.usedParts || []).forEach(usage => {
      const id = String(usage?.partId || '').trim();
      const qty = Number(usage?.qty || 0);
      if (id && qty > 0) totals[id] = (totals[id] || 0) + qty;
    }));
    const now = new Date().toISOString();
    const updates = [];
    for (const [id,qty] of Object.entries(totals)) {
      const part = state.parts.find(item => item.id === id);
      if (!part) throw new Error(`Onderdeel ${id} bestaat niet meer. Controleer het concept.`);
      updates.push({ ...part, stock:normalizePartQuantity(Number(part.stock || 0)-qty), updatedAt:now });
    }
    return updates;
  }

  function regularRecordFromDraft(kind, header, item, batchId, batchSize, now) {
    const record = { ...item };
    ['isDraft','draftRole','draftKind','draftBatchId','draftSelected','draftSchema'].forEach(key => delete record[key]);
    record.batchId = batchId;
    if (kind === 'breakdowns') {
      record.batchSize = batchSize;
      if (header?.serviceKind === 'other') { record.serviceKind = 'other'; record.workTypeName = String(header.workTypeName || 'Plaatsing').trim() || 'Plaatsing'; }
      else { delete record.serviceKind; delete record.workTypeName; }
    }
    record.date = header.date || '';
    record.time = header.time || '';
    record.technician = header.technician || '';
    record.workSessions = (header.workSessions || []).filter(row => row.date && Number(row.minutes) > 0).map(row => ({ date:row.date, minutes:Math.round(Number(row.minutes)) }));
    record.hours = record.workSessions.reduce((sum,row) => sum + Number(row.minutes || 0), 0) / 60;
    record.createdAt = item.createdAt || header.createdAt || now;
    record.updatedAt = now;
    return record;
  }

  function finalizeDraftTransaction(kind, header, allItems, selected) {
    const info = kindInfo(kind);
    const stockUpdates = partUpdatesForFinal(selected);
    const now = new Date().toISOString();
    const batchId = uid(kind === 'maintenance' ? 'mntbatch' : 'brkbatch');
    const finalRecords = selected.map(item => regularRecordFromDraft(kind, header, item, batchId, selected.length, now));
    const selectedIds = new Set(selected.map(item => item.id));
    return new Promise((resolve,reject) => {
      let tr;
      try { tr = db.transaction([info.store,'parts'], 'readwrite'); }
      catch (error) { reject(error); return; }
      const serviceStore = tr.objectStore(info.store);
      const partsStore = tr.objectStore('parts');
      stockUpdates.forEach(part => partsStore.put(part));
      finalRecords.forEach(record => serviceStore.put(record));
      serviceStore.delete(header.id);
      allItems.forEach(item => { if (!selectedIds.has(item.id)) serviceStore.delete(item.id); });
      tr.oncomplete = () => { scheduleCentralSync(); resolve({ records:finalRecords, stockUpdates }); };
      tr.onerror = () => reject(tr.error || new Error('Concept afronden mislukt.'));
      tr.onabort = () => reject(tr.error || new Error('Concept afronden afgebroken.'));
    });
  }

  async function finalizeActiveDraft() {
    const current = activeDraft;
    if (!current || current.finalizing) return;
    const form = document.getElementById('modalForm');
    if (!form) return;
    const submit = form.querySelector('button[type="submit"]');
    const oldText = submit?.textContent || 'Registreren';
    current.finalizing = true;
    clearTimeout(autosaveTimer);
    if (submit) { submit.disabled = true; submit.textContent = 'Registreren…'; }
    try {
      current.touched = true;
      await saveChain.catch(() => {});
      const saved = await saveDraftInternal({ force:true });
      if (!saved || activeDraft !== current) return;
      const selected = validateFinalHeader(current.kind, saved.header, saved.items);
      await finalizeDraftTransaction(current.kind, saved.header, saved.items, selected);
      activeDraft = null;
      baseCloseModalForDrafts();
      await refresh();
      toast(`${selected.length} ${current.kind === 'maintenance' ? 'onderhoudsregistratie' : (saved.header?.serviceKind === 'other' ? (saved.header.workTypeName || 'andere werkzaamheid') : 'depannageregistratie')}${selected.length === 1 ? '' : 's'} opgeslagen`);
    } catch (error) {
      current.finalizing = false;
      setSaveStatus(error?.message || 'Registreren mislukt', 'error');
      throw error;
    } finally {
      if (submit && document.body.contains(submit)) { submit.disabled = false; submit.textContent = oldText; }
    }
  }

  async function deleteDraft(kind, id) {
    const header = draftHeader(kind, id);
    if (!header) return;
    if (!canManageDraft(kind)) { toast('Deze rol mag dit concept niet verwijderen'); return; }
    const items = draftItems(kind, id);
    if (!confirm(`${kindInfo(kind).singular}concept definitief verwijderen? Er wordt geen voorraad aangepast.`)) return;
    const storeName = kindInfo(kind).store;
    await new Promise((resolve,reject) => {
      const tr = db.transaction(storeName, 'readwrite');
      const store = tr.objectStore(storeName);
      store.delete(header.id); items.forEach(item => store.delete(item.id));
      tr.oncomplete = () => { scheduleCentralSync(); resolve(); };
      tr.onerror = () => reject(tr.error || new Error('Concept verwijderen mislukt.'));
      tr.onabort = () => reject(tr.error || new Error('Concept verwijderen afgebroken.'));
    });
    await refreshDraftState(kind);
    toast('Concept verwijderd');
  }

  closeModal = function() {
    const current = activeDraft;
    if (!current || current.finalizing) return baseCloseModalForDrafts();
    clearTimeout(autosaveTimer);
    if (!current.touched) { activeDraft = null; return baseCloseModalForDrafts(); }
    const modal = document.getElementById('modal');
    modal?.querySelectorAll('button').forEach(button => { button.disabled = true; });
    setSaveStatus('Concept bewaren voor sluiten…', 'busy');
    queueDraftSave({ force:true }).then(() => syncDraftAcrossDevices(current.kind)).catch(error => {
      console.error('Concept bewaren bij sluiten', error);
      toast(error?.message || 'Concept kon niet worden bewaard');
    }).finally(() => {
      if (activeDraft === current) activeDraft = null;
      baseCloseModalForDrafts();
    });
  };
  window.closeModal = closeModal;

  document.addEventListener('click', event => {
    const open = event.target.closest('[data-service-draft-open]');
    if (open) { event.preventDefault(); openSavedDraft(open.dataset.serviceDraftKind, open.dataset.serviceDraftOpen); return; }
    const remove = event.target.closest('[data-service-draft-delete]');
    if (remove) { event.preventDefault(); deleteDraft(remove.dataset.serviceDraftKind, remove.dataset.serviceDraftDelete).catch(error => alert(error?.message || 'Concept verwijderen mislukt.')); }
  });

  renderDraftPanels();
})();
} catch (error) {
  console.error('[Machinepark feature service-drafts-v1]', error);
}

/* work-activities-v1 */
try {
(() => {
  const maintenanceNav = document.querySelector('.nav button[data-view="maintenance"]');
  const breakdownNav = document.querySelector('.nav button[data-view="breakdowns"]');
  if (!maintenanceNav || !breakdownNav) return;

  maintenanceNav.dataset.view = 'work';
  maintenanceNav.setAttribute('onclick', "switchView('work')");
  maintenanceNav.querySelector('.icon').textContent = '🛠';
  maintenanceNav.querySelector('.label').textContent = 'Werkzaamheden';
  breakdownNav.style.display = 'none';
  breakdownNav.setAttribute('aria-hidden','true');

  const maintenanceView = document.getElementById('view-maintenance');
  const partsView = document.getElementById('view-parts');
  const workView = document.createElement('section');
  workView.className = 'view';
  workView.id = 'view-work';
  workView.innerHTML = `
    <div id="workDraftPanels"></div>
    <div class="toolbar">
      <div class="toolbar-left">
        <select id="workKindFilter" class="filter"><option value="">Alle werkzaamheden</option><option value="maintenance">Onderhoud</option><option value="breakdowns">Depannage</option></select>
        <select id="workMaintenanceTypeFilter" class="filter"><option value="">Alle onderhoudstypes</option><option>Halfjaarlijks</option><option>Jaarlijks</option><option>Op afroep</option><option>Maandelijks</option></select>
        <select id="workBreakdownStatusFilter" class="filter"><option value="">Alle depannagestatussen</option><option>Open</option><option>In behandeling</option><option>Opgelost</option></select>
        <select id="workBreakdownPriorityFilter" class="filter"><option value="">Alle prioriteiten</option><option>Laag</option><option>Normaal</option><option>Hoog</option><option>Kritiek</option></select>
      </div>
      <div class="toolbar-right">
        <button class="btn primary" id="workAddMaintenance">+ Onderhoud registreren</button>
        <button class="btn primary" id="workAddBreakdown">+ Depannage toevoegen</button>
      </div>
    </div>
    <div class="table-wrap"><table class="table work-history-table"><thead><tr><th>Datum / uur</th><th>Type</th><th>Toestel</th><th>Werkzaamheid</th><th>Status / prioriteit</th><th>Technieker</th><th>Onderdelen</th><th>Notitie / oplossing</th><th></th></tr></thead><tbody id="workHistoryBody"></tbody></table></div>`;
  (partsView || maintenanceView?.nextSibling)?.parentNode?.insertBefore(workView, partsView || maintenanceView?.nextSibling);

  if (!Object.prototype.hasOwnProperty.call(machineparkViewQueries, 'work')) machineparkViewQueries.work = '';

  function hasViewPermission(key) {
    if (!window.machineparkAccessReady || typeof window.machineparkHasPermission !== 'function') return true;
    return window.machineparkHasPermission(key);
  }
  function canViewMaintenance() { return hasViewPermission('view.maintenance'); }
  function canViewBreakdowns() { return hasViewPermission('view.breakdowns'); }
  function canViewWork() { return canViewMaintenance() || canViewBreakdowns(); }

  function attachDraftPanels() {
    const host = document.getElementById('workDraftPanels');
    if (!host) return;
    const maintenancePanel = document.getElementById('maintenanceDraftPanel');
    const breakdownPanel = document.getElementById('breakdownsDraftPanel');
    if (maintenancePanel && maintenancePanel.parentNode !== host) host.appendChild(maintenancePanel);
    if (breakdownPanel && breakdownPanel.parentNode !== host) host.appendChild(breakdownPanel);
    if (maintenancePanel) {
      maintenancePanel.style.display = canViewMaintenance() ? '' : 'none';
      const title = maintenancePanel.querySelector('.service-draft-head strong');
      if (title) title.textContent = `Onderhoudsconcepten (${maintenancePanel.querySelectorAll('.service-draft-row').length})`;
    }
    if (breakdownPanel) {
      breakdownPanel.style.display = canViewBreakdowns() ? '' : 'none';
      const title = breakdownPanel.querySelector('.service-draft-head strong');
      if (title) title.textContent = `Depannageconcepten (${breakdownPanel.querySelectorAll('.service-draft-row').length})`;
    }
  }

  function workMatchesMaintenance(item) {
    if (item?.isDraft === true || !canViewMaintenance()) return false;
    const kind = document.getElementById('workKindFilter')?.value || '';
    const type = document.getElementById('workMaintenanceTypeFilter')?.value || '';
    if (kind && kind !== 'maintenance') return false;
    if (type && item.type !== type) return false;
    return typeof maintenanceMatchesQuery === 'function' ? maintenanceMatchesQuery(item) : true;
  }

  function workMatchesBreakdown(item) {
    if (item?.isDraft === true || !canViewBreakdowns()) return false;
    const kind = document.getElementById('workKindFilter')?.value || '';
    const status = document.getElementById('workBreakdownStatusFilter')?.value || '';
    const priority = document.getElementById('workBreakdownPriorityFilter')?.value || '';
    if (kind && kind !== 'breakdowns') return false;
    if (status && item.status !== status) return false;
    if (priority && item.priority !== priority) return false;
    return typeof breakdownMatchesQuery === 'function' ? breakdownMatchesQuery(item) : true;
  }

  function workPartsCount(item) {
    const total = list => (Array.isArray(list) ? list : []).reduce((sum, part) => {
      const qty = Number(part?.qty || 0);
      return sum + (Number.isFinite(qty) && qty > 0 ? qty : 0);
    }, 0);
    return total(item?.usedParts) + total(item?.oneOffParts);
  }

  function maintenanceRow(item) {
    const moment = recordMoment(item);
    return `<tr data-work-kind="maintenance"><td class="nowrap">${recordDateTimeFmt(item)}</td><td><span class="badge blue">Onderhoud</span></td><td><strong>${esc(deviceName(item.deviceId,moment))}</strong></td><td><span class="work-activity-type maintenance">${esc(item.type || 'Onderhoud')}</span></td><td>—</td><td>${esc(item.technician || '—')}</td><td class="work-parts-count">${formatPartQuantity(workPartsCount(item))}</td><td>${esc(item.notes || '—')}</td><td><button class="btn small" data-maintenance-details="${item.id}">Details</button></td></tr>`;
  }

  function breakdownRow(item) {
    const moment = recordMoment(item);
    return `<tr data-work-kind="breakdowns"><td class="nowrap">${recordDateTimeFmt(item)}</td><td><span class="badge danger">Depannage</span></td><td><strong>${esc(deviceName(item.deviceId,moment))}</strong></td><td><span class="work-activity-type breakdown">${esc(item.issue || 'Depannage')}</span></td><td><div class="work-status-stack">${statusBadge(item.priority || 'Normaal')}${breakdownStatusBadge(item.status || 'Open')}</div></td><td>${esc(item.technician || '—')}</td><td class="work-parts-count">${formatPartQuantity(workPartsCount(item))}</td><td>${esc(item.solution || item.diagnosis || '—')}</td><td><button class="btn small" data-edit-breakdown="${item.id}">Details</button></td></tr>`;
  }

  function renderWorkActivities() {
    attachDraftPanels();
    const body = document.getElementById('workHistoryBody');
    if (!body) return;
    const records = [
      ...(state.maintenance || []).filter(workMatchesMaintenance).map(item => ({ kind:'maintenance', item, moment:recordMoment(item) })),
      ...(state.breakdowns || []).filter(workMatchesBreakdown).map(item => ({ kind:'breakdowns', item, moment:recordMoment(item) })),
    ].sort((a,b) => String(b.moment || '').localeCompare(String(a.moment || '')));
    body.innerHTML = records.length
      ? records.map(row => row.kind === 'maintenance' ? maintenanceRow(row.item) : breakdownRow(row.item)).join('')
      : '<tr><td colspan="9"><div class="empty">Nog geen werkzaamheden gevonden.</div></td></tr>';
  }
  window.renderWorkActivities = renderWorkActivities;

  const baseRenderAllForWork = renderAll;
  renderAll = function() {
    baseRenderAllForWork();
    renderWorkActivities();
  };
  window.renderAll = renderAll;

  const baseSwitchViewForWork = switchView;
  function openWorkView() {
    if (!canViewWork()) return baseSwitchViewForWork('dashboard');
    state.view = 'work';
    document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
    workView.classList.add('active');
    document.querySelectorAll('.nav button').forEach(button => button.classList.toggle('active', button.dataset.view === 'work'));
    document.getElementById('pageTitle').textContent = 'Werkzaamheden';
    document.getElementById('pageSubtitle').textContent = 'Onderhoud en depannages in één chronologische historiek.';
    const input = document.getElementById('globalSearch');
    const actions = document.querySelector('.top-actions');
    if (actions) actions.style.display = '';
    state.query = machineparkViewQueries.work || '';
    if (input) { input.value = state.query; input.placeholder = 'Zoek in werkzaamheden…'; }
    closeGlobalSearch();
    renderAll();
  }
  switchView = function(view) {
    if (view === 'maintenance' || view === 'breakdowns' || view === 'work') return openWorkView();
    return baseSwitchViewForWork(view);
  };
  window.switchView = switchView;

  const baseApplyRoleAccessForWork = window.applyMachineparkRoleAccess || applyMachineparkRoleAccess;
  applyMachineparkRoleAccess = function() {
    const wasWork = state.view === 'work';
    if (wasWork) state.view = canViewMaintenance() ? 'maintenance' : canViewBreakdowns() ? 'breakdowns' : 'dashboard';
    try { baseApplyRoleAccessForWork(); }
    finally { if (wasWork && canViewWork()) state.view = 'work'; }
    maintenanceNav.style.display = canViewWork() ? '' : 'none';
    breakdownNav.style.display = 'none';
    const visible = [...document.querySelectorAll('.nav button[data-view]')].filter(button => button.style.display !== 'none').length;
    document.documentElement.style.setProperty('--mobile-nav-count', String(Math.max(1, visible)));
    if (wasWork && canViewWork()) {
      document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
      workView.classList.add('active');
      document.querySelectorAll('.nav button').forEach(button => button.classList.toggle('active', button.dataset.view === 'work'));
    }
  };
  window.applyMachineparkRoleAccess = applyMachineparkRoleAccess;

  const baseApplyOperationalForWork = window.applyOperationalPermissions || applyOperationalPermissions;
  applyOperationalPermissions = function() {
    baseApplyOperationalForWork();
    const addMaintenance = document.getElementById('workAddMaintenance');
    const addBreakdown = document.getElementById('workAddBreakdown');
    const canAddMaintenance = !window.machineparkAccessReady || window.machineparkHasPermission?.('maintenance.add');
    const canAddBreakdown = !window.machineparkAccessReady || window.machineparkHasPermission?.('breakdowns.add');
    if (addMaintenance) addMaintenance.style.display = canAddMaintenance && canViewMaintenance() ? '' : 'none';
    if (addBreakdown) addBreakdown.style.display = canAddBreakdown && canViewBreakdowns() ? '' : 'none';
  };
  window.applyOperationalPermissions = applyOperationalPermissions;

  document.getElementById('workAddMaintenance').onclick = () => openMaintenance();
  document.getElementById('workAddBreakdown').onclick = () => openBreakdown();
  ['workKindFilter','workMaintenanceTypeFilter','workBreakdownStatusFilter','workBreakdownPriorityFilter'].forEach(id => {
    const input = document.getElementById(id);
    if (input) input.onchange = renderWorkActivities;
  });

  attachDraftPanels();
  applyMachineparkRoleAccess();
  applyOperationalPermissions();
  renderWorkActivities();
})();
} catch (error) {
  console.error('[Machinepark feature work-activities-v1]', error);
}

/* other-works-v1 */
try {
(() => {
  const isOtherWork=item=>Boolean(item&&item.serviceKind==='other'&&item.isDraft!==true);
  const isOtherDraftHeader=item=>Boolean(item?.isDraft===true&&item.draftRole==='header'&&item.draftKind==='breakdowns'&&item.serviceKind==='other');
  const isOtherDraftItem=(item,id)=>Boolean(item?.isDraft===true&&item.draftRole==='item'&&item.draftKind==='breakdowns'&&item.draftBatchId===id);
  const canView=()=>!window.machineparkAccessReady||typeof window.machineparkHasPermission!=='function'||window.machineparkHasPermission('view.breakdowns');
  const canAdd=()=>!window.machineparkAccessReady||typeof window.machineparkHasPermission!=='function'||window.machineparkHasPermission('breakdowns.add');

  function typeNames(extra=''){
    const names=['Plaatsing'];
    (state.breakdowns||[]).forEach(item=>{if((isOtherWork(item)||isOtherDraftHeader(item))&&String(item.workTypeName||'').trim())names.push(String(item.workTypeName).trim())});
    if(String(extra||'').trim())names.push(String(extra).trim());
    return [...new Set(names)].sort((a,b)=>a==='Plaatsing'?-1:b==='Plaatsing'?1:a.localeCompare(b,'nl-BE',{numeric:true,sensitivity:'base'}));
  }

  function typeFieldHtml(selected='Plaatsing'){
    const names=typeNames(selected),known=names.includes(selected),choice=known?selected:'__new__';
    return `<div class="other-work-type-field" data-other-work-type-field><input type="hidden" name="serviceKind" value="other"><input type="hidden" name="workTypeName" value="${esc(selected||'Plaatsing')}"><div class="other-work-type-line"><div class="field"><label>Soort werkzaamheden *</label><select data-other-work-type-choice required>${names.map(name=>`<option value="${esc(name)}" ${choice===name?'selected':''}>${esc(name)}</option>`).join('')}<option value="__new__" ${choice==='__new__'?'selected':''}>+ Nieuwe naam toevoegen…</option></select></div><div class="field" data-other-work-new-field style="${choice==='__new__'?'':'display:none'}"><label>Nieuwe naam *</label><input data-other-work-new-name maxlength="100" value="${choice==='__new__'?esc(selected):''}" placeholder="bv. Ombouw, Verplaatsing…"></div></div><div class="other-work-type-help">Plaatsing staat standaard klaar. Een nieuwe naam wordt na opslaan automatisch een keuze voor volgende registraties en synchroniseert mee naar andere toestellen.</div></div>`;
  }

  function syncTypeField(root){
    const choice=root?.querySelector('[data-other-work-type-choice]'),newField=root?.querySelector('[data-other-work-new-field]'),newName=root?.querySelector('[data-other-work-new-name]'),hidden=root?.querySelector('[name="workTypeName"]');
    if(!choice||!hidden)return;const custom=choice.value==='__new__';if(newField)newField.style.display=custom?'':'none';if(newName)newName.required=custom;hidden.value=custom?String(newName?.value||'').trim():String(choice.value||'').trim();
  }

  window.machineparkPrepareOtherWorkModal=function(selected='Plaatsing'){
    const form=document.getElementById('modalForm'),grid=form?.querySelector('.modal-body .form-grid');if(!form||!grid)return;
    let field=grid.querySelector('[data-other-work-type-field]');
    if(!field){const holder=document.createElement('div');holder.innerHTML=typeFieldHtml(selected);field=holder.firstElementChild;grid.insertBefore(field,grid.firstChild)}
    else{const select=field.querySelector('[data-other-work-type-choice]');if(select&&selected&&![...select.options].some(o=>o.value===selected)){const option=document.createElement('option');option.value=selected;option.textContent=selected;select.insertBefore(option,select.querySelector('option[value="__new__"]'))}if(select&&selected)select.value=selected}
    form.dataset.otherWorkMode='1';syncTypeField(field);
    const title=document.querySelector('#modal .modal-head h3');if(title)title.textContent=selected&&selected!=='Plaatsing'?`${selected} registreren`:'Andere werken registreren';
    const submit=form.querySelector('.modal-foot button[type="submit"]');if(submit&&!form.dataset.otherWorkEdit)submit.textContent='Werkzaamheden registreren';
  };
  document.addEventListener('change',e=>{if(e.target.matches?.('[data-other-work-type-choice]'))syncTypeField(e.target.closest('[data-other-work-type-field]'))});
  document.addEventListener('input',e=>{if(e.target.matches?.('[data-other-work-new-name]'))syncTypeField(e.target.closest('[data-other-work-type-field]'))});

  const basePut=put;
  put=async function(storeName,obj){const form=document.getElementById('modalForm');if(storeName==='breakdowns'&&obj&&form?.dataset.otherWorkMode==='1'){const type=String(form.querySelector('[name="workTypeName"]')?.value||'').trim();if(!type)throw new Error('Kies of vul een naam voor Andere werken in.');obj={...obj,serviceKind:'other',workTypeName:type}}return basePut(storeName,obj)};
  window.put=put;

  function withClassic(callback){const all=state.breakdowns;state.breakdowns=(all||[]).filter(item=>!isOtherWork(item));try{return callback()}finally{state.breakdowns=all}}
  const baseRenderBreakdowns=renderBreakdowns;renderBreakdowns=function(){return withClassic(()=>baseRenderBreakdowns())};window.renderBreakdowns=renderBreakdowns;
  const baseRenderDashboard=renderDashboard;renderDashboard=function(){return withClassic(()=>baseRenderDashboard())};window.renderDashboard=renderDashboard;
  const baseProfessional=renderProfessionalDashboard;renderProfessionalDashboard=function(){return withClassic(()=>baseProfessional())};window.renderProfessionalDashboard=renderProfessionalDashboard;

  const workView=document.getElementById('view-work');
  const workToolbarRight=workView?.querySelector('.toolbar-right');
  if(workToolbarRight&&!document.getElementById('workAddOtherWork'))workToolbarRight.insertAdjacentHTML('beforeend','<button class="btn primary" id="workAddOtherWork">+ Andere werken registreren</button>');
  const kindFilter=document.getElementById('workKindFilter');if(kindFilter&&!kindFilter.querySelector('option[value="otherworks"]'))kindFilter.insertAdjacentHTML('beforeend','<option value="otherworks">Andere werken</option>');
  const workDrafts=document.getElementById('workDraftPanels');if(workDrafts&&!document.getElementById('otherWorkDraftPanelWork')){const host=document.createElement('div');host.id='otherWorkDraftPanelWork';host.className='other-work-draft-host';workDrafts.appendChild(host)}

  function partsCount(item){const total=list=>(Array.isArray(list)?list:[]).reduce((sum,p)=>sum+Math.max(0,Number(p?.qty||0)||0),0);return total(item?.usedParts)+total(item?.oneOffParts)}
  function matchesOther(item){if(!isOtherWork(item))return false;const type=document.getElementById('otherWorkTypeFilter')?.value||'',status=document.getElementById('otherWorkStatusFilter')?.value||'',priority=document.getElementById('otherWorkPriorityFilter')?.value||'';if(type&&item.workTypeName!==type||status&&item.status!==status||priority&&item.priority!==priority)return false;if(!state.query)return true;const moment=recordMoment(item);return searchDeviceIsActive(item.deviceId)&&searchIncludes([item.workTypeName,item.date,item.time,recordDateTimeFmt(item),item.issue,item.diagnosis,item.solution,item.technician,item.priority,item.status,linkedDeviceSearchText(item.deviceId,moment),linkedPartsSearchText(item.usedParts)].join(' '))}
  function otherRow(item){const moment=recordMoment(item),type=String(item.workTypeName||'Andere werken');return `<tr data-work-kind="otherworks"><td class="nowrap">${recordDateTimeFmt(item)}</td><td><span class="badge other-work-badge">${esc(type)}</span></td><td><strong>${esc(deviceName(item.deviceId,moment))}</strong></td><td><span class="work-activity-type other-work">${esc(item.issue||type)}</span></td><td><div class="work-status-stack">${statusBadge(item.priority||'Normaal')}${breakdownStatusBadge(item.status||'Open')}</div></td><td>${esc(item.technician||'—')}</td><td class="work-parts-count">${formatPartQuantity(partsCount(item))}</td><td>${esc(item.solution||item.diagnosis||'—')}</td><td><button class="btn small" data-other-work-details="${esc(item.id)}">Details</button></td></tr>`}
  function fillTypeFilter(){const select=document.getElementById('otherWorkTypeFilter');if(!select)return;const current=select.value;select.innerHTML='<option value="">Alle soorten</option>'+typeNames().map(name=>`<option value="${esc(name)}">${esc(name)}</option>`).join('');if([...select.options].some(o=>o.value===current))select.value=current}
  function draftDeviceText(header){const items=(state.breakdowns||[]).filter(item=>isOtherDraftItem(item,header.id)&&item.draftSelected!==false),names=items.map(item=>{const d=state.devices.find(x=>x.id===item.deviceId);return d?.assetCode||d?.model||''}).filter(Boolean);return names.length?`${names.length} toestel${names.length===1?'':'len'} · ${names.slice(0,3).join(', ')}${names.length>3?' …':''}`:'nog geen toestel geselecteerd'}
  function draftHtml(){const headers=(state.breakdowns||[]).filter(isOtherDraftHeader).sort((a,b)=>String(b.updatedAt||'').localeCompare(String(a.updatedAt||'')));if(!headers.length)return '';return `<div class="service-draft-panel show"><div class="service-draft-head"><strong>Andere-werkenconcepten (${headers.length})</strong><span class="muted" style="font-size:11px">Automatisch lokaal bewaard en centraal gesynchroniseerd.</span></div><div class="service-draft-list">${headers.map(h=>`<div class="service-draft-row"><div><div class="service-draft-row-title"><span class="service-draft-badge">CONCEPT</span>${esc(h.workTypeName||'Andere werken')} · ${esc(h.locationLabel||'Nog geen locatie')}</div><div class="service-draft-row-meta">${esc(draftDeviceText(h))} · laatst aangepast ${h.updatedAt?esc(new Date(h.updatedAt).toLocaleString('nl-BE')):'nog niet opgeslagen'}</div></div><div class="service-draft-actions"><button type="button" class="btn small service-draft-button" data-service-draft-open="${esc(h.id)}" data-service-draft-kind="breakdowns">Verdergaan</button><button type="button" class="btn small danger" data-service-draft-delete="${esc(h.id)}" data-service-draft-kind="breakdowns">Verwijderen</button></div></div>`).join('')}</div></div>`}
  function renderDrafts(){const html=draftHtml();['otherWorkDraftPanel','otherWorkDraftPanelWork'].forEach(id=>{const host=document.getElementById(id);if(host)host.innerHTML=html})}
  function renderOtherWorks(){fillTypeFilter();renderDrafts();const body=document.getElementById('otherWorkBody');if(!body)return;const list=(state.breakdowns||[]).filter(matchesOther).sort((a,b)=>recordMoment(b).localeCompare(recordMoment(a)));body.innerHTML=list.length?list.map(otherRow).join(''):'<tr><td colspan="9"><div class="empty">Nog geen andere werken geregistreerd.</div></td></tr>'}
  window.renderOtherWorks=renderOtherWorks;

  function renderCombined(){const body=document.getElementById('workHistoryBody');if(!body)return;const kind=document.getElementById('workKindFilter')?.value||'',mt=document.getElementById('workMaintenanceTypeFilter')?.value||'',bs=document.getElementById('workBreakdownStatusFilter')?.value||'',bp=document.getElementById('workBreakdownPriorityFilter')?.value||'',canM=!window.machineparkAccessReady||window.machineparkHasPermission?.('view.maintenance'),canB=canView(),rows=[];
    if(canM&&(!kind||kind==='maintenance'))(state.maintenance||[]).forEach(item=>{if(item?.isDraft===true||mt&&item.type!==mt||typeof maintenanceMatchesQuery==='function'&&!maintenanceMatchesQuery(item))return;rows.push({kind:'maintenance',item,moment:recordMoment(item)})});
    if(canB&&(!kind||kind==='breakdowns'))(state.breakdowns||[]).forEach(item=>{if(item?.isDraft===true||isOtherWork(item)||bs&&item.status!==bs||bp&&item.priority!==bp||typeof breakdownMatchesQuery==='function'&&!breakdownMatchesQuery(item))return;rows.push({kind:'breakdowns',item,moment:recordMoment(item)})});
    if(canB&&(!kind||kind==='otherworks'))(state.breakdowns||[]).forEach(item=>{if(!isOtherWork(item)||bs&&item.status!==bs||bp&&item.priority!==bp)return;if(state.query){const moment=recordMoment(item);if(!searchDeviceIsActive(item.deviceId)||!searchIncludes([item.workTypeName,item.issue,item.diagnosis,item.solution,item.technician,item.priority,item.status,linkedDeviceSearchText(item.deviceId,moment),linkedPartsSearchText(item.usedParts)].join(' ')))return}rows.push({kind:'otherworks',item,moment:recordMoment(item)})});
    rows.sort((a,b)=>String(b.moment||'').localeCompare(String(a.moment||'')));
    body.innerHTML=rows.length?rows.map(row=>{if(row.kind==='otherworks')return otherRow(row.item);const item=row.item,moment=row.moment;if(row.kind==='maintenance')return `<tr data-work-kind="maintenance"><td class="nowrap">${recordDateTimeFmt(item)}</td><td><span class="badge blue">Onderhoud</span></td><td><strong>${esc(deviceName(item.deviceId,moment))}</strong></td><td><span class="work-activity-type maintenance">${esc(item.type||'Onderhoud')}</span></td><td>—</td><td>${esc(item.technician||'—')}</td><td class="work-parts-count">${formatPartQuantity(partsCount(item))}</td><td>${esc(item.notes||'—')}</td><td><button class="btn small" data-maintenance-details="${item.id}">Details</button></td></tr>`;return `<tr data-work-kind="breakdowns"><td class="nowrap">${recordDateTimeFmt(item)}</td><td><span class="badge danger">Depannage</span></td><td><strong>${esc(deviceName(item.deviceId,moment))}</strong></td><td><span class="work-activity-type breakdown">${esc(item.issue||'Depannage')}</span></td><td><div class="work-status-stack">${statusBadge(item.priority||'Normaal')}${breakdownStatusBadge(item.status||'Open')}</div></td><td>${esc(item.technician||'—')}</td><td class="work-parts-count">${formatPartQuantity(partsCount(item))}</td><td>${esc(item.solution||item.diagnosis||'—')}</td><td><button class="btn small" data-edit-breakdown="${item.id}">Details</button></td></tr>`}).join(''):'<tr><td colspan="9"><div class="empty">Nog geen werkzaamheden gevonden.</div></td></tr>';renderDrafts()}
  window.machineparkRenderCombinedWork=renderCombined;

  ['workKindFilter','workMaintenanceTypeFilter','workBreakdownStatusFilter','workBreakdownPriorityFilter'].forEach(id=>{const input=document.getElementById(id);if(input)input.onchange=renderCombined});
  const baseRenderAll=renderAll;renderAll=function(){baseRenderAll();renderOtherWorks();renderCombined()};window.renderAll=renderAll;

  const baseGlobal=renderGlobalSearchResults;renderGlobalSearchResults=function(){withClassic(()=>baseGlobal());if(state.view!=='dashboard'||!state.query||!canView())return;const box=document.getElementById('globalSearchResults');if(!box)return;const matches=(state.breakdowns||[]).filter(item=>{if(!isOtherWork(item)||!searchDeviceIsActive(item.deviceId))return false;const moment=recordMoment(item);return searchIncludes([item.workTypeName,item.issue,item.diagnosis,item.solution,item.technician,linkedDeviceSearchText(item.deviceId,moment),linkedPartsSearchText(item.usedParts)].join(' '))}).sort((a,b)=>recordMoment(b).localeCompare(recordMoment(a))).slice(0,6);if(!matches.length)return;if(box.querySelector('.global-search-empty'))box.innerHTML='';box.insertAdjacentHTML('beforeend','<div class="global-search-head">Andere werken</div>'+matches.map(item=>`<button type="button" class="global-search-result" data-global-other-work="${esc(item.id)}"><strong>🧰 ${esc(item.workTypeName||'Andere werken')} · ${esc(deviceName(item.deviceId,recordMoment(item)))}</strong><small>${esc(item.issue||'')} · ${esc(item.technician||'Geen technieker')}</small></button>`).join(''));box.classList.add('show')};window.renderGlobalSearchResults=renderGlobalSearchResults;

  const baseSwitch=switchView;switchView=function(view){const target=view==='otherworks'?'work':view;const result=baseSwitch(target);if(target==='work'){const subtitle=document.getElementById('pageSubtitle');if(subtitle)subtitle.textContent='Onderhoud, depannages en andere werken in één chronologische historiek.'}return result};window.switchView=switchView;

  function applyOtherWorkAccess(){const add=document.getElementById('workAddOtherWork');if(add)add.style.display=canView()&&canAdd()?'':'none'}
  const baseRole=window.applyMachineparkRoleAccess||applyMachineparkRoleAccess;applyMachineparkRoleAccess=function(){baseRole();applyOtherWorkAccess()};window.applyMachineparkRoleAccess=applyMachineparkRoleAccess;
  const baseOperational=window.applyOperationalPermissions||applyOperationalPermissions;applyOperationalPermissions=function(){baseOperational();applyOtherWorkAccess()};window.applyOperationalPermissions=applyOperationalPermissions;

  function prepareAfterOpen(selected='Plaatsing',editing=false){setTimeout(()=>{window.machineparkPrepareOtherWorkModal(selected);const form=document.getElementById('modalForm');if(form&&editing){form.dataset.otherWorkEdit='1';const title=document.querySelector('#modal .modal-head h3');if(title)title.textContent=`${selected||'Andere werken'} bijwerken`;const submit=form.querySelector('.modal-foot button[type="submit"]');if(submit)submit.textContent='Wijzigingen opslaan'}},0);setTimeout(()=>window.machineparkPrepareOtherWorkModal(selected),120)}
  function openOtherWork(id=''){if(id){const record=(state.breakdowns||[]).find(item=>item.id===id&&isOtherWork(item));if(!record){toast('Werkzaamheid niet gevonden');return}openBreakdown(id);prepareAfterOpen(record.workTypeName||'Plaatsing',true);return}if(!canAdd()){toast('Geen recht om andere werken toe te voegen');return}openBreakdown();prepareAfterOpen('Plaatsing',false)}window.openOtherWork=openOtherWork;
  function showDetails(id){const record=(state.breakdowns||[]).find(item=>item.id===id&&isOtherWork(item));if(!record){toast('Werkzaamheid niet gevonden');return}if(typeof window.machineparkShowBreakdownDetails==='function')window.machineparkShowBreakdownDetails(id);else openBreakdown(id);setTimeout(()=>{const title=document.querySelector('#modal .modal-head h3');if(title)title.textContent=`${record.workTypeName||'Andere werken'} details`;const edit=document.getElementById('editBreakdownFromDetails');if(edit){edit.textContent=`${record.workTypeName||'Werkzaamheid'} bewerken`;edit.onclick=()=>{closeModal();openOtherWork(id)}}},30)}window.machineparkShowOtherWorkDetails=showDetails;

  const addOtherWork=document.getElementById('workAddOtherWork');if(addOtherWork)addOtherWork.onclick=()=>openOtherWork();
  document.addEventListener('click',e=>{const detail=e.target.closest?.('[data-other-work-details]');if(detail){showDetails(detail.dataset.otherWorkDetails);return}const global=e.target.closest?.('[data-global-other-work]');if(global){closeGlobalSearch();showDetails(global.dataset.globalOtherWork)}});
  applyOtherWorkAccess();renderDrafts();renderCombined();
})();
} catch (error) {
  console.error('[Machinepark feature other-works-v1]', error);
}

/* other-works-merged-v1 */
try {
window.machineparkOtherWorksMergedIntoWork=true;
} catch (error) {
  console.error('[Machinepark feature other-works-merged-v1]', error);
}

/* auto-live-sync-v1 */
try {
(() => {
  const LIVE_SYNC_INTERVAL_MS = 3000;
  let liveSyncTimer = null;
  let liveSyncRunning = false;

  async function machineparkLiveSyncNow() {
    if (liveSyncRunning) return;
    if (document.visibilityState === 'hidden') return;
    if (!navigator.onLine || !window.Clerk?.isSignedIn || !window.__koffieServiceStarted) return;

    liveSyncRunning = true;
    try {
      if (typeof window.machineparkSyncOnlineNow === 'function') {
        await window.machineparkSyncOnlineNow({ quiet: true });
      }
      if (typeof window.machineparkLoadFaultLibrary === 'function') {
        await window.machineparkLoadFaultLibrary(true);
        if (typeof window.machineparkRenderFaultLibrary === 'function') {
          window.machineparkRenderFaultLibrary();
        }
      }
      if (typeof window.machineparkLoadManualLibrary === 'function') {
        await window.machineparkLoadManualLibrary(true);
        if (typeof window.machineparkRenderManualLibrary === 'function') {
          window.machineparkRenderManualLibrary();
        }
      }
    } catch (error) {
      console.warn('Automatische live synchronisatie', error);
    } finally {
      liveSyncRunning = false;
    }
  }

  function startMachineparkLiveSync() {
    if (liveSyncTimer) return;
    liveSyncTimer = setInterval(machineparkLiveSyncNow, LIVE_SYNC_INTERVAL_MS);
    setTimeout(machineparkLiveSyncNow, 250);
  }

  window.machineparkLiveSyncNow = machineparkLiveSyncNow;
  window.machineparkStartLiveSync = startMachineparkLiveSync;
  window.addEventListener('online', () => setTimeout(machineparkLiveSyncNow, 100));
  window.addEventListener('focus', () => setTimeout(machineparkLiveSyncNow, 100));
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') setTimeout(machineparkLiveSyncNow, 100);
  });
  startMachineparkLiveSync();
})();
} catch (error) {
  console.error('[Machinepark feature auto-live-sync-v1]', error);
}

/* navigation-runtime-v2 */
try {
(() => {
  const originalSwitchView = window.switchView;

  function safePageMeta(view) {
    try {
      const meta = typeof pageMeta === 'function' ? pageMeta(view) : null;
      if (Array.isArray(meta) && meta.length >= 2) return meta;
    } catch (error) {
      console.warn('[Machinepark] paginametadata kon niet worden geladen', error);
    }
    const fallback = {
      dashboard: ['Dashboard', 'Overzicht van service, storingen en voorraad.'],
      devices: ['Toestellen', 'Beheer alle koffietoestellen en hun onderhoudsplanning.'],
      maintenance: ['Onderhoud', 'Registreer halfjaarlijkse en jaarlijkse servicebeurten.'],
      breakdowns: ['Depannages', 'Volg storingen van melding tot oplossing op.'],
      parts: ['Onderdelen', 'Voorraad en onderdelen.'],
      faults: ['Storingen', 'Zoek storingscodes, storingen en oplossingen per merk of model.'],
      manuals: ['Handleidingen', 'Technische PDF-handleidingen per merk, model of toestel.'],
      settings: ['Beheer', 'Back-up, import en instellingen.'],
    };
    return fallback[view] || ['Machinepark', ''];
  }

  function safeCall(label, fn) {
    try {
      if (typeof fn === 'function') fn();
    } catch (error) {
      console.error(`[Machinepark] ${label} mislukt`, error);
    }
  }

  function setStateView(view) {
    try {
      if (typeof state !== 'undefined' && state) state.view = view;
    } catch (error) {
      console.warn('[Machinepark] view-state kon niet worden bijgewerkt', error);
    }
  }

  function activateView(view) {
    let nextView = String(view || '').trim();
    if (nextView === 'settings' && !window.machineparkIsAdmin) nextView = 'dashboard';

    const target = document.getElementById(`view-${nextView}`);
    if (!target) {
      console.warn('[Machinepark] onbekend tabblad genegeerd:', nextView);
      return false;
    }

    // Wissel EERST de zichtbare DOM. Dit werkt zelfs wanneer de grote basis-JS
    // eerder is uitgevallen en state/renderfuncties daardoor niet beschikbaar zijn.
    document.querySelectorAll('.view').forEach((node) => node.classList.remove('active'));
    target.classList.add('active');
    document.querySelectorAll('.nav [data-view]').forEach((button) => {
      button.classList.toggle('active', button.dataset.view === nextView);
    });

    setStateView(nextView);

    const [title, subtitle] = safePageMeta(nextView);
    const titleNode = document.getElementById('pageTitle');
    const subtitleNode = document.getElementById('pageSubtitle');
    if (titleNode) titleNode.textContent = title;
    if (subtitleNode) subtitleNode.textContent = subtitle;

    safeCall('zoekbalk configureren', () => {
      if (typeof configureSearchForView === 'function') configureSearchForView(nextView);
    });
    safeCall('tabblad renderen', () => {
      if (typeof renderAll === 'function') renderAll();
    });

    if (nextView === 'faults') {
      safeCall('storingen renderen', window.machineparkRenderFaultLibrary);
    } else if (nextView === 'manuals') {
      safeCall('handleidingen renderen', window.machineparkRenderManualLibrary);
    } else if (nextView === 'settings' && window.machineparkIsAdmin) {
      safeCall('beheer laden', typeof loadAdminPanels === 'function' ? loadAdminPanels : null);
    }

    return true;
  }

  window.machineparkNavigate = activateView;
  window.switchView = activateView;

  // Houd de globale function-binding en window-property gelijk voor inline onclick.
  try { switchView = activateView; } catch (_) {}

  // Capture vóór alle oudere click/touch handlers en inline onclick. Daardoor kan
  // een oude of kapotte listener de navigatie niet meer terug naar Dashboard sturen.
  function handleNavigationEvent(event) {
    const source = event.target && event.target.nodeType === 1
      ? event.target
      : event.target?.parentElement;
    const button = source?.closest?.('.nav [data-view]');
    if (!button) return;
    if (button.style.display === 'none') return;

    event.preventDefault();
    event.stopPropagation();
    if (typeof event.stopImmediatePropagation === 'function') event.stopImmediatePropagation();
    activateView(button.dataset.view);
  }

  document.addEventListener('click', handleNavigationEvent, true);
  document.addEventListener('touchend', handleNavigationEvent, { capture: true, passive: false });

  window.machineparkOriginalSwitchView = originalSwitchView;
})();
} catch (error) {
  console.error('[Machinepark feature navigation-runtime-v2]', error);
}

/* unified-work-layout-v1 */
try {
(() => {
  const definitions = [
    ['view-maintenance','Onderhoudsverslagen','Overzicht van geregistreerd onderhoud per toestel.'],
    ['view-breakdowns','Depannageverslagen','Overzicht van geregistreerde depannages per toestel.'],
    ['view-otherworks','Andere werken','Plaatsingen en andere werkzaamheden per toestel.'],
    ['view-work','Werkzaamhedenoverzicht','Onderhoud, depannages en andere werken in één overzicht.']
  ];

  function ensurePageActions(view, title) {
    if (!view || view.querySelector(':scope > .page-print-row')) return;
    const row = document.createElement('div');
    row.className = 'page-print-row';
    row.innerHTML = `<div class="page-print-heading">Machinepark · ${title}</div><button type="button" class="btn page-print-btn">🖨 Afdrukken</button><button type="button" class="btn page-mail-btn">✉ Mail PDF</button>`;
    row.querySelector('.page-print-btn')?.addEventListener('click', () => window.printMachineparkView?.(view));
    view.insertAdjacentElement('afterbegin', row);
  }

  function decorateOverview(id, title, description) {
    const view = document.getElementById(id);
    if (!view) return;
    ensurePageActions(view, title);
    if (view.querySelector(':scope > .work-overview-panel')) return;
    const wrap = view.querySelector('.table-wrap');
    if (!wrap || !wrap.parentNode) return;
    const panel = document.createElement('div');
    panel.className = 'work-overview-panel service-visit-panel';
    panel.innerHTML = `<div class="service-visit-panel-head"><div><h3>${title}</h3><p>${description}</p></div></div>`;
    wrap.parentNode.insertBefore(panel, wrap);
    wrap.classList.add('work-overview-table-wrap');
    panel.appendChild(wrap);
  }

  function apply() { definitions.forEach(args => decorateOverview(...args)); }
  apply();
  setTimeout(apply, 0);
  setTimeout(apply, 250);
  window.machineparkApplyUnifiedWorkLayout = apply;
})();
} catch (error) {
  console.error('[Machinepark feature unified-work-layout-v1]', error);
}
