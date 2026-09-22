const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {runRender} = require('../scripts/render');
const {createProjectDirs, PROJECTS_ROOT} = require('../scripts/lib/project-paths');

test('render отказывает без утверждённого брифа', async () => {
  const id = 'render-test-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);
  try {
    await assert.rejects(() => runRender({id, version: 'v01'}), /не найден/);
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});

test('render отказывает для версии с попыткой выхода за пределы папки проекта', async () => {
  const id = 'render-test-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);
  try {
    await assert.rejects(
      () => runRender({id, version: '../../secret'}),
      /Недопустимая версия/
    );
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});

test('render отказывает, если рендер этой версии уже существует', async () => {
  const path = require('node:path');
  const id = 'render-test-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);
  const plan = {
    projectId: id, fps: 25, width: 320, height: 240, audioTrack: 'source.mp4',
    scenes: [{type: 'title-card', start: 0, end: 1, title: 'x', audioMode: 'mute'}],
  };
  fs.writeFileSync(path.join(dir, 'brief', 'v01-approved.json'), JSON.stringify(plan));
  fs.writeFileSync(path.join(dir, 'renders', 'v01.mp4'), 'existing');
  try {
    await assert.rejects(
      () => runRender({id, version: 'v01'}),
      /уже существует/
    );
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});
