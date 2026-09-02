from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="work-activities-v1"'

if MARKER not in index:
    feature = r'''
<style data-machinepark-build-fix="work-activities-v1">
#view-maintenance,#view-breakdowns{display:none!important}
.work-activity-type{font-weight:800;white-space:nowrap}.work-activity-type.maintenance{color:#245b9e}.work-activity-type.breakdown{color:#a52f2f}
#workDraftPanels{display:grid;gap:10px;margin-bottom:14px}
#workDraftPanels:empty{display:none}
#workDraftPanels .service-draft-panel{margin:0}
.work-status-stack{display:flex;gap:5px;align-items:center;flex-wrap:wrap}
.work-history-table{min-width:1180px}
@media(max-width:700px){#view-work .toolbar-right{width:100%}#view-work .toolbar-right .btn{flex:1}.work-history-table{min-width:1040px}}
</style>
<script data-machinepark-build-fix="work-activities-v1">
(() => {
  const maintenanceNav = document.querySelector('.nav button[data-view="maintenance"]');
  const breakdownNav = document.querySelector('.nav button[data-view="breakdowns"]');
  if (!maintenanceNav || !breakdownNav) return;

  maintenanceNav.dataset.view = 'work';
  maintenanceNav.setAttribute('onclick', "switchView('work')");
  maintenanceNav.querySelector('.icon').textContent = '🛠';
  maintenanceNav.querySelector('.label').textContent = 'Werkzaamheden';
  breakdownNav.style.display = 'none';
  breakdownNav.setAttribute('aria-hidden','true');

  const maintenanceView = document.getElementById('view-maintenance');
  const partsView = document.getElementById('view-parts');
  const workView = document.createElement('section');
  workView.className = 'view';
  workView.id = 'view-work';
  workView.innerHTML = `
    <div id="workDraftPanels"></div>
    <div class="toolbar">
      <div class="toolbar-left">
        <select id="workKindFilter" class="filter"><option value="">Alle werkzaamheden</option><option value="maintenance">Onderhoud</option><option value="breakdowns">Depannage</option></select>
        <select id="workMaintenanceTypeFilter" class="filter"><option value="">Alle onderhoudstypes</option><option>Halfjaarlijks</option><option>Jaarlijks</option><option>Op afroep</option><option>Maandelijks</option></select>
        <select id="workBreakdownStatusFilter" class="filter"><option value="">Alle depannagestatussen</option><option>Open</option><option>In behandeling</option><option>Opgelost</option></select>
        <select id="workBreakdownPriorityFilter" class="filter"><option value="">Alle prioriteiten</option><option>Laag</option><option>Normaal</option><option>Hoog</option><option>Kritiek</option></select>
      </div>
      <div class="toolbar-right">
        <button class="btn primary" id="workAddMaintenance">+ Onderhoud registreren</button>
        <button class="btn primary" id="workAddBreakdown">+ Depannage toevoegen</button>
      </div>
    </div>
    <div class="table-wrap"><table class="table work-history-table"><thead><tr><th>Datum / uur</th><th>Type</th><th>Toestel</th><th>Werkzaamheid</th><th>Status / prioriteit</th><th>Technieker</th><th>Onderdelen</th><th>Notitie / oplossing</th><th></th></tr></thead><tbody id="workHistoryBody"></tbody></table></div>`;
  (partsView || maintenanceView?.nextSibling)?.parentNode?.insertBefore(workView, partsView || maintenanceView?.nextSibling);

  if (!Object.prototype.hasOwnProperty.call(machineparkViewQueries, 'work')) machineparkViewQueries.work = '';

  function hasViewPermission(key) {
    if (!window.machineparkAccessReady || typeof window.machineparkHasPermission !== 'function') return true;
    return window.machineparkHasPermission(key);
  }
  function canViewMaintenance() { return hasViewPermission('view.maintenance'); }
  function canViewBreakdowns() { return hasViewPermission('view.breakdowns'); }
  function canViewWork() { return canViewMaintenance() || canViewBreakdowns(); }

  function attachDraftPanels() {
    const host = document.getElementById('workDraftPanels');
    if (!host) return;
    const maintenancePanel = document.getElementById('maintenanceDraftPanel');
    const breakdownPanel = document.getElementById('breakdownsDraftPanel');
    if (maintenancePanel && maintenancePanel.parentNode !== host) host.appendChild(maintenancePanel);
    if (breakdownPanel && breakdownPanel.parentNode !== host) host.appendChild(breakdownPanel);
    if (maintenancePanel) {
      maintenancePanel.style.display = canViewMaintenance() ? '' : 'none';
      const title = maintenancePanel.querySelector('.service-draft-head strong');
      if (title) title.textContent = `Onderhoudsconcepten (${maintenancePanel.querySelectorAll('.service-draft-row').length})`;
    }
    if (breakdownPanel) {
      breakdownPanel.style.display = canViewBreakdowns() ? '' : 'none';
      const title = breakdownPanel.querySelector('.service-draft-head strong');
      if (title) title.textContent = `Depannageconcepten (${breakdownPanel.querySelectorAll('.service-draft-row').length})`;
    }
  }

  function workMatchesMaintenance(item) {
    if (item?.isDraft === true || !canViewMaintenance()) return false;
    const kind = document.getElementById('workKindFilter')?.value || '';
    const type = document.getElementById('workMaintenanceTypeFilter')?.value || '';
    if (kind && kind !== 'maintenance') return false;
    if (type && item.type !== type) return false;
    return typeof maintenanceMatchesQuery === 'function' ? maintenanceMatchesQuery(item) : true;
  }

  function workMatchesBreakdown(item) {
    if (item?.isDraft === true || !canViewBreakdowns()) return false;
    const kind = document.getElementById('workKindFilter')?.value || '';
    const status = document.getElementById('workBreakdownStatusFilter')?.value || '';
    const priority = document.getElementById('workBreakdownPriorityFilter')?.value || '';
    if (kind && kind !== 'breakdowns') return false;
    if (status && item.status !== status) return false;
    if (priority && item.priority !== priority) return false;
    return typeof breakdownMatchesQuery === 'function' ? breakdownMatchesQuery(item) : true;
  }

  function maintenanceRow(item) {
    const moment = recordMoment(item);
    return `<tr data-work-kind="maintenance"><td class="nowrap">${recordDateTimeFmt(item)}</td><td><span class="badge blue">Onderhoud</span></td><td><strong>${esc(deviceName(item.deviceId,moment))}</strong></td><td><span class="work-activity-type maintenance">${esc(item.type || 'Onderhoud')}</span></td><td>—</td><td>${esc(item.technician || '—')}</td><td>${esc(usedPartsText(item.usedParts))}</td><td>${esc(item.notes || '—')}</td><td><button class="btn small" data-maintenance-details="${item.id}">Details</button></td></tr>`;
  }

  function breakdownRow(item) {
    const moment = recordMoment(item);
    return `<tr data-work-kind="breakdowns"><td class="nowrap">${recordDateTimeFmt(item)}</td><td><span class="badge danger">Depannage</span></td><td><strong>${esc(deviceName(item.deviceId,moment))}</strong></td><td><span class="work-activity-type breakdown">${esc(item.issue || 'Depannage')}</span></td><td><div class="work-status-stack">${statusBadge(item.priority || 'Normaal')}${breakdownStatusBadge(item.status || 'Open')}</div></td><td>${esc(item.technician || '—')}</td><td>${esc(usedPartsText(item.usedParts))}</td><td>${esc(item.solution || item.diagnosis || '—')}</td><td><button class="btn small" data-edit-breakdown="${item.id}">Details</button></td></tr>`;
  }

  function renderWorkActivities() {
    attachDraftPanels();
    const body = document.getElementById('workHistoryBody');
    if (!body) return;
    const records = [
      ...(state.maintenance || []).filter(workMatchesMaintenance).map(item => ({ kind:'maintenance', item, moment:recordMoment(item) })),
      ...(state.breakdowns || []).filter(workMatchesBreakdown).map(item => ({ kind:'breakdowns', item, moment:recordMoment(item) })),
    ].sort((a,b) => String(b.moment || '').localeCompare(String(a.moment || '')));
    body.innerHTML = records.length
      ? records.map(row => row.kind === 'maintenance' ? maintenanceRow(row.item) : breakdownRow(row.item)).join('')
      : '<tr><td colspan="9"><div class="empty">Nog geen werkzaamheden gevonden.</div></td></tr>';
  }
  window.renderWorkActivities = renderWorkActivities;

  const baseRenderAllForWork = renderAll;
  renderAll = function() {
    baseRenderAllForWork();
    renderWorkActivities();
  };
  window.renderAll = renderAll;

  const baseSwitchViewForWork = switchView;
  function openWorkView() {
    if (!canViewWork()) return baseSwitchViewForWork('dashboard');
    state.view = 'work';
    document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
    workView.classList.add('active');
    document.querySelectorAll('.nav button').forEach(button => button.classList.toggle('active', button.dataset.view === 'work'));
    document.getElementById('pageTitle').textContent = 'Werkzaamheden';
    document.getElementById('pageSubtitle').textContent = 'Onderhoud en depannages in één chronologische historiek.';
    const input = document.getElementById('globalSearch');
    const actions = document.querySelector('.top-actions');
    if (actions) actions.style.display = '';
    state.query = machineparkViewQueries.work || '';
    if (input) { input.value = state.query; input.placeholder = 'Zoek in werkzaamheden…'; }
    closeGlobalSearch();
    renderAll();
  }
  switchView = function(view) {
    if (view === 'maintenance' || view === 'breakdowns' || view === 'work') return openWorkView();
    return baseSwitchViewForWork(view);
  };
  window.switchView = switchView;

  const baseApplyRoleAccessForWork = window.applyMachineparkRoleAccess || applyMachineparkRoleAccess;
  applyMachineparkRoleAccess = function() {
    const wasWork = state.view === 'work';
    if (wasWork) state.view = canViewMaintenance() ? 'maintenance' : canViewBreakdowns() ? 'breakdowns' : 'dashboard';
    try { baseApplyRoleAccessForWork(); }
    finally { if (wasWork && canViewWork()) state.view = 'work'; }
    maintenanceNav.style.display = canViewWork() ? '' : 'none';
    breakdownNav.style.display = 'none';
    const visible = [...document.querySelectorAll('.nav button[data-view]')].filter(button => button.style.display !== 'none').length;
    document.documentElement.style.setProperty('--mobile-nav-count', String(Math.max(1, visible)));
    if (wasWork && canViewWork()) {
      document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
      workView.classList.add('active');
      document.querySelectorAll('.nav button').forEach(button => button.classList.toggle('active', button.dataset.view === 'work'));
    }
  };
  window.applyMachineparkRoleAccess = applyMachineparkRoleAccess;

  const baseApplyOperationalForWork = window.applyOperationalPermissions || applyOperationalPermissions;
  applyOperationalPermissions = function() {
    baseApplyOperationalForWork();
    const addMaintenance = document.getElementById('workAddMaintenance');
    const addBreakdown = document.getElementById('workAddBreakdown');
    const canAddMaintenance = !window.machineparkAccessReady || window.machineparkHasPermission?.('maintenance.add');
    const canAddBreakdown = !window.machineparkAccessReady || window.machineparkHasPermission?.('breakdowns.add');
    if (addMaintenance) addMaintenance.style.display = canAddMaintenance && canViewMaintenance() ? '' : 'none';
    if (addBreakdown) addBreakdown.style.display = canAddBreakdown && canViewBreakdowns() ? '' : 'none';
  };
  window.applyOperationalPermissions = applyOperationalPermissions;

  document.getElementById('workAddMaintenance').onclick = () => openMaintenance();
  document.getElementById('workAddBreakdown').onclick = () => openBreakdown();
  ['workKindFilter','workMaintenanceTypeFilter','workBreakdownStatusFilter','workBreakdownPriorityFilter'].forEach(id => {
    const input = document.getElementById(id);
    if (input) input.onchange = renderWorkActivities;
  });

  attachDraftPanels();
  applyMachineparkRoleAccess();
  applyOperationalPermissions();
  renderWorkActivities();
})();
</script>
'''
    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor Werkzaamheden')
    index = index[:pos] + feature + '\n' + index[pos:]
    index_path.write_text(index, encoding='utf-8')

built = index_path.read_text(encoding='utf-8')
required = [
    MARKER,
    "maintenanceNav.dataset.view = 'work'",
    "maintenanceNav.querySelector('.label').textContent = 'Werkzaamheden'",
    "breakdownNav.style.display = 'none'",
    'id="view-work"',
    'id="workAddMaintenance"',
    'id="workAddBreakdown"',
    '<th>Type</th>',
    '<span class="badge blue">Onderhoud</span>',
    '<span class="badge danger">Depannage</span>',
    "item?.isDraft === true",
    'Onderhoud en depannages in één chronologische historiek.',
    "if (view === 'maintenance' || view === 'breakdowns' || view === 'work')",
    'Onderhoudsconcepten',
    'Depannageconcepten',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: Werkzaamheden ontbreekt ({needle})')

print('[Machinepark] Onderhoud en Depannages samengevoegd in Werkzaamheden met gecombineerde historiek')
