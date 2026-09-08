from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
MARKER = 'data-machinepark-dashboard-kpi-nav="v2"'

index = INDEX.read_text(encoding="utf-8")

if MARKER not in index:
    dashboard_old = """      <div class="grid2">
        <div class="panel"><div class="panel-head"><h3>Komende onderhoudsmomenten</h3><button class="btn small" data-go="maintenance">Alles bekijken</button></div><div id="dashboardUpcoming" class="panel-body"></div></div>
        <div class="panel"><div class="panel-head"><h3>Aandachtspunten</h3><span class="muted" style="font-size:12px">live overzicht</span></div><div id="dashboardAlerts" class="panel-body"></div></div>
      </div>
      <div class="panel" style="margin-top:18px"><div class="panel-head"><h3>Operationele prioriteiten</h3><span class="muted" style="font-size:12px">vandaag</span></div><div id="dashboardProfessional" class="panel-body"></div></div>"""
    dashboard_new = """      <div class="panel dashboard-upcoming-panel" style="margin-top:18px"><div class="panel-head"><h3>Komende onderhoudsmomenten</h3><button class="btn small" data-dashboard-kpi="maintenance">Alles bekijken</button></div><div id="dashboardUpcoming" class="panel-body"></div></div>
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


    # De drilldown moet exact dezelfde selectie tonen als de KPI-teller.
    device_filter_old = '<select id="deviceStatusFilter" class="filter"><option value="">Alle statussen</option>'
    device_filter_new = '<select id="deviceStatusFilter" class="filter"><option value="">Alle statussen</option><option value="service">In servicebeheer</option>'
    if device_filter_old not in index:
        raise SystemExit("Buildvalidatie mislukt: toestelstatusfilter niet gevonden")
    index = index.replace(device_filter_old, device_filter_new, 1)

    device_patterns = [
        ("(!f||d.status===f)&&deviceMatchesQuery(d)", "(!f||(f==='service'?d.status!=='Buiten dienst':d.status===f))&&deviceMatchesQuery(d)"),
        ("(!f || d.status === f) && deviceMatchesQuery(d)", "(!f || (f === 'service' ? d.status !== 'Buiten dienst' : d.status === f)) && deviceMatchesQuery(d)"),
    ]
    device_replacements = 0
    for old, new in device_patterns:
        if old in index:
            device_replacements += index.count(old)
            index = index.replace(old, new)
    if device_replacements < 1:
        raise SystemExit("Buildvalidatie mislukt: renderDevices-filter niet gevonden")

    kind_old = '<select id="workKindFilter" class="filter"><option value="">Alle werkzaamheden</option>'
    kind_new = '<select id="workKindFilter" class="filter"><option value="">Alle werkzaamheden</option><option value="maintenance-attention">Onderhoud aandacht</option>'
    if kind_old not in index:
        raise SystemExit("Buildvalidatie mislukt: werkzaamhedenfilter niet gevonden")
    index = index.replace(kind_old, kind_new, 1)

    breakdown_filter_old = '<select id="workBreakdownStatusFilter" class="filter"><option value="">Alle depannagestatussen</option>'
    breakdown_filter_new = '<select id="workBreakdownStatusFilter" class="filter"><option value="">Alle depannagestatussen</option><option value="open-attention">Open of in behandeling</option>'
    if breakdown_filter_old not in index:
        raise SystemExit("Buildvalidatie mislukt: depannagestatusfilter niet gevonden")
    index = index.replace(breakdown_filter_old, breakdown_filter_new, 1)

    combined_anchor = "  function renderCombined(){const body=document.getElementById('workHistoryBody');if(!body)return;const kind=document.getElementById('workKindFilter')?.value||'',mt=document.getElementById('workMaintenanceTypeFilter')?.value||'',bs=document.getElementById('workBreakdownStatusFilter')?.value||'',bp=document.getElementById('workBreakdownPriorityFilter')?.value||'',canM=!window.machineparkAccessReady||window.machineparkHasPermission?.('view.maintenance'),canB=canView(),rows=[];"
    combined_new = combined_anchor + "if(kind==='maintenance-attention'&&typeof window.machineparkDashboardRenderMaintenanceAttention==='function'){window.machineparkDashboardRenderMaintenanceAttention(body);renderDrafts();return;}"
    if combined_anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: gecombineerde werkzaamheden-renderer niet gevonden")
    index = index.replace(combined_anchor, combined_new, 1)

    breakdown_condition_old = "isOtherWork(item)||bs&&item.status!==bs||bp&&item.priority!==bp"
    breakdown_condition_new = "isOtherWork(item)||bs&&((bs==='open-attention'&&item.status==='Opgelost')||(bs!=='open-attention'&&item.status!==bs))||bp&&item.priority!==bp"
    if breakdown_condition_old not in index:
        raise SystemExit("Buildvalidatie mislukt: depannagefilter in gecombineerde werkzaamheden niet gevonden")
    index = index.replace(breakdown_condition_old, breakdown_condition_new, 1)

    kpi_open_old = "const open=state.breakdowns.filter(b=>b.status!=='Opgelost').length;"
    kpi_open_new = "const open=state.breakdowns.filter(b=>b.status!=='Opgelost'&&b.isDraft!==true&&b.serviceKind!=='other').length;"
    if kpi_open_old not in index:
        raise SystemExit("Buildvalidatie mislukt: KPI open depannages teller niet gevonden")
    index = index.replace(kpi_open_old, kpi_open_new, 1)

    todo_go_old = "const go=()=>{actionScope='mine';if(typeof switchView==='function')switchView('actions');};"
    todo_go_new = "const go=()=>{window.machineparkDashboardTodoOpenOnly=true;actionScope='all';if(typeof switchView==='function')switchView('actions');};"
    if todo_go_old not in index:
        raise SystemExit("Buildvalidatie mislukt: ToDo KPI handler niet gevonden")
    index = index.replace(todo_go_old, todo_go_new, 1)

    todo_render_old = "const oc=document.getElementById('actionOpenCount'),dc=document.getElementById('actionDoneCount'),show=document.getElementById('actionShowAllDone');"
    todo_render_new = "const oc=document.getElementById('actionOpenCount'),dc=document.getElementById('actionDoneCount'),show=document.getElementById('actionShowAllDone'),doneSection=document.querySelector('#view-actions .action-section-done');if(doneSection)doneSection.style.display=window.machineparkDashboardTodoOpenOnly?'none':'';"
    if todo_render_old not in index:
        raise SystemExit("Buildvalidatie mislukt: ToDo renderer anker niet gevonden")
    index = index.replace(todo_render_old, todo_render_new, 1)

    todo_scope_old = "const scope=e.target.closest('[data-action-scope]');if(scope){actionScope=scope.dataset.actionScope||'all';renderActions();return;}"
    todo_scope_new = "const scope=e.target.closest('[data-action-scope]');if(scope){window.machineparkDashboardTodoOpenOnly=false;actionScope=scope.dataset.actionScope||'all';renderActions();return;}"
    if todo_scope_old not in index:
        raise SystemExit("Buildvalidatie mislukt: ToDo scope-handler niet gevonden")
    index = index.replace(todo_scope_old, todo_scope_new, 1)

    style = """
