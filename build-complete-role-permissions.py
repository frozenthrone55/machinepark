from pathlib import Path

ROOT = Path(__file__).resolve().parent
MARKER = 'machinepark-complete-role-permissions-v1'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    return text.replace(old, new, 1)


# 1) Synology: volledige permission catalog + veilige migratie van bestaande rollen.
path = 'synology/api/_role-lib.php'
text = read(path)
if MARKER not in text:
    text = replace_once(
        text,
        "        ['group'=>'Weergave','key'=>'view.actions','label'=>'Acties bekijken'],",
        "        ['group'=>'Weergave','key'=>'view.actions','label'=>'ToDo bekijken'],",
        'Synology ToDo weergavelabel',
    )
    text = replace_once(
        text,
        "        ['group'=>'Weergave','key'=>'view.settings','label'=>'Beheer bekijken'],\n",
        "        ['group'=>'Weergave','key'=>'view.settings','label'=>'Beheer bekijken'],\n"
        "        ['group'=>'ToDo','key'=>'actions.add','label'=>'ToDo toevoegen'],\n"
        "        ['group'=>'ToDo','key'=>'actions.edit','label'=>'ToDo wijzigen en koppelen'],\n"
        "        ['group'=>'ToDo','key'=>'actions.complete','label'=>'ToDo-status wijzigen en afronden'],\n"
        "        ['group'=>'ToDo','key'=>'actions.delete','label'=>'ToDo verwijderen'],\n",
        'Synology ToDo handelingen',
    )
    text = replace_once(
        text,
        "        ['group'=>'Handleidingen','key'=>'manuals.manage','label'=>'Handleidingen beheren'],\n",
        "        ['group'=>'Handleidingen','key'=>'manuals.manage','label'=>'Handleidingen beheren'],\n"
        "        ['group'=>'Werkbonnen','key'=>'workorders.manage','label'=>'Werkbontemplates beheren'],\n",
        'Synology werkbonrecht',
    )
    text = replace_once(
        text,
        "        ['group'=>'Algemeen','key'=>'print','label'=>'Pagina’s en verslagen afdrukken'],\n",
        "        ['group'=>'Algemeen','key'=>'print','label'=>'Pagina’s en verslagen afdrukken'],\n"
        "        ['group'=>'Algemeen','key'=>'mail','label'=>'PDF-verslagen mailen of delen'],\n",
        'Synology mailrecht',
    )
    text = replace_once(
        text,
        "            'breakdowns.add','breakdowns.edit','breakdowns.delete',\n            'parts.add','parts.edit','parts.stock','parts.delete','parts.export','print'\n",
        "            'breakdowns.add','breakdowns.edit','breakdowns.delete',\n"
        "            'actions.add','actions.edit','actions.complete','actions.delete',\n"
        "            'parts.add','parts.edit','parts.stock','parts.delete','parts.export','print','mail'\n",
        'standaardrechten gebruiker',
    )
    text = replace_once(
        text,
        "            'breakdowns.add','breakdowns.edit','breakdowns.delete','print'\n",
        "            'breakdowns.add','breakdowns.edit','breakdowns.delete','print','mail'\n",
        'standaardrechten technieker',
    )
    text = replace_once(
        text,
        "            'view.dashboard','view.actions','view.parts','parts.add','parts.edit','parts.stock','parts.delete','parts.export','print'\n",
        "            'view.dashboard','view.actions','view.parts','actions.add','actions.edit','actions.complete','actions.delete','parts.add','parts.edit','parts.stock','parts.delete','parts.export','print','mail'\n",
        'standaardrechten magazijnier',
    )
    text = replace_once(
        text,
        "            } elseif ($existing && !empty($existing['builtIn'])) {\n                $permissions[$key] = !empty($existing['permissions'][$key]);\n",
        "            } elseif (strpos($key, 'actions.') === 0) {\n"
        "                // Bestaande rollen met ToDo-toegang behouden hun vroegere gedrag\n"
        "                // tot de nieuwe afzonderlijke ToDo-schakelaars expliciet worden opgeslagen.\n"
        "                $permissions[$key] = !empty($source['view.actions'])\n"
        "                    || ($existing && !empty($existing['builtIn']) && !empty($existing['permissions'][$key]));\n"
        "            } elseif ($key === 'mail') {\n"
        "                // Voorheen was mailen/delen beschikbaar samen met afdrukken.\n"
        "                $permissions[$key] = !empty($source['print'])\n"
        "                    || ($existing && !empty($existing['builtIn']) && !empty($existing['permissions'][$key]));\n"
        "            } elseif ($existing && !empty($existing['builtIn'])) {\n"
        "                $permissions[$key] = !empty($existing['permissions'][$key]);\n",
        'Synology compatibiliteit nieuwe rechten',
    )
    text += f"\n// {MARKER}\n"
    write(path, text)


