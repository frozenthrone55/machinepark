from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
MARKER = 'data-machinepark-build-fix="machinepark-complete-role-permissions-finalize-v1"'

index = INDEX.read_text(encoding='utf-8')

# De complete rollenbuilder plaatst defensieve function guards in het ToDo-script.
# De uiteindelijke beveiliging zit server-side; UI-beveiliging gebeurt in de losse
# rollenlaag. Verwijder daarom deze injecties weer uit het bestaande ToDo-script,
# zodat de bewezen ToDo-runtime byte-voor-byte dezelfde syntaxis behoudt.
removals = [
    "  const actionCan = permission => !window.machineparkAccessReady || typeof window.machineparkHasPermission !== 'function' || Boolean(window.machineparkHasPermission(permission));\n",
    "    if(id ? !actionCan('actions.edit') : !actionCan('actions.add')){toast(id?'Deze rol mag ToDo’s niet wijzigen':'Deze rol mag geen ToDo toevoegen');return;}\n",
    "    if(!actionCan('actions.add')){toast('Deze rol mag geen ToDo toevoegen');return;}\n",
    "    if(!actionCan('actions.complete')){toast('Deze rol mag ToDo’s niet afronden');return;}\n",
    "    if(!actionCan('actions.complete')){toast('Deze rol mag de ToDo-status niet wijzigen');return;}\n",
    "    if(!actionCan('actions.delete')){toast('Deze rol mag geen ToDo verwijderen');return;}\n",
    "    if(!actionCan('print')){toast('Deze rol mag niet afdrukken');return;}\n",
    "    if(!actionCan('actions.edit'))throw new Error('Deze rol mag ToDo’s niet koppelen.');\n",
    "    if(!actionCan('actions.edit')){toast('Deze rol mag ToDo’s niet koppelen');return;}\n",
    "    if(!actionCan('actions.edit')){toast('Deze rol mag ToDo’s niet ontkoppelen');return;}\n",
    "    if(!actionCan('actions.complete')){toast('Deze rol mag ToDo’s niet afronden');return false;}\n",
    "    if(!actionCan('view.actions')||!actionCan('actions.edit')){toast('Deze rol mag ToDo’s niet koppelen');return;}\n",
    "    if(!actionCan('view.actions')){document.querySelector('#modal .service-linked-actions')?.remove();return;}\n",
    "    if(!actionCan('view.actions')){toast('Deze rol mag ToDo niet bekijken');return;}\n",
]
for line in removals:
    index = index.replace(line, '')

if MARKER not in index:
    # Breid de bestaande capture-handler uit: ook wanneer een oude DOM-node nog
    # even zichtbaar is, wordt de handeling geblokkeerd vóór de originele handler.
    old = """  document.addEventListener('click', event => {
    const mail = event.target.closest?.(MAIL_SELECTOR);
    if (mail && !can('mail')) {
      event.preventDefault(); event.stopImmediatePropagation();
      if (typeof toast === 'function') toast('Deze rol mag geen PDF-verslagen mailen of delen');
    }
  }, true);"""
    new = """  document.addEventListener('click', event => {
    const deny = (permission,message) => {
      if (can(permission)) return false;
      event.preventDefault(); event.stopImmediatePropagation();
      if (typeof toast === 'function') toast(message);
      return true;
    };
    if (event.target.closest?.('#actionQuickAdd,#actionNewFull,[data-create-service-action],[data-action-device-new]') && deny('actions.add','Deze rol mag geen ToDo toevoegen')) return;
    if (event.target.closest?.('[data-action-link],[data-service-action-unlink],[data-link-existing-service-action],.service-draft-action-button') && deny('actions.edit','Deze rol mag ToDo’s niet wijzigen of koppelen')) return;
    if (event.target.closest?.('[data-action-complete],[data-service-action-complete],.service-action-complete-check') && deny('actions.complete','Deze rol mag de ToDo-status niet wijzigen of afronden')) return;
    const mail = event.target.closest?.(MAIL_SELECTOR);
    if (mail && deny('mail','Deze rol mag geen PDF-verslagen mailen of delen')) return;
  }, true);"""
    if index.count(old) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: capture-handler complete rollen niet uniek ({index.count(old)})')
    index = index.replace(old, new, 1)
    body_pos = index.rfind('</body>')
    if body_pos < 0:
        raise SystemExit('Buildvalidatie mislukt: finale </body> ontbreekt voor rollenmarker')
    index = index[:body_pos] + f'<meta {MARKER}>\n' + index[body_pos:]

# Functionele eindcontrole: serverrechten blijven in de build, ToDo-script bevat
# geen actionCan-injecties meer, en UI-capture dekt alle veranderhandelingen.
for forbidden in ["const actionCan = permission =>", "!actionCan('actions.", "!actionCan('view.actions')"]:
    if forbidden in index:
        raise SystemExit(f'Buildvalidatie mislukt: directe ToDo guard bleef achter ({forbidden})')
for needle in [MARKER, "deny('actions.add'", "deny('actions.edit'", "deny('actions.complete'", "deny('mail'"]:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: finale rollen-UI mist {needle}')

INDEX.write_text(index, encoding='utf-8')
print('[Machinepark] finale rollen-UI blokkeert ToDo en mail zonder bestaande ToDo-runtime te wijzigen')

# De Synology/Web Station-compatibiliteitslaag voor het daadwerkelijk opslaan van
# nieuwe rollen draait als laatste onderdeel van de rollenbuild.
reliability = ROOT / 'build-role-save-reliability.py'
if not reliability.exists():
    raise SystemExit('Buildvalidatie mislukt: build-role-save-reliability.py ontbreekt')
exec(compile(reliability.read_text(encoding='utf-8'), str(reliability), 'exec'))
