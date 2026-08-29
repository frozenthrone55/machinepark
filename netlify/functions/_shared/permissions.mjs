export const ROLE_VALUES = ['beheerder', 'gebruiker', 'technieker', 'magazijnier'];
export const ROLE_CONFIG_KEY = 'role-config-v1';

export const PERMISSION_CATALOG = [
  { group: 'Weergave', key: 'view.dashboard', label: 'Dashboard bekijken' },
  { group: 'Weergave', key: 'view.devices', label: 'Toestellen bekijken' },
  { group: 'Weergave', key: 'view.maintenance', label: 'Onderhoud bekijken' },
  { group: 'Weergave', key: 'view.breakdowns', label: 'Depannages bekijken' },
  { group: 'Weergave', key: 'view.parts', label: 'Onderdelen bekijken' },
  { group: 'Weergave', key: 'view.settings', label: 'Beheer bekijken' },
  { group: 'Toestellen', key: 'devices.add', label: 'Toestellen toevoegen' },
  { group: 'Toestellen', key: 'devices.edit', label: 'Toestellen volledig wijzigen' },
  { group: 'Toestellen', key: 'devices.statusNotes', label: 'Alleen status en notities wijzigen' },
  { group: 'Toestellen', key: 'devices.delete', label: 'Toestellen verwijderen' },
  { group: 'Toestellen', key: 'devices.import', label: 'Toestellen synchroniseren via Excel' },
  { group: 'Onderhoud', key: 'maintenance.add', label: 'Onderhoud registreren' },
  { group: 'Onderhoud', key: 'maintenance.edit', label: 'Onderhoud wijzigen' },
  { group: 'Onderhoud', key: 'maintenance.delete', label: 'Onderhoud verwijderen' },
  { group: 'Depannages', key: 'breakdowns.add', label: 'Depannages registreren' },
  { group: 'Depannages', key: 'breakdowns.edit', label: 'Depannages wijzigen' },
  { group: 'Depannages', key: 'breakdowns.delete', label: 'Depannages verwijderen' },
  { group: 'Onderdelen', key: 'parts.add', label: 'Onderdelen toevoegen' },
  { group: 'Onderdelen', key: 'parts.edit', label: 'Onderdeelgegevens wijzigen' },
  { group: 'Onderdelen', key: 'parts.stock', label: 'Voorraad aanpassen' },
  { group: 'Onderdelen', key: 'parts.delete', label: 'Onderdelen verwijderen' },
  { group: 'Onderdelen', key: 'parts.export', label: 'Onderdelen exporteren naar Excel' },
  { group: 'Onderdelen', key: 'parts.import', label: 'Stocktelling importeren via Excel' },
  { group: 'Algemeen', key: 'print', label: 'Pagina’s en verslagen afdrukken' },
  { group: 'Beheer', key: 'backup.export', label: 'Back-up maken' },
  { group: 'Beheer', key: 'backup.import', label: 'Back-up terugzetten' },
  { group: 'Beheer', key: 'users.manage', label: 'Gebruikers beheren' },
  { group: 'Beheer', key: 'audit.view', label: 'Wijzigingslogboek bekijken' },
  { group: 'Beheer', key: 'audit.undo', label: 'Wijzigingen ongedaan maken' },
  { group: 'Beheer', key: 'roles.manage', label: 'Rollen en rechten beheren' },
];

export const ALL_PERMISSION_KEYS = PERMISSION_CATALOG.map((item) => item.key);
function permissionSet(values = []) { return Object.fromEntries(ALL_PERMISSION_KEYS.map((key) => [key, values === 'all' || values.includes(key)])); }

const DEFAULT_ROLES = [
  { id: 'beheerder', label: 'Beheerder', builtIn: true, permissions: permissionSet('all') },
  { id: 'gebruiker', label: 'Gebruiker', builtIn: true, permissions: permissionSet(['view.dashboard','view.devices','view.maintenance','view.breakdowns','view.parts','devices.add','devices.edit','devices.delete','maintenance.add','maintenance.edit','maintenance.delete','breakdowns.add','breakdowns.edit','breakdowns.delete','parts.add','parts.edit','parts.stock','parts.delete','parts.export','print']) },
  { id: 'technieker', label: 'Technieker', builtIn: true, permissions: permissionSet(['view.dashboard','view.devices','view.maintenance','view.breakdowns','view.parts','devices.statusNotes','maintenance.add','maintenance.edit','maintenance.delete','breakdowns.add','breakdowns.edit','breakdowns.delete','print']) },
  { id: 'magazijnier', label: 'Magazijnier', builtIn: true, permissions: permissionSet(['view.dashboard','view.parts','parts.add','parts.edit','parts.stock','parts.delete','parts.export','print']) },
];

