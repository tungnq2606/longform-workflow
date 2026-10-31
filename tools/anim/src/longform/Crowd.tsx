// A column of code-drawn soldiers walking along a path; far ones shrink, drawn back to front.
import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {depthScale, pointAt} from './path';
import type {Pt} from './path';
import {Soldier} from './Soldier';
import type {Faction} from './factions';

export const Crowd: React.FC<{
  path: Pt[]; count: number; spacing: number; speed: number; faction: Faction;
  horizonY: number; groundY: number; minS?: number; maxS?: number; seed?: number;
}> = ({path, count, spacing, speed, faction, horizonY, groundY, minS = 0.12, maxS = 1, seed = 0}) => {
  const frame = useCurrentFrame();
  const men = Array.from({length: count}, (_, i) => {
    const t = (((i * spacing + frame * speed) % 1) + 1) % 1;
    const p = pointAt(path, t);
    return {i, x: p.x, y: p.y, facing: (Math.cos(p.angle) >= 0 ? 1 : -1) as 1 | -1, s: depthScale(p.y, horizonY, groundY, minS, maxS)};
  }).sort((a, b) => a.y - b.y);
  return (
    <AbsoluteFill>
      <svg width="100%" height="100%" viewBox="0 0 2560 1440">
        {men.map((m) => (
          <Soldier key={m.i} x={m.x} y={m.y} s={m.s} faction={faction} seed={seed + m.i * 7} facing={m.facing} walkPhase={frame * 0.35 + m.i * 1.3} />
        ))}
      </svg>
    </AbsoluteFill>
  );
};
