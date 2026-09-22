const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {runDemo} = require('../scripts/demo');
const {getProjectDir, getPublicProjectDir} = require('../scripts/lib/project-paths');

test('полный demo-пайплайн собирает и проверяет итоговый MP4', {timeout: 600000}, async () => {
  const id = 'demo-test-' + Date.now();
  const dir = getProjectDir(id);
  const publicDir = getPublicProjectDir(id);
  const realDemoDir = getProjectDir('demo-01');
  const realDemoSnapshot = fs.existsSync(realDemoDir);

  try {
    const result = await runDemo(id);
    assert.equal(result.passed, true);
    assert.ok(fs.existsSync(result.finalPath));
    assert.equal(
      fs.existsSync(realDemoDir), realDemoSnapshot,
      'demo.test.js не должен трогать реальный проект demo-01'
    );
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
    fs.rmSync(publicDir, {recursive: true, force: true});
  }
});
