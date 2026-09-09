from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SERVICE = ROOT / "service-visits.js"
SW = ROOT / "sw.js"
MARKER = 'data-machinepark-build-fix="video-media-support-v1"'
ACCEPT = 'image/*,video/mp4,video/webm,video/quicktime'

index = INDEX.read_text(encoding="utf-8")
service = SERVICE.read_text(encoding="utf-8")
sw = SW.read_text(encoding="utf-8")

if MARKER not in index:
    helper = r'''
<style data-machinepark-build-fix="video-media-support-v1">
.machinepark-media-video{display:block;width:100%;object-fit:cover;background:#111;border-radius:inherit}
.photo-preview .machinepark-media-video{width:100%;height:100%;min-height:0;max-height:none}
.service-photo-item video{width:100%;height:96px;object-fit:cover;border-radius:8px;background:#111}
.service-photo-details video{width:100%;height:150px;object-fit:cover;border-radius:12px;background:#111}
.action-photo-item video{width:100%;height:96px;object-fit:cover;border-radius:8px;background:#111}
.action-photo-details video{width:100%;height:105px;object-fit:cover;border-radius:10px;background:#111}
.device-photo-card .device-photo-image-wrap>video{width:100%;height:100%;object-fit:cover;background:#111}
.device-detail-photo video{width:100%;height:100%;object-fit:cover;background:#111}
.service-visit-photo-grid video{width:100%;height:130px;object-fit:cover;border-radius:7px;background:#111}
.timeline-service-photo.machinepark-media-video{width:64px;height:64px;object-fit:cover}
@media print{video.machinepark-media-video{display:none!important}}
</style>
<script data-machinepark-build-fix="video-media-support-v1">
(() => {
  const MAX_VIDEO_BYTES = 20 * 1024 * 1024;
  window.machineparkIsRawVideoMedia = src => String(src || '').startsWith('data:video/');
  window.machineparkIsVideoMedia = src => {
    const value=String(src||'').trim();
    if(!value)return false;
    if(value.startsWith('data:video/'))return true;
    try{return new URL(value,location.origin).searchParams.get('media')==='video';}catch(_){return /[?&]media=video(?:&|$)/.test(value);}
  };
  window.machineparkPrepareMediaFile = async (file,imageCompressor) => {
    if(!file||!file.size)return '';
    const type=String(file.type||'').toLowerCase();
    const video=type.startsWith('video/') || /\.(mp4|webm|mov|m4v)$/i.test(String(file.name||''));
    if(!video)return await imageCompressor(file);
    if(file.size>MAX_VIDEO_BYTES)throw new Error('Een video mag maximaal 20 MB groot zijn.');
    if(type && !['video/mp4','video/webm','video/quicktime','video/x-m4v'].includes(type))throw new Error('Gebruik MP4, WebM of MOV voor video’s.');
    return await new Promise((resolve,reject)=>{const r=new FileReader();r.onerror=reject;r.onload=()=>resolve(String(r.result||''));r.readAsDataURL(file);});
  };
  async function mediaPost(url,body,label){
    const headers=typeof centralHeaders==='function'?await centralHeaders(true):{'Content-Type':'application/json'};
    if(!headers['Content-Type'])headers['Content-Type']='application/json';
    const res=await fetch(url,{method:'POST',headers,body:JSON.stringify(body),cache:'no-store',credentials:'same-origin'});
    const text=await res.text();let data={};try{data=text?JSON.parse(text):{};}catch(_){}
    if(!res.ok)throw new Error(data.error||text||label||('Media opslaan mislukt · HTTP '+res.status));
    return data;
  }
  window.machineparkPersistMediaList = async (url,idBody,list,label) => {
    const values=(Array.isArray(list)?list:[]).filter(src=>typeof src==='string'&&src.trim()).slice(0,10);
    if(navigator.onLine===false)return values;
    const refs=[];
    for(const value of values){
      if(value.startsWith('data:image/')||value.startsWith('data:video/')){
        const one=await mediaPost(url,{...idBody,photos:[value],completeList:false},label);
        const ref=Array.isArray(one.photos)?one.photos[0]:'';
        if(!ref)throw new Error(label||'Media opslaan mislukt.');
        refs.push(ref);
      }else refs.push(value);
    }
    const final=await mediaPost(url,{...idBody,photos:refs,completeList:true},label);
    return (Array.isArray(final.photos)?final.photos:refs).filter(Boolean).slice(0,10);
  };
  function enhance(root=document){
    const imgs=[];
    if(root?.matches?.('img'))imgs.push(root);
    root?.querySelectorAll?.('img').forEach(img=>imgs.push(img));
    for(const img of imgs){
      const full=img.dataset.fullSrc||img.getAttribute('src')||'';
      if(!window.machineparkIsVideoMedia(full))continue;
      const video=document.createElement('video');
      video.className=(img.className?img.className+' ':'')+'machinepark-media-video';
      video.src=full;video.controls=true;video.playsInline=true;video.preload='metadata';
      video.setAttribute('aria-label',img.alt||'Video');
      if(img.getAttribute('style'))video.setAttribute('style',img.getAttribute('style'));
      if(img.dataset.fullSrc)video.dataset.fullSrc=full;
      const card=img.closest('.device-photo-card');
      img.replaceWith(video);
      if(card){
        const radio=card.querySelector('input[name="devicePhotoOverviewChoice"]');
        if(radio){radio.disabled=true;radio.checked=false;radio.closest('label')?.setAttribute('title','Een video kan niet als overzichtsfoto gebruikt worden.');}
        const first=card.parentElement?.querySelector('input[name="devicePhotoOverviewChoice"]:not(:disabled)');
        if(first&&!card.parentElement?.querySelector('input[name="devicePhotoOverviewChoice"]:checked')){first.checked=true;first.dispatchEvent(new Event('change',{bubbles:true}));}
      }
    }
  }
  const observer=new MutationObserver(records=>records.forEach(r=>r.addedNodes.forEach(node=>{if(node.nodeType===1)enhance(node)})));
  const start=()=>{enhance(document);observer.observe(document.documentElement,{childList:true,subtree:true});setTimeout(()=>{const base=window.machineparkDeviceOverviewPhoto;if(typeof base==='function'&&!base.__mediaWrapped){const wrapped=function(device){const chosen=base(device);if(chosen&&!window.machineparkIsVideoMedia(chosen))return chosen;return (Array.isArray(device?.devicePhotos)?device.devicePhotos:[]).find(src=>src&&!window.machineparkIsVideoMedia(src))||''};wrapped.__mediaWrapped=true;window.machineparkDeviceOverviewPhoto=wrapped;if(typeof window.renderDevices==='function')window.renderDevices();}},0)};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
</script>
'''
    index = index.replace("</head>", helper + "\n</head>", 1)

