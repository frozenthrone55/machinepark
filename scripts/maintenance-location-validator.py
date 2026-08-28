from pathlib import Path
import re

p = Path('scripts/build-machinepark.py')
text = p.read_text(encoding='utf-8')
text = text.replace('"locatiegericht onderhoud": "id=\\"maintenanceLocation\\"",', '"locatiegericht onderhoud": "id=\\"maintenanceLocationSearch\\"",')
text = re.sub(r'machinepark-v[0-9.]+-[a-zA-Z0-9-]+', 'machinepark-v1.57-maintenance-location-search', text)
p.write_text(text, encoding='utf-8')
