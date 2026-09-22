const fs = require('node:fs');
const path = require('node:path');
const {ensureProjectExists} = require('./lib/project-paths');
const {validateEditPlan} = require('./lib/validate-edit-plan');

async function runApprove(args) {
  const {id, version} = args;
  if (!id || !version) {
    throw new Error('Использование: approve --id <projectId> --version <v01>');
  }
  const dir = ensureProjectExists(id);
  const briefPath = path.join(dir, 'brief', `${version}.json`);
  if (!fs.existsSync(briefPath)) {
    throw new Error(`Файл брифа не найден: ${briefPath}`);
  }
  const plan = JSON.parse(fs.readFileSync(briefPath, 'utf8'));
  const check = validateEditPlan(plan);
  if (!check.valid) {
    throw new Error('Нельзя утвердить некорректный бриф:\n' + check.errors.map((e) => `  - ${e}`).join('\n'));
  }

  const approvedPath = path.join(dir, 'brief', `${version}-approved.json`);
  if (fs.existsSync(approvedPath)) {
    throw new Error(`Версия ${version} уже утверждена: ${approvedPath}. Создайте новую версию брифа.`);
  }
  fs.copyFileSync(briefPath, approvedPath);
  console.log(`Версия ${version} утверждена: ${approvedPath}`);
  return {approvedPath};
}

module.exports = {runApprove};
