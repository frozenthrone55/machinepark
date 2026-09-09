import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const builder=readFileSync(new URL('../build-video-media-support.py',import.meta.url),'utf8');
const lib=readFileSync(new URL('../synology/api/_photo-lib.php',import.meta.url),'utf8');
const device=readFileSync(new URL('../synology/api/device-photos.php',import.meta.url),'utf8');
const service=readFileSync(new URL('../synology/api/service-photos.php',import.meta.url),'utf8');
const action=readFileSync(new URL('../synology/api/action-photos.php',import.meta.url),'utf8');
const part=readFileSync(new URL('../synology/api/part-photos.php',import.meta.url),'utf8');
const offline=readFileSync(new URL('../offline-first.js',import.meta.url),'utf8');
const pkg=JSON.parse(readFileSync(new URL('../package.json',import.meta.url),'utf8'));

test('alle fotokiezers krijgen ook video en 10 blijft gecombineerd',()=>{
  assert.match(builder,/video\\/mp4/);
  assert.match(builder,/video\\/webm/);
  assert.match(builder,/video\\/quicktime/);
  assert.match(builder,/machineparkPrepareMediaFile/);
  assert.match(builder,/machineparkIsVideoMedia/);
  assert.match(builder,/machineparkPersistMediaList/);
  assert.match(builder,/MAX_VIDEO_BYTES = 20 \\* 1024 \\* 1024/);
  assert.match(builder,/slice\\(0,10\\)/);
});

test('Synology media-opslag ondersteunt foto en video zonder nieuwe mapstructuur',()=>{
  assert.match(lib,/mp_photo_parse_data_media/);
  assert.match(lib,/video\\/mp4/);
  assert.match(lib,/video\\/webm/);
  assert.match(lib,/video\\/quicktime/);
  assert.match(lib,/mp_photo_ref_for_base/);
  assert.match(lib,/MP_PHOTO_ROOT/);
  for(const source of [device,service,action])assert.match(source,/10 foto’s en video’s samen/);
  assert.match(part,/mp_photo_parse_data_media/);
});

test('video blijft offline herkenbaar en toesteloverzicht gebruikt alleen echte fotos',()=>{
  assert.match(offline,/startsWith\\('data:video\\/'\\)/);
  assert.match(builder,/Een video kan niet als overzichtsfoto gebruikt worden/);
  assert.match(builder,/findIndex\\(src=>!window\\.machineparkIsVideoMedia/);
});

test('video builder draait na alle ToDo en dashboardlagen maar voor extractie',()=>{
  const cmd=pkg.scripts.build;
  assert.ok(cmd.indexOf('python3 build-video-media-support.py')>cmd.indexOf('python3 build-dashboard-kpi-navigation.py'));
  assert.ok(cmd.indexOf('python3 build-video-media-support.py')<cmd.indexOf('scripts/check-inline-scripts.py'));
});


test('service video uploadroute wordt op de echte servicefunctie geankerd',()=>{
  assert.match(builder,/window\.machineparkPersistServicePhotos = async function/);
  assert.match(builder,/service_start = index\.find\("window\.machineparkPersistServicePhotos = async function"\)/);
  assert.match(builder,/service-video uploadroute staat in toestelmediafunctie/);
  assert.match(builder,/service-video uploadroute ontbreekt/);
});


test('serviceconcepten behouden raw video en zichtbare labels noemen foto en video',()=>{
  assert.match(builder,/src\.startsWith\('data:video\/'\)/);
  assert.match(builder,/Foto’s \/ video’s/);
  assert.match(builder,/foto’s en video’s samen/);
});

test('PDF-fotolijsten slaan video volledig over',()=>{
  assert.match(builder,/model\.photos \|\| \[\]\)\.filter\(src=>!window\.machineparkIsVideoMedia/);
  assert.match(builder,/serviceModel\(context\)/);
});
