import { createClerkClient, verifyToken } from '@clerk/backend';
import { normalizeRole } from './_shared/permissions.mjs';

const ADMIN_EMAIL = 'kriskoffieapp@telenet.be';
const NO_STORE = { 'cache-control': 'no-store, max-age=0' };
const COFFEE_FIRST_ORIGIN = 'https://www.coffeefirst.shop';
const ALLOWED_ROLES = new Set(['beheerder', 'gebruiker', 'magazijnier']);
const MAX_IMAGE_BYTES = 3 * 1024 * 1024;

function json(data, status = 200, headers = {}) {
  return Response.json(data, { status, headers: { ...NO_STORE, ...headers } });
}

async function authenticate(req) {
  const secretKey = process.env.CLERK_SECRET_KEY;
  if (!secretKey) throw Object.assign(new Error('CLERK_SECRET_KEY is niet ingesteld in Netlify.'), { status: 500 });
  const authorization = req.headers.get('authorization') || '';
  const token = authorization.startsWith('Bearer ') ? authorization.slice(7).trim() : '';
  if (!token) throw Object.assign(new Error('Aanmelding vereist.'), { status: 401 });

  try {
    const verified = await verifyToken(token, { secretKey });
    if (!verified?.sub) throw new Error('Geen gebruiker in token.');
    const origin = req.headers.get('origin');
    if (origin && verified.azp && verified.azp !== origin) {
      throw Object.assign(new Error('Deze sessie hoort niet bij deze website.'), { status: 403 });
    }
    const clerk = createClerkClient({ secretKey });
    const user = await clerk.users.getUser(verified.sub);
    const primary = (user.emailAddresses || []).find((x) => x.id === user.primaryEmailAddressId);
    const email = String(primary?.emailAddress || user.emailAddresses?.[0]?.emailAddress || '').trim().toLowerCase();
    const owner = (user.emailAddresses || []).some((x) => String(x.emailAddress || '').trim().toLowerCase() === ADMIN_EMAIL);
    const role = normalizeRole(user?.publicMetadata?.role, { owner });
    if (!ALLOWED_ROLES.has(role)) {
      throw Object.assign(new Error('Je rol mag onderdeelgegevens niet aanpassen.'), { status: 403 });
    }
    return { ...verified, email, role };
  } catch (error) {
    if (error?.status) throw error;
    throw Object.assign(new Error('Clerk-sessie kon niet worden geverifieerd.'), { status: 401 });
  }
}

function cleanCode(value) {
  return String(value || '').trim().replace(/\s+/g, ' ');
}

function exactCodeRegex(code) {
  const escaped = code.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`(^|[^A-Za-z0-9])${escaped}([^A-Za-z0-9]|$)`, 'i');
}

function htmlDecode(value) {
  return String(value || '')
    .replace(/&amp;/gi, '&')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>');
}

function stripHtml(html) {
  return htmlDecode(String(html || '').replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<style[\s\S]*?<\/style>/gi, ' ').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' '));
}

function allowedCoffeeFirstUrl(value) {
  try {
    const url = new URL(value, COFFEE_FIRST_ORIGIN);
    const host = url.hostname.toLowerCase();
    return (host === 'coffeefirst.shop' || host === 'www.coffeefirst.shop') && (url.protocol === 'https:' || url.protocol === 'http:') ? url : null;
  } catch {
    return null;
  }
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 12000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {
      redirect: 'follow',
      ...options,
      signal: controller.signal,
      headers: {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36 Machinepark/1.0',
        'accept-language': 'nl-BE,nl;q=0.9,en;q=0.7',
        ...(options.headers || {}),
      },
    });
  } finally {
    clearTimeout(timer);
  }
}

