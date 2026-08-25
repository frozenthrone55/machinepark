from pathlib import Path
p=Path('netlify/functions/machinepark-data.mjs')
s=p.read_text(encoding='utf-8')
s=s.replace("const CLEAR_SERVICE_DATES_MIGRATION_KEY = 'migration/clear-service-dates-2026-08-25-v1';\n", "const CLEAR_SERVICE_DATES_MIGRATION_KEY = 'migration/clear-service-dates-2026-08-25-v1';\nconst ADMIN_EMAIL = 'kriskoffieapp@telenet.be';\n", 1)
s=s.replace("async function clearServiceDatesOnce(store, auth) {\n  const marker", "async function clearServiceDatesOnce(store, auth) {\n  if (String(auth?.email || '').toLowerCase() !== ADMIN_EMAIL) return;\n  const marker", 1)
if "const ADMIN_EMAIL = 'kriskoffieapp@telenet.be';" not in s or "!== ADMIN_EMAIL) return;" not in s:
    raise SystemExit('Adminbeveiliging niet toegepast')
p.write_text(s,encoding='utf-8')
