// Sound of the Longform composition: the voice parts at their timing starts, chapter music lowered under the voice
// (ducking.ts), and light sound effects anchored to sentences (so they follow each language's timing).
import React, {useMemo} from 'react';
import {Audio, Sequence, interpolate, staticFile} from 'remotion';
import {DUCK, speechSpans, volumeAt} from './ducking';
import {sentenceFrame} from './timeline';
import type {Timeline} from './timeline';
import type {AudioProps, ChapterInfo, ScenesDoc} from './types';

const MUSIC_FADE = 1; // seconds of fade at chapter edges

export const SoundTrack: React.FC<{tl: Timeline; audio: AudioProps; chapters: ChapterInfo[]; scenes: ScenesDoc; speech: {start: number; end: number}[]}> = ({
  tl, audio, chapters, scenes, speech,
}) => {
  const fps = tl.fps;
  const spans = useMemo(() => speechSpans(speech, DUCK.gap), [speech]);
  const beatFrom = (id: string) => tl.beats.find((b) => b.id === id)?.from;
  const starts = chapters.map((c) => c.beats.map(beatFrom).find((f) => f !== undefined)).map((f) => f ?? -1);
  const sfxFile = (id: string) => audio.sfx.find((s) => s.id === id)?.file;
  return (
    <>
      {audio.voice.map((v, i) => (
        <Sequence key={`v${i}`} from={Math.round(v.start * fps)} layout="none">
          <Audio src={staticFile(v.file)} />
        </Sequence>
      ))}
      {chapters.map((c, i) => {
        const file = audio.music[c.id];
        const from = starts[i];
        if (!file || from < 0) return null;
        const next = starts.slice(i + 1).find((f) => f >= 0) ?? tl.durationInFrames;
        const len = Math.max(1, next - from);
        const edge = MUSIC_FADE * fps;
        return (
          <Sequence key={`m${c.id}`} from={from} durationInFrames={len} layout="none">
            <Audio src={staticFile(file)} loop volume={(f) => volumeAt((from + f) / fps, speech, DUCK, spans) *
              interpolate(f, [0, edge, len - edge, len], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})} />
          </Sequence>
        );
      })}
      {Object.entries(scenes.beats).flatMap(([bid, b]) => (b.sfx ?? []).map((s, i) => {
        const file = sfxFile(s.id);
        const at = sentenceFrame(tl, s.sentence);
        if (!file || at < 0) return null;
        return (
          <Sequence key={`s${bid}${i}`} from={Math.max(0, at + Math.round((s.offset ?? 0) * fps))} layout="none">
            <Audio src={staticFile(file)} volume={s.gain} />
          </Sequence>
        );
      }))}
    </>
  );
};
