const fs = require('node:fs');
const path = require('node:path');

const PROJECTS_ROOT = path.join(__dirname, '..', '..', 'projects');
const PUBLIC_PROJECTS_ROOT = path.join(__dirname, '..', '..', 'remotion', 'public', 'projects');

const SUBDIRS = ['input', 'transcript', 'brief', 'assets', 'previews', 'renders', 'final'];

function getProjectDir(id, projectsRoot = PROJECTS_ROOT) {
  return path.join(projectsRoot, id);
}

function getPublicProjectDir(id, publicRoot = PUBLIC_PROJECTS_ROOT) {
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
};
