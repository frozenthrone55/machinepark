from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
MARKER = 'data-machinepark-dashboard-kpi-nav="v1"'

index = INDEX.read_text(encoding="utf-8")

if MARKER not in index:
    dashboard_old = """      <div class="grid2">
        <div class="panel"><div class="panel-head"><h3>Komende onderhoudsmomenten</h3><button class="btn small" data-go="maintenance">Alles bekijken</button></div><div id="dashboardUpcoming" class="panel-body"></div></div>
        <div class="panel"><div class="panel-head"><h3>Aandachtspunten</h3><span class="muted" style="font-size:12px">live overzicht</span></div><div id="dashboardAlerts" class="panel-body"></div></div>
      </div>
      <div class="panel" style="margin-top:18px"><div class="panel-head"><h3>Operationele prioriteiten</h3><span class="muted" style="font-size:12px">vandaag</span></div><div id="dashboardProfessional" class="panel-body"></div></div>"""
    dashboard_new = """      <div class="panel dashboard-upcoming-panel" style="margin-top:18px"><div class="panel-head"><h3>Komende onderhoudsmomenten</h3><button class="btn small" data-go="maintenance">Alles bekijken</button></div><div id="dashboardUpcoming" class="panel-body"></div></div>
      <div id="dashboardAlerts" hidden></div>"""
    if dashboard_old not in index:
        raise SystemExit("Buildvalidatie mislukt: dashboardpanelen voor aandacht/prioriteiten niet gevonden")
    index = index.replace(dashboard_old, dashboard_new, 1)

    cards = [
        (
            '<div class="kpi"><span class="dot"></span><div class="label">Actieve toestellen</div><div class="value" id="kpiDevices">0</div><div class="hint">in servicebeheer</div></div>',
            '<div class="kpi dashboard-kpi-link" data-dashboard-kpi="devices" role="button" tabindex="0" aria-label="Open Toestellen"><span class="dot"></span><div class="label">Actieve toestellen</div><div class="value" id="kpiDevices">0</div><div class="hint">in servicebeheer</div></div>'
        ),
        (
            '<div class="kpi"><span class="dot" style="background:#c37d1f"></span><div class="label">Onderhoud aandacht</div><div class="value" id="kpiDue">0</div><div class="hint">vervallen of binnen 30 dagen</div></div>',
            '<div class="kpi dashboard-kpi-link" data-dashboard-kpi="maintenance" role="button" tabindex="0" aria-label="Open Onderhoud"><span class="dot" style="background:#c37d1f"></span><div class="label">Onderhoud aandacht</div><div class="value" id="kpiDue">0</div><div class="hint">vervallen of binnen 30 dagen</div></div>'
        ),
        (
            '<div class="kpi"><span class="dot" style="background:#bc4a4a"></span><div class="label">Open depannages</div><div class="value" id="kpiBreakdowns">0</div><div class="hint">open of in behandeling</div></div>',
            '<div class="kpi dashboard-kpi-link" data-dashboard-kpi="breakdowns" role="button" tabindex="0" aria-label="Open Depannages"><span class="dot" style="background:#bc4a4a"></span><div class="label">Open depannages</div><div class="value" id="kpiBreakdowns">0</div><div class="hint">open of in behandeling</div></div>'
        ),
        (
            '<div class="kpi"><span class="dot" style="background:#a96e22"></span><div class="label">Lage voorraad</div><div class="value" id="kpiStock">0</div><div class="hint">op of onder minimumvoorraad</div></div>',
            '<div class="kpi dashboard-kpi-link" data-dashboard-kpi="parts" role="button" tabindex="0" aria-label="Open Lage voorraad"><span class="dot" style="background:#a96e22"></span><div class="label">Lage voorraad</div><div class="value" id="kpiStock">0</div><div class="hint">op of onder minimumvoorraad</div></div>'
        ),
    ]
    for old, new in cards:
        if new in index:
            continue
        if old not in index:
            raise SystemExit("Buildvalidatie mislukt: dashboard KPI-kaart niet gevonden")
        index = index.replace(old, new, 1)

    todo_old = '<div class="kpi action-kpi" id="kpiActionsCard" role="button" tabindex="0">'
    todo_new = '<div class="kpi action-kpi dashboard-kpi-link" id="kpiActionsCard" role="button" tabindex="0" aria-label="Open ToDo">'
    if todo_new not in index:
        if todo_old not in index:
            raise SystemExit("Buildvalidatie mislukt: ToDo KPI-kaart niet gevonden")
        index = index.replace(todo_old, todo_new, 1)

    style = """
<style data-machinepark-dashboard-kpi-nav="v1">
#view-dashboard .dashboard-kpi-link{cursor:pointer;transition:transform .14s ease,box-shadow .14s ease,border-color .14s ease}
#view-dashboard .dashboard-kpi-link:hover{transform:translateY(-2px);box-shadow:0 10px 28px rgba(25,57,48,.10);border-color:#bfd1ca}
#view-dashboard .dashboard-kpi-link:focus-visible{outline:3px solid rgba(44,106,88,.20);outline-offset:2px;border-color:#7ea598}
#view-dashboard .dashboard-upcoming-panel{width:100%}
</style>
"""
    if "</head>" not in index:
        raise SystemExit("Buildvalidatie mislukt: </head> ontbreekt voor dashboard KPI navigatie")
    index = index.replace("</head>", style + "</head>", 1)

    script = """
<script data-machinepark-dashboard-kpi-nav="v1">
(function(){
  function goDashboardKpi(card){
    var target=card && card.dataset ? card.dataset.dashboardKpi : "";
    if(!target)return;
    if(target==="parts"){
      var stock=document.getElementById("partStockFilter");
      if(stock)stock.value="low";
    }else if(target==="devices"){
      var device=document.getElementById("deviceStatusFilter");
      if(device)device.value="";
    }else if(target==="maintenance"){
      var maintenance=document.getElementById("maintenanceTypeFilter");
      if(maintenance)maintenance.value="";
    }else if(target==="breakdowns"){
      var status=document.getElementById("breakdownStatusFilter");
      var priority=document.getElementById("breakdownPriorityFilter");
      if(status)status.value="";
      if(priority)priority.value="";
    }
    if(typeof window.switchView==="function")window.switchView(target);
  }
  document.addEventListener("click",function(event){
    var card=event.target && event.target.closest ? event.target.closest("[data-dashboard-kpi]") : null;
    if(card)goDashboardKpi(card);
  });
  document.addEventListener("keydown",function(event){
    if(event.key!=="Enter" && event.key!==" ")return;
    var card=event.target && event.target.closest ? event.target.closest("[data-dashboard-kpi]") : null;
    if(!card)return;
    event.preventDefault();
    goDashboardKpi(card);
  });
})();
</script>
"""
    body_pos=index.rfind("</body>")
    if body_pos < 0:
        raise SystemExit("Buildvalidatie mislukt: </body> ontbreekt voor dashboard KPI navigatie")
    index=index[:body_pos]+script+index[body_pos:]

required = [
    'data-dashboard-kpi="devices"',
    'data-dashboard-kpi="maintenance"',
    'data-dashboard-kpi="breakdowns"',
    'data-dashboard-kpi="parts"',
    'action-kpi dashboard-kpi-link',
    'stock.value="low"',
    'goDashboardKpi',
    'dashboard-upcoming-panel',
]
for needle in required:
    if needle not in index:
        raise SystemExit("Buildvalidatie mislukt: dashboard KPI navigatie ontbreekt (" + needle + ")")

for forbidden in [
    '<h3>Aandachtspunten</h3>',
    '<h3>Operationele prioriteiten</h3>',
    'id="dashboardProfessional"',
]:
    if forbidden in index:
        raise SystemExit("Buildvalidatie mislukt: verwijderd dashboardblok nog aanwezig (" + forbidden + ")")

INDEX.write_text(index, encoding="utf-8")
print("[Machinepark] dashboard vereenvoudigd; vijf KPI-kaarten openen hun modules")
