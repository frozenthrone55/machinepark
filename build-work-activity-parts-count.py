from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="work-activity-parts-count-v1"'

if MARKER not in index:
    helper_anchor = "  function maintenanceRow(item) {"
    helper = r'''  function workPartsCount(item) {
    const total = list => (Array.isArray(list) ? list : []).reduce((sum, part) => {
      const qty = Number(part?.qty || 0);
      return sum + (Number.isFinite(qty) && qty > 0 ? qty : 0);
    }, 0);
    return total(item?.usedParts) + total(item?.oneOffParts);
  }

'''
    if index.count(helper_anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: Werkzaamheden-onderdelenhelper anker niet uniek')
    index = index.replace(helper_anchor, helper + helper_anchor, 1)

    old_cell = '<td>${esc(usedPartsText(item.usedParts))}</td>'
    if index.count(old_cell) != 2:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 2 onderdelen-cellen in Werkzaamheden, gevonden {index.count(old_cell)}')
    index = index.replace(old_cell, '<td class="work-parts-count">${workPartsCount(item)}</td>')

    style = f'''\n<style {MARKER}>\n.work-history-table td.work-parts-count{{text-align:center;font-weight:800;white-space:nowrap;font-variant-numeric:tabular-nums}}\n</style>\n'''
    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor compact onderdelenaantal')
    index = index[:pos] + style + index[pos:]
    index_path.write_text(index, encoding='utf-8')

built = index_path.read_text(encoding='utf-8')
required = [
    MARKER,
    'function workPartsCount(item)',
    'total(item?.usedParts) + total(item?.oneOffParts)',
    'class="work-parts-count"',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: compact onderdelenaantal ontbreekt ({needle})')
if '>${esc(usedPartsText(item.usedParts))}</td>' in built:
    raise SystemExit('Buildvalidatie mislukt: onderdelenomschrijving staat nog in Werkzaamhedenhistoriek')

print('[Machinepark] Werkzaamheden toont alleen totaal aantal gebruikte onderdelen')
