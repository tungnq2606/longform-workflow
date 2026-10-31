// The one stick figure, animated. Same shapes as tools/kit/storyboard.py figure().
// It breathes, blinks, can talk (mouth follows the voice) and moves smoothly between poses.
//
//   <Figure x={300} y={520} s={1.25} pose="present" brows="raise" eyes="right"
//           keys={[{at: s(3), pose: 'point', mouth: 'smile'}]} talk />
import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Circle, Line, Poly, Rect, useBeat} from './draw';
import {INK} from './theme';

type Pt = [number, number];
export type Pose = 'neutral' | 'wave' | 'paper' | 'point' | 'finger' | 'cross' | 'lens' | 'shrug' | 'think' | 'present';
export type Brows = 'flat' | 'raise' | 'both' | 'skeptic' | 'worry' | 'low';
export type Eyes = 'center' | 'left' | 'right' | 'down' | 'up' | 'wide';
export type Mouth = 'flat' | 'smile' | 'smirk' | 'frown' | 'o';
type State = {pose: Pose; brows: Brows; eyes: Eyes; mouth: Mouth};
export type FigKey = Partial<State> & {at: number};

const L_DOWN: Pt[] = [[0, 105], [-45, 160], [-70, 215]];
const ARMS: Record<Pose, Pt[][]> = {
  neutral: [L_DOWN, [[0, 105], [45, 160], [70, 215]]],
  wave: [L_DOWN, [[0, 105], [75, 70], [100, -25]]],
  paper: [L_DOWN, [[0, 105], [60, 155], [95, 150]]],
  point: [L_DOWN, [[0, 105], [110, 95], [210, 85]]],
  finger: [L_DOWN, [[0, 105], [75, 120], [95, 20]]],
  cross: [[[0, 110], [45, 175], [-35, 150]], [[0, 110], [-45, 175], [35, 150]]],
  lens: [L_DOWN, [[0, 105], [70, 85], [115, 70]]],
  shrug: [[[0, 105], [-75, 125], [-105, 55]], [[0, 105], [75, 125], [105, 55]]],
  think: [L_DOWN, [[0, 105], [75, 150], [30, 78]]],
  present: [L_DOWN, [[0, 105], [85, 140], [165, 115]]],
};
const BROWS: Record<Brows, Pt[][]> = {
  flat: [[[-44, -38], [-14, -38]], [[14, -38], [44, -38]]],
  raise: [[[-44, -38], [-14, -38]], [[14, -36], [44, -58]]],
  both: [[[-44, -50], [-14, -56]], [[14, -56], [44, -50]]],
  skeptic: [[[-44, -44], [-14, -34]], [[14, -34], [44, -44]]],
  worry: [[[-44, -34], [-14, -46]], [[14, -46], [44, -34]]],
  low: [[[-44, -30], [-14, -30]], [[14, -30], [44, -30]]],
};
const EYES: Record<Eyes, Pt> = {center: [0, 0], left: [-9, 0], right: [9, 0], down: [0, 7], up: [0, -6], wide: [0, 0]};
// Every mouth as 3 points so mouths can morph; 'o' is drawn as an ellipse.
const MOUTH: Record<Mouth, Pt[]> = {
  flat: [[-18, 34], [0, 34], [18, 34]],
  smile: [[-20, 28], [0, 38], [20, 28]],
  smirk: [[-18, 36], [8, 34], [22, 24]],
  frown: [[-20, 40], [0, 32], [20, 40]],
  o: [[-9, 34], [0, 34], [9, 34]],
};

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerpPts = (a: Pt[], b: Pt[], t: number): Pt[] => a.map((p, i) => [lerp(p[0], b[i][0], t), lerp(p[1], b[i][1], t)]);

