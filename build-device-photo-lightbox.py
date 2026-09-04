from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="photo-lightbox-v2"'

if MARKER not in index:
    style = f'''
<style {MARKER}>
[data-photo-lightbox]{{cursor:zoom-in}}
.device-photo-lightbox{{position:fixed;inset:0;z-index:3000;background:rgba(8,18,15,.9);display:none;align-items:center;justify-content:center;padding:24px}}
.device-photo-lightbox.show{{display:flex}}
.device-photo-lightbox-inner{{position:relative;max-width:min(1200px,96vw);max-height:94vh;display:flex;align-items:center;justify-content:center}}
.device-photo-lightbox img{{display:block;max-width:96vw;max-height:90vh;width:auto;height:auto;object-fit:contain;border-radius:14px;background:#fff;box-shadow:0 24px 70px rgba(0,0,0,.45)}}
.device-photo-lightbox-close{{position:absolute;right:-10px;top:-10px;width:42px;height:42px;border:0;border-radius:999px;background:#fff;color:#173f35;font-size:24px;line-height:1;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.25)}}
.device-photo-lightbox-caption{{position:absolute;left:12px;bottom:10px;max-width:calc(100% - 24px);padding:6px 10px;border-radius:999px;background:rgba(10,24,20,.78);color:#fff;font-size:12px}}
@media(max-width:700px){{
  .device-photo-lightbox{{padding:12px}}
  .device-photo-lightbox img{{max-width:96vw;max-height:86vh;border-radius:10px}}
  .device-photo-lightbox-close{{right:4px;top:4px}}
}}
@media print{{.device-photo-lightbox{{display:none!important}}}}
</style>
'''

    script = r'''
<script data-machinepark-build-fix="photo-lightbox-v2">
(() => {
  function ensurePhotoLightbox() {
    let box = document.getElementById('devicePhotoLightbox');
    if (box) return box;
    box = document.createElement('div');
    box.id = 'devicePhotoLightbox';
    box.className = 'device-photo-lightbox';
    box.setAttribute('aria-hidden', 'true');
    box.innerHTML = `<div class="device-photo-lightbox-inner" role="dialog" aria-modal="true" aria-label="Vergrote foto">
      <img alt="Vergrote foto">
      <div class="device-photo-lightbox-caption"></div>
      <button type="button" class="device-photo-lightbox-close" aria-label="Foto sluiten">×</button>
    </div>`;
    document.body.appendChild(box);

    const close = () => {
      box.classList.remove('show');
      box.setAttribute('aria-hidden', 'true');
      const img = box.querySelector('img');
      if (img) img.removeAttribute('src');
    };
    box.querySelector('.device-photo-lightbox-close').onclick = close;
    box.addEventListener('click', (event) => {
      if (event.target === box) close();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && box.classList.contains('show')) close();
    });
    return box;
  }

  function openPhotoLightbox(img) {
    if (!img) return;
    const src = img.dataset.fullSrc || img.currentSrc || img.src;
    if (!src) return;
    const box = ensurePhotoLightbox();
    const large = box.querySelector('img');
    const caption = box.querySelector('.device-photo-lightbox-caption');
    large.src = src;
    large.alt = img.alt || 'Vergrote foto';
    const badge = img.closest('.device-detail-photo')?.querySelector('.badge')?.textContent?.trim();
    caption.textContent = badge || img.alt || 'Foto';
    caption.style.display = caption.textContent ? '' : 'none';
    box.classList.add('show');
    box.setAttribute('aria-hidden', 'false');
    box.querySelector('.device-photo-lightbox-close')?.focus();
  }
  window.machineparkOpenPhotoLightbox = openPhotoLightbox;

  document.addEventListener('click', (event) => {
    const img = event.target.closest('img[data-photo-lightbox]');
    if (!img) return;
    event.preventDefault();
    event.stopPropagation();
    openPhotoLightbox(img);
  });
})();
</script>
'''

    if '</head>' not in index or '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-afsluiters ontbreken voor fotovergroting')
    index = index.replace('</head>', style + '</head>', 1)
    body_pos = index.rfind('</body>')
    index = index[:body_pos] + script + index[body_pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'device-photo-lightbox',
    "event.target.closest('img[data-photo-lightbox]')",
    'img.dataset.fullSrc',
    "event.key === 'Escape'",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: fotovergroting ontbreekt ({needle})')

print('[Machinepark] alle aanklikbare foto’s zijn vergrootbaar')
