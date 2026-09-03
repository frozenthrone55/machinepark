from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

DIRECT_MARKER = 'data-machinepark-' + 'build-fix=' + '"mail-pdf-direct-v3"'
MARKER = 'data-machinepark-build-fix="mail-pdf-print-parity-v1"'

if DIRECT_MARKER not in index:
    raise SystemExit("Buildvalidatie mislukt: directe Mail PDF ontbreekt voor print-pariteit")

if MARKER not in index:
    old_safe = "      .replace(/•/g, '-');"
    new_safe = "      .replace(/•/g, '-')\n      .replace(/·/g, '.');"
    if index.count(old_safe) != 1:
        raise SystemExit(f"Buildvalidatie mislukt: PDF-tekennormalisatie {index.count(old_safe)}x gevonden")
    index = index.replace(old_safe, new_safe, 1)

    model_anchor = "  function serviceModel(context) {"
    helpers = r'''  function serviceOneOffParts(record) {
    const items = Array.isArray(record?.oneOffParts) ? record.oneOffParts : [];
    const lines = items.map(item => {
      const qty = Math.max(1, Math.round(Number(item?.qty) || 1));
      const text = [cleanText(item?.supplierCode), cleanText(item?.description)].filter(Boolean).join(' · ');
      return text ? `${qty} × ${text}` : '';
    }).filter(Boolean);
    return lines.length ? lines.join('\n') : '—';
  }

  function serviceBreakdownWorkSummary(record) {
    try {
      if (typeof breakdownWorkSummary === 'function') {
        const summary = cleanText(breakdownWorkSummary(record));
        if (summary) return summary;
      }
    } catch (_) {}
    const minutes = Math.max(0, Math.round(Number(record?.hours || 0) * 60));
    const count = Math.max(1, Math.round(Number(record?.batchSize || 1)));
    return `${minutes} min / ${count} toestel${count === 1 ? '' : 'len'}`;
  }

'''
    if index.count(model_anchor) != 1:
        raise SystemExit(f"Buildvalidatie mislukt: serviceModel-anker {index.count(model_anchor)}x gevonden")
    index = index.replace(model_anchor, helpers + model_anchor, 1)

    maintenance_parts = "      { label:'Gebruikte onderdelen', value:serviceParts(record), full:true },"
    maintenance_new = "      { label:'Gebruikte onderdelen', value:serviceParts(record), full:true },\n      ...(serviceOneOffParts(record) !== '—' ? [{ label:'Eenmalige onderdelen', value:serviceOneOffParts(record), full:true }] : []),"
    if index.count(maintenance_parts) != 1:
        raise SystemExit(f"Buildvalidatie mislukt: onderhoudsonderdelen in Mail PDF {index.count(maintenance_parts)}x gevonden")
    index = index.replace(maintenance_parts, maintenance_new, 1)

    breakdown_hours = "      { label:'Werkuren', value:Number(record.hours || 0) ? `${Number(record.hours)} uur` : '—' },"
    breakdown_minutes = "      { label:'Werkminuten / toestellen', value:serviceBreakdownWorkSummary(record) },"
    if index.count(breakdown_hours) != 1:
        raise SystemExit(f"Buildvalidatie mislukt: Werkuren-veld in Mail PDF {index.count(breakdown_hours)}x gevonden")
    index = index.replace(breakdown_hours, breakdown_minutes, 1)

    breakdown_parts = "      { label:'Gebruikte onderdelen', value:serviceParts(record, true), full:true },"
    breakdown_new = "      { label:'Gebruikte onderdelen', value:serviceParts(record, true), full:true },\n      ...(serviceOneOffParts(record) !== '—' ? [{ label:'Eenmalige onderdelen', value:serviceOneOffParts(record), full:true }] : []),"
    if index.count(breakdown_parts) != 1:
        raise SystemExit(f"Buildvalidatie mislukt: depannageonderdelen in Mail PDF {index.count(breakdown_parts)}x gevonden")
    index = index.replace(breakdown_parts, breakdown_new, 1)

    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor Mail PDF print-pariteit')
    index = index[:pos] + f'\n<span {MARKER} hidden></span>\n' + index[pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    ".replace(/·/g, '.')",
    'function serviceOneOffParts(record)',
    'function serviceBreakdownWorkSummary(record)',
    "label:'Werkminuten / toestellen'",
    "label:'Eenmalige onderdelen'",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: Mail PDF print-pariteit ontbreekt ({needle})')

if "label:'Werkuren'" in index[index.find(DIRECT_MARKER):]:
    raise SystemExit('Buildvalidatie mislukt: Mail PDF toont nog Werkuren in plaats van Werkminuten / toestellen')

print('[Machinepark] Mail PDF gebruikt veilige punten en volgt afdrukvelden inclusief werkminuten en eenmalige onderdelen')
