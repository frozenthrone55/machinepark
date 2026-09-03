from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / 'index.html'
MARKER = '// iOS/Chrome-safe navigation bridge. This is registered before database startup.'
NEW_MARKER = '// Machinepark DOM-first navigation bridge v3. Registered before database startup.'

index = INDEX_PATH.read_text(encoding='utf-8')

if NEW_MARKER not in index:
    marker_pos = index.find(MARKER)
    if marker_pos < 0:
        raise SystemExit('Buildvalidatie mislukt: vroege navigatiebridge niet gevonden')

    script_start = index.rfind('<script>', 0, marker_pos)
    script_end = index.find('</script>', marker_pos)
    if script_start < 0 or script_end < 0:
        raise SystemExit('Buildvalidatie mislukt: scriptgrenzen van vroege navigatiebridge niet gevonden')
    script_end += len('</script>')

    replacement = r'''<script>
// Machinepark DOM-first navigation bridge v3. Registered before database startup.
(function(){
  function showNavigationView(view){
    var nextView=String(view||'').trim();
    var target=document.getElementById('view-'+nextView);
    if(!target) return false;

    // Maak de klik meteen zichtbaar, zonder afhankelijk te zijn van state,
    // IndexedDB, rollen, renderAll of de externe featurebundel.
    document.querySelectorAll('.view').forEach(function(node){node.classList.remove('active')});
    target.classList.add('active');
    document.querySelectorAll('.nav [data-view]').forEach(function(button){
      button.classList.toggle('active',button.getAttribute('data-view')===nextView);
    });

    var meta={
      dashboard:['Dashboard','Overzicht van service, storingen en voorraad.'],
      devices:['Toestellen','Beheer alle koffietoestellen en hun onderhoudsplanning.'],
      maintenance:['Onderhoud','Registreer halfjaarlijkse en jaarlijkse servicebeurten.'],
      breakdowns:['Depannages','Volg storingen van melding tot oplossing op.'],
      parts:['Onderdelen','Voorraad en onderdelen.'],
      faults:['Storingen','Zoek storingscodes, storingen en oplossingen per merk of model.'],
      manuals:['Handleidingen','Technische PDF-handleidingen per merk, model of toestel.'],
      settings:['Beheer','Back-up, import en instellingen.']
    }[nextView]||['Machinepark',''];
    var title=document.getElementById('pageTitle');
    var subtitle=document.getElementById('pageSubtitle');
    if(title) title.textContent=meta[0];
    if(subtitle) subtitle.textContent=meta[1];
    return true;
  }

  function navigate(view){
    if(!showNavigationView(view)) return false;

    // Synchroniseer daarna pas de volledige app. Een fout daar mag de reeds
    // zichtbare tab nooit terug naar Dashboard trekken.
    var fullNavigate=typeof window.machineparkNavigate==='function'
      ? window.machineparkNavigate
      : (typeof window.switchView==='function' ? window.switchView : null);
    if(fullNavigate && fullNavigate!==navigate){
      try{fullNavigate(view)}catch(error){
        console.error('[Machinepark] volledige navigatie faalde; DOM-tab blijft actief',error);
        showNavigationView(view);
      }
    }
    return true;
  }

  window.machineparkEarlyNavigate=navigate;

  document.addEventListener('click',function(e){
    var source=e.target&&e.target.nodeType===1?e.target:e.target&&e.target.parentElement;
    var btn=source&&source.closest?source.closest('.nav [data-view]'):null;
    if(!btn||btn.style.display==='none') return;
    e.preventDefault();
    e.stopPropagation();
    if(typeof e.stopImmediatePropagation==='function') e.stopImmediatePropagation();
    navigate(btn.getAttribute('data-view'));
  },true);

  document.addEventListener('touchend',function(e){
    var source=e.target&&e.target.nodeType===1?e.target:e.target&&e.target.parentElement;
    var btn=source&&source.closest?source.closest('.nav [data-view]'):null;
    if(!btn||btn.style.display==='none') return;
    e.preventDefault();
    e.stopPropagation();
    if(typeof e.stopImmediatePropagation==='function') e.stopImmediatePropagation();
    navigate(btn.getAttribute('data-view'));
  },{capture:true,passive:false});
})();
</script>'''

    index = index[:script_start] + replacement + index[script_end:]
    INDEX_PATH.write_text(index, encoding='utf-8')

built = INDEX_PATH.read_text(encoding='utf-8')
required = [
    NEW_MARKER,
    'window.machineparkEarlyNavigate=navigate',
    "document.querySelectorAll('.view').forEach",
    "target.classList.add('active')",
    "source.closest('.nav [data-view]')",
    "e.stopImmediatePropagation()",
    "},true);",
    "{capture:true,passive:false}",
    "showNavigationView(view);",
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: vroege DOM-first navigatie ontbreekt ({needle})')

if MARKER in built:
    raise SystemExit('Buildvalidatie mislukt: oude fragiele navigatiebridge is nog aanwezig')

print('[Machinepark] vroege DOM-first tabnavigatie v3 actief')
