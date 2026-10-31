// Code-drawn thumbnail (1280x720 still), one per language: an approved background (cropped to fill), an approved
// hero pose large on the right, and the title in at most 2 lines (ink outline, paper fill) that shrinks to fit.
// All text is drawn here, never by the image model. Rendered by python -m tools.longform.thumb.
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Img, continueRender, delayRender, staticFile} from 'remotion';
import {INK} from './factions';
import {fitTitle} from './jabreak';

export type ThumbProps = {bg: string; hero: string; title: string; lang: string};

export const THUMB_W = 1280;
export const THUMB_H = 720;
const PAPER = '#f6ecd4';
const BOX_W = 760; // title box on the left; the hero takes the right side
const FONTS: Record<string, {family: string; file: string; em: number}> = {
  ja: {family: 'NotoSansJP', file: 'tools/kit/fonts/NotoSansJP-Variable.ttf', em: 1.0},
  other: {family: 'BeVietnamProBlack', file: 'tools/kit/fonts/BeVietnamPro-Black.ttf', em: 0.58},
};

const useFont = (family: string, file: string) => {
  const [handle] = useState(() => delayRender('font ' + family));
  useEffect(() => {
    const f = new FontFace(family, `url(${staticFile(file)})`, {weight: '100 900'});
    f.load().then((ff) => { document.fonts.add(ff); continueRender(handle); }).catch(() => continueRender(handle));
  }, [family, file, handle]);
};

export const Thumb: React.FC<ThumbProps> = ({bg, hero, title, lang}) => {
  const font = FONTS[lang === 'ja' ? 'ja' : 'other'];
  useFont(font.family, font.file);
  const fit = fitTitle(title, lang, 2, lang === 'ja' ? 7 : 12);
  const size = Math.min(132, Math.floor(BOX_W / (fit.maxChars * font.em)));
  return (
    <AbsoluteFill style={{background: PAPER, overflow: 'hidden'}}>
      {bg && <Img src={staticFile(bg)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover'}} />}
      {hero && (
        <Img src={staticFile(hero)}
             style={{position: 'absolute', right: 30, bottom: 0, height: THUMB_H * 0.96, width: 'auto', objectFit: 'contain',
                     filter: 'drop-shadow(0 8px 14px rgba(0,0,0,0.35))'}} />
      )}
      <div style={{position: 'absolute', left: 48, top: 0, bottom: 0, width: BOX_W, display: 'flex', flexDirection: 'column',
                   justifyContent: 'center'}}>
        {fit.lines.map((l, i) => (
          <div key={i} style={{fontFamily: font.family, fontWeight: 900, fontSize: size, lineHeight: 1.12, color: PAPER,
                               WebkitTextStroke: `${Math.max(6, Math.round(size / 9))}px ${INK}`, paintOrder: 'stroke fill',
                               whiteSpace: 'nowrap'}}>
            {l}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
