from pathlib import Path

ROOT = Path(__file__).resolve().parent
frontend_path = ROOT / 'fault-library.js'
endpoint_path = ROOT / 'netlify/functions/fault-library.mjs'
index_path = ROOT / 'index.html'

frontend = frontend_path.read_text(encoding='utf-8')
endpoint = endpoint_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

SERVER_MARKER = "const LATTIZ2_EXCEL_SEED_KEY = 'migration/lattiz2-excel-storingen-2026-09-02-v1';"
FRONT_MARKER = '// machinepark-fault-excel-extra-fields-v1'


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    return text.replace(old, new, 1)


if SERVER_MARKER not in endpoint:
    endpoint = replace_once(
        endpoint,
        "const CONFIG_KEY = 'fault-library-v1';",
        "import { LATTIZ2_FAULT_SEED_2026_09_02 } from './_shared/lattiz2-fault-seed.mjs';\n\nconst CONFIG_KEY = 'fault-library-v1';",
        'Lattiz 2 seed-import',
    )
    endpoint = replace_once(
        endpoint,
        'const MAX_FAULTS = 5000;',
        "const MAX_FAULTS = 5000;\n" + SERVER_MARKER,
        'Lattiz 2 seed-migratiesleutel',
    )
    endpoint = replace_once(
        endpoint,
        "    description: cleanText(fault?.description, 1600),\n    symptoms: cleanLines(fault?.symptoms, 30, 500),\n    causes: cleanLines(fault?.causes, 30, 500),\n    solutions: cleanLines(fault?.solutions, 40, 800),\n    notes: cleanText(fault?.notes, 2000),",
        "    description: cleanText(fault?.description, 1600),\n    message: cleanText(fault?.message, 1600),\n    solution1: cleanText(fault?.solution1, 1200),\n    solution2: cleanText(fault?.solution2, 1200),\n    symptoms: cleanLines(fault?.symptoms, 30, 500),\n    causes: cleanLines(fault?.causes, 30, 500),\n    solutions: cleanLines(fault?.solutions, 40, 800),\n    notes: cleanText(fault?.notes, 2000),",
        'nieuwe storingsvelden in sanitizer',
    )

    helper = r'''

function faultExcelSeedNorm(value) {
  return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase().replace(/\s+/g, ' ');
}

function faultExcelSeedKey(fault) {
  return [fault?.code, fault?.category, fault?.name, fault?.brand, fault?.model].map(faultExcelSeedNorm).join('|');
}

async function writeLattiz2ExcelSeedAudit(store, auth, added, updated) {
  try {
    const at = new Date().toISOString();
    const id = crypto.randomUUID();
    const email = primaryEmailOf(auth.user) || auth.sub;
    await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, {
      id,
      at,
      userId: auth.sub,
      userEmail: email,
      userName: [auth.user?.firstName, auth.user?.lastName].filter(Boolean).join(' '),
      userRole: auth.role,
      changeCount: Math.max(1, added + updated),
      changes: [{
        entityType: 'Storingen',
        entityId: 'lattiz2-excel-2026-09-02',
        entityLabel: 'Lattiz 2 storingslijst uit Excel',
        action: 'centrale lijst bijgewerkt',
        fields: [
          { field: 'Excel-regels', before: '—', after: '191' },
          { field: 'Nieuwe storingen', before: '—', after: String(added) },
          { field: 'Bijgewerkte storingen', before: '—', after: String(updated) },
          { field: 'Nieuwe velden', before: '—', after: 'Melding, Oplossing 1, Oplossing 2' },
        ],
      }],
      truncated: false,
    }, { metadata: { at, userId: auth.sub, userEmail: email } });
  } catch (error) {
    console.error('Lattiz 2 Excel seed audit', error);
  }
}

async function applyLattiz2ExcelSeedOnce(store, access, entry, config) {
  if (!canManage(access)) return { entry, config, seed: null };
  const migration = await store.get(LATTIZ2_EXCEL_SEED_KEY, { type: 'json', consistency: 'strong' }).catch(() => null);
  if (migration?.done) return { entry, config, seed: migration };
  if (!Array.isArray(LATTIZ2_FAULT_SEED_2026_09_02) || LATTIZ2_FAULT_SEED_2026_09_02.length !== 191) {
    throw Object.assign(new Error('De ingebouwde Lattiz 2 Excel-dataset is onvolledig.'), { status: 500 });
  }

  const merged = [...config.faults];
  let added = 0;
  let updated = 0;

  for (const raw of LATTIZ2_FAULT_SEED_2026_09_02) {
    const seedId = cleanId(raw?.id);
    const seedKey = faultExcelSeedKey(raw);
    let index = merged.findIndex((item) => item.id === seedId);
    if (index < 0) index = merged.findIndex((item) => faultExcelSeedKey(item) === seedKey);
    const existing = index >= 0 ? merged[index] : null;
    // Bestaande extra kennisvelden blijven behouden; de Excel-kolommen overschrijven alleen hun eigen waarden.
    const fault = sanitizeFault({ ...existing, ...raw, id: existing?.id || seedId }, existing);
    if (existing) {
      merged[index] = fault;
      updated += 1;
    } else {
      merged.push(fault);
      added += 1;
    }
  }

  if (merged.length > MAX_FAULTS) throw Object.assign(new Error(`De storingsbibliotheek mag maximaal ${MAX_FAULTS} storingen bevatten.`), { status: 400 });
  let nextEntry = entry;
  let nextConfig = config;
  try {
    nextEntry = await saveConfig(store, { version: 1, faults: merged }, entry?.etag || null, entry?.etag || null);
    nextConfig = normalizeConfig(nextEntry.data);
  } catch (error) {
    if (error?.status === 409) return { entry, config, seed: null };
    throw error;
  }

  const seed = { done: true, at: new Date().toISOString(), rows: 191, added, updated };
  await store.setJSON(LATTIZ2_EXCEL_SEED_KEY, seed, { metadata: { type: 'one-time-migration' } });
  await writeLattiz2ExcelSeedAudit(store, access, added, updated);
  return { entry: nextEntry, config: nextConfig, seed };
}
'''
    endpoint = replace_once(endpoint, '\nexport default async (req) => {', helper + '\nexport default async (req) => {', 'Lattiz 2 seed-helper')

    old_get = "      const clearedAll = await applyOneTimeClearAllFaults(store, access, entry, config);\n      entry = clearedAll.entry;\n      config = clearedAll.config;\n      const etag = entry?.etag || null;\n      return json({ faults: config.faults, etag, canManage: canManage(access), lattizCleanup: migrated.cleanup, lattiz2Cleanup: cleanedLattiz2.cleanup, keepOnlyWaterselectorCleanup: cleanedGlobal.cleanup, clearAllFaultsCleanup: clearedAll.cleanup }, 200, etag ? { etag } : {});"
    new_get = "      const clearedAll = await applyOneTimeClearAllFaults(store, access, entry, config);\n      entry = clearedAll.entry;\n      config = clearedAll.config;\n      const excelSeed = await applyLattiz2ExcelSeedOnce(store, access, entry, config);\n      entry = excelSeed.entry;\n      config = excelSeed.config;\n      const etag = entry?.etag || null;\n      return json({ faults: config.faults, etag, canManage: canManage(access), lattizCleanup: migrated.cleanup, lattiz2Cleanup: cleanedLattiz2.cleanup, keepOnlyWaterselectorCleanup: cleanedGlobal.cleanup, clearAllFaultsCleanup: clearedAll.cleanup, lattiz2ExcelSeed: excelSeed.seed }, 200, etag ? { etag } : {});"
    endpoint = replace_once(endpoint, old_get, new_get, 'Lattiz 2 seed na centrale leegmaak')

    endpoint = replace_once(
        endpoint,
        "  return [fault?.code, fault?.name, fault?.brand, fault?.model].map(norm).join('|');",
        "  return [fault?.code, fault?.category, fault?.name, fault?.brand, fault?.model].map(norm).join('|');",
        'Excel-import sleutel inclusief categorie',
    )

