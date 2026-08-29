import { createClerkClient, verifyToken } from '@clerk/backend';
import { normalizeRole } from './_shared/permissions.mjs';

const ADMIN_EMAIL = 'kriskoffieapp@telenet.be';
const NO_STORE = { 'cache-control': 'no-store, max-age=0' };
const COFFEE_FIRST_ORIGIN = 'https://www.coffeefirst.shop';
const ALLOWED_ROLES = new Set(['beheerder', 'gebruiker', 'magazijnier']);
const MAX_IMAGE_BYTES = 3 * 1024 * 1024;

const TECHNICAL_DOCS = [
  {
    id: 'lattiz-v12-training',
    url: 'https://www.coffeefirst.shop/media/TECHNISCH/LATTIZ/TECHNICAL/Lattiz_Techniek_NL_volledig.pdf',
    model: 'v1',
  },
  {
    id: 'lattiz-v20-manual',
    url: 'https://www.coffeefirst.shop/media/wysiwyg/Lattiz_2.0_Technische_handleiding.pdf',
    model: 'v2',
  },
];

const COMPONENT_MARKERS = [
  'condensaatventiel', 'condensatordrainageklep', 'flowmeter', 'hall sensor', 'hall-sensor',
  'luchtpomp', 'waterpomp', 'productmotor', 'produktmotor', 'waterinlaatventiel', 'waterinlaatklep',
  'terugslagklep', 'melkkoppeling', 'melkbox', 'condensaatblok', 'rfid', 'antenne', 'ventiel boiler',
];

let pdfLibPromise = null;
let pngLibPromise = null;
const technicalDocCache = new Map();
const technicalImageCache = new Map();

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

