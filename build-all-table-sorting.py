from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
MARKER = 'data-machinepark-build-fix="all-table-columns-sortable-v1"'
index = INDEX.read_text(encoding='utf-8')

pattern = re.compile(
    r"function genericSortValue\(cell\)\{.*?function reapplyGenericTableSorts\(root=document\)\{.*?\}\nfunction partName",
    re.S,
)
replacement = r'''function genericSortValue(cell){
  if(!cell)return {empty:true,type:'text',value:''};
  if(cell.dataset.sortValue!==undefined){
    const explicit=String(cell.dataset.sortValue??'').trim();
    if(explicit)return genericSortPrimitive(explicit);
  }
  const checks=[...cell.querySelectorAll('input[type="checkbox"]')];
  if(checks.length)return {empty:false,type:'number',value:checks.filter(box=>box.checked).length};
  const select=cell.querySelector('select');
  if(select){
    const selected=[...select.selectedOptions].map(option=>option.textContent||option.value||'').join(' ').trim();
    return genericSortPrimitive(selected);
  }
  const field=cell.querySelector('input:not([type="hidden"]),textarea');
  if(field)return genericSortPrimitive(String(field.value??'').trim());
  let raw=String(cell.textContent??'').trim();
  if(!raw){
    const image=cell.querySelector('img');
    raw=String(image?.alt||image?.title||image?.getAttribute('src')||'').trim();
  }
  return genericSortPrimitive(raw);
}
function genericSortPrimitive(raw){
  raw=String(raw??'').trim();
  if(!raw||raw==='—')return {empty:true,type:'text',value:''};
  const dateTime=raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?/);
  if(dateTime){const [,d,m,y,h='0',mi='0']=dateTime;return {empty:false,type:'number',value:Number(`${y}${m.padStart(2,'0')}${d.padStart(2,'0')}${h.padStart(2,'0')}${mi.padStart(2,'0')}`)}}
  const iso=raw.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2}))?/);
  if(iso){const [,y,m,d,h='0',mi='0']=iso;return {empty:false,type:'number',value:Number(`${y}${m}${d}${h}${mi}`)}}
  const cleaned=raw.replace(/\s*\/\s*min.*$/i,'').replace(/[€\s]/g,'').replace(/\./g,'').replace(',','.');
  if(/^-?\d+(?:\.\d+)?$/.test(cleaned))return {empty:false,type:'number',value:Number(cleaned)};
  return {empty:false,type:'text',value:raw};
}
function compareGenericCells(a,b,dir){
  const av=genericSortValue(a),bv=genericSortValue(b);
  if(av.empty!==bv.empty)return av.empty?1:-1;
  let cmp=0;
  if(av.type==='number'&&bv.type==='number')cmp=av.value-bv.value;
  else cmp=tableSortCollator.compare(String(av.value),String(bv.value));
  return dir==='desc'?-cmp:cmp;
}
function allMachineparkTables(root=document){
  const tables=[];
  if(root?.matches?.('.table'))tables.push(root);
  if(root?.querySelectorAll)tables.push(...root.querySelectorAll('.table'));
  return [...new Set(tables)];
}
function enhanceSortableTables(root=document){
  allMachineparkTables(root).forEach(table=>{
    const heads=[...table.querySelectorAll('thead th')];
    heads.forEach((th,index)=>{
      const column=Number.isInteger(th.cellIndex)&&th.cellIndex>=0?th.cellIndex:index;
      th.classList.add('table-sortable');
      th.classList.remove('sortable','no-sort');
      th.removeAttribute('data-device-sort');
      th.dataset.tableSortIndex=String(column);
      let indicator=th.querySelector('.table-sort-indicator');
      if(!indicator){
        indicator=th.querySelector('.sort-indicator');
        if(indicator)indicator.className='table-sort-indicator';
      }
      if(!indicator){indicator=document.createElement('span');indicator.className='table-sort-indicator';th.appendChild(indicator)}
      const label=th.textContent.replace(/[▲▼]/g,'').trim()||`Kolom ${column+1}`;
      th.setAttribute('role','button');
      th.setAttribute('tabindex','0');
      th.setAttribute('aria-label',`${label} sorteren`);
      th.title='Klik om deze kolom te sorteren';
    });
  });
}
function applyGenericTableSort(table,idx,dir){
  if(!table)return;
  table.dataset.sortIndex=String(idx);
  table.dataset.sortDir=dir;
  [...table.querySelectorAll('thead th.table-sortable')].forEach(h=>{
    const active=Number(h.dataset.tableSortIndex)===idx;
    h.classList.toggle('active-sort',active);
    const ind=h.querySelector('.table-sort-indicator');
    if(ind)ind.textContent=active?(dir==='asc'?'▲':'▼'):'';
    h.setAttribute('aria-sort',active?(dir==='asc'?'ascending':'descending'):'none');
    if(active)h.title=`Gesorteerd ${dir==='asc'?'oplopend':'aflopend'} — klik om om te keren`;
    else h.title='Klik om deze kolom te sorteren';
  });
  [...table.tBodies].forEach(tbody=>{
    const rows=[...tbody.rows];
    const fixed=rows.filter(row=>!row.cells[idx]||row.cells.length===1||[...row.cells].some(cell=>cell.colSpan>1));
    const sortable=rows.filter(row=>!fixed.includes(row));
    sortable.sort((ra,rb)=>compareGenericCells(ra.cells[idx],rb.cells[idx],dir));
    sortable.forEach(row=>tbody.appendChild(row));
    fixed.forEach(row=>tbody.appendChild(row));
  });
}
function sortGenericTable(th){
  const table=th.closest('table');if(!table)return;
  const idx=Number(th.dataset.tableSortIndex);if(!Number.isInteger(idx))return;
  const previous=table.dataset.sortIndex===String(idx)?table.dataset.sortDir:'';
  applyGenericTableSort(table,idx,previous==='asc'?'desc':'asc');
}
function reapplyGenericTableSorts(root=document){
  allMachineparkTables(root).filter(table=>table.dataset.sortIndex!==undefined).forEach(table=>{
    const idx=Number(table.dataset.sortIndex),dir=table.dataset.sortDir||'asc';
    if(Number.isInteger(idx))applyGenericTableSort(table,idx,dir);
  });
}
function partName'''
index, count = pattern.subn(lambda _match: replacement, index, count=1)
if count != 1:
    raise SystemExit(f'Buildvalidatie mislukt: centrale tabelsortering kon niet eenduidig worden vervangen ({count}x)')

