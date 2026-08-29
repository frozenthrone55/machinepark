from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="device-photo-sync-size-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    anchor = """  function normalizedDevicePhotos(device) {
    return (Array.isArray(device?.devicePhotos) ? device.devicePhotos : [])
      .filter((src) => typeof src === 'string' && src.trim())
      .slice(0, 5);
  }
"""
    replacement = anchor + r'''

  function compressDevicePhoto(file) {
    if (!file || !file.size) return Promise.resolve('');
    return new Promise((resolve, reject) => {
      const img = new Image();
      const reader = new FileReader();
      reader.onerror = reject;
      reader.onload = (event) => { img.src = event.target.result; };
      img.onerror = reject;
      img.onload = () => {
        const max = 720;
        const scale = Math.min(1, max / Math.max(img.width, img.height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(img.width * scale));
        canvas.height = Math.max(1, Math.round(img.height * scale));
        canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
        let quality = .68;
        let data = canvas.toDataURL('image/jpeg', quality);
        while (data.length > 260000 && quality > .44) {
          quality -= .08;
          data = canvas.toDataURL('image/jpeg', quality);
        }
        resolve(data);
      };
      reader.readAsDataURL(file);
    });
  }
'''
    replace_once(anchor, replacement, 'compacte compressie toestelfoto’s')
    replace_once(
        "const compressed = await compressImage(file);\n          if (compressed) photos.push(compressed);",
        "const compressed = await compressDevicePhoto(file);\n          if (compressed) photos.push(compressed);",
        'toestelfoto compressie',
    )
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    index_path.write_text(index, encoding='utf-8')
    print('[Machinepark] toestelfoto’s compacter gemaakt voor betrouwbare centrale opslag')
else:
    print('[Machinepark] compacte toestelfoto-opslag reeds actief')