# File pickers accept photos and supported videos.
index = index.replace('accept="image/*"', f'accept="{ACCEPT}"')
service = service.replace('accept="image/*"', f'accept="{ACCEPT}"')

# All upload call sites use the image compressor for images and FileReader for video.
for old,new in [
    ("await compressImage(file)", "await window.machineparkPrepareMediaFile(file,compressImage)"),
    ("await compressImage(f.files[0])", "await window.machineparkPrepareMediaFile(f.files[0],compressImage)"),
    ("await compressDevicePhoto(file)", "await window.machineparkPrepareMediaFile(file,compressDevicePhoto)"),
    ("await compressImportPhoto(file)", "await window.machineparkPrepareMediaFile(file,compressImportPhoto)"),
]:
    index = index.replace(old,new)
    service = service.replace(old,new)

# Folder import also recognizes video files.
index = index.replace(
    "return String(file.type || '').startsWith('image/') || /\\.(?:jpe?g|png|webp|gif|bmp|avif)$/i.test(file.name);",
    "return /^(?:image|video)\\//.test(String(file.type || '')) || /\\.(?:jpe?g|png|webp|gif|bmp|avif|mp4|webm|mov|m4v)$/i.test(file.name);"
)

# Thumbnail refs should never point a video at an <img>.
# Loose service media filtering must also retain raw videos while offline/before persistence.
index = index.replace(
    "return src.startsWith('data:image/') || src.includes(SERVICE_PHOTO_ENDPOINT);",
    "return src.startsWith('data:image/') || src.startsWith('data:video/') || src.includes(SERVICE_PHOTO_ENDPOINT);"
)

