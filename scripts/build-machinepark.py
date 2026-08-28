from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
index = (ROOT / "index.html").read_text(encoding="utf-8")
sw = (ROOT / "sw.js").read_text(encoding="utf-8")
required = {
    "branding": "<title>Machinepark</title>",
    "Clerk profiel": "id=\"clerkUserButton\"",
    "onderdeel autocomplete": "usage-autocomplete",
    "toestel autocomplete": "device-autocomplete",
    "audit undo": "data-undo-audit",
    "apart onderdelenlogboek": "id=\"auditPartsLogBody\"",
    "operationeel dashboard": "dashboardProfessional",
    "veiligheidsbackup": "Machinepark_Veiligheidsbackup_",
    "importverslag": "downloadStockImportReport",
    "prijsimport": "Prijs excl. BTW",
    "technieker rol": "technieker",
    "magazijnier rol": "magazijnier",
    "onderhoud navigatie": "data-view=\"maintenance\"",
    "onderhoud knop": "$('#addMaintenance').onclick=()=>openMaintenance();",
    "locatiegericht onderhoud": "id=\"maintenanceLocation\"",
    "onderhoud per toestel": "maintenance-machine-card",
    "depannage navigatie": "data-view=\"breakdowns\"",
    "onderdelen navigatie": "data-view=\"parts\"",
}
for label, needle in required.items():
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: {label} ontbreekt")
if index.count("id=\"clerkUserButton\"") != 1:
    raise SystemExit("Buildvalidatie mislukt: Clerk-profielknop is niet uniek")
if "id=\"clearAll\"" in index:
    raise SystemExit("Buildvalidatie mislukt: Alles wissen is teruggekeerd")
if "machinepark-v1.55-location-maintenance" not in sw:
    raise SystemExit("Buildvalidatie mislukt: verkeerde service-worker cache")
print("[Machinepark] broncodevalidatie geslaagd")
