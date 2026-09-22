const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {ensureProjectExists} = require('./lib/project-paths');

const REPO_ROOT = path.join(__dirname, '..');

function pythonExecutable() {
  const venvPython = process.platform === 'win32'
    ? path.join(REPO_ROOT, 'python', 'venv', 'Scripts', 'python.exe')
    : path.join(REPO_ROOT, 'python', 'venv', 'bin', 'python');
  if (fs.existsSync(venvPython)) {
    return venvPython;
  }
  return 'python';
}

async function runTranscribe(args) {
  const {id} = args;
  if (!id) {
    throw new Error('Использование: transcribe --id <projectId>');
  }
  const dir = ensureProjectExists(id);

  const inputDir = path.join(dir, 'input');
  const sourceFile = fs.readdirSync(inputDir).find((f) => f.startsWith('source.'));
  if (!sourceFile) {
    throw new Error(`В проекте "${id}" не найден исходник source.* в input/`);
  }
  const sourcePath = path.join(inputDir, sourceFile);

  const transcriptDir = path.join(dir, 'transcript');
  const audioPath = path.join(transcriptDir, 'audio.wav');

  const extract = spawnSync('ffmpeg', ['-y', '-i', sourcePath, '-ac', '1', '-ar', '16000', audioPath]);
  if (extract.status !== 0) {
    throw new Error(`Не удалось извлечь звук через ffmpeg: ${extract.stderr}`);
  }

  const outPath = path.join(transcriptDir, 'transcript.json');
  const py = spawnSync(
    pythonExecutable(),
    [path.join(REPO_ROOT, 'python', 'transcribe.py'), '--audio', audioPath, '--out', outPath],
    {encoding: 'utf8'}
  );
  if (py.status !== 0) {
    throw new Error(`Ошибка транскрипции (faster-whisper): ${py.stderr}`);
  }
  console.log(py.stdout.trim());

  return {transcriptPath: outPath};
}

module.exports = {runTranscribe, pythonExecutable};