index = index.replace(
    "const value = String(src || '').trim();\n    const normalized = value",
    "const value = String(src || '').trim();\n    if(window.machineparkIsVideoMedia?.(value)) return value;\n    const normalized = value"
)
index = index.replace(
    "const value = String(src || '').trim();\n    if (!value || !ownPhotoEndpoint(value)) return value;",
    "const value = String(src || '').trim();\n    if(window.machineparkIsVideoMedia?.(value)) return value;\n    if (!value || !ownPhotoEndpoint(value)) return value;"
)

# Trigger storage for raw videos too; only images receive generated thumbnails.
index = index.replace(
    "if (!force && !list.some(isRawPhoto)) return list;",
    "if (!force && !list.some(src=>isRawPhoto(src)||window.machineparkIsRawVideoMedia?.(src))) return list;"
)
index = index.replace(
    "if (!isRawPhoto(value)) return value;",
    "if (!isRawPhoto(value) && !window.machineparkIsRawVideoMedia?.(value)) return value;"
)

# Large videos are uploaded one item per request, then the compact final reference list is committed.
index = index.replace(
    "const rawIndexes = list.map((src, index) => isRawPhoto(src) ? index : -1).filter((index) => index >= 0);\n    photoSaveBusy += 1;",
    "if(list.some(src=>window.machineparkIsRawVideoMedia?.(src))) return await window.machineparkPersistMediaList(DEVICE_PHOTO_URL,{deviceId},list,'Toestelmedia opslaan mislukt');\n    const rawIndexes = list.map((src, index) => isRawPhoto(src) ? index : -1).filter((index) => index >= 0);\n    photoSaveBusy += 1;",
    1
)
# Service has the same rawIndexes text later. Anchor on the actual function
# definition, not on an earlier reference to the function name.
needle = "const rawIndexes = list.map((src, index) => isRawPhoto(src) ? index : -1).filter((index) => index >= 0);\n    photoSaveBusy += 1;"
service_start = index.find("window.machineparkPersistServicePhotos = async function")
pos = index.find(needle, service_start if service_start >= 0 else 0)
if service_start < 0 or pos < 0:
    raise SystemExit("Buildvalidatie mislukt: service media-opslagfunctie niet gevonden")
index = index[:pos] + "if(list.some(src=>window.machineparkIsRawVideoMedia?.(src))) return await window.machineparkPersistMediaList(SERVICE_PHOTO_URL,{storeName,entityId},list,'Verslagmedia opslaan mislukt');\n    " + index[pos:]

# ToDo video previews must keep the full media ref instead of adding variant=thumb.
index = index.replace(
    "if(!value||value.startsWith('data:image/'))return value;",
    "if(!value||value.startsWith('data:image/')||window.machineparkIsVideoMedia?.(value))return value;"
)

# ToDo media uses the same sequential route when video is present.
index = index.replace(
    "const list=actionPhotoList(photos);\n    const body=await actionPhotoPost({actionId,photos:list,completeList:true});",
    "const list=actionPhotoList(photos);\n    if(list.some(src=>window.machineparkIsRawVideoMedia?.(src)))return await window.machineparkPersistMediaList(ACTION_PHOTO_URL,{actionId},list,'ToDo-media opslaan mislukt');\n    const body=await actionPhotoPost({actionId,photos:list,completeList:true});"
)

# Video cannot be an overview image; the visible chooser is disabled by the runtime enhancer.
index = index.replace(
    "return Number.isInteger(raw) && raw >= 0 && raw < photos.length ? raw : 0;",
    "if(Number.isInteger(raw)&&raw>=0&&raw<photos.length&&!window.machineparkIsVideoMedia?.(photos[raw]))return raw;const first=photos.findIndex(src=>!window.machineparkIsVideoMedia?.(src));return first>=0?first:0;"
)
index = index.replace(
    "return photos[overviewIndex(device, photos)] || photos[0] || '';",
    "const chosen=photos[overviewIndex(device,photos)]||'';if(chosen&&!window.machineparkIsVideoMedia?.(chosen))return chosen;return photos.find(src=>!window.machineparkIsVideoMedia?.(src))||'';"
)

