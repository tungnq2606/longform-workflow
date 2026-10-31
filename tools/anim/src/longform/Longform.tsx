// The production composition: one scene file, rendered in any language at that language's voice timing.
//   props come from `python -m tools.longform.render lang <project> <lang>` (render.props()).
import React, {useEffect, useMemo, useState} from 'react';
import {AbsoluteFill, Sequence, cancelRender, continueRender, delayRender, staticFile, useVideoConfig} from 'remotion';
import type {CalculateMetadataFunction} from 'remotion';
import {ChapterCard} from './Cards';
import type {LineBreaker} from './Cards';
import {Scene, FADE} from './Scene';
import {SoundTrack} from './SoundTrack';
import {build} from './timeline';
import type {FontInfo, LongformProps} from './types';

export const FPS = 30;
const CHAPTER_SECONDS = 3.5;

// Loads the language's font (languages.json) before the first frame; a missing font stops the render.
export const useFont = (font: FontInfo): void => {
  const [handle] = useState(() => delayRender(`font ${font.family}`));
  useEffect(() => {
    const f = new FontFace(font.family, `url(${staticFile(font.file)})`);
    f.load().then((ff) => { document.fonts.add(ff); continueRender(handle); }).catch((e) => cancelRender(e));
  }, [font.family, font.file, handle]);
};

export const longformMetadata: CalculateMetadataFunction<LongformProps> = ({props}) => ({
  durationInFrames: build(props.scenes, props.timing, FPS).durationInFrames,
});

export const EMPTY_PROPS: LongformProps = {
  scenes: {chapters: [], beats: {}}, timing: {lang: 'vi', duration: 1, beats: []}, labels: {}, lang: 'vi',
  audio: {voice: [], music: {}, sfx: []}, chapters: [], anchors: {}, backgrounds: {},
  font: {family: 'BeVietnamPro', file: 'tools/kit/fonts/BeVietnamPro-ExtraBold.ttf'},
};

export const Longform: React.FC<LongformProps & {lines?: LineBreaker}> = (props) => {
  const {scenes, timing, labels, lang, audio, chapters, anchors, backgrounds, font, lines} = props;
  useFont(font);
  const {fps} = useVideoConfig();
  const tl = useMemo(() => build(scenes, timing, fps, anchors), [scenes, timing, fps, anchors]);
  const speech = useMemo(() => timing.beats.flatMap((b) => b.sentences.map((s) => ({start: s.start, end: s.end}))), [timing]);
  return (
    <AbsoluteFill style={{background: '#000'}}>
      {tl.beats.map((b, i) => {
        const spec = scenes.beats[b.id];
        const last = i === tl.beats.length - 1;
        return (
          <Sequence key={b.id} from={b.from} durationInFrames={b.durationInFrames + (last ? 0 : FADE)} name={b.id}>
            <Scene spec={spec} beat={b} tl={tl} bg={backgrounds[spec.background.id]} labels={labels} lang={lang} font={font.family}
              fadeIn={i > 0} lines={lines} />
          </Sequence>
        );
      })}
      {chapters.filter((c) => c.titleCard && c.title).map((c) => {
        const first = tl.beats.find((b) => c.beats.includes(b.id));
        if (!first) return null;
        return (
          <Sequence key={`t${c.id}`} from={first.from} durationInFrames={Math.round(CHAPTER_SECONDS * fps)} name={`title ${c.id}`}>
            <ChapterCard title={c.title} font={font.family} lines={lines} />
          </Sequence>
        );
      })}
      <SoundTrack tl={tl} audio={audio} chapters={chapters} scenes={scenes} speech={speech} />
    </AbsoluteFill>
  );
};
