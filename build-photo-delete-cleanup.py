from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="photo-delete-cleanup-v1"'

if MARKER not in index:
    script = r'''
<script data-machinepark-build-fix="photo-delete-cleanup-v1">
(() => {
  const PART_PHOTO_CLEANUP_URL = '/.netlify/functions/part-photos';
  const partPhotoDeleteRequests = new Set();

  function isStoredPartPhoto(value) {
    return String(value || '').includes('/.netlify/functions/part-photos?');
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
</script>
'''
    if '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor foto-opruiming')
    before, after = index.rsplit('</body>', 1)
    index = before + script + '</body>' + after
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'partPhotoDeleteRequests',
    "JSON.stringify({ partId, photo: '' })",
    'data-remove-part-photo',
    'Volledige foto + thumbnail worden verwijderd.',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: foto-opruiming ontbreekt ({needle})')

print('[Machinepark] verwijderde foto’s en thumbnails worden volledig opgeruimd')