if FRONT_MARKER not in frontend:
    frontend = replace_once(
        frontend,
        "  function faultSearchText(fault) {\n    return faultNorm([\n      fault?.code, fault?.name, fault?.category, fault?.brand, fault?.model,\n      fault?.description, ...(fault?.symptoms || []), ...(fault?.causes || []),\n      ...(fault?.solutions || []), fault?.notes,\n    ].filter(Boolean).join(' '));\n  }",
        "  // machinepark-fault-excel-extra-fields-v1\n  function faultSearchText(fault) {\n    return faultNorm([\n      fault?.code, fault?.name, fault?.category, fault?.brand, fault?.model,\n      fault?.description, fault?.message, fault?.solution1, fault?.solution2,\n      ...(fault?.symptoms || []), ...(fault?.causes || []), ...(fault?.solutions || []), fault?.notes,\n    ].filter(Boolean).join(' '));\n  }",
        'nieuwe velden in storingszoektekst',
    )
    frontend = replace_once(
        frontend,
        "      const solution = fault.solutions?.[0] || fault.description || '—';",
        "      const solution = fault.solution1 || fault.solution2 || fault.solutions?.[0] || fault.message || fault.description || '—';",
        'oplossingspreview nieuwe velden',
    )
    frontend = replace_once(
        frontend,
        "${textSection('Omschrijving', fault.description)}${listSection('Symptomen', fault.symptoms)}",
        "${textSection('Gedetailleerde omschrijving', fault.description)}${textSection('Melding', fault.message)}${listSection('Symptomen', fault.symptoms)}",
        'Melding in storingsdetails',
    )
    frontend = replace_once(
        frontend,
        "${listSection('Controle / oplossing', fault.solutions)}${textSection('Interne opmerkingen', fault.notes)}",
        "${textSection('Oplossing 1', fault.solution1)}${textSection('Oplossing 2', fault.solution2)}${listSection('Extra controle / oplossingen', fault.solutions)}${textSection('Interne opmerkingen', fault.notes)}",
        'Oplossing 1 en 2 in storingsdetails',
    )
    frontend = replace_once(frontend, '<label>Storing / korte omschrijving *</label>', '<label>Algemene omschrijving / storing *</label>', 'algemene omschrijving label')
    frontend = replace_once(frontend, '<label>Omschrijving</label><textarea name="description" maxlength="1600" placeholder="Wat betekent deze storing?">', '<label>Gedetailleerde omschrijving</label><textarea name="description" maxlength="1600" placeholder="Wat betekent deze storing?">', 'gedetailleerde omschrijving label')
    frontend = replace_once(
        frontend,
        "<textarea name=\"description\" maxlength=\"1600\" placeholder=\"Wat betekent deze storing?\">${esc(fault?.description || '')}</textarea></div><div class=\"field full\"><label>Symptomen</label>",
        "<textarea name=\"description\" maxlength=\"1600\" placeholder=\"Wat betekent deze storing?\">${esc(fault?.description || '')}</textarea></div><div class=\"field full\"><label>Melding</label><textarea name=\"message\" maxlength=\"1600\" placeholder=\"Melding die op het toestel verschijnt\">${esc(fault?.message || '')}</textarea></div><div class=\"field full\"><label>Symptomen</label>",
        'Melding in storingseditor',
    )
    frontend = replace_once(
        frontend,
        "<div class=\"field full\"><label>Controle / oplossingen</label><textarea name=\"solutions\" style=\"min-height:130px\" placeholder=\"Eén controle of oplossing per regel\">${esc((fault?.solutions || []).join('\\n'))}</textarea></div>",
        "<div class=\"field full\"><label>Oplossing 1</label><textarea name=\"solution1\" maxlength=\"1200\">${esc(fault?.solution1 || '')}</textarea></div><div class=\"field full\"><label>Oplossing 2</label><textarea name=\"solution2\" maxlength=\"1200\">${esc(fault?.solution2 || '')}</textarea></div><div class=\"field full\"><label>Extra controle / oplossingen</label><textarea name=\"solutions\" style=\"min-height:130px\" placeholder=\"Eén extra controle of oplossing per regel\">${esc((fault?.solutions || []).join('\\n'))}</textarea></div>",
        'Oplossing 1 en 2 in storingseditor',
    )
    frontend = replace_once(
        frontend,
        "          description: val(fd, 'description'),\n          symptoms: faultLines(val(fd, 'symptoms')),",
        "          description: val(fd, 'description'),\n          message: val(fd, 'message'),\n          solution1: val(fd, 'solution1'),\n          solution2: val(fd, 'solution2'),\n          symptoms: faultLines(val(fd, 'symptoms')),",
        'nieuwe velden in storingspayload',
    )
    frontend = replace_once(
        frontend,
        "      model: fault.model || '',\n      solutions: [...(fault.solutions || [])],",
        "      model: fault.model || '',\n      message: fault.message || '',\n      solution1: fault.solution1 || '',\n      solution2: fault.solution2 || '',\n      solutions: [...(fault.solutions || [])],",
        'nieuwe velden in storingssnapshot',
    )
    frontend = replace_once(
        frontend,
        "    if (solutionInput && Array.isArray(fault.solutions) && fault.solutions.length) {\n      const proposed = fault.solutions.join('\\n');\n      if (!solutionInput.value.trim() || confirm('Er staat al een oplossing ingevuld. Vervangen door de oplossing uit de storingsbibliotheek?')) solutionInput.value = proposed;\n    }",
        "    const proposedSolutions = [fault.solution1, fault.solution2, ...(Array.isArray(fault.solutions) ? fault.solutions : [])].map((item) => String(item || '').trim()).filter(Boolean);\n    if (solutionInput && proposedSolutions.length) {\n      const proposed = proposedSolutions.join('\\n');\n      if (!solutionInput.value.trim() || confirm('Er staat al een oplossing ingevuld. Vervangen door de oplossing uit de storingsbibliotheek?')) solutionInput.value = proposed;\n    }",
        'Oplossing 1 en 2 toepassen op depannage',
    )

