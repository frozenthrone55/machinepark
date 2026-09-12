import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const testsDir = path.resolve('tests');

test('geen regressietest verwijst nog naar versie 1.68.9', () => {
  const matches = fs.readdirSync(testsDir)
    .filter((name) => name.endsWith('.test.mjs') && name !== '000-version-scan.test.mjs')
    .filter((name) => fs.readFileSync(path.join(testsDir, name), 'utf8').includes('1.68.9'))
    .sort();
  console.log('MACHINEPARK_LEGACY_VERSION_TESTS=' + JSON.stringify(matches));
  assert.deepEqual(matches, []);
});
