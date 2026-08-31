from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="breakdown-details-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    replace_once(
        "const gb=e.target.closest('[data-global-breakdown]');if(gb){closeGlobalSearch();openBreakdown(gb.dataset.globalBreakdown);return}",
        "const gb=e.target.closest('[data-global-breakdown]');if(gb){closeGlobalSearch();if(window.machineparkShowBreakdownDetails)window.machineparkShowBreakdownDetails(gb.dataset.globalBreakdown);else openBreakdown(gb.dataset.globalBreakdown);return}",
        "depannage vanuit globale zoekresultaten",
    )
    replace_once(
        "const b=e.target.closest('[data-edit-breakdown]');if(b)openBreakdown(b.dataset.editBreakdown);",
        "const b=e.target.closest('[data-edit-breakdown]');if(b){if(window.machineparkShowBreakdownDetails)window.machineparkShowBreakdownDetails(b.dataset.editBreakdown);else openBreakdown(b.dataset.editBreakdown);}",
        "depannage-detailsknop",
    )

    feature = r'''
<style data-machinepark-build-fix="breakdown-details-v1">
.breakdown-detail-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.breakdown-detail-field{border:1px solid var(--line);border-radius:11px;background:#f9fbfa;padding:11px;min-width:0}
.breakdown-detail-field.full{grid-column:1/-1}
.breakdown-detail-field label{display:block;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-bottom:5px}
.breakdown-detail-field .value{font-size:13px;line-height:1.5;white-space:pre-wrap;overflow-wrap:anywhere}
.breakdown-detail-parts{display:grid;gap:5px}
.breakdown-detail-part{font-size:13px;line-height:1.5;padding:5px 0;border-bottom:1px solid #e7ece9;overflow-wrap:anywhere}
.breakdown-detail-part:last-child{border-bottom:0}
.breakdown-detail-photos{display:grid;grid-template-columns:repeat(auto-fill,minmax(135px,1fr));gap:10px;margin-top:4px}
.breakdown-detail-photos img{display:block;width:100%;height:135px;object-fit:cover;border:1px solid var(--line);border-radius:10px;background:#f8faf9;cursor:zoom-in}
@media(max-width:650px){.breakdown-detail-summary{grid-template-columns:1fr}.breakdown-detail-field.full{grid-column:1}.breakdown-detail-photos{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
<script data-machinepark-build-fix="breakdown-details-v1">
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
    if (window.machineparkCanEdit && typeof window.machineparkCanEdit.breakdowns !== 'undefined') return !!window.machineparkCanEdit.breakdowns;
    if (typeof window.machineparkHasPermission === 'function') return window.machineparkHasPermission('breakdowns.edit');
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
        print.textContent = '🖨 Afdrukken';
        print.onclick = () => window.printMachineparkServiceRecord('breakdowns', id);
        foot.insertBefore(print, primary || null);
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
</script>
'''

    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor depannagedetails')
    index = index[:pos] + feature + '\n' + index[pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'machineparkShowBreakdownDetails',
    'Depannagedetails',
    'editBreakdownFromDetails',
    "openBreakdown(id)",
    'Werkdagen en tijd',
    'Probleem / melding',
    'Diagnose',
    'Oplossing / uitgevoerde werken',
    'Gebruikte onderdelen',
    'breakdown-detail-parts',
    'usedPartsText([part])',
    'Foto’s bij verslag',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: depannagedetails ontbreken ({needle})')

print('[Machinepark] depannages openen eerst in detailweergave met aparte bewerkknop')
