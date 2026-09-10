from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

DIRECT_MARKER = 'data-machinepark-build-fix="mail-pdf-direct-v4"'
MARKER = 'machinepark-desktop-mail-client-v1'

if DIRECT_MARKER not in index:
    raise SystemExit("Buildvalidatie mislukt: directe Mail PDF ontbreekt voor desktop-mailclient")

if MARKER not in index:
    start = index.find("  async function shareFile(file, title) {")
    end = index.find("\n  async function directMailPdf(button) {", start)
    if start < 0 or end < 0:
        raise SystemExit("Buildvalidatie mislukt: shareFile-route niet gevonden voor desktop-mailclient")

    replacement = r'''  // machinepark-desktop-mail-client-v1
  function machineparkMailUsesNativeShare() {
    const ua = String(navigator.userAgent || '');
    const uaDataMobile = navigator.userAgentData?.mobile === true;
    const phoneOrAndroid = /Android|iPhone|iPod/i.test(ua);
    const iPad = /iPad/i.test(ua) || (navigator.platform === 'MacIntel' && Number(navigator.maxTouchPoints || 0) > 1);
    return uaDataMobile || phoneOrAndroid || iPad;
  }

  async function shareFile(file, title) {
    const subject = `Machinepark - ${title}`;
    const text = `In bijlage vind je de PDF uit Machinepark: ${title}.`;
    const shareData = { files:[file], title:subject, text };
    const useNativeShare = machineparkMailUsesNativeShare();
    const canShareFile = typeof navigator.share === 'function' && (typeof navigator.canShare !== 'function' || navigator.canShare(shareData));

    // Mobiel behoudt de bestaande deelroute. Op pc slaan we het deelvenster
    // bewust over en openen we rechtstreeks het standaard mailprogramma.
    if (useNativeShare && canShareFile) {
      try { await navigator.share(shareData); return; }
      catch (error) {
        if (error?.name === 'AbortError') return;
        console.warn('[Machinepark] Mobiele PDF-deling mislukt; mailprogramma wordt gebruikt.', error);
      }
    }

    downloadFile(file);
    const body = `${text}\n\nDe PDF is op je toestel gedownload. Voeg het bestand ${file.name} toe als bijlage.`;
    const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    notify(useNativeShare
      ? 'PDF gedownload. Je mailprogramma wordt geopend; voeg de gedownloade PDF toe als bijlage.'
      : 'PDF gedownload. Je standaard mailprogramma wordt geopend; voeg de gedownloade PDF toe als bijlage.');
    setTimeout(() => { window.location.href = mailto; }, 120);
  }
'''
    index = index[:start] + replacement + index[end:]

    old_busy = "      button.textContent = 'Delen…';"
    new_busy = "      button.textContent = machineparkMailUsesNativeShare() ? 'Delen…' : 'Mail openen…';"
    if index.count(old_busy) != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1 Mail PDF statusregel, gevonden {index.count(old_busy)}")
    index = index.replace(old_busy, new_busy, 1)
    index_path.write_text(index, encoding="utf-8")

required = [
    MARKER,
    'function machineparkMailUsesNativeShare()',
    "navigator.userAgentData?.mobile === true",
    '/Android|iPhone|iPod/i',
    "navigator.platform === 'MacIntel'",
    'if (useNativeShare && canShareFile)',
    'await navigator.share(shareData)',
    'const mailto = `mailto:?subject=',
    'window.location.href = mailto',
    "'Mail openen…'",
    'Je standaard mailprogramma wordt geopend',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: desktop-mailclient ontbreekt ({needle})")

print('[Machinepark] Mail PDF: mobiel blijft delen, desktop opent standaard mailprogramma')
