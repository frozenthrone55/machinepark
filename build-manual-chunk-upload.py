from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
client_path = ROOT / 'manual-library.js'
endpoint_path = ROOT / 'netlify/functions/manual-library.mjs'

for path in (client_path, endpoint_path):
    if not path.exists():
        raise SystemExit(f'Buildvalidatie mislukt: {path.name} ontbreekt voor chunk-upload van handleidingen')

# Netlify Functions accepteren maximaal ongeveer 6 MB request-body. Houd ieder
# PDF-blok ruim daaronder en bouw het document server-side opnieuw op in Blobs.
client = client_path.read_text(encoding='utf-8')
CLIENT_MARKER = '// machinepark-manual-chunk-upload-v1'
if CLIENT_MARKER not in client:
    pattern = r"  async function uploadManualFile\(file\) \{.*?\n  \}\n\n  function openManualEditor"
    replacement = r'''  // machinepark-manual-chunk-upload-v1
  async function uploadManualFile(file) {
    if (!file) return null;
    if (file.type && file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) throw new Error('Kies een PDF-bestand.');
    if (file.size > 12_000_000) throw new Error('De PDF is groter dan 12 MB.');
    if (!file.size) throw new Error('Het PDF-bestand is leeg.');

    const chunkBytes = 3_500_000;
    const total = Math.max(1, Math.ceil(file.size / chunkBytes));
    const uploadId = (typeof crypto?.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`
    ).replace(/[^a-zA-Z0-9_-]/g, '');

    const request = async (params, body = undefined, contentType = '') => {
      const headers = await centralHeaders(false);
      if (contentType) headers['content-type'] = contentType;
      const url = `${MANUAL_LIBRARY_URL}?${new URLSearchParams(params).toString()}`;
      const res = await fetch(url, { method: 'PUT', cache: 'no-store', headers, ...(body !== undefined ? { body } : {}) });
      const text = await res.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (_) {}
      if (!res.ok) throw new Error(data.error || text || `PDF-upload mislukt (${res.status})`);
      return data;
    };

    try {
      for (let index = 0; index < total; index += 1) {
        const start = index * chunkBytes;
        const end = Math.min(file.size, start + chunkBytes);
        const chunk = file.slice(start, end, 'application/octet-stream');
        await request({
          action: 'upload-chunk',
          uploadId,
          index: String(index),
          total: String(total),
          fileName: file.name || 'handleiding.pdf',
          fileSize: String(file.size),
        }, chunk, 'application/octet-stream');
        if (typeof setCentralSyncStatus === 'function') {
          setCentralSyncStatus(`☁ PDF uploaden… ${Math.round(((index + 1) / total) * 90)}%`, 'busy');
        }
      }

      if (typeof setCentralSyncStatus === 'function') setCentralSyncStatus('☁ PDF afronden…', 'busy');
      return await request({
        action: 'finalize-upload',
        uploadId,
        total: String(total),
        fileName: file.name || 'handleiding.pdf',
        fileSize: String(file.size),
      });
    } catch (error) {
      try {
        await request({ action: 'abort-upload', uploadId, total: String(total) });
      } catch (_) {}
      throw error;
    }
  }

  function openManualEditor'''
    client, count = re.subn(pattern, replacement, client, count=1, flags=re.S)
    if count != 1:
        raise SystemExit('Buildvalidatie mislukt: PDF-uploadfunctie niet uniek gevonden')
    client_path.write_text(client, encoding='utf-8')

