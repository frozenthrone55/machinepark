import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const stateMachine = readFileSync(new URL('../build-service-todo-state-machine.py', import.meta.url), 'utf8');
const repeatCycle = readFileSync(new URL('../build-service-todo-repeat-cycle.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

const build = pkg.scripts.build;

test('servicewerkzaamheden blijven de bron van waarheid voor ToDo-status', () => {
  assert.match(stateMachine, /function serviceWorkStateFromRecords\(records\)/);
  assert.match(stateMachine, /window\.machineparkServiceReportWorkState=serviceWorkStateForReport/);
  assert.match(stateMachine, /records:result\.finals\|\|\[\]/);
  assert.match(stateMachine, /item\.serviceReportStatus=reportStatus/);
  assert.match(stateMachine, /item\.serviceVisitStatus=visitStatus/);
});

test('automatische service-ToDo koppeling blijft over onbeperkte open-afgewerkt cycli actief', () => {
  assert.match(repeatCycle, /machinepark-service-todo-repeat-cycle-v2/);
  assert.match(repeatCycle, /serviceAutoManagedReportIds/);
  assert.match(repeatCycle, /serviceAutomation:true/);
  assert.match(repeatCycle, /Servicestatus automatisch gevolgd/);
  assert.match(repeatCycle, /serviceActionLinkedWorkState/);
  assert.match(repeatCycle, /persistServiceManagedActionState/);
  assert.match(repeatCycle, /if "if\(entry\.type==='reopened'\)return false;" in index:/);
  assert.match(repeatCycle, /oude eenmalige service\/ToDo-historyheuristiek is nog actief/);
});

test('meerdere gekoppelde serviceverslagen worden samen beoordeeld', () => {
  assert.match(repeatCycle, /const ids=typeof actionServiceIds==='function'\?actionServiceIds\(item\):\[\]/);
  assert.match(repeatCycle, /states\.some\(state=>state==='in_progress'\)/);
  assert.match(repeatCycle, /states\.some\(state=>state==='open'\)/);
  assert.match(repeatCycle, /return 'done'/);
});

test('state-machine en herhaalcyclus staan in veilige buildvolgorde', () => {
  const stateAt = build.indexOf('python3 build-service-todo-state-machine.py');
  const repeatAt = build.indexOf('python3 build-service-todo-repeat-cycle.py');
  const timelineAt = build.indexOf('python3 build-action-machine-timeline.py');
  assert.ok(stateAt >= 0, 'service state-machine ontbreekt uit build');
  assert.ok(repeatAt > stateAt, 'herhaalcyclus moet na state-machine draaien');
  assert.ok(timelineAt > repeatAt, 'timeline moet na service/ToDo synchronisatiepatches draaien');
});