# Maak de bestaande Excel-import ook compatibel met dit aangeleverde werkblad.
if 'fault-excel-import-v1' in index and 'Algemene omschrijving' not in index:
    alias_old = "['Storing', 'Storing / korte omschrijving', 'Storingsomschrijving', 'Probleem']"
    alias_new = "['Storing', 'Storing / korte omschrijving', 'Storingsomschrijving', 'Probleem', 'Algemene omschrijving']"
    if index.count(alias_old) != 2:
        raise SystemExit(f'Buildvalidatie mislukt: Excel naamalias verwacht 2x, gevonden {index.count(alias_old)}x')
    index = index.replace(alias_old, alias_new)
    index = replace_once(index, "return [fault?.code, fault?.name, fault?.brand, fault?.model].map(excelFaultNorm).join('|');", "return [fault?.code, fault?.category, fault?.name, fault?.brand, fault?.model].map(excelFaultNorm).join('|');", 'Excel UI sleutel inclusief categorie')
    index = replace_once(index, "brand: faultExcelColumn(headers, ['Merk', 'Brand']),", "brand: faultExcelColumn(headers, ['Merk', 'Brand', 'Merk / model', 'Merk/model']),", 'Merk/model Excel-alias')
    index = replace_once(index, "description: faultExcelColumn(headers, ['Omschrijving', 'Beschrijving', 'Description']),", "description: faultExcelColumn(headers, ['Omschrijving', 'Beschrijving', 'Description', 'gedetailleerde omschrijving']),\n      message: faultExcelColumn(headers, ['Melding', 'Message']),\n      solution1: faultExcelColumn(headers, ['Oplossing 1', 'Solution 1']),\n      solution2: faultExcelColumn(headers, ['Oplossing 2', 'Solution 2']),", 'extra Excel-kolommen')
    index = replace_once(
        index,
        "      description: String(fault?.description || '').trim(),\n      symptoms: Array.isArray(fault?.symptoms)",
        "      description: String(fault?.description || '').trim(),\n      message: String(fault?.message || '').trim(),\n      solution1: String(fault?.solution1 || '').trim(),\n      solution2: String(fault?.solution2 || '').trim(),\n      symptoms: Array.isArray(fault?.symptoms)",
        'extra Excel-vergelijkvelden',
    )
    index = replace_once(
        index,
        "        description: get(row, 'description'),\n        symptoms: excelFaultLines(get(row, 'symptoms')),",
        "        description: get(row, 'description'),\n        message: get(row, 'message'),\n        solution1: get(row, 'solution1'),\n        solution2: get(row, 'solution2'),\n        symptoms: excelFaultLines(get(row, 'symptoms')),",
        'extra Excel-importwaarden',
    )