old_click = "const genericSortHead=e.target.closest('.table:not(.device-table) th.table-sortable');"
new_click = "const genericSortHead=e.target.closest('.table th.table-sortable');"
if index.count(old_click) != 1:
    raise SystemExit(f'Buildvalidatie mislukt: generieke sorteerklik verwacht 1x, gevonden {index.count(old_click)}x')
index = index.replace(old_click, new_click, 1)

# Bestaande CSS gold alleen voor niet-toesteltabellen. Trek dezelfde visuele
# feedback door naar iedere Machinepark-tabel.
index = index.replace('.table:not(.device-table) th.table-sortable{', '.table th.table-sortable{')
index = index.replace('.table:not(.device-table) th.table-sortable:hover{', '.table th.table-sortable:hover{')
index = index.replace('.table:not(.device-table) th.table-sortable.active-sort .table-sort-indicator{', '.table th.table-sortable.active-sort .table-sort-indicator{')

if MARKER not in index:
    observer = r'''
<script data-machinepark-build-fix="all-table-columns-sortable-v1">
(() => {
  let scheduled = false;
  const refreshSortableTables = () => {
    if (scheduled) return;
    scheduled = true;
    queueMicrotask(() => {
      scheduled = false;
      if (typeof enhanceSortableTables === 'function') enhanceSortableTables(document);
      if (typeof reapplyGenericTableSorts === 'function') reapplyGenericTableSorts(document);
    });
  };
  const start = () => {
    refreshSortableTables();
    if (window.machineparkSortableTableObserver) return;
    const observer = new MutationObserver(refreshSortableTables);
    observer.observe(document.body, { childList:true, subtree:true });
    window.machineparkSortableTableObserver = observer;
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once:true });
  else start();
  document.addEventListener('keydown', event => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const th = event.target.closest?.('.table th.table-sortable');
    if (!th) return;
    event.preventDefault();
    sortGenericTable(th);
  });
})();
</script>
'''
    if '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor dynamische tabelsortering')
    index = index.replace('</body>', observer + '</body>', 1)

INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
required = [
    MARKER,
    "root?.matches?.('.table')",
    "root.querySelectorAll('.table')",
    "th.classList.add('table-sortable')",
    "th.removeAttribute('data-device-sort')",
    "input[type=\"checkbox\"]",
    "cell.querySelector('select')",
    "input:not([type=\"hidden\"]),textarea",
    "const genericSortHead=e.target.closest('.table th.table-sortable');",
    'new MutationObserver(refreshSortableTables)',
    'reapplyGenericTableSorts(document)',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: volledige tabelsortering ontbreekt ({needle})')

for forbidden in [
    "root.querySelectorAll('.table:not(.device-table)')",
    "text==='details'",
    "text==='bewerk'",
    "th.classList.contains('no-sort')",
    "const genericSortHead=e.target.closest('.table:not(.device-table) th.table-sortable');",
]:
    if forbidden in built:
        raise SystemExit(f'Buildvalidatie mislukt: oude tabelsorteeruitzondering bleef actief ({forbidden})')

print('[Machinepark] elke kolom van elke tabel generiek sorteerbaar in beide richtingen')
