import {AbsoluteFill, Img, Video} from 'remotion';
import {resolveMedia} from '../resolveMedia';
import {THEME} from '../Theme';

const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.gif'];

function isImage(fileName) {
  const lower = String(fileName).toLowerCase();
  return IMAGE_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export const BRollScene = ({projectId, media, title}) => {
  const src = resolveMedia(projectId, media);
  return (
    <AbsoluteFill style={{backgroundColor: THEME.colors.background}}>
      {isImage(media) ? (
        <Img src={src} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      ) : (
        <Video src={src} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      )}
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
