const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {runPreview} = require('../scripts/preview');
const {createProjectDirs, PROJECTS_ROOT} = require('../scripts/lib/project-paths');

test('preview отказывает для невалидного брифа, не запуская рендер', async () => {
  const id = 'preview-test-' + Date.now();
  const dir = createProjectDirs(id, PROJECTS_ROOT);
  const briefPath = path.join(os.tmpdir(), `bad-brief-${id}.json`);
  const badPlan = {
    projectId: id, fps: 30, width: 1080, height: 1920,
    audioTrack: 'source.mp4',
    scenes: [{type: 'title-card', start: 0, end: 1, audioMode: 'mute'}],
  };
  fs.writeFileSync(briefPath, JSON.stringify(badPlan));
  try {
    await assert.rejects(() => runPreview({id, brief: briefPath}), /некорректен/);
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
    fs.rmSync(briefPath, {force: true});
  }
});
