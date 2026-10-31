// An important character drawn by AI as an approved kit (library/characters/<id>/kit.json).
// Only kit images can be used: `image` is a HeroKey ('<kit id>/<pose>.<expression>'), so an unknown pose fails tsc.
//
//   <Hero image="tran-hung-dao/stand.calm" x={2050} groundY={1300} enter="right" at={90}
//         keys={[{at: 180, image: 'tran-hung-dao/point.determined'}]} />
import React from 'react';
import {Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {KITS} from './kits.generated';
import type {HeroKey} from './kits.generated';

type KitImage = {file: string; anchor: readonly [number, number] | readonly number[]; size: readonly number[]; blink?: string};
type Kit = {name: string; height: number; images: Record<string, KitImage>};

const FADE = 4; // frames of cross-fade between two kit images
const BLINK = 4; // frames the eyes stay closed

function lookup(key: string): {kit: Kit; im: KitImage} {
  const cut = key.indexOf('/');
  const kit = (KITS as unknown as Record<string, Kit>)[key.slice(0, cut)];
  const im = kit?.images[key.slice(cut + 1)];
  if (!kit || !im) throw new Error(`Hero: no kit image "${key}"`);
  return {kit, im};
}

const Pose: React.FC<{k: string; x: number; groundY: number; s: number; opacity: number; blink: boolean; breathe: number}> = ({k, x, groundY, s, opacity, blink, breathe}) => {
  const {kit, im} = lookup(k);
  const scale = (s * kit.height) / im.anchor[1];
  const [w, h] = [im.size[0] * scale, im.size[1] * scale];
  const src = staticFile(blink && im.blink ? im.blink : im.file);
  return (
    <Img
      src={src}
      style={{
        position: 'absolute', left: x - im.anchor[0] * scale, top: groundY - im.anchor[1] * scale, width: w, height: h, opacity,
        transformOrigin: `${im.anchor[0] * scale}px ${im.anchor[1] * scale}px`, transform: `scaleY(${breathe})`,
      }}
    />
  );
};

export const Hero: React.FC<{
  image: HeroKey; x: number; groundY: number; s?: number; enter?: 'left' | 'right' | 'none'; at?: number;
  keys?: {at: number; image: HeroKey}[]; seed?: number;
}> = ({image, x, groundY, s = 1, enter = 'none', at = 0, keys = [], seed = 0}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (frame < at) return null;
  const steps = [{at: 0, image: image as string}, ...keys.map((k) => ({at: k.at, image: k.image as string}))].sort((a, b) => a.at - b.at);
  let cur = 0;
  steps.forEach((st, i) => { if (frame >= st.at) cur = i; });
  const fade = cur > 0 ? interpolate(frame - steps[cur].at, [0, FADE], [0, 1], {extrapolateRight: 'clamp'}) : 1;
  const slide = enter === 'none' ? 0 : (1 - spring({frame: frame - at, fps, durationInFrames: 18, config: {damping: 200}})) * 600 * (enter === 'left' ? -1 : 1);
  const breathe = 1 + 0.008 * Math.sin((2 * Math.PI * 0.25 * frame) / fps);
  const period = 95 + ((seed * 13) % 31);
  const blink = (frame + seed * 7) % period < BLINK;
  const {kit, im} = lookup(steps[cur].image);
  const shadowW = im.size[0] * ((s * kit.height) / im.anchor[1]) * 0.4;
  const hx = x + slide;
  return (
    <>
      <div style={{position: 'absolute', left: hx - shadowW / 2, top: groundY - shadowW * 0.04, width: shadowW, height: shadowW * 0.08,
        borderRadius: '50%', background: 'rgba(40,30,20,0.25)', filter: 'blur(4px)'}} />
      {cur > 0 && fade < 1 && <Pose k={steps[cur - 1].image} x={hx} groundY={groundY} s={s} opacity={1 - fade} blink={false} breathe={breathe} />}
      <Pose k={steps[cur].image} x={hx} groundY={groundY} s={s} opacity={fade} blink={blink} breathe={breathe} />
    </>
  );
};
