const fs = require('node:fs');
const path = require('node:path');
const Ajv = require('ajv');

const schema = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', '..', 'schema', 'edit-plan.schema.json'), 'utf8')
);

const ajv = new Ajv({allErrors: true});
const validateSchema = ajv.compile(schema);

function validateEditPlan(plan) {
  const errors = [];

  const schemaOk = validateSchema(plan);
  if (!schemaOk) {
    for (const err of validateSchema.errors) {
      errors.push(`${err.instancePath || '(корень)'} ${err.message}`);
    }
    return {valid: false, errors};
  }

  const scenes = plan.scenes;
  if (scenes[0].start !== 0) {
    errors.push(`Первая сцена должна начинаться с 0, а начинается с ${scenes[0].start}`);
  }
  for (let i = 0; i < scenes.length; i++) {
    const scene = scenes[i];
    if (scene.end <= scene.start) {
      errors.push(`Сцена ${i}: end (${scene.end}) должен быть больше start (${scene.start})`);
    }
    if (i > 0) {
      const prev = scenes[i - 1];
      if (Math.abs(scene.start - prev.end) > 1e-6) {
        errors.push(
          `Между сценой ${i - 1} (конец ${prev.end}) и сценой ${i} (начало ${scene.start}) есть разрыв или наложение`
        );
      }
    }
  }

  return {valid: errors.length === 0, errors};
}

module.exports = {validateEditPlan};
