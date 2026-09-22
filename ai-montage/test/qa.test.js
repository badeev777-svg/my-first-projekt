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

test('qa отказывает для версии с попыткой выхода за пределы папки проекта', async () => {
  const id = 'qa-test-' + Date.now();
  createProjectDirs(id, PROJECTS_ROOT);
  const dir = path.join(PROJECTS_ROOT, id);
  try {
    await assert.rejects(
      () => runQa({id, version: '../../secret'}),
      /Недопустимая версия/
    );
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});

test('qa сообщает понятную ошибку, если утверждённый бриф отсутствует', async () => {
  const id = 'qa-test-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);
  const clip = makeFixtureVideo({duration: 1});
  fs.copyFileSync(clip, path.join(dir, 'renders', 'v01.mp4'));
  try {
    await assert.rejects(
      () => runQa({id, version: 'v01'}),
      /Утверждённый бриф не найден/
    );
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});

test('qa не требует звуковую дорожку, если в плане нет сцен с audioMode sync', async () => {
  const id = 'qa-test-mute-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);

  const plan = {
    projectId: id, fps: 25, width: 320, height: 240,
    scenes: [{type: 'title-card', start: 0, end: 1, title: 'x', audioMode: 'mute'}],
  };
  fs.writeFileSync(path.join(dir, 'brief', 'v01-approved.json'), JSON.stringify(plan));

  const clip = makeFixtureVideo({duration: 1, withAudio: false});
  fs.copyFileSync(clip, path.join(dir, 'renders', 'v01.mp4'));

  try {
    const result = await runQa({id, version: 'v01'});
    assert.equal(result.passed, true);
    assert.ok(fs.existsSync(result.finalPath));
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});

test('qa по-прежнему требует звуковую дорожку, если есть сцена с audioMode sync', async () => {
  const id = 'qa-test-sync-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);

  const plan = {
    projectId: id, fps: 25, width: 320, height: 240,
    audioTrack: 'source.mp4',
    scenes: [{type: 'speaker', start: 0, end: 1, audioMode: 'sync', subtitle: 'x'}],
  };
  fs.writeFileSync(path.join(dir, 'brief', 'v01-approved.json'), JSON.stringify(plan));

  const clip = makeFixtureVideo({duration: 1, withAudio: false});
  fs.copyFileSync(clip, path.join(dir, 'renders', 'v01.mp4'));

  try {
    const result = await runQa({id, version: 'v01'});
    assert.equal(result.passed, false);
    assert.ok(result.problems.some((p) => p.includes('звуковой дорожки')));
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});

test('qa отказывает, если итоговый файл уже существует', async () => {
  const id = 'qa-test-final-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);

  const plan = {
    projectId: id, fps: 25, width: 320, height: 240,
    scenes: [{type: 'title-card', start: 0, end: 1, title: 'x', audioMode: 'mute'}],
  };
  fs.writeFileSync(path.join(dir, 'brief', 'v01-approved.json'), JSON.stringify(plan));

  const clip = makeFixtureVideo({duration: 1});
  fs.copyFileSync(clip, path.join(dir, 'renders', 'v01.mp4'));
  fs.writeFileSync(path.join(dir, 'final', `${id}.mp4`), 'existing');

  try {
    await assert.rejects(
      () => runQa({id, version: 'v01'}),
      /уже существует/
    );
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});

test('qa отклоняет рендер с неверным fps', async () => {
  const id = 'qa-test-fps-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);

  const plan = {
    projectId: id, fps: 60, width: 320, height: 240,
    scenes: [{type: 'title-card', start: 0, end: 1, title: 'x', audioMode: 'mute'}],
  };
  fs.writeFileSync(path.join(dir, 'brief', 'v01-approved.json'), JSON.stringify(plan));

  const clip = makeFixtureVideo({duration: 1});
  fs.copyFileSync(clip, path.join(dir, 'renders', 'v01.mp4'));

  try {
    const result = await runQa({id, version: 'v01'});
    assert.equal(result.passed, false);
    assert.ok(result.problems.some((p) => p.includes('fps') || p.includes('кадр')));
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});

test('qa отклоняет рендер с неверным разрешением', async () => {
  const id = 'qa-test-res-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);

  const plan = {
    projectId: id, fps: 25, width: 1080, height: 1920,
    scenes: [{type: 'title-card', start: 0, end: 1, title: 'x', audioMode: 'mute'}],
  };
  fs.writeFileSync(path.join(dir, 'brief', 'v01-approved.json'), JSON.stringify(plan));

  const clip = makeFixtureVideo({duration: 1});
  fs.copyFileSync(clip, path.join(dir, 'renders', 'v01.mp4'));

  try {
    const result = await runQa({id, version: 'v01'});
    assert.equal(result.passed, false);
    assert.ok(result.problems.some((p) => p.includes('разрешение') || p.includes('320') || p.includes('1080')));
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});

test('qa пропускает корректный рендер и создаёт final', async () => {
  const id = 'qa-test-ok-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);

  const plan = {
    projectId: id, fps: 25, width: 320, height: 240,
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
