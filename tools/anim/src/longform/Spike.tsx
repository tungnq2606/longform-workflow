// 10-second spike (Plan 1): AI background + code-drawn crowd + AI hero kit + Remotion title, for the owner's style verdict.
import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import bg from '../../../../library/backgrounds/bach-dang-path-01.json';
import {Crowd} from './Crowd';
import {Hero} from './Hero';
import type {Pt} from './path';
import {Title} from './Title';

export const SPIKE_FRAMES = 300;

const Boil: React.FC<{on: boolean; children: React.ReactNode}> = ({on, children}) => {
  const seed = Math.floor(useCurrentFrame() / 3) % 7;
  if (!on) return <>{children}</>;
  return (
    <AbsoluteFill style={{filter: 'url(#boil)'}}>
      <svg width={0} height={0} style={{position: 'absolute'}}>
        <filter id="boil">
          <feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves={2} seed={seed} />
          <feDisplacementMap in="SourceGraphic" scale={3} />
        </filter>
      </svg>
      {children}
    </AbsoluteFill>
  );
};

export const Spike: React.FC<{boil: boolean}> = ({boil}) => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, SPIKE_FRAMES], [1, 1.06]);
  const pan = interpolate(frame, [0, SPIKE_FRAMES], [0, -40]);
  const black = interpolate(frame, [0, 15], [1, 0], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <AbsoluteFill style={{transform: `translateX(${pan}px) scale(${zoom})`, transformOrigin: '60% 60%'}}>
        <Img src={staticFile(bg.image)} style={{width: 2560, height: 1440, objectFit: 'cover'}} />
        <Boil on={boil}>
          <Crowd path={bg.path as Pt[]} count={30} spacing={0.03} speed={0.0012} faction="nguyen" horizonY={bg.horizonY} groundY={bg.groundY} seed={3} />
        </Boil>
        <Hero image="tran-hung-dao/stand.calm" x={2050} groundY={bg.heroGround} enter="right" at={90}
          keys={[{at: 180, image: 'tran-hung-dao/point.determined'}]} seed={2} />
      </AbsoluteFill>
      <Title kicker="1288" title="Sông Bạch Đằng" sub="Quân Nguyên tiến về cửa biển…" at={45} />
      <AbsoluteFill style={{background: '#000', opacity: black}} />
    </AbsoluteFill>
  );
};
