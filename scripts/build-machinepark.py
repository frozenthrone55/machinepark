from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
sw = (ROOT / "sw.js").read_text(encoding="utf-8")

PATCH_MARKER = 'data-machinepark-build-fix="mobile-search-v2"'
PHOTO_PATCH_MARKER = 'data-machinepark-build-fix="service-report-photos-v2"'

# Mobiele zoekbalk. De vroegere hardcoded technieker-wrapper is bewust verwijderd:
# alle toestelrechten worden centraal door het configureerbare rollenmodel bepaald.
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
    if "</head>" not in index:
        raise SystemExit("Buildvalidatie mislukt: HTML-head ontbreekt")
    index = index.replace("</head>", mobile_style + "</head>", 1)
    index_path.write_text(index, encoding="utf-8")

# Onderhoud en depannage krijgen maximaal vijf gecomprimeerde foto's per verslag.
# Nieuwe/bewerkte foto’s worden via machineparkPersistServicePhotos buiten de centrale
# snapshot opgeslagen. Bestaande base64-foto’s blijven compatibel tot de achtergrondmigratie.
if PHOTO_PATCH_MARKER not in index:
    photo_style = f'''
<style {PHOTO_PATCH_MARKER}>
.service-photo-editor{{grid-column:1/-1}}
.service-photo-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(105px,1fr));gap:10px;margin:8px 0}}
.service-photo-item{{border:1px solid var(--line);border-radius:12px;background:#f8faf9;padding:7px;display:grid;gap:6px}}
.service-photo-item img{{width:100%;height:96px;object-fit:cover;border-radius:8px;background:white;cursor:zoom-in}}
.service-photo-item label{{display:flex;gap:6px;align-items:center;font-size:11px;font-weight:650;color:var(--muted)}}
.service-photo-files{{padding:9px!important}}
.service-photo-details{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-top:8px}}
.service-photo-details img{{width:100%;height:150px;object-fit:cover;border-radius:12px;border:1px solid var(--line);background:#f8faf9;cursor:zoom-in}}
@media(max-width:700px){{
  .service-photo-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}
  .service-photo-details{{grid-template-columns:repeat(2,minmax(0,1fr))}}
}}
</style>
'''

    photo_script = f'''
<script {PHOTO_PATCH_MARKER}>
(() => {{
  const REPORT_PHOTO_LIMIT = 5;
  const SERVICE_PHOTO_ENDPOINT = '/.netlify/functions/service-photos?';

  function insertBeforeLastDiv(html, extra) {{
    const pos = html.lastIndexOf('</div>');
    return pos < 0 ? html + extra : html.slice(0, pos) + extra + html.slice(pos);
  }}

  function insertBeforeFinalDivPair(html, extra) {{
    const marker = '</div></div>';
    const pos = html.lastIndexOf(marker);
    return pos < 0 ? insertBeforeLastDiv(html, extra) : html.slice(0, pos) + extra + html.slice(pos);
  }}

  function isServicePhoto(value) {{
    const src = String(value || '').trim();
    return src.startsWith('data:image/') || src.includes(SERVICE_PHOTO_ENDPOINT);
  }}

  function photoArray(value) {{
    return Array.isArray(value) ? value.filter(x => typeof x === 'string' && isServicePhoto(x)).slice(0, REPORT_PHOTO_LIMIT) : [];
  }}

  function photoPreviewSrc(src) {{
    return typeof window.machineparkThumbnailRef === 'function' ? window.machineparkThumbnailRef(src) : src;
  }}

  function servicePhotoEditorHtml(existing = [], inputClass = '') {{
    const photos = photoArray(existing);
    const current = photos.length
      ? `<div class="service-photo-grid">${{photos.map((src, i) => `<div class="service-photo-item"><img src="${{esc(photoPreviewSrc(src))}}" data-full-src="${{esc(src)}}" data-photo-lightbox loading="lazy" decoding="async" alt="Verslagfoto ${{i + 1}}"><label><input type="checkbox" class="service-photo-remove" value="${{i}}"> Verwijderen</label></div>`).join('')}}</div>`
      : '<div class="muted" style="font-size:11px;margin:4px 0 8px">Nog geen foto’s toegevoegd.</div>';
    return `<div class="field full service-photo-editor">
      <label>Foto’s bij verslag</label>
      ${{current}}
      <input class="service-photo-files ${{inputClass}}" type="file" accept="image/*" multiple>
      <div class="muted" style="font-size:11px;margin-top:4px">Maximaal ${{REPORT_PHOTO_LIMIT}} foto’s per verslag. Foto’s worden automatisch verkleind en apart opgeslagen.</div>
      <div class="service-photo-selected muted" style="font-size:11px;margin-top:4px"></div>
    </div>`;
  }}

  function servicePhotoDetailsHtml(photos) {{
    const list = photoArray(photos);
    if (!list.length) return '<span class="muted">Geen foto’s bij dit verslag.</span>';
    return `<div class="service-photo-details">${{list.map((src, i) => `<img src="${{esc(photoPreviewSrc(src))}}" data-full-src="${{esc(src)}}" data-photo-lightbox loading="lazy" decoding="async" alt="Verslagfoto ${{i + 1}}">`).join('')}}</div>`;
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
    return [...kept, ...added].filter(Boolean).slice(0, REPORT_PHOTO_LIMIT);
  }}

  async function persistServicePhotos(storeName, item, photos) {{
    if (typeof window.machineparkPersistServicePhotos !== 'function') return photos;
    return window.machineparkPersistServicePhotos(storeName, item.id, photos);
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
        const photos = await collectServicePhotos(editor, obj.photos || []);
        obj = {{ ...obj, photos: await persistServicePhotos(storeName, obj, photos) }};
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
        if (!editor) {{ enriched.push(item); continue; }}
        const photos = await collectServicePhotos(editor, item.photos || []);
        enriched.push({{ ...item, photos: await persistServicePhotos(storeName, item, photos) }});
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
    "verslagfoto patch": PHOTO_PATCH_MARKER,
    "onderhoud verslagfoto's": "originalMaintenanceForm",
    "depannage verslagfoto's": "originalBreakdownForm",
    "foto's per toestel": "editorForRecord",
    "foto opslag": "collectServicePhotos",
    "Blob verslagfoto-opslag": "machineparkPersistServicePhotos",
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
if 'Technieker kan alleen toestelstatus en notities aanpassen.' in index:
    raise SystemExit("Buildvalidatie mislukt: oude hardcoded techniekerwrapper is nog actief")
print("[Machinepark] broncodevalidatie geslaagd")
