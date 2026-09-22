const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {runNewProject} = require('../scripts/new-project');
const {runTranscribe} = require('../scripts/transcribe');
const {getPublicProjectDir} = require('../scripts/lib/project-paths');
const {makeFixtureVideo} = require('./helpers/fixture-video');

test('runTranscribe создаёт transcript.json для тестового ролика', {timeout: 300000}, async () => {
  const fixture = makeFixtureVideo({duration: 2});
  const id = 'test-transcribe-' + Date.now();
  const project = await runNewProject({id, input: fixture});

  try {
    const result = await runTranscribe({id});
    assert.ok(fs.existsSync(result.transcriptPath));
    const transcript = JSON.parse(fs.readFileSync(result.transcriptPath, 'utf8'));
    assert.ok(Array.isArray(transcript.words));
    assert.ok(Array.isArray(transcript.segments));
    assert.equal(typeof transcript.text, 'string');
  } finally {
    fs.rmSync(project.dir, {recursive: true, force: true});
    fs.rmSync(getPublicProjectDir(id), {recursive: true, force: true});
  }
});
