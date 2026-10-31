import React from 'react';
import {Composition} from 'remotion';
import {Spike, SPIKE_FRAMES} from './longform/Spike';
import {THUMB_H, THUMB_W, Thumb, type ThumbProps} from './longform/Thumb';

// Long-form compositions (see tools/anim/src/longform/). Render with: python -m tools.longform.render
export const Root: React.FC = () => (
  <>
    <Composition id="Spike" component={Spike} width={2560} height={1440} fps={30} durationInFrames={SPIKE_FRAMES} defaultProps={{boil: false}} />
    {/* Plan 6: per-language thumbnail still (python -m tools.longform.thumb) */}
    <Composition id="Thumb" component={Thumb} width={THUMB_W} height={THUMB_H} fps={30} durationInFrames={1}
                 defaultProps={{bg: '', hero: '', title: 'Bạch Đằng 1288', lang: 'vi'} as ThumbProps} />
  </>
);
