function calculateDurationInFrames(scenes, fps) {
  if (!scenes || scenes.length === 0) {
    return fps;
  }
  const lastEnd = Math.max(...scenes.map((s) => s.end));
  return Math.max(1, Math.round(lastEnd * fps));
}

module.exports = {calculateDurationInFrames};
