const {staticFile} = require('remotion');

function resolveMedia(projectId, fileName) {
  return staticFile(`projects/${projectId}/${fileName}`);
}

module.exports = {resolveMedia};
