const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {ensureProjectExists} = require('./lib/project-paths');

const DURATION_TOLERANCE_SECONDS = 0.5;

function probe(filePath) {
  const result = spawnSync(
    'ffprobe',
    ['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filePath],
    {encoding: 'utf8'}
  );
  if (result.status !== 0) {
    throw new Error(`ffprobe не смог прочитать файл: ${result.stderr}`);
  }
  return JSON.parse(result.stdout);
}

function fullDecodeCheck(filePath) {
  const result = spawnSync('ffmpeg', ['-v', 'error', '-i', filePath, '-f', 'null', '-'], {encoding: 'utf8'});
  return {ok: result.status === 0 && !result.stderr.trim(), detail: result.stderr};
}

async function runQa(args) {
  const {id, version} = args;
  if (!id || !version) {
    throw new Error('Использование: qa --id <projectId> --version <v01>');
  }
  const dir = ensureProjectExists(id);
  const renderPath = path.join(dir, 'renders', `${version}.mp4`);
  if (!fs.existsSync(renderPath)) {
    throw new Error(`Рендер не найден: ${renderPath}. Сначала выполните: render --id ${id} --version ${version}`);
  }
  const approvedPath = path.join(dir, 'brief', `${version}-approved.json`);
  const plan = JSON.parse(fs.readFileSync(approvedPath, 'utf8'));
  const expectedDuration = Math.max(...plan.scenes.map((s) => s.end));

  const problems = [];

  const decode = fullDecodeCheck(renderPath);
  if (!decode.ok) {
    problems.push(`Файл не декодируется полностью: ${decode.detail}`);
  }

  const passport = probe(renderPath);
  const actualDuration = Number(passport.format.duration);
  if (Math.abs(actualDuration - expectedDuration) > DURATION_TOLERANCE_SECONDS) {
    problems.push(
      `Длительность рендера (${actualDuration.toFixed(2)} c) не совпадает с планом (${expectedDuration.toFixed(2)} c)`
    );
  }

  const hasVideo = passport.streams.some((s) => s.codec_type === 'video');
  const hasAudio = passport.streams.some((s) => s.codec_type === 'audio');
  if (!hasVideo) problems.push('В файле нет видеодорожки');
  if (!hasAudio) problems.push('В файле нет звуковой дорожки');

  if (problems.length > 0) {
    console.error('QA не пройдена:');
    for (const p of problems) console.error(`  - ${p}`);
    return {passed: false, problems};
  }

  const finalPath = path.join(dir, 'final', `${id}.mp4`);
  fs.copyFileSync(renderPath, finalPath);
  console.log(`QA пройдена. Финал: ${finalPath}`);
  return {passed: true, finalPath};
}

module.exports = {runQa, probe, fullDecodeCheck};
