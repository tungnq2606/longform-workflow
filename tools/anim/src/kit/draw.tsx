// Drawing primitives (ink lines, boxes, text) and motion helpers.
// Every motion helper takes `at` = the frame (inside the current beat) where it starts.
// Use useBeat().s(k) to get the frame where sentence k of the voice block starts.
import React, {createContext, useContext} from 'react';
import {Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {INK} from './theme';

// ------------------------------------------------------------------ beat context
export type BeatInfo = {
  block: number;
  dur: number; // frames this beat is on screen
  s: (k: number, frac?: number) => number; // frame (relative to beat start) where sentence k starts
  amp: () => number; // voice loudness now, 0..1 (for talking mouths)
};
export const BeatCtx = createContext<BeatInfo>({block: 0, dur: 1, s: () => 0, amp: () => 0});
export const useBeat = () => useContext(BeatCtx);

// ------------------------------------------------------------------ easing helpers
export const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
/** 0..1 eased progress from frame `at` over `dur` frames. */
export const useProgress = (at = 0, dur = 12, ease = Easing.inOut(Easing.cubic)) => {
  const f = useCurrentFrame();
  return interpolate(f, [at, at + dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease});
};
/** Springy 0..1 (overshoots a little) starting at frame `at`. */
export const useSpring = (at = 0, damping = 12, mass = 0.6) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: f - at, fps, config: {damping, mass}});
};

// ------------------------------------------------------------------ primitives
type Pt = [number, number];
export const Line: React.FC<{x1: number; y1: number; x2: number; y2: number; w?: number; c?: string; dash?: string; draw?: number}> = ({x1, y1, x2, y2, w = 6, c = INK, dash, draw}) => (
  <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={c} strokeWidth={w} strokeLinecap="round"
    {...(draw !== undefined ? {pathLength: 1, strokeDasharray: '1 1', strokeDashoffset: 1 - draw} : dash ? {strokeDasharray: dash} : {})} />
);
export const Rect: React.FC<{x: number; y: number; w: number; h: number; fill?: string; c?: string; sw?: number; r?: number; opacity?: number}> = ({x, y, w, h, fill = 'none', c = INK, sw = 6, r = 10, opacity}) => (
  <rect x={x} y={y} width={Math.max(0, w)} height={Math.max(0, h)} rx={r} fill={fill} stroke={c} strokeWidth={sw} opacity={opacity} />
);
export const Poly: React.FC<{pts: Pt[]; c?: string; w?: number; fill?: string; draw?: number}> = ({pts, c = INK, w = 7, fill = 'none', draw}) => (
  <polyline points={pts.map((p) => p.join(',')).join(' ')} fill={fill} stroke={c} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round"
    {...(draw !== undefined ? {pathLength: 1, strokeDasharray: '1 1', strokeDashoffset: 1 - draw} : {})} />
);
export const Circle: React.FC<{cx: number; cy: number; r: number; fill?: string; c?: string; sw?: number}> = ({cx, cy, r, fill = '#fff', c = INK, sw = 7}) => (
  <circle cx={cx} cy={cy} r={r} fill={fill} stroke={c} strokeWidth={sw} />
);
/** Text. Size is multiplied by 1.15 like the static kit (Patrick Hand runs narrow). */
export const T: React.FC<{x: number; y: number; children: React.ReactNode; size?: number; anchor?: 'start' | 'middle' | 'end'; fill?: string; bold?: boolean; opacity?: number}> = ({x, y, children, size = 40, anchor = 'middle', fill = INK, bold = false, opacity}) => (
  <text x={x} y={y} fontSize={Math.round(size * 1.15)} textAnchor={anchor} fill={fill} fontWeight={bold ? 'bold' : 'normal'} opacity={opacity}>{children}</text>
);
export const G: React.FC<{x?: number; y?: number; s?: number; rot?: number; o?: number; children: React.ReactNode}> = ({x = 0, y = 0, s = 1, rot = 0, o, children}) => (
  <g transform={`translate(${x},${y}) rotate(${rot}) scale(${s})`} opacity={o}>{children}</g>
);

