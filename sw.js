const CACHE='machinepark-v1.68.9-assets-d2338969ae80';
const ASSETS=[
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./machinepark-logo.svg",
  "./machinepark-coffee-device-icon.png",
  "./offline-first.js?v=1.68.9",
  "./fault-library.js?v=1.68.9-256747f2968a",
  "./fault-library.css?v=1.68.9-256747f2968a",
  "./manual-library.js?v=fedde8b04b9f",
  "./manual-library.css",
  "./assets/machinepark-build.js?v=1.68.9-d2338969ae80",
  "./assets/machinepark-build.css?v=1.68.9-d2338969ae80",
  "./service-visits.js?v=b9bf7c0fbc8f",
  "./service-visits.css?v=b9bf7c0fbc8f",
];
const CACHEABLE_API=new Set([
  '/.netlify/functions/work-order-templates',
  '/.netlify/functions/device-photos',
  '/.netlify/functions/part-photos',
  '/.netlify/functions/service-photos'
]);

self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));
  self.clients.claim();
});

function apiCacheKey(url){
  return new Request(url.pathname+url.search,{method:'GET'});
}

self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  const url=new URL(e.request.url);
  if(url.hostname!==self.location.hostname)return;

  if(url.pathname.startsWith('/.netlify/functions/')){
    if(!CACHEABLE_API.has(url.pathname))return;
    const key=apiCacheKey(url);
    e.respondWith(
      fetch(e.request).then(r=>{
        if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(key,copy));}
        return r;
      }).catch(()=>caches.match(key,{ignoreVary:true}).then(r=>r||Response.error()))
    );
    return;
  }

  if(e.request.mode==='navigate'){
    e.respondWith(
      fetch(e.request).then(r=>{
        if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put('./index.html',copy));}
        return r;
      }).catch(()=>caches.match('./index.html'))
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(cached=>cached||fetch(e.request).then(r=>{
      if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));}
      return r;
    }))
  );
});
