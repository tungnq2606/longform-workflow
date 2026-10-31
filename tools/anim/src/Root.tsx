import React from 'react';
import {Composition} from 'remotion';
import {Spike, SPIKE_FRAMES} from './longform/Spike';
import {EMPTY_PROPS, FPS, Longform, longformMetadata} from './longform/Longform';

// Long-form compositions (see tools/anim/src/longform/). Render with: python -m tools.longform.render
export const Root: React.FC = () => (
  <>
    <Composition id="Spike" component={Spike} width={2560} height={1440} fps={30} durationInFrames={SPIKE_FRAMES} defaultProps={{boil: false}} />
    {/* Production long-form video (Plan 5): props from render.props(), duration from the language's voice timing */}
    <Composition id="Longform" component={Longform} width={2560} height={1440} fps={FPS} durationInFrames={1}
      defaultProps={EMPTY_PROPS} calculateMetadata={longformMetadata} />
  </>
);
