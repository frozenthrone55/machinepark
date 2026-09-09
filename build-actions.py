from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SERVICE = ROOT / "service-visits.js"
MARKER = 'data-machinepark-build-fix="actions-v1"'

index = INDEX.read_text(encoding="utf-8")

def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)

if MARKER not in index:
    replace_once(
        "const DB_NAME='KoffieServiceProDB', DB_VERSION=1;",
        "const DB_NAME='KoffieServiceProDB', DB_VERSION=2;",
        "IndexedDB-versie voor Acties",
    )
    replace_once(
        "const stores=['parts','devices','maintenance','breakdowns'];",
        "const stores=['parts','devices','maintenance','breakdowns','actions'];",
        "datastores voor Acties",
    )
    replace_once(
        "let db, state={parts:[],devices:[],maintenance:[],breakdowns:[],view:'dashboard',query:'',deviceSort:{key:'location',dir:'asc'}};",
        "let db, state={parts:[],devices:[],maintenance:[],breakdowns:[],actions:[],view:'dashboard',query:'',deviceSort:{key:'location',dir:'asc'}};",
        "state voor Acties",
    )

    # Handleidingen heeft de basis-schermvolgorde eerder uitgebreid. Voeg Acties
    # pas hier toe, zodat oudere builders hun verwachte anker blijven herkennen.
    allowed_old = "return ['dashboard','devices','maintenance','breakdowns','faults','manuals','parts','settings'].find((view) => hasPermission(viewPermission(view))) || 'dashboard';"
    allowed_new = "return ['dashboard','devices','maintenance','breakdowns','actions','faults','manuals','parts','settings'].find((view) => hasPermission(viewPermission(view))) || 'dashboard';"
    replace_once(allowed_old, allowed_new, "toegestane schermvolgorde voor Acties")

    nav_anchor = """      <button type="button" data-view="maintenance" onclick="switchView('maintenance')"><span class="icon">🔧</span><span class="label">Onderhoud</span></button>"""
    nav_action = nav_anchor + """
      <button type="button" data-view="actions" onclick="switchView('actions')" class="action-nav-button"><span class="icon">✓</span><span class="label">Acties</span><span class="action-nav-count" id="actionNavCount" hidden>0</span></button>"""
    replace_once(nav_anchor, nav_action, "Acties navigatie")

    view_anchor = """    <section class="view" id="view-breakdowns">"""
    action_view = """    <section class="view" id="view-actions">
      <div class="action-quickbar">
        <div class="action-quick-input"><input id="actionQuickInput" type="text" maxlength="180" autocomplete="off" placeholder="Nieuwe actie snel toevoegen…"><button type="button" class="btn primary" id="actionQuickAdd">+ Toevoegen</button></div>
        <button type="button" class="btn" id="actionNewFull">+ Nieuwe actie met details</button>
      </div>
      <div class="action-scope-row"><button type="button" class="action-scope active" data-action-scope="all">Alle acties</button><button type="button" class="action-scope" data-action-scope="mine">Mijn acties</button><button type="button" class="action-scope" data-action-scope="late">Te laat</button></div>
      <section class="action-section action-section-open"><div class="action-section-head"><div><h3>Nog te doen <span id="actionOpenCount" class="action-count-pill">0</span></h3></div></div><div id="actionOpenList" class="action-list"></div></section>
      <section class="action-section action-section-done"><div class="action-section-head"><div><h3>Uitgevoerd <span id="actionDoneCount" class="action-count-pill">0</span></h3></div><button type="button" class="btn small" id="actionShowAllDone" hidden>Alle uitgevoerde acties</button></div><div id="actionDoneList" class="action-list"></div></section>
    </section>

"""
    replace_once(view_anchor, action_view + view_anchor, "Acties view")

    style = r"""
<style data-machinepark-build-fix="actions-v1">
.action-nav-button{position:relative}
.action-nav-count{position:absolute;right:9px;top:9px;min-width:18px;height:18px;padding:0 5px;border-radius:999px;background:#b74646;color:#fff;font-size:10px;font-weight:900;line-height:18px;text-align:center}
.action-quickbar{display:flex;gap:10px;align-items:center;margin-bottom:12px;flex-wrap:wrap}
.action-quick-input{display:flex;gap:8px;flex:1 1 520px}
.action-quick-input input{min-width:0;flex:1;border:1px solid var(--line);border-radius:11px;padding:10px 12px;background:#fff;font:inherit}
.action-scope-row{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px}
.action-scope{border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 11px;font-size:11px;font-weight:800;color:#52615b;cursor:pointer}
.action-scope.active{background:#eaf3ef;color:#164f3e;border-color:#bfd5cc}
.action-section{border:1px solid var(--line);border-radius:14px;background:#fff;overflow:hidden;margin-bottom:14px}
.action-section-head{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:12px 14px;background:#f7faf8;border-bottom:1px solid var(--line)}
.action-section-head h3{margin:0;font-size:15px}
.action-count-pill{display:inline-flex;align-items:center;justify-content:center;min-width:23px;height:21px;padding:0 6px;border-radius:999px;background:#e8efec;color:#355147;font-size:11px;margin-left:5px}
.action-list{display:grid}
.action-card{display:grid;grid-template-columns:6px minmax(0,1fr) auto;gap:12px;padding:13px 14px;border-bottom:1px solid #e7ece9;align-items:start}
.action-card:last-child{border-bottom:0}
.action-priority-bar{width:5px;height:100%;min-height:54px;border-radius:999px;background:#9eaaa5}
.action-card.priority-urgent .action-priority-bar{background:#c34141}
.action-card.priority-normal .action-priority-bar{background:#d18a29}
.action-card.priority-low .action-priority-bar{background:#6d9c88}
.action-card.done .action-priority-bar{background:#75a38f}
.action-card-title{font-size:13px;font-weight:850;color:#24352f;line-height:1.35;overflow-wrap:anywhere}
.action-card-meta{display:flex;gap:6px 12px;flex-wrap:wrap;margin-top:6px;color:var(--muted);font-size:11px}
.action-card-note{margin-top:6px;font-size:11px;color:#586760;line-height:1.45;white-space:pre-wrap;overflow-wrap:anywhere}
.action-card-actions{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.action-photo-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(108px,1fr));gap:9px;margin-top:8px}
.action-photo-item{border:1px solid #dbe5e1;border-radius:11px;background:#f8faf9;padding:7px;overflow:hidden}
.action-photo-item img{display:block;width:100%;height:96px;object-fit:cover;border-radius:8px;background:#eef3f1;cursor:pointer}
.action-photo-item label{display:flex;gap:6px;align-items:center;margin-top:6px;font-size:10.5px;color:#52615b}
.action-photo-item input[type="checkbox"]{width:auto}
.action-photo-editor input[type="file"]{margin-top:9px}
.action-photo-pending{margin-top:9px}
.action-photo-pending .action-photo-grid{margin-top:0}
.action-photo-pending video{display:block;width:100%;height:96px;object-fit:cover;border-radius:8px;background:#111}
.action-photo-pending-remove{margin-top:6px;width:100%}
.action-photo-details{display:grid;grid-template-columns:repeat(auto-fill,minmax(115px,1fr));gap:9px}
.action-photo-details img{display:block;width:100%;height:105px;object-fit:cover;border-radius:10px;border:1px solid #dbe5e1;background:#eef3f1;cursor:pointer}
.action-badge{display:inline-flex;align-items:center;border-radius:999px;padding:3px 7px;font-size:10px;font-weight:850;background:#edf2f0;color:#50615a}
.action-badge.urgent{background:#f9dfdf;color:#9d2929}
.action-badge.late{background:#fff0d9;color:#92590c}
.action-badge.today{background:#fff5c9;color:#755b09}
.action-badge.done{background:#e4f2eb;color:#27614d}
.action-empty{padding:28px 16px;text-align:center;color:var(--muted);font-size:12px}
.action-form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.action-form-grid .field.full{grid-column:1/-1}
.action-form-grid input,.action-form-grid select,.action-form-grid textarea{width:100%;border:1px solid var(--line);border-radius:9px;padding:9px;background:#fff}
.action-form-grid textarea{min-height:92px;resize:vertical}
.action-device-picker{position:relative}
.action-device-suggestions{display:none;position:absolute;z-index:20;left:0;right:0;top:calc(100% + 4px);max-height:230px;overflow:auto;border:1px solid var(--line);border-radius:10px;background:#fff;box-shadow:0 12px 30px rgba(22,54,45,.16)}
.action-device-suggestions.show{display:grid}
.action-device-choice{border:0;border-bottom:1px solid #edf1ef;background:#fff;padding:9px 10px;text-align:left;cursor:pointer}
.action-device-choice:last-child{border-bottom:0}
.action-device-choice strong,.action-device-choice small{display:block}
.action-device-choice small{margin-top:2px;color:var(--muted)}
.action-history{display:grid;gap:7px;margin-top:8px}
.action-history-row{border-left:3px solid #c8d7d1;padding:5px 0 5px 10px}
.action-history-row strong{display:block;font-size:11.5px}
.action-history-row small{display:block;color:var(--muted);font-size:10.5px;margin-top:2px}
.action-device-summary{margin-top:12px;border:1px solid #dbe5e1;border-radius:12px;background:#f8faf9;padding:11px}
.action-device-summary-head{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:8px}
.action-device-summary-list{display:grid;gap:6px}
.action-device-summary-row{display:flex;justify-content:space-between;gap:10px;align-items:center;border-top:1px solid #e5ebe8;padding-top:6px;font-size:11px}
.action-device-summary-row:first-child{border-top:0;padding-top:0}
.kpis.actions-kpis{grid-template-columns:repeat(5,minmax(0,1fr))}
.kpi.action-kpi{cursor:pointer}
.kpi.action-kpi:hover{box-shadow:0 8px 24px rgba(25,57,48,.09)}
@media(max-width:1180px){.kpis.actions-kpis{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:760px){
  .kpis.actions-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
  .action-card{grid-template-columns:5px minmax(0,1fr)}
  .action-card-actions{grid-column:2;justify-content:flex-start}
  .action-form-grid{grid-template-columns:1fr}.action-form-grid .field.full{grid-column:1}
  .action-quick-input{flex-basis:100%}.action-quickbar>#actionNewFull{width:100%}
}
@media(max-width:480px){.kpis.actions-kpis{grid-template-columns:1fr}}
@media print{#view-actions .action-quickbar,#view-actions .action-scope-row,.action-card-actions{display:none!important}}
</style>
"""
    index = index.replace("</head>", style + "</head>", 1)

    script = r"""
<script data-machinepark-build-fix="actions-v1">
(() => {
  const ACTION_USERS_CACHE = 'machinepark-action-users-v1';
  const ACTION_PHOTO_URL = '/machinepark/synology/api/action-photos.php';
  const ACTION_PHOTO_LIMIT = 10;
  let actionUsers = [];
  let actionScope = 'all';
  let showAllDone = false;

  function actionCurrentUser() {
    const user = window.Clerk?.user || {};
    const email = String(user?.primaryEmailAddress?.emailAddress || user?.emailAddresses?.[0]?.emailAddress || '').trim().toLowerCase();
    const name = String(user?.fullName || [user?.firstName,user?.lastName].filter(Boolean).join(' ') || user?.username || email || document.getElementById('accountDisplayName')?.textContent || 'Gebruiker').trim();
    return { id:String(user?.id || email || 'local-user'), name, email };
  }

  function actionUserKey(user) { return String(user?.id || user?.email || '').trim().toLowerCase(); }
  function actionMine(item) {
    const me=actionCurrentUser(), assigneeId=String(item?.assigneeId||'').toLowerCase(), assigneeEmail=String(item?.assigneeEmail||'').toLowerCase();
    return (assigneeId && assigneeId===String(me.id).toLowerCase()) || (assigneeEmail && assigneeEmail===me.email);
  }
  function actionDevice(item) { return (state.devices||[]).find(d=>d.id===item?.deviceId)||null; }
  function actionDeviceLabel(item) {
    const d=actionDevice(item);
    return d ? [d.assetCode||d.model||'Toestel',deviceLocationAt(d)||d.location||''].filter(Boolean).join(' · ') : '';
  }
  function actionDate(value) { return value ? dateFmt(String(value).slice(0,10)) : '—'; }
  function actionPriorityLabel(value) { return ({urgent:'Dringend',normal:'Normaal',low:'Laag'})[value]||'Normaal'; }
  function actionPriorityRank(value) { return value==='urgent'?0:value==='normal'?1:2; }
  function actionDueState(item) {
    if(!item?.dueDate || item.status==='done') return '';
    const today=todayISO();
    if(item.dueDate<today)return 'late';
    if(item.dueDate===today)return 'today';
    return '';
  }
  function actionPersonOption(user,selected='') {
    const id=actionUserKey(user), label=String(user.fullName||user.name||[user.firstName,user.lastName].filter(Boolean).join(' ')||user.email||'Gebruiker');
    return `<option value="${esc(id)}" ${id===selected?'selected':''}>${esc(label)}${user.email?' · '+esc(user.email):''}</option>`;
  }
  function normalizeActionUser(raw={}) {
    const email=String(raw.email||'').trim().toLowerCase();
    return {id:String(raw.id||email||''),email,firstName:String(raw.firstName||''),lastName:String(raw.lastName||''),fullName:String(raw.fullName||raw.name||[raw.firstName,raw.lastName].filter(Boolean).join(' ')||email||'Gebruiker'),role:String(raw.role||'')};
  }
  function ensureCurrentActionUser(list=[]) {
    const me=actionCurrentUser(), result=list.map(normalizeActionUser);
    if(!result.some(u=>actionUserKey(u)===String(me.id).toLowerCase() || (me.email&&u.email===me.email))) result.unshift(normalizeActionUser({id:me.id,email:me.email,fullName:me.name}));
    return result;
  }
  function readActionUsersCache() {
    try { const list=JSON.parse(localStorage.getItem(ACTION_USERS_CACHE)||'[]'); return Array.isArray(list)?ensureCurrentActionUser(list):ensureCurrentActionUser([]); } catch(_) { return ensureCurrentActionUser([]); }
  }
  async function loadActionUsers(force=false) {
    if(!actionUsers.length) actionUsers=readActionUsersCache();
    if(!navigator.onLine && !force)return actionUsers;
    try {
      const headers=typeof centralHeaders==='function'?await centralHeaders(false):{};
      const response=await fetch('/machinepark/synology/api/action-users.php',{headers,cache:'no-store',credentials:'same-origin'});
      if(!response.ok)throw new Error('HTTP '+response.status);
      const body=await response.json();
      actionUsers=ensureCurrentActionUser(Array.isArray(body.users)?body.users:[]);
      try{localStorage.setItem(ACTION_USERS_CACHE,JSON.stringify(actionUsers));}catch(_){}
    } catch(error) {
      console.warn('Actiegebruikers laden',error);
      actionUsers=readActionUsersCache();
    }
    return actionUsers;
  }

  function historyEntry(type,label,detail='') {
    const me=actionCurrentUser();
    return {id:uid('actlog'),at:new Date().toISOString(),type,label,detail,byId:me.id,byName:me.name,byEmail:me.email};
  }
  function appendActionHistory(item,entry) {
    return [...(Array.isArray(item?.history)?item.history:[]),entry].slice(-120);
  }

  function actionMatches(item) {
    if(actionScope==='mine'&&!actionMine(item))return false;
    if(actionScope==='late'&&!(item.status!=='done'&&actionDueState(item)==='late'))return false;
    const q=String(state.query||'').trim().toLowerCase();
    if(!q)return true;
    return [item.title,item.notes,item.location,item.assigneeName,item.assigneeEmail,item.completionNote,item.completedByName,actionDeviceLabel(item),item.sourceLabel].join(' ').toLowerCase().includes(q);
  }
  function actionOpenSort(a,b) {
    const priority=actionPriorityRank(a.priority)-actionPriorityRank(b.priority);if(priority)return priority;
    const ad=a.dueDate||'9999-12-31',bd=b.dueDate||'9999-12-31';if(ad!==bd)return ad.localeCompare(bd);
    return String(b.updatedAt||b.createdAt||'').localeCompare(String(a.updatedAt||a.createdAt||''));
  }
  function actionDoneSort(a,b) { return String(b.completedAt||b.updatedAt||'').localeCompare(String(a.completedAt||a.updatedAt||'')); }

  function actionPhotoList(value) {
    const seen=new Set(),out=[];
    for(const src of Array.isArray(value)?value:[]){
      if(typeof src!=='string'||!src.trim())continue;
      const clean=src.trim();
      if(seen.has(clean))continue;
      seen.add(clean);out.push(clean);
      if(out.length>=ACTION_PHOTO_LIMIT)break;
    }
    return out;
  }
  function actionPhotoPreview(src) {
    const value=String(src||'').trim();
    if(!value||value.startsWith('data:image/'))return value;
    try{
      const url=new URL(value,location.origin);
      url.searchParams.set('variant','thumb');
      return url.pathname+'?'+url.searchParams.toString();
    }catch(_){return value;}
  }
  function actionPhotoGridHtml(photos=[],editable=false) {
    const list=actionPhotoList(photos);
    if(!list.length)return editable?'<div class="muted">Nog geen foto’s toegevoegd.</div>':'<div class="muted">Geen foto’s bij deze ToDo.</div>';
    if(!editable)return '<div class="action-photo-details">'+list.map((src,i)=>'<img src="'+esc(actionPhotoPreview(src))+'" data-full-src="'+esc(src)+'" data-photo-lightbox loading="lazy" decoding="async" alt="ToDo-foto '+(i+1)+'">').join('')+'</div>';
    return '<div class="action-photo-grid">'+list.map((src,i)=>'<div class="action-photo-item"><img src="'+esc(actionPhotoPreview(src))+'" data-full-src="'+esc(src)+'" data-photo-lightbox loading="lazy" decoding="async" alt="ToDo-foto '+(i+1)+'"><label><input type="checkbox" class="action-photo-remove" value="'+i+'"> Verwijderen</label></div>').join('')+'</div>';
  }
  function actionPhotoEditorHtml(photos=[]) {
    return '<div class="field full action-photo-editor"><label>Foto’s bij ToDo <span class="muted">(optioneel)</span></label>'+actionPhotoGridHtml(photos,true)+'<input class="action-photo-files" type="file" accept="image/*" multiple><div class="action-photo-pending"></div><div class="action-photo-count muted" style="font-size:11px;margin-top:4px"></div><div class="muted" style="font-size:11px;margin-top:2px">Maximaal '+ACTION_PHOTO_LIMIT+' foto’s per ToDo.</div></div>';
  }
  function actionExistingKeptCount(editor) {
    const existing=[...editor.querySelectorAll('.action-photo-remove')];
    return existing.filter(input=>!input.checked).length;
  }
  function renderActionPendingMedia(editor) {
    const holder=editor?.querySelector('.action-photo-pending');
    const count=editor?.querySelector('.action-photo-count');
    if(!holder)return;
    const files=Array.isArray(editor.__actionPendingFiles)?editor.__actionPendingFiles:[];
    const oldUrls=Array.isArray(editor.__actionPendingUrls)?editor.__actionPendingUrls:[];
    oldUrls.forEach(url=>{try{URL.revokeObjectURL(url);}catch(_){ }});
    const urls=[];
    holder.innerHTML='';
    if(files.length){
      const grid=document.createElement('div');grid.className='action-photo-grid';
      files.forEach((file,index)=>{
        const url=URL.createObjectURL(file);urls.push(url);
        const item=document.createElement('div');item.className='action-photo-item action-photo-pending-item';
        const isVideo=String(file.type||'').startsWith('video/')||/\.(mp4|webm|mov|m4v)$/i.test(String(file.name||''));
        const media=document.createElement(isVideo?'video':'img');
        media.src=url;
        if(isVideo){media.controls=true;media.playsInline=true;media.preload='metadata';}
        else{media.loading='lazy';media.decoding='async';}
        media.setAttribute('aria-label',isVideo?'Nieuwe ToDo-video':'Nieuwe ToDo-foto');
        const remove=document.createElement('button');remove.type='button';remove.className='btn small action-photo-pending-remove';remove.textContent='Verwijderen';
        remove.onclick=()=>{
          const next=[...(editor.__actionPendingFiles||[])];next.splice(index,1);editor.__actionPendingFiles=next;renderActionPendingMedia(editor);
        };
        item.append(media,remove);grid.appendChild(item);
      });
      holder.appendChild(grid);
    }
    editor.__actionPendingUrls=urls;
    if(count){
      const total=actionExistingKeptCount(editor)+files.length;
      count.textContent=total+' van maximaal '+ACTION_PHOTO_LIMIT+' foto’s geselecteerd';
    }
  }
  function initActionPhotoEditor() {
    const editor=document.querySelector('#modal .action-photo-editor');
    if(!editor||editor.dataset.previewReady==='1')return;
    editor.dataset.previewReady='1';
    editor.__actionPendingFiles=[];
    editor.__actionPendingUrls=[];
    const input=editor.querySelector('.action-photo-files');
    if(input)input.addEventListener('change',()=>{
      const chosen=[...(input.files||[])].filter(file=>file&&file.size);
      const current=[...(editor.__actionPendingFiles||[])];
      const kept=actionExistingKeptCount(editor);
      const available=Math.max(0,ACTION_PHOTO_LIMIT-kept-current.length);
      if(chosen.length>available)alert('Je kunt nog maximaal '+available+' foto'+(available===1?'':'’s')+' toevoegen. Een ToDo kan maximaal '+ACTION_PHOTO_LIMIT+' foto’s bevatten.');
      editor.__actionPendingFiles=[...current,...chosen.slice(0,available)];
      input.value='';
      renderActionPendingMedia(editor);
    });
    editor.addEventListener('change',event=>{if(event.target?.classList?.contains('action-photo-remove'))renderActionPendingMedia(editor);});
    renderActionPendingMedia(editor);
  }

  async function actionPhotoPost(body) {
    const headers=typeof centralHeaders==='function'?await centralHeaders(true):{'Content-Type':'application/json'};
    if(!headers['Content-Type'])headers['Content-Type']='application/json';
    const response=await fetch(ACTION_PHOTO_URL,{method:'POST',headers,body:JSON.stringify(body),cache:'no-store',credentials:'same-origin'});
    const text=await response.text();
    let data={};try{data=text?JSON.parse(text):{};}catch(_){}
    if(!response.ok)throw new Error(data.error||text||('ToDo-foto’s opslaan mislukt ('+response.status+')'));
    return data;
  }
  window.machineparkPersistActionPhotos=async function(actionId,photos) {
    const list=actionPhotoList(photos);
    const body=await actionPhotoPost({actionId,photos:list,completeList:true});
    return actionPhotoList(Array.isArray(body.photos)?body.photos:list);
  };
  async function collectActionPhotos(existing=[],actionId='') {
    const editor=document.querySelector('#modal .action-photo-editor');
    const current=actionPhotoList(existing);
    if(!editor)return current;
    const remove=new Set([...editor.querySelectorAll('.action-photo-remove:checked')].map(x=>Number(x.value)).filter(Number.isFinite));
    const kept=current.filter((_,i)=>!remove.has(i));
    const files=Array.isArray(editor.__actionPendingFiles)?editor.__actionPendingFiles:[...(editor.querySelector('.action-photo-files')?.files||[])].filter(file=>file&&file.size);
    if(kept.length+files.length>ACTION_PHOTO_LIMIT)throw new Error('Maximaal '+ACTION_PHOTO_LIMIT+' foto’s per ToDo.');
    if(!remove.size&&!files.length)return current;
    if(navigator.onLine===false)throw new Error('Foto’s toevoegen of verwijderen bij een ToDo vereist tijdelijk een internetverbinding.');
    const added=[];
    for(const file of files)added.push(await compressImage(file));
    return await window.machineparkPersistActionPhotos(String(actionId),[...kept,...added]);
  }

  function actionCard(item,done=false) {
    const due=actionDueState(item),device=actionDeviceLabel(item),priority=item.priority||'normal';
    const badges=[
      `<span class="action-badge ${priority==='urgent'?'urgent':''}">${esc(actionPriorityLabel(priority))}</span>`,
      due==='late'?'<span class="action-badge late">Te laat</span>':due==='today'?'<span class="action-badge today">Vandaag</span>':'',
      done?'<span class="action-badge done">✓ Uitgevoerd</span>':''
    ].filter(Boolean).join(' ');
    const meta=[
      item.assigneeName?`Toegewezen aan: ${esc(item.assigneeName)}`:'',
      item.dueDate?`Tegen: ${actionDate(item.dueDate)}`:'',
      device?esc(device):(item.location?esc(item.location):''),
      actionPhotoList(item.photos).length?'📷 '+actionPhotoList(item.photos).length:'',
      done&&item.completedByName?`Uitgevoerd door: ${esc(item.completedByName)}`:'',
      done&&item.completedDate?`${actionDate(item.completedDate)}`:''
    ].filter(Boolean).map(x=>`<span>${x}</span>`).join('');
    const buttons=done
      ? `<button class="btn small" type="button" data-action-open="${esc(item.id)}">Bekijken</button>`
      : `<button class="btn small" type="button" data-action-open="${esc(item.id)}">Openen</button>${item.deviceId?'':`<button class="btn small" type="button" data-action-link="${esc(item.id)}">Koppelen</button>`}<button class="btn small primary" type="button" data-action-complete="${esc(item.id)}">✓ Afronden</button>`;
    return `<article class="action-card ${done?'done':''} priority-${esc(priority)}"><div class="action-priority-bar"></div><div><div>${badges}</div><div class="action-card-title" style="margin-top:6px">${esc(item.title||'Actie')}</div><div class="action-card-meta">${meta}</div>${item.notes?`<div class="action-card-note">${esc(item.notes)}</div>`:''}</div><div class="action-card-actions">${buttons}</div></article>`;
  }

  function renderActionDashboard() {
    const all=Array.isArray(state.actions)?state.actions:[],open=all.filter(a=>a.status!=='done'),mine=open.filter(actionMine);
    let kpi=document.getElementById('kpiActionsCard');
    if(!kpi){
      const box=document.querySelector('#view-dashboard .kpis');
      if(box){
        box.classList.add('actions-kpis');
        box.insertAdjacentHTML('beforeend','<div class="kpi action-kpi" id="kpiActionsCard" role="button" tabindex="0"><span class="dot" style="background:#4d806e"></span><div class="label">Open acties</div><div class="value" id="kpiActions">0</div><div class="hint" id="kpiActionsHint">0 voor jou</div></div>');
        kpi=document.getElementById('kpiActionsCard');
        const go=()=>{actionScope='mine';if(typeof switchView==='function')switchView('actions');};
        kpi?.addEventListener('click',go);kpi?.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go();}});
      }
    }
    const value=document.getElementById('kpiActions'),hint=document.getElementById('kpiActionsHint');
    if(value)value.textContent=String(open.length);if(hint)hint.textContent=`${mine.length} voor jou`;
    const nav=document.getElementById('actionNavCount');
    if(nav){nav.textContent=String(mine.length);nav.hidden=mine.length===0;}
  }

  function renderActions() {
    if(!Array.isArray(state.actions))state.actions=[];
    const input=document.getElementById('globalSearch');if(state.view==='actions'&&input)input.placeholder='Zoek in acties…';
    document.querySelectorAll('[data-action-scope]').forEach(btn=>btn.classList.toggle('active',btn.dataset.actionScope===actionScope));
    const filtered=state.actions.filter(actionMatches),open=filtered.filter(a=>a.status!=='done').sort(actionOpenSort),allDone=filtered.filter(a=>a.status==='done').sort(actionDoneSort);
    const cutoff=Date.now()-30*86400000;
    const recentDone=showAllDone?allDone:allDone.filter(a=>{const t=new Date(a.completedAt||a.updatedAt||0).getTime();return Number.isFinite(t)&&t>=cutoff;});
    const openBox=document.getElementById('actionOpenList'),doneBox=document.getElementById('actionDoneList');
    if(openBox)openBox.innerHTML=open.length?open.map(x=>actionCard(x,false)).join(''):'<div class="action-empty">Geen openstaande acties.</div>';
    if(doneBox)doneBox.innerHTML=recentDone.length?recentDone.map(x=>actionCard(x,true)).join(''):'<div class="action-empty">Nog geen uitgevoerde acties in deze periode.</div>';
    const oc=document.getElementById('actionOpenCount'),dc=document.getElementById('actionDoneCount'),show=document.getElementById('actionShowAllDone');
    if(oc)oc.textContent=String(open.length);if(dc)dc.textContent=String(allDone.length);
    if(show){show.hidden=showAllDone||recentDone.length===allDone.length;show.textContent=`Alle uitgevoerde acties (${allDone.length})`;}
    renderActionDashboard();
  }
  window.machineparkRenderActions=renderActions;

  function actionDeviceSearchField(selectedId='') {
    const d=(state.devices||[]).find(x=>x.id===selectedId),display=d?[d.assetCode||d.model||'Toestel',deviceLocationAt(d)||d.location||'',d.brand||'',d.model||''].filter(Boolean).join(' · '):'';
    return `<div class="field full"><label>Koppelen aan toestel <span class="muted">(optioneel)</span></label><div class="action-device-picker"><input type="search" class="action-device-search" autocomplete="off" placeholder="Zoek op toestelnummer, locatie, merk of model…" value="${esc(display)}"><input type="hidden" name="deviceId" class="action-device-id" value="${esc(selectedId)}"><div class="action-device-suggestions"></div></div></div>`;
  }
  function actionDeviceMatches(query) {
    const q=String(query||'').trim().toLowerCase();if(!q)return [];
    return (state.devices||[]).filter(d=>[d.assetCode,d.serial,d.brand,d.model,deviceLocationAt(d),d.location].join(' ').toLowerCase().includes(q)).sort((a,b)=>String(a.assetCode||'').localeCompare(String(b.assetCode||''),'nl',{numeric:true})).slice(0,12);
  }
  function initActionDeviceSearch(selectedId='') {
    const input=document.querySelector('.action-device-search'),hidden=document.querySelector('.action-device-id'),box=document.querySelector('.action-device-suggestions');if(!input||!hidden||!box)return;
    const hide=()=>box.classList.remove('show');
    const show=()=>{const list=actionDeviceMatches(input.value);box.innerHTML=list.length?list.map(d=>`<button type="button" class="action-device-choice" data-action-device-choice="${esc(d.id)}"><strong>${esc(d.assetCode||d.model||'Toestel')}</strong><small>${esc([deviceLocationAt(d)||d.location,d.brand,d.model,d.serial&&'S/N '+d.serial].filter(Boolean).join(' · '))}</small></button>`).join(''):'<div class="action-empty" style="padding:10px">Geen toestel gevonden.</div>';box.classList.add('show');};
    input.addEventListener('input',()=>{hidden.value='';if(input.value.trim())show();else hide();});
    input.addEventListener('focus',()=>{if(input.value.trim()&&!hidden.value)show();});
    box.addEventListener('click',e=>{const btn=e.target.closest('[data-action-device-choice]');if(!btn)return;const d=(state.devices||[]).find(x=>x.id===btn.dataset.actionDeviceChoice);if(!d)return;hidden.value=d.id;input.value=[d.assetCode||d.model||'Toestel',deviceLocationAt(d)||d.location||'',d.brand||'',d.model||''].filter(Boolean).join(' · ');const location=document.querySelector('[name="location"]');if(location&&!location.value)location.value=deviceLocationAt(d)||d.location||'';hide();});
    input.addEventListener('focusout',()=>setTimeout(hide,160));
  }

  function assigneeSelect(selected='') {
    const me=actionCurrentUser(), users=ensureCurrentActionUser(actionUsers.length?actionUsers:readActionUsersCache());
    const key=selected||String(me.id).toLowerCase();
    return `<select name="assigneeKey">${users.map(u=>actionPersonOption(u,key)).join('')}</select>`;
  }
  function selectedAssignee(key) {
    const users=ensureCurrentActionUser(actionUsers.length?actionUsers:readActionUsersCache()),normalized=String(key||'').toLowerCase();
    const u=users.find(x=>actionUserKey(x)===normalized)||users[0]||normalizeActionUser(actionCurrentUser());
    return {id:String(u.id||u.email||''),email:String(u.email||'').toLowerCase(),name:String(u.fullName||u.email||'Gebruiker')};
  }

  async function openActionEditor(id='',context={}) {
    await loadActionUsers();
    const old=(state.actions||[]).find(a=>a.id===id)||{},actionId=old.id||uid('action'),deviceId=context.deviceId!==undefined?context.deviceId:(old.deviceId||''),sourceLabel=context.sourceLabel||old.sourceLabel||'';
    const currentAssignee=String(old.assigneeId||old.assigneeEmail||'').toLowerCase();
    const body=`<div class="action-form-grid"><div class="field full"><label>Actie *</label><input name="title" maxlength="180" required value="${esc(context.title||old.title||'')}"></div><div class="field"><label>Toewijzen aan</label>${assigneeSelect(currentAssignee)}</div><div class="field"><label>Prioriteit</label><select name="priority"><option value="low" ${old.priority==='low'?'selected':''}>Laag</option><option value="normal" ${!old.priority||old.priority==='normal'?'selected':''}>Normaal</option><option value="urgent" ${old.priority==='urgent'?'selected':''}>Dringend</option></select></div><div class="field"><label>Tegen wanneer <span class="muted">(optioneel)</span></label><input name="dueDate" type="date" value="${esc(old.dueDate||'')}"></div><div class="field"><label>Locatie <span class="muted">(optioneel)</span></label><input name="location" maxlength="160" value="${esc(context.location!==undefined?context.location:(old.location||''))}"></div>${actionDeviceSearchField(deviceId)}<div class="field full"><label>Opmerking <span class="muted">(optioneel)</span></label><textarea name="notes" maxlength="1500">${esc(old.notes||'')}</textarea></div>${actionPhotoEditorHtml(old.photos||[])}${sourceLabel?`<div class="field full"><div class="alert"><strong>Gekoppelde bron</strong>${esc(sourceLabel)}</div></div>`:''}</div>`;
    showModal(id?'Actie bewerken':'Nieuwe actie',body,'Actie opslaan',async fd=>{
      const title=val(fd,'title');if(!title)throw new Error('Vul een actie in.');
      const assignee=selectedAssignee(val(fd,'assigneeKey')),now=new Date().toISOString(),me=actionCurrentUser(),newDeviceId=val(fd,'deviceId'),device=(state.devices||[]).find(d=>d.id===newDeviceId),location=val(fd,'location')||(device?(deviceLocationAt(device)||device.location||''):'');
      const photos=await collectActionPhotos(old.photos||[],actionId);
      let history=Array.isArray(old.history)?old.history:[];
      if(!id)history=appendActionHistory(old,historyEntry('created','Actie aangemaakt',`Toegewezen aan ${assignee.name}`));
      else {
        const changes=[];
        if(old.assigneeId!==assignee.id||old.assigneeEmail!==assignee.email)changes.push(`toegewezen aan ${assignee.name}`);
        if((old.deviceId||'')!==newDeviceId)changes.push(newDeviceId?`gekoppeld aan ${device?.assetCode||'toestel'}`:'toestelkoppeling verwijderd');
        if(old.title!==title)changes.push('omschrijving gewijzigd');
        if(changes.length)history=appendActionHistory(old,historyEntry('edited','Actie gewijzigd',changes.join(' · ')));
      }
      const obj={...old,id:actionId,title,notes:val(fd,'notes'),priority:val(fd,'priority')||'normal',dueDate:val(fd,'dueDate'),location,deviceId:newDeviceId,assigneeId:assignee.id,assigneeName:assignee.name,assigneeEmail:assignee.email,photos,status:old.status||'open',sourceKind:context.sourceKind||old.sourceKind||'',sourceId:context.sourceId||old.sourceId||'',sourceLabel:sourceLabel,createdAt:old.createdAt||now,createdById:old.createdById||me.id,createdByName:old.createdByName||me.name,createdByEmail:old.createdByEmail||me.email,updatedAt:now,history};
      await put('actions',obj);closeModal();await refresh();toast(id?'Actie bijgewerkt':'Actie toegevoegd');
    });
    setTimeout(()=>{initActionDeviceSearch(deviceId);initActionPhotoEditor();document.querySelector('#modal [name="title"]')?.focus();},0);
  }
  window.machineparkOpenActionEditor=openActionEditor;

  async function quickAddAction() {
    const input=document.getElementById('actionQuickInput'),title=String(input?.value||'').trim();if(!title){input?.focus();return;}
    const me=actionCurrentUser(),now=new Date().toISOString(),obj={id:uid('action'),title,notes:'',priority:'normal',dueDate:'',location:'',deviceId:'',assigneeId:me.id,assigneeName:me.name,assigneeEmail:me.email,photos:[],status:'open',sourceKind:'',sourceId:'',sourceLabel:'',createdAt:now,createdById:me.id,createdByName:me.name,createdByEmail:me.email,updatedAt:now,history:[historyEntry('created','Actie snel aangemaakt',`Toegewezen aan ${me.name}`)]};
    await put('actions',obj);if(input)input.value='';await refresh();toast('Actie toegevoegd');
  }

  async function openCompleteAction(id) {
    await loadActionUsers();
    const item=(state.actions||[]).find(a=>a.id===id);if(!item)return;
    const me=actionCurrentUser(),selected=String(me.id||me.email).toLowerCase();
    const body=`<div class="action-form-grid"><div class="field full"><div class="alert"><strong>Actie afronden</strong>${esc(item.title)}</div></div><div class="field"><label>Datum uitgevoerd</label><input type="date" name="completedDate" required value="${todayISO()}"></div><div class="field"><label>Uitgevoerd door</label>${assigneeSelect(selected)}</div>${item.deviceId?'':actionDeviceSearchField('')}<div class="field full"><label>Opmerking bij uitvoering <span class="muted">(optioneel)</span></label><textarea name="completionNote" maxlength="1500"></textarea></div></div>`;
    showModal('Actie afronden',body,'Bevestig afronden',async fd=>{
      const by=selectedAssignee(val(fd,'assigneeKey')),newDeviceId=item.deviceId||val(fd,'deviceId'),device=(state.devices||[]).find(d=>d.id===newDeviceId),now=new Date().toISOString(),completedDate=val(fd,'completedDate')||todayISO(),detail=[`Uitgevoerd door ${by.name}`,device?`toestel ${device.assetCode||device.model||''}`:''].filter(Boolean).join(' · ');
      const updated={...item,status:'done',deviceId:newDeviceId,location:item.location||(device?(deviceLocationAt(device)||device.location||''):''),completedDate,completedAt:now,completedById:by.id,completedByName:by.name,completedByEmail:by.email,completionNote:val(fd,'completionNote'),updatedAt:now,history:appendActionHistory(item,historyEntry('completed','Actie uitgevoerd',detail))};
      await put('actions',updated);closeModal();await refresh();toast('Actie uitgevoerd');
    });
    setTimeout(()=>initActionDeviceSearch(item.deviceId||''),0);
  }

  async function reopenAction(id) {
    const item=(state.actions||[]).find(a=>a.id===id);if(!item||!confirm('Deze uitgevoerde actie opnieuw bij Nog te doen plaatsen?'))return;
    const updated={...item,status:'open',completedDate:'',completedAt:'',completedById:'',completedByName:'',completedByEmail:'',completionNote:'',updatedAt:new Date().toISOString(),history:appendActionHistory(item,historyEntry('reopened','Actie heropend'))};
    await put('actions',updated);await refresh();toast('Actie opnieuw geopend');
  }

  async function pushActionDeletionNow(id) {
    if(!centralSync?.enabled||navigator.onLine===false)return false;
    const pushNow=async()=>{
      clearTimeout(centralSync.pushTimer);
      centralSync.pushTimer=null;
      centralSync.pending=true;
      await centralPush();
    };
    try{
      await pushNow();
      return true;
    }catch(firstError){
      // machinepark-action-delete-one-click-v1
      // Een 409-pull kan de zonet verwijderde ToDo lokaal opnieuw binnenhalen.
      // De gebruiker heeft de verwijdering al bevestigd: verwijder die record
      // automatisch opnieuw en push nog één keer met de verse centrale etag.
      const restored=(await getAll('actions')).some(action=>String(action?.id||'')===String(id));
      if(restored){
        await del('actions',id);
        try{
          await pushNow();
          return true;
        }catch(secondError){
          console.warn('ToDo-verwijdering wacht op centrale synchronisatie',secondError);
          scheduleCentralSync();
          return false;
        }
      }
      console.warn('ToDo-verwijdering lokaal uitgevoerd; centrale synchronisatie wordt opnieuw geprobeerd',firstError);
      scheduleCentralSync();
      return false;
    }
  }

  async function deleteAction(id) {
    const item=(state.actions||[]).find(a=>a.id===id);if(!item)return;
    const linked=actionDeviceLabel(item);
    const message=`Actie “${item.title||'Actie'}” definitief verwijderen?${linked?`\n\nDe koppeling met ${linked} verdwijnt eveneens.`:''}\n\nDeze verwijdering wordt centraal gesynchroniseerd.`;
    if(!confirm(message))return;
    try{
      // Eerst de ToDo-record verwijderen. Media-opruiming mag de recorddelete nooit blokkeren.
      await del('actions',item.id);
      await pushActionDeletionNow(item.id);
      if(navigator.onLine!==false&&typeof window.machineparkPersistActionPhotos==='function'&&actionPhotoList(item.photos).length){
        try{await window.machineparkPersistActionPhotos(item.id,[]);}
        catch(error){console.warn('ToDo-foto’s/video’s opruimen',error);}
      }
      closeModal();
      await refresh();
      toast('Actie verwijderd');
    }catch(error){
      console.error('Actie verwijderen',error);
      alert(error?.message||'Actie verwijderen mislukt.');
    }
  }

  function actionHistoryHtml(item) {
    const linkedServiceIds=new Set([
      ...(Array.isArray(item.serviceReportIds)?item.serviceReportIds:[]),
      ...(Array.isArray(item.serviceLinks)?item.serviceLinks.map(link=>link&&link.id):[]),
      item.sourceKind==='service-report'?item.sourceId:''
    ].filter(Boolean).map(String));
    const existingDraftReportIds=new Set(
      [...(state.maintenance||[]),...(state.breakdowns||[])]
        .filter(record=>record&&record.isDraft===true&&record.draftKind==='serviceVisit'&&record.draftRole==='header'&&record.draftReportId)
        .map(record=>String(record.draftReportId))
    );
    const activeDraftServiceIds=new Set([...linkedServiceIds].filter(id=>existingDraftReportIds.has(id)));
    const rows=[...(Array.isArray(item.history)?item.history:[])].filter(entry=>{
      const label=String(entry&&entry.label||'').toLowerCase();
      const isConcept=label.includes('serviceconcept');
      if(!isConcept)return true;
      if(entry&&entry.serviceReportId)return existingDraftReportIds.has(String(entry.serviceReportId));
      return activeDraftServiceIds.size>0;
    }).sort((a,b)=>String(b.at||'').localeCompare(String(a.at||'')));
    return rows.length?`<div class="action-history">${rows.map(h=>`<div class="action-history-row"><strong>${esc(h.label||h.type||'Wijziging')}</strong><small>${esc(h.byName||'Gebruiker')} · ${h.at?esc(new Date(h.at).toLocaleString('nl-BE')):''}${h.detail?' · '+esc(h.detail):''}</small></div>`).join('')}</div>`:'<div class="muted">Nog geen historiek.</div>';
  }
  function actionPrintStatus(item) {
    return item?.status==='done'?'Uitgevoerd':item?.status==='in_progress'?'In behandeling':'Nog te doen';
  }
  function actionPrintPhotoList(item) {
    return actionPhotoList(item?.photos||[]).filter(src=>!(typeof window.machineparkIsVideoMedia==='function'&&window.machineparkIsVideoMedia(src)));
  }
  function actionPrintHtml(item) {
    const device=actionDeviceLabel(item),photos=actionPrintPhotoList(item),history=actionHistoryHtml(item);
    const photoHtml=photos.length?'<section><h2>Foto’s</h2><div class="print-photo-grid">'+photos.map((src,i)=>'<img src="'+esc(src)+'" alt="ToDo-foto '+(i+1)+'">').join('')+'</div></section>':'';
    const done=item.status==='done'?'<div class="print-field"><span>Uitgevoerd door</span><strong>'+esc(item.completedByName||'—')+'</strong></div><div class="print-field"><span>Uitgevoerd op</span><strong>'+actionDate(item.completedDate)+'</strong></div><div class="print-field full"><span>Opmerking uitvoering</span><strong>'+esc(item.completionNote||'—')+'</strong></div>':'';
    return '<!doctype html><html><head><meta charset="utf-8"><title>ToDo - '+esc(item.title||'ToDo')+'</title><style>'+
      '@page{size:A4;margin:15mm}body{font-family:Arial,sans-serif;color:#18211e;margin:0;font-size:11pt}h1{margin:0 0 3mm;font-size:22pt}h2{font-size:13pt;margin:7mm 0 3mm;border-bottom:1px solid #ccd7d2;padding-bottom:2mm}.meta{display:grid;grid-template-columns:1fr 1fr;gap:4mm 7mm;margin-top:6mm}.print-field{border:1px solid #d9e1de;border-radius:3mm;padding:3mm}.print-field.full{grid-column:1/-1}.print-field span{display:block;font-size:8.5pt;color:#5c6863;text-transform:uppercase;font-weight:700;margin-bottom:1mm}.print-field strong{display:block;white-space:pre-wrap}.status{display:inline-block;padding:1.5mm 3mm;border:1px solid #b9c9c3;border-radius:999px;font-weight:700}.notes{white-space:pre-wrap;border-left:3px solid #c8d7d1;padding-left:3mm;margin-top:4mm}.print-photo-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4mm}.print-photo-grid img{width:100%;height:70mm;object-fit:contain;border:1px solid #d9e1de;border-radius:2mm;background:#fff}.action-history{display:grid;gap:2mm}.action-history-row{border-left:3px solid #c8d7d1;padding:1.5mm 0 1.5mm 3mm}.action-history-row strong{display:block}.action-history-row small{display:block;color:#5c6863;margin-top:1mm}.muted{color:#5c6863}@media print{button{display:none}}</style></head><body>'+
      '<div class="status">'+esc(actionPrintStatus(item))+'</div><h1>'+esc(item.title||'ToDo')+'</h1>'+
      (item.notes?'<div class="notes">'+esc(item.notes)+'</div>':'')+
      '<div class="meta"><div class="print-field"><span>Prioriteit</span><strong>'+esc(actionPriorityLabel(item.priority))+'</strong></div><div class="print-field"><span>Toegewezen aan</span><strong>'+esc(item.assigneeName||'—')+'</strong></div><div class="print-field"><span>Tegen wanneer</span><strong>'+actionDate(item.dueDate)+'</strong></div><div class="print-field"><span>Locatie</span><strong>'+esc(item.location||'—')+'</strong></div><div class="print-field"><span>Toestel</span><strong>'+esc(device||'—')+'</strong></div>'+(item.sourceLabel?'<div class="print-field"><span>Bron</span><strong>'+esc(item.sourceLabel)+'</strong></div>':'')+done+'</div>'+
      photoHtml+'<section><h2>Historiek</h2>'+history+'</section></body></html>';
  }
  function printAction(id) {
    const item=(state.actions||[]).find(a=>a.id===id);if(!item)return;
    const printWindow=window.open('','_blank');
    if(!printWindow){alert('Sta pop-ups toe om de ToDo af te drukken.');return;}
    printWindow.document.open();
    printWindow.document.write(actionPrintHtml(item));
    printWindow.document.close();
    const images=[...printWindow.document.images];
    const finish=()=>setTimeout(()=>{try{printWindow.focus();printWindow.print();}catch(_){}},120);
    if(!images.length){finish();return;}
    let pending=images.length;
    const done=()=>{pending-=1;if(pending<=0)finish();};
    images.forEach(img=>{if(img.complete)done();else{img.onload=done;img.onerror=done;}});
    setTimeout(()=>{if(pending>0)finish();},1800);
  }

  function openActionDetails(id) {
    const item=(state.actions||[]).find(a=>a.id===id);if(!item)return;const device=actionDeviceLabel(item);
    const body=`<div class="action-form-grid"><div class="field full"><div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><span class="action-badge ${item.priority==='urgent'?'urgent':''}">${esc(actionPriorityLabel(item.priority))}</span>${item.status==='done'?'<span class="action-badge done">✓ Uitgevoerd</span>':''}</div><h3 style="margin:9px 0 3px">${esc(item.title)}</h3>${item.notes?`<div class="muted" style="white-space:pre-wrap">${esc(item.notes)}</div>`:''}</div><div class="field"><label>Toegewezen aan</label><strong>${esc(item.assigneeName||'—')}</strong></div><div class="field"><label>Tegen wanneer</label><strong>${actionDate(item.dueDate)}</strong></div><div class="field"><label>Locatie</label><strong>${esc(item.location||'—')}</strong></div><div class="field"><label>Toestel</label><strong>${esc(device||'—')}</strong></div>${item.sourceLabel?`<div class="field full"><label>Bron</label><strong>${esc(item.sourceLabel)}</strong></div>`:''}<div class="field full"><label>Foto’s</label>${actionPhotoGridHtml(item.photos||[],false)}</div>${item.status==='done'?`<div class="field"><label>Uitgevoerd door</label><strong>${esc(item.completedByName||'—')}</strong></div><div class="field"><label>Uitgevoerd op</label><strong>${actionDate(item.completedDate)}</strong></div><div class="field full"><label>Opmerking uitvoering</label><div>${esc(item.completionNote||'—')}</div></div>`:''}<div class="field full"><label>Historiek</label>${actionHistoryHtml(item)}</div></div>`;
    showModal('Actie',body,'Sluiten',async()=>closeModal());
    setTimeout(()=>{const form=document.getElementById('modalForm'),foot=form?.querySelector('.modal-foot'),cancel=document.getElementById('cancelModal'),submit=form?.querySelector('button[type="submit"]');if(!foot||!submit)return;if(cancel)cancel.style.display='none';submit.textContent='Sluiten';const remove=document.createElement('button');remove.type='button';remove.className='btn danger';remove.textContent='Verwijderen';remove.onclick=()=>void deleteAction(item.id);foot.insertBefore(remove,foot.firstChild);const print=document.createElement('button');print.type='button';print.className='btn';print.textContent='Afdrukken';print.onclick=()=>printAction(item.id);foot.insertBefore(print,submit);const edit=document.createElement('button');edit.type='button';edit.className='btn';edit.textContent='Bewerken';edit.onclick=()=>{closeModal();void openActionEditor(item.id);};foot.insertBefore(edit,submit);if(item.status==='done'){const reopen=document.createElement('button');reopen.type='button';reopen.className='btn';reopen.textContent='Heropenen';reopen.onclick=()=>{closeModal();void reopenAction(item.id);};foot.insertBefore(reopen,submit);}else{const complete=document.createElement('button');complete.type='button';complete.className='btn primary';complete.textContent='✓ Afronden';complete.onclick=()=>{closeModal();void openCompleteAction(item.id);};submit.classList.remove('primary');foot.appendChild(complete);}},0);
  }

  function contextFor(kind,id) {
    if(kind==='device'){const d=(state.devices||[]).find(x=>x.id===id);return d?{deviceId:d.id,location:deviceLocationAt(d)||d.location||'',sourceKind:'device',sourceId:d.id,sourceLabel:`Toestel ${d.assetCode||d.model||''}`}:{};}
    if(kind==='maintenance'){const m=(state.maintenance||[]).find(x=>x.id===id),d=m?(state.devices||[]).find(x=>x.id===m.deviceId):null;return m?{deviceId:m.deviceId||'',location:d?(deviceLocationAt(d,recordMoment(m))||d.location||''):'',sourceKind:'maintenance',sourceId:m.id,sourceLabel:`Onderhoud ${recordDateTimeFmt(m)} · ${d?.assetCode||'toestel'}`}:{};}
    if(kind==='breakdown'){const b=(state.breakdowns||[]).find(x=>x.id===id),d=b?(state.devices||[]).find(x=>x.id===b.deviceId):null;return b?{deviceId:b.deviceId||'',location:d?(deviceLocationAt(d,recordMoment(b))||d.location||''):'',sourceKind:'breakdown',sourceId:b.id,sourceLabel:`Depannage · ${b.issue||d?.assetCode||'toestel'}`}:{};}
    return {};
  }
  function decorateContextModal(kind,id) {
    const foot=document.querySelector('#modal #modalForm .modal-foot');if(!foot||foot.querySelector('[data-create-action-context]'))return;
    const btn=document.createElement('button');btn.type='button';btn.className='btn';btn.dataset.createActionContext=kind;btn.textContent='+ Actie maken';btn.onclick=()=>{const ctx=contextFor(kind,id);closeModal();setTimeout(()=>void openActionEditor('',ctx),0);};foot.insertBefore(btn,foot.firstChild);
  }

  function deviceActionsHtml(deviceId) {
    const rows=(state.actions||[]).filter(a=>a.deviceId===deviceId),open=rows.filter(a=>a.status!=='done').sort(actionOpenSort),done=rows.filter(a=>a.status==='done').sort(actionDoneSort).slice(0,6);
    const list=(items,isDone)=>items.length?items.map(a=>`<div class="action-device-summary-row"><div><strong>${esc(a.title)}</strong><div class="muted">${isDone?(a.completedDate?actionDate(a.completedDate):'Uitgevoerd'):(a.dueDate?'tegen '+actionDate(a.dueDate):esc(a.assigneeName||''))}</div></div><button type="button" class="btn small" data-action-open="${esc(a.id)}">Bekijken</button></div>`).join(''):'<div class="muted">Geen acties.</div>';
    return `<div class="action-device-summary"><div class="action-device-summary-head"><strong>Open acties (${open.length})</strong><button type="button" class="btn small" data-action-device-new="${esc(deviceId)}">+ Actie</button></div><div class="action-device-summary-list">${list(open,false)}</div><div class="section-title" style="margin-top:12px">Uitgevoerde acties</div><div class="action-device-summary-list">${list(done,true)}</div></div>`;
  }
  function decorateDeviceModal(deviceId) {
    const grid=document.querySelector('#modal .modal-body .form-grid');if(!grid||grid.querySelector('.action-device-summary'))return;
    const holder=document.createElement('div');holder.className='field full';holder.innerHTML=deviceActionsHtml(deviceId);
    const history=grid.querySelector('.history-group')?.closest('.field.full');if(history)grid.insertBefore(holder,history);else grid.appendChild(holder);
    decorateContextModal('device',deviceId);
  }

  const baseRenderAll=typeof renderAll==='function'?renderAll:null;
  if(baseRenderAll){
    renderAll=function(){const result=baseRenderAll();renderActions();renderActionDashboard();return result;};
    window.renderAll=renderAll;
  }
  try{if(typeof machineparkViewQueries==='object')machineparkViewQueries.actions='';}catch(_){}

  const baseDeviceHistory=typeof showDeviceHistory==='function'?showDeviceHistory:null;
  if(baseDeviceHistory){showDeviceHistory=function(id){const r=baseDeviceHistory(id);setTimeout(()=>decorateDeviceModal(id),0);return r;};window.showDeviceHistory=showDeviceHistory;}
  const baseMaintenanceDetails=typeof showMaintenanceDetails==='function'?showMaintenanceDetails:null;
  if(baseMaintenanceDetails){showMaintenanceDetails=function(id){const r=baseMaintenanceDetails(id);setTimeout(()=>decorateContextModal('maintenance',id),0);return r;};window.showMaintenanceDetails=showMaintenanceDetails;}
  const baseBreakdown=typeof openBreakdown==='function'?openBreakdown:null;
  if(baseBreakdown){openBreakdown=function(id,...args){const r=baseBreakdown(id,...args);if(id)setTimeout(()=>decorateContextModal('breakdown',id),0);return r;};window.openBreakdown=openBreakdown;}

  window.machineparkDecorateServiceReportActions=function(report,foot){
    if(!foot||foot.querySelector('[data-create-service-action]'))return;
    const deviceIds=[...new Set((report?.records||[]).map(row=>row?.item?.deviceId||row?.deviceId).filter(Boolean))],deviceId=deviceIds.length===1?deviceIds[0]:'',location=report?.visits?.[0]?.location||'',date=report?.date?dateFmt(report.date):'',label=[date,location].filter(Boolean).join(' · ');
    const btn=document.createElement('button');btn.type='button';btn.className='btn';btn.dataset.createServiceAction='1';btn.textContent='+ Actie maken';btn.onclick=()=>{closeModal();setTimeout(()=>void openActionEditor('',{deviceId,location,sourceKind:'service-report',sourceId:report?.id||'',sourceLabel:`Serviceverslag ${label}`}),0);};foot.insertBefore(btn,foot.firstChild);
  };

  document.addEventListener('click',e=>{
    const scope=e.target.closest('[data-action-scope]');if(scope){actionScope=scope.dataset.actionScope||'all';renderActions();return;}
    const open=e.target.closest('[data-action-open]');if(open){openActionDetails(open.dataset.actionOpen);return;}
    const complete=e.target.closest('[data-action-complete]');if(complete){void openCompleteAction(complete.dataset.actionComplete);return;}
    const link=e.target.closest('[data-action-link]');if(link){void openActionEditor(link.dataset.actionLink);return;}
    const deviceNew=e.target.closest('[data-action-device-new]');if(deviceNew){void openActionEditor('',contextFor('device',deviceNew.dataset.actionDeviceNew));return;}
  });
  document.getElementById('actionQuickAdd')?.addEventListener('click',()=>void quickAddAction());
  document.getElementById('actionQuickInput')?.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();void quickAddAction();}});
  document.getElementById('actionNewFull')?.addEventListener('click',()=>void openActionEditor());
  document.getElementById('actionShowAllDone')?.addEventListener('click',()=>{showAllDone=true;renderActions();});
  window.addEventListener('online',()=>void loadActionUsers(true));
  loadActionUsers().catch(()=>{});
  renderActionDashboard();
})();
</script>
"""
    body_pos = index.rfind("</body>")
    if body_pos < 0:
        raise SystemExit("Buildvalidatie mislukt: </body> ontbreekt voor Acties")
    index = index[:body_pos] + script + index[body_pos:]
    INDEX.write_text(index, encoding="utf-8")

