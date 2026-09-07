from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="other-works-merged-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    index = index.replace(old, new, 1)


if MARKER not in index:
    old_view = r'''  const workNav=document.querySelector('.nav button[data-view="work"]'),otherNav=document.createElement('button');otherNav.type='button';otherNav.dataset.otherWorksNav='1';otherNav.innerHTML='<span class="icon">🧰</span><span class="label">Andere werken</span>';if(workNav?.parentNode)workNav.insertAdjacentElement('afterend',otherNav);
  const workView=document.getElementById('view-work'),otherView=document.createElement('section');otherView.className='view';otherView.id='view-otherworks';
  otherView.innerHTML=`<div id="otherWorkDraftPanel" class="other-work-draft-host"></div><div class="toolbar"><div class="toolbar-left"><select id="otherWorkTypeFilter" class="filter"><option value="">Alle soorten</option></select><select id="otherWorkStatusFilter" class="filter"><option value="">Alle statussen</option><option>Open</option><option>In behandeling</option><option>Opgelost</option></select><select id="otherWorkPriorityFilter" class="filter"><option value="">Alle prioriteiten</option><option>Laag</option><option>Normaal</option><option>Hoog</option><option>Kritiek</option></select></div><div class="toolbar-right"><button class="btn primary" id="addOtherWork">+ Andere werken registreren</button></div></div><div class="table-wrap"><table class="table"><thead><tr><th>Datum / uur</th><th>Type</th><th>Toestel</th><th>Werkzaamheid</th><th>Status / prioriteit</th><th>Technieker</th><th>Onderdelen</th><th>Oplossing</th><th></th></tr></thead><tbody id="otherWorkBody"></tbody></table></div>`;
  if(workView?.parentNode)workView.insertAdjacentElement('afterend',otherView);machineparkViewQueries.otherworks=machineparkViewQueries.otherworks||'';
  const kindFilter=document.getElementById('workKindFilter');if(kindFilter&&!kindFilter.querySelector('option[value="otherworks"]'))kindFilter.insertAdjacentHTML('beforeend','<option value="otherworks">Andere werken</option>');
  const workDrafts=document.getElementById('workDraftPanels');if(workDrafts&&!document.getElementById('otherWorkDraftPanelWork')){const host=document.createElement('div');host.id='otherWorkDraftPanelWork';host.className='other-work-draft-host';workDrafts.appendChild(host)}'''

    new_view = r'''  const workView=document.getElementById('view-work');
  const workToolbarRight=workView?.querySelector('.toolbar-right');
  if(workToolbarRight&&!document.getElementById('workAddOtherWork'))workToolbarRight.insertAdjacentHTML('beforeend','<button class="btn primary" id="workAddOtherWork">+ Andere werken registreren</button>');
  const kindFilter=document.getElementById('workKindFilter');if(kindFilter&&!kindFilter.querySelector('option[value="otherworks"]'))kindFilter.insertAdjacentHTML('beforeend','<option value="otherworks">Andere werken</option>');
  const workDrafts=document.getElementById('workDraftPanels');if(workDrafts&&!document.getElementById('otherWorkDraftPanelWork')){const host=document.createElement('div');host.id='otherWorkDraftPanelWork';host.className='other-work-draft-host';workDrafts.appendChild(host)}'''
    replace_once(old_view, new_view, 'aparte Andere werken-tab vervangen door knop in Werkzaamheden')

    old_navigation = r'''  function openView(){if(!canView())return switchView('dashboard');state.view='otherworks';document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));otherView.classList.add('active');document.querySelectorAll('.nav button').forEach(b=>b.classList.remove('active'));otherNav.classList.add('active');document.getElementById('pageTitle').textContent='Andere werken';document.getElementById('pageSubtitle').textContent='Plaatsingen en andere werkzaamheden met dezelfde registratievelden als een depannage.';const input=document.getElementById('globalSearch'),actions=document.querySelector('.top-actions');if(actions)actions.style.display='';state.query=machineparkViewQueries.otherworks||'';if(input){input.value=state.query;input.placeholder='Zoek in andere werken…'}closeGlobalSearch();renderAll()}
  const baseSwitch=switchView;switchView=function(view){if(view==='otherworks')return openView();otherNav.classList.remove('active');return baseSwitch(view)};window.switchView=switchView;otherNav.onclick=openView;

  function access(){const allowed=canView();otherNav.style.display=allowed?'':'none';const add=document.getElementById('addOtherWork');if(add)add.style.display=allowed&&canAdd()?'':'none';const visible=[...document.querySelectorAll('.nav button')].filter(b=>b.style.display!=='none'&&b.getAttribute('aria-hidden')!=='true').length;document.documentElement.style.setProperty('--mobile-nav-count',String(Math.max(1,visible)));if(state.view==='otherworks'&&!allowed)baseSwitch('dashboard')}
  const baseRole=window.applyMachineparkRoleAccess||applyMachineparkRoleAccess;applyMachineparkRoleAccess=function(){const was=state.view==='otherworks';if(was)state.view='breakdowns';try{baseRole()}finally{if(was&&canView())state.view='otherworks';access()}if(was&&canView()){document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));otherView.classList.add('active');document.querySelectorAll('.nav button').forEach(b=>b.classList.remove('active'));otherNav.classList.add('active')}};window.applyMachineparkRoleAccess=applyMachineparkRoleAccess;
  const baseOperational=window.applyOperationalPermissions||applyOperationalPermissions;applyOperationalPermissions=function(){baseOperational();access()};window.applyOperationalPermissions=applyOperationalPermissions;'''

    new_navigation = r'''  const baseSwitch=switchView;switchView=function(view){const target=view==='otherworks'?'work':view;const result=baseSwitch(target);if(target==='work'){const subtitle=document.getElementById('pageSubtitle');if(subtitle)subtitle.textContent='Onderhoud, depannages en andere werken in één chronologische historiek.'}return result};window.switchView=switchView;

  function applyOtherWorkAccess(){const add=document.getElementById('workAddOtherWork');if(add)add.style.display=canView()&&canAdd()?'':'none'}
  const baseRole=window.applyMachineparkRoleAccess||applyMachineparkRoleAccess;applyMachineparkRoleAccess=function(){baseRole();applyOtherWorkAccess()};window.applyMachineparkRoleAccess=applyMachineparkRoleAccess;
  const baseOperational=window.applyOperationalPermissions||applyOperationalPermissions;applyOperationalPermissions=function(){baseOperational();applyOtherWorkAccess()};window.applyOperationalPermissions=applyOperationalPermissions;'''
    replace_once(old_navigation, new_navigation, 'aparte Andere werken-navigatie verwijderen')

    old_actions = r'''  document.getElementById('addOtherWork').onclick=()=>openOtherWork();['otherWorkTypeFilter','otherWorkStatusFilter','otherWorkPriorityFilter'].forEach(id=>{const input=document.getElementById(id);if(input)input.onchange=renderOtherWorks});
  document.addEventListener('click',e=>{const detail=e.target.closest?.('[data-other-work-details]');if(detail){showDetails(detail.dataset.otherWorkDetails);return}const global=e.target.closest?.('[data-global-other-work]');if(global){closeGlobalSearch();showDetails(global.dataset.globalOtherWork)}});
  access();renderOtherWorks();renderCombined();'''

    new_actions = r'''  const addOtherWork=document.getElementById('workAddOtherWork');if(addOtherWork)addOtherWork.onclick=()=>openOtherWork();
  document.addEventListener('click',e=>{const detail=e.target.closest?.('[data-other-work-details]');if(detail){showDetails(detail.dataset.otherWorkDetails);return}const global=e.target.closest?.('[data-global-other-work]');if(global){closeGlobalSearch();showDetails(global.dataset.globalOtherWork)}});
  applyOtherWorkAccess();renderDrafts();renderCombined();'''
    replace_once(old_actions, new_actions, 'Andere werken-knop koppelen aan Werkzaamheden')

    marker = '\n<script data-machinepark-build-fix="other-works-merged-v1">window.machineparkOtherWorksMergedIntoWork=true;</script>\n'
    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor samengevoegde Andere werken')
    index = index[:pos] + marker + index[pos:]
    index_path.write_text(index, encoding='utf-8')

built = index_path.read_text(encoding='utf-8')
required = [
    MARKER,
    'id="workAddOtherWork"',
    '+ Andere werken registreren',
    "view==='otherworks'?'work':view",
    'Onderhoud, depannages en andere werken in één chronologische historiek.',
    "option value=\"otherworks\"",
    'renderDrafts();renderCombined()',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: samengevoegde Andere werken ontbreekt ({needle})')
for forbidden in ["otherNav=document.createElement('button')", "otherView.id='view-otherworks'", "id=\"addOtherWork\""]:
    if forbidden in built:
        raise SystemExit(f'Buildvalidatie mislukt: aparte Andere werken-tab bleef aanwezig ({forbidden})')

print('[Machinepark] Andere werken volledig samengevoegd in Werkzaamheden zonder apart tabblad')
