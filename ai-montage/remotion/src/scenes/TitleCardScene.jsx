import {AbsoluteFill, useCurrentFrame, spring, useVideoConfig} from 'remotion';
import {THEME} from '../Theme';

export const TitleCardScene = ({title, subtitle}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const scale = spring({frame, fps, config: {damping: 12}});

  return (
    <AbsoluteFill
      style={{
        backgroundColor: THEME.colors.background,
        alignItems: 'center',
        justifyContent: 'center',
        padding: THEME.safeZoneMargin,
      }}
    >
      <div style={{transform: `scale(${scale})`, textAlign: 'center'}}>
        <div style={{color: THEME.colors.foreground, fontFamily: THEME.fonts.title, fontSize: 72, fontWeight: 700}}>
          {title}
        </div>
        {subtitle ? (
          <div style={{color: THEME.colors.accent, fontFamily: THEME.fonts.body, fontSize: 40, marginTop: 24}}>
            {subtitle}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
