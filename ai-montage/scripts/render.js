const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {ensureProjectExists} = require('./lib/project-paths');
const {validateEditPlan} = require('./lib/validate-edit-plan');

const REPO_ROOT = path.join(__dirname, '..');

async function runRender(args) {
  const {id, version} = args;
  if (!id || !version) {
    throw new Error('Использование: render --id <projectId> --version <v01>');
  }
  const dir = ensureProjectExists(id);
  const approvedPath = path.join(dir, 'brief', `${version}-approved.json`);
  if (!fs.existsSync(approvedPath)) {
    throw new Error(
      `Утверждённый бриф не найден: ${approvedPath}. Сначала выполните: approve --id ${id} --version ${version}`
    );
  }
  const plan = JSON.parse(fs.readFileSync(approvedPath, 'utf8'));
  const check = validateEditPlan(plan);
  if (!check.valid) {
    throw new Error('Утверждённый бриф стал некорректным:\n' + check.errors.map((e) => `  - ${e}`).join('\n'));
  }

  const outPath = path.join(dir, 'renders', `${version}.mp4`);
  const result = spawnSync(
    'npx',
    ['remotion', 'render', 'remotion/src/index.jsx', 'EditPlan', outPath, `--props=${approvedPath}`],
    {cwd: REPO_ROOT, encoding: 'utf8', shell: true}
  );
  if (result.status !== 0) {
    throw new Error(`Ошибка Remotion при финальном рендере: ${result.stderr}`);
  }
  console.log(`Рендер готов: ${outPath}`);
  return {outPath, plan};
}

module.exports = {runRender};