service = SERVICE.read_text(encoding="utf-8")
hook = "window.machineparkDecorateServiceReportActions(report,foot)"
if hook not in service:
    start = service.find("  function showServiceReportDetails(id) {")
    end = service.find("\n  function showServiceVisitDetails", start)
    if start < 0 or end < 0:
        raise SystemExit("Buildvalidatie mislukt: serviceverslag-details niet gevonden voor Acties")
    block = service[start:end]
    close_pos = block.rfind("\n    },0);")
    if close_pos < 0:
        raise SystemExit("Buildvalidatie mislukt: serviceverslag-footeranker niet gevonden voor Acties")
    injection = "\n      if(typeof window.machineparkDecorateServiceReportActions==='function') window.machineparkDecorateServiceReportActions(report,foot);"
    block = block[:close_pos] + injection + block[close_pos:]
    service = service[:start] + block + service[end:]
    SERVICE.write_text(service, encoding="utf-8")

built = INDEX.read_text(encoding="utf-8")
required = [
    MARKER,
    "DB_VERSION=2",
    "['parts','devices','maintenance','breakdowns','actions']",
    "actions:[]",
    'data-view="actions"',
    'id="view-actions"',
    "Nog te doen",
    "Uitgevoerd",
    "machineparkRenderActions",
    "machineparkDecorateServiceReportActions",
    "kpiActions",
    "action-device-summary",
    "machinepark-action-users-v1",
    "deleteAction",
    "pushActionDeletionNow",
    "machinepark-action-delete-one-click-v1",
    "Actie verwijderd",
    "'breakdowns','actions','faults'",
    "ACTION_PHOTO_LIMIT = 10",
    "actionPhotoEditorHtml",
    "initActionPhotoEditor",
    "action-photo-pending",
    "printAction",
    "Afdrukken",
    "machineparkPersistActionPhotos",
    "/machinepark/synology/api/action-photos.php",
]
for needle in required:
    if needle not in built:
        raise SystemExit(f"Buildvalidatie mislukt: Acties ontbreekt ({needle})")
if hook not in SERVICE.read_text(encoding="utf-8"):
    raise SystemExit("Buildvalidatie mislukt: Acties serviceverslag-hook ontbreekt")

print("[Machinepark] Acties-module: offline datastore, 2 lijsten, toewijzing, toestel/servicekoppeling en afronding actief")
