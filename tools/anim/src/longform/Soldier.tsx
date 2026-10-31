// One code-drawn stick soldier (crowd tier): big round head, big eyes, stick limbs, helmet, shield, weapon.
// Feet at (x, y); s = 1 is about 270 px tall on the 1440p frame.
import React from 'react';
import {FACTIONS, INK} from './factions';
import type {Faction} from './factions';

const MOUTHS = ['flat', 'o', 'frown', 'smile'] as const;

export const Soldier: React.FC<{x: number; y: number; s: number; faction: Faction; seed: number; facing?: 1 | -1; walkPhase: number}> = ({
  x, y, s, faction, seed, facing = 1, walkPhase,
}) => {
  const f = FACTIONS[faction];
  const sw = 6;
  const swing = Math.sin(walkPhase) * 0.35;
  const bob = -Math.abs(Math.sin(walkPhase)) * 5;
  const leg = 75;
  const hip: [number, number] = [0, -leg];
  const foot = (a: number): [number, number] => [Math.sin(a) * leg, -leg + Math.cos(a) * leg];
  const [fa, fb] = [foot(swing), foot(-swing)];
  const neck = -150 + bob;
  const head = -200 + bob;
  const mouth = MOUTHS[Math.abs(seed) % MOUTHS.length];
  const look = 6 * facing;
  return (
    <g transform={`translate(${x} ${y}) scale(${s * facing} ${s})`}>
      <line x1={hip[0]} y1={hip[1]} x2={fa[0]} y2={fa[1]} stroke={INK} strokeWidth={sw} strokeLinecap="round" />
      <line x1={hip[0]} y1={hip[1]} x2={fb[0]} y2={fb[1]} stroke={INK} strokeWidth={sw} strokeLinecap="round" />
      <path d={`M -16 ${neck + 8} L 16 ${neck + 8} L 20 ${hip[1] + 6} L -20 ${hip[1] + 6} Z`} fill={f.tunic} stroke={INK} strokeWidth={4} />
      {f.weapon === 'spear' ? (
        <g>
          <line x1={34} y1={-60} x2={34} y2={head - 90} stroke={INK} strokeWidth={5} />
          <path d={`M 26 ${head - 88} L 34 ${head - 115} L 42 ${head - 88} Z`} fill="#6b6b6b" stroke={INK} strokeWidth={3} />
        </g>
      ) : (
        <line x1={30} y1={-95} x2={58} y2={-150} stroke="#7d7d7d" strokeWidth={6} strokeLinecap="round" />
      )}
      <line x1={0} y1={neck + 14} x2={30} y2={-95} stroke={INK} strokeWidth={sw} strokeLinecap="round" />
      <line x1={0} y1={neck + 14} x2={-26} y2={-100} stroke={INK} strokeWidth={sw} strokeLinecap="round" />
      {f.shield && (
        <g>
          <circle cx={-30} cy={-100} r={28} fill="#7a5532" stroke={INK} strokeWidth={4} />
          <circle cx={-30} cy={-100} r={10} fill="#a77a48" stroke={INK} strokeWidth={3} />
        </g>
      )}
      <circle cx={0} cy={head} r={46} fill={f.skin} stroke={INK} strokeWidth={5} />
      {f.helmet === 'round' ? (
        <path d={`M -50 ${head - 6} A 50 46 0 0 1 50 ${head - 6} L 54 ${head + 2} L -54 ${head + 2} Z`} fill="#6e6656" stroke={INK} strokeWidth={4} />
      ) : (
        <path d={`M -52 ${head - 4} L 0 ${head - 78} L 52 ${head - 4} Z`} fill="#4f5a5e" stroke={INK} strokeWidth={4} />
      )}
      <circle cx={-14} cy={head + 8} r={13} fill="#fff" stroke={INK} strokeWidth={3} />
      <circle cx={18} cy={head + 8} r={13} fill="#fff" stroke={INK} strokeWidth={3} />
      <circle cx={-14 + look} cy={head + 9} r={5} fill={INK} />
      <circle cx={18 + look} cy={head + 9} r={5} fill={INK} />
      {mouth === 'o' && <ellipse cx={4} cy={head + 30} rx={5} ry={7} fill={INK} />}
      {mouth === 'flat' && <line x1={-6} y1={head + 30} x2={14} y2={head + 30} stroke={INK} strokeWidth={4} strokeLinecap="round" />}
      {mouth === 'frown' && <path d={`M -6 ${head + 33} Q 4 ${head + 25} 14 ${head + 33}`} fill="none" stroke={INK} strokeWidth={4} strokeLinecap="round" />}
      {mouth === 'smile' && <path d={`M -6 ${head + 27} Q 4 ${head + 35} 14 ${head + 27}`} fill="none" stroke={INK} strokeWidth={4} strokeLinecap="round" />}
    </g>
  );
};
