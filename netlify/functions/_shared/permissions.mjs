export const ROLE_VALUES = ['beheerder', 'gebruiker', 'technieker', 'magazijnier'];

export function normalizeRole(value, { owner = false } = {}) {
  if (owner) return 'beheerder';
  const role = String(value || '').trim().toLowerCase();
  return ROLE_VALUES.includes(role) ? role : 'gebruiker';
}

export function roleLabel(role) {
  return ({
    beheerder: 'Beheerder',
    gebruiker: 'Gebruiker',
    technieker: 'Technieker',
    magazijnier: 'Magazijnier',
  })[normalizeRole(role)] || 'Gebruiker';
}

export function validSnapshot(data) {
  return Boolean(
    data &&
    data.app === 'Machinepark' &&
    Number(data.schema) === 1 &&
    Array.isArray(data.parts) &&
    Array.isArray(data.devices) &&
    Array.isArray(data.maintenance) &&
    Array.isArray(data.breakdowns)
  );
}

function stable(value) {
  return JSON.stringify(value);
}

function changedStores(before, after) {
  const stores = ['devices', 'parts', 'maintenance', 'breakdowns'];
  return stores.filter((store) => stable(before?.[store] || []) !== stable(after?.[store] || []));
}

function changedRecordKeys(before, after) {
  const keys = new Set([...Object.keys(before || {}), ...Object.keys(after || {})]);
  return [...keys].filter((key) => stable(before?.[key]) !== stable(after?.[key]));
}

function onlyAllowedRecordChanges(beforeList = [], afterList = [], allowedKeys = []) {
  const allowed = new Set([...allowedKeys, 'updatedAt']);
  const beforeMap = new Map(beforeList.map((item) => [item.id, item]));
  const afterMap = new Map(afterList.map((item) => [item.id, item]));
  if (beforeMap.size !== afterMap.size) return false;
  for (const [id, before] of beforeMap) {
    const after = afterMap.get(id);
    if (!after) return false;
    if (changedRecordKeys(before, after).some((key) => !allowed.has(key))) return false;
  }
  return true;
}

export function assertSnapshotWriteAllowed(before, after, roleValue) {
  const role = normalizeRole(roleValue);
  if (!validSnapshot(after)) {
    throw Object.assign(new Error('Ongeldige Machinepark-gegevens.'), { status: 400 });
  }

  // Hoofdbeheerder en de bestaande standaardrol behouden alle operationele rechten.
  if (role === 'beheerder' || role === 'gebruiker') return true;
  if (!before) {
    throw Object.assign(new Error('Alleen een beheerder of gebruiker kan de centrale database initialiseren.'), { status: 403 });
  }

  const stores = changedStores(before, after);

  if (role === 'magazijnier') {
    if (stores.some((store) => store !== 'parts')) {
      throw Object.assign(new Error('Een magazijnier kan alleen onderdelen en voorraad wijzigen.'), { status: 403 });
    }
    return true;
  }

  if (role === 'technieker') {
    const allowedStores = new Set(['maintenance', 'breakdowns', 'parts', 'devices']);
    if (stores.some((store) => !allowedStores.has(store))) {
      throw Object.assign(new Error('Deze wijziging valt buiten de rechten van een technieker.'), { status: 403 });
    }
    if (stores.includes('parts') && !onlyAllowedRecordChanges(before.parts, after.parts, ['stock'])) {
      throw Object.assign(new Error('Een technieker kan bij onderdelen alleen de voorraad wijzigen via gebruikte onderdelen.'), { status: 403 });
    }
    if (stores.includes('devices') && !onlyAllowedRecordChanges(before.devices, after.devices, ['status', 'notes'])) {
      throw Object.assign(new Error('Een technieker kan bij toestellen alleen status en notities wijzigen.'), { status: 403 });
    }
    return true;
  }

  throw Object.assign(new Error('Onbekende gebruikersrol.'), { status: 403 });
}
