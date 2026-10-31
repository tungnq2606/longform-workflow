// Animated scenes for this video (Remotion toolkit, see tools/anim/README.md).
// Pattern to copy from: channels/median-worker/videos/001-rent-vs-pay/anim/scenes.tsx. Vary layouts between videos.
import React from 'react';
import {Beat, Figure, Ground, In, Prop, T, useBeat} from '@kit';

export const BG: Record<number, string> = {1: '#E4EEF6'};

// Chapter cards (silence before the block). prep.py reads this object, keep it on simple "N: \"title\"" lines.
export const CHAPTERS: Record<number, string> = {};

const B1_open: React.FC = () => {
  const {s} = useBeat();
  return (
    <>
      <Ground />
      <Figure x={300} y={520} s={1.25} keys={[{at: 4, pose: 'present'}]} talk />
      <In at={s(1, 0.4)} x={1300} y={600} how="pop"><Prop name="house" x={1300} y={600} s={1.4} /></In>
      <In at={10} how="up" dist={40}><T x={1300} y={300} size={60} bold>REPLACE ME</T></In>
    </>
  );
};

export const SCENES: Record<number, Beat[]> = {
  1: [{s: 1, el: B1_open}],
};
