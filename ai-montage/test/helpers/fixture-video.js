const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');

function makeFixtureVideo({duration = 1} = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ai-montage-fixture-'));
  const file = path.join(dir, 'fixture.mp4');
  const result = spawnSync('ffmpeg', [
    '-y', '-f', 'lavfi', '-i', `testsrc=size=320x240:duration=${duration}:rate=25`,
    '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
    '-shortest', '-t', String(duration), file,
  ]);
  if (result.status !== 0) {
    throw new Error('Не удалось создать тестовое видео через ffmpeg: ' + result.stderr);
  }
  return file;
}

module.exports = {makeFixtureVideo};
