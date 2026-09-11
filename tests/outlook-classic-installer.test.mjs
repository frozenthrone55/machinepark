import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const setup = readFileSync(new URL('../machinepark-outlook-classic-setup.cmd', import.meta.url), 'utf8');

test('Outlook Classic installer vindt alleen de echte PowerShell payload-marker', () => {
  assert.ok(
    setup.includes('machinepark-outlook-installer-loader-v2'),
    'Veilige Outlook installer-loader ontbreekt'
  );
  assert.ok(
    setup.includes("[regex]::Match($raw,'(?m)^###MACHINEPARK_POWERSHELL###\\r?$')"),
    'Payload-marker wordt niet als aparte regel gezocht'
  );
  assert.ok(
    !setup.includes("$mark='###MACHINEPARK_POWERSHELL###'; $pos=$raw.IndexOf($mark)"),
    'Oude foutgevoelige IndexOf-loader is nog aanwezig'
  );

  const delimiterLines = setup
    .split(/\r?\n/)
    .filter((line) => line === '###MACHINEPARK_POWERSHELL###');
  assert.equal(delimiterLines.length, 1, 'Er moet exact één echte payload-markerregel zijn');
});
