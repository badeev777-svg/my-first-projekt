const fs = require('node:fs');
const path = require('node:path');

const PROJECTS_ROOT = path.join(__dirname, '..', '..', 'projects');
const PUBLIC_PROJECTS_ROOT = path.join(__dirname, '..', '..', 'remotion', 'public', 'projects');

const SUBDIRS = ['input', 'transcript', 'brief', 'assets', 'previews', 'renders', 'final'];

const SAFE_ID_PATTERN = /^[A-Za-z0-9_-]+$/;

function assertSafeId(id) {
  if (typeof id !== 'string' || !SAFE_ID_PATTERN.test(id)) {
    throw new Error(`Недопустимый id проекта: "${id}". Разрешены только буквы, цифры, "-" и "_".`);
  }
}

function assertSafeVersion(version) {
  if (typeof version !== 'string' || !SAFE_ID_PATTERN.test(version)) {
    throw new Error(`Недопустимая версия: "${version}". Разрешены только буквы, цифры, "-" и "_".`);
  }
}

function getProjectDir(id, projectsRoot = PROJECTS_ROOT) {
  assertSafeId(id);
  return path.join(projectsRoot, id);
}

function getPublicProjectDir(id, publicRoot = PUBLIC_PROJECTS_ROOT) {
  assertSafeId(id);
  return path.join(publicRoot, id);
}

function ensureProjectExists(id, projectsRoot = PROJECTS_ROOT) {
  const dir = getProjectDir(id, projectsRoot);
  if (!fs.existsSync(dir)) {
    throw new Error(
      `Проект "${id}" не найден в папке projects/. Сначала выполните: new-project --id ${id} --input <путь к видео>`
    );
  }
  return dir;
}

function createProjectDirs(id, projectsRoot = PROJECTS_ROOT, publicRoot = PUBLIC_PROJECTS_ROOT) {
  const dir = getProjectDir(id, projectsRoot);
  if (fs.existsSync(dir)) {
    throw new Error(`Проект "${id}" уже существует: ${dir}`);
  }
  for (const sub of SUBDIRS) {
    fs.mkdirSync(path.join(dir, sub), {recursive: true});
  }
  fs.mkdirSync(getPublicProjectDir(id, publicRoot), {recursive: true});
  return dir;
}

module.exports = {
  PROJECTS_ROOT,
  PUBLIC_PROJECTS_ROOT,
  getProjectDir,
  getPublicProjectDir,
  ensureProjectExists,
  createProjectDirs,
  assertSafeVersion,
};
