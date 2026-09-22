const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {runApprove} = require('../scripts/approve');
const {createProjectDirs, PROJECTS_ROOT} = require('../scripts/lib/project-paths');

const validPlan = {
  projectId: 'approve-test',
  fps: 30, width: 1080, height: 1920,
  audioTrack: 'source.mp4',
  scenes: [{type: 'title-card', start: 0, end: 1, title: 'x', audioMode: 'mute'}],
};

test('approve создаёт -approved.json для валидного брифа', async () => {
  const id = 'approve-test-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);
  fs.writeFileSync(path.join(dir, 'brief', 'v01.json'), JSON.stringify(validPlan));
  try {
    const result = await runApprove({id, version: 'v01'});
    assert.ok(fs.existsSync(result.approvedPath));
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});

test('approve отказывает при повторном утверждении той же версии', async () => {
  const id = 'approve-test-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);
  fs.writeFileSync(path.join(dir, 'brief', 'v01.json'), JSON.stringify(validPlan));
  try {
    await runApprove({id, version: 'v01'});
    await assert.rejects(() => runApprove({id, version: 'v01'}), /уже утверждена/);
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});

test('approve отказывает для невалидного брифа', async () => {
  const id = 'approve-test-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);
  const badPlan = JSON.parse(JSON.stringify(validPlan));
  delete badPlan.scenes[0].title;
  fs.writeFileSync(path.join(dir, 'brief', 'v01.json'), JSON.stringify(badPlan));
  try {
    await assert.rejects(() => runApprove({id, version: 'v01'}), /некорректный бриф/);
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
});
