from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-build-fix="excel-local-save-v1"'
OLD = "downloadBlob(`Machinepark_Onderdelen_${todayISO()}.xlsx`, xlsxBlob);"
NEW = "if (!(await saveMachineparkExcelFile(`Machinepark_Onderdelen_${todayISO()}.xlsx`, xlsxBlob))) return;"

if MARKER not in index:
    if OLD not in index and NEW not in index:
        raise SystemExit("Buildvalidatie mislukt: Excel-downloadregel niet gevonden")
    index = index.replace(OLD, NEW, 1)

    script = r'''
<script data-machinepark-build-fix="excel-local-save-v1">
async function saveMachineparkExcelFile(fileName, blob) {
  if (typeof window.showSaveFilePicker === 'function') {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: fileName,
        types: [{
          description: 'Excel-werkmap',
          accept: {
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
          }
        }]
      });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return true;
    } catch (error) {
      if (error?.name === 'AbortError') return false;
      console.warn('Rechtstreeks Excel opslaan niet beschikbaar, normale download wordt gebruikt.', error);
    }
  }

  downloadBlob(fileName, blob);
  return true;
}
</script>
'''

    if "</body>" not in index:
        raise SystemExit("Buildvalidatie mislukt: body-afsluiter ontbreekt voor lokaal Excel opslaan")
    index = index.replace("</body>", script + "</body>", 1)
    index_path.write_text(index, encoding="utf-8")

required = [
    MARKER,
    "showSaveFilePicker",
    "createWritable",
    "saveMachineparkExcelFile",
    NEW,
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: lokaal Excel opslaan ontbreekt ({needle})")

print("[Machinepark] Excel-export wordt via Opslaan als lokaal opgeslagen waar ondersteund")
