from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="central-sync-reliability-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    replace_once(
        "const centralSync={enabled:false,applying:false,pushing:false,etag:null,pushTimer:null,pollTimer:null,lastRemoteAt:''};",
        "const centralSync={enabled:false,applying:false,pushing:false,pending:false,pushPromise:null,etag:null,pushTimer:null,pollTimer:null,lastRemoteAt:''};",
        'centrale syncstatus',
    )

    old_push = "async function centralPush({initial=false}={}){if((!centralSync.enabled&&!initial)||centralSync.applying||centralSync.pushing||!window.Clerk?.isSignedIn)return;centralSync.pushing=true;setCentralSyncStatus('☁ Wijzigingen synchroniseren…','busy');try{const data=await localSnapshot(),headers=await centralHeaders(true);const res=await fetch(CENTRAL_SYNC_URL,{method:'PUT',headers,body:JSON.stringify({data,etag:centralSync.etag}),cache:'no-store'});if(res.status===409){setCentralSyncStatus('☁ Nieuwere cloudversie gevonden','busy');await centralPull({apply:true,quiet:true});toast('Nieuwere centrale gegevens geladen. Controleer je laatste wijziging.');return}if(!res.ok){const msg=await res.text();throw new Error(msg||`Cloud opslaan mislukt (${res.status})`)}const body=await res.json();centralSync.etag=body.etag||centralSync.etag;centralSync.lastRemoteAt=data.updatedAt;setCentralSyncStatus('☁ Alles centraal opgeslagen','ok')}catch(e){console.error('Centrale synchronisatie:',e);setCentralSyncStatus('☁ Synchronisatie mislukt','error');throw e}finally{centralSync.pushing=false}}"
    new_push = "async function centralPush({initial=false}={}){if((!centralSync.enabled&&!initial)||centralSync.applying||!window.Clerk?.isSignedIn)return;if(centralSync.pushing){centralSync.pending=true;if(centralSync.pushPromise)await centralSync.pushPromise;if(centralSync.pending&&!centralSync.pushing)return centralPush({initial});return}centralSync.pushing=true;centralSync.pending=false;setCentralSyncStatus('☁ Wijzigingen synchroniseren…','busy');const run=(async()=>{try{const data=await localSnapshot(),headers=await centralHeaders(true);const res=await fetch(CENTRAL_SYNC_URL,{method:'PUT',headers,body:JSON.stringify({data,etag:centralSync.etag}),cache:'no-store'});if(res.status===409){setCentralSyncStatus('☁ Nieuwere cloudversie gevonden','busy');await centralPull({apply:true,quiet:true});throw new Error('De centrale gegevens waren intussen gewijzigd. De nieuwste versie is geladen; sla je wijziging opnieuw op.')}if(!res.ok){const msg=await res.text();throw new Error(msg||`Cloud opslaan mislukt (${res.status})`)}const body=await res.json();centralSync.etag=body.etag||centralSync.etag;centralSync.lastRemoteAt=data.updatedAt;setCentralSyncStatus('☁ Alles centraal opgeslagen','ok');return body}catch(e){console.error('Centrale synchronisatie:',e);setCentralSyncStatus('☁ Synchronisatie mislukt','error');throw e}})();centralSync.pushPromise=run;try{return await run}finally{centralSync.pushing=false;centralSync.pushPromise=null;if(centralSync.pending&&centralSync.enabled&&!centralSync.applying){clearTimeout(centralSync.pushTimer);centralSync.pushTimer=setTimeout(()=>{centralSync.pushTimer=null;centralPush().catch(()=>{})},120)}}}"
    replace_once(old_push, new_push, 'centrale push met wachtrij')

    old_schedule = "function scheduleCentralSync(){if(!centralSync.enabled||centralSync.applying)return;clearTimeout(centralSync.pushTimer);setCentralSyncStatus('☁ Lokale wijziging…','busy');centralSync.pushTimer=setTimeout(()=>{centralSync.pushTimer=null;centralPush().catch(()=>{})},650)}"
    new_schedule = "function scheduleCentralSync(){if(!centralSync.enabled||centralSync.applying)return;centralSync.pending=true;clearTimeout(centralSync.pushTimer);setCentralSyncStatus('☁ Lokale wijziging…','busy');centralSync.pushTimer=setTimeout(()=>{centralSync.pushTimer=null;centralPush().catch(()=>{})},650)}"
    replace_once(old_schedule, new_schedule, 'centrale syncplanning')

    old_device_save = "await put('devices',obj);closeModal();await refresh();toast(editing&&val(fd,'newLocation')?'Toestel en locatiewijziging opgeslagen':'Toestel opgeslagen')"
    new_device_save = "await put('devices',obj);if(centralSync.enabled){clearTimeout(centralSync.pushTimer);centralSync.pushTimer=null;centralSync.pending=true;await centralPush()}closeModal();await refresh();toast(editing&&val(fd,'newLocation')?'Toestel en locatiewijziging centraal opgeslagen':'Toestel centraal opgeslagen')"
    replace_once(old_device_save, new_device_save, 'toestel direct centraal bevestigen')

    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    index_path.write_text(index, encoding='utf-8')
    print('[Machinepark] centrale syncwachtrij en bevestigde toestelopslag actief')
else:
    print('[Machinepark] betrouwbare centrale sync reeds actief')
