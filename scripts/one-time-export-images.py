from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent.parent
index_path = ROOT / 'index.html'
text = index_path.read_text(encoding='utf-8')

old_button = '<button class="btn" id="exportPartsCsv">CSV export</button>'
if old_button not in text:
    raise SystemExit('CSV-exportknop niet gevonden')
text = text.replace(old_button, '<button class="btn" id="exportPartsCsv">ZIP export + foto\'s</button>', 1)
text = text.replace(
    'Maak een back-up van alle Machinepark-gegevens of zet een eerder gemaakte back-up terug.',
    'Maak een back-up van alle Machinepark-gegevens inclusief opgeslagen afbeeldingen, of zet een eerder gemaakte back-up terug.',
    1,
)
text = re.sub(r'v1\.\d+(?:\.\d+)? • [^<]+', 'v1.64 • Export inclusief afbeeldingen', text, count=1)

export_code = r'''function downloadBlob(name,blob){const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1500)}
const ZIP_CRC_TABLE=(()=>{const t=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=(c&1)?(0xedb88320^(c>>>1)):(c>>>1);t[n]=c>>>0}return t})();
function zipCrc32(bytes){let c=0xffffffff;for(const b of bytes)c=ZIP_CRC_TABLE[(c^b)&255]^(c>>>8);return(c^0xffffffff)>>>0}
function zipDosDateTime(date=new Date()){const year=Math.max(1980,date.getFullYear());return{time:((date.getHours()&31)<<11)|((date.getMinutes()&63)<<5)|(Math.floor(date.getSeconds()/2)&31),date:(((year-1980)&127)<<9)|(((date.getMonth()+1)&15)<<5)|(date.getDate()&31)}}
function makeStoreZip(files){const enc=new TextEncoder(),locals=[],centrals=[],dt=zipDosDateTime(),set16=(v,o,n)=>v.setUint16(o,n,true),set32=(v,o,n)=>v.setUint32(o,n>>>0,true);let offset=0;for(const file of files){const name=enc.encode(file.name),bytes=file.bytes instanceof Uint8Array?file.bytes:new Uint8Array(file.bytes),crc=zipCrc32(bytes),local=new Uint8Array(30+name.length),lv=new DataView(local.buffer);set32(lv,0,0x04034b50);set16(lv,4,20);set16(lv,6,0);set16(lv,8,0);set16(lv,10,dt.time);set16(lv,12,dt.date);set32(lv,14,crc);set32(lv,18,bytes.length);set32(lv,22,bytes.length);set16(lv,26,name.length);set16(lv,28,0);local.set(name,30);locals.push(local,bytes);const central=new Uint8Array(46+name.length),cv=new DataView(central.buffer);set32(cv,0,0x02014b50);set16(cv,4,20);set16(cv,6,20);set16(cv,8,0);set16(cv,10,0);set16(cv,12,dt.time);set16(cv,14,dt.date);set32(cv,16,crc);set32(cv,20,bytes.length);set32(cv,24,bytes.length);set16(cv,28,name.length);set16(cv,30,0);set16(cv,32,0);set16(cv,34,0);set16(cv,36,0);set32(cv,38,0);set32(cv,42,offset);central.set(name,46);centrals.push(central);offset+=local.length+bytes.length}const centralOffset=offset,centralSize=centrals.reduce((n,x)=>n+x.length,0),end=new Uint8Array(22),ev=new DataView(end.buffer);set32(ev,0,0x06054b50);set16(ev,4,0);set16(ev,6,0);set16(ev,8,files.length);set16(ev,10,files.length);set32(ev,12,centralSize);set32(ev,16,centralOffset);set16(ev,20,0);return new Blob([...locals,...centrals,end],{type:'application/zip'})}
function exportFileSafeName(value){const cleaned=String(value||'bestand').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-zA-Z0-9._-]+/g,'-').replace(/^-+|-+$/g,'');return cleaned||'bestand'}
function dataUrlExportImage(dataUrl){if(typeof dataUrl!=='string'||!dataUrl.startsWith('data:image/'))return null;const m=dataUrl.match(/^data:(image\/[a-zA-Z0-9.+-]+);base64,([\s\S]+)$/);if(!m)return null;try{const binary=atob(m[2].replace(/\s/g,'')),bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);const extMap={'image/jpeg':'jpg','image/jpg':'jpg','image/png':'png','image/webp':'webp','image/gif':'gif'};return{bytes,ext:extMap[m[1].toLowerCase()]||'img',mime:m[1]}}catch{return null}}
async function exportPartsCsv(){const rows=[['Art nr','omschrijving','Merk toestel','prijs','Voorraad locatie 1','Code leverancier','Magazijnlocatie','Minimumvoorraad','Afbeelding bestand']],files=[],usedNames=new Set(),enc=new TextEncoder();let imageCount=0;for(const p of state.parts){let imagePath='';const image=dataUrlExportImage(p.photo);if(image){const base=exportFileSafeName(p.artNr||p.id||'onderdeel');let fileName=`${base}.${image.ext}`,n=2;while(usedNames.has(fileName.toLowerCase()))fileName=`${base}-${n++}.${image.ext}`;usedNames.add(fileName.toLowerCase());imagePath=`afbeeldingen/${fileName}`;files.push({name:imagePath,bytes:image.bytes});imageCount++}rows.push([p.artNr,p.description,p.deviceBrand,p.price,p.stock,p.supplierCode,p.warehouse,p.minStock,imagePath])}const csv='\ufeff'+rows.map(r=>r.map(csvEscape).join(';')).join('\n');files.unshift({name:'Onderdelen.csv',bytes:enc.encode(csv)});files.push({name:'README.txt',bytes:enc.encode(`Machinepark onderdelenexport\nDatum: ${new Date().toLocaleString('nl-BE')}\nOnderdelen: ${state.parts.length}\nAfbeeldingen: ${imageCount}\n\nDe kolom "Afbeelding bestand" in Onderdelen.csv verwijst naar de map afbeeldingen.`)});downloadBlob(`Machinepark_Onderdelen_${todayISO()}.zip`,makeStoreZip(files));toast(`Onderdelenexport gemaakt · ${state.parts.length} onderdelen · ${imageCount} afbeelding${imageCount===1?'':'en'}`)}'''
start = text.index('function exportPartsCsv(){')
end = text.index('\n\nfunction normalizeHeader', start)
text = text[:start] + export_code + text[end:]

