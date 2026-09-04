from pathlib import Path

ROOT = Path(__file__).resolve().parent
offline_path = ROOT / 'offline-first.js'
source = offline_path.read_text(encoding='utf-8')
MARKER = '// machinepark-central-auth-retry-v1'

old_headers = """    const baseHeaders = typeof centralHeaders === 'function' ? centralHeaders : null;
    if (baseHeaders) {
      centralHeaders = async function(json = false) {
        if (!navigator.onLine && !window.Clerk?.isSignedIn) return json ? { 'Content-Type': 'application/json' } : {};
        try { return await baseHeaders(json); }
        catch (error) {
          if (isNetworkFailure(error)) return json ? { 'Content-Type': 'application/json' } : {};
          throw error;
        }
      };
      window.centralHeaders = centralHeaders;
    }
"""

new_headers = """    const baseHeaders = typeof centralHeaders === 'function' ? centralHeaders : null;
    if (baseHeaders) {
      // machinepark-central-auth-retry-v1
      centralHeaders = async function(json = false) {
        if (!navigator.onLine && !window.Clerk?.isSignedIn) return json ? { 'Content-Type': 'application/json' } : {};
        let lastError = null;
        for (let attempt = 0; attempt < 5; attempt += 1) {
          try { return await baseHeaders(json); }
          catch (error) {
            lastError = error;
            if (isNetworkFailure(error)) return json ? { 'Content-Type': 'application/json' } : {};
            const message = String(error?.message || error || '');
            const tokenNotReady = /geen actieve clerk-sessie/i.test(message);
            if (!tokenNotReady || attempt >= 4 || !navigator.onLine) throw error;
            await new Promise((resolve) => setTimeout(resolve, 180 + attempt * 220));
          }
        }
        throw lastError || new Error('Clerk-sessie is nog niet beschikbaar.');
      };
      window.centralHeaders = centralHeaders;
    }
"""

if MARKER not in source:
    count = source.count(old_headers)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1 centrale headerwrapper, gevonden {count}')
    source = source.replace(old_headers, new_headers, 1)

old_status = """          remote = { exists: false, offline: true, startupError: String(error?.message || error || 'onbekende centrale fout') };
          setCentralSyncStatus('☁ Centrale synchronisatie tijdelijk niet beschikbaar · lokaal gestart', 'error');
"""
new_status = """          const startupError = String(error?.message || error || 'onbekende centrale fout').replace(/\\s+/g, ' ').trim().slice(0, 180);
          window.machineparkLastCentralStartupError = startupError;
          remote = { exists: false, offline: true, startupError };
          setCentralSyncStatus(`☁ Centrale synchronisatie niet beschikbaar · ${startupError} · lokale gegevens actief`, 'error');
"""
if old_status in source:
    source = source.replace(old_status, new_status, 1)
elif 'window.machineparkLastCentralStartupError' not in source:
    raise SystemExit('Buildvalidatie mislukt: centrale opstartstatus niet gevonden')

offline_path.write_text(source, encoding='utf-8')

built = offline_path.read_text(encoding='utf-8')
for needle in [
    MARKER,
    'attempt < 5',
    'geen actieve clerk-sessie',
    'machineparkLastCentralStartupError',
    'lokale gegevens actief',
]:
    if needle not in built.lower() if needle == 'geen actieve clerk-sessie' else needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: centrale auth-retry ontbreekt ({needle})')

print('[Machinepark] Clerk-token wordt kort herprobeerd en centrale foutoorzaak wordt zichtbaar getoond')
