const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {makeFixtureVideo} = require('./helpers/fixture-video');

const REPO_ROOT = path.join(__dirname, '..');

test('remotion render собирает mp4 из тестового edit-плана', {timeout: 180000}, () => {
  const projectId = 'render-smoke-' + Date.now();
  const publicDir = path.join(REPO_ROOT, 'remotion', 'public', 'projects', projectId);
  fs.mkdirSync(publicDir, {recursive: true});

  const fixture = makeFixtureVideo({duration: 3});
  fs.copyFileSync(fixture, path.join(publicDir, 'source.mp4'));

  const plan = {
    projectId,
    fps: 30,
    width: 320,
    height: 568,
    audioTrack: 'source.mp4',
    scenes: [
      {type: 'speaker', start: 0, end: 1, audioMode: 'sync', subtitle: 'Привет'},
      {type: 'title-card', start: 1, end: 2, title: 'Заголовок', audioMode: 'mute'},
      {type: 'b-roll', start: 2, end: 3, media: 'source.mp4', audioMode: 'mute'},
    ],
  };

  const propsPath = path.join(os.tmpdir(), `props-${projectId}.json`);
  fs.writeFileSync(propsPath, JSON.stringify(plan));
  const outPath = path.join(os.tmpdir(), `${projectId}.mp4`);

  const result = spawnSync(
    'npx',
    ['remotion', 'render', 'remotion/src/index.jsx', 'EditPlan', outPath, `--props=${propsPath}`],
    {cwd: REPO_ROOT, encoding: 'utf8', shell: true}
  );

  try {
    assert.equal(result.status, 0, result.stderr || result.stdout);
    assert.ok(fs.existsSync(outPath));
    assert.ok(fs.statSync(outPath).size > 0);
  } finally {
    fs.rmSync(publicDir, {recursive: true, force: true});
    fs.rmSync(propsPath, {force: true});
    fs.rmSync(outPath, {force: true});
  }
});
