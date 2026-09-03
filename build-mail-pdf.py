from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-build-fix="mail-pdf-v1"'

if MARKER not in index:
    style = r'''
<style data-machinepark-build-fix="mail-pdf-v1">
.page-print-row{gap:8px;flex-wrap:wrap}
.page-mail-btn,.service-detail-mail-btn,.device-detail-mail-btn{display:inline-flex;align-items:center;gap:7px}
.machinepark-pdf-stage{
  position:fixed;
  left:-12000px;
  top:0;
  width:186mm;
  min-height:20mm;
  padding:0;
  margin:0;
  background:#fff;
  color:#111;
  z-index:-1;
  font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;
}
.machinepark-pdf-stage *{box-sizing:border-box}
.machinepark-pdf-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12mm;border-bottom:2px solid #173f35;padding:0 0 5mm;margin:0 0 6mm}
.machinepark-pdf-head h1{margin:0;color:#173f35;font-size:20pt;line-height:1.15}
.machinepark-pdf-head .machinepark-pdf-subtitle{margin-top:2mm;font-size:10pt;font-weight:700;color:#333}
.machinepark-pdf-date{font-size:8.5pt;color:#555;white-space:nowrap}
.machinepark-pdf-stage .page-print-row,
.machinepark-pdf-stage .toolbar,
.machinepark-pdf-stage .modal-foot,
.machinepark-pdf-stage button,
.machinepark-pdf-stage input[type="file"]{display:none!important}
.machinepark-pdf-stage .table-wrap{overflow:visible!important;max-height:none!important}
.machinepark-pdf-stage .table,
.machinepark-pdf-stage .device-table{min-width:0!important;width:100%!important}
.machinepark-pdf-stage img{max-width:100%}
@media(max-width:700px){
  .page-print-row .page-print-btn,.page-print-row .page-mail-btn{width:auto;flex:1 1 145px;justify-content:center}
}
@media print{
  .page-mail-btn,.service-detail-mail-btn,.device-detail-mail-btn{display:none!important}
}
</style>
'''

    script = r'''
<script data-machinepark-build-fix="mail-pdf-v1">
(() => {
  const HTML2PDF_SRC = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.14.0/html2pdf.bundle.min.js';
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
          scrollY: 0
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
</script>
'''

    if "</head>" not in index or "</body>" not in index:
        raise SystemExit("Buildvalidatie mislukt: HTML-afsluiters ontbreken voor Mail PDF")
    index = index.replace("</head>", style + "</head>", 1)
    index = index.replace("</body>", script + "</body>", 1)
    index_path.write_text(index, encoding="utf-8")

required = [
    MARKER,
    "✉ Mail PDF",
    "html2pdf.js/0.14.0/html2pdf.bundle.min.js",
    "navigator.share",
    "navigator.canShare",
    "new File([blob]",
    "mailto:?subject=",
    "page-print-btn",
    "service-detail-print-btn",
    "printDeviceDetails",
    "machineparkMailPdf",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: Mail PDF ontbreekt ({needle})")

print("[Machinepark] Mail PDF actief naast pagina-, onderhouds-, depannage- en toestelafdruk")
