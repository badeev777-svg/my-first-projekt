const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {runNewProject} = require('../scripts/new-project');
const {getPublicProjectDir} = require('../scripts/lib/project-paths');
const {makeFixtureVideo} = require('./helpers/fixture-video');

test('runNewProject создаёт проект и паспорт исходника', async () => {
  const fixture = makeFixtureVideo({duration: 1});
  const id = 'test-' + Date.now();
  const result = await runNewProject({id, input: fixture});
  try {
    assert.ok(fs.existsSync(require('node:path').join(result.dir, 'input', 'passport.json')));
    assert.ok(Number(result.passport.format.duration) > 0);
    assert.ok(fs.existsSync(require('node:path').join(result.dir, 'input', result.sourceFileName)));
  } finally {
    fs.rmSync(result.dir, {recursive: true, force: true});
    fs.rmSync(getPublicProjectDir(id), {recursive: true, force: true});
  }
});

test('runNewProject требует и --id, и --input', async () => {
  await assert.rejects(() => runNewProject({id: 'only-id'}), /Использование/);
});
