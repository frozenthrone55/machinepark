from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
MARKER = 'data-machinepark-build-fix="all-table-columns-sortable-v1"'
STYLE_MARKER = 'data-machinepark-table-sort-style="v1"'
index = INDEX.read_text(encoding='utf-8')

# Deze eindlaag raakt geen bestaande Machinepark-functies meer aan. Ze werkt
# volledig via een capture-handler + MutationObserver, zodat ToDo, Service,
# Handleidingen en toekomstige tabellen hun eigen rendercode behouden.
if MARKER not in index:
    style = r'''
<style data-machinepark-table-sort-style="v1">
.table th.machinepark-universal-sortable{cursor:pointer;user-select:none;white-space:nowrap}
.table th.machinepark-universal-sortable:hover{background:#eef3f1;color:#3f4f49}
.machinepark-universal-sort-indicator{display:inline-block;margin-left:5px;color:#8b9893;font-size:10px;min-width:10px}
.table th.machinepark-universal-sortable.active-sort .machinepark-universal-sort-indicator{color:var(--brand);font-weight:900}
</style>
'''
    script = r'''
<script data-machinepark-build-fix="all-table-columns-sortable-v1">
(() => {
  const collator = new Intl.Collator('nl-BE', { numeric:true, sensitivity:'base' });
  let observer = null;
  let refreshQueued = false;

  function primitive(raw) {
    raw = String(raw ?? '').trim();
    if (!raw || raw === '—') return { empty:true, type:'text', value:'' };
    const dateTime = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?/);
    if (dateTime) {
      const [,d,m,y,h='0',mi='0'] = dateTime;
      return { empty:false, type:'number', value:Number(`${y}${m.padStart(2,'0')}${d.padStart(2,'0')}${h.padStart(2,'0')}${mi.padStart(2,'0')}`) };
    }
    const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2}))?/);
    if (iso) {
      const [,y,m,d,h='0',mi='0'] = iso;
      return { empty:false, type:'number', value:Number(`${y}${m}${d}${h}${mi}`) };
    }
    const cleaned = raw.replace(/\s*\/\s*min.*$/i,'').replace(/[€\s]/g,'').replace(/\./g,'').replace(',','.');
    if (/^-?\d+(?:\.\d+)?$/.test(cleaned)) return { empty:false, type:'number', value:Number(cleaned) };
    return { empty:false, type:'text', value:raw };
  }

  function cellValue(cell) {
    if (!cell) return { empty:true, type:'text', value:'' };
    if (cell.dataset.sortValue !== undefined && String(cell.dataset.sortValue).trim()) return primitive(cell.dataset.sortValue);
    const toggles = [...cell.querySelectorAll('input[type="checkbox"],input[type="radio"]')];
    if (toggles.length) return { empty:false, type:'number', value:toggles.filter(input => input.checked).length };
    const select = cell.querySelector('select');
    if (select) return primitive([...select.selectedOptions].map(option => option.textContent || option.value || '').join(' '));
    const field = cell.querySelector('input:not([type="hidden"]),textarea');
    if (field) return primitive(field.value);
    let raw = String(cell.textContent ?? '').trim();
    if (!raw) {
      const image = cell.querySelector('img');
      raw = String(image?.alt || image?.title || image?.getAttribute('src') || '').trim();
    }
    return primitive(raw);
  }

  function compareCells(a,b,dir) {
    const av = cellValue(a), bv = cellValue(b);
    if (av.empty !== bv.empty) return av.empty ? 1 : -1;
    let result = 0;
    if (av.type === 'number' && bv.type === 'number') result = av.value - bv.value;
    else result = collator.compare(String(av.value), String(bv.value));
    return dir === 'desc' ? -result : result;
  }

  function tables(root = document) {
    const list = [];
    if (root?.matches?.('.table')) list.push(root);
    if (root?.querySelectorAll) list.push(...root.querySelectorAll('.table'));
    return [...new Set(list)];
  }

  function enhance(root = document) {
    tables(root).forEach(table => {
      [...table.querySelectorAll('thead th')].forEach((th,index) => {
        const column = Number.isInteger(th.cellIndex) && th.cellIndex >= 0 ? th.cellIndex : index;
        th.classList.add('machinepark-universal-sortable');
        th.removeAttribute('data-device-sort');
        th.dataset.machineparkSortIndex = String(column);
        th.setAttribute('role','button');
        th.setAttribute('tabindex','0');
        const label = th.textContent.replace(/[▲▼]/g,'').trim() || `Kolom ${column + 1}`;
        th.setAttribute('aria-label', `${label} sorteren`);
        let indicator = th.querySelector('.machinepark-universal-sort-indicator');
        if (!indicator) {
          indicator = th.querySelector('.table-sort-indicator,.sort-indicator');
          if (!indicator) {
            indicator = document.createElement('span');
            th.appendChild(indicator);
          }
          indicator.classList.add('table-sort-indicator','machinepark-universal-sort-indicator');
        }
        th.title = 'Klik om deze kolom te sorteren';
      });
    });
  }

  function observe() {
    if (!observer) observer = new MutationObserver(queueRefresh);
    observer.observe(document.body, { childList:true, subtree:true });
  }

  function paused(callback) {
    if (observer) observer.disconnect();
    try { return callback(); }
    finally { if (document.body) observe(); }
  }

  function applyRows(table,index,dir) {
    if (!table || !Number.isInteger(index)) return;
    table.dataset.machineparkSortIndex = String(index);
    table.dataset.machineparkSortDir = dir;
    [...table.querySelectorAll('thead th.machinepark-universal-sortable')].forEach(th => {
      const active = Number(th.dataset.machineparkSortIndex) === index;
      th.classList.toggle('active-sort',active);
      const indicator = th.querySelector('.machinepark-universal-sort-indicator');
      if (indicator) indicator.textContent = active ? (dir === 'asc' ? '▲' : '▼') : '';
      th.setAttribute('aria-sort', active ? (dir === 'asc' ? 'ascending' : 'descending') : 'none');
      th.title = active ? `Gesorteerd ${dir === 'asc' ? 'oplopend' : 'aflopend'} — klik om om te keren` : 'Klik om deze kolom te sorteren';
    });
    [...table.tBodies].forEach(tbody => {
      const rows = [...tbody.rows];
      const fixed = rows.filter(row => !row.cells[index] || row.cells.length === 1 || [...row.cells].some(cell => cell.colSpan > 1));
      const sortable = rows.filter(row => !fixed.includes(row));
      sortable.sort((a,b) => compareCells(a.cells[index],b.cells[index],dir));
      sortable.forEach(row => tbody.appendChild(row));
      fixed.forEach(row => tbody.appendChild(row));
    });
  }

  function applyCurrent(table) {
    const index = Number(table.dataset.machineparkSortIndex);
    if (!Number.isInteger(index)) return;
    applyRows(table,index,table.dataset.machineparkSortDir || 'asc');
  }

  function refresh() {
    paused(() => {
      enhance(document);
      tables(document).forEach(applyCurrent);
    });
  }

  function queueRefresh() {
    if (refreshQueued) return;
    refreshQueued = true;
    queueMicrotask(() => {
      refreshQueued = false;
      refresh();
    });
  }

  function sortHeader(th) {
    const table = th.closest('table');
    if (!table) return;
    const index = Number(th.dataset.machineparkSortIndex);
    if (!Number.isInteger(index)) return;
    const same = table.dataset.machineparkSortIndex === String(index);
    const dir = same && table.dataset.machineparkSortDir === 'asc' ? 'desc' : 'asc';
    paused(() => {
      enhance(table);
      applyRows(table,index,dir);
    });
  }

  document.addEventListener('click', event => {
    const th = event.target.closest?.('.table th.machinepark-universal-sortable');
    if (!th) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    sortHeader(th);
  }, true);

  document.addEventListener('keydown', event => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const th = event.target.closest?.('.table th.machinepark-universal-sortable');
    if (!th) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    sortHeader(th);
  }, true);

  function start() {
    refresh();
    observe();
    window.machineparkUniversalTableSorting = { refresh, sortHeader };
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once:true });
  else start();
})();
</script>
'''
    if '</head>' not in index or '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-afsluiters ontbreken voor universele tabelsortering')
    index = index.replace('</head>', style + '</head>', 1)
    index = index.replace('</body>', script + '</body>', 1)
    INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
