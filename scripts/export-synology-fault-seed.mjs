import { writeFile } from 'node:fs/promises';
import { LATTIZ2_FAULT_SEED_2026_09_02 } from '../netlify/functions/_shared/lattiz2-fault-seed.mjs';

if (!Array.isArray(LATTIZ2_FAULT_SEED_2026_09_02) || LATTIZ2_FAULT_SEED_2026_09_02.length !== 191) {
  throw new Error('De ingebouwde Lattiz 2 storingsdataset is onvolledig.');
}

const payload = {
  version: 1,
  source: 'lattiz2-fault-seed-2026-09-02',
  generatedAt: new Date().toISOString(),
  faults: LATTIZ2_FAULT_SEED_2026_09_02,
};

await writeFile(
  new URL('../synology/fault-seed.json', import.meta.url),
  JSON.stringify(payload, null, 2) + '\n',
  'utf8',
);

console.log('[Machinepark] ' + payload.faults.length + ' storingen klaargezet voor lokale Synology-initialisatie');
