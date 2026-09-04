from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'index.html'
text = path.read_text(encoding='utf-8')

MARKER = '// machinepark-print-device-photo-ready-v1'
if MARKER not in text:
    old = r'''  async function waitForPrintImages(doc) {
    const images = [...doc.images];
    if (!images.length) return;
    await Promise.all(images.map((img) => img.complete
      ? Promise.resolve()
      : new Promise((resolve) => {
          const done = () => resolve();
          img.addEventListener('load', done, { once: true });
          img.addEventListener('error', done, { once: true });
          setTimeout(done, 2500);
        })));
  }
'''
    new = r'''  // machinepark-print-device-photo-ready-v1
  async function waitForPrintImages(doc) {
    const images = [...doc.images];
    if (!images.length) return;

    await Promise.all(images.map(async (img) => {
      if (!img.complete || !img.naturalWidth) {
        await new Promise((resolve) => {
          let finished = false;
          const done = () => {
            if (finished) return;
            finished = true;
            resolve();
          };
          img.addEventListener('load', done, { once: true });
          img.addEventListener('error', done, { once: true });
          setTimeout(done, 7000);
        });
      }

      if (typeof img.decode === 'function' && img.naturalWidth) {
        try {
          await Promise.race([
            img.decode(),
            new Promise((resolve) => setTimeout(resolve, 3500)),
          ]);
        } catch (_) {}
      }
    }));

    await new Promise((resolve) => {
      const view = doc.defaultView;
      if (!view || typeof view.requestAnimationFrame !== 'function') {
        setTimeout(resolve, 120);
        return;
      }
      view.requestAnimationFrame(() => view.requestAnimationFrame(resolve));
    });
  }
'''
    if text.count(old) != 1:
        raise SystemExit('Afdrukfoto-fix: waitForPrintImages-anker niet uniek')
    text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')

built = path.read_text(encoding='utf-8')
for needle in [MARKER, "typeof img.decode === 'function'", 'img.naturalWidth', 'setTimeout(done, 7000)', 'requestAnimationFrame(() => view.requestAnimationFrame(resolve))']:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: afdrukfoto-wachtlogica ontbreekt ({needle})')

print('[Machinepark] toestelfoto’s worden voor afdrukken volledig geladen en gedecodeerd')
