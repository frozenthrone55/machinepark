import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const setup = readFileSync(new URL('../machinepark-outlook-classic-setup.cmd', import.meta.url), 'utf8');

test('Outlook Classic installer voert de ingebedde PowerShell veilig als tijdelijk script uit', () => {
  assert.ok(
    setup.includes('machinepark-outlook-installer-temp-ps1-v3'),
    'Veilige tijdelijke PowerShell-loader ontbreekt'
  );
  assert.ok(
    setup.includes("[regex]::Match($raw,'(?m)^###MACHINEPARK_POWERSHELL###\\r?$')"),
    'Payload-marker wordt niet als aparte regel gezocht'
  );
  assert.ok(
    setup.includes('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%MP_PS1%"'),
    'Uitgepakte PowerShell wordt niet via -File uitgevoerd'
  );
  assert.ok(
    setup.includes('[IO.File]::WriteAllText($env:MP_PS1,$payload,(New-Object Text.UTF8Encoding($false)))'),
    'PowerShell payload wordt niet veilig naar het tijdelijke script geschreven'
  );
  assert.ok(!setup.includes('Invoke-Expression $payload'), 'Invoke-Expression mag niet meer in de installer staan');
  assert.ok(
    !setup.includes("$mark='###MACHINEPARK_POWERSHELL###'; $pos=$raw.IndexOf($mark)"),
    'Oude foutgevoelige IndexOf-loader is nog aanwezig'
  );

  const delimiterLines = setup
    .split(/\r?\n/)
    .filter((line) => line === '###MACHINEPARK_POWERSHELL###');
  assert.equal(delimiterLines.length, 1, 'Er moet exact één echte payload-markerregel zijn');
});