required = [
    MARKER,
    STYLE_MARKER,
    "root?.matches?.('.table')",
    "root.querySelectorAll('.table')",
    "th.classList.add('machinepark-universal-sortable')",
    "th.removeAttribute('data-device-sort')",
    'input[type="checkbox"],input[type="radio"]',
    "cell.querySelector('select')",
    "input:not([type=\"hidden\"]),textarea",
    "dir === 'desc' ? -result : result",
    'new MutationObserver(queueRefresh)',
    'observer.disconnect()',
    'event.stopImmediatePropagation()',
    "document.addEventListener('click'",
    'window.machineparkUniversalTableSorting',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: universele tabelsortering ontbreekt ({needle})')

start = built.find('<script ' + MARKER + '>')
end = built.find('</script>', start)
if start < 0 or end < 0:
    raise SystemExit('Buildvalidatie mislukt: los universeel sorteerscript ontbreekt')
block = built[start:end]
for forbidden in ["text==='details'", "text==='bewerk'", "classList.contains('no-sort')", '.table:not(.device-table)']:
    if forbidden in block:
        raise SystemExit(f'Buildvalidatie mislukt: universele sorteerlaag bevat nog een kolomuitzondering ({forbidden})')

print('[Machinepark] elke kolom van elke tabel sorteerbaar via losse universele eindlaag')
