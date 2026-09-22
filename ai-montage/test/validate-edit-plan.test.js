const test = require('node:test');
const assert = require('node:assert/strict');
const {validateEditPlan} = require('../scripts/lib/validate-edit-plan');

const validPlan = {
  projectId: 'demo-01',
  fps: 30,
  width: 1080,
  height: 1920,
  audioTrack: 'source.mp4',
  scenes: [
    {type: 'speaker', start: 0, end: 2, audioMode: 'sync'},
    {type: 'title-card', start: 2, end: 4, title: 'Привет', audioMode: 'mute'},
    {type: 'b-roll', start: 4, end: 6, media: 'source.mp4', audioMode: 'mute'},
  ],
};

test('валидный план проходит проверку', () => {
  const result = validateEditPlan(validPlan);
  assert.equal(result.valid, true);
  assert.deepEqual(result.errors, []);
});

test('план с разрывом между сценами отклоняется', () => {
  const plan = JSON.parse(JSON.stringify(validPlan));
  plan.scenes[1].start = 2.5;
  const result = validateEditPlan(plan);
  assert.equal(result.valid, false);
  assert.ok(result.errors.some((e) => e.includes('разрыв')));
});

test('title-card без title отклоняется schema', () => {
  const plan = JSON.parse(JSON.stringify(validPlan));
  delete plan.scenes[1].title;
  const result = validateEditPlan(plan);
  assert.equal(result.valid, false);
});

test('неизвестный тип сцены отклоняется', () => {
  const plan = JSON.parse(JSON.stringify(validPlan));
  plan.scenes[0].type = 'unknown-type';
  const result = validateEditPlan(plan);
  assert.equal(result.valid, false);
});

test('сцены не по порядку (вторая сцена стартует раньше первой) отклоняются', () => {
  const plan = JSON.parse(JSON.stringify(validPlan));
  plan.scenes = [plan.scenes[1], plan.scenes[0], plan.scenes[2]];
  const result = validateEditPlan(plan);
  assert.equal(result.valid, false);
});
