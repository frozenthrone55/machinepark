(() => {
  const MANUAL_LIBRARY_URL = '/.netlify/functions/manual-library';
  const MANUAL_CACHE_DB = 'MachineparkManualLibraryDB';
  const MANUAL_CACHE_STORE = 'cache';
  const MANUAL_FILE_CACHE = 'machinepark-manual-files-v1';
  const MANUAL_TYPES = [
    'Gebruikershandleiding',
    'Technische handleiding',
    'Service manual',
    'Onderdelenlijst',
    'Installatiehandleiding',
    'Reiniging / onderhoud',
    'Elektrisch schema',
    'Overig',
  ];

  let manualLibrary = [];
  let manualLibraryEtag = null;
  let manualLibraryLoaded = false;
  let manualLibraryLoading = null;
  let manualLibraryOffline = false;

  function derivedManualPermissions(permissions = {}) {
    return {
      'view.manuals': Boolean(permissions['view.devices'] || permissions['view.breakdowns'] || permissions['view.settings']),
      'manuals.manage': Boolean(permissions['view.settings']),
    };
  }

  function installDerivedManualPermissions() {
    if (!window.machineparkPermissions) return;
    Object.assign(window.machineparkPermissions, derivedManualPermissions(window.machineparkPermissions));
  }

  function canViewManuals() {
    if (window.machineparkAccessReady && typeof window.machineparkHasPermission === 'function') return window.machineparkHasPermission('view.manuals');
    return Boolean(window.machineparkRole && window.machineparkRole !== 'magazijnier');
  }

  function canManageManuals() {
    if (window.machineparkAccessReady && typeof window.machineparkHasPermission === 'function') return window.machineparkHasPermission('manuals.manage');
    return Boolean(window.machineparkIsAdmin);
  }

  function manualNorm(value) {
    return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  }

  function manualSearchText(manual) {
    return manualNorm([
      manual?.title, manual?.type, manual?.brand, manual?.model, manual?.versionLabel,
      manual?.language, manual?.notes, manual?.fileName,
    ].filter(Boolean).join(' '));
  }

  function manualDevice(manual) {
    return state.devices.find((device) => device.id === manual?.deviceId) || null;
  }

  function manualScopeText(manual) {
    const exact = manualDevice(manual);
    if (manual?.deviceId) return exact
      ? `${exact.assetCode || exact.model || 'Toestel'} · ${deviceLocationAt(exact) || 'geen locatie'}`
      : 'Specifiek toestel';
    if (manual?.brand && manual?.model) return `${manual.brand} · ${manual.model}`;
    if (manual?.brand) return `${manual.brand} · alle modellen`;
    return 'Algemeen · alle toestellen';
  }

  function manualAppliesToDevice(manual, device) {
    if (!manual || !device || manual.active === false) return false;
    if (manual.deviceId) return manual.deviceId === device.id;
    if (!manual.brand) return true;
    const brandNeedle = manualNorm(manual.brand);
    const deviceBrand = manualNorm([device.brand, device.model].filter(Boolean).join(' '));
    if (!brandNeedle || !(deviceBrand.includes(brandNeedle) || brandNeedle.includes(deviceBrand))) return false;
    if (!manual.model) return true;
    const modelNeedle = manualNorm(manual.model);
    const deviceModel = manualNorm([device.model, device.brand].filter(Boolean).join(' '));
    return Boolean(modelNeedle && (deviceModel.includes(modelNeedle) || modelNeedle.includes(deviceModel)));
  }

  function manualSpecificity(manual) {
    return manual?.deviceId ? 0 : manual?.brand && manual?.model ? 1 : manual?.brand ? 2 : 3;
  }

  function manualsForDevice(deviceId) {
    const device = state.devices.find((item) => item.id === deviceId);
    if (!device) return [];
    return manualLibrary
      .filter((manual) => manualAppliesToDevice(manual, device))
      .sort((a, b) => manualSpecificity(a) - manualSpecificity(b) || String(a.type || '').localeCompare(String(b.type || ''), 'nl-BE') || String(a.title || '').localeCompare(String(b.title || ''), 'nl-BE'));
  }
  window.machineparkManualsForDevice = async function(deviceId, force = false) {
    await loadManualLibrary(force);
    return manualsForDevice(deviceId);
  };
  window.machineparkManualListHtml = async function(deviceId, compact = true) {
    await loadManualLibrary();
    return deviceManualListHtml(deviceId, compact);
  };

  function openManualCacheDb() {
    return new Promise((resolve, reject) => {
      if (!window.indexedDB) { reject(new Error('IndexedDB niet beschikbaar')); return; }
      const req = indexedDB.open(MANUAL_CACHE_DB, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(MANUAL_CACHE_STORE)) db.createObjectStore(MANUAL_CACHE_STORE, { keyPath: 'key' });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error || new Error('Handleidingencache kon niet worden geopend'));
    });
  }

  async function readManualCache() {
    try {
      const db = await openManualCacheDb();
      return await new Promise((resolve, reject) => {
        const tx = db.transaction(MANUAL_CACHE_STORE, 'readonly');
        const req = tx.objectStore(MANUAL_CACHE_STORE).get('library');
        req.onsuccess = () => resolve(req.result || null);
        req.onerror = () => reject(req.error);
        tx.oncomplete = () => db.close();
      });
    } catch (_) { return null; }
  }

  async function writeManualCache() {
    try {
      const db = await openManualCacheDb();
      await new Promise((resolve, reject) => {
        const tx = db.transaction(MANUAL_CACHE_STORE, 'readwrite');
        tx.objectStore(MANUAL_CACHE_STORE).put({ key: 'library', manuals: manualLibrary, etag: manualLibraryEtag, updatedAt: new Date().toISOString() });
        tx.oncomplete = resolve;
        tx.onerror = () => reject(tx.error);
        tx.onabort = () => reject(tx.error);
      });
      db.close();
    } catch (_) {}
  }

  async function manualJsonRequest(options = {}) {
    const headers = await centralHeaders(options.body !== undefined);
    if (manualLibraryEtag && String(options.method || 'GET').toUpperCase() === 'GET') headers['X-Machinepark-If-None-Match'] = manualLibraryEtag;
    const res = await fetch(MANUAL_LIBRARY_URL, { cache: 'no-store', ...options, headers: { ...headers, ...(options.headers || {}) } });
    const text = await res.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch (_) {}
    if (!res.ok) {
      const error = new Error(data.error || text || `Handleidingenactie mislukt (${res.status})`);
      error.status = res.status;
      throw error;
    }
    if (Array.isArray(data.manuals)) manualLibrary = data.manuals;
    if (data.etag !== undefined) manualLibraryEtag = data.etag || null;
    manualLibraryOffline = false;
    manualLibraryLoaded = true;
    await writeManualCache();
    return data;
  }

  async function loadManualLibrary(force = false) {
    if (!canViewManuals()) return [];
    if (!force && manualLibraryLoaded) return manualLibrary;
    if (manualLibraryLoading) return manualLibraryLoading;
    manualLibraryLoading = (async () => {
      if (!manualLibraryLoaded) {
        const cached = await readManualCache();
        if (cached && Array.isArray(cached.manuals)) {
          manualLibrary = cached.manuals;
          manualLibraryEtag = cached.etag || null;
          manualLibraryLoaded = true;
          manualLibraryOffline = true;
        }
      }
      if (navigator.onLine === false) return manualLibrary;
      try {
        await manualJsonRequest();
      } catch (error) {
        if (!manualLibraryLoaded) throw error;
        manualLibraryOffline = true;
      }
      return manualLibrary;
    })().finally(() => { manualLibraryLoading = null; });
    return manualLibraryLoading;
  }
  window.machineparkLoadManualLibrary = loadManualLibrary;

  function manualOfflineUrl(manual) {
    const version = encodeURIComponent(manual?.updatedAt || manual?.version || '1');
    return `${location.origin}/__machinepark_manual_offline__/${encodeURIComponent(manual.id)}?v=${version}`;
  }

  async function clearOfflineManualVersions(id) {
    if (!window.caches) return;
    const cache = await caches.open(MANUAL_FILE_CACHE);
    const keys = await cache.keys();
    await Promise.all(keys.filter((req) => req.url.includes(`/__machinepark_manual_offline__/${encodeURIComponent(id)}?`)).map((req) => cache.delete(req)));
  }

  async function isManualOffline(manual) {
    if (!window.caches || !manual?.id) return false;
    const cache = await caches.open(MANUAL_FILE_CACHE);
    return Boolean(await cache.match(manualOfflineUrl(manual)));
  }

  async function fetchManualPdf(manual) {
    const headers = await centralHeaders(false);
    const url = `${MANUAL_LIBRARY_URL}?file=${encodeURIComponent(manual.fileKey)}`;
    const res = await fetch(url, { cache: 'no-store', headers });
    if (!res.ok) {
      let message = `Handleiding kon niet worden geladen (${res.status})`;
      try { message = (await res.json())?.error || message; } catch (_) {}
      throw new Error(message);
    }
    return res.blob();
  }

  async function getManualPdf(manual) {
    if (window.caches) {
      const cache = await caches.open(MANUAL_FILE_CACHE);
      const cached = await cache.match(manualOfflineUrl(manual));
      if (navigator.onLine === false) {
        if (!cached) throw new Error('Deze handleiding is niet offline beschikbaar gemaakt.');
        return cached.blob();
      }
      try { return await fetchManualPdf(manual); }
      catch (error) { if (cached) return cached.blob(); throw error; }
    }
    if (navigator.onLine === false) throw new Error('Deze handleiding is niet offline beschikbaar.');
    return fetchManualPdf(manual);
  }

  async function makeManualOffline(manual) {
    if (!window.caches) throw new Error('Offline PDF-opslag wordt door deze browser niet ondersteund.');
    if (navigator.onLine === false) throw new Error('Maak de handleiding offline beschikbaar wanneer je internet hebt.');
    const blob = await fetchManualPdf(manual);
    await clearOfflineManualVersions(manual.id);
    const cache = await caches.open(MANUAL_FILE_CACHE);
    await cache.put(manualOfflineUrl(manual), new Response(blob, { headers: { 'content-type': 'application/pdf', 'x-machinepark-file-name': manual.fileName || 'handleiding.pdf' } }));
    return true;
  }

  async function removeManualOffline(manual) {
    await clearOfflineManualVersions(manual.id);
  }

  async function openManualPdf(manual) {
    const tab = window.open('', '_blank');
    if (tab) {
      try { tab.document.write('<title>Handleiding laden…</title><p style="font-family:system-ui;padding:24px">Handleiding laden…</p>'); } catch (_) {}
    }
    try {
      const blob = await getManualPdf(manual);
      const objectUrl = URL.createObjectURL(blob);
      if (tab) tab.location.href = objectUrl;
      else window.location.href = objectUrl;
      setTimeout(() => URL.revokeObjectURL(objectUrl), 10 * 60 * 1000);
    } catch (error) {
      try { tab?.close(); } catch (_) {}
      alert(error?.message || 'Handleiding kon niet worden geopend.');
    }
  }
  window.machineparkOpenManualPdf = openManualPdf;

  function optionValues(values) {
    return [...new Set(values.map((item) => String(item || '').trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'nl-BE', { numeric: true, sensitivity: 'base' }));
  }

  function fillSelect(select, values, emptyLabel) {
    if (!select) return;
    const current = select.value;
    select.innerHTML = `<option value="">${esc(emptyLabel)}</option>` + optionValues(values).map((value) => `<option value="${esc(value)}">${esc(value)}</option>`).join('');
    if ([...select.options].some((option) => option.value === current)) select.value = current;
  }

  async function refreshManualOfflineIndicators() {
    const nodes = [...document.querySelectorAll('[data-manual-offline-state]')];
    await Promise.all(nodes.map(async (node) => {
      const manual = manualLibrary.find((item) => item.id === node.dataset.manualOfflineState);
      if (!manual) return;
      const offline = await isManualOffline(manual);
      node.textContent = offline ? '✓ Offline' : 'Online';
      node.className = `badge manual-offline-badge ${offline ? 'success' : 'gray'}`;
    }));
  }

  function renderManualLibrary() {
    const body = document.getElementById('manualLibraryBody');
    const status = document.getElementById('manualLibraryStatus');
    if (!body || !status) return;
    const add = document.getElementById('addManualLibraryItem');
    if (add) add.style.display = canManageManuals() ? '' : 'none';
    const settingsAdd = document.getElementById('addManualFromSettings');
    if (settingsAdd) settingsAdd.style.display = canManageManuals() ? '' : 'none';

    if (!canViewManuals()) {
      body.innerHTML = '<tr><td colspan="6"><div class="empty">Geen toegang tot de handleidingenbibliotheek.</div></td></tr>';
      return;
    }
    if (!manualLibraryLoaded) {
      status.textContent = 'Handleidingen laden…';
      body.innerHTML = '<tr><td colspan="6"><div class="empty">Handleidingen worden geladen…</div></td></tr>';
      loadManualLibrary().then(renderManualLibrary).catch((error) => {
        status.textContent = error.message;
        body.innerHTML = '<tr><td colspan="6"><div class="empty">Handleidingenbibliotheek niet beschikbaar.</div></td></tr>';
      });
      return;
    }

    const brandFilter = document.getElementById('manualBrandFilter');
    const modelFilter = document.getElementById('manualModelFilter');
    const typeFilter = document.getElementById('manualTypeFilter');
    fillSelect(brandFilter, manualLibrary.map((manual) => manual.brand), 'Alle merken');
    const selectedBrand = brandFilter?.value || '';
    fillSelect(modelFilter, manualLibrary.filter((manual) => !selectedBrand || manual.brand === selectedBrand).map((manual) => manual.model), 'Alle modellen');
    fillSelect(typeFilter, manualLibrary.map((manual) => manual.type), 'Alle types');

    const query = manualNorm(state.query || '');
    const selectedModel = modelFilter?.value || '';
    const selectedType = typeFilter?.value || '';
    const visible = manualLibrary.filter((manual) => {
      if (manual.active === false && !canManageManuals()) return false;
      if (selectedBrand && manual.brand !== selectedBrand) return false;
      if (selectedModel && manual.model !== selectedModel) return false;
      if (selectedType && manual.type !== selectedType) return false;
      if (query && !manualSearchText(manual).includes(query)) return false;
      return true;
    }).sort((a, b) => manualSpecificity(a) - manualSpecificity(b) || String(a.brand || '').localeCompare(String(b.brand || ''), 'nl-BE') || String(a.model || '').localeCompare(String(b.model || ''), 'nl-BE') || String(a.title || '').localeCompare(String(b.title || ''), 'nl-BE'));

    status.textContent = `${visible.length} van ${manualLibrary.length} handleiding${manualLibrary.length === 1 ? '' : 'en'}${manualLibraryOffline ? ' · offline opgeslagen lijst' : ' · centraal bijgewerkt'}`;
    if (!visible.length) {
      body.innerHTML = '<tr><td colspan="6"><div class="empty"><div class="big">📘</div>Geen handleidingen gevonden.</div></td></tr>';
      return;
    }
    body.innerHTML = visible.map((manual) => `<tr><td><span class="badge blue">${esc(manual.type || 'Overig')}</span></td><td><span class="manual-title">${esc(manual.title)}</span><div class="manual-file-meta">${esc(manual.fileName || 'PDF')}${manual.fileSize ? ` · ${(Number(manual.fileSize) / 1024 / 1024).toFixed(1)} MB` : ''}</div></td><td><div class="manual-scope">${esc(manualScopeText(manual))}</div></td><td>${esc(manual.versionLabel || '—')}<br><span class="muted">${esc(manual.language || '—')}</span></td><td><span data-manual-offline-state="${esc(manual.id)}" class="badge gray manual-offline-badge">…</span></td><td><div class="manual-actions"><button type="button" class="btn small" data-manual-open="${esc(manual.id)}">PDF openen</button><button type="button" class="btn small" data-manual-details="${esc(manual.id)}">Details</button></div></td></tr>`).join('');
    refreshManualOfflineIndicators().catch(() => {});
  }
  window.machineparkRenderManualLibrary = renderManualLibrary;

  function manualInfoHtml(manual) {
    return `<div class="manual-detail-grid"><div><strong style="font-size:20px">${esc(manual.title)}</strong><div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:7px"><span class="badge blue">${esc(manual.type || 'Overig')}</span>${manual.versionLabel ? `<span class="badge">Versie ${esc(manual.versionLabel)}</span>` : ''}${manual.language ? `<span class="badge gray">${esc(manual.language)}</span>` : ''}</div><div class="muted" style="margin-top:7px">${esc(manualScopeText(manual))}</div></div><div class="manual-detail-card"><h4>PDF-bestand</h4><p>${esc(manual.fileName || 'handleiding.pdf')}${manual.fileSize ? ` · ${(Number(manual.fileSize) / 1024 / 1024).toFixed(1)} MB` : ''}</p></div>${manual.notes ? `<div class="manual-detail-card"><h4>Opmerkingen</h4><p>${esc(manual.notes)}</p></div>` : ''}</div>`;
  }

  function showManualDetails(id) {
    const manual = manualLibrary.find((item) => item.id === id);
    if (!manual) return;
    showModal('Handleiding', manualInfoHtml(manual), 'Sluiten', async () => closeModal());
    setTimeout(async () => {
      const foot = document.querySelector('#modal .modal-foot');
      if (!foot) return;
      const open = document.createElement('button');
      open.type = 'button'; open.className = 'btn primary'; open.textContent = 'PDF openen'; open.onclick = () => openManualPdf(manual);
      foot.insertBefore(open, foot.lastElementChild);
      const offline = document.createElement('button');
      offline.type = 'button'; offline.className = 'btn';
      const refreshLabel = async () => { offline.textContent = await isManualOffline(manual) ? 'Offline verwijderen' : 'Offline beschikbaar maken'; };
      await refreshLabel();
      offline.onclick = async () => {
        offline.disabled = true;
        try {
          if (await isManualOffline(manual)) { await removeManualOffline(manual); toast('Offline handleiding verwijderd'); }
          else { await makeManualOffline(manual); toast('Handleiding is offline beschikbaar'); }
          await refreshLabel(); renderManualLibrary();
        } catch (error) { alert(error?.message || 'Offline opslaan mislukt.'); }
        finally { offline.disabled = false; }
      };
      foot.insertBefore(offline, open);
      if (canManageManuals()) {
        const edit = document.createElement('button');
        edit.type = 'button'; edit.className = 'btn'; edit.textContent = 'Bewerken / PDF vervangen'; edit.onclick = () => openManualEditor(manual);
        const del = document.createElement('button');
        del.type = 'button'; del.className = 'btn danger'; del.textContent = 'Verwijderen'; del.onclick = () => deleteManual(manual);
        foot.insertBefore(del, foot.firstChild);
        foot.insertBefore(edit, foot.firstChild);
      }
    }, 0);
  }

  function manualTypeOptions(current = '') {
    const values = optionValues([...MANUAL_TYPES, current]);
    return values.map((type) => `<option value="${esc(type)}" ${type === current ? 'selected' : ''}>${esc(type)}</option>`).join('');
  }

  function deviceOptions(current = '') {
    const devices = [...state.devices].sort((a, b) => String(a.assetCode || '').localeCompare(String(b.assetCode || ''), 'nl-BE', { numeric: true }));
    return '<option value="">Geen specifiek toestel</option>' + devices.map((device) => `<option value="${esc(device.id)}" ${device.id === current ? 'selected' : ''}>${esc([device.assetCode, deviceLocationAt(device), device.brand, device.model].filter(Boolean).join(' · '))}</option>`).join('');
  }

  async function uploadManualFile(file) {
    if (!file) return null;
    if (file.type && file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) throw new Error('Kies een PDF-bestand.');
    if (file.size > 12_000_000) throw new Error('De PDF is groter dan 12 MB.');
    const headers = await centralHeaders(false);
    headers['content-type'] = 'application/pdf';
    const url = `${MANUAL_LIBRARY_URL}?action=upload&fileName=${encodeURIComponent(file.name || 'handleiding.pdf')}`;
    const res = await fetch(url, { method: 'PUT', cache: 'no-store', headers, body: file });
    const text = await res.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch (_) {}
    if (!res.ok) throw new Error(data.error || text || `PDF-upload mislukt (${res.status})`);
    return data;
  }

  function openManualEditor(manual = null) {
    if (!canManageManuals()) return;
    const editing = Boolean(manual?.id);
    const body = `<div class="form-grid"><div class="field full"><label>Titel *</label><input name="title" maxlength="180" required value="${esc(manual?.title || '')}" placeholder="bv. Bravilor Bolero servicehandleiding"></div><div class="field"><label>Type handleiding</label><select name="type">${manualTypeOptions(manual?.type || 'Technische handleiding')}</select></div><div class="field"><label>Versie / datum</label><input name="versionLabel" maxlength="80" value="${esc(manual?.versionLabel || '')}" placeholder="bv. 3.2 of 2026"></div><div class="field"><label>Merk</label><input name="brand" maxlength="100" value="${esc(manual?.brand || '')}" placeholder="Leeg = alle merken"></div><div class="field"><label>Model</label><input name="model" maxlength="140" value="${esc(manual?.model || '')}" placeholder="Leeg = alle modellen"></div><div class="field full"><label>Specifiek toestel</label><select name="deviceId">${deviceOptions(manual?.deviceId || '')}</select><div class="muted" style="font-size:11px;margin-top:4px">Optioneel. Kies dit alleen als de handleiding uitsluitend voor één concreet toestel geldt.</div></div><div class="field"><label>Taal</label><input name="language" maxlength="60" value="${esc(manual?.language || 'Nederlands')}"></div><div class="field"><label>${editing ? 'Nieuw PDF-bestand (optioneel)' : 'PDF-bestand *'}</label><input type="file" name="pdf" accept="application/pdf,.pdf" ${editing ? '' : 'required'}><div class="muted" style="font-size:11px;margin-top:4px">Maximaal 12 MB.${editing && manual?.fileName ? ` Huidig: ${esc(manual.fileName)}` : ''}</div></div><div class="field full"><label>Opmerkingen</label><textarea name="notes" maxlength="2000" placeholder="Interne informatie, revisie-opmerking, bron…">${esc(manual?.notes || '')}</textarea></div><div class="field full"><label style="display:flex;align-items:center;gap:8px"><input type="checkbox" name="active" ${manual?.active === false ? '' : 'checked'} style="width:auto"> Actief en zichtbaar</label></div></div>`;
    showModal(editing ? 'Handleiding bewerken' : 'Handleiding toevoegen', body, editing ? 'Wijzigingen opslaan' : 'Handleiding opslaan', async (formData) => {
      const file = document.querySelector('#modal input[name="pdf"]')?.files?.[0] || null;
      let fileInfo = manual ? { fileKey: manual.fileKey, fileName: manual.fileName, fileSize: manual.fileSize } : null;
      if (file) {
        setCentralSyncStatus?.('☁ PDF uploaden…', 'busy');
        fileInfo = await uploadManualFile(file);
      }
      if (!fileInfo?.fileKey) throw new Error('Kies een PDF-bestand.');
      const payload = {
        id: manual?.id || undefined,
        title: String(formData.get('title') || '').trim(),
        type: String(formData.get('type') || '').trim(),
        brand: String(formData.get('brand') || '').trim(),
        model: String(formData.get('model') || '').trim(),
        deviceId: String(formData.get('deviceId') || '').trim(),
        versionLabel: String(formData.get('versionLabel') || '').trim(),
        language: String(formData.get('language') || '').trim(),
        notes: String(formData.get('notes') || '').trim(),
        active: formData.get('active') === 'on',
        ...fileInfo,
      };
      await manualJsonRequest({ method: 'POST', body: JSON.stringify({ action: 'save-manual', manual: payload, etag: manualLibraryEtag }) });
      closeModal();
      toast(editing ? 'Handleiding bijgewerkt' : 'Handleiding toegevoegd');
      renderManualLibrary();
      if (typeof window.machineparkLiveSyncNow === 'function') window.machineparkLiveSyncNow();
    });
  }

  async function deleteManual(manual) {
    if (!canManageManuals() || !manual) return;
    if (!confirm(`Handleiding “${manual.title}” en het gekoppelde PDF-bestand definitief verwijderen?`)) return;
    try {
      await manualJsonRequest({ method: 'POST', body: JSON.stringify({ action: 'delete-manual', id: manual.id, etag: manualLibraryEtag }) });
      await removeManualOffline(manual);
      closeModal();
      renderManualLibrary();
      toast('Handleiding verwijderd');
      if (typeof window.machineparkLiveSyncNow === 'function') window.machineparkLiveSyncNow();
    } catch (error) { alert(error?.message || 'Handleiding verwijderen mislukt.'); }
  }

  function deviceManualListHtml(deviceId, compact = false) {
    const matches = manualsForDevice(deviceId);
    if (!matches.length) return '<div class="muted" style="font-size:12px">Geen passende handleidingen gevonden.</div>';
    return matches.map((manual) => `<div class="${compact ? 'manual-inline-result' : 'manual-device-item'}"><div><strong>${esc(manual.title)}</strong><small>${esc([manual.type, manual.versionLabel, manual.language].filter(Boolean).join(' · '))}</small></div><button type="button" class="btn small" data-manual-open="${esc(manual.id)}">PDF openen</button></div>`).join('');
  }

  async function injectDeviceManuals(deviceId) {
    await loadManualLibrary();
    const body = document.querySelector('#modal .modal-body');
    if (!body || body.querySelector('.manual-device-section')) return;
    const section = document.createElement('div');
    section.className = 'manual-device-section';
    section.innerHTML = `<div class="section-title">📘 Handleidingen voor dit toestel</div><div class="manual-device-list">${deviceManualListHtml(deviceId)}</div>`;
    body.appendChild(section);
  }

  function attachSingleBreakdownManualTool(record = null) {
    const grid = document.querySelector('#modal .modal-body .form-grid');
    if (!grid || grid.querySelector('.manual-breakdown-single')) return;
    const field = document.createElement('div');
    field.className = 'field full manual-breakdown-single manual-inline-tools';
    field.innerHTML = '<button type="button" class="btn small manual-inline-toggle">📘 Handleidingen voor dit toestel</button><div class="manual-inline-panel"></div>';
    grid.appendChild(field);
    const toggle = field.querySelector('.manual-inline-toggle');
    const panel = field.querySelector('.manual-inline-panel');
    toggle.onclick = async () => {
      const deviceId = document.querySelector('#modal .device-select')?.value || record?.deviceId || '';
      if (!deviceId) { toast('Kies eerst een toestel'); return; }
      await loadManualLibrary();
      panel.innerHTML = deviceManualListHtml(deviceId, true);
      panel.classList.toggle('show');
    };
  }

  function augmentBreakdownManualCards() {
    document.querySelectorAll('#modal .breakdown-machine-card').forEach((card) => {
      if (card.querySelector('.manual-inline-tools')) return;
      const tools = document.createElement('div');
      tools.className = 'manual-inline-tools';
      tools.innerHTML = '<button type="button" class="btn small manual-inline-toggle">📘 Handleidingen</button><div class="manual-inline-panel"></div>';
      const target = card.querySelector('.breakdown-machine-issue')?.parentElement || card;
      target.insertBefore(tools, target.firstChild);
      const toggle = tools.querySelector('.manual-inline-toggle');
      const panel = tools.querySelector('.manual-inline-panel');
      toggle.onclick = async () => {
        const deviceId = card.dataset.breakdownDevice || '';
        await loadManualLibrary();
        panel.innerHTML = deviceManualListHtml(deviceId, true);
        panel.classList.toggle('show');
      };
    });
  }

  async function injectRecordedBreakdownManuals(record) {
    if (!record?.deviceId) return;
    await loadManualLibrary();
    const body = document.querySelector('#modal .modal-body');
    if (!body || body.querySelector('.manual-breakdown-recorded')) return;
    const section = document.createElement('div');
    section.className = 'manual-device-section manual-breakdown-recorded';
    section.innerHTML = `<div class="section-title">📘 Handleidingen voor deze depannage</div><div class="manual-device-list">${deviceManualListHtml(record.deviceId)}</div>`;
    body.appendChild(section);
  }

  const baseShowDeviceHistoryForManuals = showDeviceHistory;
  showDeviceHistory = function(id) {
    const result = baseShowDeviceHistoryForManuals(id);
    if (id) loadManualLibrary().then(() => setTimeout(() => injectDeviceManuals(id), 0)).catch(() => {});
    return result;
  };
  window.showDeviceHistory = showDeviceHistory;

  const baseInitBreakdownLocationForManuals = initBreakdownLocationForm;
  initBreakdownLocationForm = function() {
    const result = baseInitBreakdownLocationForManuals();
    const box = document.getElementById('breakdownLocationDevices');
    if (box) {
      augmentBreakdownManualCards();
      const observer = new MutationObserver(() => augmentBreakdownManualCards());
      observer.observe(box, { childList: true, subtree: true });
      setTimeout(() => { if (!document.body.contains(box)) observer.disconnect(); }, 300000);
    }
    return result;
  };

  const baseOpenBreakdownForManuals = openBreakdown;
  openBreakdown = function(id) {
    const record = id ? state.breakdowns.find((item) => item.id === id) || null : null;
    const result = baseOpenBreakdownForManuals(id);
    loadManualLibrary().then(() => setTimeout(() => {
      if (record) injectRecordedBreakdownManuals(record);
      else { attachSingleBreakdownManualTool(record); augmentBreakdownManualCards(); }
    }, 0)).catch(() => setTimeout(() => { if (!record) attachSingleBreakdownManualTool(record); }, 0));
    return result;
  };
  window.openBreakdown = openBreakdown;

  const basePageMetaForManuals = pageMeta;
  pageMeta = function(view) {
    if (view === 'manuals') return ['Handleidingen', 'Technische PDF-handleidingen per merk, model of toestel.'];
    return basePageMetaForManuals(view);
  };
  machineparkViewQueries.manuals = machineparkViewQueries.manuals || '';

  const baseConfigureSearchForManuals = configureSearchForView;
  configureSearchForView = function(view) {
    if (view !== 'manuals') return baseConfigureSearchForManuals(view);
    const input = document.getElementById('globalSearch');
    const actions = document.querySelector('.top-actions');
    if (!input || !actions) return;
    actions.style.display = '';
    state.query = machineparkViewQueries.manuals || '';
    input.value = state.query;
    input.placeholder = 'Zoek handleiding, merk, model of type…';
    closeGlobalSearch();
  };

  const baseRenderAllForManuals = renderAll;
  renderAll = function() {
    baseRenderAllForManuals();
    if (state.view === 'manuals') renderManualLibrary();
  };

  const baseRenderGlobalSearchForManuals = renderGlobalSearchResults;
  renderGlobalSearchResults = function() {
    baseRenderGlobalSearchForManuals();
    if (state.view !== 'dashboard' || !state.query || !canViewManuals() || !manualLibraryLoaded) return;
    const box = document.getElementById('globalSearchResults');
    if (!box) return;
    const q = manualNorm(state.query);
    const matches = manualLibrary.filter((manual) => manual.active !== false && manualSearchText(manual).includes(q)).slice(0, 6);
    if (!matches.length) return;
    box.querySelector('.global-search-empty')?.remove();
    box.insertAdjacentHTML('beforeend', '<div class="global-search-head">Handleidingen</div>' + matches.map((manual) => `<button type="button" class="global-search-result" data-global-manual="${esc(manual.id)}"><strong>📘 ${esc(manual.title)}</strong><small>${esc(manualScopeText(manual))} · ${esc(manual.type || 'Handleiding')}</small></button>`).join(''));
    box.classList.add('show');
  };

  function bindManualLibraryPage() {
    const refresh = document.getElementById('refreshManualLibrary');
    const add = document.getElementById('addManualLibraryItem');
    const settingsAdd = document.getElementById('addManualFromSettings');
    const settingsManage = document.getElementById('manageManualsFromSettings');
    const brand = document.getElementById('manualBrandFilter');
    const model = document.getElementById('manualModelFilter');
    const type = document.getElementById('manualTypeFilter');
    if (refresh) refresh.onclick = async () => { await loadManualLibrary(true); renderManualLibrary(); };
    if (add) add.onclick = () => openManualEditor();
    if (settingsAdd) settingsAdd.onclick = () => openManualEditor();
    if (settingsManage) settingsManage.onclick = () => switchView('manuals');
    if (brand) brand.onchange = () => { if (model) model.value = ''; renderManualLibrary(); };
    if (model) model.onchange = renderManualLibrary;
    if (type) type.onchange = renderManualLibrary;
    document.body.addEventListener('click', async (event) => {
      const open = event.target.closest('[data-manual-open]');
      if (open) { const manual = manualLibrary.find((item) => item.id === open.dataset.manualOpen); if (manual) openManualPdf(manual); return; }
      const details = event.target.closest('[data-manual-details]');
      if (details) { showManualDetails(details.dataset.manualDetails); return; }
      const global = event.target.closest('[data-global-manual]');
      if (global) { closeGlobalSearch(); showManualDetails(global.dataset.globalManual); return; }
    });
  }

  const previousServerAccessForManuals = window.applyMachineparkServerAccess;
  if (typeof previousServerAccessForManuals === 'function') {
    window.applyMachineparkServerAccess = function(body) {
      let next = body;
      if (body?.permissions) next = { ...body, permissions: { ...body.permissions, ...derivedManualPermissions(body.permissions) } };
      const result = previousServerAccessForManuals(next);
      installDerivedManualPermissions();
      if (canViewManuals()) loadManualLibrary(true).then(() => { if (state.view === 'manuals') renderManualLibrary(); }).catch(() => {});
      return result;
    };
  }

  function initManualFeature() {
    installDerivedManualPermissions();
    if (window.machineparkAccessReady && typeof window.applyMachineparkRoleAccess === 'function') window.applyMachineparkRoleAccess();
    bindManualLibraryPage();
    readManualCache().then((cached) => {
      if (cached && Array.isArray(cached.manuals)) {
        manualLibrary = cached.manuals;
        manualLibraryEtag = cached.etag || null;
        manualLibraryLoaded = true;
        manualLibraryOffline = true;
      }
      if (canViewManuals()) loadManualLibrary(true).then(() => { if (state.view === 'manuals') renderManualLibrary(); }).catch(() => {});
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initManualFeature, { once: true });
  else initManualFeature();
})();
