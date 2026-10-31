// Music ducking: chapter music sits low under the voice and comes back up in long pauses, with soft ramps.
// Pure function of time (seconds) so Remotion's per-frame `volume` callback can call it.

export type Span = {start: number; end: number};
export type DuckOpts = {low: number; high: number; ramp: number; gap: number};
export const DUCK: DuckOpts = {low: 0.22, high: 0.55, ramp: 0.3, gap: 1.5};

// Speech spans with short pauses (< gap) merged in, so the music does not pump between sentences.
export function speechSpans(sentences: Span[], gap: number): Span[] {
  const sorted = [...sentences].sort((a, b) => a.start - b.start);
  const out: Span[] = [];
  for (const s of sorted) {
    const last = out[out.length - 1];
    if (last && s.start - last.end < gap) last.end = Math.max(last.end, s.end);
    else out.push({start: s.start, end: s.end});
  }
  return out;
}

export function volumeAt(t: number, sentences: Span[], opts: DuckOpts = DUCK, spans?: Span[]): number {
  const merged = spans ?? speechSpans(sentences, opts.gap);
  let dist = Infinity;
  for (const s of merged) {
    if (t >= s.start && t <= s.end) return opts.low;
    dist = Math.min(dist, t < s.start ? s.start - t : t - s.end);
  }
  return opts.low + (opts.high - opts.low) * Math.min(1, dist / opts.ramp);
}
