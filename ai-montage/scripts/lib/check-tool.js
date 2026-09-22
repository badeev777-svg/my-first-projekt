const {spawnSync} = require('node:child_process');

function checkTool(command, versionArgs = ['--version']) {
  const result = spawnSync(command, versionArgs, {encoding: 'utf8'});
  if (result.error || result.status !== 0) {
    return {ok: false, version: null};
  }
  const output = (result.stdout || result.stderr || '').trim().split('\n')[0];
  return {ok: true, version: output};
}

module.exports = {checkTool};