export const Figure: React.FC<{
  x: number; y: number; s?: number; flip?: boolean;
  pose?: Pose; brows?: Brows; eyes?: Eyes; mouth?: Mouth;
  keys?: FigKey[]; // changes over time (frames relative to the beat)
  talk?: boolean | [number, number]; // mouth follows the voice (optionally only between two frames)
  still?: boolean; // no breathing (for tiny figures in a crowd)
  seed?: number;
}> = ({x, y, s = 1, flip = false, pose = 'neutral', brows = 'flat', eyes = 'center', mouth = 'flat', keys = [], talk = false, still = false, seed = 0}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const beat = useBeat();

  // resolve previous and current state, and progress of the latest change
  let prev: State = {pose, brows, eyes, mouth};
  let cur: State = prev;
  let at = -999;
  for (const k of [...keys].sort((a, b) => a.at - b.at)) {
    if (k.at > f) break;
    prev = cur;
    cur = {...cur, ...k};
    at = k.at;
  }
  const p = at < 0 ? 1 : spring({frame: f - at, fps, config: {damping: 13, mass: 0.55}});
  const arms = ARMS[prev.pose].map((a, i) => lerpPts(a, ARMS[cur.pose][i], p));
  const brs = BROWS[prev.brows].map((b, i) => lerpPts(b, BROWS[cur.brows][i], Math.min(p, 1)));
  const eo: Pt = [lerp(EYES[prev.eyes][0], EYES[cur.eyes][0], p), lerp(EYES[prev.eyes][1], EYES[cur.eyes][1], p)];
  const mPts = lerpPts(MOUTH[prev.mouth], MOUTH[cur.mouth], Math.min(p, 1));
  const wideW = (prev.eyes === 'wide' ? 1 - p : 0) + (cur.eyes === 'wide' ? p : 0);

  // breathing and blinking (deterministic per figure)
  const bob = still ? 0 : Math.sin((f + seed * 23) / 45 * 2 * Math.PI) * 3;
  const period = 95 + ((seed * 37) % 50);
  const blinkK = (f + seed * 11) % period;
  const blink = !still && blinkK < 4;

  // talking: open mouth with the voice loudness
  const talking = talk === true || (Array.isArray(talk) && f >= talk[0] && f < talk[1]);
  const amp = talking ? beat.amp() : 0;
  const open = amp > 0.12 ? Math.min(1, amp * 1.6) : 0;

  // pose props fade in/out with the change
  const w = (name: Pose) => (prev.pose === name ? 1 - p : 0) + (cur.pose === name ? p : 0);

  const body = (
    <g transform={`translate(0,${bob})`}>
      <Circle cx={0} cy={0} r={72} />
      {[-24, 24].map((ex) => (
        <g key={ex}>
          {wideW > 0.02 && <circle cx={ex} cy={-6} r={13 * wideW} fill="#fff" stroke={INK} strokeWidth={4} />}
          {blink ? <Line x1={ex - 8} y1={-6} x2={ex + 8} y2={-6} w={5} /> : <circle cx={ex + eo[0]} cy={-6 + eo[1]} r={6} fill={INK} />}
        </g>
      ))}
      {brs.map((b, i) => <Line key={i} x1={b[0][0]} y1={b[0][1]} x2={b[1][0]} y2={b[1][1]} w={7} />)}
      {open > 0 ? (
        <ellipse cx={0} cy={34} rx={14} ry={3 + open * 12} fill={INK} />
      ) : cur.mouth === 'o' && p > 0.5 ? (
        <ellipse cx={0} cy={34} rx={9} ry={11} fill="none" stroke={INK} strokeWidth={6} />
      ) : (
        <Poly pts={mPts} w={6} />
      )}
      <Line x1={0} y1={72} x2={0} y2={235} w={7} />
      {arms.map((a, i) => <Poly key={i} pts={a} w={7} />)}
      {w('paper') > 0.05 && (
        <g opacity={w('paper')}>
          <Rect x={60} y={70} w={100} h={130} fill="#fff" sw={5} r={6} />
          <Line x1={76} y1={100} x2={144} y2={100} w={4} />
          <Line x1={76} y1={124} x2={144} y2={124} w={4} />
          <Line x1={76} y1={148} x2={120} y2={148} w={4} />
        </g>
      )}
      {w('lens') > 0.05 && <circle cx={140} cy={40} r={42} fill="none" stroke={INK} strokeWidth={7} opacity={w('lens')} />}
      {w('finger') > 0.05 && <g opacity={w('finger')}><Line x1={95} y1={20} x2={95} y2={-12} w={7} /></g>}
      {w('shrug') > 0.05 && (
        <g opacity={w('shrug')}>
          <Line x1={-105} y1={55} x2={-125} y2={45} w={6} />
          <Line x1={105} y1={55} x2={125} y2={45} w={6} />
        </g>
      )}
    </g>
  );
  const legs = (
    <>
      <Line x1={0} y1={235 + bob} x2={-55} y2={340} w={7} />
      <Line x1={0} y1={235 + bob} x2={55} y2={340} w={7} />
    </>
  );
  const inner = <g transform={`translate(${x},${y}) scale(${s})`}>{body}{legs}</g>;
  return flip ? <g transform={`translate(${2 * x},0) scale(-1,1)`}>{inner}</g> : inner;
};

