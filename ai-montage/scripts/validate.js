const fs = require('node:fs');
const {validateEditPlan} = require('./lib/validate-edit-plan');

function runValidate(args) {
  const {id, file} = args;
  if (!id || !file) {
    throw new Error('Использование: validate --id <projectId> --file <путь к брифу>');
  }
  const plan = JSON.parse(fs.readFileSync(file, 'utf8'));
  const result = validateEditPlan(plan);
  if (!result.valid) {
    console.error('Монтажный лист не прошёл проверку:');
    for (const e of result.errors) console.error(`  - ${e}`);
    process.exitCode = 1;
    return result;
  }
  console.log(`Монтажный лист ${file} корректен.`);
  return result;
}

module.exports = {runValidate};
