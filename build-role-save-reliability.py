from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
ROLE_API = ROOT / 'synology/api/role-management.php'
MARKER = 'machinepark-role-save-reliability-v1'

index = INDEX.read_text(encoding='utf-8')
api = ROLE_API.read_text(encoding='utf-8')

# 1. Client: lees altijd de ruwe respons zodat Synology/PHP-fouten zichtbaar
# blijven. Wanneer Synology een lege HTTP 400 op de JSON-POST teruggeeft,
# probeer dezelfde beveiligde aanvraag één keer opnieuw als urlencoded payload.
old_fetch = """  async function roleFetch(options = {}) {
    const headers = await centralHeaders(options.body !== undefined);
    const res = await fetch(ROLE_MANAGEMENT_URL, { ...options, headers: { ...headers, ...(options.headers || {}) }, cache: 'no-store' });
    let body = {};
    try { body = await res.json(); } catch (_) {}
    if (!res.ok) throw new Error(body?.error || `Rollenbeheer mislukt (${res.status})`);
    return body;
  }"""
new_fetch = """  async function roleFetch(options = {}) {
    const run = async (requestOptions) => {
      const headers = await centralHeaders(requestOptions.body !== undefined);
      const res = await fetch(ROLE_MANAGEMENT_URL, {
        ...requestOptions,
        headers: { ...headers, ...(requestOptions.headers || {}) },
        cache: 'no-store',
        credentials: 'same-origin',
      });
      const text = await res.text();
      let body = {};
      try { body = text ? JSON.parse(text) : {}; } catch (_) {}
      return { res, text, body };
    };

    let result = await run(options);
    const method = String(options?.method || 'GET').toUpperCase();

    // Sommige Synology/Web Station-combinaties beantwoorden een JSON POST
    // uitzonderlijk met een lege 400. Herhaal dan exact dezelfde payload via
    // application/x-www-form-urlencoded; de PHP-route valideert daarna normaal.
    if (!result.res.ok && result.res.status === 400 && method === 'POST' && !result.body?.error && typeof options.body === 'string') {
      const fallbackHeaders = await centralHeaders(false);
      fallbackHeaders['Content-Type'] = 'application/x-www-form-urlencoded;charset=UTF-8';
      const fallbackRes = await fetch(ROLE_MANAGEMENT_URL + '?compat=1', {
        method: 'POST',
        headers: fallbackHeaders,
        body: 'payload=' + encodeURIComponent(options.body),
        cache: 'no-store',
        credentials: 'same-origin',
      });
      const fallbackText = await fallbackRes.text();
      let fallbackBody = {};
      try { fallbackBody = fallbackText ? JSON.parse(fallbackText) : {}; } catch (_) {}
      result = { res: fallbackRes, text: fallbackText, body: fallbackBody };
    }

    if (!result.res.ok) {
      const raw = String(result.body?.error || result.text || '')
        .replace(/<script[\\s\\S]*?<\\/script>/gi, ' ')
        .replace(/<style[\\s\\S]*?<\\/style>/gi, ' ')
        .replace(/<[^>]*>/g, ' ')
        .replace(/\\s+/g, ' ')
        .trim()
        .slice(0, 260);
      const error = new Error(raw || `Rollenbeheer mislukt (${result.res.status})`);
      error.status = result.res.status;
      throw error;
    }
    return result.body;
  }"""

if MARKER not in index:
    count = index.count(old_fetch)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: roleFetch verwacht 1x, gevonden {count}x')
    index = index.replace(old_fetch, new_fetch, 1)
    end = index.rfind('</body>')
    if end < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor role save reliability')
    index = index[:end] + f'\n<!-- {MARKER} -->\n' + index[end:]
    INDEX.write_text(index, encoding='utf-8')

