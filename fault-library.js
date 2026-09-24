(() => {
  const FAULT_LIBRARY_URL = './synology/api/fault-library.php'; // machinepark-synology-local-faults-v1
  const FAULT_CACHE_DB = 'MachineparkFaultLibraryDB';
  const FAULT_CACHE_STORE = 'cache';
  let faultLibrary = [];
  let faultLibraryEtag = null;
  let faultLibraryLoaded = false;
  let faultLibraryLoading = null;
  let faultLibraryOffline = false;

  function canViewFaultLibrary() {
    if (window.machineparkAccessReady && typeof window.machineparkHasPermission === 'function') return window.machineparkHasPermission('view.faults');
    return Boolean(window.machineparkRole && window.machineparkRole !== 'magazijnier');
  }

  function canManageFaultLibrary() {
    if (window.machineparkAccessReady && typeof window.machineparkHasPermission === 'function') return window.machineparkHasPermission('faults.manage');
    return Boolean(window.machineparkIsAdmin);
  }

  function faultNorm(value) {
    return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase();
  }

  function faultLines(value) {
    return (Array.isArray(value) ? value : String(value || '').split(/\r?\n/)).map((item) => String(item || '').trim()).filter(Boolean);
  }

  function faultScopeText(fault) {
    if (fault?.brand && fault?.model) return `${fault.brand} · ${fault.model}`;
    if (fault?.brand) return `${fault.brand} · alle modellen`;
    return 'Algemeen · alle merken';
  }

  function faultScopeBadge(fault) {
    if (fault?.brand && fault?.model) return '<span class="badge blue">Model</span>';
    if (fault?.brand) return '<span class="badge warn">Merk</span>';
    return '<span class="badge gray">Algemeen</span>';
  }

  function faultTitle(fault) {
    return [fault?.code, fault?.name].filter(Boolean).join(' — ') || 'Storing';
  }

  // machinepark-fault-picker-refresh-search-v1
  // machinepark-fault-excel-extra-fields-v1
  function faultSearchText(fault) {
    return faultNorm([
      fault?.code, fault?.name, fault?.category, fault?.brand, fault?.model,
      fault?.description, fault?.message, fault?.solution1, fault?.solution2,
      ...(fault?.symptoms || []), ...(fault?.causes || []), ...(fault?.solutions || []), fault?.notes,
    ].filter(Boolean).join(' '));
  }

  function faultCompact(value) {
    return faultNorm(value).replace(/[^a-z0-9]+/g, '');
  }

  function faultMatchesQuery(fault, query) {
    const q = faultNorm(query);
    if (!q) return true;
    const text = faultSearchText(fault);
    if (text.includes(q)) return true;
    const compactQuery = faultCompact(q);
    return Boolean(compactQuery && faultCompact(text).includes(compactQuery));
  }

  // machinepark-fault-picker-matching-v2
  function faultScopeComparable(value) {
    return faultNorm(value)
      .replace(/\([^)]*\)/g, ' ')
      .replace(/[^a-z0-9]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function faultScopeMatches(needleValue, targetValue) {
    const needle = faultScopeComparable(needleValue);
    const target = faultScopeComparable(targetValue);
    if (!needle) return true;
    if (!target) return false;
    if (needle === target || target.includes(needle) || needle.includes(target)) return true;
    const needleTokens = needle.split(' ').filter((token) => token.length > 1);
    const targetTokens = target.split(' ').filter((token) => token.length > 1);
    if (!needleTokens.length || !targetTokens.length) return false;
    return needleTokens.every((token) => targetTokens.includes(token)) || targetTokens.every((token) => needleTokens.includes(token));
  }

  function faultAppliesToDevice(fault, device) {
    if (!fault?.brand) return true;
    const deviceBrand = String(device?.brand || '');
    const deviceModel = String(device?.model || '');
    const deviceCombined = [deviceBrand, deviceModel].filter(Boolean).join(' ');
    const brandMatches = faultScopeMatches(fault.brand, deviceBrand) || faultScopeMatches(fault.brand, deviceCombined);
    if (!brandMatches) return false;
    if (!fault?.model) return true;
    return faultScopeMatches(fault.model, deviceModel) || faultScopeMatches(fault.model, deviceCombined);
  }

  function faultSpecificity(fault) {
    return fault?.brand && fault?.model ? 0 : fault?.brand ? 1 : 2;
  }

  function openFaultCacheDb() {
    return new Promise((resolve, reject) => {
      if (!window.indexedDB) { reject(new Error('IndexedDB niet beschikbaar')); return; }
      const req = indexedDB.open(FAULT_CACHE_DB, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(FAULT_CACHE_STORE)) db.createObjectStore(FAULT_CACHE_STORE, { keyPath: 'key' });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error || new Error('Cache kon niet worden geopend'));
    });
  }

  async function readFaultCache() {
    try {
      const db = await openFaultCacheDb();
      return await new Promise((resolve, reject) => {
        const tx = db.transaction(FAULT_CACHE_STORE, 'readonly');
        const req = tx.objectStore(FAULT_CACHE_STORE).get('library');
        req.onsuccess = () => resolve(req.result || null);
        req.onerror = () => reject(req.error);
        tx.oncomplete = () => db.close();
      });
    } catch (_) { return null; }
  }

  async function writeFaultCache() {
    try {
      const db = await openFaultCacheDb();
      await new Promise((resolve, reject) => {
        const tx = db.transaction(FAULT_CACHE_STORE, 'readwrite');
        tx.objectStore(FAULT_CACHE_STORE).put({ key: 'library', faults: faultLibrary, etag: faultLibraryEtag, updatedAt: new Date().toISOString() });
        tx.oncomplete = resolve;
        tx.onerror = () => reject(tx.error);
        tx.onabort = () => reject(tx.error);
      });
      db.close();
    } catch (_) {}
  }

  async function faultLibraryRequest(options = {}) {
    const headers = await centralHeaders(options.body !== undefined);
    const res = await fetch(FAULT_LIBRARY_URL, { cache: 'no-store', ...options, headers: { ...headers, ...(options.headers || {}) } });
    const text = await res.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch (_) {}
    if (!res.ok) {
      const error = new Error(data.error || text || `Storingsactie mislukt (${res.status})`);
      error.status = res.status;
      throw error;
    }
    if (Array.isArray(data.faults)) faultLibrary = data.faults;
    if (data.etag !== undefined) faultLibraryEtag = data.etag || null;
    faultLibraryOffline = false;
    faultLibraryLoaded = true;
    await writeFaultCache();
    return data;
  }

  async function loadFaultLibrary(force = false) {
    if (!canViewFaultLibrary()) return [];
    // machinepark-fault-cache-online-refresh-v1
    // Offline mag de laatst bekende bibliotheek direct gebruikt worden. Online moet de centrale lijst altijd opnieuw worden opgehaald, ook als IndexedDB al geladen is.
    if (!force && faultLibraryLoading) return faultLibraryLoading;
    if (!force && faultLibraryLoaded && navigator.onLine === false) return faultLibrary;
    faultLibraryLoading = (async () => {
      if (!faultLibraryLoaded) {
        const cached = await readFaultCache();
        if (cached && Array.isArray(cached.faults)) {
          faultLibrary = cached.faults;
          faultLibraryEtag = cached.etag || null;
          faultLibraryLoaded = true;
          faultLibraryOffline = true;
        }
      }
      if (navigator.onLine === false) return faultLibrary;
      try {
        await faultLibraryRequest();
      } catch (error) {
        if (!faultLibraryLoaded) throw error;
        faultLibraryOffline = true;
      }
      return faultLibrary;
    })().finally(() => { faultLibraryLoading = null; });
    return faultLibraryLoading;
  }
  window.machineparkLoadFaultLibrary = loadFaultLibrary;

  function optionValues(values) {
    return [...new Set(values.map((item) => String(item || '').trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'nl-BE', { numeric: true, sensitivity: 'base' }));
  }

  function fillSelect(select, values, emptyLabel) {
    if (!select) return;
    const current = select.value;
    select.innerHTML = `<option value="">${esc(emptyLabel)}</option>` + optionValues(values).map((value) => `<option value="${esc(value)}">${esc(value)}</option>`).join('');
    if ([...select.options].some((option) => option.value === current)) select.value = current;
  }

  function renderFaultLibrary() {
    const body = document.getElementById('faultLibraryBody');
    const status = document.getElementById('faultLibraryStatus');
    if (!body || !status) return;
    const add = document.getElementById('addFaultLibraryItem');
    if (add) add.style.display = canManageFaultLibrary() ? '' : 'none';
    if (!canViewFaultLibrary()) {
      body.innerHTML = '<tr><td colspan="15"><div class="empty">Geen toegang tot de storingsbibliotheek.</div></td></tr>';
      return;
    }
    if (!faultLibraryLoaded) {
      status.textContent = 'Storingsbibliotheek laden…';
      body.innerHTML = '<tr><td colspan="15"><div class="empty">Storingen worden geladen…</div></td></tr>';
      loadFaultLibrary().then(renderFaultLibrary).catch((error) => {
        status.textContent = error.message;
        body.innerHTML = '<tr><td colspan="15"><div class="empty">Storingsbibliotheek niet beschikbaar.</div></td></tr>';
      });
      return;
    }

    const brandFilter = document.getElementById('faultBrandFilter');
    const modelFilter = document.getElementById('faultModelFilter');
    const categoryFilter = document.getElementById('faultCategoryFilter');
    fillSelect(brandFilter, faultLibrary.map((fault) => fault.brand), 'Alle merken');
    const selectedBrand = brandFilter?.value || '';
    fillSelect(modelFilter, faultLibrary.filter((fault) => !selectedBrand || fault.brand === selectedBrand).map((fault) => fault.model), 'Alle modellen');
    fillSelect(categoryFilter, faultLibrary.map((fault) => fault.category), 'Alle categorieën');

    const query = faultNorm(state.query || '');
    const selectedModel = modelFilter?.value || '';
    const selectedCategory = categoryFilter?.value || '';
    const visible = faultLibrary.filter((fault) => {
      if (fault.active === false && !canManageFaultLibrary()) return false;
      if (selectedBrand && fault.brand !== selectedBrand) return false;
      if (selectedModel && fault.model !== selectedModel) return false;
      if (selectedCategory && fault.category !== selectedCategory) return false;
      if (query && !faultSearchText(fault).includes(query)) return false;
      return true;
    }).sort((a, b) => faultSpecificity(a) - faultSpecificity(b) || String(a.brand || '').localeCompare(String(b.brand || ''), 'nl-BE') || String(a.model || '').localeCompare(String(b.model || ''), 'nl-BE') || String(a.code || a.name || '').localeCompare(String(b.code || b.name || ''), 'nl-BE', { numeric: true }));

    status.textContent = `${visible.length} van ${faultLibrary.length} storing${faultLibrary.length === 1 ? '' : 'en'}${faultLibraryOffline ? ' · offline opgeslagen bibliotheek' : ' · centraal bijgewerkt'}`;
    if (!visible.length) {
      body.innerHTML = '<tr><td colspan="15"><div class="empty"><div class="big">⚠</div>Geen storingen gevonden.</div></td></tr>';
      return;
    }
    body.innerHTML = visible.map((fault) => {
      // machinepark-fault-overview-all-fields-v1
      const overviewText = (value) => String(value ?? '').trim() || '—';
      const overviewList = (items) => faultLines(items).join(' · ') || '—';
      // Elke overzichtswaarde wordt bij elke render rechtstreeks uit hetzelfde actuele fault-object gelezen als de detailweergave.
      const overview = {
        code: overviewText(fault.code),
        name: overviewText(fault.name),
        category: overviewText(fault.category),
        brand: overviewText(fault.brand),
        model: overviewText(fault.model),
        description: overviewText(fault.description),
        message: overviewText(fault.message),
        symptoms: overviewList(fault.symptoms),
        causes: overviewList(fault.causes),
        solution1: overviewText(fault.solution1),
        solution2: overviewText(fault.solution2),
        solutions: overviewList(fault.solutions),
        notes: overviewText(fault.notes),
        active: fault.active !== false,
      };
      return `<tr><td><span class="fault-code">${esc(overview.code)}</span></td><td><span class="fault-name">${esc(overview.name)}</span></td><td>${esc(overview.category)}</td><td>${esc(overview.brand)}</td><td>${esc(overview.model)}</td><td><div class="fault-overview-cell" title="${esc(overview.description)}">${esc(overview.description)}</div></td><td><div class="fault-overview-cell" title="${esc(overview.message)}">${esc(overview.message)}</div></td><td><div class="fault-overview-cell" title="${esc(overview.symptoms)}">${esc(overview.symptoms)}</div></td><td><div class="fault-overview-cell" title="${esc(overview.causes)}">${esc(overview.causes)}</div></td><td><div class="fault-overview-cell" title="${esc(overview.solution1)}">${esc(overview.solution1)}</div></td><td><div class="fault-overview-cell" title="${esc(overview.solution2)}">${esc(overview.solution2)}</div></td><td><div class="fault-overview-cell" title="${esc(overview.solutions)}">${esc(overview.solutions)}</div></td><td><div class="fault-overview-cell" title="${esc(overview.notes)}">${esc(overview.notes)}</div></td><td>${overview.active ? '<span class="badge success">Ja</span>' : '<span class="badge gray">Nee</span>'}</td><td><button type="button" class="btn small" data-fault-details="${esc(fault.id)}">Bekijken</button></td></tr>`;
    }).join('');
  }
  window.machineparkRenderFaultLibrary = renderFaultLibrary;

  // machinepark-fault-overview-live-sync-v1
  let faultOverviewSyncing = null;
  async function syncFaultOverviewFromCentral() {
    if (!canViewFaultLibrary() || navigator.onLine === false) return faultLibrary;
    if (faultOverviewSyncing) return faultOverviewSyncing;
    faultOverviewSyncing = loadFaultLibrary(true)
      .then((faults) => {
        if (state.view === 'faults') renderFaultLibrary();
        return faults;
      })
      .finally(() => { faultOverviewSyncing = null; });
    return faultOverviewSyncing;
  }
  window.machineparkSyncFaultOverview = syncFaultOverviewFromCentral;

  function listSection(title, items) {
    if (!Array.isArray(items) || !items.length) return '';
    return `<div class="fault-detail-section"><h4>${esc(title)}</h4><ol class="fault-detail-list">${items.map((item) => `<li>${esc(item)}</li>`).join('')}</ol></div>`;
  }

  function textSection(title, text) {
    if (!String(text || '').trim()) return '';
    return `<div class="fault-detail-section"><h4>${esc(title)}</h4><p>${esc(text)}</p></div>`;
  }

  function showFaultDetails(id) {
    const fault = faultLibrary.find((item) => item.id === id);
    if (!fault) return;
    const body = `<div class="fault-detail-grid"><div><div style="display:flex;gap:7px;align-items:center;flex-wrap:wrap"><strong style="font-size:19px">${esc(faultTitle(fault))}</strong>${faultScopeBadge(fault)}${fault.category ? `<span class="badge">${esc(fault.category)}</span>` : ''}</div><div class="muted" style="margin-top:5px">${esc(faultScopeText(fault))}</div></div>${textSection('Gedetailleerde omschrijving', fault.description)}${textSection('Melding', fault.message)}${listSection('Symptomen', fault.symptoms)}${listSection('Mogelijke oorzaken', fault.causes)}${textSection('Oplossing 1', fault.solution1)}${textSection('Oplossing 2', fault.solution2)}${listSection('Extra controle / oplossingen', fault.solutions)}${textSection('Interne opmerkingen', fault.notes)}</div>`;
    showModal('Storing', body, 'Sluiten', async () => closeModal());
    setTimeout(() => {
      if (!canManageFaultLibrary()) return;
      const foot = document.querySelector('#modal .modal-foot');
      if (!foot) return;
      const edit = document.createElement('button');
      edit.type = 'button'; edit.className = 'btn'; edit.textContent = 'Bewerken';
      edit.onclick = () => openFaultEditor(fault);
      const del = document.createElement('button');
      del.type = 'button'; del.className = 'btn danger'; del.textContent = 'Verwijderen';
      del.onclick = () => deleteFaultLibraryItem(fault);
      foot.insertBefore(del, foot.firstChild);
      foot.insertBefore(edit, foot.firstChild);
    }, 0);
  }

  function openFaultEditor(fault = null) {
    if (!canManageFaultLibrary()) return;
    const editing = Boolean(fault?.id);
    const body = `<div class="form-grid"><div class="field"><label>Storingscode / nummer</label><input name="code" maxlength="80" value="${esc(fault?.code || '')}" placeholder="Optioneel, bv. E187"></div><div class="field"><label>Categorie</label><input name="category" maxlength="100" value="${esc(fault?.category || '')}" placeholder="bv. Water, Elektrisch"></div><div class="field full"><label>Algemene omschrijving / storing *</label><input name="name" maxlength="160" required value="${esc(fault?.name || '')}" placeholder="bv. Waterlek, Aardfout of Boiler vult niet"></div><div class="field"><label>Merk</label><input name="brand" maxlength="100" value="${esc(fault?.brand || '')}" placeholder="Leeg = alle merken"><div class="fault-editor-help">Leeg laten voor een algemene storing.</div></div><div class="field"><label>Model</label><input name="model" maxlength="140" value="${esc(fault?.model || '')}" placeholder="Leeg = alle modellen van het merk"><div class="fault-editor-help">Een model wordt alleen gebruikt als ook een merk is ingevuld.</div></div><div class="field full"><label>Gedetailleerde omschrijving</label><textarea name="description" maxlength="1600" placeholder="Wat betekent deze storing?">${esc(fault?.description || '')}</textarea></div><div class="field full"><label>Melding</label><textarea name="message" maxlength="1600" placeholder="Melding die op het toestel verschijnt">${esc(fault?.message || '')}</textarea></div><div class="field full"><label>Symptomen</label><textarea name="symptoms" placeholder="Eén symptoom per regel">${esc((fault?.symptoms || []).join('\n'))}</textarea></div><div class="field full"><label>Mogelijke oorzaken</label><textarea name="causes" placeholder="Eén mogelijke oorzaak per regel">${esc((fault?.causes || []).join('\n'))}</textarea></div><div class="field full"><label>Oplossing 1</label><textarea name="solution1" maxlength="1200">${esc(fault?.solution1 || '')}</textarea></div><div class="field full"><label>Oplossing 2</label><textarea name="solution2" maxlength="1200">${esc(fault?.solution2 || '')}</textarea></div><div class="field full"><label>Extra controle / oplossingen</label><textarea name="solutions" style="min-height:130px" placeholder="Eén extra controle of oplossing per regel">${esc((fault?.solutions || []).join('\n'))}</textarea></div><div class="field full"><label>Interne opmerkingen</label><textarea name="notes" maxlength="2000">${esc(fault?.notes || '')}</textarea></div><div class="field full"><label style="display:flex;align-items:center;gap:8px"><input type="checkbox" name="active" ${fault?.active === false ? '' : 'checked'} style="width:auto"> Actief en zichtbaar voor techniekers</label></div></div>`;
    showModal(editing ? 'Storing bewerken' : 'Storing toevoegen', body, editing ? 'Wijzigingen opslaan' : 'Storing opslaan', async (fd) => {
      try {
        const payload = {
          id: fault?.id || '',
          code: val(fd, 'code'),
          name: val(fd, 'name'),
          category: val(fd, 'category'),
          brand: val(fd, 'brand'),
          model: val(fd, 'model'),
          description: val(fd, 'description'),
          message: val(fd, 'message'),
          solution1: val(fd, 'solution1'),
          solution2: val(fd, 'solution2'),
          symptoms: faultLines(val(fd, 'symptoms')),
          causes: faultLines(val(fd, 'causes')),
          solutions: faultLines(val(fd, 'solutions')),
          notes: val(fd, 'notes'),
          active: Boolean(fd.get('active')),
        };
        await faultLibraryRequest({ method: 'POST', body: JSON.stringify({ action: 'save-fault', fault: payload, etag: faultLibraryEtag }) });
        closeModal();
        toast(editing ? 'Storing bijgewerkt' : 'Storing toegevoegd');
        renderFaultLibrary();
      } catch (error) { alert(error.message); }
    });
  }

  async function deleteFaultLibraryItem(fault) {
    if (!canManageFaultLibrary() || !fault) return;
    if (!confirm(`Storing “${faultTitle(fault)}” verwijderen? Bestaande depannages die deze storing gebruikten behouden hun opgeslagen tekst.`)) return;
    try {
      await faultLibraryRequest({ method: 'POST', body: JSON.stringify({ action: 'delete-fault', faultId: fault.id, etag: faultLibraryEtag }) });
      closeModal();
      toast('Storing verwijderd');
      renderFaultLibrary();
    } catch (error) { alert(error.message); }
  }

  function matchingFaultsForDevice(device, query = '') {
    const q = faultNorm(query);
    const candidates = faultLibrary.filter((fault) => fault.active !== false && faultMatchesQuery(fault, q));
    const visible = q ? candidates : candidates.filter((fault) => faultAppliesToDevice(fault, device));
    return visible.sort((a, b) => {
      const aMismatch = faultAppliesToDevice(a, device) ? 0 : 1;
      const bMismatch = faultAppliesToDevice(b, device) ? 0 : 1;
      return aMismatch - bMismatch || faultSpecificity(a) - faultSpecificity(b) || String(a.code || a.name || '').localeCompare(String(b.code || b.name || ''), 'nl-BE', { numeric: true });
    }).slice(0, 12);
  }

  function pickerResultsHtml(device, query) {
    const matches = matchingFaultsForDevice(device, query);
    if (!matches.length) return '<div class="global-search-empty">Geen passende storing gevonden.</div>';
    return matches.map((fault) => {
      const applies = faultAppliesToDevice(fault, device);
      const mismatch = applies ? '' : ' · ⚠ ander merk/model';
      return `<button type="button" class="fault-picker-result" data-fault-pick="${esc(fault.id)}"><strong>${esc(faultTitle(fault))}</strong><small>${esc(faultScopeText(fault))}${fault.category ? ` · ${esc(fault.category)}` : ''}${mismatch}</small></button>`;
    }).join('');
  }

  function faultSnapshot(fault) {
    return {
      id: fault.id,
      version: fault.version || 1,
      code: fault.code || '',
      name: fault.name || '',
      category: fault.category || '',
      brand: fault.brand || '',
      model: fault.model || '',
      message: fault.message || '',
      solution1: fault.solution1 || '',
      solution2: fault.solution2 || '',
      solutions: [...(fault.solutions || [])],
      capturedAt: new Date().toISOString(),
    };
  }

  function applyFaultToInputs(fault, issueInput, solutionInput, holder) {
    if (!fault || !issueInput) return;
    issueInput.value = faultTitle(fault);
    const proposedSolutions = [fault.solution1, fault.solution2, ...(Array.isArray(fault.solutions) ? fault.solutions : [])].map((item) => String(item || '').trim()).filter(Boolean);
    if (solutionInput && proposedSolutions.length) {
      const proposed = proposedSolutions.join('\n');
      if (!solutionInput.value.trim() || confirm('Er staat al een oplossing ingevuld. Vervangen door de oplossing uit de storingsbibliotheek?')) solutionInput.value = proposed;
    }
    if (holder) {
      holder._machineparkFaultSnapshot = faultSnapshot(fault);
      const selected = holder.querySelector('.fault-picker-selected');
      if (selected) selected.textContent = `Gekoppeld: ${faultTitle(fault)}`;
    }
  }

  function attachSingleBreakdownFaultPicker(record) {
    const grid = document.querySelector('#modal .modal-body .form-grid');
    if (!grid || grid.querySelector('.fault-breakdown-picker')) return;
    const field = document.createElement('div');
    field.className = 'field full fault-breakdown-picker';
    field.innerHTML = `<div class="fault-breakdown-picker-head"><div><strong>Storingsbibliotheek</strong><div class="muted" style="font-size:11px;margin-top:3px">Zoek op code, storing of oplossing. Resultaten worden afgestemd op het gekozen toestel.</div></div></div><input type="search" class="fault-picker-search" placeholder="bv. E187, waterlek, aardfout…" autocomplete="off"><div class="fault-picker-results"></div><div class="fault-picker-selected">${record?.faultRef ? `Gekoppeld: ${esc([record.faultRef.code, record.faultRef.name].filter(Boolean).join(' — '))}` : ''}</div>`;
    if (record?.faultRef) field._machineparkFaultSnapshot = record.faultRef;
    grid.appendChild(field);
    const input = field.querySelector('.fault-picker-search');
    const results = field.querySelector('.fault-picker-results');
    const render = async () => {
      await loadFaultLibrary(true);
      const deviceId = document.querySelector('#modal .device-select')?.value || record?.deviceId || '';
      const device = state.devices.find((item) => item.id === deviceId) || {};
      results.innerHTML = pickerResultsHtml(device, input.value);
      results.classList.add('show');
    };
    input.onfocus = render;
    input.oninput = render;
    input.onkeydown = (event) => { if (event.key === 'Escape') results.classList.remove('show'); };
    results.onclick = (event) => {
      const choice = event.target.closest('[data-fault-pick]');
      if (!choice) return;
      const fault = faultLibrary.find((item) => item.id === choice.dataset.faultPick);
      applyFaultToInputs(fault, document.querySelector('#modal [name="issue"]'), document.querySelector('#modal [name="solution"]'), field);
      input.value = faultTitle(fault);
      results.classList.remove('show');
    };
  }

  function augmentBreakdownCards() {
    document.querySelectorAll('#modal .breakdown-machine-card').forEach((card) => {
      if (card.querySelector('.fault-inline-tools')) return;
      const issue = card.querySelector('.breakdown-machine-issue');
      if (!issue) return;
      const tools = document.createElement('div');
      tools.className = 'fault-inline-tools';
      tools.innerHTML = `<button type="button" class="btn small fault-inline-toggle">⚠ Storingsbibliotheek</button><div class="fault-inline-panel"><input type="search" class="fault-picker-search" placeholder="Zoek code of storing…" autocomplete="off"><div class="fault-picker-results"></div><div class="fault-picker-selected"></div></div>`;
      issue.parentElement?.insertBefore(tools, issue);
      const toggle = tools.querySelector('.fault-inline-toggle');
      const panel = tools.querySelector('.fault-inline-panel');
      const input = tools.querySelector('.fault-picker-search');
      const results = tools.querySelector('.fault-picker-results');
      toggle.onclick = async () => {
        if (!card.querySelector('.breakdown-machine-check')?.checked) { toast('Selecteer eerst dit toestel'); return; }
        panel.classList.toggle('show');
        if (panel.classList.contains('show')) {
          await loadFaultLibrary(true);
          input.focus();
          const device = state.devices.find((item) => item.id === card.dataset.breakdownDevice) || {};
          results.innerHTML = pickerResultsHtml(device, input.value);
          results.classList.add('show');
        }
      };
      input.oninput = () => {
        const device = state.devices.find((item) => item.id === card.dataset.breakdownDevice) || {};
        results.innerHTML = pickerResultsHtml(device, input.value);
        results.classList.add('show');
      };
      input.onkeydown = (event) => { if (event.key === 'Escape') panel.classList.remove('show'); };
      results.onclick = (event) => {
        const choice = event.target.closest('[data-fault-pick]');
        if (!choice) return;
        const fault = faultLibrary.find((item) => item.id === choice.dataset.faultPick);
        applyFaultToInputs(fault, issue, card.querySelector('.breakdown-machine-solution'), tools);
        input.value = faultTitle(fault);
        results.classList.remove('show');
      };
    });
  }

  window.machineparkAugmentBreakdownFaultCards = augmentBreakdownCards;
  window.machineparkFaultRefFromCard = card => card?.querySelector('.fault-inline-tools')?._machineparkFaultSnapshot || null;

  const baseInitBreakdownLocationFormForFaults = initBreakdownLocationForm;
  initBreakdownLocationForm = function() {
    const result = baseInitBreakdownLocationFormForFaults();
    const box = document.getElementById('breakdownLocationDevices');
    if (box) {
      augmentBreakdownCards();
      const observer = new MutationObserver(() => augmentBreakdownCards());
      observer.observe(box, { childList: true, subtree: true });
      setTimeout(() => { if (!document.body.contains(box)) observer.disconnect(); }, 300000);
    }
    return result;
  };

  const baseOpenBreakdownForFaults = openBreakdown;
  openBreakdown = function(id) {
    const record = id ? state.breakdowns.find((item) => item.id === id) || null : null;
    const result = baseOpenBreakdownForFaults(id);
    if (id) loadFaultLibrary().then(() => setTimeout(() => attachSingleBreakdownFaultPicker(record), 0)).catch(() => setTimeout(() => attachSingleBreakdownFaultPicker(record), 0));
    return result;
  };
  window.openBreakdown = openBreakdown;

  const basePutForFaults = put;
  put = async function(storeName, obj) {
    if (storeName === 'breakdowns' && obj) {
      const picker = document.querySelector('#modal .fault-breakdown-picker');
      if (picker?._machineparkFaultSnapshot) obj = { ...obj, faultRef: picker._machineparkFaultSnapshot };
    }
    return basePutForFaults(storeName, obj);
  };

  const basePutManyForFaults = putMany;
  putMany = async function(storeName, items) {
    if (storeName === 'breakdowns' && Array.isArray(items)) {
      items = items.map((item) => {
        const card = [...document.querySelectorAll('#modal .breakdown-machine-card')].find((candidate) => candidate.dataset.breakdownDevice === item.deviceId);
        const holder = card?.querySelector('.fault-inline-tools');
        return holder?._machineparkFaultSnapshot ? { ...item, faultRef: holder._machineparkFaultSnapshot } : item;
      });
    }
    return basePutManyForFaults(storeName, items);
  };

  const basePageMetaForFaults = pageMeta;
  pageMeta = function(view) {
    if (view === 'faults') return ['Storingen', 'Zoek storingscodes, storingen en oplossingen per merk of model.'];
    return basePageMetaForFaults(view);
  };
  machineparkViewQueries.faults = machineparkViewQueries.faults || '';

  const baseConfigureSearchForFaults = configureSearchForView;
  configureSearchForView = function(view) {
    if (view !== 'faults') return baseConfigureSearchForFaults(view);
    const input = document.getElementById('globalSearch');
    const actions = document.querySelector('.top-actions');
    if (!input || !actions) return;
    actions.style.display = '';
    state.query = machineparkViewQueries.faults || '';
    input.value = state.query;
    input.placeholder = 'Zoek code, storing, oorzaak of oplossing…';
    closeGlobalSearch();
  };

  const baseRenderAllForFaults = renderAll;
  renderAll = function() {
    baseRenderAllForFaults();
    if (state.view === 'faults') {
      renderFaultLibrary();
      syncFaultOverviewFromCentral().catch(() => {});
    }
  };

  const baseRenderGlobalSearchForFaults = renderGlobalSearchResults;
  renderGlobalSearchResults = function() {
    baseRenderGlobalSearchForFaults();
    if (state.view !== 'dashboard' || !state.query || !canViewFaultLibrary() || !faultLibraryLoaded) return;
    const box = document.getElementById('globalSearchResults');
    if (!box) return;
    const q = faultNorm(state.query);
    const matches = faultLibrary.filter((fault) => fault.active !== false && faultSearchText(fault).includes(q)).slice(0, 6);
    if (!matches.length) return;
    box.querySelector('.global-search-empty')?.remove();
    box.insertAdjacentHTML('beforeend', '<div class="global-search-head">Storingen</div>' + matches.map((fault) => `<button type="button" class="global-search-result" data-global-fault="${esc(fault.id)}"><strong>⚠ ${esc(faultTitle(fault))}</strong><small>${esc(faultScopeText(fault))}${fault.category ? ` · ${esc(fault.category)}` : ''}</small></button>`).join(''));
    box.classList.add('show');
  };

  function bindFaultLibraryPage() {
    const refresh = document.getElementById('refreshFaultLibrary');
    const add = document.getElementById('addFaultLibraryItem');
    const brand = document.getElementById('faultBrandFilter');
    const model = document.getElementById('faultModelFilter');
    const category = document.getElementById('faultCategoryFilter');
    if (refresh) refresh.onclick = async () => { await syncFaultOverviewFromCentral(); };
    if (add) add.onclick = () => openFaultEditor();
    if (brand) brand.onchange = () => { if (model) model.value = ''; renderFaultLibrary(); };
    if (model) model.onchange = renderFaultLibrary;
    if (category) category.onchange = renderFaultLibrary;
    document.body.addEventListener('click', (event) => {
      const details = event.target.closest('[data-fault-details]');
      if (details) { showFaultDetails(details.dataset.faultDetails); return; }
      const global = event.target.closest('[data-global-fault]');
      if (global) { closeGlobalSearch(); showFaultDetails(global.dataset.globalFault); }
    });
  }

  const previousServerAccessForFaults = window.applyMachineparkServerAccess;
  if (typeof previousServerAccessForFaults === 'function') {
    window.applyMachineparkServerAccess = function(body) {
      const result = previousServerAccessForFaults(body);
      if (canViewFaultLibrary()) loadFaultLibrary().then(() => { if (state.view === 'faults') renderFaultLibrary(); }).catch(() => {});
      return result;
    };
  }

  function initFaultFeature() {
    bindFaultLibraryPage();
    readFaultCache().then((cached) => {
      if (cached && Array.isArray(cached.faults)) {
        faultLibrary = cached.faults;
        faultLibraryEtag = cached.etag || null;
        faultLibraryLoaded = true;
        faultLibraryOffline = true;
      }
      if (canViewFaultLibrary()) loadFaultLibrary().then(() => { if (state.view === 'faults') renderFaultLibrary(); }).catch(() => {});
    });
  }

  // machinepark-fault-cache-reconnect-sync-v1
  window.addEventListener('online', () => {
    if (!canViewFaultLibrary()) return;
    loadFaultLibrary(true).then(() => { if (state.view === 'faults') renderFaultLibrary(); }).catch(() => {});
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initFaultFeature, { once: true });
  else initFaultFeature();
})();
