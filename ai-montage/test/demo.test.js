const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {runDemo} = require('../scripts/demo');
const {getProjectDir, getPublicProjectDir} = require('../scripts/lib/project-paths');

test('полный demo-пайплайн собирает и проверяет итоговый MP4', {timeout: 600000}, async () => {
  const dir = getProjectDir('demo-01');
  const publicDir = getPublicProjectDir('demo-01');
  if (fs.existsSync(dir)) fs.rmSync(dir, {recursive: true, force: true});
  if (fs.existsSync(publicDir)) fs.rmSync(publicDir, {recursive: true, force: true});

  try {
    const result = await runDemo();
    assert.equal(result.passed, true);
    assert.ok(fs.existsSync(result.finalPath));
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
    fs.rmSync(publicDir, {recursive: true, force: true});
  }
});
