// Pure timing for the Longform composition (no React; tested with `node --test src/longform/`).
// Beats come from the scene file; their frames come from one language's voice timing (lang/<code>/timing.json),
// so the same scene file plays at every language's own pace.

export type TimedSentence = {id: string; start: number; end: number};
export type Timing = {lang: string; duration: number; beats: {id: string; start: number; end: number; sentences: TimedSentence[]}[]};
// Source-language (vi) sentence id -> its place in its beat. Scene anchors are vi ids; a rewritten language maps them
// by position inside the beat (sentence i of n -> sentence floor(i*m/n) of the m sentences that language has).
export type Anchors = Record<string, {beat: string; index: number; count: number}>;
export type TlSentence = {id: string; from: number; end: number};
export type TlBeat = {id: string; from: number; durationInFrames: number; sentences: TlSentence[]};
export type Timeline = {fps: number; durationInFrames: number; beats: TlBeat[]; anchors: Anchors};
export type Cam = {zoom: number; x: number; y: number};

export const TAIL = 15; // frames after the last word

export function build(scenes: {beats: Record<string, unknown>}, timing: Timing, fps: number, anchors: Anchors = {}): Timeline {
  const durationInFrames = Math.max(1, Math.ceil(timing.duration * fps)) + TAIL;
  const used = timing.beats.filter((b) => b.id in scenes.beats);
  const froms = used.map((b, i) => (i === 0 ? 0 : Math.round(b.start * fps)));
  const beats = used.map((b, i) => ({
    id: b.id,
    from: froms[i],
    durationInFrames: Math.max(1, (i + 1 < used.length ? froms[i + 1] : durationInFrames) - froms[i]),
    sentences: b.sentences.map((s) => ({id: s.id, from: Math.round(s.start * fps), end: Math.round(s.end * fps)})),
  }));
  return {fps, durationInFrames, beats, anchors};
}

// Absolute frame where a scene's sentence anchor starts in this language, or -1 when it cannot be placed.
export function sentenceFrame(tl: Timeline, sentenceId: string): number {
  const a = tl.anchors[sentenceId];
  if (a) {
    const beat = tl.beats.find((b) => b.id === a.beat);
    if (!beat || beat.sentences.length === 0) return -1;
    const m = beat.sentences.length;
    return beat.sentences[Math.min(m - 1, Math.floor((a.index * m) / Math.max(1, a.count)))].from;
  }
  for (const b of tl.beats) {
    const s = b.sentences.find((x) => x.id === sentenceId);
    if (s) return s.from;
  }
  return -1;
}

// Eased camera move over a beat: t01 is the beat's progress (0..1). Smoothstep, so pans start and stop softly.
export function camera(t01: number, from: Cam, to: Cam): Cam {
  const t = Math.min(1, Math.max(0, t01));
  const e = t * t * (3 - 2 * t);
  const mix = (a: number, b: number) => a * (1 - e) + b * e;
  return {zoom: mix(from.zoom, to.zoom), x: mix(from.x, to.x), y: mix(from.y, to.y)};
}
