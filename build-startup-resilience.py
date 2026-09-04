from pathlib import Path

ROOT = Path(__file__).resolve().parent
offline_path = ROOT / 'offline-first.js'
source = offline_path.read_text(encoding='utf-8')
MARKER = '// machinepark-startup-central-fallback-v1'

old = """        } catch (error) {
          if (!isNetworkFailure(error)) throw error;
          console.warn('Centrale gegevens tijdelijk niet beschikbaar', error);
        }

        if (remote?.exists && remote.data) {"""

new = """        } catch (error) {
          // machinepark-startup-central-fallback-v1
          // Een centrale API-fout (ook 401/403/409/500) mag de lokale app niet blokkeren.
          // Bewaar de bestaande IndexedDB-data onaangeroerd, start lokaal en laat polling/reconnect later opnieuw proberen.
          console.warn('Centrale gegevens tijdelijk niet beschikbaar; Machinepark start met lokale gegevens', error);
          remote = { exists: false, offline: true, startupError: String(error?.message || error || 'onbekende centrale fout') };
          setCentralSyncStatus('☁ Centrale synchronisatie tijdelijk niet beschikbaar · lokaal gestart', 'error');
        }

        if (remote?.exists && remote.data) {"""

if MARKER not in source:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1 centrale opstartfallback, gevonden {count}')
    source = source.replace(old, new, 1)
    offline_path.write_text(source, encoding='utf-8')

built = offline_path.read_text(encoding='utf-8')
for needle in [
    MARKER,
    'Centrale synchronisatie tijdelijk niet beschikbaar · lokaal gestart',
    'remote = { exists: false, offline: true',
    'startCentralPolling();',
]:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: robuuste opstartfallback ontbreekt ({needle})')

# De oude fatale rethrow mag in deze specifieke eerste centrale GET-catch niet meer voorkomen.
startup_anchor = built.find("setCentralSyncStatus('☁ Centrale gegevens ophalen…', 'busy');")
startup_end = built.find('if (remote?.exists && remote.data)', startup_anchor)
startup_slice = built[startup_anchor:startup_end]
if "if (!isNetworkFailure(error)) throw error;" in startup_slice:
    raise SystemExit('Buildvalidatie mislukt: centrale opstartfout wordt nog fataal doorgegooid')

print('[Machinepark] centrale opstartfouten blokkeren lokale gegevens niet meer')
