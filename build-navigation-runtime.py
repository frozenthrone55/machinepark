from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="navigation-runtime-v2"'

if MARKER not in index:
    script = r'''
<script __BUILD_MARKER__>
(() => {
  const originalSwitchView = window.switchView;

  function safePageMeta(view) {
    try {
      const meta = typeof pageMeta === 'function' ? pageMeta(view) : null;
      if (Array.isArray(meta) && meta.length >= 2) return meta;
    } catch (error) {
      console.warn('[Machinepark] paginametadata kon niet worden geladen', error);
    }
    const fallback = {
      dashboard: ['Dashboard', 'Overzicht van service, storingen en voorraad.'],
      devices: ['Toestellen', 'Beheer alle koffietoestellen en hun onderhoudsplanning.'],
      maintenance: ['Onderhoud', 'Registreer halfjaarlijkse en jaarlijkse servicebeurten.'],
      breakdowns: ['Depannages', 'Volg storingen van melding tot oplossing op.'],
      parts: ['Onderdelen', 'Voorraad en onderdelen.'],
      faults: ['Storingen', 'Zoek storingscodes, storingen en oplossingen per merk of model.'],
      manuals: ['Handleidingen', 'Technische PDF-handleidingen per merk, model of toestel.'],
      settings: ['Beheer', 'Back-up, import en instellingen.'],
    };
    return fallback[view] || ['Machinepark', ''];
  }

  function safeCall(label, fn) {
    try {
      if (typeof fn === 'function') fn();
    } catch (error) {
      console.error(`[Machinepark] ${label} mislukt`, error);
    }
  }

  function setStateView(view) {
    try {
      if (typeof state !== 'undefined' && state) state.view = view;
    } catch (error) {
      console.warn('[Machinepark] view-state kon niet worden bijgewerkt', error);
    }
  }

  function activateView(view) {
    let nextView = String(view || '').trim();
    if (nextView === 'settings' && !window.machineparkIsAdmin) nextView = 'dashboard';

    const target = document.getElementById(`view-${nextView}`);
    if (!target) {
      console.warn('[Machinepark] onbekend tabblad genegeerd:', nextView);
      return false;
    }

    // Wissel EERST de zichtbare DOM. Dit werkt zelfs wanneer de grote basis-JS
    // eerder is uitgevallen en state/renderfuncties daardoor niet beschikbaar zijn.
    document.querySelectorAll('.view').forEach((node) => node.classList.remove('active'));
    target.classList.add('active');
    document.querySelectorAll('.nav [data-view]').forEach((button) => {
      button.classList.toggle('active', button.dataset.view === nextView);
    });

    setStateView(nextView);

    const [title, subtitle] = safePageMeta(nextView);
    const titleNode = document.getElementById('pageTitle');
    const subtitleNode = document.getElementById('pageSubtitle');
    if (titleNode) titleNode.textContent = title;
    if (subtitleNode) subtitleNode.textContent = subtitle;

    safeCall('zoekbalk configureren', () => {
      if (typeof configureSearchForView === 'function') configureSearchForView(nextView);
    });
    safeCall('tabblad renderen', () => {
      if (typeof renderAll === 'function') renderAll();
    });

    if (nextView === 'faults') {
      safeCall('storingen renderen', window.machineparkRenderFaultLibrary);
    } else if (nextView === 'manuals') {
      safeCall('handleidingen renderen', window.machineparkRenderManualLibrary);
    } else if (nextView === 'settings' && window.machineparkIsAdmin) {
      safeCall('beheer laden', typeof loadAdminPanels === 'function' ? loadAdminPanels : null);
    }

    return true;
  }

  window.machineparkNavigate = activateView;
  window.switchView = activateView;

  // Houd de globale function-binding en window-property gelijk voor inline onclick.
  try { switchView = activateView; } catch (_) {}

  // Capture vóór alle oudere click/touch handlers en inline onclick. Daardoor kan
  // een oude of kapotte listener de navigatie niet meer terug naar Dashboard sturen.
  function handleNavigationEvent(event) {
    const source = event.target && event.target.nodeType === 1
      ? event.target
      : event.target?.parentElement;
    const button = source?.closest?.('.nav [data-view]');
    if (!button) return;
    if (button.style.display === 'none') return;

    event.preventDefault();
    event.stopPropagation();
    if (typeof event.stopImmediatePropagation === 'function') event.stopImmediatePropagation();
    activateView(button.dataset.view);
  }

  document.addEventListener('click', handleNavigationEvent, true);
  document.addEventListener('touchend', handleNavigationEvent, { capture: true, passive: false });

  window.machineparkOriginalSwitchView = originalSwitchView;
})();
</script>
'''.replace('__BUILD_MARKER__', MARKER)

    body_pos = index.rfind('</body>')
    if body_pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor navigatie-runtime')
    index = index[:body_pos] + script + index[body_pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'window.switchView = activateView',
    'window.machineparkNavigate = activateView',
    "document.getElementById(`view-${nextView}`)",
    "document.querySelectorAll('.nav [data-view]')",
    "faults: ['Storingen'",
    "manuals: ['Handleidingen'",
    'window.machineparkRenderFaultLibrary',
    'window.machineparkRenderManualLibrary',
    "if (typeof renderAll === 'function') renderAll()",
    "document.addEventListener('click', handleNavigationEvent, true)",
    "document.addEventListener('touchend', handleNavigationEvent, { capture: true, passive: false })",
    'event.stopImmediatePropagation()',
    "if (typeof state !== 'undefined' && state) state.view = view",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: navigatie-runtime ontbreekt ({needle})')

print('[Machinepark] tabnavigatie runtime v2: capture-handler + DOM-first fallback actief')
