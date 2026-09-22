const path = require('node:path');
const {spawnSync} = require('node:child_process');

const REPO_ROOT = path.join(__dirname, '..', '..');
const REMOTION_CLI = path.join(REPO_ROOT, 'node_modules', '@remotion', 'cli', 'remotion-cli.js');

const MAX_BUFFER_BYTES = 200 * 1024 * 1024;

function buildRenderCommand(remotionArgs) {
  return {
    command: process.execPath,
    args: [REMOTION_CLI, 'render', ...remotionArgs],
    options: {cwd: REPO_ROOT, encoding: 'utf8', maxBuffer: MAX_BUFFER_BYTES},
  };
}

function renderComposition(remotionArgs) {
  const {command, args, options} = buildRenderCommand(remotionArgs);
  return spawnSync(command, args, options);
}

module.exports = {renderComposition, buildRenderCommand, REPO_ROOT, REMOTION_CLI};
