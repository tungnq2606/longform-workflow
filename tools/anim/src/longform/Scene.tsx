// One beat on screen: background under an eased camera, code-drawn crowds, kit heroes (pose changes on sentences),
// a code-drawn map when the beat has one, text cards on their sentence. Frames inside are local to the beat's <Sequence>.
import React from 'react';
import {AbsoluteFill, Img, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {ChapterCard, DateCard, NameLabel, TwoSourceCard} from './Cards';
import type {LineBreaker} from './Cards';
import {Crowd} from './Crowd';
import {Hero} from './Hero';
import {MapView} from './MapView';
import type {HeroKey} from './kits.generated';
import type {Pt} from './path';
import {camera, sentenceFrame} from './timeline';
import type {Timeline, TlBeat} from './timeline';
import {label} from './types';
import type {BeatSpec, BgInfo, CardSpec, Labels} from './types';

export const FADE = 10; // frames of cross-fade into a beat
const CARD_SECONDS = 4.5;

const Card: React.FC<{c: CardSpec; labels: Labels; lang: string; font: string; lines?: LineBreaker}> = ({c, labels, lang, font, lines}) => {
  const text = label(labels, c.text_key, lang);
  if (c.type === 'date') return <DateCard text={text} font={font} lines={lines} />;
  if (c.type === 'name') return <NameLabel text={text} font={font} lines={lines} />;
  if (c.type === 'two_source') return <TwoSourceCard left={text} right={label(labels, c.text_key2, lang)} font={font} lines={lines} />;
  return <ChapterCard title={text} font={font} lines={lines} />;
};

export const Scene: React.FC<{
  spec: BeatSpec; beat: TlBeat; tl: Timeline; bg: BgInfo | undefined; labels: Labels; lang: string; font: string;
  fadeIn: boolean; lines?: LineBreaker;
}> = ({spec, beat, tl, bg, labels, lang, font, fadeIn, lines}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = (sid: string) => sentenceFrame(tl, sid) - beat.from;
  const cam = camera(frame / Math.max(1, beat.durationInFrames), spec.background.camera.from, spec.background.camera.to);
  const opacity = fadeIn ? interpolate(frame, [0, FADE], [0, 1], {extrapolateRight: 'clamp'}) : 1;
  const horizonY = bg?.horizonY ?? 600;
  const groundY = bg?.groundY ?? 1440;
  const heroGround = bg?.heroGround ?? Math.min(groundY, 1320);
  return (
    <AbsoluteFill style={{opacity, background: '#000'}}>
      <AbsoluteFill style={{transform: `translate(${cam.x}px, ${cam.y}px) scale(${cam.zoom})`, transformOrigin: '50% 50%'}}>
        {bg && <Img src={staticFile(bg.image)} style={{width: 2560, height: 1440, objectFit: 'cover'}} />}
        {(spec.crowds ?? []).map((c, i) => (
          <Crowd key={`c${i}`} path={(c.path === 'background' ? bg?.path ?? [] : c.path) as Pt[]} count={c.count} spacing={1 / Math.max(1, c.count)}
            speed={c.speed} faction={c.faction} horizonY={horizonY} groundY={groundY} seed={i * 11 + 3} />
        ))}
        {(spec.heroes ?? []).map((h, i) => (
          <Hero key={`h${i}`} image={h.key as HeroKey} x={h.x} groundY={heroGround} enter={h.enter ?? 'none'} at={0} seed={i + 1}
            keys={(h.keys ?? []).map((k) => ({at: local(k.sentence), image: k.key as HeroKey})).filter((k) => k.at >= 0)} />
        ))}
      </AbsoluteFill>
      {spec.map && <MapView map={spec.map} labels={labels} lang={lang} font={font} arrowsAt={(spec.map.arrows ?? []).map((a) => local(a.sentence))} />}
      {(spec.cards ?? []).map((c, i) => {
        const at = local(c.sentence);
        if (at < 0 || at >= beat.durationInFrames) return null;
        const len = c.type === 'two_source' ? beat.durationInFrames - at : Math.min(beat.durationInFrames - at, Math.round(CARD_SECONDS * fps));
        return (
          <Sequence key={`k${i}`} from={at} durationInFrames={Math.max(1, len)} layout="none">
            <Card c={c} labels={labels} lang={lang} font={font} lines={lines} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