async function lookupMagentoGraphql(code) {
  const query = `query MachineparkPart($sku: String!) {
    products(filter: { sku: { eq: $sku } }) {
      items {
        sku
        name
        url_key
        canonical_url
        image { url label }
        small_image { url label }
        thumbnail { url label }
      }
    }
  }`;
  try {
    const response = await fetchWithTimeout(`${COFFEE_FIRST_ORIGIN}/graphql`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', accept: 'application/json' },
      body: JSON.stringify({ query, variables: { sku: code } }),
    });
    if (!response.ok) return null;
    const body = await response.json();
    const items = Array.isArray(body?.data?.products?.items) ? body.data.products.items : [];
    const exact = items.filter((item) => cleanCode(item?.sku).toLowerCase() === code.toLowerCase());
    if (exact.length !== 1) return null;
    const item = exact[0];
    const imageCandidates = [item?.image?.url, item?.small_image?.url, item?.thumbnail?.url].filter(Boolean);
    const imageUrl = imageCandidates.map(allowedCoffeeFirstUrl).find(Boolean);
    if (!imageUrl || /placeholder|no[_-]?selection/i.test(imageUrl.pathname)) return null;
    let productUrl = null;
    if (item?.canonical_url) productUrl = allowedCoffeeFirstUrl(item.canonical_url);
    if (!productUrl && item?.url_key) productUrl = allowedCoffeeFirstUrl(`${COFFEE_FIRST_ORIGIN}/${String(item.url_key).replace(/^\/+/, '')}.html`);
    return { code, name: String(item?.name || '').trim(), productUrl: productUrl?.href || '', imageUrl: imageUrl.href, method: 'graphql' };
  } catch (error) {
    console.warn('Coffee First GraphQL lookup', error?.message || error);
    return null;
  }
}

function extractProductLinks(html) {
  const links = [];
  const patterns = [
    /<a[^>]*class=["'][^"']*product-item-link[^"']*["'][^>]*href=["']([^"']+)["']/gi,
    /<a[^>]*href=["']([^"']+)["'][^>]*class=["'][^"']*product-item-link[^"']*["']/gi,
  ];
  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(html))) {
      const url = allowedCoffeeFirstUrl(htmlDecode(match[1]));
      if (url && !links.includes(url.href)) links.push(url.href);
    }
  }
  return links.slice(0, 12);
}

function extractMeta(html, key, value) {
  const patterns = [
    new RegExp(`<meta[^>]*${key}=["']${value}["'][^>]*content=["']([^"']+)["']`, 'i'),
    new RegExp(`<meta[^>]*content=["']([^"']+)["'][^>]*${key}=["']${value}["']`, 'i'),
  ];
  for (const pattern of patterns) {
    const match = String(html || '').match(pattern);
    if (match?.[1]) return htmlDecode(match[1]);
  }
  return '';
}

function extractProductName(html) {
  return extractMeta(html, 'property', 'og:title') || extractMeta(html, 'name', 'title') || '';
}

