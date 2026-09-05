from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-build-fix="purge-service-photos-on-delete-v1"'

if MARKER not in index:
    script = f'''
<script {MARKER}>
(() => {{
  const originalDeleteServiceRecordForPhotoCleanup = deleteServiceRecord;

  async function purgeDeletedServicePhotos(storeName, entityId) {{
    const token = await window.Clerk?.session?.getToken();
    if (!token) throw new Error('Geen actieve Clerk-sessie.');
    const response = await fetch('/.netlify/functions/purge-service-audit-photos', {{
      method: 'POST',
      headers: {{
        Authorization: `Bearer ${{token}}`,
        'Content-Type': 'application/json',
      }},
      body: JSON.stringify({{ storeName, entityId }}),
      cache: 'no-store',
    }});
    const body = await response.json().catch(() => ({{}}));
    if (!response.ok) throw new Error(body.error || 'Opschonen van verslagfoto’s mislukt.');
    return body;
  }}

  deleteServiceRecord = async function(storeName, id) {{
    const collection = storeName === 'maintenance' ? state.maintenance : storeName === 'breakdowns' ? state.breakdowns : null;
    const existedBefore = Boolean(collection?.some(item => item.id === id));
    const result = await originalDeleteServiceRecordForPhotoCleanup(storeName, id);
    if (!existedBefore) return result;

    const currentCollection = storeName === 'maintenance' ? state.maintenance : state.breakdowns;
    const deleted = !currentCollection.some(item => item.id === id);
    if (!deleted) return result;

    try {{
      if (typeof centralSync !== 'undefined' && centralSync.pushTimer) {{
        clearTimeout(centralSync.pushTimer);
        centralSync.pushTimer = null;
      }}
      if (typeof centralPush === 'function') await centralPush();
      await purgeDeletedServicePhotos(storeName, id);
    }} catch (error) {{
      console.warn('Verwijderde verslagfoto’s konden niet volledig uit het logboek worden opgeschoond:', error);
    }}
    return result;
  }};

  window.purgeDeletedServicePhotos = purgeDeletedServicePhotos;
}})();
</script>
'''
    if "</body>" not in index:
        raise SystemExit("Buildvalidatie mislukt: HTML-afsluiter ontbreekt voor foto-opruiming")
    index = index.replace("</body>", script + "</body>", 1)
    index_path.write_text(index, encoding="utf-8")

required = [
    MARKER,
    "purge-service-audit-photos",
    "purgeDeletedServicePhotos",
    "originalDeleteServiceRecordForPhotoCleanup",
    "await centralPush()",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: foto-opruiming ontbreekt ({needle})")

print("[Machinepark] verwijderde verslagfoto's worden uit centrale hersteldata opgeschoond")
