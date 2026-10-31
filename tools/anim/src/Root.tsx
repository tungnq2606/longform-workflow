import React from 'react';
import {Composition} from 'remotion';
import {Spike, SPIKE_FRAMES} from './longform/Spike';

// Long-form compositions (see tools/anim/src/longform/). Render with: python -m tools.longform.render
export const Root: React.FC = () => (
  <>
    <Composition id="Spike" component={Spike} width={2560} height={1440} fps={30} durationInFrames={SPIKE_FRAMES} defaultProps={{boil: false}} />
  </>
);
