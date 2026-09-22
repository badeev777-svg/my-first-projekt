const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {ensureProjectExists} = require('./lib/project-paths');
const {validateEditPlan} = require('./lib/validate-edit-plan');

const REPO_ROOT = path.join(__dirname, '..');

async function runPreview(args) {
  const {id, brief} = args;
  if (!id || !brief) {
    throw new Error('Использование: preview --id <projectId> --brief <путь к брифу>');
  }
  const dir = ensureProjectExists(id);
  const plan = JSON.parse(fs.readFileSync(brief, 'utf8'));
  const check = validateEditPlan(plan);
  if (!check.valid) {
    throw new Error('Монтажный лист некорректен:\n' + check.errors.map((e) => `  - ${e}`).join('\n'));
  }

  const briefName = path.basename(brief, '.json');
  const outPath = path.join(dir, 'previews', `${briefName}-preview.mp4`);

  const result = spawnSync(
    'npx',
    ['remotion', 'render', 'remotion/src/index.jsx', 'EditPlan', outPath, `--props=${brief}`, '--scale=0.5'],
    {cwd: REPO_ROOT, encoding: 'utf8', shell: true}
  );
  if (result.status !== 0) {
    throw new Error(`Ошибка Remotion при сборке preview: ${result.stderr}`);
  }
  console.log(`Preview собран: ${outPath}`);
  return {outPath};
}

module.exports = {runPreview};