function extractProductImage(html) {
  const candidates = [
    extractMeta(html, 'property', 'og:image'),
    extractMeta(html, 'name', 'twitter:image'),
  ];
  const imagePatterns = [
    /<img[^>]*class=["'][^"']*(?:gallery-placeholder__image|fotorama__img|product-image-photo)[^"']*["'][^>]*(?:src|data-src)=["']([^"']+)["']/i,
    /<img[^>]*(?:src|data-src)=["']([^"']+)["'][^>]*class=["'][^"']*(?:gallery-placeholder__image|fotorama__img|product-image-photo)[^"']*["']/i,
  ];
  for (const pattern of imagePatterns) {
    const match = String(html || '').match(pattern);
    if (match?.[1]) candidates.push(htmlDecode(match[1]));
  }
  return candidates.map(allowedCoffeeFirstUrl).find((url) => url && !/placeholder|no[_-]?selection/i.test(url.pathname)) || null;
}

async function lookupHtml(code) {
  const searchUrls = [
    `${COFFEE_FIRST_ORIGIN}/catalogsearch/result/?q=${encodeURIComponent(code)}`,
    `${COFFEE_FIRST_ORIGIN}/catalogsearch/result/index/?q=${encodeURIComponent(code)}`,
  ];
  for (const searchUrl of searchUrls) {
    try {
      const response = await fetchWithTimeout(searchUrl, { headers: { accept: 'text/html,application/xhtml+xml' } });
      if (!response.ok) continue;
      const html = await response.text();
      const links = extractProductLinks(html);
      const exactCandidates = [];
      for (const link of links) {
        const productResponse = await fetchWithTimeout(link, { headers: { accept: 'text/html,application/xhtml+xml' } });
        if (!productResponse.ok) continue;
        const productHtml = await productResponse.text();
        const text = stripHtml(productHtml);
        if (!exactCodeRegex(code).test(text)) continue;
        const imageUrl = extractProductImage(productHtml);
        if (!imageUrl) continue;
        exactCandidates.push({
          code,
          name: extractProductName(productHtml),
          productUrl: link,
          imageUrl: imageUrl.href,
          method: 'html',
        });
      }
      const unique = [...new Map(exactCandidates.map((x) => [x.productUrl, x])).values()];
      if (unique.length === 1) return unique[0];
      if (unique.length > 1) return { ambiguous: true, count: unique.length };
    } catch (error) {
      console.warn('Coffee First HTML lookup', searchUrl, error?.message || error);
    }
  }
  return null;
}

async function imageAsDataUrl(imageUrl) {
  const safe = allowedCoffeeFirstUrl(imageUrl);
  if (!safe) throw Object.assign(new Error('De gevonden afbeelding staat niet bij Coffee First.'), { status: 422 });
  const response = await fetchWithTimeout(safe.href, { headers: { accept: 'image/avif,image/webp,image/png,image/jpeg,image/*' } }, 15000);
  if (!response.ok) throw Object.assign(new Error(`Coffee First-afbeelding kon niet worden geladen (${response.status}).`), { status: 502 });
  const contentType = String(response.headers.get('content-type') || '').split(';')[0].trim().toLowerCase();
  if (!contentType.startsWith('image/')) throw Object.assign(new Error('De gevonden Coffee First-bron is geen afbeelding.'), { status: 422 });
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (!bytes.length || bytes.length > MAX_IMAGE_BYTES) throw Object.assign(new Error('De gevonden afbeelding is leeg of te groot.'), { status: 422 });
  return `data:${contentType};base64,${Buffer.from(bytes).toString('base64')}`;
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });
  try {
    await authenticate(req);
    if (req.method !== 'POST') return json({ error: 'Methode niet toegestaan.' }, 405, { allow: 'POST, OPTIONS' });
    const body = await req.json();
    const supplierCode = cleanCode(body?.supplierCode);
    const deviceBrand = String(body?.deviceBrand || '').trim();
    if (!supplierCode) return json({ error: 'Code leverancier ontbreekt.' }, 400);
    if (supplierCode.length > 80) return json({ error: 'Code leverancier is ongeldig.' }, 400);
    if (deviceBrand && !/lattiz/i.test(deviceBrand)) return json({ error: 'Dit onderdeel is niet als Lattiz gemarkeerd.' }, 400);

    let match = await lookupMagentoGraphql(supplierCode);
    if (!match) match = await lookupHtml(supplierCode);
    if (match?.ambiguous) return json({ found: false, reason: 'ambiguous', matches: match.count }, 409);
    if (!match) return json({ found: false, reason: 'not-found' }, 404);

    const imageDataUrl = await imageAsDataUrl(match.imageUrl);
    return json({
      found: true,
      supplierCode,
      productName: match.name || '',
      productUrl: match.productUrl || '',
      imageUrl: match.imageUrl,
      imageDataUrl,
      lookupMethod: match.method,
    });
  } catch (error) {
    console.error('lattiz-part-photo', error);
    return json({ error: error?.message || 'Onbekende serverfout.' }, error?.status || 500);
  }
};
