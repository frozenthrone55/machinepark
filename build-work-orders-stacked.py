from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="work-orders-stacked-v1"'

if MARKER not in index:
    style = f'''
<style {MARKER}>
/* Werkbonnen blijven overal verticaal: invullen, details, tijdlijn en afdruk. */
.workorder-maintenance-head{{display:grid;grid-template-columns:1fr;justify-items:start;align-items:start}}
.workorder-maintenance-fields,
.workorder-details-grid,
.timeline-workorder-grid,
.workorder-print-grid{{grid-template-columns:1fr!important}}
.workorder-maintenance-field.full,
.workorder-print-grid .service-print-field.full{{grid-column:1!important}}
@media print{{
  .workorder-print-grid,
  .timeline-workorder-grid{{grid-template-columns:1fr!important}}
}}
</style>
'''
    if "</head>" not in index:
        raise SystemExit("Buildvalidatie mislukt: HTML-head ontbreekt voor verticale werkbonlayout")
    index = index.replace("</head>", style + "</head>", 1)
    index_path.write_text(index, encoding="utf-8")

required = [
    ".workorder-maintenance-fields,",
    ".workorder-details-grid,",
    ".timeline-workorder-grid,",
    ".workorder-print-grid{grid-template-columns:1fr!important}",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: verticale werkbonlayout ontbreekt: {needle}")

print("[Machinepark] werkbonnen staan overal onder elkaar")
