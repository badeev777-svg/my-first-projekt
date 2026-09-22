#!/usr/bin/env node

const COMMANDS = {
  'check-env': () => require('./check-env').runCheckEnv,
  'new-project': () => require('./new-project').runNewProject,
  transcribe: () => require('./transcribe').runTranscribe,
  validate: () => require('./validate').runValidate,
  preview: () => require('./preview').runPreview,
  approve: () => require('./approve').runApprove,
  render: () => require('./render').runRender,
  qa: () => require('./qa').runQa,
  demo: () => require('./demo').runDemo,
};

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i];
    if (!key || !key.startsWith('--')) {
      throw new Error(`Ожидался флаг вида --name, получено: ${key}`);
    }
    args[key.slice(2)] = argv[i + 1];
  }
  return args;
}

function printHelp() {
  console.log('Использование: node scripts/cli.js <command> [--flag value ...]');
  console.log('Команды: ' + Object.keys(COMMANDS).join(', '));
}

async function main() {
  const [command, ...rest] = process.argv.slice(2);
  if (!command) {
    printHelp();
    process.exitCode = 1;
    return;
  }
  const loader = COMMANDS[command];
  if (!loader) {
    console.error(`Неизвестная команда: ${command}`);
    printHelp();
    process.exitCode = 1;
    return;
  }
  const args = parseArgs(rest);
  const fn = loader();
  await fn(args);
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err.message);
    process.exitCode = 1;
  });
}

module.exports = {parseArgs};