function normalizeText(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
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

async function fetchWithTimeout(url, options = {}, timeoutMs = 5500) {
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
  if (!code) return null;
  const query = `query MachineparkPart($sku: String!) {
    products(filter: { sku: { eq: $sku } }) {
      items {
        sku
        name
        url_key
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
    }, 5000);
    if (!response.ok) return null;
    const body = await response.json();
    const items = Array.isArray(body?.data?.products?.items) ? body.data.products.items : [];
    const exact = items.filter((item) => cleanCode(item?.sku).toLowerCase() === code.toLowerCase());
    if (exact.length !== 1) return null;
    const item = exact[0];
    const imageCandidates = [item?.image?.url, item?.small_image?.url, item?.thumbnail?.url].filter(Boolean);
    const imageUrl = imageCandidates.map(allowedCoffeeFirstUrl).find(Boolean);
    if (!imageUrl || /placeholder|no[_-]?selection/i.test(imageUrl.pathname)) return null;
    const productUrl = item?.url_key ? allowedCoffeeFirstUrl(`${COFFEE_FIRST_ORIGIN}/${String(item.url_key).replace(/^\/+/, '')}.html`) : null;
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
  return links.slice(0, 6);
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

async function inspectProductPage(link, code) {
  try {
    const productResponse = await fetchWithTimeout(link, { headers: { accept: 'text/html,application/xhtml+xml' } }, 4500);
    if (!productResponse.ok) return null;
    const productHtml = await productResponse.text();
    if (!exactCodeRegex(code).test(stripHtml(productHtml))) return null;
    const imageUrl = extractProductImage(productHtml);
    if (!imageUrl) return null;
    return { code, name: extractProductName(productHtml), productUrl: link, imageUrl: imageUrl.href, method: 'html' };
  } catch {
    return null;
  }
}

async function lookupHtml(code) {
  if (!code) return null;
  const searchUrls = [
    `${COFFEE_FIRST_ORIGIN}/catalogsearch/result/?q=${encodeURIComponent(code)}`,
    `${COFFEE_FIRST_ORIGIN}/catalogsearch/result/index/?q=${encodeURIComponent(code)}`,
  ];
  for (const searchUrl of searchUrls) {
    try {
      const response = await fetchWithTimeout(searchUrl, { headers: { accept: 'text/html,application/xhtml+xml' } }, 4500);
      if (!response.ok) continue;
      const html = await response.text();
      const links = extractProductLinks(html);
      if (!links.length) continue;
      const checked = await Promise.all(links.map((link) => inspectProductPage(link, code)));
      const exactCandidates = checked.filter(Boolean);
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
  const response = await fetchWithTimeout(safe.href, { headers: { accept: 'image/avif,image/webp,image/png,image/jpeg,image/*' } }, 7000);
  if (!response.ok) throw Object.assign(new Error(`Coffee First-afbeelding kon niet worden geladen (${response.status}).`), { status: 502 });
  const contentType = String(response.headers.get('content-type') || '').split(';')[0].trim().toLowerCase();
  if (!contentType.startsWith('image/')) throw Object.assign(new Error('De gevonden Coffee First-bron is geen afbeelding.'), { status: 422 });
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (!bytes.length || bytes.length > MAX_IMAGE_BYTES) throw Object.assign(new Error('De gevonden afbeelding is leeg of te groot.'), { status: 422 });
  return `data:${contentType};base64,${Buffer.from(bytes).toString('base64')}`;
}

function technicalProfile(description) {
  const text = normalizeText(description);
  const profiles = [
    { test: /condensaatventiel|condensatordrainage/, label: 'Condensaatventiel', aliases: ['condensaatventiel', 'condensatordrainageklep'] },
    { test: /flowmeter/, label: 'Flowmeter', aliases: ['flowmeter'] },
    { test: /hall sensor/, label: 'Hall-sensor', aliases: ['hall sensor', 'hall-sensor'] },
    { test: /luchtpomp/, label: 'Luchtpomp', aliases: ['luchtpomp'] },
    { test: /waterpomp/, label: 'Waterpomp', aliases: ['waterpomp', 'water pump'] },
    { test: /produktmotor|productmotor/, label: 'Productmotor', aliases: ['productmotor', 'produktmotor'] },
    { test: /water inlaat ventiel|waterinlaatventiel/, label: 'Waterinlaatventiel', aliases: ['waterinlaatventiel', 'waterinlaatklep', 'inlaatklep'] },
    { test: /terugslagklep/, label: 'Terugslagklep', aliases: ['terugslagklep'] },
    { test: /koppeling melkbox|melkkoppeling/, label: 'Melkkoppeling', aliases: ['melkkoppeling', 'melkbox'] },
    { test: /condensaatblok/, label: 'Condensaatblok', aliases: ['condensaatblok', 'condensatorblok'] },
  ];
  return profiles.find((profile) => profile.test.test(text)) || null;
}

function technicalDocsFor(description) {
  const text = normalizeText(description);
  if (/lattiz 2 0|\b2 0\b/.test(text)) return TECHNICAL_DOCS.filter((doc) => doc.model === 'v2');
  if (/lattiz 1 0|lattiz v1|v1 x|v1 1|v1 2|\b1 0\b/.test(text)) return TECHNICAL_DOCS.filter((doc) => doc.model === 'v1');
  return TECHNICAL_DOCS;
}

async function pdfLibrary() {
  if (!pdfLibPromise) pdfLibPromise = import('pdfjs-dist/legacy/build/pdf.mjs');
  return pdfLibPromise;
}

async function pngLibrary() {
  if (!pngLibPromise) pngLibPromise = import('pngjs');
  return pngLibPromise;
}

async function loadTechnicalDocument(definition) {
  if (technicalDocCache.has(definition.id)) return technicalDocCache.get(definition.id);
  const promise = (async () => {
    const response = await fetchWithTimeout(definition.url, { headers: { accept: 'application/pdf' } }, 9000);
    if (!response.ok) throw new Error(`Technische Coffee First-documentatie kon niet worden geladen (${response.status}).`);
    const contentType = String(response.headers.get('content-type') || '').toLowerCase();
    if (!contentType.includes('pdf')) throw new Error('De Coffee First-techniekbron is geen PDF.');
    const bytes = new Uint8Array(await response.arrayBuffer());
    const pdfjs = await pdfLibrary();
    const loadingTask = pdfjs.getDocument({
      data: bytes,
      disableWorker: true,
      isOffscreenCanvasSupported: false,
      useSystemFonts: true,
    });
    const pdf = await loadingTask.promise;
    return { definition, pdf };
  })().catch((error) => {
    technicalDocCache.delete(definition.id);
    throw error;
  });
  technicalDocCache.set(definition.id, promise);
  return promise;
}

function componentDensity(text) {
  const normalized = normalizeText(text);
  return COMPONENT_MARKERS.reduce((count, marker) => count + (normalized.includes(normalizeText(marker)) ? 1 : 0), 0);
}

async function findTechnicalPage(document, profile) {
  let best = null;
  let tied = false;
  for (let pageNumber = 1; pageNumber <= document.pdf.numPages; pageNumber += 1) {
    const page = await document.pdf.getPage(pageNumber);
    const content = await page.getTextContent();
    const text = normalizeText((content.items || []).map((item) => item?.str || '').join(' '));
    const hits = profile.aliases.filter((alias) => text.includes(normalizeText(alias))).length;
    if (!hits) continue;
    const density = componentDensity(text);
    const componentPage = text.includes('componenten');
    const repairPage = text.includes('reparatie') || text.includes('vervangen') || text.includes('demontage') || text.includes('montage');
    if (density > 3 && !componentPage) continue;
    const score = hits * 10 + (componentPage ? 8 : 0) + (repairPage ? 5 : 0) - Math.max(0, density - 1) * 3;
    if (!best || score > best.score) {
      best = { pageNumber, page, text, score, density };
      tied = false;
    } else if (best && score === best.score) {
      tied = true;
    }
  }
  if (!best || tied || best.score < 10) return null;
  return best;
}

function objectFromStore(store, name) {
  if (!store || !name) return Promise.resolve(null);
  try {
    if (store.has(name)) return Promise.resolve(store.get(name));
  } catch {}
  return new Promise((resolve) => {
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(value || null);
    };
    const timer = setTimeout(() => finish(null), 1200);
    try {
      store.get(name, finish);
    } catch {
      finish(null);
    }
  });
}

function rgbaFromPdfImage(image) {
  const width = Number(image?.width || 0);
  const height = Number(image?.height || 0);
  const raw = image?.data;
  if (!width || !height || !raw) return null;
  const src = Buffer.from(raw.buffer, raw.byteOffset || 0, raw.byteLength || raw.length || 0);
  const pixels = width * height;
  if (src.length === pixels * 4) return { width, height, data: Buffer.from(src) };
  if (src.length === pixels * 3) {
    const out = Buffer.allocUnsafe(pixels * 4);
    for (let i = 0, j = 0; i < src.length; i += 3, j += 4) {
      out[j] = src[i]; out[j + 1] = src[i + 1]; out[j + 2] = src[i + 2]; out[j + 3] = 255;
    }
    return { width, height, data: out };
  }
  if (src.length === pixels) {
    const out = Buffer.allocUnsafe(pixels * 4);
    for (let i = 0, j = 0; i < src.length; i += 1, j += 4) {
      out[j] = src[i]; out[j + 1] = src[i]; out[j + 2] = src[i]; out[j + 3] = 255;
    }
    return { width, height, data: out };
  }
  return null;
}

async function technicalPageImage(document, pageInfo) {
  const cacheKey = `${document.definition.id}:${pageInfo.pageNumber}`;
  if (technicalImageCache.has(cacheKey)) return technicalImageCache.get(cacheKey);
  const promise = (async () => {
    const pdfjs = await pdfLibrary();
    const page = pageInfo.page;
    const operatorList = await page.getOperatorList();
    const viewport = page.getViewport({ scale: 1 });
    const pageRatio = viewport.width / Math.max(1, viewport.height);
    const candidates = [];

    for (let index = 0; index < operatorList.fnArray.length; index += 1) {
      const fn = operatorList.fnArray[index];
      const args = operatorList.argsArray[index];
      let image = null;
      if (fn === pdfjs.OPS.paintInlineImageXObject) {
        image = args?.[0] || null;
      } else if (fn === pdfjs.OPS.paintImageXObject) {
        const name = args?.[0];
        const store = String(name || '').startsWith('g_') ? page.commonObjs : page.objs;
        image = await objectFromStore(store, name);
      } else {
        continue;
      }
      const rgba = rgbaFromPdfImage(image);
      if (!rgba || rgba.width < 100 || rgba.height < 70) continue;
      const area = rgba.width * rgba.height;
      if (area < 12000) continue;
      const ratio = rgba.width / Math.max(1, rgba.height);
      if (ratio > 4.2 || ratio < 0.24) continue;
      candidates.push({ ...rgba, area, ratio });
    }

    if (!candidates.length) return null;
    candidates.sort((a, b) => b.area - a.area);
    if (candidates.length > 1) {
      for (const candidate of candidates) {
        const looksLikeFullPage = candidate.area > 700000 && Math.abs(candidate.ratio - pageRatio) < 0.18;
        candidate.rank = candidate.area * (looksLikeFullPage ? 0.015 : 1);
      }
      candidates.sort((a, b) => b.rank - a.rank);
    } else {
      const only = candidates[0];
      if (only.area > 700000 && Math.abs(only.ratio - pageRatio) < 0.18) return null;
    }

    const chosen = candidates[0];
    const { PNG } = await pngLibrary();
    const encoded = PNG.sync.write({ width: chosen.width, height: chosen.height, data: chosen.data }, { colorType: 6 });
    if (!encoded.length || encoded.length > MAX_IMAGE_BYTES) return null;
    return `data:image/png;base64,${encoded.toString('base64')}`;
  })().catch((error) => {
    console.warn('Coffee First PDF-afbeelding', cacheKey, error?.message || error);
    return null;
  });
  technicalImageCache.set(cacheKey, promise);
  return promise;
}

async function lookupTechnicalDocumentation(description) {
  const profile = technicalProfile(description);
  if (!profile) return null;
  const docs = technicalDocsFor(description);
  const matches = [];
  for (const definition of docs) {
    try {
      const document = await loadTechnicalDocument(definition);
      const pageInfo = await findTechnicalPage(document, profile);
      if (!pageInfo) continue;
      const imageDataUrl = await technicalPageImage(document, pageInfo);
      if (!imageDataUrl) continue;
      matches.push({
        code: '',
        name: `${profile.label} · Coffee First technische documentatie`,
        productUrl: `${definition.url}#page=${pageInfo.pageNumber}`,
        imageUrl: '',
        imageDataUrl,
        method: 'technical-pdf',
        sourcePage: pageInfo.pageNumber,
      });
    } catch (error) {
      console.warn('Coffee First technical documentation', definition.id, error?.message || error);
    }
  }
  if (matches.length !== 1) return null;
  return matches[0];
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });
  try {
    await authenticate(req);
    if (req.method !== 'POST') return json({ error: 'Methode niet toegestaan.' }, 405, { allow: 'POST, OPTIONS' });
    const body = await req.json();
    const supplierCode = cleanCode(body?.supplierCode);
    const deviceBrand = String(body?.deviceBrand || '').trim();
    const description = String(body?.description || '').trim();
    if (supplierCode.length > 80) return json({ error: 'Code leverancier is ongeldig.' }, 400);
    if (!description && !supplierCode) return json({ error: 'Leverancierscode en omschrijving ontbreken.' }, 400);
    if (deviceBrand && !/lattiz/i.test(deviceBrand)) return json({ error: 'Dit onderdeel is niet als Lattiz gemarkeerd.' }, 400);

    let match = null;
    if (supplierCode) {
      match = await lookupMagentoGraphql(supplierCode);
      if (!match) match = await lookupHtml(supplierCode);
      if (match?.ambiguous) return json({ found: false, reason: 'ambiguous', matches: match.count }, 409);
    }

    if (match) {
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
    }

    const technical = await lookupTechnicalDocumentation(description);
    if (!technical) return json({ found: false, reason: 'not-found' }, 404);

    return json({
      found: true,
      supplierCode,
      productName: technical.name,
      productUrl: technical.productUrl,
      imageUrl: '',
      imageDataUrl: technical.imageDataUrl,
      lookupMethod: technical.method,
      sourcePage: technical.sourcePage,
    });
  } catch (error) {
    console.error('lattiz-part-photo', error);
    return json({ error: error?.message || 'Onbekende serverfout.' }, error?.status || 500);
  }
};
