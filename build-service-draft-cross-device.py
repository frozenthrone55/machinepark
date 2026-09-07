from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="service-draft-cross-device-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    replace_once(
        "  async function refreshDraftState(kind) {\n    const storeName = kindInfo(kind).store;\n    state[storeName] = await getAll(storeName);\n    renderDraftPanels();\n  }",
        "  async function refreshDraftState(kind) {\n    const storeName = kindInfo(kind).store;\n    state[storeName] = await getAll(storeName);\n    renderDraftPanels();\n  }\n\n  async function syncDraftAcrossDevices(kind, { pullLatest = false } = {}) {\n    if (!navigator.onLine || !window.Clerk?.isSignedIn || typeof window.machineparkSyncOnlineNow !== 'function') return false;\n    try {\n      await window.machineparkSyncOnlineNow({ quiet:true });\n      if (pullLatest) await refreshDraftState(kind);\n      return true;\n    } catch (error) {\n      console.warn('Concept synchroniseren tussen toestellen', error);\n      return false;\n    }\n  }\n  window.machineparkSyncDraftAcrossDevices = syncDraftAcrossDevices;",
        "cross-device conceptsync helper",
    )

    replace_once(
        "    if (manual) toast(`${kindInfo(current.kind).singular}concept bewaard`);\n    return { header, items };",
        "    if (manual) {\n      const synced = await syncDraftAcrossDevices(current.kind);\n      toast(synced ? `${kindInfo(current.kind).singular}concept bewaard en gesynchroniseerd` : `${kindInfo(current.kind).singular}concept bewaard`);\n    }\n    return { header, items };",
        "directe sync na handmatig concept bewaren",
    )

    replace_once(
        "  function openSavedDraft(kind, id) {\n    const header = draftHeader(kind, id);",
        "  async function openSavedDraft(kind, id) {\n    setSaveStatus('Nieuwste concept ophalen…', 'busy');\n    await syncDraftAcrossDevices(kind, { pullLatest:true });\n    const header = draftHeader(kind, id);",
        "nieuwste concept ophalen voor verdergaan",
    )

    replace_once(
        "    queueDraftSave({ force:true }).catch(error => {\n      console.error('Concept bewaren bij sluiten', error);",
        "    queueDraftSave({ force:true }).then(() => syncDraftAcrossDevices(current.kind)).catch(error => {\n      console.error('Concept bewaren bij sluiten', error);",
        "directe sync bij concept sluiten",
    )

    replace_once(
        "<span class=\"muted\" style=\"font-size:11px\">Automatisch lokaal bewaard en centraal gesynchroniseerd.</span>",
        "<span class=\"muted\" style=\"font-size:11px\">Centraal gesynchroniseerd · verdergaan op pc, tablet of gsm.</span>",
        "cross-device uitleg in conceptenlijst",
    )

    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor cross-device conceptsync')
    index = index[:pos] + f'<span {MARKER} hidden></span>\n' + index[pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'syncDraftAcrossDevices',
    'window.machineparkSyncOnlineNow({ quiet:true })',
    'pullLatest:true',
    'concept bewaard en gesynchroniseerd',
    'queueDraftSave({ force:true }).then(() => syncDraftAcrossDevices(current.kind))',
    'verdergaan op pc, tablet of gsm',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: cross-device conceptsync ontbreekt ({needle})')

print('[Machinepark] serviceconcepten zijn direct hervatbaar op andere toestellen')
