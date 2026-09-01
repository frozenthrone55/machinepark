from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="print-device-details-v1"'

if MARKER not in index:
    script = r'''
<script data-machinepark-build-fix="print-device-details-v1">
(() => {
  function canPrintDeviceDetails() {
    if (window.machineparkAccessReady && typeof window.machineparkHasPermission === 'function') {
      return window.machineparkHasPermission('print');
    }
    return true;
  }

  function absoluteImageSources(root) {
    root.querySelectorAll('img').forEach((img) => {
      try { img.setAttribute('src', img.src); } catch (_) {}
      img.removeAttribute('loading');
    });
  }

  async function waitForPrintImages(doc) {
    const images = [...doc.images];
    if (!images.length) return;
    await Promise.all(images.map((img) => img.complete
      ? Promise.resolve()
      : new Promise((resolve) => {
          const done = () => resolve();
          img.addEventListener('load', done, { once: true });
          img.addEventListener('error', done, { once: true });
          setTimeout(done, 2500);
        })));
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
      @media print{body{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
    </style></head><body><div class="print-head"><div><h1>Machinepark</h1><div class="subtitle">Toesteldetails · ${esc(label)}</div></div><div class="print-date">Afgedrukt ${new Date().toLocaleString('nl-BE')}</div></div><main>${clone.innerHTML}</main></body></html>`);
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
      button.textContent = '🖨 Afdrukken';
      button.onclick = () => window.printDeviceDetails(id);
      foot.insertBefore(button, foot.firstChild);
    }, 30);
  };
  window.showDeviceHistory = showDeviceHistory;
})();
</script>
'''
    if '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor toesteldetails afdrukken')
    index = index.replace('</body>', script + '</body>', 1)
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'printDeviceDetails',
    'Toesteldetails',
    '🖨 Afdrukken',
    "window.machineparkHasPermission('print')",
    'waitForPrintImages',
    '.device-detail-photo-gallery',
    '.timeline-item',
    '.manual-device-section',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: toesteldetails-afdrukfunctie ontbreekt ({needle})')

print('[Machinepark] toesteldetails individueel afdrukbaar inclusief tijdlijn en foto’s, zonder handleidingen')
