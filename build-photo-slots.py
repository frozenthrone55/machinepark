from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-build-fix="service-report-photo-slots-v2"'

if MARKER not in index:
    style = f'''
<style {MARKER}>
.service-photo-files{{display:none!important}}
.service-photo-four-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:8px 0}}
.service-photo-slot{{border:1px solid var(--line);border-radius:12px;background:#f8faf9;padding:10px;display:grid;gap:8px;min-width:0}}
.service-photo-slot-title{{font-size:12px;font-weight:800;color:#3e4b46}}
.service-photo-slot input[type=file]{{width:100%;min-width:0;padding:8px!important;background:white}}
.service-photo-slot-preview{{min-height:30px;font-size:11px;color:var(--muted);display:grid;gap:6px}}
.service-photo-slot-preview img{{width:100%;height:110px;object-fit:cover;border-radius:9px;border:1px solid var(--line);background:white}}
@media(max-width:700px){{
  .service-photo-four-grid{{grid-template-columns:1fr}}
  .service-photo-slot-preview img{{height:150px}}
}}
</style>
'''

    script = f'''
<script {MARKER}>
(() => {{
  const REPORT_PHOTO_LIMIT = 4;

  function photoArray(value) {{
    return Array.isArray(value)
      ? value.filter(x => typeof x === 'string' && x.startsWith('data:image/')).slice(0, REPORT_PHOTO_LIMIT)
      : [];
  }}

  function updateSelectedCount(editor) {{
    if (!editor) return;
    const count = [...editor.querySelectorAll('.service-photo-slot-file')]
      .filter(input => input.files?.[0]?.size).length;
    const info = editor.querySelector('.service-photo-selected');
    if (info) info.textContent = count ? `${{count}} nieuwe foto${{count === 1 ? '' : '’s'}} geselecteerd` : '';
  }}

  function expandServicePhotoEditor(editor) {{
    if (!editor || editor.dataset.fourPhotoSlots === '1') return;
    const original = editor.querySelector('.service-photo-files');
    if (!original) return;

    original.style.display = 'none';
    original.tabIndex = -1;
    original.setAttribute('aria-hidden', 'true');

    const hasExisting = editor.querySelectorAll('.service-photo-item').length > 0;
    const grid = document.createElement('div');
    grid.className = 'service-photo-four-grid';
    for (let i = 1; i <= REPORT_PHOTO_LIMIT; i += 1) {{
      const slot = document.createElement('div');
      slot.className = 'service-photo-slot';
      slot.innerHTML = `
        <div class="service-photo-slot-title">${{hasExisting ? 'Nieuwe foto' : 'Foto'}} ${{i}}</div>
        <input type="file" accept="image/*" class="service-photo-slot-file" ${{original.disabled ? 'disabled' : ''}}>
        <div class="service-photo-slot-preview">Nog geen foto gekozen</div>`;
      grid.appendChild(slot);
    }}
    original.insertAdjacentElement('beforebegin', grid);

    const hint = [...editor.querySelectorAll('.muted')]
      .find(el => el.textContent.includes('Maximaal') && el.textContent.includes('foto'));
    if (hint) hint.textContent = 'Kies maximaal één foto per vak. In totaal blijven maximaal 4 foto’s per verslag mogelijk.';

    editor.dataset.fourPhotoSlots = '1';
    updateSelectedCount(editor);
  }}

  function expandAll(root = document) {{
    root.querySelectorAll?.('.service-photo-editor').forEach(expandServicePhotoEditor);
  }}

  async function collectFourSlotPhotos(editor, existing = []) {{
    if (!editor) return photoArray(existing);
    const remove = new Set(
      [...editor.querySelectorAll('.service-photo-remove:checked')].map(x => Number(x.value))
    );
    const kept = photoArray(existing).filter((_, i) => !remove.has(i));
    const files = [...editor.querySelectorAll('.service-photo-slot-file')]
      .map(input => input.files?.[0])
      .filter(file => file && file.size);

    if (kept.length + files.length > REPORT_PHOTO_LIMIT) {{
      throw new Error(`Er kunnen maximaal ${{REPORT_PHOTO_LIMIT}} foto’s bij dit verslag staan. Verwijder eerst een bestaande foto of kies minder nieuwe foto’s.`);
    }}

    const added = [];
    for (const file of files) added.push(await compressImage(file));
    return [...kept, ...added].filter(Boolean).slice(0, REPORT_PHOTO_LIMIT);
  }}

  function batchEditor(storeName, deviceId) {{
    const attr = storeName === 'maintenance' ? 'maintenanceDevice' : 'breakdownDevice';
    return [...document.querySelectorAll('.maintenance-machine-card')]
      .find(card => card.dataset?.[attr] === deviceId)
      ?.querySelector('.service-photo-editor') || null;
  }}

  async function withoutV1Editors(callback) {{
    const editors = [...document.querySelectorAll('.service-photo-editor')];
    editors.forEach(editor => editor.classList.remove('service-photo-editor'));
    try {{
      return await callback();
    }} finally {{
      editors.forEach(editor => editor.classList.add('service-photo-editor'));
    }}
  }}

  const v1Put = put;
  put = async function(storeName, obj) {{
    if ((storeName === 'maintenance' || storeName === 'breakdowns') && obj) {{
      expandAll(document);
      const editor = document.querySelector('#modalForm .modal-body > .form-grid > .service-photo-editor');
      if (editor && !editor.closest('.maintenance-machine-card')) {{
        obj = {{ ...obj, photos: await collectFourSlotPhotos(editor, obj.photos || []) }};
        return withoutV1Editors(() => v1Put(storeName, obj));
      }}
    }}
    return v1Put(storeName, obj);
  }};

  const v1PutMany = putMany;
  putMany = async function(storeName, items) {{
    if ((storeName === 'maintenance' || storeName === 'breakdowns') && Array.isArray(items) && items.length) {{
      expandAll(document);
      const enriched = [];
      for (const item of items) {{
        const editor = batchEditor(storeName, item.deviceId);
        enriched.push(editor ? {{ ...item, photos: await collectFourSlotPhotos(editor, []) }} : item);
      }}
      return withoutV1Editors(() => v1PutMany(storeName, enriched));
    }}
    return v1PutMany(storeName, items);
  }};

  const v1SetMaintenanceMachineEnabled = setMaintenanceMachineEnabled;
  setMaintenanceMachineEnabled = function(card, enabled) {{
    v1SetMaintenanceMachineEnabled(card, enabled);
    expandAll(card || document);
    card?.querySelectorAll('.service-photo-slot-file').forEach(input => input.disabled = !enabled);
  }};

  const v1SetBreakdownMachineEnabled = setBreakdownMachineEnabled;
  setBreakdownMachineEnabled = function(card, enabled) {{
    v1SetBreakdownMachineEnabled(card, enabled);
    expandAll(card || document);
    card?.querySelectorAll('.service-photo-slot-file').forEach(input => input.disabled = !enabled);
  }};

  const v1ShowModal = showModal;
  showModal = function(...args) {{
    const result = v1ShowModal(...args);
    expandAll(document.querySelector('#modal') || document);
    return result;
  }};

  document.addEventListener('change', event => {{
    const input = event.target.closest?.('.service-photo-slot-file');
    if (!input) return;
    const editor = input.closest('.service-photo-editor');
    const preview = input.closest('.service-photo-slot')?.querySelector('.service-photo-slot-preview');
    if (preview) {{
      const oldUrl = preview.dataset.objectUrl;
      if (oldUrl) URL.revokeObjectURL(oldUrl);
      const file = input.files?.[0];
      if (file) {{
        const url = URL.createObjectURL(file);
        preview.dataset.objectUrl = url;
        preview.innerHTML = `<img src="${{url}}" alt="Geselecteerde verslagfoto"><span>${{esc(file.name || 'Foto geselecteerd')}}</span>`;
      }} else {{
        preview.textContent = 'Nog geen foto gekozen';
        delete preview.dataset.objectUrl;
      }}
    }}
    updateSelectedCount(editor);
  }});

  const modal = document.querySelector('#modal');
  if (modal) {{
    new MutationObserver(() => expandAll(modal)).observe(modal, {{ childList: true, subtree: true }});
  }}
  expandAll(document);
}})();
</script>
'''

    if "</head>" not in index or "</body>" not in index:
        raise SystemExit("Buildvalidatie mislukt: HTML-afsluiters ontbreken voor vier fotovakken")
    index = index.replace("</head>", style + "</head>", 1)
    index = index.replace("</body>", script + "</body>", 1)
    index_path.write_text(index, encoding="utf-8")

if MARKER not in index:
    raise SystemExit("Buildvalidatie mislukt: vier aparte fotovakken ontbreken")
if "service-photo-slot-file" not in index or "Foto'}} ${{i}}" not in index:
    raise SystemExit("Buildvalidatie mislukt: fotovakken zijn onvolledig")

print("[Machinepark] vier aparte fotovakken actief")
