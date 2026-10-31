// Assembles a whole video: chapter cards, voice blocks, beats timed to sentences, camera, transitions.
import React from 'react';
import {AbsoluteFill, Audio, Easing, interpolate, Sequence, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useAudioData, visualizeAudio} from '@remotion/media-utils';
import {BeatCtx} from './draw';
import {Card} from './scene';
import {DH, DW, FONT, FONT_URL, PAPER} from './theme';

export type Cam = {zoom?: [number, number]; focus?: [number, number]; at?: number; dur?: number};
/** One beat: starts at sentence `s` (1-based) of the block, `frac` of the way into it. */
export type Beat = {s: number; frac?: number; el: React.FC; cam?: Cam};
export type Scenes = Record<number, Beat[]>;
export type Block = {n: number; audio: string; start: number; card: number; dur: number; gap: number; starts: number[]; sents: string[]; cuts?: number[][]};
export type Timing = {fps: number; total: number; chapters: Record<string, string>; blocks: Block[]};

// the licensed font, loaded once per render tab
const fontHandle = delayRender('Patrick Hand font');
new FontFace('PatrickHand', `url(${FONT_URL})`).load().then((f) => {
  document.fonts.add(f);
  continueRender(fontHandle);
});

const XFADE = 6; // frames of crossfade between beats

/** Paper page with the hand-drawn wobble. The wobble pattern changes every 5 frames ("line boil"). */
const Page: React.FC<{bg: string; seed: number; cam?: Cam; beatDur: number; children: React.ReactNode}> = ({bg, seed, cam, beatDur, children}) => {
  const f = useCurrentFrame();
  const boil = seed * 7 + (Math.floor(f / 5) % 3);
  const [z0, z1] = cam?.zoom ?? [1, 1.03];
  const at = cam?.at ?? 0;
  const dur = cam?.dur ?? (cam?.zoom ? 18 : beatDur);
  const z = interpolate(f, [at, at + dur], [z0, z1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: cam?.zoom ? Easing.inOut(Easing.cubic) : Easing.linear});
  const [fx, fy] = cam?.focus ?? [DW / 2, DH / 2];
  return (
    <AbsoluteFill style={{backgroundColor: bg}}>
      <svg width="100%" height="100%" viewBox={`0 0 ${DW} ${DH}`} style={{fontFamily: FONT}}>
        <defs>
          <filter id={`rough${seed}`} x="-5%" y="-5%" width="110%" height="110%">
            <feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves={2} seed={boil} result="n" />
            <feDisplacementMap in="SourceGraphic" in2="n" scale={3.5} />
          </filter>
        </defs>
        <rect width={DW} height={DH} fill={bg} />
        <g transform={`translate(${fx},${fy}) scale(${z}) translate(${-fx},${-fy})`}>
          <g filter={`url(#rough${seed})`}>{children}</g>
        </g>
      </svg>
    </AbsoluteFill>
  );
};

const FadeIn: React.FC<{on: boolean; children: React.ReactNode}> = ({on, children}) => {
  const f = useCurrentFrame();
  const o = on ? interpolate(f, [0, XFADE], [0, 1], {extrapolateRight: 'clamp'}) : 1;
  return <AbsoluteFill style={{opacity: o}}>{children}</AbsoluteFill>;
};

