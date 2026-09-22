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