# Visible copy consistently describes the combined photo/video list.
for old,new in [
    ("Foto onderdeel", "Foto of video onderdeel"),
    ("om foto toe te voegen", "om foto of video toe te voegen"),
    ("Foto’s toestel", "Foto’s / video’s toestel"),
    ("+ Foto’s toevoegen", "+ Foto’s / video’s toevoegen"),
    ("Foto’s bij verslag", "Foto’s / video’s bij verslag"),
    ("Geen foto’s bij dit verslag.", "Geen foto’s of video’s bij dit verslag."),
    ("Nog geen foto’s toegevoegd.", "Nog geen foto’s of video’s toegevoegd."),
    ("Maximaal ${DEVICE_PHOTO_LIMIT} foto’s. Kies één foto als overzichtsfoto voor de toestellenlijst.", "Maximaal ${DEVICE_PHOTO_LIMIT} foto’s en video’s samen. Alleen een foto kan als overzichtsfoto dienen."),
    (" van maximaal ${DEVICE_PHOTO_LIMIT} foto’s", " van maximaal ${DEVICE_PHOTO_LIMIT} media-items"),
    ("Maximaal ${REPORT_PHOTO_LIMIT} foto’s per verslag. Foto’s worden automatisch verkleind en apart opgeslagen.", "Maximaal ${REPORT_PHOTO_LIMIT} foto’s en video’s samen per verslag. Foto’s worden verkleind; video’s worden apart opgeslagen."),
    ("Maximaal '+ACTION_PHOTO_LIMIT+' foto’s per ToDo.", "Maximaal '+ACTION_PHOTO_LIMIT+' foto’s en video’s samen per ToDo."),
    ("Foto’s bij ToDo", "Foto’s / video’s bij ToDo"),
    ("📷 '+actionPhotoList(item.photos).length", "📎 '+actionPhotoList(item.photos).length"),
]:
    index = index.replace(old,new)

for old,new in [
    ("Foto’s bij ${photoLabel}", "Foto’s / video’s bij ${photoLabel}"),
    ("Maximaal 10 foto’s per toestelregistratie.", "Maximaal 10 foto’s en video’s samen per toestelregistratie."),
    ("Conceptfoto ", "Conceptmedia "),
]:
    service = service.replace(old,new)

# Remaining limit/error copy should not imply that video is excluded.
for old,new in [
    ("Maximaal ${REPORT_PHOTO_LIMIT} foto’s per onderhouds- of depannageverslag.", "Maximaal ${REPORT_PHOTO_LIMIT} foto’s en video’s samen per onderhouds- of depannageverslag."),
    ("Een toestel kan maximaal ${DEVICE_PHOTO_LIMIT} foto’s bevatten.", "Een toestel kan maximaal ${DEVICE_PHOTO_LIMIT} foto’s en video’s samen bevatten."),
    ("Foto’s worden verwerkt…", "Media wordt verwerkt…"),
    ("Een van de foto’s kon niet worden verwerkt.", "Een van de media-items kon niet worden verwerkt."),
    ("Maximaal 10 foto’s per verslag. Foto’s worden automatisch verkleind en apart opgeslagen.", "Maximaal 10 foto’s en video’s samen per verslag. Foto’s worden verkleind; video’s worden apart opgeslagen."),
    ("Maximaal 10 foto’s per onderhouds- of depannageconcept.", "Maximaal 10 foto’s en video’s samen per onderhouds- of depannageconcept."),
    ("Geen foto’s bij deze ToDo.", "Geen foto’s of video’s bij deze ToDo."),
    ("<label>Foto’s</label>${actionPhotoGridHtml(item.photos||[],false)}", "<label>Foto’s / video’s</label>${actionPhotoGridHtml(item.photos||[],false)}"),
]:
    index = index.replace(old,new)

