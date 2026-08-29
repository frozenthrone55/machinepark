from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-build-fix="lattiz-part-photos-v2"'

if MARKER not in index:
    script = r'''
<script data-machinepark-build-fix="lattiz-part-photos-v2">
(() => {
  const LATTIZ_PHOTO_URL = '/.netlify/functions/lattiz-part-photo';

  function isLattizPart(part) {
    return /lattiz/i.test(String(part?.deviceBrand || ''));
  }

  function missingPartPhoto(part) {
    return !String(part?.photo || '').trim();
  }

  function canFillLattizPhotos() {
    const role = String(window.machineparkRole || '').toLowerCase();
    return role === 'beheerder' || role === 'gebruiker' || role === 'magazijnier';
  }

  function compressLattizDataUrl(dataUrl) {
    if (typeof dataUrl !== 'string' || !dataUrl.startsWith('data:image/')) return Promise.resolve('');
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        try {
          const max = 900;
          const scale = Math.min(1, max / Math.max(img.width || 1, img.height || 1));
          const canvas = document.createElement('canvas');
          canvas.width = Math.max(1, Math.round((img.width || 1) * scale));
          canvas.height = Math.max(1, Math.round((img.height || 1) * scale));
          const ctx = canvas.getContext('2d');
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          resolve(canvas.toDataURL('image/jpeg', 0.76));
        } catch (error) {
          console.warn('Lattiz foto comprimeren', error);
          resolve('');
        }
      };
      img.onerror = () => resolve('');
      img.src = dataUrl;
    });
  }

  async function findCoffeeFirstPhoto(part) {
    const headers = await centralHeaders(true);
    const response = await fetch(LATTIZ_PHOTO_URL, {
      method: 'POST',
      headers,
      cache: 'no-store',
      body: JSON.stringify({
        supplierCode: String(part.supplierCode || '').trim(),
        deviceBrand: part.deviceBrand || '',
        artNr: part.artNr || '',
        description: part.description || '',
      }),
    });

    let body = {};
    try { body = await response.json(); } catch (_) {}
    if (response.status === 404) return { status: 'not-found' };
    if (response.status === 409) return { status: 'ambiguous' };
    if (!response.ok) return { status: 'error', error: body?.error || `HTTP ${response.status}` };
    if (!body?.found || !body?.imageDataUrl) return { status: 'not-found' };
    const photo = await compressLattizDataUrl(body.imageDataUrl);
    if (!photo) return { status: 'error', error: 'Afbeelding kon niet worden verwerkt.' };
    return {
      status: 'found',
      photo,
      productName: body.productName || '',
      productUrl: body.productUrl || '',
      lookupMethod: body.lookupMethod || '',
      sourcePage: body.sourcePage || null,
    };
  }

  function resultLine(part, result) {
    const code = String(part.supplierCode || '').trim();
    const source = result.lookupMethod === 'technical-pdf' ? 'Coffee First techniekdocumentatie' : 'Coffee First webshop';
    const label = [part.artNr, part.description].filter(Boolean).join(' · ');
    if (result.status === 'found') return `✓ ${label}${code ? ` (${code})` : ''} — ${source}`;
    if (result.status === 'ambiguous') return `⚠ ${label}${code ? ` (${code})` : ''} — meerdere exacte resultaten`;
    if (result.status === 'not-found') return `— ${label}${code ? ` (${code})` : ''} — niet gevonden`;
    return `✕ ${label}${code ? ` (${code})` : ''} — ${result.error || 'fout'}`;
  }

  function showLattizPhotoResult(results, noCodeCount, updatedCount) {
    const missing = results.filter(x => x.result.status === 'not-found').length;
    const ambiguous = results.filter(x => x.result.status === 'ambiguous').length;
    const errors = results.filter(x => x.result.status === 'error').length;
    const docs = results.filter(x => x.result.status === 'found' && x.result.lookupMethod === 'technical-pdf').length;
    const webshop = results.filter(x => x.result.status === 'found' && x.result.lookupMethod !== 'technical-pdf').length;
    const details = results.map(x => resultLine(x.part, x.result)).join('\n');
    alert(
      `Lattiz foto-aanvulling voltooid.\n\n` +
      `Toegevoegd: ${updatedCount}\n` +
      `  via webshop: ${webshop}\n` +
      `  via techniekdocumentatie: ${docs}\n` +
      `Niet gevonden: ${missing}\n` +
      `Meerdere resultaten: ${ambiguous}\n` +
      `Zonder leverancierscode (toch op omschrijving gezocht): ${noCodeCount}\n` +
      `Fouten: ${errors}\n\n` +
      (details || 'Er waren geen Lattiz-onderdelen zonder foto.')
    );
  }

  async function fillMissingLattizPartPhotos() {
    const button = document.getElementById('fillLattizPhotos');
    if (!canFillLattizPhotos()) {
      alert('Je rol mag onderdeelgegevens niet aanpassen.');
      return;
    }

    const candidates = state.parts.filter(part => isLattizPart(part) && missingPartPhoto(part));
    const noCode = candidates.filter(part => !String(part.supplierCode || '').trim());

    if (!candidates.length) {
      toast('Alle Lattiz-onderdelen hebben al een foto');
      return;
    }

    const originalText = button?.textContent || 'Lattiz foto’s aanvullen';
    if (button) button.disabled = true;
    const results = [];

    try {
      for (let start = 0; start < candidates.length; start += 2) {
        const batch = candidates.slice(start, start + 2);
        if (button) button.textContent = `Foto’s zoeken ${start + 1}-${Math.min(start + batch.length, candidates.length)}/${candidates.length}…`;
        const batchResults = await Promise.all(batch.map(async part => {
          try {
            return { part, result: await findCoffeeFirstPhoto(part) };
          } catch (error) {
            return { part, result: { status: 'error', error: error?.message || 'Onbekende fout' } };
          }
        }));
        results.push(...batchResults);
      }

      const updates = [];
      for (const item of results) {
        if (item.result.status !== 'found') continue;
        const current = state.parts.find(p => p.id === item.part.id);
        if (!current || !missingPartPhoto(current) || !isLattizPart(current)) continue;
        updates.push({ ...current, photo: item.result.photo, updatedAt: new Date().toISOString() });
      }

      if (updates.length) {
        if (button) button.textContent = `Foto’s opslaan ${updates.length}…`;
        await putMany('parts', updates);
        await refresh();
        if (typeof centralPush === 'function') await centralPush();
      }

      showLattizPhotoResult(results, noCode.length, updates.length);
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = originalText;
      }
    }
  }

  function ensureLattizPhotoButton() {
    const exportButton = document.getElementById('exportPartsCsv');
    const toolbar = exportButton?.closest('.toolbar-right');
    if (!toolbar) return;
    let button = document.getElementById('fillLattizPhotos');
    if (!button) {
      button = document.createElement('button');
      button.type = 'button';
      button.id = 'fillLattizPhotos';
      button.className = 'btn';
      button.textContent = 'Lattiz foto’s aanvullen';
      button.title = 'Zoek ontbrekende Lattiz-foto’s via Coffee First webshop en officiële techniekdocumentatie';
      button.onclick = fillMissingLattizPartPhotos;
      exportButton.insertAdjacentElement('afterend', button);
    }
    button.style.display = canFillLattizPhotos() ? '' : 'none';
  }

  window.fillMissingLattizPartPhotos = fillMissingLattizPartPhotos;
  window.ensureLattizPhotoButton = ensureLattizPhotoButton;

  const previousRoleAccess = window.applyMachineparkRoleAccess;
  if (typeof previousRoleAccess === 'function') {
    window.applyMachineparkRoleAccess = function(...args) {
      const result = previousRoleAccess.apply(this, args);
      ensureLattizPhotoButton();
      return result;
    };
  }

  ensureLattizPhotoButton();
  document.addEventListener('DOMContentLoaded', ensureLattizPhotoButton, { once: true });
  setTimeout(ensureLattizPhotoButton, 500);
  setTimeout(ensureLattizPhotoButton, 1800);
})();
</script>
'''
    if "</body>" not in index:
        raise SystemExit("Buildvalidatie mislukt: body-afsluiter ontbreekt voor Lattiz-foto-aanvuller")
    index = index.replace("</body>", script + "</body>", 1)
    index_path.write_text(index, encoding="utf-8")

required = [
    MARKER,
    "fillMissingLattizPartPhotos",
    "Lattiz foto’s aanvullen",
    "/.netlify/functions/lattiz-part-photo",
    "technical-pdf",
    "putMany('parts', updates)",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: Lattiz-foto-aanvuller ontbreekt ({needle})")

print("[Machinepark] Lattiz onderdeelfoto-aanvuller via Coffee First webshop + techniekdocumentatie actief")
