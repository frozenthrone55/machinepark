from pathlib import Path
import re
import hashlib
ROOT = Path(__file__).resolve().parent
p = ROOT / 'index.html'
s = p.read_text()
marker = 'data-machinepark-build-fix="sharepoint-device-sync-v1"'
if marker not in s:
    start = s.index('    for(const r of activeAdds)', s.index('function showDeviceSyncPreview'))
    end = s.index('    closeModal();', start)
    loops = s[start:end]
    helper = 'async function applyDeviceSyncRecords(activeAdds,activeUpdates,fileName,syncMoment,loggedAt){\n' + loops + '\n}\n'
    s = s[:start] + '    await applyDeviceSyncRecords(activeAdds,activeUpdates,fileName,syncMoment,loggedAt);\n' + s[end:]
    pos = s.index('function showDeviceSyncPreview')
    s = s[:pos] + helper + s[pos:]
    s = s.replace('</head>', f'<meta {marker}>\n</head>', 1)
    pos = s.rfind('</body>')
    s = s[:pos] + '<script src="./sharepoint-device-sync.js"></script>\n' + s[pos:]
    p.write_text(s)
# Version the separate admin UI so cached clients fetch changed synchronization text.
ui_version = hashlib.sha256((ROOT / 'sharepoint-device-sync.js').read_bytes()).hexdigest()[:16]
s = re.sub(r'(<script src="\./sharepoint-device-sync\.js)(?:\?v=[^"]*)?("[^>]*></script>)', lambda m: m.group(1) + '?v=' + ui_version + m.group(2), s)
p.write_text(s)
# The NAS worker uses the actual manual planner and writer, not a second implementation.
names = ['normalizeMoment','locationEvents','deviceLocationAt','normalizeHeader','cleanCell','findHeaderIndex','validYmd','parseInventoryDate','syncTextSame','installSourceDisplay','currentInstallDisplay','deviceSyncPlan']
functions = []
for name in names:
    m = re.search(r'^function '+name+r'\([^\n]+', s, re.M)
    if not m: raise SystemExit('Missing shared sync function: '+name)
    functions.append(m.group(0))
start = s.index('async function applyDeviceSyncRecords(')
end = s.index('function showDeviceSyncPreview', start)
helper = s[start:end].strip()
constants = '\n'.join(re.search(r'^const '+name+r'=[^\n]+', s, re.M).group(0) for name in ['uid','pad2','localDateISO','todayISO','nowLocalTime','nowLocalDateTime','dateFmt'])
worker = "'use strict';\nprocess.env.TZ='Europe/Brussels';\n" + constants + '\n' + '\n'.join(functions) + '\n' + helper + '''
async function synchronize(input){
 const stateInput=input.devices;
 if(!Array.isArray(stateInput))throw Error('Ongeldige toestelgegevens');
 state.devices=stateInput;
 const matrix=input.matrix;
 matrix.__redRows=new Set(input.redRows||[]);
 const records=deviceSyncPlan(matrix),adds=records.filter(r=>r.action==='add'),updates=records.filter(r=>r.action==='update');
 if(!records.some(r=>r.action!=='skip'))throw Error('Geen geldige toestellen in bronbestand');
 const changes=[];
 await applyDeviceSyncRecords(adds,updates,input.fileName,input.syncMoment,input.loggedAt);
 for(const next of written){const old=stateInput.find(d=>d.id===next.id);for(const field of ['assetCode','location','brand','installDate','installDatePrecision','installDateSource','status']){if((old?.[field]||'')!==(next[field]||''))changes.push({code:next.assetCode,field,oldValue:old?.[field]||'',newValue:next[field]||'',action:old?'update':'add'});}}
 return {devices:written,changes,read:records.filter(r=>r.action!=='skip').length,added:adds.length,updated:updates.length,unchanged:records.filter(r=>r.action==='same').length,skipped:records.filter(r=>r.action==='skip').map(r=>r.reason)};
}
const state={devices:[]},written=[];
async function put(store,value){if(store!=='devices')throw Error('Unexpected store');written.push(value);}
let raw='';process.stdin.setEncoding('utf8');process.stdin.on('data',s=>raw+=s);process.stdin.on('end',async()=>{try{console.log(JSON.stringify(await synchronize(JSON.parse(raw))));}catch(e){console.error(e.message);process.exitCode=1;}});
'''
(ROOT / 'synology/device-sync-worker.cjs').write_text(worker)
print('[Machinepark] automatische toestelsynchronisatie deelt handmatige planner en verwerking')
