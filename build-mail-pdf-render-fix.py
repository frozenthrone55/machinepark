from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-' + 'build-fix=' + '"mail-pdf-v1"'
if MARKER not in index:
    raise SystemExit("Buildvalidatie mislukt: Mail PDF-code ontbreekt voor renderfix")

# Houd de PDF-bron in de echte DOM zodat layout/computed styles beschikbaar zijn.
# De bron blijft voor de gebruiker buiten beeld; alleen de html2canvas-kopie wordt
# tijdens het renderen naar de normale oorsprong verplaatst.
anchor = """          scrollX: 0,\n          scrollY: 0"""
replacement = """          scrollX: 0,\n          scrollY: 0,\n          onclone: (clonedDoc) => {\n            const clonedStage = clonedDoc.querySelector('.machinepark-pdf-stage');\n            if (!clonedStage) return;\n            clonedStage.style.position = 'static';\n            clonedStage.style.left = '0';\n            clonedStage.style.top = '0';\n            clonedStage.style.zIndex = 'auto';\n            clonedStage.style.transform = 'none';\n            clonedStage.style.visibility = 'visible';\n          }"""

if index.count(anchor) != 1:
    raise SystemExit(f"Buildvalidatie mislukt: Mail PDF html2canvas-anker {index.count(anchor)}x gevonden")
index = index.replace(anchor, replacement, 1)

required = [
    "left:-12000px",
    "document.body.appendChild(stage);",
    "onclone: (clonedDoc) =>",
    "clonedDoc.querySelector('.machinepark-pdf-stage')",
    "clonedStage.style.position = 'static'",
    "clonedStage.style.left = '0'",
    "clonedStage.style.top = '0'",
    "clonedStage.style.zIndex = 'auto'",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: Mail PDF renderfix ontbreekt ({needle})")

index_path.write_text(index, encoding="utf-8")
print("[Machinepark] Mail PDF renderstage blijft gemount; html2canvas-kopie wordt binnen capturevlak geplaatst")
