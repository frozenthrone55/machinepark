from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / 'index.html'
BOOTSTRAP_MARKER = '<!-- machinepark-navigation-bootstrap-v1 -->'

index = INDEX_PATH.read_text(encoding='utf-8')

if BOOTSTRAP_MARKER not in index:
    bootstrap = r'''
<!-- machinepark-navigation-bootstrap-v1 -->
<script data-machinepark-navigation-bootstrap="v1">
(() => {
  const titles = {
    dashboard: ['Dashboard', 'Overzicht van service, storingen en voorraad.'],
    devices: ['Toestellen', 'Beheer alle koffietoestellen en hun onderhoudsplanning.'],
    maintenance: ['Onderhoud', 'Registreer halfjaarlijkse en jaarlijkse servicebeurten.'],
    breakdowns: ['Depannages', 'Volg storingen van melding tot oplossing op.'],
    parts: ['Onderdelen', 'Voorraad en onderdelen.'],
    faults: ['Storingen', 'Zoek storingscodes, storingen en oplossingen per merk of model.'],
    manuals: ['Handleidingen', 'Technische PDF-handleidingen per merk, model of toestel.'],
    settings: ['Beheer', 'Back-up, import en instellingen.'],
  };

  function showView(view) {
    const nextView = String(view || '').trim();
    const target = document.getElementById(`view-${nextView}`);
    if (!target) return false;

    document.querySelectorAll('.view').forEach((node) => node.classList.remove('active'));
    target.classList.add('active');
    document.querySelectorAll('.nav [data-view]').forEach((button) => {
      button.classList.toggle('active', button.dataset.view === nextView);
    });

    const meta = titles[nextView] || ['Machinepark', ''];
    const title = document.getElementById('pageTitle');
    const subtitle = document.getElementById('pageSubtitle');
    if (title) title.textContent = meta[0];
    if (subtitle) subtitle.textContent = meta[1];
    return true;
  }

  function navigate(view) {
    // De inline fallback wisselt de DOM eerst. Daarna mag de volledige runtime
    // state, rechten, zoekbalk en feature-renderers synchroniseren.
    if (!showView(view)) return false;
    if (typeof window.machineparkNavigate === 'function') {
      try {
        window.machineparkNavigate(view);
      } catch (error) {
        console.error('[Machinepark] volledige navigatie-runtime faalde; inline view blijft actief', error);
      }
    }
    return true;
  }

  function interceptNavigation(event) {
    const source = event.target && event.target.nodeType === 1
      ? event.target
      : event.target?.parentElement;
    const button = source?.closest?.('.nav [data-view]');
    if (!button || button.style.display === 'none') return;

    event.preventDefault();
    event.stopPropagation();
    if (typeof event.stopImmediatePropagation === 'function') event.stopImmediatePropagation();
    navigate(button.dataset.view);
  }

  // Deze listener blijft inline in index.html en is dus niet afhankelijk van
  // machinepark-build.js. Capture zorgt dat oudere listeners hem niet overschrijven.
  document.addEventListener('click', interceptNavigation, true);
  document.addEventListener('touchend', interceptNavigation, { capture: true, passive: false });
  window.machineparkInlineNavigate = navigate;
})();
</script>
'''
    body_pos = index.rfind('</body>')
    if body_pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor inline navigatie-bootstrap')
    index = index[:body_pos] + bootstrap + index[body_pos:]
    INDEX_PATH.write_text(index, encoding='utf-8')

built = INDEX_PATH.read_text(encoding='utf-8')
required = [
    BOOTSTRAP_MARKER,
    'data-machinepark-navigation-bootstrap="v1"',
    "document.addEventListener('click', interceptNavigation, true)",
    "document.addEventListener('touchend', interceptNavigation, { capture: true, passive: false })",
    "document.querySelectorAll('.view').forEach",
    'target.classList.add(\'active\')',
    'window.machineparkInlineNavigate = navigate',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: inline navigatie-bootstrap ontbreekt ({needle})')

# Dit script mag expres NIET als feature-buildfix gemarkeerd zijn: extract-build-assets.py
# moet het in index.html laten staan als onafhankelijke laatste verdedigingslaag.
bootstrap_start = built.index(BOOTSTRAP_MARKER)
bootstrap_end = built.index('</script>', bootstrap_start)
bootstrap_block = built[bootstrap_start:bootstrap_end]
if 'data-machinepark-build-fix=' in bootstrap_block:
    raise SystemExit('Buildvalidatie mislukt: inline navigatie-bootstrap zou uit HTML worden geëxtraheerd')

print('[Machinepark] inline tabnavigatie fallback actief')
