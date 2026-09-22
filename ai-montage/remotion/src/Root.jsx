import {Composition} from 'remotion';
import {EditPlanComposition} from './EditPlanComposition';
import {calculateDurationInFrames} from './calculateDuration';

const defaultEditPlan = {
  projectId: 'default',
  fps: 30,
  width: 1080,
  height: 1920,
  audioTrack: 'source.mp4',
  scenes: [{type: 'title-card', start: 0, end: 1, title: 'ai-montage', audioMode: 'mute'}],
};

export const RemotionRoot = () => {
  return (
    <Composition
      id="EditPlan"
      component={EditPlanComposition}
      durationInFrames={30}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultEditPlan}
      calculateMetadata={async ({props}) => ({
        fps: props.fps,
        width: props.width,
        height: props.height,
        durationInFrames: calculateDurationInFrames(props.scenes, props.fps),
      })}
    />
  );
};
