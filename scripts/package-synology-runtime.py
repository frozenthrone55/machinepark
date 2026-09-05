#!/usr/bin/env python3
from pathlib import Path
import argparse
import shutil

ROOT = Path(__file__).resolve().parents[1]

RUNTIME_FILES = [
    "index.html",
    "service-visits.js",
    "service-visits.css",
    "fault-library.js",
    "fault-library.css",
    "manual-library.js",
    "manual-library.css",
    "offline-first.js",
    "sw.js",
    "synology-local-auth.js",
    "manifest.webmanifest",
    "machinepark-logo.svg",
    "machinepark-coffee-device-icon.png",
]


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    out = Path(args.output).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    missing = []
    for relative in RUNTIME_FILES:
        src = ROOT / relative
        if not src.is_file():
            missing.append(relative)
            continue
        copy_file(src, out / relative)

    assets = ROOT / "assets"
    if assets.is_dir():
        shutil.copytree(assets, out / "assets")

    # PHP-bestanden en gegenereerde lokale seeddata voor de Synology-backend meenemen.
    synology = ROOT / "synology"
    if synology.is_dir():
        for src in synology.rglob("*.php"):
            relative = src.relative_to(ROOT)
            copy_file(src, out / relative)
        seed = synology / "fault-seed.json"
        if seed.is_file():
            copy_file(seed, out / seed.relative_to(ROOT))

    if missing:
        raise SystemExit("Ontbrekende runtime-bestanden: " + ", ".join(missing))

    print(f"Synology runtime klaar in {out}")


if __name__ == "__main__":
    main()
