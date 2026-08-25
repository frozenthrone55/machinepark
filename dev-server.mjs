import http from 'node:http';
import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';
import { verifyToken } from '@clerk/backend';

const ROOT = fileURLToPath(new URL('.', import.meta.url));
const DATA_DIR = join(ROOT, '.dev-data');
const DATA_FILE = join(DATA_DIR, 'machinepark-state.json');
const HOST = '127.0.0.1';
const PORT = Number(process.env.PORT || 8888);
const MIME={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.webmanifest':'application/manifest+json; charset=utf-8','.css':'text/css; charset=utf-8','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.svg':'image/svg+xml','.ico':'image/x-icon'};

function send(res,status,body='',headers={}){res.writeHead(status,{'cache-control':'no-store',...headers});res.end(body)}
function json(res,status,data,headers={}){send(res,status,JSON.stringify(data),{'content-type':'application/json; charset=utf-8',...headers})}
function etagOf(text){return '"'+createHash('sha256').update(text).digest('hex').slice(0,32)+'"'}
async function readState(){try{const text=await readFile(DATA_FILE,'utf8');return{text,data:JSON.parse(text),etag:etagOf(text)}}catch(e){if(e?.code==='ENOENT')return null;throw e}}
async function authenticate(req){const secretKey=process.env.CLERK_SECRET_KEY;if(!secretKey?.startsWith('sk_test_'))throw Object.assign(new Error('Gebruik een Clerk Development secret key (sk_test_...).'),{status:500});const auth=req.headers.authorization||'';const token=auth.startsWith('Bearer ')?auth.slice(7).trim():'';if(!token)throw Object.assign(new Error('Aanmelding vereist.'),{status:401});try{const verified=await verifyToken(token,{secretKey});if(!verified?.sub)throw new Error('Geen gebruiker in token.');const origin=req.headers.origin;if(origin&&verified.azp&&verified.azp!==origin)throw Object.assign(new Error('Deze sessie hoort niet bij deze lokale website.'),{status:403});return verified}catch(e){if(e?.status)throw e;throw Object.assign(new Error('Clerk Development-sessie kon niet worden geverifieerd.'),{status:401})}}
function validSnapshot(data){return Boolean(data&&data.app==='Machinepark'&&Number(data.schema)===1&&Array.isArray(data.parts)&&Array.isArray(data.devices)&&Array.isArray(data.maintenance)&&Array.isArray(data.breakdowns))}
async function readBody(req){const chunks=[];for await(const chunk of req)chunks.push(chunk);return Buffer.concat(chunks).toString('utf8')}

async function handleFunction(req,res,pathname){
  if(pathname==='/.netlify/functions/clerk-config'){const publishableKey=process.env.CLERK_PUBLISHABLE_KEY;if(!publishableKey?.startsWith('pk_test_'))return json(res,500,{error:'Gebruik een Clerk Development publishable key (pk_test_...).'});return json(res,200,{publishableKey})}
  if(pathname!=='/.netlify/functions/machinepark-data')return false;
  if(req.method==='OPTIONS')return send(res,204);
  try{
    const auth=await authenticate(req);const current=await readState();
    if(req.method==='GET'){if(!current)return json(res,200,{exists:false,etag:null});const requested=req.headers['if-none-match'];if(requested&&requested===current.etag)return send(res,304,'',{etag:current.etag});return json(res,200,{exists:true,etag:current.etag,data:current.data},{etag:current.etag})}
    if(req.method==='PUT'){const body=JSON.parse(await readBody(req)||'{}');const data=body?.data;const expectedEtag=body?.etag||null;if(!validSnapshot(data))return json(res,400,{error:'Ongeldige Machinepark-gegevens.'});if(current&&!expectedEtag)return json(res,409,{error:'Er bestaat al een lokale development-versie.',etag:current.etag});if(current&&expectedEtag!==current.etag)return json(res,409,{error:'De lokale development-gegevens zijn intussen gewijzigd.',etag:current.etag});if(!current&&expectedEtag)return json(res,409,{error:'De lokale development-store is leeg.',etag:null});data.updatedAt=new Date().toISOString();data.updatedBy=auth.sub;const text=JSON.stringify(data);await mkdir(DATA_DIR,{recursive:true});await writeFile(DATA_FILE,text,'utf8');const etag=etagOf(text);return json(res,200,{ok:true,etag,updatedAt:data.updatedAt})}
    return json(res,405,{error:'Methode niet toegestaan.'},{allow:'GET, PUT, OPTIONS'});
  }catch(e){console.error('[development api]',e);return json(res,e?.status||500,{error:e?.message||'Onbekende lokale serverfout.'})}
}

async function serveStatic(req,res,pathname){let rel=pathname==='/'?'index.html':decodeURIComponent(pathname).replace(/^\/+/, '');rel=normalize(rel).replace(/^(\.\.(\/|\\|$))+/, '');const file=join(ROOT,rel);if(!file.startsWith(ROOT))return send(res,403,'Forbidden');try{const info=await stat(file);if(!info.isFile())throw Object.assign(new Error(),{code:'ENOENT'});const body=await readFile(file);send(res,200,body,{'content-type':MIME[extname(file).toLowerCase()]||'application/octet-stream'})}catch(e){if(e?.code==='ENOENT')return send(res,404,'Niet gevonden');throw e}}

const server=http.createServer(async(req,res)=>{try{const url=new URL(req.url,`http://${req.headers.host||`${HOST}:${PORT}`}`);if(url.pathname.startsWith('/.netlify/functions/')){const handled=await handleFunction(req,res,url.pathname);if(handled!==false)return}await serveStatic(req,res,url.pathname)}catch(e){console.error(e);send(res,500,'Lokale development-serverfout')}});
server.listen(PORT,HOST,()=>{console.log('');console.log('================================================');console.log(' Machinepark DEVELOPMENT — ZERO NETLIFY CREDITS');console.log(` http://${HOST}:${PORT}`);console.log(' Testdata: .dev-data/machinepark-state.json');console.log(' Stoppen: Ctrl+C');console.log('================================================');console.log('')});