backup_code = r'''function countEmbeddedPartImages(parts=[]){return parts.filter(p=>typeof p?.photo==='string'&&p.photo.startsWith('data:image/')).length}
async function makeBackupPayload(){const data={app:'Machinepark',schema:1,backupVersion:3,includesImages:true,exportedAt:new Date().toISOString()};for(const store of stores)data[store]=await getAll(store);data.counts=Object.fromEntries(stores.map(store=>[store,data[store].length]));data.images={parts:countEmbeddedPartImages(data.parts)};return data}
async function exportBackup(){const data=await makeBackupPayload();download('Machinepark_Backup_'+todayISO()+'.json',JSON.stringify(data,null,2));toast(`Back-up gemaakt · ${data.devices.length} toestellen · ${data.parts.length} onderdelen · ${data.images.parts} afbeeldingen`)}
async function importBackup(file){try{if(!file)return;const data=JSON.parse(await file.text());validateBackupData(data);const imageCount=countEmbeddedPartImages(data.parts),summary=`${data.devices.length} toestellen, ${data.parts.length} onderdelen, ${data.maintenance.length} onderhoudsregels, ${data.breakdowns.length} depannages en ${imageCount} afbeeldingen`;if(!confirm(`Deze geldige back-up bevat ${summary}. Bestaande gegevens vervangen? Vooraf wordt automatisch een veiligheidsback-up gedownload.`))return;const safety=await makeBackupPayload();download('Machinepark_Veiligheidsbackup_'+todayISO()+'.json',JSON.stringify(safety,null,2));const normalized={...data,app:'Machinepark',schema:1};await replaceLocalSnapshot(normalized);await refresh();setCentralSyncStatus('☁ Back-up centraal opslaan…','busy');await centralPush();toast(`Back-up gecontroleerd en teruggezet · ${imageCount} afbeeldingen hersteld`)}catch(e){console.error(e);alert('Back-up terugzetten mislukt: '+(e.message||'onbekende fout'))}}'''
start = text.index('async function makeBackupPayload(){')
end = text.index('\nfunction bind', start)
text = text[:start] + backup_code + text[end:]
index_path.write_text(text, encoding='utf-8')

sw_path = ROOT / 'sw.js'
sw = sw_path.read_text(encoding='utf-8').replace('machinepark-v1.63-thin-coffee-icon', 'machinepark-v1.64-export-images')
sw_path.write_text(sw, encoding='utf-8')

pkg_path = ROOT / 'package.json'
pkg = json.loads(pkg_path.read_text(encoding='utf-8'))
pkg['version'] = '1.64.0'
pkg_path.write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

test_path = ROOT / 'tests/build-smoke.test.mjs'
tests = test_path.read_text(encoding='utf-8')
marker = "    'downloadStockImportReport',\n"
extra = marker + "    'makeStoreZip',\n    'Afbeelding bestand',\n    'afbeeldingen/',\n    'backupVersion:3',\n    'includesImages:true',\n    'countEmbeddedPartImages',\n"
if "'makeStoreZip'" not in tests:
    tests = tests.replace(marker, extra, 1)
tests = tests.replace('machinepark-v1.63-thin-coffee-icon', 'machinepark-v1.64-export-images')
tests = tests.replace('service worker forceert nieuwe cache voor het nieuwe toestelicoon', 'service worker forceert nieuwe cache voor export met afbeeldingen')
test_path.write_text(tests, encoding='utf-8')

validator_path = ROOT / 'scripts/build-machinepark.py'
validator = validator_path.read_text(encoding='utf-8')
marker = '    "importverslag": "downloadStockImportReport",\n'
extra = marker + '    "onderdelenexport afbeeldingen": "makeStoreZip",\n    "afbeeldingskolom export": "Afbeelding bestand",\n    "back-up afbeeldingen": "includesImages:true",\n'
if '"onderdelenexport afbeeldingen"' not in validator:
    validator = validator.replace(marker, extra, 1)
validator = validator.replace('machinepark-v1.63-thin-coffee-icon', 'machinepark-v1.64-export-images')
validator_path.write_text(validator, encoding='utf-8')

print('[Machinepark] export met afbeeldingen voorbereid')
