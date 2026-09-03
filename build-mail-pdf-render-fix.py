from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-' + 'build-fix=' + '"mail-pdf-v1"'
if MARKER not in index:
    raise SystemExit("Buildvalidatie mislukt: Mail PDF-code ontbreekt voor renderfix")

old_position = """  position:fixed;\n  left:-12000px;\n  top:0;"""
new_position = """  position:relative;\n  left:auto;\n  top:auto;"""
if index.count(old_position) != 1:
    raise SystemExit(f"Buildvalidatie mislukt: Mail PDF offscreen-position {index.count(old_position)}x gevonden")
index = index.replace(old_position, new_position, 1)

old_z_index = "  z-index:-1;"
if index.count(old_z_index) != 1:
    raise SystemExit(f"Buildvalidatie mislukt: Mail PDF negatieve z-index {index.count(old_z_index)}x gevonden")
index = index.replace(old_z_index, "  z-index:auto;", 1)

old_mount = "    document.body.appendChild(stage);\n    return stage;"
if index.count(old_mount) != 1:
    raise SystemExit(f"Buildvalidatie mislukt: Mail PDF DOM-mount {index.count(old_mount)}x gevonden")
index = index.replace(old_mount, "    return stage;", 1)

if "left:-12000px" in index:
    raise SystemExit("Buildvalidatie mislukt: Mail PDF staat nog buiten het capturevlak")
if "document.body.appendChild(stage);" in index:
    raise SystemExit("Buildvalidatie mislukt: Mail PDF renderstage wordt nog zichtbaar gemount")
if "position:relative;\n  left:auto;\n  top:auto;" not in index or "z-index:auto;" not in index:
    raise SystemExit("Buildvalidatie mislukt: Mail PDF renderstage is niet capture-veilig")

index_path.write_text(index, encoding="utf-8")
print("[Machinepark] Mail PDF renderstage capture-veilig gemaakt (geen negatieve offscreen-positie)")
