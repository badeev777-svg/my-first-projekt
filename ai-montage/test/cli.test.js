const test = require('node:test');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const path = require('node:path');

const cliPath = path.join(__dirname, '..', 'scripts', 'cli.js');

test('запуск без команды печатает помощь и завершается с кодом 1', () => {
  const result = spawnSync('node', [cliPath], {encoding: 'utf8'});
  assert.equal(result.status, 1);
  assert.match(result.stdout, /Использование/);
});

test('неизвестная команда печатает ошибку и завершается с кодом 1', () => {
  const result = spawnSync('node', [cliPath, 'not-a-real-command'], {encoding: 'utf8'});
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Неизвестная команда/);
});

const {parseArgs} = require('../scripts/cli.js');

test('parseArgs разбирает пары --flag value', () => {
  const args = parseArgs(['--id', 'demo-01', '--file', 'brief.json']);
  assert.deepEqual(args, {id: 'demo-01', file: 'brief.json'});
});