endpoint = endpoint_path.read_text(encoding='utf-8')
SERVER_MARKER = '// machinepark-manual-chunk-upload-server-v1'
if SERVER_MARKER not in endpoint:
    const_anchor = "const MAX_FILE_BYTES = 12_000_000;\n"
    if endpoint.count(const_anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: MAX_FILE_BYTES niet uniek gevonden')
    endpoint = endpoint.replace(
        const_anchor,
        const_anchor + "const UPLOAD_CHUNK_PREFIX = 'manual-upload-chunks/';\nconst MAX_CHUNK_BYTES = 3_750_000;\nconst MAX_UPLOAD_CHUNKS = 8;\n",
        1,
    )

    helper_anchor = "function sanitizeManual(raw, existing = null) {"
    helpers = r'''// machinepark-manual-chunk-upload-server-v1
function cleanUploadId(value) {
  const id = String(value || '').trim();
  return /^[a-zA-Z0-9_-]{8,100}$/.test(id) ? id : '';
}

function chunkKey(uploadId, index) {
  return `${UPLOAD_CHUNK_PREFIX}${uploadId}-${index}`;
}

async function cleanupUploadChunks(store, uploadId, total, userId = '') {
  const deletes = [];
  for (let index = 0; index < total; index += 1) {
    const key = chunkKey(uploadId, index);
    if (userId) {
      const metadata = await store.getMetadata(key, { consistency: 'strong' }).catch(() => null);
      if (metadata?.uploadedBy !== userId) continue;
    }
    deletes.push(store.delete(key).catch(() => {}));
  }
  await Promise.all(deletes);
}

'''
    if endpoint.count(helper_anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: sanitizeManual-anker niet uniek gevonden')
    endpoint = endpoint.replace(helper_anchor, helpers + helper_anchor, 1)

    put_pattern = r"    if \(req\.method === 'PUT'\) \{.*?\n    \}\n\n    if \(req\.method === 'POST'\)"
    put_replacement = r'''    if (req.method === 'PUT') {
      if (!canManage(access)) return json({ error: 'Alleen een beheerder kan handleidingen uploaden.' }, 403);
      const action = String(url.searchParams.get('action') || '');
      const fileName = cleanText(url.searchParams.get('fileName'), 220) || 'handleiding.pdf';

      // Achterwaartse compatibiliteit voor reeds geopende clients met kleine PDF's.
      if (action === 'upload') {
        if (!fileName.toLowerCase().endsWith('.pdf')) return json({ error: 'Alleen PDF-handleidingen zijn toegestaan.' }, 400);
        const bytes = Buffer.from(await req.arrayBuffer());
        if (!bytes.length) return json({ error: 'Het PDF-bestand is leeg.' }, 400);
        if (bytes.length > MAX_FILE_BYTES) return json({ error: 'De PDF is groter dan 12 MB.' }, 413);
        if (bytes.subarray(0, 5).toString('ascii') !== '%PDF-') return json({ error: 'Het gekozen bestand is geen geldige PDF.' }, 400);
        const key = `${FILE_PREFIX}${crypto.randomUUID()}.pdf`;
        await store.set(key, new Blob([bytes], { type: 'application/pdf' }), {
          metadata: { contentType: 'application/pdf', fileName, size: bytes.length, uploadedAt: new Date().toISOString(), uploadedBy: access.sub },
        });
        return json({ ok: true, fileKey: key, fileName, fileSize: bytes.length });
      }

      const uploadId = cleanUploadId(url.searchParams.get('uploadId'));
      const total = Number(url.searchParams.get('total'));
      if (!uploadId) return json({ error: 'Ongeldige upload-ID.' }, 400);
      if (!Number.isInteger(total) || total < 1 || total > MAX_UPLOAD_CHUNKS) return json({ error: 'Ongeldig aantal PDF-blokken.' }, 400);

      if (action === 'abort-upload') {
        await cleanupUploadChunks(store, uploadId, total, access.sub);
        return json({ ok: true });
      }

      const fileSize = Number(url.searchParams.get('fileSize'));
      if (!Number.isInteger(fileSize) || fileSize < 1 || fileSize > MAX_FILE_BYTES) return json({ error: 'De PDF is groter dan 12 MB of heeft een ongeldige grootte.' }, 413);
      if (!fileName.toLowerCase().endsWith('.pdf')) return json({ error: 'Alleen PDF-handleidingen zijn toegestaan.' }, 400);

      if (action === 'upload-chunk') {
        const index = Number(url.searchParams.get('index'));
        if (!Number.isInteger(index) || index < 0 || index >= total) return json({ error: 'Ongeldig PDF-bloknummer.' }, 400);
        const bytes = Buffer.from(await req.arrayBuffer());
        if (!bytes.length) return json({ error: 'Een PDF-blok is leeg.' }, 400);
        if (bytes.length > MAX_CHUNK_BYTES) return json({ error: 'Een PDF-blok is te groot.' }, 413);
        if (index === 0 && bytes.subarray(0, 5).toString('ascii') !== '%PDF-') return json({ error: 'Het gekozen bestand is geen geldige PDF.' }, 400);
        await store.set(chunkKey(uploadId, index), new Blob([bytes], { type: 'application/octet-stream' }), {
          metadata: {
            uploadedBy: access.sub,
            uploadedAt: new Date().toISOString(),
            index,
            total,
            fileSize,
            fileName,
          },
        });
        return json({ ok: true, index, received: bytes.length });
      }

      if (action === 'finalize-upload') {
        const buffers = [];
        let receivedBytes = 0;
        for (let index = 0; index < total; index += 1) {
          const entry = await store.getWithMetadata(chunkKey(uploadId, index), { type: 'arrayBuffer', consistency: 'strong' });
          if (!entry?.data) return json({ error: `PDF-blok ${index + 1} ontbreekt. Probeer de upload opnieuw.` }, 409);
          if (entry.metadata?.uploadedBy !== access.sub) return json({ error: 'Deze PDF-upload hoort bij een andere gebruiker.' }, 403);
          if (Number(entry.metadata?.total) !== total || Number(entry.metadata?.fileSize) !== fileSize) return json({ error: 'De PDF-upload is niet consistent. Probeer opnieuw.' }, 409);
          const part = Buffer.from(entry.data);
          receivedBytes += part.length;
          if (receivedBytes > MAX_FILE_BYTES) return json({ error: 'De PDF is groter dan 12 MB.' }, 413);
          buffers.push(part);
        }
        if (receivedBytes !== fileSize) return json({ error: 'De PDF-upload is onvolledig. Probeer opnieuw.' }, 409);
        const bytes = Buffer.concat(buffers, receivedBytes);
        if (bytes.subarray(0, 5).toString('ascii') !== '%PDF-') return json({ error: 'Het gekozen bestand is geen geldige PDF.' }, 400);
        const key = `${FILE_PREFIX}${crypto.randomUUID()}.pdf`;
        await store.set(key, new Blob([bytes], { type: 'application/pdf' }), {
          metadata: { contentType: 'application/pdf', fileName, size: bytes.length, uploadedAt: new Date().toISOString(), uploadedBy: access.sub },
        });
        await cleanupUploadChunks(store, uploadId, total, access.sub);
        return json({ ok: true, fileKey: key, fileName, fileSize: bytes.length });
      }

      return json({ error: 'Ongeldige uploadactie.' }, 400);
    }

    if (req.method === 'POST')'''
    endpoint, count = re.subn(put_pattern, put_replacement, endpoint, count=1, flags=re.S)
    if count != 1:
        raise SystemExit('Buildvalidatie mislukt: bestaande PDF PUT-route niet uniek gevonden')
    endpoint_path.write_text(endpoint, encoding='utf-8')

client = client_path.read_text(encoding='utf-8')
endpoint = endpoint_path.read_text(encoding='utf-8')
required = [
    (client, CLIENT_MARKER),
    (client, "chunkBytes = 3_500_000"),
    (client, "action: 'upload-chunk'"),
    (client, "action: 'finalize-upload'"),
    (client, "action: 'abort-upload'"),
    (endpoint, SERVER_MARKER),
    (endpoint, "UPLOAD_CHUNK_PREFIX = 'manual-upload-chunks/'"),
    (endpoint, 'MAX_CHUNK_BYTES = 3_750_000'),
    (endpoint, "action === 'upload-chunk'"),
    (endpoint, "action === 'finalize-upload'"),
    (endpoint, 'Buffer.concat(buffers, receivedBytes)'),
]
missing = [needle for haystack, needle in required if needle not in haystack]
if missing:
    raise SystemExit('Buildvalidatie chunk-upload handleidingen mislukt: ' + ', '.join(missing))

print('[Machinepark] PDF-handleidingen uploaden in 3.5 MB blokken onder Netlify requestlimiet')
