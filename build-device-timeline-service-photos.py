from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="device-timeline-service-photos-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    helper = r'''function deviceTimelinePhotosHtml(photos,label='Verslagfoto'){
 const list=(Array.isArray(photos)?photos:[]).filter(src=>typeof src==='string'&&src.trim()).slice(0,5);
 if(!list.length)return '';
 return `<div class="timeline-service-photos">${list.map((src,index)=>{const preview=typeof window.machineparkThumbnailRef==='function'?window.machineparkThumbnailRef(src):src;return `<img class="timeline-service-photo" src="${esc(preview)}" data-full-src="${esc(src)}" data-photo-lightbox loading="lazy" decoding="async" alt="${esc(label)} ${index+1}" title="Klik om te vergroten">`}).join('')}</div>`
}
'''
    replace_once(
        'function deviceUnifiedTimelineHtml(d){',
        helper + 'function deviceUnifiedTimelineHtml(d){',
        'tijdlijn fotohelper',
    )

    replace_once(
        "<p>${esc(m.notes||'Geen notitie')}${m.usedParts?.length?'<br>Onderdelen: '+esc(usedPartsText(m.usedParts)):''}</p>`})});",
        "<p>${esc(m.notes||'Geen notitie')}${m.usedParts?.length?'<br>Onderdelen: '+esc(usedPartsText(m.usedParts)):''}</p>${deviceTimelinePhotosHtml(m.photos,'Onderhoudsfoto')}`})});",
        'onderhoudsfoto’s in toesteltijdlijn',
    )

    replace_once(
        "<p>${extras.join('<br>')}</p>`})});",
        "<p>${extras.join('<br>')}</p>${deviceTimelinePhotosHtml(b.photos,'Depannagefoto')}`})});",
        'depannagefoto’s in toesteltijdlijn',
    )

    # De afdruk van Machinedetails gebruikt voor tijdlijnfoto’s de volledige bron,
    # niet de kleine thumbnail die op het scherm wordt gebruikt.
    replace_once(
        "try { img.setAttribute('src', img.src); } catch (_) {}",
        "try { img.setAttribute('src', img.dataset.fullSrc || img.src); } catch (_) {}",
        'volledige tijdlijnfoto bij afdrukken',
    )

    # printDeviceDetails opent een apart document. De gewone pagina-CSS wordt daar niet
    # automatisch meegenomen, dus geef tijdlijnfoto’s expliciet dezelfde afdrukmaat en
    # 3-kolomsindeling als de toestel-/machinefoto’s in dat document.
    replace_once(
        '      .device-detail-photo .badge{position:absolute;left:2mm;bottom:2mm;background:#fff}\n      @media print{body{print-color-adjust:exact;-webkit-print-color-adjust:exact}}',
        '      .device-detail-photo .badge{position:absolute;left:2mm;bottom:2mm;background:#fff}\n      .timeline-service-photos{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:3mm;margin-top:3mm}\n      .timeline-service-photo{display:block;width:100%!important;height:48mm!important;object-fit:contain!important;background:#fff;border:1px solid #ccc;border-radius:2mm;break-inside:avoid}\n      @media print{body{print-color-adjust:exact;-webkit-print-color-adjust:exact}}',
        'tijdlijnfoto afdrukformaat gelijk aan machinefoto’s',
    )

    style = f'''
<style {MARKER}>
.timeline-service-photos{{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px}}
.timeline-service-photo{{width:64px;height:64px;display:block;object-fit:cover;border:1px solid var(--line);border-radius:11px;background:#eef2f0;cursor:zoom-in}}
.timeline-service-photo:hover{{box-shadow:0 4px 14px rgba(20,45,38,.16);transform:translateY(-1px)}}
@media(max-width:700px){{
  .timeline-service-photos{{gap:6px}}
  .timeline-service-photo{{width:64px;height:64px}}
}}
@media print{{
  .timeline-service-photos{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:3mm;margin-top:3mm}}
  .timeline-service-photo{{width:100%!important;height:48mm!important;object-fit:contain!important;background:#fff;border:1px solid #ccc;border-radius:2mm;break-inside:avoid}}
}}
</style>
'''
    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: </head> ontbreekt voor tijdlijnfoto’s')
    index = index.replace('</head>', style + '</head>', 1)
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'function deviceTimelinePhotosHtml(',
    "deviceTimelinePhotosHtml(m.photos,'Onderhoudsfoto')",
    "deviceTimelinePhotosHtml(b.photos,'Depannagefoto')",
    'class="timeline-service-photo"',
    'width:64px;height:64px',
    'grid-template-columns:repeat(3,minmax(0,1fr))',
    'height:48mm!important',
    'data-photo-lightbox',
    "img.dataset.fullSrc || img.src",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: verslagfoto in Machinedetails ontbreekt ({needle})')

print('[Machinepark] tijdlijnfoto’s scherm 64x64 px en afdruk gelijk aan machinefoto’s')
