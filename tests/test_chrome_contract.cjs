// Exercise shipped client functions with plain element stubs, without a network
// or browser extension install. Financial results remain owned by the core.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..', 'chrome-extension');

function functionSource(file, start, end) {
  const source = fs.readFileSync(path.join(root, file), 'utf8');
  return source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
}

for (const file of ['popup.js', 'content.js']) {
  const source = functionSource(file, 'function normalizeScorePayload(', file === 'popup.js' ? 'function renderResult(' : '// 显示结果');
  const normalize = vm.runInNewContext(`${source}; normalizeScorePayload`);
  for (const score of [null, 88.7]) {
    const out = normalize({ report: {
      display: score, overall: score, path_risk: score === null ? null : 0.7,
      pillars: { Credibility: { value: score }, 'Return quality': { value: score } },
      meta: { core_version: '0.4.0', n_trials: null, dsr: null },
    } }, 'en');
    assert.equal(out.display, score);
    assert.equal(out.meta.core_version, '0.4.0');
    assert.equal(out.pillars['Path risk'].value, score === null ? null : 0.7);
    assert.equal(out.meta.n_trials, null);
    assert.equal(out.pillars['Overfit risk'], undefined);
  }
}

const elements = {};
const getElement = id => elements[id] || (elements[id] = { textContent: '', innerHTML: '' });
const context = {
  document: { getElementById: getElement }, langInput: { value: 'en' },
  localizedGrade: x => x, localizedPillarName: x => x, localizedEdge: x => x,
  escapeHtml: String, uiCopy: () => ({}), searchNote: () => 'Search trials: unknown',
  renderDiagnosticDetails: () => '', renderSmartCTA: () => '',
};
const renderSource = functionSource('popup.js', 'function renderResult(', 'function renderSmartCTA(');
const render = vm.runInNewContext(`${renderSource}; renderResult`, context);
render({ display: null, overall: null, grade: 'PROVISIONAL', pillars: { 'Path risk': { value: null } }, meta: { core_version: '0.4.0' } });
assert.equal(elements['score-number'].textContent, 'N/A');
assert.match(elements['pillar-list'].innerHTML, />N\/A<\/div>/);
assert.match(elements['meta-line'].textContent, /core 0.4.0.*unknown/);
render({ display: 88.7, grade: 'GOLD', pillars: { 'Path risk': { value: 0.7 } }, meta: { core_version: '0.4.0' } });
assert.equal(elements['score-number'].textContent, '88.7');
console.log('Chrome score contract: both payload adapters and nullable popup rendering passed.');