# 2. Server: houd PHP-waarschuwingen uit de JSON-respons en accepteer de
# compatibiliteitspayload. De autorisatie, rechtencontrole en ETag-logica blijven
# identiek aan de normale JSON-route.
if MARKER not in api:
    require_anchor = "require_once __DIR__ . '/_audit-lib.php';\n"
    if api.count(require_anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: role API require-anker niet uniek')
    api = api.replace(
        require_anchor,
        require_anchor + "\n@ini_set('display_errors', '0');\n",
        1,
    )

    json_anchor = """function role_json(array $body, int $status = 200, array $headers = []): void {
    http_response_code($status);
    foreach ($headers as $name => $value) header($name . ': ' . $value);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}
"""
    json_new = """function role_json(array $body, int $status = 200, array $headers = []): void {
    http_response_code($status);
    header('X-Machinepark-Role-API: 2');
    foreach ($headers as $name => $value) header($name . ': ' . $value);
    $json = json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false) {
        echo '{\"error\":\"Rollenbeheer kon geen geldige JSON-respons maken.\"}';
        exit;
    }
    echo $json;
    exit;
}

function role_decode_request_body($raw): array {
    $decoded = json_decode($raw === false ? '' : (string)$raw, true);
    if (is_array($decoded)) return $decoded;
    $compat = isset($_POST['payload']) ? (string)$_POST['payload'] : '';
    if ($compat !== '') {
        $decoded = json_decode($compat, true);
        if (is_array($decoded)) return $decoded;
    }
    return [];
}
"""
    if api.count(json_anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: role_json anker niet uniek')
    api = api.replace(json_anchor, json_new, 1)

    body_old = """$raw = file_get_contents('php://input');
$body = json_decode($raw === false ? '' : $raw, true);
if (!is_array($body)) role_json(['error'=>'Ongeldige aanvraag.'], 400);"""
    body_new = """$raw = file_get_contents('php://input');
$body = role_decode_request_body($raw);
if (!$body) role_json(['error'=>'Ongeldige aanvraag. Vernieuw de pagina en probeer opnieuw.'], 400);"""
    if api.count(body_old) != 1:
        raise SystemExit('Buildvalidatie mislukt: role request body anker niet uniek')
    api = api.replace(body_old, body_new, 1)

    # Een volledig geldige zichtbare rolnaam mag nooit stranden omdat alleen de
    # technische slug leeg wordt (bijv. een naam met uitsluitend Unicode).
    id_old = """        $requestedId = mp_role_sanitize_id($incoming['id'] ?? ($incoming['label'] ?? ''));
        $label = trim((string)($incoming['label'] ?? ''));
        if ($requestedId === '' || $label === '') throw new RuntimeException('Vul een geldige rolnaam in.');"""
    id_new = """        $label = trim((string)($incoming['label'] ?? ''));
        if ($label === '') throw new RuntimeException('Vul een geldige rolnaam in.');
        $requestedId = mp_role_sanitize_id($incoming['id'] ?? $label);
        if ($requestedId === '') $requestedId = 'rol-' . substr(hash('sha256', $label), 0, 12);"""
    if api.count(id_old) != 1:
        raise SystemExit('Buildvalidatie mislukt: role id anker niet uniek')
    api = api.replace(id_old, id_new, 1)

    api += f"\n// {MARKER}\n"
    ROLE_API.write_text(api, encoding='utf-8')

# Eindcontrole.
index = INDEX.read_text(encoding='utf-8')
api = ROLE_API.read_text(encoding='utf-8')
for needle in [
    MARKER,
    "application/x-www-form-urlencoded;charset=UTF-8",
    "credentials: 'same-origin'",
    "const text = await res.text()",
    'role_decode_request_body',
    "X-Machinepark-Role-API: 2",
    "rol-' . substr(hash('sha256', $label), 0, 12)",
]:
    if needle not in index + '\n' + api:
        raise SystemExit('Buildvalidatie role save reliability mislukt: ' + needle)

print('[Machinepark] nieuwe rollen opslaan robuust gemaakt voor Synology/Web Station')
