from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

BASE_MARKER = 'data-machinepark-build-fix="mail-pdf-v1"'
MARKER = 'data-machinepark-build-fix="mail-pdf-direct-v2"'

if BASE_MARKER not in index:
    raise SystemExit("Buildvalidatie mislukt: basis Mail PDF ontbreekt voor directe PDF-route")

if MARKER not in index:
    feature = r'''
<script data-machinepark-build-fix="mail-pdf-direct-v2">
(() => {
  const JSPDF_SRC = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
  const MAIL_SELECTOR = '.page-mail-btn,.service-detail-mail-btn,.device-detail-mail-btn';
  let jsPdfPromise = null;

  function cleanText(value) {
    return String(value ?? '')
      .replace(/\u00a0/g, ' ')
      .replace(/[\t\r ]+/g, ' ')
      .replace(/\n\s+/g, '\n')
      .trim();
  }

  function pdfSafeText(value) {
    return cleanText(value)
      .replace(/[–—]/g, '-')
      .replace(/[‘’]/g, "'")
      .replace(/[“”]/g, '"')
      .replace(/•/g, '-');
  }

  function safeFilename(value) {
    return cleanText(value || 'Machinepark')
      .replace(/[\\/:*?"<>|]+/g, '-')
      .replace(/\s+/g, '_')
      .replace(/_+/g, '_')
      .replace(/^[_-]+|[_-]+$/g, '')
      .slice(0, 110) || 'Machinepark';
  }

  function notify(message) {
    if (typeof toast === 'function') toast(message);
    else alert(message);
  }

  function withTimeout(promise, ms, message) {
    let timer;
    const timeout = new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(message)), ms);
    });
    return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
  }

  function loadJsPdf() {
    if (window.jspdf?.jsPDF) return Promise.resolve(window.jspdf.jsPDF);
    if (jsPdfPromise) return jsPdfPromise;

    jsPdfPromise = withTimeout(new Promise((resolve, reject) => {
      let script = document.getElementById('machineparkJsPdfScript');
      const ready = () => {
        if (window.jspdf?.jsPDF) resolve(window.jspdf.jsPDF);
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
      script.id = 'machineparkJsPdfScript';
      script.src = JSPDF_SRC;
      script.async = true;
      script.crossOrigin = 'anonymous';
      script.addEventListener('load', () => {
        script.dataset.loaded = '1';
        ready();
      }, { once: true });
      script.addEventListener('error', failed, { once: true });
      document.head.appendChild(script);
    }), 12000, 'PDF-bibliotheek reageert niet. Probeer opnieuw.').catch((error) => {
      jsPdfPromise = null;
      throw error;
    });

    return jsPdfPromise;
  }

  function activePageTitle(view) {
    const labels = {
      dashboard: 'Dashboard',
      devices: 'Toestellen',
      maintenance: 'Onderhoud',
      breakdowns: 'Depannages',
      parts: 'Onderdelen',
      faults: 'Storingen',
      manuals: 'Handleidingen',
      settings: 'Beheer'
    };
    const key = String(view?.id || '').replace(/^view-/, '');
    return labels[key] || cleanText(document.getElementById('pageTitle')?.textContent) || 'Machinepark';
  }

  function modalTitle() {
    const page = cleanText(document.getElementById('pageTitle')?.textContent);
    const heading = cleanText(document.querySelector('#modal .modal-title, #modal .modal-head h1, #modal .modal-head h2, #modal .modal-head h3')?.textContent);
    if (page && heading && !heading.toLowerCase().includes(page.toLowerCase())) return `${page} · ${heading}`;
    return heading || page || 'Machinepark';
  }

  function getContext(button) {
    const row = button.closest('.page-print-row');
    if (row) {
      const view = button.closest('.view');
      if (!view) return null;
      return { source: view, title: activePageTitle(view), kind: 'page' };
    }
    const body = document.querySelector('#modal .modal-body');
    if (!body) return null;
    return { source: body, title: modalTitle(), kind: 'modal' };
  }

  function fieldValue(field) {
    if (field instanceof HTMLSelectElement) {
      return cleanText(field.selectedOptions?.[0]?.textContent || field.value);
    }
    if (field instanceof HTMLInputElement && (field.type === 'checkbox' || field.type === 'radio')) {
      return field.checked ? (cleanText(field.value) || 'Ja') : '';
    }
    return cleanText(field.value);
  }

  function labelledDetailLines(source) {
    const nodes = [...source.querySelectorAll('[class*="detail-field"]')];
    const lines = [];
    for (const node of nodes) {
      const label = cleanText(node.querySelector('label,.label,[class*="detail-label"]')?.textContent);
      if (!label) continue;
      const copy = node.cloneNode(true);
      copy.querySelectorAll('label,.label,[class*="detail-label"],button,img,input[type="file"]').forEach(el => el.remove());
      const sourceFields = [...node.querySelectorAll('input,textarea,select')];
      const copyFields = [...copy.querySelectorAll('input,textarea,select')];
      copyFields.forEach((field, index) => {
        const value = fieldValue(sourceFields[index] || field);
        field.replaceWith(document.createTextNode(value));
      });
      const value = cleanText(copy.textContent) || '—';
      lines.push(`${label}: ${value}`);
    }
    return lines;
  }

  function tableLines(source) {
    return [...source.querySelectorAll('table tr')].map((row) => {
      const cells = [...row.querySelectorAll('th,td')]
        .map(cell => cleanText(cell.textContent))
        .filter(Boolean);
      return cells.join(' | ');
    }).filter(Boolean);
  }

  function genericLines(source) {
    const copy = source.cloneNode(true);
    copy.querySelectorAll(`${MAIL_SELECTOR},.page-print-row,.toolbar,.modal-foot,button,input[type="file"],script,style,img,.device-photo-remove,.device-photo-overview`).forEach(el => el.remove());

    const sourceFields = [...source.querySelectorAll('input,textarea,select')];
    const copyFields = [...copy.querySelectorAll('input,textarea,select')];
    copyFields.forEach((field, index) => {
      const value = fieldValue(sourceFields[index] || field);
      field.replaceWith(document.createTextNode(value ? `${value}\n` : ''));
    });

    copy.querySelectorAll('br').forEach(el => el.replaceWith(document.createTextNode('\n')));
    copy.querySelectorAll('th,td').forEach(el => el.appendChild(document.createTextNode(' | ')));
    copy.querySelectorAll('tr,h1,h2,h3,h4,h5,p,li,label,.value,.card,.panel,.breakdown-detail-part').forEach(el => el.appendChild(document.createTextNode('\n')));

    return String(copy.textContent || '')
      .split(/\n+/)
      .map(cleanText)
      .filter(Boolean);
  }

  function extractLines(context) {
    if (!context?.source) return [];
    if (context.kind === 'modal') {
      const detail = labelledDetailLines(context.source);
      if (detail.length >= 2) return detail;
    }
    const table = tableLines(context.source);
    if (table.length >= 2) return table;
    return genericLines(context.source);
  }

  function addHeader(doc, title) {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(18);
    doc.text('Machinepark', 15, 18);
    doc.setFontSize(12);
    doc.text(pdfSafeText(title), 15, 26);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8.5);
    doc.text(new Date().toLocaleString('nl-BE'), 195, 18, { align: 'right' });
    doc.setDrawColor(80);
    doc.line(15, 31, 195, 31);
  }

  function addContent(doc, lines, title) {
    let y = 39;
    const maxY = 282;
    const lineHeight = 4.8;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9.5);

    for (const raw of lines) {
      const text = pdfSafeText(raw);
      if (!text) continue;
      const wrapped = doc.splitTextToSize(text, 180);
      const needed = Math.max(1, wrapped.length) * lineHeight + 1.5;
      if (y + needed > maxY) {
        doc.addPage();
        addHeader(doc, title);
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(9.5);
        y = 39;
      }
      doc.text(wrapped, 15, y);
      y += needed;
    }
  }

  function addPageNumbers(doc) {
    const pages = doc.getNumberOfPages();
    for (let page = 1; page <= pages; page += 1) {
      doc.setPage(page);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.text(`Pagina ${page} / ${pages}`, 195, 290, { align: 'right' });
    }
  }

  async function createDirectPdf(context) {
    const lines = extractLines(context);
    const useful = lines.join(' ').replace(/\s+/g, ' ').trim();
    if (useful.length < 5) throw new Error('Er is geen inhoud gevonden om in de PDF te zetten.');

    const JsPDF = await loadJsPdf();
    const doc = new JsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait', compress: true });
    addHeader(doc, context.title);
    addContent(doc, lines, context.title);
    addPageNumbers(doc);

    const blob = doc.output('blob');
    if (!(blob instanceof Blob) || blob.size < 1000) {
      throw new Error('De PDF bevat geen geldige inhoud. Probeer opnieuw.');
    }

    const stamp = new Date().toISOString().slice(0, 10);
    const filename = `${safeFilename(`Machinepark_${context.title}_${stamp}`)}.pdf`;
    return new File([blob], filename, { type: 'application/pdf', lastModified: Date.now() });
  }

  function downloadFile(file) {
    const url = URL.createObjectURL(file);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = file.name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }

  async function shareFile(file, title) {
    const subject = `Machinepark - ${title}`;
    const text = `In bijlage vind je de PDF uit Machinepark: ${title}.`;
    const shareData = { files: [file], title: subject, text };
    const canShareFile = typeof navigator.share === 'function'
      && (typeof navigator.canShare !== 'function' || navigator.canShare(shareData));

    if (canShareFile) {
      try {
        await navigator.share(shareData);
        return;
      } catch (error) {
        if (error?.name === 'AbortError') return;
        console.warn('[Machinepark] Directe PDF-deling mislukt; desktopfallback wordt gebruikt.', error);
      }
    }

    downloadFile(file);
    const body = `${text}\n\nDe PDF is op je toestel gedownload. Voeg het bestand ${file.name} toe als bijlage.`;
    notify('PDF gedownload. Je mailprogramma wordt geopend; voeg de gedownloade PDF toe als bijlage.');
    setTimeout(() => {
      window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    }, 120);
  }

  async function directMailPdf(button) {
    if (!button || button.dataset.directPdfBusy === '1') return;
    const context = getContext(button);
    if (!context) {
      notify('Er is geen afdrukbare inhoud gevonden.');
      return;
    }

    const original = button.textContent;
    button.dataset.directPdfBusy = '1';
    button.disabled = true;
    button.textContent = 'PDF maken…';
    try {
      const file = await createDirectPdf(context);
      button.textContent = 'Delen…';
      await shareFile(file, context.title);
    } catch (error) {
      console.error('[Machinepark] Directe Mail PDF mislukt', error);
      notify(error?.message || 'De PDF kon niet worden gemaakt.');
    } finally {
      button.disabled = false;
      button.dataset.directPdfBusy = '0';
      button.textContent = original;
    }
  }

  document.addEventListener('click', (event) => {
    const target = event.target instanceof Element ? event.target : event.target?.parentElement;
    const button = target?.closest?.(MAIL_SELECTOR);
    if (!button) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    void directMailPdf(button);
  }, true);

  window.machineparkDirectMailPdf = directMailPdf;
})();
</script>
'''

    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor directe Mail PDF-route')
    index = index[:pos] + feature + '\n' + index[pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'jspdf/2.5.1/jspdf.umd.min.js',
    'withTimeout(',
    '12000',
    'extractLines(context)',
    "doc.output('blob')",
    'blob.size < 1000',
    'event.stopImmediatePropagation()',
    'machineparkDirectMailPdf',
    "button.textContent = 'Delen…'",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: directe Mail PDF-route ontbreekt ({needle})')

print('[Machinepark] Mail PDF gebruikt directe jsPDF-opbouw zonder html2canvas; mobiel heeft timeout en lege-PDF-validatie')