export function defaultRoleConfig() { return { version: 1, roles: DEFAULT_ROLES.map((role) => ({ ...role, permissions: { ...role.permissions } })) }; }
export function sanitizeRoleId(value) { return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 50); }
export function normalizeRoleConfig(config) {
  const fallback = defaultRoleConfig();
  const input = Array.isArray(config?.roles) ? config.roles : [];
  const byId = new Map();
  for (const base of fallback.roles) byId.set(base.id, { ...base, permissions: { ...base.permissions } });
  for (const item of input) {
    const id = sanitizeRoleId(item?.id); if (!id) continue;
    const existing = byId.get(id);
    const label = String(item?.label || existing?.label || id).trim().slice(0, 80) || id;
    const permissions = permissionSet(ALL_PERMISSION_KEYS.filter((key) => Boolean(item?.permissions?.[key])));
    byId.set(id, { id, label, builtIn: Boolean(existing?.builtIn), permissions });
  }
  return { version: 1, roles: [...byId.values()] };
}
export function roleDefinition(roleValue, config) { const normalized = normalizeRoleConfig(config); const id = sanitizeRoleId(roleValue); return normalized.roles.find((role) => role.id === id) || normalized.roles.find((role) => role.id === 'gebruiker'); }
export function normalizeRole(value, { owner = false, config = null } = {}) { if (owner) return 'beheerder'; return roleDefinition(value, config)?.id || 'gebruiker'; }
export function roleLabel(role, config = null) { return roleDefinition(role, config)?.label || 'Gebruiker'; }
export function permissionsForRole(roleValue, config = null, { owner = false } = {}) { if (owner) return permissionSet('all'); return { ...roleDefinition(roleValue, config).permissions }; }
export function hasPermission(roleValue, permission, config = null, { owner = false } = {}) { return Boolean(permissionsForRole(roleValue, config, { owner })[permission]); }
export function validSnapshot(data) { return Boolean(data && data.app === 'Machinepark' && Number(data.schema) === 1 && Array.isArray(data.parts) && Array.isArray(data.devices) && Array.isArray(data.maintenance) && Array.isArray(data.breakdowns)); }

function stable(value) { return JSON.stringify(value); }
function changedRecordKeys(before, after) { const keys = new Set([...Object.keys(before || {}), ...Object.keys(after || {})]); return [...keys].filter((key) => stable(before?.[key]) !== stable(after?.[key])); }
function diffList(beforeList = [], afterList = []) {
  const before = new Map(beforeList.map((x) => [x.id, x])); const after = new Map(afterList.map((x) => [x.id, x]));
  const added = [], removed = [], changed = [];
  for (const [id, item] of after) { if (!before.has(id)) added.push(item); else { const keys = changedRecordKeys(before.get(id), item).filter((key) => key !== 'updatedAt'); if (keys.length) changed.push({ id, before: before.get(id), after: item, keys }); } }
  for (const [id, item] of before) if (!after.has(id)) removed.push(item);
  return { added, removed, changed };
}
function deny(message) { throw Object.assign(new Error(message), { status: 403 }); }
function requirePermission(permissions, key, message) { if (!permissions[key]) deny(message); }
function validateDevicePhotos(devices = []) {
  for (const device of devices) {
    if (device?.devicePhotos !== undefined && !Array.isArray(device.devicePhotos)) {
      throw Object.assign(new Error('Toestelfoto’s moeten als een geldige fotolijst worden opgeslagen.'), { status: 400 });
    }
    const photos = Array.isArray(device?.devicePhotos) ? device.devicePhotos : [];
    if (photos.length > 3) throw Object.assign(new Error('Een toestel kan maximaal 3 foto’s bevatten.'), { status: 400 });
    if (photos.some((src) => typeof src !== 'string' || !src.trim())) {
      throw Object.assign(new Error('Een toestelfoto bevat ongeldige gegevens.'), { status: 400 });
    }
    if (photos.length) {
      const index = Number(device?.deviceOverviewPhotoIndex ?? 0);
      if (!Number.isInteger(index) || index < 0 || index >= photos.length) {
        throw Object.assign(new Error('De gekozen overzichtsfoto van het toestel is ongeldig.'), { status: 400 });
      }
    }
  }
}

