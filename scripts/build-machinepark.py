from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
sw = (ROOT / "sw.js").read_text(encoding="utf-8")

PATCH_MARKER = 'data-machinepark-build-fix="mobile-search-technician-v1"'
PHOTO_PATCH_MARKER = 'data-machinepark-build-fix="service-report-photos-v1"'

# De bronpagina is bewust één groot zelfstandig HTML-bestand. Voeg deze twee kleine
# UI-correcties tijdens de build idempotent toe, zodat de bestaande applicatielogica
# niet breed hoeft te worden herschreven.
if PATCH_MARKER not in index:
    mobile_style = f'''
<style {PATCH_MARKER}>
@media(max-width:700px){{
  .topbar{{flex-wrap:wrap}}
  .title{{order:1;min-width:0;flex:1 1 180px}}
  .account-summary{{order:2;flex:0 0 auto}}
  .top-actions{{display:flex;order:3;width:100%}}
  .top-actions .search{{width:100%}}
  .top-actions .search input{{width:100%}}
}}
</style>
'''

    technician_script = f'''
<script {PATCH_MARKER}>
(() => {{
  const originalOpenDevice = openDevice;
  const originalShowDeviceHistory = showDeviceHistory;
  const technicianCanEditDevice = () => window.machineparkRole === 'technieker';
  window.machineparkTechnicianCanEditDevice = technicianCanEditDevice;

  openDevice = function(id) {{
    if (!technicianCanEditDevice() || !id) return originalOpenDevice(id);
    const old = state.devices.find(d => d.id === id);
    if (!old) {{ toast('Toestel niet gevonden'); return; }}

    const body = `<div class="form-grid">
      <div class="field full"><div class="alert"><strong>Techniekerrechten</strong>Technieker kan alleen toestelstatus en notities aanpassen. Andere toestelgegevens blijven alleen-lezen.</div></div>
      <div class="field"><label>Toestel</label><input value="${{esc(old.assetCode || old.model || 'Toestel')}}" readonly style="background:#f4f6f5"></div>
      <div class="field"><label>Locatie</label><input value="${{esc(deviceLocationAt(old) || old.location || 'Geen locatie')}}" readonly style="background:#f4f6f5"></div>
      <div class="field"><label>Status</label><select name="status">${{['Actief','In herstelling','Buiten dienst'].map(x => `<option ${{old.status === x ? 'selected' : ''}}>${{x}}</option>`).join('')}}</select></div>
      <div class="field full"><label>Notities</label><textarea name="notes">${{esc(old.notes || '')}}</textarea></div>
    </div>`;

    showModal('Toestelstatus & notities', body, 'Opslaan', async fd => {{
      const obj = {{
        ...old,
        status: val(fd, 'status') || old.status || 'Actief',
        notes: val(fd, 'notes'),
        updatedAt: new Date().toISOString(),
      }};
      await put('devices', obj);
      closeModal();
      await refresh();
      toast('Toestelstatus en notities opgeslagen');
    }});
  }};

  showDeviceHistory = function(id) {{
    originalShowDeviceHistory(id);
    if (!technicianCanEditDevice()) return;
    setTimeout(() => {{
      const foot = $('#modal .modal-foot');
      if (!foot || $('#technicianEditDevice')) return;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.id = 'technicianEditDevice';
      btn.className = 'btn';
      btn.textContent = 'Status / notities aanpassen';
      btn.onclick = () => {{ closeModal(); openDevice(id); }};
      foot.insertBefore(btn, foot.querySelector('.btn.primary') || null);
    }}, 0);
  }};
}})();
</script>
'''

    if "</head>" not in index or "</body>" not in index:
        raise SystemExit("Buildvalidatie mislukt: HTML-afsluiters ontbreken")
    index = index.replace("</head>", mobile_style + "</head>", 1)
    index = index.replace("</body>", technician_script + "</body>", 1)
    index_path.write_text(index, encoding="utf-8")

