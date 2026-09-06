from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SERVICE = ROOT / "service-visits.js"
index = INDEX.read_text(encoding="utf-8")
service = SERVICE.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="decimal-part-usage-v1"'
SERVICE_MARKER = 'machinepark-decimal-part-usage-v1'


def replace_exact(text, old, new, label, expected=1):
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"Decimale onderdelen: verwacht {expected}x {label}, gevonden {count}x")
    return text.replace(old, new)


if MARKER not in index:
    old = "function usedPartsText(items=[]){if(!items.length)return '—';return items.map(i=>`${partName(i.partId)} × ${i.qty}`).join(', ')}"
    new = """function normalizePartQuantity(value,fallback=0){const raw=typeof value==='string'?value.replace(',','.'):value,n=Number(raw);if(!Number.isFinite(n))return fallback;return Math.round(n*1000)/1000}
function formatPartQuantity(value){return normalizePartQuantity(value,0).toLocaleString('nl-BE',{minimumFractionDigits:0,maximumFractionDigits:3})}
function usedPartsText(items=[]){if(!items.length)return '—';return items.map(i=>`${partName(i.partId)} × ${formatPartQuantity(i.qty)}`).join(', ')}"""
    index = replace_exact(index, old, new, "hoeveelheidhelper")

    index = replace_exact(
        index,
        '<input class="usage-qty" type="number" min="1" step="1" value="${u.qty||1}">',
        '<input class="usage-qty" type="number" min="0.001" step="0.001" inputmode="decimal" value="${normalizePartQuantity(u.qty,1)}">',
        "voorraadonderdeel hoeveelheid",
    )

    index = index.replace(
        "qty:Number(r.querySelector('.usage-qty').value||1)",
        "qty:normalizePartQuantity(r.querySelector('.usage-qty').value,1)",
    )
    index = index.replace(
        "qty:Number(row.querySelector('.usage-qty')?.value||1)",
        "qty:normalizePartQuantity(row.querySelector('.usage-qty')?.value,1)",
    )

    for old, new in {
        "stock:Number(p.stock||0)-q": "stock:normalizePartQuantity(Number(p.stock||0)-q)",
        "stock:Number(p.stock||0)-qty": "stock:normalizePartQuantity(Number(p.stock||0)-qty)",
        "stock:Number(part.stock||0)+qty": "stock:normalizePartQuantity(Number(part.stock||0)+qty)",
        "stock:Number(part.stock || 0) - qty": "stock:normalizePartQuantity(Number(part.stock || 0)-qty)",
        "stock:Number(part.stock || 0) + qty": "stock:normalizePartQuantity(Number(part.stock || 0)+qty)",
        "stock:Number(part.stock||0)+Number(qty||0)": "stock:normalizePartQuantity(Number(part.stock||0)+Number(qty||0))",
    }.items():
        index = index.replace(old, new)

    for old, new in {
        "qty: Math.max(1, Math.min(999999, Math.round(Number(item?.qty) || 1))),":
            "qty: Math.max(0.001, Math.min(999999, normalizePartQuantity(item?.qty, 1))),",
        "qty:Math.max(1, Math.round(Number(part?.qty) || 1)),":
            "qty:Math.max(0.001, normalizePartQuantity(part?.qty,1)),",
        "qty:Math.max(1,Math.round(Number(part?.qty)||1)),":
            "qty:Math.max(0.001,normalizePartQuantity(part?.qty,1)),",
        "const qty = Math.max(1, Math.round(Number(item?.qty) || 1));":
            "const qty = Math.max(0.001, normalizePartQuantity(item?.qty, 1));",
        "const qty = Math.max(1, Math.round(Number(item.qty) || 1));":
            "const qty = Math.max(0.001, normalizePartQuantity(item.qty, 1));",
    }.items():
        index = index.replace(old, new)

    index = index.replace(
        'class="service-oneoff-qty" type="number" min="1" step="1" inputmode="numeric"',
        'class="service-oneoff-qty" type="number" min="0.001" step="0.001" inputmode="decimal"',
    )

    index = index.replace('return `${item.qty} × ${text}`;', 'return `${formatPartQuantity(item.qty)} × ${text}`;')
    index = index.replace("return text ? `${qty} x ${text}` : '';", "return text ? `${formatPartQuantity(qty)} x ${text}` : '';")
    index = index.replace('servicePrintEsc(row.qty)', 'servicePrintEsc(formatPartQuantity(row.qty))')
    index = index.replace('<td class="work-parts-count">${workPartsCount(item)}</td>', '<td class="work-parts-count">${formatPartQuantity(workPartsCount(item))}</td>')
    index = index.replace('<td class="work-parts-count">${partsCount(item)}</td>', '<td class="work-parts-count">${formatPartQuantity(partsCount(item))}</td>')
    index = index.replace('voorraad ${Number(p.stock||0)}', 'voorraad ${formatPartQuantity(p.stock)}')
    index = index.replace('(voorraad ${Number(p.stock||0)})', '(voorraad ${formatPartQuantity(p.stock)})')

    if "</head>" not in index:
        raise SystemExit("Decimale onderdelen: </head> ontbreekt")
    index = index.replace("</head>", f'<meta {MARKER}>\n</head>', 1)