# 2) Netlify: zelfde catalog, defaults en migratie als Synology.
path = 'netlify/functions/_shared/permissions.mjs'
text = read(path)
if MARKER not in text:
    text = replace_once(
        text,
        "  { group: 'Weergave', key: 'view.faults', label: 'Storingen bekijken' },\n  { group: 'Weergave', key: 'view.parts', label: 'Onderdelen bekijken' },",
        "  { group: 'Weergave', key: 'view.faults', label: 'Storingen bekijken' },\n"
        "  { group: 'Weergave', key: 'view.manuals', label: 'Handleidingen bekijken' },\n"
        "  { group: 'Weergave', key: 'view.actions', label: 'ToDo bekijken' },\n"
        "  { group: 'Weergave', key: 'view.parts', label: 'Onderdelen bekijken' },",
        'Netlify ontbrekende weergaverechten',
    )
    text = replace_once(
        text,
        "  { group: 'Weergave', key: 'view.settings', label: 'Beheer bekijken' },\n",
        "  { group: 'Weergave', key: 'view.settings', label: 'Beheer bekijken' },\n"
        "  { group: 'ToDo', key: 'actions.add', label: 'ToDo toevoegen' },\n"
        "  { group: 'ToDo', key: 'actions.edit', label: 'ToDo wijzigen en koppelen' },\n"
        "  { group: 'ToDo', key: 'actions.complete', label: 'ToDo-status wijzigen en afronden' },\n"
        "  { group: 'ToDo', key: 'actions.delete', label: 'ToDo verwijderen' },\n",
        'Netlify ToDo handelingen',
    )
    text = replace_once(
        text,
        "  { group: 'Storingen', key: 'faults.manage', label: 'Storingsbibliotheek beheren' },\n",
        "  { group: 'Storingen', key: 'faults.manage', label: 'Storingsbibliotheek beheren' },\n"
        "  { group: 'Handleidingen', key: 'manuals.manage', label: 'Handleidingen beheren' },\n"
        "  { group: 'Werkbonnen', key: 'workorders.manage', label: 'Werkbontemplates beheren' },\n",
        'Netlify handleiding en werkbonrechten',
    )
    text = replace_once(
        text,
        "  { group: 'Algemeen', key: 'print', label: 'Pagina’s en verslagen afdrukken' },\n",
        "  { group: 'Algemeen', key: 'print', label: 'Pagina’s en verslagen afdrukken' },\n"
        "  { group: 'Algemeen', key: 'mail', label: 'PDF-verslagen mailen of delen' },\n",
        'Netlify mailrecht',
    )
    text = replace_once(
        text,
        "  { id: 'gebruiker', label: 'Gebruiker', builtIn: true, permissions: permissionSet(['view.dashboard','view.devices','view.maintenance','view.breakdowns','view.faults','view.parts','devices.add','devices.edit','devices.delete','maintenance.add','maintenance.edit','maintenance.delete','breakdowns.add','breakdowns.edit','breakdowns.delete','parts.add','parts.edit','parts.stock','parts.delete','parts.export','print']) },",
        "  { id: 'gebruiker', label: 'Gebruiker', builtIn: true, permissions: permissionSet(['view.dashboard','view.devices','view.maintenance','view.breakdowns','view.faults','view.manuals','view.actions','view.parts','devices.add','devices.edit','devices.delete','maintenance.add','maintenance.edit','maintenance.delete','breakdowns.add','breakdowns.edit','breakdowns.delete','actions.add','actions.edit','actions.complete','actions.delete','parts.add','parts.edit','parts.stock','parts.delete','parts.export','print','mail']) },",
        'Netlify standaardrechten gebruiker',
    )
    text = replace_once(
        text,
        "  { id: 'technieker', label: 'Technieker', builtIn: true, permissions: permissionSet(['view.dashboard','view.devices','view.maintenance','view.breakdowns','view.faults','view.parts','devices.statusNotes','maintenance.add','maintenance.edit','maintenance.delete','breakdowns.add','breakdowns.edit','breakdowns.delete','print']) },",
        "  { id: 'technieker', label: 'Technieker', builtIn: true, permissions: permissionSet(['view.dashboard','view.devices','view.maintenance','view.breakdowns','view.faults','view.manuals','view.parts','devices.statusNotes','maintenance.add','maintenance.edit','maintenance.delete','breakdowns.add','breakdowns.edit','breakdowns.delete','print','mail']) },",
        'Netlify standaardrechten technieker',
    )
    text = replace_once(
        text,
        "  { id: 'magazijnier', label: 'Magazijnier', builtIn: true, permissions: permissionSet(['view.dashboard','view.parts','parts.add','parts.edit','parts.stock','parts.delete','parts.export','print']) },",
        "  { id: 'magazijnier', label: 'Magazijnier', builtIn: true, permissions: permissionSet(['view.dashboard','view.actions','view.parts','actions.add','actions.edit','actions.complete','actions.delete','parts.add','parts.edit','parts.stock','parts.delete','parts.export','print','mail']) },",
        'Netlify standaardrechten magazijnier',
    )
    text = replace_once(
        text,
        "      if (Object.prototype.hasOwnProperty.call(sourcePermissions, key)) return Boolean(sourcePermissions[key]);\n      return Boolean(existing?.builtIn && existing?.permissions?.[key]);",
        "      if (Object.prototype.hasOwnProperty.call(sourcePermissions, key)) return Boolean(sourcePermissions[key]);\n"
        "      if (key === 'view.manuals') return Boolean(sourcePermissions['view.devices'] || sourcePermissions['view.breakdowns'] || sourcePermissions['view.settings'] || (existing?.builtIn && existing?.permissions?.[key]));\n"
        "      if (key === 'manuals.manage') return Boolean(sourcePermissions['view.settings'] || (existing?.builtIn && existing?.permissions?.[key]));\n"
        "      if (key.startsWith('actions.')) return Boolean(sourcePermissions['view.actions'] || (existing?.builtIn && existing?.permissions?.[key]));\n"
        "      if (key === 'mail') return Boolean(sourcePermissions.print || (existing?.builtIn && existing?.permissions?.[key]));\n"
        "      return Boolean(existing?.builtIn && existing?.permissions?.[key]);",
        'Netlify compatibiliteit nieuwe rechten',
    )

    # ToDo-mutaties zijn server-side afzonderlijk afdwingbaar.
    text = replace_once(
        text,
        "  const devices = diffList(before.devices, after.devices); const maintenance = diffList(before.maintenance, after.maintenance); const breakdowns = diffList(before.breakdowns, after.breakdowns); const parts = diffList(before.parts, after.parts);",
        "  const devices = diffList(before.devices, after.devices); const maintenance = diffList(before.maintenance, after.maintenance); const breakdowns = diffList(before.breakdowns, after.breakdowns); const actions = diffList(before.actions, after.actions); const parts = diffList(before.parts, after.parts);",
        'Netlify action diff',
    )
    text = replace_once(
        text,
        "  const maintenanceStockMutation = serviceDiffPermission(maintenance, permissions, 'maintenance', 'onderhoud');\n  const breakdownStockMutation = serviceDiffPermission(breakdowns, permissions, 'breakdowns', 'depannage');\n  if (parts.added.length)",
        "  const maintenanceStockMutation = serviceDiffPermission(maintenance, permissions, 'maintenance', 'onderhoud');\n"
        "  const breakdownStockMutation = serviceDiffPermission(breakdowns, permissions, 'breakdowns', 'depannage');\n"
        "  if (actions.added.length) requirePermission(permissions, 'actions.add', 'Deze rol mag geen ToDo toevoegen.');\n"
        "  if (actions.removed.length) requirePermission(permissions, 'actions.delete', 'Deze rol mag geen ToDo verwijderen.');\n"
        "  const actionCompletionKeys = new Set(['status','completedDate','completedAt','completedById','completedByName','completedByEmail','completionNote','deviceId','location','history']);\n"
        "  const actionCompletionTriggers = new Set(['status','completedDate','completedAt','completedById','completedByName','completedByEmail','completionNote']);\n"
        "  for (const change of actions.changed) {\n"
        "    const completionChange = change.keys.some((key) => actionCompletionTriggers.has(key)) && change.keys.every((key) => actionCompletionKeys.has(key));\n"
        "    requirePermission(permissions, completionChange ? 'actions.complete' : 'actions.edit', completionChange ? 'Deze rol mag de ToDo-status niet wijzigen of afronden.' : 'Deze rol mag ToDo’s niet wijzigen of koppelen.');\n"
        "  }\n"
        "  if (parts.added.length)",
        'Netlify action mutation permissions',
    )
    text += f"\n// {MARKER}\n"
    write(path, text)


