from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-build-fix="parts-xlsx-export-v1"'

if MARKER not in index:
    script = r'''
<script data-machinepark-build-fix="parts-xlsx-export-v1">
(() => {
  const enc = new TextEncoder();

  function xlsxXmlEsc(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
  }

  function xlsxTextCell(ref, value, style = 0) {
    return `<c r="${ref}" s="${style}" t="inlineStr"><is><t xml:space="preserve">${xlsxXmlEsc(value)}</t></is></c>`;
  }

  function xlsxNumberCell(ref, value, style = 0) {
    const n = Number(value);
    return Number.isFinite(n)
      ? `<c r="${ref}" s="${style}"><v>${n}</v></c>`
      : xlsxTextCell(ref, '', style);
  }

  async function normalizePartImageForExcel(dataUrl) {
    const image = dataUrlExportImage(dataUrl);
    if (!image) return null;
    if (image.mime === 'image/jpeg' || image.mime === 'image/jpg') return { bytes: image.bytes, ext: 'jpg', mime: 'image/jpeg' };
    if (image.mime === 'image/png') return { bytes: image.bytes, ext: 'png', mime: 'image/png' };

    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        try {
          const canvas = document.createElement('canvas');
          const max = 900;
          const scale = Math.min(1, max / Math.max(img.width || 1, img.height || 1));
          canvas.width = Math.max(1, Math.round((img.width || 1) * scale));
          canvas.height = Math.max(1, Math.round((img.height || 1) * scale));
          const ctx = canvas.getContext('2d');
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          const converted = dataUrlExportImage(canvas.toDataURL('image/jpeg', 0.84));
          resolve(converted ? { bytes: converted.bytes, ext: 'jpg', mime: 'image/jpeg' } : null);
        } catch {
          resolve(null);
        }
      };
      img.onerror = () => resolve(null);
      img.src = dataUrl;
    });
  }

  function xlsxContentTypes(images) {
    const extensions = new Set(images.map(x => x.ext));
    const imageDefaults = [...extensions].map(ext => {
      const mime = ext === 'png' ? 'image/png' : 'image/jpeg';
      return `<Default Extension="${ext}" ContentType="${mime}"/>`;
    }).join('');
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
${imageDefaults}
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
<Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>
</Types>`;
  }

  function xlsxStyles() {
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/><family val="2"/></font>
    <font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/><family val="2"/></font>
  </fonts>
  <fills count="3">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF173F35"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border><left style="thin"><color rgb="FFDDE5E1"/></left><right style="thin"><color rgb="FFDDE5E1"/></right><top style="thin"><color rgb="FFDDE5E1"/></top><bottom style="thin"><color rgb="FFDDE5E1"/></bottom><diagonal/></border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="4">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"><alignment vertical="center"/></xf>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFill="1" applyFont="1"><alignment vertical="center" wrapText="1"/></xf>
    <xf numFmtId="4" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1"><alignment vertical="center"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"><alignment vertical="center" wrapText="1"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>`;
  }

  function xlsxSheet(parts) {
    const headers = ['Foto','Art nr','Omschrijving','Merk toestel','Prijs excl. BTW','Voorraad locatie 1','Code leverancier','Magazijnlocatie','Minimumvoorraad'];
    const letters = ['A','B','C','D','E','F','G','H','I'];
    const headerCells = headers.map((h, i) => xlsxTextCell(`${letters[i]}1`, h, 1)).join('');
    const rows = parts.map((p, index) => {
      const r = index + 2;
      const cells = [
        xlsxTextCell(`A${r}`, p.photo ? 'Foto' : '', 0),
        xlsxTextCell(`B${r}`, p.artNr || '', 0),
        xlsxTextCell(`C${r}`, p.description || '', 3),
        xlsxTextCell(`D${r}`, p.deviceBrand || '', 3),
        p.price === '' || p.price === null || p.price === undefined ? xlsxTextCell(`E${r}`, '', 2) : xlsxNumberCell(`E${r}`, p.price, 2),
        xlsxNumberCell(`F${r}`, Number(p.stock || 0), 0),
        xlsxTextCell(`G${r}`, p.supplierCode || '', 0),
        xlsxTextCell(`H${r}`, p.warehouse || '', 0),
        xlsxNumberCell(`I${r}`, Number(p.minStock || 0), 0),
      ].join('');
      return `<row r="${r}" ht="60" customHeight="1">${cells}</row>`;
    }).join('');
    const lastRow = Math.max(1, parts.length + 1);
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <dimension ref="A1:I${lastRow}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetFormatPr defaultRowHeight="15"/>
  <cols>
    <col min="1" max="1" width="13" customWidth="1"/>
    <col min="2" max="2" width="16" customWidth="1"/>
    <col min="3" max="3" width="38" customWidth="1"/>
    <col min="4" max="4" width="26" customWidth="1"/>
    <col min="5" max="5" width="16" customWidth="1"/>
    <col min="6" max="6" width="19" customWidth="1"/>
    <col min="7" max="7" width="20" customWidth="1"/>
    <col min="8" max="8" width="22" customWidth="1"/>
    <col min="9" max="9" width="18" customWidth="1"/>
  </cols>
  <sheetData><row r="1" ht="24" customHeight="1">${headerCells}</row>${rows}</sheetData>
  <autoFilter ref="A1:I${lastRow}"/>
  <drawing r:id="rId1"/>
</worksheet>`;
  }

  function xlsxDrawing(images) {
    const anchors = images.map((image, index) => {
      const id = index + 1;
      const row = image.partIndex + 1;
      return `<xdr:oneCellAnchor>
  <xdr:from><xdr:col>0</xdr:col><xdr:colOff>47625</xdr:colOff><xdr:row>${row}</xdr:row><xdr:rowOff>47625</xdr:rowOff></xdr:from>
  <xdr:ext cx="666750" cy="666750"/>
  <xdr:pic>
    <xdr:nvPicPr><xdr:cNvPr id="${id}" name="Onderdeel foto ${id}"/><xdr:cNvPicPr/></xdr:nvPicPr>
    <xdr:blipFill><a:blip r:embed="rId${id}"/><a:stretch><a:fillRect/></a:stretch></xdr:blipFill>
    <xdr:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="666750" cy="666750"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr>
  </xdr:pic>
  <xdr:clientData/>
</xdr:oneCellAnchor>`;
    }).join('');
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">${anchors}</xdr:wsDr>`;
  }

  function xlsxDrawingRels(images) {
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${images.map((image, index) => `<Relationship Id="rId${index + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image${index + 1}.${image.ext}"/>`).join('')}</Relationships>`;
  }

  async function exportPartsExcel() {
    const button = document.getElementById('exportPartsCsv');
    const oldText = button?.textContent || 'Excel exporteren';
    if (button) { button.disabled = true; button.textContent = 'Excel maken…'; }
    try {
      const parts = [...state.parts].sort((a, b) => String(a.artNr || '').localeCompare(String(b.artNr || ''), 'nl', { numeric: true, sensitivity: 'base' }));
      const images = [];
      for (let partIndex = 0; partIndex < parts.length; partIndex++) {
        const normalized = await normalizePartImageForExcel(parts[partIndex]?.photo);
        if (normalized) images.push({ ...normalized, partIndex });
      }

      const files = [
        { name: '[Content_Types].xml', bytes: enc.encode(xlsxContentTypes(images)) },
        { name: '_rels/.rels', bytes: enc.encode(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`) },
        { name: 'xl/workbook.xml', bytes: enc.encode(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><bookViews><workbookView/></bookViews><sheets><sheet name="Onderdelen" sheetId="1" r:id="rId1"/></sheets></workbook>`) },
        { name: 'xl/_rels/workbook.xml.rels', bytes: enc.encode(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`) },
        { name: 'xl/styles.xml', bytes: enc.encode(xlsxStyles()) },
        { name: 'xl/worksheets/sheet1.xml', bytes: enc.encode(xlsxSheet(parts)) },
        { name: 'xl/worksheets/_rels/sheet1.xml.rels', bytes: enc.encode(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing1.xml"/></Relationships>`) },
        { name: 'xl/drawings/drawing1.xml', bytes: enc.encode(xlsxDrawing(images)) },
        { name: 'xl/drawings/_rels/drawing1.xml.rels', bytes: enc.encode(xlsxDrawingRels(images)) },
      ];
      images.forEach((image, index) => files.push({ name: `xl/media/image${index + 1}.${image.ext}`, bytes: image.bytes }));

      const blob = makeStoreZip(files);
      const xlsxBlob = new Blob([blob], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      downloadBlob(`Machinepark_Onderdelen_${todayISO()}.xlsx`, xlsxBlob);
      toast(`Excel-export gemaakt · ${parts.length} onderdelen · ${images.length} foto${images.length === 1 ? '' : '’s'} ingebed`);
    } catch (error) {
      console.error('Onderdelen Excel-export', error);
      alert('Excel-export mislukt: ' + (error?.message || 'onbekende fout'));
    } finally {
      if (button) { button.disabled = false; button.textContent = 'Excel exporteren'; }
    }
  }

  window.exportPartsExcel = exportPartsExcel;
  try { exportPartsCsv = exportPartsExcel; } catch (_) {}

  function activateExcelExportButton() {
    const button = document.getElementById('exportPartsCsv');
    if (!button) return;
    button.textContent = 'Excel exporteren';
    button.title = 'Exporteer alle onderdelen en foto’s in één Excel-bestand';
    button.onclick = exportPartsExcel;
  }

  activateExcelExportButton();
  document.addEventListener('DOMContentLoaded', activateExcelExportButton, { once: true });
  setTimeout(activateExcelExportButton, 0);
  setTimeout(activateExcelExportButton, 1500);
})();
</script>
'''

    if "</body>" not in index:
        raise SystemExit("Buildvalidatie mislukt: body-afsluiter ontbreekt voor Excel-export")
    index = index.replace("</body>", script + "</body>", 1)
    index_path.write_text(index, encoding="utf-8")

required = [
    MARKER,
    "exportPartsExcel",
    "Machinepark_Onderdelen_",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xl/drawings/drawing1.xml",
    "xl/media/image",
    "Excel exporteren",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: Excel-export ontbreekt ({needle})")

print("[Machinepark] onderdelenexport als XLSX met ingebedde foto's actief")
