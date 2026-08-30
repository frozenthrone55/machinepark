from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="photo-config-v1"'


def replace_exact(old, new, expected, label):
    global index
    count = index.count(old)
    if count != expected:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht {expected}x {label}, gevonden {count}x')
    index = index.replace(old, new)


def replace_once(old, new, label):
    replace_exact(old, new, 1, label)


if MARKER not in index:
    # Eén centrale limiet van vijf voor verslagfoto’s.
    replace_once(
        'const REPORT_PHOTO_LIMIT = 4;',
        'const REPORT_PHOTO_LIMIT = 5;',
        'limiet verslagfoto’s',
    )

    # Eén centrale limiet van vijf voor toestel-/machinefoto’s.
    replace_exact('old.devicePhotos.slice(0,3)', 'old.devicePhotos.slice(0,5)', 1, 'opslaglimiet bestaande toestelfoto’s')
    replace_exact('.slice(0, 3)', '.slice(0, 5)', 3, 'limiet toestelfoto’s')
    replace_once('Maximaal 3 foto’s.', 'Maximaal 5 foto’s.', 'uitleg maximum toestelfoto’s')
    replace_once('van maximaal 3 foto’s', 'van maximaal 5 foto’s', 'status maximum toestelfoto’s')
    replace_exact('photos.length >= 3', 'photos.length >= 5', 2, 'knoplimiet toestelfoto’s')
    replace_once('const available = 3 - photos.length;', 'const available = 5 - photos.length;', 'beschikbare fotoplaatsen')
    replace_once('Een toestel kan maximaal 3 foto’s bevatten.', 'Een toestel kan maximaal 5 foto’s bevatten.', 'melding maximum toestelfoto’s')
    replace_once('${photos.length} van 3', '${photos.length} van 5', 'detailteller toestelfoto’s')

    # Toestelfoto’s worden compact gemaakt vóór Blob-opslag. Deze logica stond vroeger
    # in een aparte correctiepatch; ze hoort nu samen met de fotoconfiguratie.
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

    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: </head> ontbreekt voor fotoconfiguratie')
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'const REPORT_PHOTO_LIMIT = 5;',
    'Maximaal 5 foto’s.',
    'van maximaal 5 foto’s',
    'const available = 5 - photos.length;',
    'Een toestel kan maximaal 5 foto’s bevatten.',
    'function compressDevicePhoto(file)',
    'const max = 720;',
    'const compressed = await compressDevicePhoto(file);',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: centrale fotoconfiguratie ontbreekt ({needle})')

for obsolete in [
    'const REPORT_PHOTO_LIMIT = 4;',
    'Maximaal 3 foto’s. Kies één foto als overzichtsfoto',
    'Een toestel kan maximaal 3 foto’s bevatten.',
]:
    if obsolete in index:
        raise SystemExit(f'Buildvalidatie mislukt: oude foto-instelling is nog actief ({obsolete})')

print('[Machinepark] centrale fotoconfiguratie: maximaal 5 foto’s en compacte toestelopslag actief')
