from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
index = INDEX.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="synology-local-vendor-v1"'

if MARKER not in index:
    replacements = {
        "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.14.0/html2pdf.bundle.min.js": "./vendor/html2pdf.bundle.min.js",
        "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js": "./vendor/jspdf.umd.min.js",
    }
    for old, new in replacements.items():
        count = index.count(old)
        if count < 1:
            raise SystemExit(f"Buildvalidatie mislukt: CDN-bibliotheek niet gevonden ({old})")
        index = index.replace(old, new)

    index = index.replace(
        "</head>",
        f'<meta {MARKER}><meta name="machinepark-browser-vendor" content="local">\n</head>',
        1,
    )
    INDEX.write_text(index, encoding="utf-8")

built = INDEX.read_text(encoding="utf-8")
for forbidden in ["cdnjs.cloudflare.com", "html2pdf.js/0.14.0", "jspdf/2.5.1"]:
    if forbidden in built:
        raise SystemExit(f"Buildvalidatie mislukt: externe PDF-bibliotheek blijft aanwezig ({forbidden})")
for required in ["./vendor/html2pdf.bundle.min.js", "./vendor/jspdf.umd.min.js", MARKER]:
    if required not in built:
        raise SystemExit(f"Buildvalidatie mislukt: lokale PDF-bibliotheek ontbreekt ({required})")

for file_name in ["vendor/html2pdf.bundle.min.js", "vendor/jspdf.umd.min.js"]:
    path = ROOT / file_name
    if not path.is_file() or path.stat().st_size < 10000:
        raise SystemExit(f"Buildvalidatie mislukt: lokale browserbibliotheek ontbreekt of is te klein ({file_name})")

print("[Machinepark] PDF-browserbibliotheken worden lokaal vanaf Synology geladen")
