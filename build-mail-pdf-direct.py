from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

BASE_MARKER = 'data-machinepark-' + 'build-fix=' + '"mail-pdf-v1"'
MARKER = 'data-machinepark-build-fix="mail-pdf-direct-v4"'

if BASE_MARKER not in index:
    raise SystemExit("Buildvalidatie mislukt: basis Mail PDF ontbreekt voor directe PDF-route")

if MARKER not in index:
    feature = r'''
<script data-machinepark-build-fix="mail-pdf-direct-v4">
(() => {
  const JSPDF_SRC = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
  const MAIL_SELECTOR = '.page-mail-btn,.service-detail-mail-btn,.device-detail-mail-btn,.service-visit-mail-btn';
  const PAGE_BOTTOM = 282;
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
      .replace(/[·•]/g, '.')
      .replace(/[×✕✖]/g, 'x')
      .replace(/…/g, '...')
      .replace(/[\u2009\u202f]/g, ' ');
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
      const ready = () => window.jspdf?.jsPDF ? resolve(window.jspdf.jsPDF) : reject(new Error('PDF-bibliotheek is niet beschikbaar.'));
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
      script.addEventListener('load', () => { script.dataset.loaded = '1'; ready(); }, { once: true });
      script.addEventListener('error', failed, { once: true });
      document.head.appendChild(script);
    }), 12000, 'PDF-bibliotheek reageert niet. Probeer opnieuw.').catch((error) => {
      jsPdfPromise = null;
      throw error;
    });
    return jsPdfPromise;
  }

  function activePageTitle(view) {
    const labels = { dashboard:'Dashboard', devices:'Toestellen', maintenance:'Onderhoud', breakdowns:'Depannages', parts:'Onderdelen', faults:'Storingen', manuals:'Handleidingen', settings:'Beheer' };
    const key = String(view?.id || '').replace(/^view-/, '');
    return labels[key] || cleanText(document.getElementById('pageTitle')?.textContent) || 'Machinepark';
  }

  function getContext(button) {
    const row = button.closest('.page-print-row');
    if (row) {
      const view = button.closest('.view');
      return view ? { source:view, title:activePageTitle(view), kind:'page' } : null;
    }
    const body = document.querySelector('#modal .modal-body');
    if (!body) return null;
    if (button.matches('.service-visit-mail-btn')) {
      const recordId = button.dataset.serviceVisitMailId || '';
      return { source:body, kind:'serviceVisit', recordId, title:`Serviceverslag ${button.dataset.serviceVisitLabel || recordId}` };
    }
    const foot = button.closest('.modal-foot') || document.querySelector('#modal .modal-foot');
    const servicePrint = foot?.querySelector('.service-detail-print-btn[data-service-print-id]');
    if (servicePrint) {
      return {
        source: body,
        kind: 'service',
        serviceKind: servicePrint.dataset.servicePrintKind || 'breakdowns',
        recordId: servicePrint.dataset.servicePrintId || ''
      };
    }
    const devicePrint = foot?.querySelector('#printDeviceDetails[data-device-print-id]');
    if (devicePrint) return { source:body, kind:'device', recordId:devicePrint.dataset.devicePrintId || '' };
    const heading = cleanText(document.querySelector('#modal .modal-head h3')?.textContent) || 'Machinepark';
    return { source:body, title:heading, kind:'modal' };
  }

  function serviceDevice(record) {
    try { return deviceName(record.deviceId, recordMoment(record)) || '—'; }
    catch (_) {
      const device = state.devices.find(item => item.id === record?.deviceId);
      return [device?.assetCode, device?.brand, device?.model].filter(Boolean).join(' · ') || '—';
    }
  }

  function serviceDate(record) {
    if (!record?.date) return '—';
    const date = new Date(`${record.date}T00:00:00`);
    return Number.isNaN(date.getTime()) ? String(record.date) : date.toLocaleDateString('nl-BE');
  }

  function serviceParts(record, multiline = false) {
    const parts = Array.isArray(record?.usedParts) ? record.usedParts.filter(Boolean) : [];
    if (!parts.length) return '—';
    if (!multiline) {
      try { return usedPartsText(parts) || '—'; } catch (_) { return '—'; }
    }
    const lines = parts.map(part => {
      try { return usedPartsText([part]) || ''; } catch (_) { return ''; }
    }).map(cleanText).filter(Boolean);
    return lines.length ? lines.join('\n') : '—';
  }

  function serviceOneOffParts(record) {
    const items = Array.isArray(record?.oneOffParts) ? record.oneOffParts : [];
    const lines = items.map(item => {
      const qty = Math.max(1, Math.round(Number(item?.qty) || 1));
      const text = [
        cleanText(item?.supplier),
        cleanText(item?.supplierCode),
        cleanText(item?.description)
      ].filter(Boolean).join(' . ');
      return text ? `${qty} x ${text}` : '';
    }).filter(Boolean);
    return lines.length ? lines.join('\n') : '—';
  }

  function serviceWorkSummary(kind, record) {
    const sessions = Array.isArray(record?.workSessions) ? record.workSessions : [];
    const sessionMinutes = sessions.reduce((sum, row) => sum + Math.max(0, Math.round(Number(row?.minutes) || 0)), 0);
    if (record?.serviceVisitId) {
      const reportSessions = Array.isArray(record?.serviceReportWorkSessions) && record.serviceReportWorkSessions.length ? record.serviceReportWorkSessions : sessions;
      const reportMinutes = reportSessions.reduce((sum, row) => sum + Math.max(0, Math.round(Number(row?.minutes) || 0)), 0);
      const minutes = Math.max(0, Math.round(Number(record?.serviceReportTotalMinutes) || reportMinutes || Number(record?.hours || 0) * 60));
      const linked = [...(state.maintenance || []), ...(state.breakdowns || [])].filter(item => (item?.serviceReportId || item?.serviceVisitId) === (record?.serviceReportId || record?.serviceVisitId));
      const unique = new Set(linked.map(item => item?.deviceId).filter(Boolean)).size;
      const count = Math.max(1, unique || Math.round(Number(record?.serviceReportDeviceCount || record?.serviceVisitDeviceCount || record?.batchSize) || 1));
      return `${minutes} min / ${count} toestel${count === 1 ? '' : 'len'}`;
    }
    const minutes = sessionMinutes || Math.max(0, Math.round(Number(record?.hours || 0) * 60));
    const collection = kind === 'maintenance' ? state.maintenance : state.breakdowns;
    let count = Math.max(1, Math.round(Number(record?.batchSize) || 1));
    if (record?.batchId && Array.isArray(collection)) {
      const grouped = collection.filter(item => item?.batchId === record.batchId).length;
      if (grouped > 0) count = grouped;
    }
    return `${minutes} min / ${count} toestel${count === 1 ? '' : 'len'}`;
  }

  function servicePhotos(record) {
    return (Array.isArray(record?.photos) ? record.photos : [])
      .filter(src => typeof src === 'string' && src.trim());
  }

  function serviceModel(context) {
    const list = context.serviceKind === 'maintenance' ? state.maintenance : state.breakdowns;
    const record = list.find(item => item.id === context.recordId);
    if (!record) return null;
    const maintenance = context.serviceKind === 'maintenance';
    const title = maintenance ? 'Onderhoudsverslag' : 'Depannageverslag';
    const oneOff = serviceOneOffParts(record);
    const fields = maintenance ? [
      { label:'Datum', value:serviceDate(record) },
      { label:'Type onderhoud', value:record.type || '—' },
      { label:'Toestel', value:serviceDevice(record), full:true },
      { label:'Technieker', value:record.technician || '—' },
      { label:record?.serviceVisitId?'Servicetijd volledig verslag / toestellen':'Werkminuten / toestellen', value:serviceWorkSummary('maintenance', record) },
      { label:'Gebruikte onderdelen', value:serviceParts(record, true), full:true },
      ...(oneOff !== '—' ? [{ label:'Eenmalige onderdelen', value:oneOff, full:true }] : []),
      { label:'Uitgevoerde werkzaamheden / notitie', value:record.notes || '—', full:true },
    ] : [
      { label:'Datum', value:serviceDate(record) },
      { label:'Toestel', value:serviceDevice(record) },
      { label:'Prioriteit', value:record.priority || '—' },
      { label:'Status', value:record.status || '—' },
      { label:'Technieker', value:record.technician || '—' },
      { label:record?.serviceVisitId?'Servicetijd volledig verslag / toestellen':'Werkminuten / toestellen', value:serviceWorkSummary('breakdowns', record) },
      { label:'Probleem / melding', value:record.issue || '—', full:true },
      { label:'Diagnose', value:record.diagnosis || '—', full:true },
      { label:'Oplossing / uitgevoerde werken', value:record.solution || '—', full:true },
      { label:'Gebruikte onderdelen', value:serviceParts(record, true), full:true },
      ...(oneOff !== '—' ? [{ label:'Eenmalige onderdelen', value:oneOff, full:true }] : []),
    ];
    const photos = servicePhotos(record);
    return {
      headerTitle: `Machinepark . ${title}`,
      subtitle: serviceDevice(record),
      rightText: serviceDate(record),
      filenameTitle: title,
      fields,
      photos,
      photoTitle: 'Foto’s bij verslag',
      photoColumns: 2,
      photoMaxHeight: 105,
      timelines: []
    };
  }

  function fieldValueFromNode(node) {
    const clone = node.cloneNode(true);
    clone.querySelectorAll('label,button,img,input[type="file"],.device-photo-remove,.device-photo-overview,.manual-device-section').forEach(el => el.remove());
    const originalFields = [...node.querySelectorAll('input,textarea,select')];
    const cloneFields = [...clone.querySelectorAll('input,textarea,select')];
    cloneFields.forEach((field, index) => {
      const original = originalFields[index] || field;
      let value = original.value || '';
      if (original instanceof HTMLSelectElement) value = original.selectedOptions?.[0]?.textContent || original.value || '';
      if (original instanceof HTMLInputElement && (original.type === 'checkbox' || original.type === 'radio')) value = original.checked ? (original.value || 'Ja') : '';
      field.replaceWith(document.createTextNode(value));
    });
    return cleanText(clone.textContent) || '—';
  }

  function deviceModel(context) {
    const device = state.devices.find(item => item.id === context.recordId);
    if (!device) return null;
    const label = [device.assetCode, device.brand, device.model].filter(Boolean).join(' · ') || 'Toestel';
    const fields = [];
    const grid = context.source.querySelector('.form-grid');
    if (grid) {
      [...grid.children].filter(node => node.classList?.contains('field')).forEach((node) => {
        if (node.querySelector('.device-detail-photo-section') || node.classList.contains('manual-device-section')) return;
        const fieldLabel = cleanText(node.querySelector(':scope > label')?.textContent || node.querySelector('label')?.textContent);
        if (!fieldLabel) return;
        fields.push({ label:fieldLabel, value:fieldValueFromNode(node), full:node.classList.contains('full') });
      });
    }
    const photos = [...context.source.querySelectorAll('.device-detail-photo img')]
      .map(img => img.dataset.fullSrc || img.currentSrc || img.src)
      .filter(Boolean);
    const timelines = [...context.source.querySelectorAll('.history-group')].map(group => ({
      title: cleanText(group.querySelector('h4')?.textContent) || 'Historiek',
      items: [...group.querySelectorAll('.timeline-item')].map(item => ({
        label: cleanText(item.querySelector('.event-label')?.textContent),
        date: cleanText(item.querySelector('.date')?.textContent),
        title: cleanText(item.querySelector('strong')?.textContent),
        text: cleanText(item.querySelector('p')?.textContent)
      }))
    })).filter(group => group.items.length);
    return {
      headerTitle: 'Machinepark',
      subtitle: `Toesteldetails · ${label}`,
      rightText: `Afgedrukt ${new Date().toLocaleString('nl-BE')}`,
      filenameTitle: `Toesteldetails_${label}`,
      fields,
      photos,
      photoTitle: 'Foto’s toestel',
      photoColumns: 3,
      photoMaxHeight: 48,
      timelines
    };
  }

  function genericLines(source) {
    const copy = source.cloneNode(true);
    copy.querySelectorAll(`${MAIL_SELECTOR},.page-print-row,.toolbar,.modal-foot,button,input[type="file"],script,style,img,.device-photo-remove,.device-photo-overview`).forEach(el => el.remove());
    copy.querySelectorAll('br').forEach(el => el.replaceWith(document.createTextNode('\n')));
    copy.querySelectorAll('th,td').forEach(el => el.appendChild(document.createTextNode(' | ')));
    copy.querySelectorAll('tr,h1,h2,h3,h4,h5,p,li,label,.value,.card,.panel').forEach(el => el.appendChild(document.createTextNode('\n')));
    return String(copy.textContent || '').split(/\n+/).map(cleanText).filter(Boolean);
  }

  function addHeader(doc, model) {
    doc.setTextColor(20);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(20);
    doc.text(pdfSafeText(model.headerTitle), 15, 18);
    if (model.subtitle) {
      doc.setFontSize(10.5);
      doc.text(pdfSafeText(model.subtitle), 15, 26);
    }
    doc.setTextColor(70);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    if (model.rightText) doc.text(pdfSafeText(model.rightText), 195, 18, { align:'right' });
    doc.setDrawColor(34);
    doc.setLineWidth(.6);
    doc.line(15, 31, 195, 31);
    doc.setTextColor(20);
  }

  function newModelPage(doc, model) {
    doc.addPage();
    addHeader(doc, model);
    return 39;
  }

  function fieldMetrics(doc, field, width) {
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10.5);
    const lines = doc.splitTextToSize(pdfSafeText(field.value || '—'), width);
    return { lines, height:5 + Math.max(1, lines.length) * 4.8 + 3 };
  }

  function drawField(doc, field, x, y, width, metrics) {
    doc.setTextColor(85);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8.5);
    doc.text(pdfSafeText(field.label).toUpperCase(), x, y + 3);
    doc.setTextColor(20);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10.5);
    doc.text(metrics.lines, x, y + 8);
  }

  function addFields(doc, model, startY) {
    let y = startY;
    const fields = model.fields || [];
    const fullWidth = 180;
    const colWidth = 86;
    const gap = 8;
    for (let i = 0; i < fields.length;) {
      const first = fields[i];
      if (first.full) {
        const m = fieldMetrics(doc, first, fullWidth);
        if (y + m.height > PAGE_BOTTOM) y = newModelPage(doc, model);
        drawField(doc, first, 15, y, fullWidth, m);
        y += m.height + 3;
        i += 1;
        continue;
      }
      const second = fields[i + 1] && !fields[i + 1].full ? fields[i + 1] : null;
      const m1 = fieldMetrics(doc, first, colWidth);
      const m2 = second ? fieldMetrics(doc, second, colWidth) : { lines:[], height:0 };
      const rowHeight = Math.max(m1.height, m2.height);
      if (y + rowHeight > PAGE_BOTTOM) y = newModelPage(doc, model);
      drawField(doc, first, 15, y, colWidth, m1);
      if (second) drawField(doc, second, 15 + colWidth + gap, y, colWidth, m2);
      y += rowHeight + 3;
      i += second ? 2 : 1;
    }
    return y;
  }

  function addTimeline(doc, model, startY) {
    let y = startY;
    for (const group of model.timelines || []) {
      if (y + 12 > PAGE_BOTTOM) y = newModelPage(doc, model);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(13);
      doc.text(pdfSafeText(group.title), 15, y + 5);
      y += 10;
      for (const item of group.items) {
        const header = [item.label, item.date].filter(Boolean).join(' · ');
        const body = [item.title, item.text].filter(Boolean).join('\n');
        doc.setFontSize(9.5);
        const bodyLines = doc.splitTextToSize(pdfSafeText(body || '—'), 168);
        const height = 10 + Math.max(1, bodyLines.length) * 4.6;
        if (y + height > PAGE_BOTTOM) y = newModelPage(doc, model);
        doc.setDrawColor(190);
        doc.roundedRect(18, y, 174, height, 2.5, 2.5);
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(8);
        doc.setTextColor(85);
        if (header) doc.text(pdfSafeText(header), 22, y + 5);
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(9.5);
        doc.setTextColor(30);
        doc.text(bodyLines, 22, y + 10);
        y += height + 4;
      }
      y += 2;
    }
    return y;
  }

  async function imageData(src) {
    if (!src) return null;
    if (src.startsWith('data:image/')) return src;
    try {
      const response = await withTimeout(fetch(src, { credentials:'same-origin', cache:'force-cache' }), 6000, 'Foto laden duurt te lang.');
      if (!response.ok) return null;
      const blob = await response.blob();
      return await withTimeout(new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ''));
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      }), 4000, 'Foto verwerken duurt te lang.');
    } catch (error) {
      console.warn('[Machinepark] Foto overgeslagen in PDF', error);
      return null;
    }
  }

  async function addPhotos(doc, model, startY) {
    const photos = model.photos || [];
    if (!photos.length) return startY;
    let y = startY;
    if (y + 14 > PAGE_BOTTOM) y = newModelPage(doc, model);
    doc.setDrawColor(185);
    doc.line(15, y, 195, y);
    y += 7;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.text(pdfSafeText(model.photoTitle || 'Foto’s'), 15, y);
    y += 6;

    const columns = Math.max(1, Number(model.photoColumns || 2));
    const gap = 5;
    const boxWidth = (180 - gap * (columns - 1)) / columns;
    const maxHeight = Number(model.photoMaxHeight || 80);

    for (let index = 0; index < photos.length; index += columns) {
      const batch = photos.slice(index, index + columns);
      const dataItems = await Promise.all(batch.map(imageData));
      const row = dataItems.map((data) => {
        if (!data) return { data:null, height:35 };
        try {
          const props = doc.getImageProperties(data);
          const ratioHeight = boxWidth * (Number(props.height) / Math.max(1, Number(props.width)));
          return { data, height:Math.min(maxHeight, Math.max(25, ratioHeight)) };
        } catch (_) {
          return { data:null, height:35 };
        }
      });
      const rowHeight = Math.max(...row.map(item => item.height)) + 4;
      if (y + rowHeight > PAGE_BOTTOM) y = newModelPage(doc, model);
      row.forEach((item, col) => {
        const x = 15 + col * (boxWidth + gap);
        doc.setDrawColor(190);
        doc.rect(x, y, boxWidth, rowHeight - 2);
        if (!item.data) {
          doc.setFont('helvetica', 'normal');
          doc.setFontSize(8);
          doc.setTextColor(100);
          doc.text('Foto kon niet worden geladen', x + boxWidth / 2, y + 12, { align:'center' });
          doc.setTextColor(20);
          return;
        }
        try {
          const format = item.data.startsWith('data:image/png') ? 'PNG' : 'JPEG';
          const props = doc.getImageProperties(item.data);
          const naturalHeight = boxWidth * (Number(props.height) / Math.max(1, Number(props.width)));
          const drawHeight = Math.min(item.height, naturalHeight);
          const drawWidth = Math.min(boxWidth - 4, drawHeight * (Number(props.width) / Math.max(1, Number(props.height))));
          const actualHeight = drawWidth * (Number(props.height) / Math.max(1, Number(props.width)));
          doc.addImage(item.data, format, x + (boxWidth - drawWidth) / 2, y + 2, drawWidth, actualHeight, undefined, 'FAST');
        } catch (error) {
          console.warn('[Machinepark] Foto kon niet in PDF worden geplaatst', error);
        }
      });
      y += rowHeight + gap;
    }
    return y;
  }

  function addGenericContent(doc, model, lines) {
    let y = 39;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9.5);
    for (const raw of lines) {
      const wrapped = doc.splitTextToSize(pdfSafeText(raw), 180);
      const needed = Math.max(1, wrapped.length) * 4.8 + 1.5;
      if (y + needed > PAGE_BOTTOM) y = newModelPage(doc, model);
      doc.text(wrapped, 15, y);
      y += needed;
    }
  }

  const SERVICE_PDF = {
    green:[24,63,53],
    ink:[17,17,17],
    muted:[51,51,51],
    border:[85,85,85],
    meta:[236,236,234],
    table:[222,222,219],
    tableLight:[236,236,234],
    maintenance:[36,72,93],
    breakdowns:[107,45,45],
    otherworks:[75,60,103],
  };

  function servicePdfSetText(doc,color=SERVICE_PDF.ink){doc.setTextColor(...color);}
  function servicePdfSetDraw(doc,color=SERVICE_PDF.border){doc.setDrawColor(...color);}
  function servicePdfSetFill(doc,color=SERVICE_PDF.meta){doc.setFillColor(...color);}
  function servicePdfSafe(value){return pdfSafeText(value===undefined||value===null?'—':String(value));}

  function servicePdfFitSingleLine(doc,value,maxWidth,baseSize=8.2,minSize=5.6) {
    const text=servicePdfSafe(value),original=doc.getFontSize?.()||baseSize;
    let size=baseSize;doc.setFontSize(size);
    while(size>minSize&&doc.getTextWidth(text)>maxWidth){size=Math.max(minSize,size-.25);doc.setFontSize(size);}
    doc.setFontSize(original);
    return {text,size};
  }

  function servicePdfCodeColumnWidth(doc,codes,totalWidth,reservedWidth,baseSize=8.2,minDescriptionWidth=30) {
    const original=doc.getFontSize?.()||baseSize;doc.setFontSize(baseSize);
    const values=['ONDERDEEL',...(codes||[]).map(value=>servicePdfSafe(value||'—'))];
    const widest=Math.max(...values.map(value=>doc.getTextWidth(value)),0);
    const tenSpaces=doc.getTextWidth('          ');
    doc.setFontSize(original);
    const wanted=widest+tenSpaces+4;
    return Math.max(12,Math.min(wanted,totalWidth-reservedWidth-minDescriptionWidth));
  }

  function servicePdfSectionTitle(doc,title,y) {
    servicePdfSetText(doc,SERVICE_PDF.ink);
    doc.setFont('helvetica','bold');doc.setFontSize(10.5);
    doc.text(servicePdfSafe(title),8,y);
    servicePdfSetDraw(doc,SERVICE_PDF.border);doc.setLineWidth(.35);doc.line(8,y+2,202,y+2);
    return y+7;
  }

  function servicePdfMetaBoxes(doc,meta,y) {
    const fields=(meta||[]).slice(0,4),count=Math.max(1,fields.length),gap=2.5,width=(194-gap*(count-1))/count,height=17;
    fields.forEach((field,index)=>{
      const x=8+index*(width+gap);
      servicePdfSetFill(doc,SERVICE_PDF.meta);servicePdfSetDraw(doc,SERVICE_PDF.border);doc.setLineWidth(.35);
      doc.roundedRect(x,y,width,height,2.2,2.2,'FD');
      servicePdfSetText(doc,SERVICE_PDF.ink);doc.setFont('helvetica','bold');doc.setFontSize(6.7);
      doc.text(servicePdfSafe(field.label).toUpperCase(),x+2.3,y+4.2);
      doc.setFontSize(8.6);
      const lines=doc.splitTextToSize(servicePdfSafe(field.value),width-4.6).slice(0,2);
      doc.text(lines,x+2.3,y+9.2);
    });
    return y+height+5;
  }

  function servicePdfTable(doc,{headers=[],rows=[],widths=[],y,headerFill=SERVICE_PDF.table,rowFont=8.2,nowrapCols=[],rightCols=[]}) {
    const x=8,total=widths.reduce((sum,w)=>sum+w,0),headerH=8;
    servicePdfSetFill(doc,headerFill);servicePdfSetDraw(doc,SERVICE_PDF.border);doc.setLineWidth(.3);
    doc.rect(x,y,total,headerH,'FD');
    let cx=x;
    doc.setFont('helvetica','bold');doc.setFontSize(6.8);servicePdfSetText(doc,SERVICE_PDF.ink);
    headers.forEach((header,i)=>{const right=rightCols.includes(i);doc.text(servicePdfSafe(header).toUpperCase(),right?cx+(widths[i]||0)-2:cx+2,y+5.1,right?{align:'right'}:undefined);cx+=widths[i]||0;});
    y+=headerH;
    for(const row of rows) {
      const cells=row.map(cell=>servicePdfSafe(cell));
      doc.setFont('helvetica','normal');doc.setFontSize(rowFont);
      const wrapped=cells.map((cell,i)=>nowrapCols.includes(i)?[cell]:doc.splitTextToSize(cell,Math.max(5,(widths[i]||20)-4)));
      const rowH=Math.max(8,...wrapped.map(lines=>Math.max(1,lines.length)*3.8+3));
      servicePdfSetDraw(doc,[120,120,120]);doc.rect(x,y,total,rowH);
      let xx=x;servicePdfSetText(doc,SERVICE_PDF.ink);
      wrapped.forEach((lines,i)=>{
        const right=rightCols.includes(i);
        doc.setFont('helvetica',right?'bold':'normal');
        if(nowrapCols.includes(i)){
          const fit=servicePdfFitSingleLine(doc,lines[0],Math.max(5,(widths[i]||20)-4),rowFont);
          doc.setFontSize(fit.size);doc.text(fit.text,right?xx+(widths[i]||0)-2:xx+2,y+4.8,right?{align:'right'}:undefined);doc.setFontSize(rowFont);
        }else{
          doc.text(lines,right?xx+(widths[i]||0)-2:xx+2,y+4.8,right?{align:'right'}:undefined);
        }
        xx+=widths[i]||0;
      });
      y+=rowH;
    }
    return y;
  }

  function servicePdfSummaryPage(doc,model) {
    const layout=model.servicePrintLayout;
    servicePdfSetText(doc,SERVICE_PDF.ink);
    doc.setFont('helvetica','bold');doc.setFontSize(16);
    doc.text(servicePdfSafe(layout.title),8,13);
    doc.setFont('helvetica','normal');doc.setFontSize(8.5);
    doc.text(servicePdfSafe(layout.subtitle),8,19);
    let y=24;
    y=servicePdfMetaBoxes(doc,layout.meta,y);
    y=servicePdfSectionTitle(doc,'Werkdagen en tijd',y);
    doc.setFont('helvetica','normal');doc.setFontSize(8.3);servicePdfSetText(doc,SERVICE_PDF.ink);
    if(layout.sessions?.length){
      for(const row of layout.sessions){
        doc.text(servicePdfSafe(`${row.date} · ${row.minutes} min`),8,y);
        y+=4.5;
      }
    }else{doc.text('—',8,y);y+=4.5;}
    doc.setFont('helvetica','bold');doc.text(servicePdfSafe(`Totaal: ${layout.totalMinutes||0} min`),8,y);y+=7;

    y=servicePdfSectionTitle(doc,'Totaaloverzicht werkzaamheden',y);
    y=servicePdfTable(doc,{
      headers:['Locatie','Toestellen','Onderhoud','Depannage','Andere werken'],
      rows:(layout.locations||[]).map(row=>[row.location,row.devices,row.maintenance,row.breakdowns,row.otherWorks]),
      widths:[62,30,32,32,38],y
    })+6;

    y=servicePdfSectionTitle(doc,'Totaal gebruikte onderdelen · alle locaties',y);
    const partRows=(layout.parts?.length?layout.parts:[{code:'—',description:'Geen onderdelen gebruikt.',qty:'',devices:[]}]).map(row=>[row.code||'—',row.description||'—',row.qty,(row.devices||[]).join(', ')]);
    const qtyW=18,devicesW=76,totalPartsW=194,codeW=servicePdfCodeColumnWidth(doc,partRows.map(row=>row[0]),totalPartsW,qtyW+devicesW,8.2,34),descriptionW=totalPartsW-codeW-qtyW-devicesW;
    servicePdfTable(doc,{
      headers:['Onderdeel','Omschrijving','Aantal','Locaties / toestellen'],
      rows:partRows,
      widths:[codeW,descriptionW,qtyW,devicesW],y,nowrapCols:[0,2],rightCols:[2]
    });
  }

  function servicePdfKindColor(kind) {
    return kind==='maintenance'?SERVICE_PDF.maintenance:(kind==='otherworks'?SERVICE_PDF.otherworks:SERVICE_PDF.breakdowns);
  }

  function servicePdfWorkHeader(doc,model,page) {
    servicePdfSetText(doc,SERVICE_PDF.ink);
    doc.setFont('helvetica','bold');doc.setFontSize(6.8);doc.text('SERVICEVERSLAG',8,8);
    doc.setFontSize(8.5);doc.text(servicePdfSafe(model.servicePrintLayout.reportLabel),8,14);
    const label=servicePdfSafe(page.kindLabel),pillW=Math.max(24,doc.getTextWidth(label)+10);
    servicePdfSetFill(doc,SERVICE_PDF.green);doc.roundedRect(202-pillW,5,pillW,9,4.5,4.5,'F');
    doc.setTextColor(255,255,255);doc.setFontSize(7.5);doc.text(label,202-pillW/2,10.7,{align:'center'});
    servicePdfSetDraw(doc,SERVICE_PDF.green);doc.setLineWidth(.7);doc.line(8,19,202,19);
    servicePdfSetText(doc,SERVICE_PDF.ink);doc.setFontSize(6.8);doc.text(servicePdfSafe(`WERKZAAMHEID ${page.index}`),8,25);
    doc.setFontSize(14);doc.text(servicePdfSafe(page.device),8,33);
    return 38;
  }

  function servicePdfMeasureDetails(doc,lines,width) {
    let height=0;doc.setFont('helvetica','normal');doc.setFontSize(8.2);
    for(const raw of lines||[]) {
      const chunks=String(raw??'—').split(/\n/);
      for(const chunk of chunks){
        const wrapped=doc.splitTextToSize(servicePdfSafe(chunk||'—'),width);
        height+=Math.max(1,wrapped.length)*3.8+1;
      }
    }
    return height;
  }

  function servicePdfMeasureParts(doc,parts,width) {
    let height=14;
    if(!parts?.length)return height+8;
    const qtyW=18,codeW=servicePdfCodeColumnWidth(doc,parts.map(part=>part.code),width,qtyW,7.8,34),descW=Math.max(30,width-codeW-qtyW);
    doc.setFont('helvetica','normal');doc.setFontSize(7.8);
    for(const part of parts){
      const wrapped=doc.splitTextToSize(servicePdfSafe(part.description||'—'),descW-5);
      height+=Math.max(8,wrapped.length*3.5+(part.oneOff?5:3));
    }
    return height;
  }

  function servicePdfPartsBox(doc,page,x,y,width) {
    const parts=page.parts||[],titleH=7,headH=7,qtyW=18,codeW=servicePdfCodeColumnWidth(doc,parts.map(part=>part.code),width,qtyW,7.8,34),descW=width-codeW-qtyW;
    servicePdfSetDraw(doc,SERVICE_PDF.border);doc.setLineWidth(.35);
    servicePdfSetFill(doc,SERVICE_PDF.table);doc.roundedRect(x,y,width,titleH+headH+(parts.length?0:8),2,2,'S');
    doc.rect(x,y,width,titleH,'F');
    servicePdfSetText(doc,SERVICE_PDF.ink);doc.setFont('helvetica','bold');doc.setFontSize(6.8);
    doc.text('ONDERDELEN VOOR DEZE WERKZAAMHEID',x+2.5,y+4.7);
    y+=titleH;
    servicePdfSetFill(doc,SERVICE_PDF.tableLight);doc.rect(x,y,width,headH,'F');servicePdfSetDraw(doc,SERVICE_PDF.border);doc.rect(x,y,width,headH);
    doc.setFontSize(6.4);
    doc.text('ONDERDEEL',x+2.5,y+4.7);
    doc.text('OMSCHRIJVING',x+codeW+2.5,y+4.7);
    doc.text('AANTAL',x+width-2.5,y+4.7,{align:'right'});
    y+=headH;
    if(!parts.length){
      doc.setFont('helvetica','normal');doc.setFontSize(7.8);doc.text('Geen onderdelen gebruikt.',x+codeW+2.5,y+5);
      servicePdfSetDraw(doc,SERVICE_PDF.border);doc.rect(x,y,width,8);return y+8;
    }
    for(const part of parts){
      doc.setFont('helvetica','normal');doc.setFontSize(7.8);
      const wrapped=doc.splitTextToSize(servicePdfSafe(part.description||'—'),Math.max(12,descW-5));
      const rowH=Math.max(8,wrapped.length*3.5+(part.oneOff?5:3));
      servicePdfSetDraw(doc,[120,120,120]);doc.rect(x,y,width,rowH);
      const fit=servicePdfFitSingleLine(doc,part.code||'—',codeW-5,7.8);
      servicePdfSetText(doc,SERVICE_PDF.ink);doc.setFontSize(fit.size);doc.text(fit.text,x+2.5,y+4.5);
      doc.setFontSize(7.8);doc.setFont('helvetica','normal');doc.text(wrapped,x+codeW+2.5,y+4.5);
      doc.setFont('helvetica','bold');doc.text(servicePdfSafe(part.qty),x+width-2.5,y+4.5,{align:'right'});
      if(part.oneOff){doc.setFontSize(5.7);doc.setFont('helvetica','normal');doc.text('EENMALIG / LEVERANCIER',x+codeW+2.5,y+rowH-2);}
      y+=rowH;
    }
    return y;
  }

  async function servicePdfWorkPhotos(doc,model,page,startY) {
    if(!page.photos?.length)return;
    let y=startY+6;
    if(y>235){doc.addPage();y=servicePdfWorkHeader(doc,model,page)+4;}
    y=servicePdfSectionTitle(doc,'Foto’s bij deze werkzaamheid',y);
    const gap=5,boxW=(194-gap)/2;
    for(let index=0;index<page.photos.length;index+=2){
      if(y+65>278){doc.addPage();y=servicePdfWorkHeader(doc,model,page)+4;y=servicePdfSectionTitle(doc,'Foto’s bij deze werkzaamheid',y);}
      const batch=page.photos.slice(index,index+2),data=await Promise.all(batch.map(imageData));
      data.forEach((img,col)=>{
        const x=8+col*(boxW+gap);servicePdfSetDraw(doc,SERVICE_PDF.border);doc.rect(x,y,boxW,58);
        if(!img)return;
        try{
          const props=doc.getImageProperties(img),ratio=Math.min((boxW-4)/props.width,54/props.height),w=props.width*ratio,h=props.height*ratio;
          doc.addImage(img,img.startsWith('data:image/png')?'PNG':'JPEG',x+(boxW-w)/2,y+2+(54-h)/2,w,h,undefined,'FAST');
        }catch(_){}
      });
      y+=63;
    }
  }

  async function servicePdfWorkPage(doc,model,page) {
    doc.addPage();
    let y=servicePdfWorkHeader(doc,model,page);
    y=servicePdfMetaBoxes(doc,[
      {label:'Locatie',value:page.location},
      {label:'Servicetijd / toestellen',value:`${Math.max(0,Math.round(Number(page.serviceMinutes)||0))} min · ${Math.max(1,Math.round(Number(page.deviceCount)||1))} toestel${Math.max(1,Math.round(Number(page.deviceCount)||1))===1?'':'len'}`},
      {label:'Technieker',value:page.technician},
    ],y);

    const detailH=servicePdfMeasureDetails(doc,page.detailLines,178),partsH=servicePdfMeasureParts(doc,page.parts,184);
    const cardX=8,cardW=194,cardY=y,cardH=Math.min(215,12+detailH+5+partsH+5);
    servicePdfSetDraw(doc,SERVICE_PDF.border);doc.setLineWidth(.35);doc.roundedRect(cardX,cardY,cardW,cardH,2.5,2.5,'S');

    let cy=cardY+7;
    servicePdfSetText(doc,SERVICE_PDF.ink);doc.setFont('helvetica','bold');doc.setFontSize(8.8);doc.text(servicePdfSafe(page.device),cardX+3,cy);
    cy+=7;

    doc.setFont('helvetica','normal');doc.setFontSize(8.2);
    for(const raw of page.detailLines||[]){
      for(const chunk of String(raw??'—').split(/\n/)){
        const wrapped=doc.splitTextToSize(servicePdfSafe(chunk||'—'),178);
        servicePdfSetText(doc,SERVICE_PDF.ink);doc.text(wrapped,cardX+3,cy);
        cy+=Math.max(1,wrapped.length)*3.8+1;
      }
    }
    cy+=2;
    cy=servicePdfPartsBox(doc,page,cardX+3,cy,cardW-6);
    await servicePdfWorkPhotos(doc,model,page,Math.max(cardY+cardH,cy));
  }

  async function addServiceVisitPrintLayout(doc,model) {
    servicePdfSummaryPage(doc,model);
    for(const page of model.servicePrintLayout?.workPages||[])await servicePdfWorkPage(doc,model,page);
  }

  function addPageNumbers(doc) {
    const pages = doc.getNumberOfPages();
    for (let page = 1; page <= pages; page += 1) {
      doc.setPage(page);
      doc.setDrawColor(185);
      doc.line(15, 286, 195, 286);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(85);
      doc.text('Afgedrukt vanuit Machinepark', 15, 291);
      doc.text(`Pagina ${page} / ${pages}`, 195, 291, { align:'right' });
    }
  }

  async function createDirectPdf(context) {
    const JsPDF = await loadJsPdf();
    const doc = new JsPDF({ unit:'mm', format:'a4', orientation:'portrait', compress:true });
    let model = null;
    if (context.kind === 'service') model = serviceModel(context);
    if (context.kind === 'serviceVisit' && typeof window.machineparkServiceVisitPdfModel === 'function') model = window.machineparkServiceVisitPdfModel(context.recordId);
    if (context.kind === 'device') model = deviceModel(context);

    if (model) {
      if (!(model.fields?.length || model.timelines?.length || model.photos?.length || model.servicePrintLayout)) throw new Error('Er is geen inhoud gevonden om in de PDF te zetten.');
      if (context.kind === 'serviceVisit' && model.servicePrintLayout) {
        await addServiceVisitPrintLayout(doc, model);
      } else {
        addHeader(doc, model);
        let y = addFields(doc, model, 39);
        y = addTimeline(doc, model, y);
        await addPhotos(doc, model, y);
      }
    } else {
      const lines = genericLines(context.source);
      const useful = lines.join(' ').replace(/\s+/g, ' ').trim();
      if (useful.length < 5) throw new Error('Er is geen inhoud gevonden om in de PDF te zetten.');
      model = { headerTitle:'Machinepark', subtitle:context.title || 'Machinepark', rightText:new Date().toLocaleString('nl-BE'), filenameTitle:context.title || 'Machinepark' };
      addHeader(doc, model);
      addGenericContent(doc, model, lines);
    }

    if (!(context.kind === 'serviceVisit' && model?.servicePrintLayout)) addPageNumbers(doc);
    const blob = doc.output('blob');
    if (!(blob instanceof Blob) || blob.size < 1200) throw new Error('De PDF bevat geen geldige inhoud. Probeer opnieuw.');
    const stamp = new Date().toISOString().slice(0, 10);
    const filename = `${safeFilename(`Machinepark_${model.filenameTitle}_${stamp}`)}.pdf`;
    return new File([blob], filename, { type:'application/pdf', lastModified:Date.now() });
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
    const shareData = { files:[file], title:subject, text };
    const canShareFile = typeof navigator.share === 'function' && (typeof navigator.canShare !== 'function' || navigator.canShare(shareData));
    if (canShareFile) {
      try { await navigator.share(shareData); return; }
      catch (error) {
        if (error?.name === 'AbortError') return;
        console.warn('[Machinepark] Directe PDF-deling mislukt; desktopfallback wordt gebruikt.', error);
      }
    }
    downloadFile(file);
    const body = `${text}\n\nDe PDF is op je toestel gedownload. Voeg het bestand ${file.name} toe als bijlage.`;
    notify('PDF gedownload. Je mailprogramma wordt geopend; voeg de gedownloade PDF toe als bijlage.');
    setTimeout(() => { window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`; }, 120);
  }

  async function directMailPdf(button) {
    if (!button || button.dataset.directPdfBusy === '1') return;
    const context = getContext(button);
    if (!context) { notify('Er is geen afdrukbare inhoud gevonden.'); return; }
    const original = button.textContent;
    button.dataset.directPdfBusy = '1';
    button.disabled = true;
    button.textContent = 'PDF maken…';
    try {
      const file = await createDirectPdf(context);
      button.textContent = 'Delen…';
      await shareFile(file, context.title || context.kind);
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
    'servicePrintKind',
    'devicePrintId',
    'serviceModel(context)',
    'serviceOneOffParts(record)',
    "serviceWorkSummary('maintenance', record)",
    "serviceWorkSummary('breakdowns', record)",
    'Servicetijd volledig verslag / toestellen',
    'serviceReportTotalMinutes',
    'serviceReportDeviceCount',
    "label:'Eenmalige onderdelen'",
    'servicePhotos(record)',
    ".replace(/[·•]/g, '.')",
    ".replace(/[×✕✖]/g, 'x')",
    'deviceModel(context)',
    "photoTitle: 'Foto’s bij verslag'",
    "photoTitle: 'Foto’s toestel'",
    'photoColumns: 2',
    'photoColumns: 3',
    'addTimeline(doc, model',
    'await addPhotos(doc, model',
    'doc.addImage(',
    'withTimeout(',
    '12000',
    "doc.output('blob')",
    'blob.size < 1200',
    'event.stopImmediatePropagation()',
    'machineparkDirectMailPdf',
    'service-visit-mail-btn',
    'machineparkServiceVisitPdfModel',
    'servicePrintLayout',
    'addServiceVisitPrintLayout',
    'servicePdfSummaryPage',
    'servicePdfWorkPage',
    'ONDERDELEN VOOR DEZE WERKZAAMHEID',
    'servicePdfFitSingleLine',
    "headers:['Onderdeel','Omschrijving','Aantal','Locaties / toestellen']",
    'nowrapCols:[0,2],rightCols:[2]',
    'green:[24,63,53]',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: directe Mail PDF-route ontbreekt ({needle})')

print('[Machinepark] Mail PDF volgt afdrukopbouw met 2-koloms velden, tijdlijn en dezelfde foto’s; mobiel zonder paginacanvas')
