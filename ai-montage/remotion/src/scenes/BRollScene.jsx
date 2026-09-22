import {AbsoluteFill, Video} from 'remotion';
import {resolveMedia} from '../resolveMedia';
import {THEME} from '../Theme';

export const BRollScene = ({projectId, media, title}) => {
  return (
    <AbsoluteFill style={{backgroundColor: THEME.colors.background}}>
      <Video src={resolveMedia(projectId, media)} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      {title ? (
        <div
          style={{
            position: 'absolute',
            top: THEME.safeZoneMargin,
            left: THEME.safeZoneMargin,
            right: THEME.safeZoneMargin,
            color: THEME.colors.foreground,
            fontFamily: THEME.fonts.title,
            fontSize: 36,
            textShadow: '0 2px 8px rgba(0,0,0,0.8)',
          }}
        >
          {title}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