/** The voice part of one block: audio plus its beats. */
const VoiceBlock: React.FC<{b: Block; beats: Beat[]; bg: string}> = ({b, beats, bg}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const src = staticFile(b.audio);
  const audioData = useAudioData(src);
  // cuts are [start, end] seconds of the voice file left out of the video
  const cuts = b.cuts ?? [];
  const toSrc = (t: number) => {
    let x = t;
    for (const [a, c] of cuts) if (x >= a) x += c - a;
    return x;
  };
  const amp = () => {
    if (!audioData || f >= b.dur * fps) return 0;
    const v = visualizeAudio({fps, frame: Math.round(toSrc(f / fps) * fps), audioData, numberOfSamples: 32});
    return Math.min(1, (v.slice(0, 12).reduce((a, c) => a + c, 0) / 12) * 6);
  };
  const tSent = (k: number, frac = 0) => {
    const s0 = b.starts[k - 1] ?? b.dur;
    const s1 = b.starts[k] ?? b.dur;
    return s0 + frac * (s1 - s0);
  };
  const times = beats.map((bt, i) => (i === 0 ? 0 : tSent(bt.s, bt.frac ?? 0)));
  const end = b.dur + b.gap;
  return (
    <>
      {cuts.length === 0 ? (
        <Audio src={src} />
      ) : (
        [[0, cuts[0][0]], ...cuts.map(([, c], i) => [c, cuts[i + 1]?.[0] ?? -1])].map(([a, c], i) => {
          let out = a;
          for (const [x, y] of cuts) if (a >= y) out -= y - x;
          return (
            <Sequence key={'a' + i} from={Math.round(out * fps)} name={`voice part ${i + 1}`}>
              <Audio src={src} trimBefore={Math.round(a * fps)} {...(c >= 0 ? {trimAfter: Math.round(c * fps)} : {})} />
            </Sequence>
          );
        })
      )}
      {beats.map((bt, i) => {
        const from = Math.round(times[i] * fps);
        const to = Math.round((i + 1 < beats.length ? times[i + 1] : end) * fps);
        const last = i + 1 === beats.length;
        const len = Math.max(1, to - from + (last ? 0 : XFADE));
        const El = bt.el;
        return (
          <Sequence key={i} from={from} durationInFrames={len} name={`beat ${b.n}.${i + 1} (s${bt.s})`}>
            <BeatCtx.Provider value={{block: b.n, dur: to - from, s: (k, frac = 0) => Math.round(tSent(k, frac) * fps) - from, amp}}>
              <FadeIn on={i > 0}>
                <Page bg={bg} seed={b.n * 10 + i} cam={bt.cam} beatDur={len}>
                  <El />
                </Page>
              </FadeIn>
            </BeatCtx.Provider>
          </Sequence>
        );
      })}
    </>
  );
};

/** The whole video, or one block (`block` prop) for quick tests. */
export const Video: React.FC<{timing: Timing; scenes: Scenes; bg: Record<number, string>; block?: number}> = ({timing, scenes, bg, block}) => {
  const {fps} = useVideoConfig();
  const blocks = timing.blocks.filter((b) => scenes[b.n] && (block === undefined || b.n === block));
  const order = Object.keys(timing.chapters).map(Number).sort((a, c) => a - c);
  const offset = blocks.length ? blocks[0].start : 0;
  return (
    <AbsoluteFill style={{backgroundColor: PAPER}}>
      {blocks.map((b) => {
        const from = Math.round((b.start - offset) * fps);
        const card = Math.round(b.card * fps);
        const len = card + Math.round((b.dur + b.gap) * fps);
        const color = bg[b.n] ?? PAPER;
        return (
          <Sequence key={b.n} from={from} durationInFrames={len} name={`block ${b.n}`}>
            {card > 0 && (
              <Sequence durationInFrames={card} name="card">
                <Page bg={color} seed={900 + b.n} beatDur={card}>
                  <Card index={order.indexOf(b.n) + 1} title={timing.chapters[String(b.n)]} />
                </Page>
              </Sequence>
            )}
            <Sequence from={card} name="voice">
              <VoiceBlock b={b} beats={scenes[b.n]} bg={color} />
            </Sequence>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

/** Length in frames of the whole video or of one block. */
export const videoFrames = (timing: Timing, scenes: Scenes, block?: number) => {
  const bs = timing.blocks.filter((b) => scenes[b.n] && (block === undefined || b.n === block));
  if (!bs.length) return 1;
  const last = bs[bs.length - 1];
  return Math.round((last.start + last.card + last.dur + last.gap - bs[0].start) * timing.fps);
};
