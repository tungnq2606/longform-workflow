// Video made of generated images (images/frames/*.png): each image is shown from its sentence until the next
// image, with a slow zoom, a short crossfade, optional text overlays and the chapter cards drawn on top.
import React from 'react';
import {AbsoluteFill, Audio, Easing, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {ACC, FONT, INK} from './theme';

export type Overlay = {text: string; x?: number; y?: number; size?: number; color?: string; at?: number};
export type FrameItem = {id: string; file: string; from: number; to: number; block: number; overlays?: Overlay[]};
export type FBlock = {n: number; audio: string; start: number; card: number; dur: number; gap: number; cuts?: number[][]};
export type FramesTimeline = {fps: number; total: number; blocks: FBlock[]; frames: FrameItem[];
  chapters: {block: number; index: number; title: string; start: number; card: number}[]};

const XFADE = 8;

const OverlayText: React.FC<{o: Overlay}> = ({o}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const at = Math.round((o.at ?? 0.3) * fps);
  if (f < at) return null;
  const p = spring({frame: f - at, fps, config: {damping: 12, mass: 0.6}});
  return (
    <div style={{position: 'absolute', left: `${o.x ?? 50}%`, top: `${o.y ?? 15}%`, transform: `translate(-50%,-50%) scale(${p})`,
      background: 'rgba(255,255,255,0.92)', border: `6px solid ${INK}`, borderRadius: 28, padding: '10px 34px',
      fontFamily: FONT, fontSize: o.size ?? 110, color: o.color ?? ACC, fontWeight: 'bold', whiteSpace: 'nowrap'}}>
      {o.text}
    </div>
  );
};

const Shot: React.FC<{item: FrameItem; index: number; len: number}> = ({item, index, len}) => {
  const f = useCurrentFrame();
  const zoomIn = index % 2 === 0;
  const z = interpolate(f, [0, len], zoomIn ? [1, 1.06] : [1.06, 1], {extrapolateRight: 'clamp', easing: Easing.inOut(Easing.quad)});
  const o = index === 0 ? 1 : interpolate(f, [0, XFADE], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{opacity: o, overflow: 'hidden'}}>
      <Img src={staticFile(item.file)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${z})`}} />
      {(item.overlays ?? []).map((ov, i) => <OverlayText key={i} o={ov} />)}
    </AbsoluteFill>
  );
};

const ChapterCard: React.FC<{index: number; title: string}> = ({index, title}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 6, 39, 45], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'flex-start', opacity: o}}>
      <div style={{marginLeft: 160, background: 'rgba(250,247,240,0.94)', border: `8px solid ${INK}`, borderRadius: 36,
        padding: '40px 80px', fontFamily: FONT}}>
        <div style={{fontSize: 60, color: '#5b616b'}}>Part {index}</div>
        <div style={{fontSize: 130, color: INK, fontWeight: 'bold', lineHeight: 1.05}}>{title}</div>
      </div>
    </AbsoluteFill>
  );
};

const BlockAudio: React.FC<{b: FBlock}> = ({b}) => {
  const {fps} = useVideoConfig();
  const src = staticFile(b.audio);
  const cuts = b.cuts ?? [];
  if (!cuts.length) return <Audio src={src} />;
  const parts: number[][] = [[0, cuts[0][0]], ...cuts.map(([, c], i) => [c, cuts[i + 1]?.[0] ?? -1])];
  return (
    <>
      {parts.map(([a, c], i) => {
        let out = a;
        for (const [x, y] of cuts) if (a >= y) out -= y - x;
        return (
          <Sequence key={i} from={Math.round(out * fps)}>
            <Audio src={src} trimBefore={Math.round(a * fps)} {...(c >= 0 ? {trimAfter: Math.round(c * fps)} : {})} />
          </Sequence>
        );
      })}
    </>
  );
};

export const FramesVideo: React.FC<{tl: FramesTimeline}> = ({tl}) => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{backgroundColor: '#111'}}>
      {tl.frames.map((it, i) => {
        const from = Math.round(it.from * fps);
        const to = Math.round(it.to * fps);
        const len = Math.max(1, to - from + (i + 1 < tl.frames.length ? XFADE : 0));
        return (
          <Sequence key={it.id} from={from} durationInFrames={len} name={`frame ${it.id}`}>
            <Shot item={it} index={i} len={len} />
          </Sequence>
        );
      })}
      {tl.chapters.map((c) => (
        <Sequence key={'c' + c.block} from={Math.round(c.start * fps)} durationInFrames={Math.max(1, Math.round(c.card * fps))} name={`card ${c.title}`}>
          <ChapterCard index={c.index} title={c.title} />
        </Sequence>
      ))}
      {tl.blocks.map((b) => (
        <Sequence key={'a' + b.n} from={Math.round((b.start + b.card) * fps)} name={`voice ${b.n}`}>
          <BlockAudio b={b} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
