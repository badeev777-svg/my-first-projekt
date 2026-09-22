const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {createProjectDirs, getPublicProjectDir} = require('./lib/project-paths');

function probeMedia(filePath) {
  const result = spawnSync(
    'ffprobe',
    ['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filePath],
    {encoding: 'utf8'}
  );
  if (result.status !== 0) {
    throw new Error(`ffprobe не смог прочитать файл ${filePath}: ${result.stderr}`);
  }
  return JSON.parse(result.stdout);
}

async function runNewProject(args) {
  const {id, input} = args;
  if (!id || !input) {
    throw new Error('Использование: new-project --id <projectId> --input <путь к видео>');
  }
  if (!fs.existsSync(input)) {
    throw new Error(`Исходный файл не найден: ${input}`);
  }

  const dir = createProjectDirs(id);
  const ext = path.extname(input);
  const destName = `source${ext}`;
  const destPath = path.join(dir, 'input', destName);
  fs.copyFileSync(input, destPath);

  const passport = probeMedia(destPath);
  fs.writeFileSync(path.join(dir, 'input', 'passport.json'), JSON.stringify(passport, null, 2));

  const publicDir = getPublicProjectDir(id);
  fs.copyFileSync(destPath, path.join(publicDir, destName));

  console.log(`Проект "${id}" создан: ${dir}`);
  console.log(`Исходник: ${destName}, длительность ${passport.format.duration} c`);
  return {dir, passport, sourceFileName: destName};
}

module.exports = {runNewProject, probeMedia};
