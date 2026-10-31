// Render settings follow YouTube's upload recommendation for 1440p30 (channel standard).
import {Config} from '@remotion/cli/config';
import path from 'path';

const root = process.cwd();
Config.overrideWebpackConfig((c) => ({
  ...c,
  resolve: {
    ...c.resolve,
    // videos/NNN-slug/anim/scenes.tsx lives outside this folder: let it import the kit and our node_modules
    alias: {...(c.resolve?.alias ?? {}), '@kit': path.join(root, 'src/kit/index.ts')},
    modules: [path.join(root, 'node_modules'), 'node_modules'],
  },
}));
Config.setCodec('h264');
Config.setPixelFormat('yuv420p');
Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(95);
// Target 16M (YouTube 1440p30). Flat drawings need less: x264 lands near 10 Mbps, CRF 10 would be 3.7 Mbps.
Config.setVideoBitrate('16M');
Config.setAudioBitrate('128k');
Config.setX264Preset('medium');
Config.setChromiumOpenGlRenderer('angle'); // GPU: about 4x faster than the default for the SVG wobble filter
