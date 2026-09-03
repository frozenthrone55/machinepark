from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'index.html'

html = INDEX.read_text(encoding='utf-8')
script_re = re.compile(r'<script(?P<attrs>[^>]*)>(?P<body>.*?)</script\s*>', re.IGNORECASE | re.DOTALL)
checked = 0

for number, match in enumerate(script_re.finditer(html), start=1):
    attrs = match.group('attrs') or ''
    body = match.group('body') or ''
    if re.search(r'\bsrc\s*=', attrs, re.IGNORECASE):
        continue
    type_match = re.search(r'\btype\s*=\s*["\']([^"\']+)["\']', attrs, re.IGNORECASE)
    if type_match and type_match.group(1).lower() not in {
        'text/javascript',
        'application/javascript',
        'module',
    }:
        continue
    if not body.strip():
        continue

    checked += 1
    with tempfile.NamedTemporaryFile('w', suffix='.mjs', encoding='utf-8', delete=False) as temp:
        temp.write(body)
        temp_path = Path(temp.name)
    try:
        result = subprocess.run(
            ['node', '--check', str(temp_path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    if result.returncode != 0:
        output = (result.stderr or result.stdout or '').strip()
        raise SystemExit(
            f'Inline JavaScript syntaxfout in index.html script #{number} '
            f'(attrs: {attrs.strip() or "geen"}):\n{output}'
        )

if checked == 0:
    raise SystemExit('Buildvalidatie mislukt: geen inline JavaScript gevonden in index.html')

print(f'[Machinepark] {checked} inline scripts syntactisch geldig')