# Onderhoud en depannage krijgen maximaal vier gecomprimeerde foto's per verslag.
# De bestaande formulieren en opslagfuncties worden alleen aan de UI-rand uitgebreid;
# de onderliggende records blijven volledig compatibel met bestaande gegevens.
if PHOTO_PATCH_MARKER not in index:
    photo_style = f'''
<style {PHOTO_PATCH_MARKER}>
.service-photo-editor{{grid-column:1/-1}}
.service-photo-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(105px,1fr));gap:10px;margin:8px 0}}
.service-photo-item{{border:1px solid var(--line);border-radius:12px;background:#f8faf9;padding:7px;display:grid;gap:6px}}
.service-photo-item img{{width:100%;height:96px;object-fit:cover;border-radius:8px;background:white}}
.service-photo-item label{{display:flex;gap:6px;align-items:center;font-size:11px;font-weight:650;color:var(--muted)}}
.service-photo-files{{padding:9px!important}}
.service-photo-details{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-top:8px}}
.service-photo-details img{{width:100%;height:150px;object-fit:cover;border-radius:12px;border:1px solid var(--line);background:#f8faf9}}
@media(max-width:700px){{
  .service-photo-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}
  .service-photo-details{{grid-template-columns:repeat(2,minmax(0,1fr))}}
}}
</style>
'''

    photo_script = f'''
<script {PHOTO_PATCH_MARKER}>
(() => {{
  const REPORT_PHOTO_LIMIT = 4;

  function insertBeforeLastDiv(html, extra) {{
    const pos = html.lastIndexOf('</div>');
    return pos < 0 ? html + extra : html.slice(0, pos) + extra + html.slice(pos);
  }}

  function insertBeforeFinalDivPair(html, extra) {{
    const marker = '</div></div>';
    const pos = html.lastIndexOf(marker);
    return pos < 0 ? insertBeforeLastDiv(html, extra) : html.slice(0, pos) + extra + html.slice(pos);
  }}

  function photoArray(value) {{
    return Array.isArray(value) ? value.filter(x => typeof x === 'string' && x.startsWith('data:image/')) : [];
  }}

  function servicePhotoEditorHtml(existing = [], inputClass = '') {{
    const photos = photoArray(existing);
    const current = photos.length
      ? `<div class="service-photo-grid">${{photos.map((src, i) => `<div class="service-photo-item"><img src="${{src}}" alt="Verslagfoto ${{i + 1}}"><label><input type="checkbox" class="service-photo-remove" value="${{i}}"> Verwijderen</label></div>`).join('')}}</div>`
      : '<div class="muted" style="font-size:11px;margin:4px 0 8px">Nog geen foto’s toegevoegd.</div>';
    return `<div class="field full service-photo-editor">
      <label>Foto’s bij verslag</label>
      ${{current}}
      <input class="service-photo-files ${{inputClass}}" type="file" accept="image/*" multiple>
      <div class="muted" style="font-size:11px;margin-top:4px">Maximaal ${{REPORT_PHOTO_LIMIT}} foto’s per verslag. Foto’s worden automatisch verkleind voor opslag.</div>
      <div class="service-photo-selected muted" style="font-size:11px;margin-top:4px"></div>
    </div>`;
  }}

  function servicePhotoDetailsHtml(photos) {{
    const list = photoArray(photos);
    if (!list.length) return '<span class="muted">Geen foto’s bij dit verslag.</span>';
    return `<div class="service-photo-details">${{list.map((src, i) => `<img src="${{src}}" alt="Verslagfoto ${{i + 1}}">`).join('')}}</div>`;
  }}

  async function collectServicePhotos(editor, existing = []) {{
    if (!editor) return photoArray(existing);
    const remove = new Set([...editor.querySelectorAll('.service-photo-remove:checked')].map(x => Number(x.value)));
    const kept = photoArray(existing).filter((_, i) => !remove.has(i));
    const input = editor.querySelector('.service-photo-files');
    const files = [...(input?.files || [])].filter(file => file && file.size);
    if (kept.length + files.length > REPORT_PHOTO_LIMIT) {{
      throw new Error(`Maximaal ${{REPORT_PHOTO_LIMIT}} foto’s per onderhouds- of depannageverslag.`);
    }}
    const added = [];
    for (const file of files) added.push(await compressImage(file));
    return [...kept, ...added].filter(Boolean);
  }}

  function editorForRecord(storeName, deviceId) {{
    const attr = storeName === 'maintenance' ? 'maintenanceDevice' : 'breakdownDevice';
    return [...document.querySelectorAll('.maintenance-machine-card')]
      .find(card => card.dataset?.[attr] === deviceId)
      ?.querySelector('.service-photo-editor') || null;
  }}

  const originalMaintenanceForm = maintenanceForm;
  maintenanceForm = function(m = {{}}) {{
    return insertBeforeLastDiv(originalMaintenanceForm(m), servicePhotoEditorHtml(m.photos || []));
  }};

  const originalBreakdownForm = breakdownForm;
  breakdownForm = function(b = {{}}) {{
    return insertBeforeLastDiv(originalBreakdownForm(b), servicePhotoEditorHtml(b.photos || []));
  }};

  const originalMaintenanceMachineCardHtml = maintenanceMachineCardHtml;
  maintenanceMachineCardHtml = function(d) {{
    return insertBeforeFinalDivPair(
      originalMaintenanceMachineCardHtml(d),
      servicePhotoEditorHtml([], 'maintenance-machine-photos')
    );
  }};

  const originalBreakdownMachineCardHtml = breakdownMachineCardHtml;
  breakdownMachineCardHtml = function(d) {{
    return insertBeforeFinalDivPair(
      originalBreakdownMachineCardHtml(d),
      servicePhotoEditorHtml([], 'breakdown-machine-photos')
    );
  }};

  const originalSetMaintenanceMachineEnabled = setMaintenanceMachineEnabled;
  setMaintenanceMachineEnabled = function(card, enabled) {{
    originalSetMaintenanceMachineEnabled(card, enabled);
    card?.querySelectorAll('.maintenance-machine-photos').forEach(el => el.disabled = !enabled);
  }};

  const originalSetBreakdownMachineEnabled = setBreakdownMachineEnabled;
  setBreakdownMachineEnabled = function(card, enabled) {{
    originalSetBreakdownMachineEnabled(card, enabled);
    card?.querySelectorAll('.breakdown-machine-photos').forEach(el => el.disabled = !enabled);
  }};

  const originalPut = put;
  put = async function(storeName, obj) {{
    if ((storeName === 'maintenance' || storeName === 'breakdowns') && obj) {{
      const editor = document.querySelector('#modalForm .modal-body > .form-grid > .service-photo-editor');
      if (editor && !editor.closest('.maintenance-machine-card')) {{
        obj = {{ ...obj, photos: await collectServicePhotos(editor, obj.photos || []) }};
      }}
    }}
    return originalPut(storeName, obj);
  }};

  const originalPutMany = putMany;
  putMany = async function(storeName, items) {{
    if ((storeName === 'maintenance' || storeName === 'breakdowns') && Array.isArray(items) && items.length) {{
      const enriched = [];
      for (const item of items) {{
        const editor = editorForRecord(storeName, item.deviceId);
        enriched.push(editor ? {{ ...item, photos: await collectServicePhotos(editor, []) }} : item);
      }}
      items = enriched;
    }}
    return originalPutMany(storeName, items);
  }};

  const originalShowMaintenanceDetails = showMaintenanceDetails;
  showMaintenanceDetails = function(id) {{
    originalShowMaintenanceDetails(id);
    const m = state.maintenance.find(x => x.id === id);
    const grid = document.querySelector('#modal .modal-body .form-grid');
    if (m && grid) {{
      grid.insertAdjacentHTML('beforeend', `<div class="field full"><label>Foto’s bij verslag</label>${{servicePhotoDetailsHtml(m.photos)}}</div>`);
    }}
  }};

  document.addEventListener('change', event => {{
    const input = event.target.closest?.('.service-photo-files');
    if (!input) return;
    const editor = input.closest('.service-photo-editor');
    const info = editor?.querySelector('.service-photo-selected');
    if (info) {{
      const count = input.files?.length || 0;
      info.textContent = count ? `${{count}} nieuwe foto${{count === 1 ? '' : '’s'}} geselecteerd` : '';
    }}
  }});
}})();
</script>
'''
    if "</head>" not in index or "</body>" not in index:
        raise SystemExit("Buildvalidatie mislukt: HTML-afsluiters ontbreken voor verslagfoto's")
    index = index.replace("</head>", photo_style + "</head>", 1)
    index = index.replace("</body>", photo_script + "</body>", 1)
    index_path.write_text(index, encoding="utf-8")

