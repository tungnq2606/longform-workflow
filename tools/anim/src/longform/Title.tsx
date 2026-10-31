// Chapter title card drawn on the picture: small spaced kicker, bold title, underline drawn left to right,
// optional subtitle typed letter by letter (all text comes from Remotion, never from AI images).
import React, {useEffect, useState} from 'react';
import {continueRender, delayRender, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {INK} from './factions';

const FONT = 'BeVietnamPro';
const useFont = () => {
  const [handle] = useState(() => delayRender('font'));
  useEffect(() => {
    const f = new FontFace(FONT, `url(${staticFile('tools/kit/fonts/BeVietnamPro-ExtraBold.ttf')})`);
    f.load().then((ff) => { document.fonts.add(ff); continueRender(handle); });
  }, [handle]);
};

export const Title: React.FC<{kicker: string; title: string; sub?: string; at: number; x?: number; y?: number}> = ({kicker, title, sub, at, x = 120, y = 110}) => {
  useFont();
  const f = useCurrentFrame() - at;
  if (f < 0) return null;
  const fade = interpolate(f, [0, 12], [0, 1], {extrapolateRight: 'clamp'});
  const line = interpolate(f, [8, 28], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const typed = sub ? sub.slice(0, Math.max(0, Math.floor((f - 30) / 1.5))) : '';
  return (
    <div style={{position: 'absolute', left: x, top: y, color: INK, fontFamily: FONT, opacity: fade}}>
      <div style={{fontSize: 38, letterSpacing: 10, color: '#8a3b2a'}}>{kicker}</div>
      <div style={{fontSize: 112, lineHeight: 1.1, marginTop: 8}}>{title}</div>
      <div style={{height: 6, width: 560 * line, background: INK, marginTop: 14, borderRadius: 3}} />
      {sub && <div style={{fontSize: 46, marginTop: 22, fontStyle: 'italic', opacity: 0.85}}>{typed}</div>}
    </div>
  );
};
