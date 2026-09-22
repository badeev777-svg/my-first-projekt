import {AbsoluteFill, Audio, Sequence} from 'remotion';
import {SpeakerScene} from './scenes/SpeakerScene';
import {TitleCardScene} from './scenes/TitleCardScene';
import {BRollScene} from './scenes/BRollScene';
import {resolveMedia} from './resolveMedia';
import {THEME} from './Theme';

const SCENE_COMPONENTS = {
  speaker: SpeakerScene,
  'title-card': TitleCardScene,
  'b-roll': BRollScene,
};

export const EditPlanComposition = ({projectId, fps, audioTrack, scenes}) => {
  return (
    <AbsoluteFill style={{backgroundColor: THEME.colors.background}}>
      {audioTrack ? <Audio src={resolveMedia(projectId, audioTrack)} /> : null}
      {scenes.map((scene, index) => {
        const SceneComponent = SCENE_COMPONENTS[scene.type];
        if (!SceneComponent) {
          throw new Error(`Неизвестный тип сцены: ${scene.type}`);
        }
        const from = Math.round(scene.start * fps);
        const durationInFrames = Math.max(1, Math.round((scene.end - scene.start) * fps));
        return (
          <Sequence key={index} from={from} durationInFrames={durationInFrames}>
            <SceneComponent {...scene} projectId={projectId} audioTrack={audioTrack} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
