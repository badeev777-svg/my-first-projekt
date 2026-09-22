import {AbsoluteFill, Video} from 'remotion';
import {resolveMedia} from '../resolveMedia';
import {THEME} from '../Theme';

export const SpeakerScene = ({projectId, media, audioTrack, subtitle, sourceStartFrame}) => {
  const videoFile = media || audioTrack;
  return (
    <AbsoluteFill style={{backgroundColor: THEME.colors.background}}>
      {videoFile ? (
        <Video
          src={resolveMedia(projectId, videoFile)}
          startFrom={sourceStartFrame}
          muted
          style={{width: '100%', height: '100%', objectFit: 'cover'}}
        />
      ) : null}
      {subtitle ? (
        <div
          style={{
            position: 'absolute',
            bottom: THEME.safeZoneMargin,
            left: THEME.safeZoneMargin,
            right: THEME.safeZoneMargin,
            color: THEME.colors.foreground,
            fontFamily: THEME.fonts.body,
            fontSize: 48,
            textAlign: 'center',
            textShadow: '0 2px 8px rgba(0,0,0,0.8)',
          }}
        >
          {subtitle}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
