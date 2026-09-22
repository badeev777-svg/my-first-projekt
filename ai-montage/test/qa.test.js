const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {runQa} = require('../scripts/qa');
const {createProjectDirs, PROJECTS_ROOT} = require('../scripts/lib/project-paths');
const {makeFixtureVideo} = require('./helpers/fixture-video');

test('qa отклоняет рендер с длительностью, не совпадающей с планом, и не создаёт final', async () => {
  const id = 'qa-test-' + Date.now();
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
    const result = await runQa({id, version: 'v01'});
    assert.equal(result.passed, false);
    assert.ok(result.problems.some((p) => p.includes('Длительность')));
    assert.ok(!fs.existsSync(path.join(dir, 'final', `${id}.mp4`)));
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});

test('qa пропускает корректный рендер и создаёт final', async () => {
  const id = 'qa-test-ok-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);

  const plan = {
    projectId: id, fps: 30, width: 320, height: 568,
    audioTrack: 'source.mp4',
    scenes: [{type: 'title-card', start: 0, end: 1, title: 'x', audioMode: 'mute'}],
  };
  fs.writeFileSync(path.join(dir, 'brief', 'v01-approved.json'), JSON.stringify(plan));

  const clip = makeFixtureVideo({duration: 1});
  fs.copyFileSync(clip, path.join(dir, 'renders', 'v01.mp4'));

  try {
    const result = await runQa({id, version: 'v01'});
    assert.equal(result.passed, true);
    assert.ok(fs.existsSync(result.finalPath));
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});