# 3) Synology centrale snapshot: dezelfde ToDo-mutatierechten afdwingen.
path = 'synology/api/machinepark-data.php'
text = read(path)
if MARKER not in text:
    text = replace_once(
        text,
        "    $breakdowns = mp_store_diff($before, $after, 'breakdowns');\n    $parts = mp_store_diff($before, $after, 'parts');",
        "    $breakdowns = mp_store_diff($before, $after, 'breakdowns');\n    $actions = mp_store_diff($before, $after, 'actions');\n    $parts = mp_store_diff($before, $after, 'parts');",
        'Synology action diff',
    )
    text = replace_once(
        text,
        "    if ($breakdowns['changed']) mp_require_permission($permissions, 'breakdowns.edit', 'Deze rol mag depannages niet wijzigen.');\n\n    if ($parts['added'])",
        "    if ($breakdowns['changed']) mp_require_permission($permissions, 'breakdowns.edit', 'Deze rol mag depannages niet wijzigen.');\n\n"
        "    if ($actions['added']) mp_require_permission($permissions, 'actions.add', 'Deze rol mag geen ToDo toevoegen.');\n"
        "    if ($actions['removed']) mp_require_permission($permissions, 'actions.delete', 'Deze rol mag geen ToDo verwijderen.');\n"
        "    $actionCompletionKeys = ['status','completedDate','completedAt','completedById','completedByName','completedByEmail','completionNote','deviceId','location','history'];\n"
        "    $actionCompletionTriggers = ['status','completedDate','completedAt','completedById','completedByName','completedByEmail','completionNote'];\n"
        "    foreach ($actions['changed'] as $change) {\n"
        "        $keys = isset($change['keys']) && is_array($change['keys']) ? $change['keys'] : [];\n"
        "        $completionChange = count(array_intersect($keys, $actionCompletionTriggers)) > 0 && count(array_diff($keys, $actionCompletionKeys)) === 0;\n"
        "        mp_require_permission($permissions, $completionChange ? 'actions.complete' : 'actions.edit', $completionChange ? 'Deze rol mag de ToDo-status niet wijzigen of afronden.' : 'Deze rol mag ToDo’s niet wijzigen of koppelen.');\n"
        "    }\n\n"
        "    if ($parts['added'])",
        'Synology action mutation permissions',
    )
    text += f"\n// {MARKER}\n"
    write(path, text)


