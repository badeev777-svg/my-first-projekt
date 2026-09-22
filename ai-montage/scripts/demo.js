const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {spawnSync} = require('node:child_process');
const {runCheckEnv} = require('./check-env');
const {runNewProject} = require('./new-project');
const {runTranscribe} = require('./transcribe');
const {runApprove} = require('./approve');
const {runRender} = require('./render');
const {runQa} = require('./qa');
const {getProjectDir} = require('./lib/project-paths');

const DEMO_ID = 'demo-01';

function makeDemoSourceVideo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ai-montage-demo-'));
  const file = path.join(dir, 'demo-source.mp4');
  const result = spawnSync('ffmpeg', [
    '-y', '-f', 'lavfi', '-i', 'testsrc=size=640x360:duration=6:rate=30',
    '-f', 'lavfi', '-i', 'sine=frequency=440:duration=6',
    '-shortest', '-t', '6', file,
  ]);
  if (result.status !== 0) {
    throw new Error('Не удалось создать нейтральное demo-видео: ' + result.stderr);
  }
  return file;
}

async function runDemo(id = DEMO_ID) {
  console.log('=== ai-montage: сборка нейтрального demo ===');

  const env = await runCheckEnv();
  if (!env.ok) {
    throw new Error('Сначала установите недостающие инструменты (см. вывод check-env выше).');
  }

  const dir = getProjectDir(id);
  if (fs.existsSync(dir)) {
    throw new Error(`Проект "${id}" уже существует: ${dir}. Удалите папку вручную, чтобы пересобрать demo.`);
  }

  const source = makeDemoSourceVideo();
  await runNewProject({id, input: source});
  await runTranscribe({id});

  const briefPath = path.join(dir, 'brief', 'v01.json');
  const plan = {
    projectId: id,
    fps: 30,
    width: 1080,
    height: 1920,
    audioTrack: 'source.mp4',
    scenes: [
      {type: 'speaker', start: 0, end: 2, audioMode: 'sync', subtitle: 'Демонстрационный ролик'},
      {type: 'title-card', start: 2, end: 4, title: 'ai-montage', subtitle: 'нейтральное demo', audioMode: 'mute'},
      {type: 'b-roll', start: 4, end: 6, media: 'source.mp4', audioMode: 'mute'},
    ],
  };
  fs.writeFileSync(briefPath, JSON.stringify(plan, null, 2));

  await runApprove({id, version: 'v01'});
  await runRender({id, version: 'v01'});
  const qaResult = await runQa({id, version: 'v01'});

  if (!qaResult.passed) {
    throw new Error('Demo не прошло QA: ' + qaResult.problems.join('; '));
  }

  console.log(`Готово: ${qaResult.finalPath}`);
  return qaResult;
}

module.exports = {runDemo};

if (require.main === module) {
  runDemo().catch((err) => {
    console.error(err.message);
    process.exitCode = 1;
  });
}
