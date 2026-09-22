const test = require('node:test');
const assert = require('node:assert/strict');
const {calculateDurationInFrames} = require('../remotion/src/calculateDuration');

test('считает длительность по последней сцене', () => {
  const scenes = [
    {start: 0, end: 2},
    {start: 2, end: 5.5},
  ];
  assert.equal(calculateDurationInFrames(scenes, 30), 165);
});

test('возвращает 1 секунду для пустого списка сцен', () => {
  assert.equal(calculateDurationInFrames([], 30), 30);
});
