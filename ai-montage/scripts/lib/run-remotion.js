const path = require('node:path');
const {spawnSync} = require('node:child_process');

const REPO_ROOT = path.join(__dirname, '..', '..');
const REMOTION_CLI = path.join(REPO_ROOT, 'node_modules', '@remotion', 'cli', 'remotion-cli.js');

function buildRenderCommand(remotionArgs) {
  return {
    command: process.execPath,
    args: [REMOTION_CLI, 'render', ...remotionArgs],
    options: {cwd: REPO_ROOT, encoding: 'utf8'},
  };
}

function renderComposition(remotionArgs) {
  const {command, args, options} = buildRenderCommand(remotionArgs);
  return spawnSync(command, args, options);
}

module.exports = {renderComposition, buildRenderCommand, REPO_ROOT, REMOTION_CLI};
