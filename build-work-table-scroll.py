from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
MARKER = 'data-machinepark-build-fix="work-table-scroll-v1"'

index = INDEX.read_text(encoding='utf-8')

required_source = [
    'id=\"serviceVisitPanel\"',
    'work-overview-table-wrap',
    'id=\"workHistoryBody\"',
]
for needle in required_source:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: Werkzaamheden-tabel ontbreekt voor scrollfix ({needle})')

if MARKER not in index:
    style = r'''
<style data-machinepark-build-fix="work-table-scroll-v1">
/* Alleen de twee grote tabellen op Werkzaamheden krijgen een eigen scrollgebied. */
#view-work #serviceVisitPanel > .table-wrap,
#view-work .work-overview-panel .work-overview-table-wrap{
  max-height:clamp(320px,52vh,560px);
  overflow:auto;
  overscroll-behavior:contain;
  scrollbar-gutter:stable;
  -webkit-overflow-scrolling:touch;
}
#view-work #serviceVisitPanel > .table-wrap .table th,
#view-work .work-overview-panel .work-overview-table-wrap .table th{
  position:sticky;
  top:0;
  z-index:3;
  background:#f4f7f5;
}
@media(max-width:700px){
  #view-work #serviceVisitPanel > .table-wrap,
  #view-work .work-overview-panel .work-overview-table-wrap{
    max-height:50vh;
  }
}
</style>
'''
    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: </head> ontbreekt voor Werkzaamheden-scrollfix')
    index = index.replace('</head>', style + '</head>', 1)
    INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
required = [
    MARKER,
    '#view-work #serviceVisitPanel > .table-wrap',
    '#view-work .work-overview-panel .work-overview-table-wrap',
    'max-height:clamp(320px,52vh,560px)',
    'overflow:auto',
    'scrollbar-gutter:stable',
    'position:sticky',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: Werkzaamheden-scrolltoken ontbreekt ({needle})')

print('[Machinepark] Serviceverslagen en Werkzaamhedenoverzicht hebben elk een eigen verticale scrollbar')