export function assertSnapshotWriteAllowed(before, after, roleValue, config = null, { owner = false } = {}) {
  if (!validSnapshot(after)) throw Object.assign(new Error('Ongeldige Machinepark-gegevens.'), { status: 400 });
  validateDevicePhotos(after.devices);
  const role = normalizeRole(roleValue, { owner, config }); const permissions = permissionsForRole(role, config, { owner });
  if (!before) { if (owner || role === 'beheerder') return true; deny('Alleen de hoofdbeheerder of een beheerder kan de centrale database initialiseren.'); }
  const devices = diffList(before.devices, after.devices); const maintenance = diffList(before.maintenance, after.maintenance); const breakdowns = diffList(before.breakdowns, after.breakdowns); const parts = diffList(before.parts, after.parts);
  if (devices.added.length) requirePermission(permissions, 'devices.add', role === 'magazijnier' ? 'Een magazijnier kan alleen onderdelen en voorraad wijzigen.' : 'Deze rol mag geen toestellen toevoegen.');
  if (devices.removed.length) requirePermission(permissions, 'devices.delete', role === 'magazijnier' ? 'Een magazijnier kan alleen onderdelen en voorraad wijzigen.' : 'Deze rol mag geen toestellen verwijderen.');
  for (const change of devices.changed) { const statusNotesOnly = change.keys.every((key) => ['status', 'notes'].includes(key)); if (statusNotesOnly && (permissions['devices.statusNotes'] || permissions['devices.edit'])) continue; if (!permissions['devices.edit']) { if (role === 'magazijnier') deny('Een magazijnier kan alleen onderdelen en voorraad wijzigen.'); if (role === 'technieker') deny('Een technieker kan bij toestellen alleen status en notities wijzigen.'); deny('Deze rol mag toestelgegevens niet volledig wijzigen.'); } }
  if (maintenance.added.length) requirePermission(permissions, 'maintenance.add', 'Deze rol mag geen onderhoud registreren.');
  if (maintenance.removed.length) requirePermission(permissions, 'maintenance.delete', 'Deze rol mag geen onderhoud verwijderen.');
  if (maintenance.changed.length) requirePermission(permissions, 'maintenance.edit', 'Deze rol mag onderhoud niet wijzigen.');
  if (breakdowns.added.length) requirePermission(permissions, 'breakdowns.add', 'Deze rol mag geen depannages registreren.');
  if (breakdowns.removed.length) requirePermission(permissions, 'breakdowns.delete', 'Deze rol mag geen depannages verwijderen.');
  if (breakdowns.changed.length) requirePermission(permissions, 'breakdowns.edit', 'Deze rol mag depannages niet wijzigen.');
  if (parts.added.length) requirePermission(permissions, 'parts.add', 'Deze rol mag geen onderdelen toevoegen.');
  if (parts.removed.length) requirePermission(permissions, 'parts.delete', 'Deze rol mag geen onderdelen verwijderen.');
  const serviceMutationAllowed = (maintenance.added.length && permissions['maintenance.add']) || (maintenance.changed.length && permissions['maintenance.edit']) || (maintenance.removed.length && permissions['maintenance.delete']) || (breakdowns.added.length && permissions['breakdowns.add']) || (breakdowns.changed.length && permissions['breakdowns.edit']) || (breakdowns.removed.length && permissions['breakdowns.delete']);
  for (const change of parts.changed) { const stockOnly = change.keys.every((key) => key === 'stock'); if (stockOnly && (permissions['parts.stock'] || permissions['parts.edit'] || serviceMutationAllowed)) continue; if (!permissions['parts.edit']) { if (role === 'technieker') deny('Een technieker kan bij onderdelen alleen de voorraad wijzigen via gebruikte onderdelen.'); deny('Deze rol mag onderdeelgegevens niet wijzigen.'); } }
  return true;
}
