from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
sw = (ROOT / "sw.js").read_text(encoding="utf-8")

PATCH_MARKER = 'data-machinepark-build-fix="mobile-search-technician-v1"'

# De bronpagina is bewust één groot zelfstandig HTML-bestand. Voeg deze twee kleine
# UI-correcties tijdens de build idempotent toe, zodat de bestaande applicatielogica
# niet breed hoeft te worden herschreven.
if PATCH_MARKER not in index:
    mobile_style = f'''\n<style {PATCH_MARKER}>
@media(max-width:700px){{
  .topbar{{flex-wrap:wrap}}
  .title{{order:1;min-width:0;flex:1 1 180px}}
  .account-summary{{order:2;flex:0 0 auto}}
  .top-actions{{display:flex;order:3;width:100%}}
  .top-actions .search{{width:100%}}
  .top-actions .search input{{width:100%}}
}}
</style>\n'''

    technician_script = f'''\n<script {PATCH_MARKER}>
(() => {{
  const originalOpenDevice = openDevice;
  const originalShowDeviceHistory = showDeviceHistory;
  const technicianCanEditDevice = () => window.machineparkRole === 'technieker';
  window.machineparkTechnicianCanEditDevice = technicianCanEditDevice;

  openDevice = function(id) {{
    if (!technicianCanEditDevice() || !id) return originalOpenDevice(id);
    const old = state.devices.find(d => d.id === id);
    if (!old) {{ toast('Toestel niet gevonden'); return; }}

    const body = `<div class="form-grid">
      <div class="field full"><div class="alert"><strong>Techniekerrechten</strong>Technieker kan alleen toestelstatus en notities aanpassen. Andere toestelgegevens blijven alleen-lezen.</div></div>
      <div class="field"><label>Toestel</label><input value="${{esc(old.assetCode || old.model || 'Toestel')}}" readonly style="background:#f4f6f5"></div>
      <div class="field"><label>Locatie</label><input value="${{esc(deviceLocationAt(old) || old.location || 'Geen locatie')}}" readonly style="background:#f4f6f5"></div>
      <div class="field"><label>Status</label><select name="status">${{['Actief','In herstelling','Buiten dienst'].map(x => `<option ${{old.status === x ? 'selected' : ''}}>${{x}}</option>`).join('')}}</select></div>
      <div class="field full"><label>Notities</label><textarea name="notes">${{esc(old.notes || '')}}</textarea></div>
    </div>`;

    showModal('Toestelstatus & notities', body, 'Opslaan', async fd => {{
      const obj = {{
        ...old,
        status: val(fd, 'status') || old.status || 'Actief',
        notes: val(fd, 'notes'),
        updatedAt: new Date().toISOString(),
      }};
      await put('devices', obj);
      closeModal();
      await refresh();
      toast('Toestelstatus en notities opgeslagen');
    }});
  }};

  showDeviceHistory = function(id) {{
    originalShowDeviceHistory(id);
    if (!technicianCanEditDevice()) return;
    setTimeout(() => {{
      const foot = $('#modal .modal-foot');
      if (!foot || $('#technicianEditDevice')) return;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.id = 'technicianEditDevice';
      btn.className = 'btn';
      btn.textContent = 'Status / notities aanpassen';
      btn.onclick = () => {{ closeModal(); openDevice(id); }};
      foot.insertBefore(btn, foot.querySelector('.btn.primary') || null);
    }}, 0);
  }};
}})();
</script>\n'''

    if "</head>" not in index or "</body>" not in index:
        raise SystemExit("Buildvalidatie mislukt: HTML-afsluiters ontbreken")
    index = index.replace("</head>", mobile_style + "</head>", 1)
    index = index.replace("</body>", technician_script + "</body>", 1)
    index_path.write_text(index, encoding="utf-8")

required = {
    "branding": "<title>Machinepark</title>",
    "Clerk profiel": "id=\"clerkUserButton\"",
    "onderdeel autocomplete": "usage-autocomplete",
    "toestel autocomplete": "device-autocomplete",
    "audit undo": "data-undo-audit",
    "apart onderdelenlogboek": "id=\"auditPartsLogBody\"",
    "operationeel dashboard": "dashboardProfessional",
    "wit koffietoestel SVG navigatie-icoon": "class=\"device-nav-icon-svg\"",
    "dashboard toestelbolletje": "<span class=\"dot\"></span><div class=\"label\">Actieve toestellen</div>",
    "veiligheidsbackup": "Machinepark_Veiligheidsbackup_",
    "importverslag": "downloadStockImportReport",
    "onderdelenexport afbeeldingen": "makeStoreZip",
    "afbeeldingskolom export": "Afbeelding bestand",
    "back-up afbeeldingen": "includesImages:true",
    "prijsimport": "Prijs excl. BTW",
    "technieker rol": "technieker",
    "magazijnier rol": "magazijnier",
    "onderhoud navigatie": "data-view=\"maintenance\"",
    "onderhoud knop": "$('#addMaintenance').onclick=()=>openMaintenance();",
    "locatiegericht onderhoud": "id=\"maintenanceLocationSearch\"",
    "zoeken op toestelnummer": "locationGroupMatches",
    "zoekhint locatie of toestel": "Typ locatie of toestelnummer…",
    "onderhoud per toestel": "maintenance-machine-card",
    "depannage navigatie": "data-view=\"breakdowns\"",
    "locatiegerichte depannage": "id=\"breakdownLocationSearch\"",
    "depannage per toestel": "breakdown-machine-card",
    "registraties verwijderen": "deleteServiceRecordAtomic",
    "onderhoud verwijderen": "deleteMaintenanceFromDetails",
    "depannage verwijderen": "deleteBreakdownFromDetails",
    "onderdelen navigatie": "data-view=\"parts\"",
    "mobiele zoekfix": PATCH_MARKER,
    "technieker beperkte toestelbewerking": "Technieker kan alleen toestelstatus en notities aanpassen.",
    "technieker bewerkknop": "Status / notities aanpassen",
}
for label, needle in required.items():
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: {label} ontbreekt")
if index.count("id=\"clerkUserButton\"") != 1:
    raise SystemExit("Buildvalidatie mislukt: Clerk-profielknop is niet uniek")
if "id=\"clearAll\"" in index:
    raise SystemExit("Buildvalidatie mislukt: Alles wissen is teruggekeerd")
if "machinepark-v1.64-export-images" not in sw:
    raise SystemExit("Buildvalidatie mislukt: verkeerde service-worker cache")
print("[Machinepark] broncodevalidatie geslaagd")