required = {
    "branding": "<title>Machinepark</title>",
    "Clerk profiel": 'id="clerkUserButton"',
    "onderdeel autocomplete": "usage-autocomplete",
    "toestel autocomplete": "device-autocomplete",
    "audit undo": "data-undo-audit",
    "apart onderdelenlogboek": 'id="auditPartsLogBody"',
    "operationeel dashboard": "dashboardProfessional",
    "wit koffietoestel SVG navigatie-icoon": 'class="device-nav-icon-svg"',
    "dashboard toestelbolletje": '<span class="dot"></span><div class="label">Actieve toestellen</div>',
    "veiligheidsbackup": "Machinepark_Veiligheidsbackup_",
    "importverslag": "downloadStockImportReport",
    "onderdelenexport afbeeldingen": "makeStoreZip",
    "afbeeldingskolom export": "Afbeelding bestand",
    "back-up afbeeldingen": "includesImages:true",
    "prijsimport": "Prijs excl. BTW",
    "technieker rol": "technieker",
    "magazijnier rol": "magazijnier",
    "onderhoud navigatie": 'data-view="maintenance"',
    "onderhoud knop": "$('#addMaintenance').onclick=()=>openMaintenance();",
    "locatiegericht onderhoud": 'id="maintenanceLocationSearch"',
    "zoeken op toestelnummer": "locationGroupMatches",
    "zoekhint locatie of toestel": "Typ locatie of toestelnummer…",
    "onderhoud per toestel": "maintenance-machine-card",
    "depannage navigatie": 'data-view="breakdowns"',
    "locatiegerichte depannage": 'id="breakdownLocationSearch"',
    "depannage per toestel": "breakdown-machine-card",
    "registraties verwijderen": "deleteServiceRecordAtomic",
    "onderhoud verwijderen": "deleteMaintenanceFromDetails",
    "depannage verwijderen": "deleteBreakdownFromDetails",
    "onderdelen navigatie": 'data-view="parts"',
    "mobiele zoekfix": PATCH_MARKER,
    "technieker beperkte toestelbewerking": "Technieker kan alleen toestelstatus en notities aanpassen.",
    "technieker bewerkknop": "Status / notities aanpassen",
    "verslagfoto patch": PHOTO_PATCH_MARKER,
    "onderhoud verslagfoto's": "originalMaintenanceForm",
    "depannage verslagfoto's": "originalBreakdownForm",
    "foto's per toestel": "editorForRecord",
    "foto opslag": "collectServicePhotos",
}
for label, needle in required.items():
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: {label} ontbreekt")
if index.count('id="clerkUserButton"') != 1:
    raise SystemExit("Buildvalidatie mislukt: Clerk-profielknop is niet uniek")
if 'id="clearAll"' in index:
    raise SystemExit("Buildvalidatie mislukt: Alles wissen is teruggekeerd")
if "machinepark-v1.64-export-images" not in sw:
    raise SystemExit("Buildvalidatie mislukt: verkeerde service-worker cache")
print("[Machinepark] broncodevalidatie geslaagd")
