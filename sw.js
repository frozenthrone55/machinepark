const CACHE='machinepark-v1.68.11-assets-f40db23580cd';
const ASSETS=[
  "./assets/machinepark-build.css?v=1.68.11-f40db23580cd",
  "./assets/machinepark-build.js?v=1.68.11-f40db23580cd",
  "./fault-library.css?v=1.68.11-256747f2968a",
  "./fault-library.js?v=1.68.11-256747f2968a",
  "./index.html",
  "./machinepark-coffee-device-icon.png",
  "./machinepark-logo.svg",
  "./manifest.webmanifest",
  "./manual-library.css",
  "./manual-library.js?v=5efce4383df3",
  "./offline-first.js?v=15dad2d0f8ed",
  "./service-visits.css?v=986c837ec72d",
  "./service-visits.js?v=715d776a797c",
  "./synology-local-auth.js?v=82184890286a",
];
const CACHEABLE_API=new Set([]);

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

  // machinepark-synology-api-network-only-v1
  if(url.pathname.includes('/synology/api/') || e.request.cache==='no-store'){
    e.respondWith(fetch(e.request));
    return;
  }

  if(url.pathname==='/deploy-meta.json'||url.pathname.endsWith('/deploy-meta.json')){
    e.respondWith(fetch(e.request,{cache:'no-store'}));
    return;
  }

  // machinepark-manual-assets-network-first-v1
  if(url.pathname.endsWith('/manual-library.js')||url.pathname.endsWith('/manual-library.css')){
    e.respondWith(
      fetch(e.request,{cache:'no-store'}).then(r=>{
        if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));}
        return r;
      }).catch(()=>caches.match(e.request).then(r=>r||Response.error()))
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
