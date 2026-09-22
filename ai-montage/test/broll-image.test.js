const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {renderComposition} = require('../scripts/lib/run-remotion');

const REPO_ROOT = path.join(__dirname, '..');

function makeGreenImage(dir) {
  const file = path.join(dir, 'still.png');
  const result = spawnSync('ffmpeg', [
    '-y', '-f', 'lavfi', '-i', 'color=c=green:s=320x240:d=1',
    '-frames:v', '1', file,
  ]);
  if (result.status !== 0) throw new Error('ffmpeg (image) failed: ' + result.stderr);
  return file;
}

function averageRGBAt(filePath, atSeconds) {
  const result = spawnSync('ffmpeg', [
    '-y', '-ss', String(atSeconds), '-i', filePath,
    '-vframes', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1',
  ], {maxBuffer: 1024 * 1024 * 20});
  if (result.status !== 0) throw new Error('ffmpeg (frame extract) failed: ' + result.stderr.toString());
  const buf = result.stdout;
  let r = 0, g = 0, b = 0, count = 0;
  for (let i = 0; i + 2 < buf.length; i += 3) {
    r += buf[i]; g += buf[i + 1]; b += buf[i + 2]; count++;
  }
  return {r: r / count, g: g / count, b: b / count};
}

test('b-roll-сцена со статичным изображением рендерится и показывает картинку', {timeout: 120000}, () => {
  const projectId = 'broll-image-' + Date.now();
  const publicDir = path.join(REPO_ROOT, 'remotion', 'public', 'projects', projectId);
  fs.mkdirSync(publicDir, {recursive: true});

  const image = makeGreenImage(fs.mkdtempSync(path.join(os.tmpdir(), 'ai-montage-broll-img-')));
  fs.copyFileSync(image, path.join(publicDir, 'still.png'));

  const plan = {
    projectId, fps: 25, width: 320, height: 240,
    scenes: [{type: 'b-roll', start: 0, end: 1, media: 'still.png', audioMode: 'mute'}],
  };
  const propsPath = path.join(os.tmpdir(), `props-${projectId}.json`);
  fs.writeFileSync(propsPath, JSON.stringify(plan));
  const outPath = path.join(os.tmpdir(), `${projectId}.mp4`);

  const result = renderComposition(['remotion/src/index.jsx', 'EditPlan', outPath, `--props=${propsPath}`]);

  try {
    assert.equal(result.status, 0, result.stderr || result.stdout);
    const color = averageRGBAt(outPath, 0.4);
    assert.ok(color.g > color.r && color.g > color.b, `b-roll с изображением должен показывать зелёную картинку, получено ${JSON.stringify(color)}`);
  } finally {
    fs.rmSync(publicDir, {recursive: true, force: true});
    fs.rmSync(propsPath, {force: true});
    fs.rmSync(outPath, {force: true});
  }
});
