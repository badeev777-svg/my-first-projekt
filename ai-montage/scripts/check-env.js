const {checkTool} = require('./lib/check-tool');

const TOOLS = [
  {name: 'Node.js', command: 'node', args: ['--version'], hint: 'должен быть уже установлен, раз вы это запускаете'},
  {name: 'Python 3', command: 'python', args: ['--version'], hint: 'установите с python.org или через winget install Python.Python.3'},
  {name: 'FFmpeg', command: 'ffmpeg', args: ['-version'], hint: 'установите через winget install Gyan.FFmpeg'},
  {name: 'FFprobe', command: 'ffprobe', args: ['-version'], hint: 'ставится вместе с FFmpeg'},
];

async function runCheckEnv() {
  const results = TOOLS.map((tool) => ({
    ...tool,
    ...checkTool(tool.command, tool.args),
  }));

  console.log('Проверка окружения ai-montage:');
  for (const r of results) {
    if (r.ok) {
      console.log(`  [OK]      ${r.name}: ${r.version}`);
    } else {
      console.log(`  [НЕ НАЙДЕНО] ${r.name} — ${r.hint}`);
    }
  }

  const allOk = results.every((r) => r.ok);
  if (allOk) {
    console.log('Всё готово, можно создавать проект (new-project).');
  } else {
    console.log('Установите недостающие инструменты и запустите check-env снова.');
    process.exitCode = 1;
  }
  return {ok: allOk, results};
}

module.exports = {runCheckEnv};
