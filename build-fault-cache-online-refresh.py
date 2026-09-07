from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'fault-library.js'
text = path.read_text(encoding='utf-8')

MARKER = '// machinepark-fault-cache-online-refresh-v1'
if MARKER not in text:
    old = "    if (!force && faultLibraryLoaded) return faultLibrary;\n    if (!force && faultLibraryLoading) return faultLibraryLoading;"
    new = "    // machinepark-fault-cache-online-refresh-v1\n    // Offline mag de laatst bekende bibliotheek direct gebruikt worden. Online moet de centrale lijst altijd opnieuw worden opgehaald, ook als IndexedDB al geladen is.\n    if (!force && faultLibraryLoading) return faultLibraryLoading;\n    if (!force && faultLibraryLoaded && navigator.onLine === false) return faultLibrary;"
    if text.count(old) != 1:
        raise SystemExit('Storingscache-refresh: loadFaultLibrary-anker niet uniek')
    text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')

built = path.read_text(encoding='utf-8')
for needle in [
    MARKER,
    "if (!force && faultLibraryLoading) return faultLibraryLoading;",
    "if (!force && faultLibraryLoaded && navigator.onLine === false) return faultLibrary;",
    "await faultLibraryRequest();",
    "await writeFaultCache();",
]:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: online storingscache-refresh ontbreekt ({needle})')

if "if (!force && faultLibraryLoaded) return faultLibrary;" in built:
    raise SystemExit('Buildvalidatie mislukt: oude online cache-shortcut is nog aanwezig')

print('[Machinepark] storingscache toont offline lokaal maar ververst online altijd centraal')