# PDF/print image-only surfaces ignore video rather than rendering broken image boxes.
service = service.replace(
    "photos:(item.photos||[]).filter(src=>typeof src==='string'&&src.trim()),",
    "photos:(item.photos||[]).filter(src=>typeof src==='string'&&src.trim()&&!window.machineparkIsVideoMedia?.(src)),"
)
service = service.replace(
    "photos:reportPhotos(report).map(p=>p.src),",
    "photos:reportPhotos(report).map(p=>p.src).filter(src=>!window.machineparkIsVideoMedia?.(src)),"
)
service = service.replace(
    "const item=row.item||{},photos=(item.photos||[]).filter(src=>typeof src==='string'&&src.trim());",
    "const item=row.item||{},photos=(item.photos||[]).filter(src=>typeof src==='string'&&src.trim()&&!window.machineparkIsVideoMedia?.(src));"
)

# Loose maintenance/depannage PDF and the generic photo renderer should omit videos
# entirely rather than drawing an empty "foto kon niet worden geladen" box.
index = index.replace(
    ".filter(src => typeof src === 'string' && src.trim());\n  }\n\n  function serviceModel(context)",
    ".filter(src => typeof src === 'string' && src.trim() && !window.machineparkIsVideoMedia?.(src));\n  }\n\n  function serviceModel(context)"
)
index = index.replace(
    "const photos = model.photos || [];\n    if (!photos.length) return startY;",
    "const photos = (model.photos || []).filter(src=>!window.machineparkIsVideoMedia?.(src));\n    if (!photos.length) return startY;"
)

# Refresh service asset hash after modifying service-visits.js.
SERVICE.write_text(service, encoding="utf-8")
new_hash = hashlib.sha256((service + "\n" + (ROOT / "service-visits.css").read_text(encoding="utf-8")).encode("utf-8")).hexdigest()[:12]
index = re.sub(r'/service-visits\\.js\\?v=[a-f0-9]+', f'/service-visits.js?v={new_hash}', index)
index = re.sub(r'/service-visits\\.css\\?v=[a-f0-9]+', f'/service-visits.css?v={new_hash}', index)
sw = re.sub(r"'/service-visits\\.js\\?v=[a-f0-9]+'", f"'/service-visits.js?v={new_hash}'", sw)
sw = re.sub(r"'/service-visits\\.css\\?v=[a-f0-9]+'", f"'/service-visits.css?v={new_hash}'", sw)

INDEX.write_text(index, encoding="utf-8")
SW.write_text(sw, encoding="utf-8")

built = INDEX.read_text(encoding="utf-8")
for needle in [
    MARKER,
    'video/mp4',
    'machineparkPrepareMediaFile',
    'machineparkIsVideoMedia',
    'machineparkPersistMediaList',
    'MAX_VIDEO_BYTES = 20 * 1024 * 1024',
]:
    if needle not in built:
        raise SystemExit(f"Buildvalidatie mislukt: video/media-ondersteuning ontbreekt ({needle})")
if 'accept="image/*"' in built or 'accept="image/*"' in SERVICE.read_text(encoding="utf-8"):
    raise SystemExit("Buildvalidatie mislukt: er staat nog een foto-only mediakiezer in de app")
device_block = built[built.find("window.machineparkPersistDevicePhotoList = async function", built.find("/* photo-storage-optimization")):built.find("window.machineparkPersistPartPhoto = async function", built.find("/* photo-storage-optimization"))]
service_block = built[built.find("window.machineparkPersistServicePhotos = async function"):built.find("function writeStoreDirect", built.find("window.machineparkPersistServicePhotos = async function"))]
if "SERVICE_PHOTO_URL,{storeName,entityId}" in device_block:
    raise SystemExit("Buildvalidatie mislukt: service-video uploadroute staat in toestelmediafunctie")
if "SERVICE_PHOTO_URL,{storeName,entityId}" not in service_block:
    raise SystemExit("Buildvalidatie mislukt: service-video uploadroute ontbreekt")
if "Foto’s / video’s" not in built:
    raise SystemExit("Buildvalidatie mislukt: media-interface gebruikt nog foto-only labels")
if "src.startsWith('data:video/')" not in built:
    raise SystemExit("Buildvalidatie mislukt: raw video wordt niet door de service-mediafilter behouden")
if "const photos = (model.photos || []).filter(src=>!window.machineparkIsVideoMedia?.(src));" not in built:
    raise SystemExit("Buildvalidatie mislukt: generieke PDF filtert video niet uit")
print("[Machinepark] foto + video media actief · maximaal 10 items per bestaande fotolijst")