if SERVICE_MARKER not in service:
    service = service.replace(
        '  function oneOffRowHtml(p={}) {',
        '  /* machinepark-decimal-part-usage-v1 */\n  function oneOffRowHtml(p={}) {',
        1,
    )
    service = replace_exact(
        service,
        '<input class="sv-oneoff-qty" type="number" min="1" step="1" value="${Math.max(1,Math.round(Number(p.qty) || 1))}">',
        '<input class="sv-oneoff-qty" type="number" min="0.001" step="0.001" inputmode="decimal" value="${Math.max(0.001,normalizePartQuantity(p.qty,1))}">',
        "service eenmalig onderdeel",
    )
    service = replace_exact(
        service,
        "qty:Math.max(1,Math.round(Number(r.querySelector('.sv-oneoff-qty')?.value)||1))",
        "qty:Math.max(0.001,normalizePartQuantity(r.querySelector('.sv-oneoff-qty')?.value,1))",
        "service eenmalig onderdeel verzamelen",
    )
    service = replace_exact(
        service,
        "qty:Number(r.querySelector('.usage-qty')?.value||1)",
        "qty:normalizePartQuantity(r.querySelector('.usage-qty')?.value,1)",
        "service voorraadonderdeel verzamelen",
    )

    service = service.replace(
        "qty=Number(u?.qty||0);if(id&&qty>0)totals[id]=(totals[id]||0)+qty;",
        "qty=normalizePartQuantity(u?.qty,0);if(id&&qty>0)totals[id]=normalizePartQuantity((totals[id]||0)+qty);",
    )
    service = service.replace(
        "qty=Number(u?.qty||0);if(id&&qty>0)totals[id]=(totals[id]||0)-qty;",
        "qty=normalizePartQuantity(u?.qty,0);if(id&&qty>0)totals[id]=normalizePartQuantity((totals[id]||0)-qty);",
    )
    service = service.replace(
        "stock:Number(p.stock||0)-qty",
        "stock:normalizePartQuantity(Number(p.stock||0)-qty)",
    )
    service = service.replace(
        "stock:Number(part.stock||0)+Number(qty||0)",
        "stock:normalizePartQuantity(Number(part.stock||0)+Number(qty||0))",
    )

INDEX.write_text(index, encoding="utf-8")
SERVICE.write_text(service, encoding="utf-8")

built_index = INDEX.read_text(encoding="utf-8")
built_service = SERVICE.read_text(encoding="utf-8")
for needle in [
    MARKER,
    "function normalizePartQuantity(value,fallback=0)",
    "function formatPartQuantity(value)",
    'class="usage-qty" type="number" min="0.001" step="0.001" inputmode="decimal"',
    'class="service-oneoff-qty" type="number" min="0.001" step="0.001" inputmode="decimal"',
    "formatPartQuantity(i.qty)",
]:
    if needle not in built_index:
        raise SystemExit(f"Decimale onderdelen ontbreken in index: {needle}")

for needle in [
    SERVICE_MARKER,
    'class="sv-oneoff-qty" type="number" min="0.001" step="0.001" inputmode="decimal"',
    "qty:normalizePartQuantity(r.querySelector('.usage-qty')?.value,1)",
    "stock:normalizePartQuantity(Number(p.stock||0)-qty)",
]:
    if needle not in built_service:
        raise SystemExit(f"Decimale onderdelen ontbreken in service: {needle}")

print("[Machinepark] decimale onderdeelaantallen actief voor onderhoud, depannage en serviceverslagen")
