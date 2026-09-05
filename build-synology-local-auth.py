from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="synology-local-auth-v1"'

def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)

if MARKER not in index:
    replacements = [
        ('/* Netlify + Clerk loginlaag */', '/* Lokale Synology loginlaag */', 'login CSS label'),
        ('Open Machinepark via een HTTPS-webadres (via Netlify) in Chrome of Safari.',
         'Open Machinepark via het lokale Synology-webadres in Chrome of Safari.', 'noscript hostingtekst'),
        ('<small>Gehost via Netlify • Login via Clerk</small>',
         '<small>Lokaal gehost op Synology • Eigen gebruikersbeheer</small>', 'auth footer'),
        ('<p>Gebruik je Machinepark-account.</p>\n      <div id="clerkSignIn"></div>\n      <div id="authLoading">Clerk wordt geladen…</div>',
         '<p>Gebruik je lokale Machinepark-account.</p>\n      <div id="localAuthForm"></div>\n      <div id="authLoading">Lokale sessie controleren…</div>', 'auth formulier'),
        ('<div class="side-foot">Centrale synchronisatie • Netlify + Clerk<br><br>v1.64 • Export inclusief afbeeldingen</div>',
         '<div class="side-foot">Lokale synchronisatie • Synology<br><br>Eigen beheer • lokale opslag</div>', 'sidebar footer'),
        ('<div id="clerkUserButton" class="clerk-user-slot clerk-user-single"></div>',
         '<button type="button" id="localLogoutBtn" class="btn small" style="white-space:nowrap">Afmelden</button>', 'afmeldknop'),
    ]
    for old, new, label in replacements:
        replace_once(old, new, label)

    # Vervang de token-headerfunctie zonder afhankelijk te zijn van de Clerk template-literal.
    header_start = index.find("async function centralHeaders(json=false){")
    header_end_anchor = "\nasync function localSnapshot"
    header_end = index.find(header_end_anchor, header_start)
    if header_start < 0 or header_end < 0:
        raise SystemExit("Buildvalidatie mislukt: centrale headerfunctie niet gevonden")
    index = (
        index[:header_start]
        + "async function centralHeaders(json=false){const h={};if(json)h['Content-Type']='application/json';return h}"
        + index[header_end:]
    )

    # Verwijder de volledige Clerk bootlaag.
    clerk_start_marker = "<script>\n(function(){\n  let signInMounted=false;"
    clerk_start = index.find(clerk_start_marker)
    if clerk_start < 0:
        raise SystemExit("Buildvalidatie mislukt: Clerk opstartscript niet gevonden")
    clerk_end_marker = "\n})();\n</script>"
    clerk_end = index.find(clerk_end_marker, clerk_start)
    if clerk_end < 0:
        raise SystemExit("Buildvalidatie mislukt: einde Clerk opstartscript niet gevonden")
    clerk_end += len(clerk_end_marker)
    index = index[:clerk_start] + index[clerk_end:]

    worker_anchor = "<script>\nif ('serviceWorker' in navigator"
    if worker_anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: service worker script niet gevonden")
    index = index.replace(
        worker_anchor,
        '<script src="./synology-local-auth.js"></script>\n' + worker_anchor,
        1,
    )

    # Relatieve paden werken zowel via lokaal IP, synology.me als DuckDNS.
    index = index.replace('src="/machinepark-logo.svg"', 'src="./machinepark-logo.svg"')
    index = index.replace(
        'Controleer de Netlify HTTPS-link en probeer opnieuw.',
        'Controleer de Synology-verbinding en probeer opnieuw.'
    )
    index = index.replace(
        'Het login-e-mailadres wordt door Clerk beheerd en vereist verificatie om te wijzigen.',
        'Het login-e-mailadres wordt lokaal op de Synology beheerd.'
    )

    index = index.replace(
        "</head>",
        f'<meta {MARKER}><meta name="machinepark-auth" content="synology-local">\n</head>',
        1,
    )
    index_path.write_text(index, encoding="utf-8")

built = index_path.read_text(encoding="utf-8")
required = [
    MARKER,
    'src="./synology-local-auth.js"',
    'Lokaal gehost op Synology',
    'Eigen gebruikersbeheer',
    'id="localAuthForm"',
    'id="localLogoutBtn"',
    "async function centralHeaders(json=false){const h={};",
    'machinepark-auth',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f"Buildvalidatie mislukt: lokale Synology-login ontbreekt ({needle})")

for forbidden in [
    '/.netlify/functions/clerk-config',
    'CLERK_PUBLISHABLE_KEY',
    'Login via Clerk',
    'Clerk wordt geladen',
]:
    if forbidden in built:
        raise SystemExit(f"Buildvalidatie mislukt: oude Clerk-opstart blijft aanwezig ({forbidden})")

print("[Machinepark] lokale Synology login vervangt Clerk")
