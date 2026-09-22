const test = require('node:test');
const assert = require('node:assert/strict');
const {buildRenderCommand, REMOTION_CLI} = require('../scripts/lib/run-remotion');

test('buildRenderCommand не включает shell и передаёт аргументы как есть, без склейки в строку', () => {
  const {command, args, options} = buildRenderCommand([
    'remotion/src/index.jsx',
    'EditPlan',
    'out.mp4',
    '--props=brief.json; rm -rf /',
  ]);
  assert.equal(command, process.execPath);
  assert.deepEqual(args, [
    REMOTION_CLI,
    'render',
    'remotion/src/index.jsx',
    'EditPlan',
    'out.mp4',
    '--props=brief.json; rm -rf /',
  ]);
  assert.ok(!options.shell, 'опции spawn не должны включать shell (иначе аргументы могут быть переинтерпретированы им)');
});