frontend_path.write_text(frontend, encoding='utf-8')
endpoint_path.write_text(endpoint, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')

built_frontend = frontend_path.read_text(encoding='utf-8')
built_endpoint = endpoint_path.read_text(encoding='utf-8')
built_index = index_path.read_text(encoding='utf-8')

for needle in [FRONT_MARKER, "name=\"message\"", "name=\"solution1\"", "name=\"solution2\"", "textSection('Melding'", "textSection('Oplossing 1'", 'proposedSolutions']:
    if needle not in built_frontend:
        raise SystemExit(f'Buildvalidatie mislukt: uitgebreide storingsvelden ontbreken ({needle})')
for needle in [SERVER_MARKER, 'LATTIZ2_FAULT_SEED_2026_09_02', 'applyLattiz2ExcelSeedOnce', 'rows: 191', "message: cleanText(fault?.message", "solution1: cleanText(fault?.solution1", 'lattiz2ExcelSeed: excelSeed.seed']:
    if needle not in built_endpoint:
        raise SystemExit(f'Buildvalidatie mislukt: Lattiz 2 centrale seed ontbreekt ({needle})')
for needle in ['Algemene omschrijving', 'Merk / model', "message: get(row, 'message')", "solution1: get(row, 'solution1')", "solution2: get(row, 'solution2')"]:
    if needle not in built_index:
        raise SystemExit(f'Buildvalidatie mislukt: Excel-import ondersteunt aangeleverde kolom niet ({needle})')

print('[Machinepark] storingen uitgebreid met Melding/Oplossing 1/Oplossing 2 en 191 Lattiz 2 Excel-regels centraal klaargezet')