<style data-machinepark-dashboard-kpi-nav="v2">
#view-dashboard .kpis{grid-template-columns:repeat(3,minmax(0,1fr))}
#view-dashboard .dashboard-kpi-link{cursor:pointer;transition:transform .14s ease,box-shadow .14s ease,border-color .14s ease}
#view-dashboard .dashboard-kpi-link:hover{transform:translateY(-2px);box-shadow:0 10px 28px rgba(25,57,48,.10);border-color:#bfd1ca}
#view-dashboard .dashboard-kpi-link:focus-visible{outline:3px solid rgba(44,106,88,.20);outline-offset:2px;border-color:#7ea598}
#view-dashboard [data-dashboard-kpi="devices"]{order:1}
#view-dashboard #kpiActionsCard{order:2}
#view-dashboard [data-dashboard-kpi="parts"]{order:3}
#view-dashboard #kpiOpenServiceCard{order:4}
#view-dashboard [data-dashboard-kpi="breakdowns"]{order:5}
#view-dashboard [data-dashboard-kpi="maintenance"]{order:6}
#view-dashboard .dashboard-upcoming-panel{width:100%}
@media (max-width:1050px){#view-dashboard .kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:680px){#view-dashboard .kpis{grid-template-columns:1fr}}
</style>
"""
    if "</head>" not in index:
        raise SystemExit("Buildvalidatie mislukt: </head> ontbreekt voor dashboard KPI navigatie")
    index = index.replace("</head>", style + "</head>", 1)

    script = """
<script data-machinepark-dashboard-kpi-nav="v2">
(function(){

  window.machineparkDashboardRenderMaintenanceAttention=function(body){
    if(!body)return;
    var attention=[];
    (state.devices||[]).filter(function(device){return device.status!=="Buiten dienst";}).forEach(function(device){
      if(device.nextHalf&&daysUntil(device.nextHalf)<=30)attention.push({device:device,type:"Halfjaarlijks",date:device.nextHalf});
      if(device.nextAnnual&&daysUntil(device.nextAnnual)<=30)attention.push({device:device,type:"Jaarlijks",date:device.nextAnnual});
    });
    attention.sort(function(a,b){return String(a.date||"").localeCompare(String(b.date||""));});
    body.innerHTML="";
    if(!attention.length){
      var emptyRow=document.createElement("tr"),emptyCell=document.createElement("td"),empty=document.createElement("div");
      emptyCell.colSpan=9;empty.className="empty";empty.textContent="Geen onderhoud dat aandacht nodig heeft.";
      emptyCell.appendChild(empty);emptyRow.appendChild(emptyCell);body.appendChild(emptyRow);return;
    }
    attention.forEach(function(row){
      var tr=document.createElement("tr");tr.dataset.workKind="maintenance-attention";
      var date=document.createElement("td");date.className="nowrap";var dateStrong=document.createElement("strong");dateStrong.textContent=dateFmt(row.date);date.appendChild(dateStrong);
      var kind=document.createElement("td");kind.innerHTML='<span class="badge blue">Onderhoud</span>';
      var deviceCell=document.createElement("td"),deviceStrong=document.createElement("strong"),location=document.createElement("span");
      deviceStrong.textContent=row.device.assetCode||row.device.model||"Toestel";location.className="muted";location.textContent=deviceLocationAt(row.device,row.date)||"";
      deviceCell.appendChild(deviceStrong);deviceCell.appendChild(document.createElement("br"));deviceCell.appendChild(location);
      var type=document.createElement("td"),typeSpan=document.createElement("span");typeSpan.className="work-activity-type maintenance";typeSpan.textContent=row.type;type.appendChild(typeSpan);
      var status=document.createElement("td");status.innerHTML=dueBadge(row.date);
      var tech=document.createElement("td");tech.textContent="—";
      var parts=document.createElement("td");parts.textContent="—";
      var note=document.createElement("td");note.textContent="Vervallen of binnen 30 dagen";
      var action=document.createElement("td"),button=document.createElement("button");button.type="button";button.className="btn small";button.dataset.deviceDetails=row.device.id;button.textContent="Toestel";action.appendChild(button);
      [date,kind,deviceCell,type,status,tech,parts,note,action].forEach(function(cell){tr.appendChild(cell);});
      body.appendChild(tr);
    });
  };


  function ensureServiceOverviewView(){
    var view=document.getElementById("view-service-overview");
    if(view)return view;
    view=document.createElement("section");
    view.id="view-service-overview";
    view.className="view";
    var work=document.getElementById("view-work"),parts=document.getElementById("view-parts");
    var parent=(work||parts)&&((work||parts).parentNode);
    if(parent)parent.insertBefore(view,parts||((work&&work.nextSibling)||null));
    else (document.querySelector("main")||document.body).appendChild(view);
    return view;
  }

  function serviceOverviewRows(){
    return Array.prototype.slice.call(document.querySelectorAll("#serviceVisitBody tr")).filter(function(row){
      return !!row.querySelector(".service-visit-status");
    });
  }

  function serviceOverviewApplyFilter(){
    var select=document.getElementById("serviceOverviewStatusFilter");
    var filter=select?select.value:"open";
    serviceOverviewRows().forEach(function(row){
      var status=(row.querySelector(".service-visit-status")||{}).textContent||"";
      status=status.trim();
      var open=status==="Open"||status==="In behandeling";
      row.style.display=filter==="all"?"":filter==="closed"?(open?"none":""):(open?"":"none");
    });
    var drafts=document.getElementById("serviceVisitDraftList");
    if(drafts)drafts.style.display=filter==="closed"?"none":"";
    var title=document.getElementById("pageTitle");
    if(state&&state.view==="service-overview"&&title)title.textContent=filter==="open"?"Open service":"Service";
  }

  function ensureOpenServiceKpi(){
    var box=document.querySelector("#view-dashboard .kpis");
    if(!box)return null;
    var card=document.getElementById("kpiOpenServiceCard");
    if(!card){
      card=document.createElement("div");
      card.id="kpiOpenServiceCard";
      card.className="kpi dashboard-kpi-link";
      card.dataset.dashboardKpi="service";
      card.setAttribute("role","button");
      card.setAttribute("tabindex","0");
      card.setAttribute("aria-label","Open service");
      card.innerHTML='<span class="dot" style="background:#397a68"></span><div class="label">Open service</div><div class="value" id="kpiOpenService">0</div><div class="hint" id="kpiOpenServiceHint">0 verslagen · 0 concepten</div>';
      box.appendChild(card);
    }
    return card;
  }

  function updateOpenServiceKpi(){
    ensureOpenServiceKpi();
    var openReports=serviceOverviewRows().filter(function(row){
      var status=(row.querySelector(".service-visit-status")||{}).textContent||"";
      status=status.trim();
      return status==="Open"||status==="In behandeling";
    }).length;
    var concepts=document.querySelectorAll("#serviceVisitDraftList [data-sv-draft-open]").length;
    var value=document.getElementById("kpiOpenService");
    var hint=document.getElementById("kpiOpenServiceHint");
    if(value)value.textContent=String(openReports+concepts);
    if(hint)hint.textContent=String(openReports)+" verslag"+(openReports===1?"":"en")+" · "+String(concepts)+" concept"+(concepts===1?"":"en");
  }

  function syncServiceOverview(){
    var panel=document.getElementById("serviceVisitPanel");
    if(!panel){ensureOpenServiceKpi();updateOpenServiceKpi();return;}
    var view=ensureServiceOverviewView();
    if(panel.parentNode!==view)view.appendChild(panel);

    var head=panel.querySelector(".service-visit-panel-head");
    if(head&&!document.getElementById("serviceOverviewStatusFilter")){
      var select=document.createElement("select");
      select.id="serviceOverviewStatusFilter";
      select.className="filter";
      select.innerHTML='<option value="open">Open service</option><option value="all">Alle serviceverslagen</option><option value="closed">Afgesloten</option>';
      select.value="open";
      select.addEventListener("change",serviceOverviewApplyFilter);
      var add=document.getElementById("serviceVisitAdd");
      if(add&&add.parentNode===head)head.insertBefore(select,add);
      else head.appendChild(select);
    }

    var m=document.getElementById("workAddMaintenance"),b=document.getElementById("workAddBreakdown");
    if(m&&m.textContent.indexOf("Los onderhoud")>=0)m.textContent="+ Onderhoud registreren";
    if(b&&b.textContent.indexOf("Losse depannage")>=0)b.textContent="+ Depannage toevoegen";

    serviceOverviewApplyFilter();
    updateOpenServiceKpi();
    restoreServiceOverviewActive();

    if(!panel.__machineparkServiceOverviewObserver){
      var scheduled=false;
      panel.__machineparkServiceOverviewObserver=new MutationObserver(function(){
        if(scheduled)return;
        scheduled=true;
        requestAnimationFrame(function(){scheduled=false;serviceOverviewApplyFilter();updateOpenServiceKpi();restoreServiceOverviewActive();});
      });
      panel.__machineparkServiceOverviewObserver.observe(panel,{childList:true,subtree:true,characterData:true});
    }
  }

  function restoreServiceOverviewActive(){
    if(!state||state.view!=="service-overview")return;
    var view=ensureServiceOverviewView();
    document.querySelectorAll(".view").forEach(function(node){node.classList.remove("active");});
    view.classList.add("active");
    document.querySelectorAll(".nav button").forEach(function(button){button.classList.remove("active");});
    var select=document.getElementById("serviceOverviewStatusFilter");
    var title=document.getElementById("pageTitle"),subtitle=document.getElementById("pageSubtitle"),search=document.getElementById("globalSearch");
    if(title)title.textContent=(select&&select.value==="open")?"Open service":"Service";
    if(subtitle)subtitle.textContent="Serviceconcepten en gezamenlijke serviceverslagen in een apart overzicht.";
    if(search){search.value="";search.placeholder="Serviceoverzicht";}
    if(typeof closeGlobalSearch==="function")closeGlobalSearch();
  }

  function openServiceOverview(filter){
    syncServiceOverview();
    ensureServiceOverviewView();
    var select=document.getElementById("serviceOverviewStatusFilter");
    if(select)select.value=filter||"open";

    var navigate=window.machineparkNavigate||window.switchView;
    if(typeof navigate==="function"){
      try{navigate("service-overview");}
      catch(error){console.warn("[Machinepark] Service-navigatie via runtime mislukt",error);state.view="service-overview";}
    }else{
      state.view="service-overview";
    }

    restoreServiceOverviewActive();
    serviceOverviewApplyFilter();
  }
  window.machineparkOpenServiceOverview=openServiceOverview;

  var baseServiceRender=window.renderMachineparkServiceVisits;
  if(typeof baseServiceRender==="function"){
    window.renderMachineparkServiceVisits=function(){
      var result=baseServiceRender.apply(this,arguments);
      setTimeout(syncServiceOverview,0);
      return result;
    };
  }
  setTimeout(syncServiceOverview,0);

  function goDashboardKpi(card){
    var target=card && card.dataset ? card.dataset.dashboardKpi : "";
    if(!target)return;
    if(target==="service"){
      if(typeof window.machineparkOpenServiceOverview==="function")window.machineparkOpenServiceOverview("open");
      return;
    }
    var route=target;

    if(target==="parts"){
      var stock=document.getElementById("partStockFilter");
      if(stock)stock.value="low";
    }else if(target==="devices"){
      var device=document.getElementById("deviceStatusFilter");
      if(device)device.value="service";
    }else if(target==="maintenance" || target==="breakdowns"){
      // Onderhoud en depannages zijn in de huidige app samengevoegd onder
      // Werkzaamheden. De oude view-maintenance/view-breakdowns zijn leeg.
      route="work";
      var kind=document.getElementById("workKindFilter");
      var maintenanceType=document.getElementById("workMaintenanceTypeFilter");
      var breakdownStatus=document.getElementById("workBreakdownStatusFilter");
      var breakdownPriority=document.getElementById("workBreakdownPriorityFilter");
      if(kind)kind.value=target==="maintenance" ? "maintenance-attention" : "breakdowns";
      if(maintenanceType)maintenanceType.value="";
      if(breakdownStatus)breakdownStatus.value=target==="breakdowns" ? "open-attention" : "";
      if(breakdownPriority)breakdownPriority.value="";
    }

    var navigate=window.machineparkInlineNavigate || window.machineparkEarlyNavigate || window.machineparkNavigate || window.switchView;
    if(typeof navigate==="function")navigate(route);

    if(route==="work"){
      setTimeout(function(){
        if(typeof window.machineparkRenderCombinedWork==="function")window.machineparkRenderCombinedWork();
        else if(typeof window.renderWorkActivities==="function")window.renderWorkActivities();
      },0);
    }
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
    'device.value="service"',
    'maintenance-attention',
    'open-attention',
    'machineparkDashboardRenderMaintenanceAttention',
    'machineparkDashboardTodoOpenOnly',
    'view-service-overview',
    'kpiOpenServiceCard',
    'serviceOverviewStatusFilter',
    'machineparkOpenServiceOverview',
    'restoreServiceOverviewActive',
    'navigate("service-overview")',
    'route="work"',
    'workKindFilter',
    'machineparkInlineNavigate',
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


# Maak service-overview ook bekend bij de gegenereerde navigatieruntime.
nav_meta_old = "    settings: ['Beheer', 'Back-up, import en instellingen.'],\\n    };"
nav_meta_new = "    settings: ['Beheer', 'Back-up, import en instellingen.'],\\n      'service-overview': ['Open service', 'Serviceconcepten en gezamenlijke serviceverslagen in een apart overzicht.'],\\n    };"
if nav_meta_old in index and "'service-overview': ['Open service'" not in index:
    index = index.replace(nav_meta_old, nav_meta_new, 1)

INDEX.write_text(index, encoding="utf-8")
print("[Machinepark] dashboard vereenvoudigd; vijf KPI-kaarten openen hun modules")
