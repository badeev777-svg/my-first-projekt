const test = require('node:test');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const {createProjectDirs, PROJECTS_ROOT} = require('../scripts/lib/project-paths');
const {makeFixtureVideo} = require('./helpers/fixture-video');

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

test('qa через CLI завершается с кодом 1, если QA не пройдена', () => {
  const id = 'cli-qa-fail-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);
  const plan = {
    projectId: id, fps: 30, width: 320, height: 568,
    audioTrack: 'source.mp4',
    scenes: [{type: 'title-card', start: 0, end: 5, title: 'x', audioMode: 'mute'}],
  };
  fs.writeFileSync(path.join(dir, 'brief', 'v01-approved.json'), JSON.stringify(plan));
  const shortClip = makeFixtureVideo({duration: 1});
  fs.copyFileSync(shortClip, path.join(dir, 'renders', 'v01.mp4'));

  try {
    const result = spawnSync('node', [cliPath, 'qa', '--id', id, '--version', 'v01'], {encoding: 'utf8'});
    assert.equal(result.status, 1);
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});