# 4) ToDo-media: schrijven volgt ToDo toevoegen/wijzigen/verwijderen, niet enkel bekijken.
path = 'synology/api/action-photos.php'
text = read(path)
if MARKER not in text:
    text = replace_once(
        text,
        "if (!mp_photo_can($user, ['view.actions'])) mp_photo_json(['error'=>'Deze rol mag ToDo-foto’s niet wijzigen.'],403);",
        "if (!mp_photo_can($user, ['actions.add','actions.edit','actions.delete'])) mp_photo_json(['error'=>'Deze rol mag ToDo-media niet wijzigen.'],403);",
        'ToDo media permission',
    )
    text += f"\n// {MARKER}\n"
    write(path, text)


# 5) Werkbontemplates: niet langer hardcoded rolnaam, maar eigen schakelaar.
path = 'synology/api/work-order-templates.php'
text = read(path)
if MARKER not in text:
    text = replace_once(
        text,
        "$canManage = !empty($user['isOwner']) || (string)($user['role'] ?? '') === 'beheerder';",
        "$canManage = !empty($user['isOwner']) || !empty($permissions['workorders.manage']);",
        'Synology werkbon manage permission',
    )
    text = text.replace("Alleen een beheerder kan werkbonnen configureren.", "Deze rol mag werkbontemplates niet beheren.")
    text += f"\n// {MARKER}\n"
    write(path, text)

