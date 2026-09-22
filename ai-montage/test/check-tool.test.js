const test = require('node:test');
const assert = require('node:assert/strict');
const {checkTool} = require('../scripts/lib/check-tool');

test('существующая команда node определяется как доступная', () => {
  const result = checkTool('node', ['--version']);
  assert.equal(result.ok, true);
  assert.match(result.version, /^v?\d+\.\d+\.\d+/);
});

test('несуществующая команда определяется как недоступная', () => {
  const result = checkTool('definitely-not-a-real-command-xyz', ['--version']);
  assert.equal(result.ok, false);
  assert.equal(result.version, null);
});
