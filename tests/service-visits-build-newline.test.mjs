import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-service-visits.py', import.meta.url), 'utf8');

test('servicebezoek-build schrijft echte regeleinden en geen zichtbare \\n-tekst', () => {
  assert.doesNotMatch(build, />\\\\n<\/head>/);
  assert.doesNotMatch(build, /<\/script>\\\\n<\/body>/);
  assert.doesNotMatch(build, /service_js_url\}',\\\\n/);
  assert.match(build, /service_css_url\}" \{MARKER\}>\\n<\/head>/);
  assert.match(build, /service_js_url\}" \{MARKER\}><\/script>\\n<\/body>/);
});
