import React from 'react';
import {Composition} from 'remotion';
import {Video, videoFrames} from './kit/Video';
import type {Timing} from './kit/Video';
import {BG, SCENES, TIMING} from './current';
import {FramesVideo} from './kit/FramesVideo';
import type {FramesTimeline} from './kit/FramesVideo';
import {FRAMES} from './current_frames';

const timing = TIMING as unknown as Timing;
const frames = FRAMES as unknown as FramesTimeline;

// Props must stay JSON (Remotion serialises them), so scenes are imported here, not passed as props.
const Main: React.FC<{block: number | null}> = ({block}) => <Video timing={timing} scenes={SCENES} bg={BG} block={block ?? undefined} />;

// "Video" renders the whole video; pass --props='{"block":1}' to render one voice block.
const FramesMain: React.FC = () => <FramesVideo tl={frames} />;

export const Root: React.FC = () => (
  <>
  <Composition
    id="Video"
    component={Main}
    width={2560}
    height={1440}
    fps={timing.fps}
    durationInFrames={videoFrames(timing, SCENES)}
    defaultProps={{block: null as number | null}}
    calculateMetadata={({props}) => ({durationInFrames: videoFrames(timing, SCENES, props.block ?? undefined)})}
  />
  {/* "Frames": video built from generated images (tools/anim/render_frames.sh) */}
  <Composition id="Frames" component={FramesMain} width={2560} height={1440} fps={frames.fps}
    durationInFrames={Math.max(1, Math.round(frames.total * frames.fps))} />
  </>
);