path = 'netlify/functions/work-order-templates.mjs'
text = read(path)
if MARKER not in text:
    text = replace_once(
        text,
        "function canManage(access) {\n  return Boolean(access?.owner || access?.role === 'beheerder');\n}",
        "function canManage(access) {\n  return Boolean(access?.owner || access?.permissions?.['workorders.manage']);\n}",
        'Netlify werkbon manage permission',
    )
    text = text.replace("Alleen een beheerder kan werkbonnen configureren.", "Deze rol mag werkbontemplates niet beheren.")
    text += f"\n// {MARKER}\n"
    write(path, text)


# 6) Finale UI: ToDo-handelingknoppen en mail/delen respecteren de schakelaars.
path = 'index.html'
index = read(path)
if f'data-machinepark-build-fix="{MARKER}"' not in index:
    index = replace_once(
        index,
        "  const ACTION_PHOTO_LIMIT = 10;\n",
        "  const ACTION_PHOTO_LIMIT = 10;\n"
        "  const actionCan = permission => !window.machineparkAccessReady || typeof window.machineparkHasPermission !== 'function' || Boolean(window.machineparkHasPermission(permission));\n",
        'actionCan helper',
    )

    guards = [
        ("  async function openActionEditor(id='',context={}) {\n", "    if(id ? !actionCan('actions.edit') : !actionCan('actions.add')){toast(id?'Deze rol mag ToDo’s niet wijzigen':'Deze rol mag geen ToDo toevoegen');return;}\n", 'ToDo editor'),
        ("  async function quickAddAction() {\n", "    if(!actionCan('actions.add')){toast('Deze rol mag geen ToDo toevoegen');return;}\n", 'ToDo quick add'),
        ("  async function openCompleteAction(id) {\n", "    if(!actionCan('actions.complete')){toast('Deze rol mag ToDo’s niet afronden');return;}\n", 'ToDo afronden'),
        ("  async function reopenAction(id) {\n", "    if(!actionCan('actions.complete')){toast('Deze rol mag de ToDo-status niet wijzigen');return;}\n", 'ToDo heropenen'),
        ("  async function setActionWorkStatus(id,status) {\n", "    if(!actionCan('actions.complete')){toast('Deze rol mag de ToDo-status niet wijzigen');return;}\n", 'ToDo werkstatus'),
        ("  async function deleteAction(id) {\n", "    if(!actionCan('actions.delete')){toast('Deze rol mag geen ToDo verwijderen');return;}\n", 'ToDo verwijderen'),
        ("  function printAction(id) {\n", "    if(!actionCan('print')){toast('Deze rol mag niet afdrukken');return;}\n", 'ToDo print'),
        ("  async function applyServiceDraftActionLinks(ctx,ids,finalized=false){\n", "    if(!actionCan('actions.edit'))throw new Error('Deze rol mag ToDo’s niet koppelen.');\n", 'service ToDo links'),
        ("  async function linkExistingActionToService(report) {\n", "    if(!actionCan('actions.edit')){toast('Deze rol mag ToDo’s niet koppelen');return;}\n", 'bestaande ToDo koppelen'),
        ("  async function unlinkActionFromService(actionId,report) {\n", "    if(!actionCan('actions.edit')){toast('Deze rol mag ToDo’s niet ontkoppelen');return;}\n", 'ToDo ontkoppelen'),
        ("  async function completeLinkedActionFromService(actionId,ctx={}){\n", "    if(!actionCan('actions.complete')){toast('Deze rol mag ToDo’s niet afronden');return false;}\n", 'gekoppelde ToDo afronden'),
        ("  window.machineparkOpenServiceDraftActionPicker=function(ctx){\n", "    if(!actionCan('view.actions')||!actionCan('actions.edit')){toast('Deze rol mag ToDo’s niet koppelen');return;}\n", 'serviceconcept ToDo picker'),
        ("  function renderLinkedServiceActions(report) {\n", "    if(!actionCan('view.actions')){document.querySelector('#modal .service-linked-actions')?.remove();return;}\n", 'gekoppelde ToDo zichtbaarheid'),
        ("  function openActionDetails(id) {\n", "    if(!actionCan('view.actions')){toast('Deze rol mag ToDo niet bekijken');return;}\n", 'ToDo detail view'),
    ]
    for signature, guard, label in guards:
        index = replace_once(index, signature, signature + guard, label)

    script = r'''
<script data-machinepark-build-fix="machinepark-complete-role-permissions-v1">
(() => {
  const can = key => !window.machineparkAccessReady || typeof window.machineparkHasPermission !== 'function' || Boolean(window.machineparkHasPermission(key));
  const MAIL_SELECTOR = '.page-mail-btn,.service-detail-mail-btn,.device-detail-mail-btn,.service-visit-mail-btn';
  function showByPermission(selector, permission) {
    document.querySelectorAll(selector).forEach(el => { el.style.display = can(permission) ? '' : 'none'; });
  }
  function applyCompletePermissions() {
    showByPermission('#actionQuickAdd,#actionNewFull', 'actions.add');
    const quick = document.getElementById('actionQuickInput');
    if (quick) { quick.disabled = !can('actions.add'); quick.title = can('actions.add') ? '' : 'Deze rol mag geen ToDo toevoegen.'; }
    showByPermission('[data-action-link],[data-service-action-unlink],[data-link-existing-service-action],.service-draft-action-button', 'actions.edit');
    showByPermission('[data-create-service-action]', 'actions.add');
    showByPermission('[data-action-complete],[data-service-action-complete],.service-action-complete-check', 'actions.complete');
    showByPermission(MAIL_SELECTOR, 'mail');
    const kpi = document.getElementById('kpiActionsCard');
    if (kpi) kpi.style.display = can('view.actions') ? '' : 'none';

    const modal = document.getElementById('modal');
    const heading = String(modal?.querySelector('.modal-head h3')?.textContent || '').trim().toLowerCase();
    if (heading === 'todo' || heading.startsWith('todo ·')) {
      modal.querySelectorAll('.modal-foot button').forEach(btn => {
        const label = String(btn.textContent || '').trim();
        if (label === 'Verwijderen') btn.style.display = can('actions.delete') ? '' : 'none';
        else if (label === 'Bewerken') btn.style.display = can('actions.edit') ? '' : 'none';
        else if (label === 'Heropenen' || label.includes('In behandeling') || label.includes('Nog te doen') || label.includes('Afronden')) btn.style.display = can('actions.complete') ? '' : 'none';
        else if (label === 'Afdrukken') btn.style.display = can('print') ? '' : 'none';
      });
    }
  }
  window.machineparkApplyCompleteRolePermissions = applyCompletePermissions;

  const previousApply = window.applyOperationalPermissions;
  if (typeof previousApply === 'function' && !previousApply.__completeRolePermissions) {
    const wrapped = function(...args) { const result = previousApply.apply(this,args); applyCompletePermissions(); return result; };
    wrapped.__completeRolePermissions = true;
    window.applyOperationalPermissions = wrapped;
    try { applyOperationalPermissions = wrapped; } catch (_) {}
  }

  document.addEventListener('click', event => {
    const mail = event.target.closest?.(MAIL_SELECTOR);
    if (mail && !can('mail')) {
      event.preventDefault(); event.stopImmediatePropagation();
      if (typeof toast === 'function') toast('Deze rol mag geen PDF-verslagen mailen of delen');
    }
  }, true);

  const observer = new MutationObserver(() => applyCompletePermissions());
  const start = () => { applyCompletePermissions(); observer.observe(document.body,{childList:true,subtree:true}); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true}); else start();
})();
</script>
'''
    body_pos = index.rfind('</body>')
    if body_pos < 0:
        raise SystemExit('Buildvalidatie mislukt: finale </body> ontbreekt voor complete rollenrechten')
    index = index[:body_pos] + script + index[body_pos:]
    write(path, index)


# Finale buildvalidatie: alle nieuwe schakelaars en afdwinging moeten aanwezig zijn.
combined = '\n'.join([
    read('synology/api/_role-lib.php'),
    read('netlify/functions/_shared/permissions.mjs'),
    read('synology/api/machinepark-data.php'),
    read('synology/api/action-photos.php'),
    read('synology/api/work-order-templates.php'),
    read('netlify/functions/work-order-templates.mjs'),
    read('index.html'),
])
for needle in [
    'actions.add','actions.edit','actions.complete','actions.delete',
    'workorders.manage','manuals.manage','view.manuals','view.actions',
    "key'=>'mail'", "key: 'mail'",
    'machinepark-complete-role-permissions-v1',
    'machineparkApplyCompleteRolePermissions',
    'Deze rol mag ToDo’s niet wijzigen of koppelen',
]:
    if needle not in combined:
        raise SystemExit(f'Buildvalidatie mislukt: compleet rollenrecht ontbreekt ({needle})')

print('[Machinepark] alle relevante rollenrechten compleet: ToDo, werkbonnen, handleidingen, mail/delen en bestaande functies')