/** A running figure with a label on its chest (pay vs rent races). Legs cycle while running. */
export const Runner: React.FC<{x: number; y: number; s?: number; label: string; color: string; mouth?: 'flat' | 'smile' | 'frown'; sweat?: boolean; running?: boolean}> = ({x, y, s = 1, label, color, mouth = 'flat', sweat = false, running = true}) => {
  const f = useCurrentFrame();
  const ph = running ? Math.floor(f / 4) % 2 : 0;
  const bob = running ? (ph ? -6 : 0) : 0;
  const M: Record<string, Pt[]> = {smile: [[10, 26], [30, 36], [48, 26]], frown: [[12, 36], [30, 28], [46, 36]], flat: [[12, 32], [46, 32]]};
  const legsA: Pt[][] = [[[-40, 210], [20, 260], [10, 330]], [[-40, 210], [-90, 270], [-150, 280]]];
  const legsB: Pt[][] = [[[-40, 210], [-10, 270], [-60, 330]], [[-40, 210], [10, 265], [70, 290]]];
  const armsA: Pt[][] = [[[-18, 95], [40, 120], [70, 85]], [[-18, 95], [-70, 135], [-95, 110]]];
  const armsB: Pt[][] = [[[-18, 95], [-40, 140], [-10, 160]], [[-18, 95], [30, 135], [60, 120]]];
  const legs = ph ? legsB : legsA;
  const arms = ph ? armsB : armsA;
  const swt = interpolate(f % 20, [0, 19], [0, 14]);
  return (
    <g transform={`translate(${x},${y + bob * s}) scale(${s})`}>
      <Circle cx={0} cy={0} r={62} />
      <circle cx={14} cy={-6} r={6} fill={INK} />
      <circle cx={40} cy={-6} r={6} fill={INK} />
      <Line x1={4} y1={-34} x2={26} y2={-40} w={6} />
      <Line x1={32} y1={-40} x2={52} y2={-32} w={6} />
      <Poly pts={M[mouth]} w={6} />
      <Line x1={-10} y1={62} x2={-40} y2={210} w={7} />
      {arms.map((a, i) => <Poly key={i} pts={a} w={7} />)}
      {legs.map((a, i) => <Poly key={'l' + i} pts={a} w={7} />)}
      <g transform="rotate(14 -25 132)">
        <Rect x={-75} y={108} w={100} h={48} fill={color} sw={5} r={6} />
        <text x={-25} y={143} fontSize={32} textAnchor="middle" fill={color === '#fff' ? INK : '#fff'} fontWeight="bold">{label}</text>
      </g>
      {running && [0, 1, 2].map((k) => <Line key={k} x1={-175 - k * 10 - ((f * 3 + k * 20) % 40)} y1={60 + k * 50} x2={-115 - k * 10 - ((f * 3 + k * 20) % 40)} y2={60 + k * 50} w={5} c="#9fb3c4" />)}
      {sweat && <path d={`M-62 ${-40 + swt} q-10 18 0 26 q10 -8 0 -26`} fill="#7fb6e6" stroke={INK} strokeWidth={3} />}
    </g>
  );
};
