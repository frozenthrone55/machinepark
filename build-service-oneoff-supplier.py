from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="service-oneoff-supplier-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


def replace_count(old, new, expected, label):
    global index
    count = index.count(old)
    if count != expected:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht {expected}x {label}, gevonden {count}x")
    index = index.replace(old, new)


if MARKER not in index:
    replace_once(
        '.service-oneoff-head,.service-oneoff-row{display:grid;grid-template-columns:minmax(135px,180px) minmax(200px,1fr) 90px 42px;gap:8px;align-items:center}',
        '.service-oneoff-head,.service-oneoff-row{display:grid;grid-template-columns:minmax(130px,170px) minmax(130px,170px) minmax(180px,1fr) 90px 42px;gap:8px;align-items:center}',
        'kolommen eenmalige onderdelen',
    )
    replace_once(
        '.service-oneoff-code,.service-oneoff-description{grid-column:1}',
        '.service-oneoff-supplier,.service-oneoff-code,.service-oneoff-description{grid-column:1}',
        'mobiele tekstvelden eenmalige onderdelen',
    )
    replace_once(
        '.service-oneoff-qty{grid-column:2;grid-row:1/3}',
        '.service-oneoff-qty{grid-column:2;grid-row:1/4}',
        'mobiele aantalpositie',
    )
    replace_once(
        '.service-oneoff-remove{grid-column:3;grid-row:1/3}',
        '.service-oneoff-remove{grid-column:3;grid-row:1/4}',
        'mobiele verwijderpositie',
    )

    replace_once(
        "return (Array.isArray(items) ? items : []).map(item => ({\n      supplierCode: String(item?.supplierCode || '').trim().slice(0, 120),",
        "return (Array.isArray(items) ? items : []).map(item => ({\n      supplier: String(item?.supplier || '').trim().slice(0, 120),\n      supplierCode: String(item?.supplierCode || '').trim().slice(0, 120),",
        'leverancier normaliseren',
    )
    replace_once(
        '})).filter(item => item.supplierCode || item.description).slice(0, LIMIT);',
        '})).filter(item => item.supplier || item.supplierCode || item.description).slice(0, LIMIT);',
        'lege eenmalige onderdelen filteren',
    )
    replace_once(
        "const text = [item.supplierCode, item.description].filter(Boolean).join(' · ');",
        "const text = [item.supplier, item.supplierCode, item.description].filter(Boolean).join(' · ');",
        'leverancier in details en afdruk',
    )
    replace_once(
        "const normalized = normalize([item])[0] || { supplierCode:'', description:'', qty:1 };",
        "const normalized = normalize([item])[0] || { supplier:'', supplierCode:'', description:'', qty:1 };",
        'lege invoerregel met leverancier',
    )
    replace_once(
        'return `<div class="service-oneoff-row"><input class="service-oneoff-code"',
        'return `<div class="service-oneoff-row"><input class="service-oneoff-supplier" type="text" maxlength="120" placeholder="Leverancier" value="${escAttr(normalized.supplier)}"${off}><input class="service-oneoff-code"',
        'leveranciersveld in invoerregel',
    )
    replace_once(
        '<div class="service-oneoff-head"><span>Leveranciercode</span><span>Omschrijving</span><span>Aantal</span><span></span></div>',
        '<div class="service-oneoff-head"><span>Leverancier</span><span>Leveranciercode</span><span>Omschrijving</span><span>Aantal</span><span></span></div>',
        'kolomkop leverancier',
    )
    replace_once(
        "return normalize([...root.querySelectorAll('.service-oneoff-row')].map(row => ({\n      supplierCode: row.querySelector('.service-oneoff-code')?.value || '',",
        "return normalize([...root.querySelectorAll('.service-oneoff-row')].map(row => ({\n      supplier: row.querySelector('.service-oneoff-supplier')?.value || '',\n      supplierCode: row.querySelector('.service-oneoff-code')?.value || '',",
        'leverancier verzamelen',
    )
    replace_count(
        ".service-oneoff-code,.service-oneoff-description,.service-oneoff-qty,.service-oneoff-add,.service-oneoff-remove",
        ".service-oneoff-supplier,.service-oneoff-code,.service-oneoff-description,.service-oneoff-qty,.service-oneoff-add,.service-oneoff-remove",
        2,
        'leveranciersveld activeren per machine',
    )
    replace_once(
        "list.lastElementChild?.querySelector('.service-oneoff-code')?.focus();",
        "list.lastElementChild?.querySelector('.service-oneoff-supplier')?.focus();",
        'focus nieuw eenmalig onderdeel',
    )
    replace_once(
        "row.querySelector('.service-oneoff-code').value = '';\n      row.querySelector('.service-oneoff-description').value = '';",
        "row.querySelector('.service-oneoff-supplier').value = '';\n      row.querySelector('.service-oneoff-code').value = '';\n      row.querySelector('.service-oneoff-description').value = '';",
        'leverancier wissen bij lege laatste regel',
    )

    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor leveranciersveld')
    index = index[:pos] + f'<span {MARKER} hidden></span>\n' + index[pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'service-oneoff-supplier',
    '<span>Leverancier</span><span>Leveranciercode</span>',
    "supplier: String(item?.supplier || '').trim().slice(0, 120)",
    "supplier: row.querySelector('.service-oneoff-supplier')?.value || ''",
    '[item.supplier, item.supplierCode, item.description]',
    'placeholder="Leverancier"',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: leverancier bij eenmalig onderdeel ontbreekt ({needle})')

print('[Machinepark] leverancier toegevoegd vóór leveranciercode bij eenmalige onderdelen')