// ------------------------------------------------------------------ motion wrappers
type Enter = 'pop' | 'up' | 'down' | 'left' | 'right' | 'fade' | 'slam' | 'grow';
/**
 * Brings children in at frame `at`. `x, y` is the anchor for scaling (pop/slam/grow).
 * `out` (frame) fades them away again.
 */
export const In: React.FC<{at?: number; x?: number; y?: number; how?: Enter; dist?: number; out?: number; children: React.ReactNode}> = ({at = 0, x = 960, y = 540, how = 'pop', dist = 120, out, children}) => {
  const f = useCurrentFrame();
  const sp = useSpring(at, how === 'slam' ? 9 : 12);
  const lin = useProgress(at, 8);
  if (f < at) return null;
  const o = out !== undefined ? interpolate(f, [out, out + 6], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
  let tr = '';
  if (how === 'pop') tr = `translate(${x},${y}) scale(${sp}) translate(${-x},${-y})`;
  if (how === 'grow') tr = `translate(${x},${y}) scale(1,${sp}) translate(${-x},${-y})`;
  if (how === 'slam') tr = `translate(${x},${y}) scale(${2.2 - 1.2 * sp}) translate(${-x},${-y})`;
  if (how === 'up') tr = `translate(0,${(1 - sp) * dist})`;
  if (how === 'down') tr = `translate(0,${-(1 - sp) * dist})`;
  if (how === 'left') tr = `translate(${(1 - sp) * dist},0)`;
  if (how === 'right') tr = `translate(${-(1 - sp) * dist},0)`;
  return <g transform={tr} opacity={Math.min(lin * 1.5, 1) * o}>{children}</g>;
};

/** Gentle floating (for icons, bubbles) so nothing is ever perfectly still. */
export const Float: React.FC<{amp?: number; period?: number; seed?: number; children: React.ReactNode}> = ({amp = 6, period = 70, seed = 0, children}) => {
  const f = useCurrentFrame();
  return <g transform={`translate(0,${Math.sin((f + seed * 17) / period * 2 * Math.PI) * amp})`}>{children}</g>;
};

/** Shake (for a stamp landing or a "no"). */
export const Shake: React.FC<{at: number; dur?: number; amp?: number; children: React.ReactNode}> = ({at, dur = 10, amp = 10, children}) => {
  const f = useCurrentFrame();
  const k = f - at;
  const dx = k >= 0 && k < dur ? Math.sin(k * 2.2) * amp * (1 - k / dur) : 0;
  return <g transform={`translate(${dx},0)`}>{children}</g>;
};

/** Number counting up from `from` to `to` starting at `at`. */
export const Count: React.FC<{at?: number; dur?: number; from?: number; to: number; fmt?: (v: number) => string; x: number; y: number; size?: number; fill?: string; bold?: boolean; anchor?: 'start' | 'middle' | 'end'}> = ({at = 0, dur = 24, from = 0, to, fmt = (v) => Math.round(v).toLocaleString('en-US'), ...t}) => {
  const p = useProgress(at, dur, Easing.out(Easing.cubic));
  return <T {...t}>{fmt(from + (to - from) * p)}</T>;
};

/** Reveals children left-to-right with a clip (good for strips, bars, underlines). */
export const Wipe: React.FC<{at?: number; dur?: number; x: number; y: number; w: number; h: number; children: React.ReactNode; id: string}> = ({at = 0, dur = 14, x, y, w, h, children, id}) => {
  const p = useProgress(at, dur);
  return (
    <g>
      <defs><clipPath id={id}><rect x={x} y={y} width={w * p} height={h} /></clipPath></defs>
      <g clipPath={`url(#${id})`}>{children}</g>
    </g>
  );
};
