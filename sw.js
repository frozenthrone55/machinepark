const CACHE='machinepark-v1.68.9-assets-d57e9560f6d5';
const ASSETS=[
  "./manifest.webmanifest",
  "./machinepark-logo.svg",
  "./machinepark-coffee-device-icon.png",
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
