# Animated video toolkit (Remotion)

Animated version of the channel style: the stick figure breathes, blinks, changes pose smoothly, can talk
with the voice; props pop in, stamps slam, strips get cut, runners run, numbers count, the ink "boils".
Drawings use the same 1920x1080 space, shapes, palette and Patrick Hand font as `tools/kit`; output is
2560x1440 H.264 + AAC 48 kHz.

## Use

```
tools/anim/render.sh videos/NNN-slug studio   # live preview in the browser (scrub, tweak, reload)
tools/anim/render.sh videos/NNN-slug 1        # render voice block 1 only (test)
tools/anim/render.sh videos/NNN-slug          # whole video -> render/NNN-slug_1440p.mp4
```

`render.sh` runs `prep.py` first: it finds where each sentence starts in `audio/NN.mp3` (same alignment as
the static pipeline) and writes `anim/timing.json` and `src/current.ts`.

## Writing scenes

`videos/NNN-slug/anim/scenes.tsx` exports `BG`, `CHAPTERS` and `SCENES`:

```tsx
export const SCENES: Record<number, Beat[]> = {
  1: [
    {s: 1, el: MyScene, cam: {zoom: [1.08, 1], dur: 40}},   // beat starts at sentence 1
    {s: 2, frac: 0.5, el: Other},                          // halfway through sentence 2
  ],
};
const MyScene: React.FC = () => {
  const {s} = useBeat();                                   // s(k, frac) = frame where sentence k is spoken
  return (<>
    <Ground />
    <Figure x={300} y={520} s={1.25} keys={[{at: 4, pose: 'present'}, {at: s(1, 0.6), brows: 'worry'}]} talk />
    <In at={12} x={1500} y={760} how="pop"><Prop name="house" x={1500} y={760} /></In>
    <Stamp x={820} y={300} text="NOT EXACTLY" at={40} />
  </>);
};
```

Kit (`src/kit`): `Figure`, `Runner`, `Prop` (24 icons + calendar, pie), `Bubble`, `ThinkIcons`, `Stamp`,
`Strip`, `Scissors`, `Check`, `Bill`, `Track`, `Pie`, `LineChart`, `Signpost`, `Tightrope`, `Note`, `Big`,
`Chalkboard`, `Gavel`, `Table`, `Stairs`, `CrowdLine`, `Card`; motion: `In` (pop/up/down/left/right/fade/slam/grow),
`Count`, `Wipe`, `Float`, `Shake`, `useProgress`, `useSpring`. Frames are 30 per second; `at` is a frame
inside the beat.

## Notes

- Props must stay JSON (Remotion serialises them): scenes come in through `src/current.ts`, not props.
- GPU rendering (`--gl=angle`, set in `remotion.config.ts`) is about 4x faster; a 66 s block renders in ~30 s.
- Bitrate target is 16M; flat drawings need less, x264 lands near 10 Mbps. Quality is not the limit.
- Licence: see `LICENSES.md` (workspace root) (Remotion row).
