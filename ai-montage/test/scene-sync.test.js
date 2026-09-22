const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {renderComposition} = require('../scripts/lib/run-remotion');

const REPO_ROOT = path.join(__dirname, '..');

function makeSplitColorSource() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ai-montage-split-'));
  const red = path.join(dir, 'red.mp4');
  const blue = path.join(dir, 'blue.mp4');
  const out = path.join(dir, 'source.mp4');

  for (const [file, color] of [[red, 'red'], [blue, 'blue']]) {
    const result = spawnSync('ffmpeg', [
      '-y', '-f', 'lavfi', '-i', `color=c=${color}:s=320x240:d=2:r=25`,
      '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2',
      '-shortest', '-t', '2', file,
    ]);
    if (result.status !== 0) throw new Error('ffmpeg (segment) failed: ' + result.stderr);
  }

  const concatResult = spawnSync('ffmpeg', [
    '-y', '-i', red, '-i', blue,
    '-filter_complex', '[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]',
    '-map', '[v]', '-map', '[a]', out,
  ]);
  if (concatResult.status !== 0) throw new Error('ffmpeg (concat) failed: ' + concatResult.stderr);
  return out;
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

function meanVolumeDb(filePath, start, duration) {
  const result = spawnSync('ffmpeg', [
    '-ss', String(start), '-t', String(duration), '-i', filePath,
    '-af', 'volumedetect', '-f', 'null', '-',
  ], {encoding: 'utf8'});
  const match = result.stderr.match(/mean_volume:\s*(-?[\d.]+|-inf)\s*dB/);
  if (!match) throw new Error('volumedetect не вернул mean_volume: ' + result.stderr);
  return match[1] === '-inf' ? -Infinity : Number(match[1]);
}

test('speaker-сцена начинает источник со своего start, а audioMode "mute" реально глушит звук', {timeout: 120000}, () => {
  const projectId = 'scene-sync-' + Date.now();
  const publicDir = path.join(REPO_ROOT, 'remotion', 'public', 'projects', projectId);
  fs.mkdirSync(publicDir, {recursive: true});

  const source = makeSplitColorSource();
  fs.copyFileSync(source, path.join(publicDir, 'source.mp4'));

  const plan = {
    projectId, fps: 30, width: 320, height: 568,
    audioTrack: 'source.mp4',
    scenes: [
      {type: 'title-card', start: 0, end: 2, title: 'x', audioMode: 'mute'},
      {type: 'speaker', start: 2, end: 4, audioMode: 'sync', subtitle: 'x'},
    ],
  };
  const propsPath = path.join(os.tmpdir(), `props-${projectId}.json`);
  fs.writeFileSync(propsPath, JSON.stringify(plan));
  const outPath = path.join(os.tmpdir(), `${projectId}.mp4`);

  const result = renderComposition(['remotion/src/index.jsx', 'EditPlan', outPath, `--props=${propsPath}`]);

  try {
    assert.equal(result.status, 0, result.stderr || result.stdout);

    const colorInSpeakerScene = averageRGBAt(outPath, 2.5);
    assert.ok(
      colorInSpeakerScene.b > colorInSpeakerScene.r,
      `speaker-сцена (start=2) должна показывать источник с его 2-й секунды (синий), получено r=${colorInSpeakerScene.r} b=${colorInSpeakerScene.b}`
    );

    const titleCardVolume = meanVolumeDb(outPath, 0.3, 1.4);
    assert.ok(titleCardVolume < -40, `звук в 'mute'-сцене должен быть тихим, получено ${titleCardVolume} dB`);

    const speakerVolume = meanVolumeDb(outPath, 2.3, 1.4);
    assert.ok(speakerVolume > -40, `звук в 'sync'-сцене должен быть слышен, получено ${speakerVolume} dB`);
  } finally {
    fs.rmSync(publicDir, {recursive: true, force: true});
    fs.rmSync(propsPath, {force: true});
    fs.rmSync(outPath, {force: true});
  }
});
