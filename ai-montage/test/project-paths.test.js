const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {createProjectDirs, ensureProjectExists} = require('../scripts/lib/project-paths');

function makeTempRoot() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'ai-montage-test-'));
}

test('createProjectDirs создаёт все подпапки проекта', () => {
  const root = makeTempRoot();
  const publicRoot = makeTempRoot();
  const dir = createProjectDirs('demo-01', root, publicRoot);
  for (const sub of ['input', 'transcript', 'brief', 'assets', 'previews', 'renders', 'final']) {
    assert.ok(fs.existsSync(path.join(dir, sub)), `подпапка ${sub} должна существовать`);
  }
  assert.ok(fs.existsSync(path.join(publicRoot, 'demo-01')));
});

test('createProjectDirs отказывает, если проект уже существует', () => {
  const root = makeTempRoot();
  const publicRoot = makeTempRoot();
  createProjectDirs('demo-01', root, publicRoot);
  assert.throws(() => createProjectDirs('demo-01', root, publicRoot), /уже существует/);
});

test('ensureProjectExists бросает понятную ошибку для несуществующего проекта', () => {
  const root = makeTempRoot();
  assert.throws(() => ensureProjectExists('no-such-project', root), /не найден/);
});
