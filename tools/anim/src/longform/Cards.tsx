// On-screen text cards: every word on screen comes from here, in the render language (never from AI images).
// Each card starts at its own frame 0 (wrap it in a <Sequence from={sentence frame}>).
// `font` is the CSS family loaded by Longform; `lines` breaks a text into lines (default: no breaking, the browser
// wraps at spaces). Japanese passes its own rule-based breaker (Plan 6).
import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {INK} from './factions';

export type LineBreaker = (text: string) => string[];
export const noBreak: LineBreaker = (t) => [t];
type Common = {font: string; lines?: LineBreaker};

const PAPER = 'rgba(246, 236, 214, 0.94)';
const RED = '#8a3b2a';

const fadeIn = (f: number, len = 10) => interpolate(f, [0, len], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
const Lines: React.FC<{text: string; lines: LineBreaker}> = ({text, lines}) => (
  <>{lines(text).map((l, i) => <div key={i}>{l}</div>)}</>
);

// A year or date, top left, with a line drawn under it.
export const DateCard: React.FC<Common & {text: string}> = ({text, font, lines = noBreak}) => {
  const f = useCurrentFrame();
  const line = interpolate(f, [6, 24], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', left: 120, top: 100, fontFamily: font, color: INK, opacity: fadeIn(f), maxWidth: 1400}}>
      <div style={{fontSize: 104, lineHeight: 1.1, textShadow: '0 0 18px rgba(246,236,214,0.9)'}}><Lines text={text} lines={lines} /></div>
      <div style={{height: 7, width: 420 * line, background: RED, marginTop: 12, borderRadius: 4}} />
    </div>
  );
};

// A person's or place's name, as a paper tag in the lower third.
export const NameLabel: React.FC<Common & {text: string; x?: number; y?: number}> = ({text, font, lines = noBreak, x = 160, y = 1150}) => {
  const f = useCurrentFrame();
  const slide = interpolate(f, [0, 12], [-40, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', left: x + slide, top: y, fontFamily: font, fontSize: 60, color: INK, opacity: fadeIn(f),
      background: PAPER, border: `5px solid ${INK}`, borderLeft: `18px solid ${RED}`, borderRadius: 10, padding: '18px 34px', maxWidth: 1500}}>
      <Lines text={text} lines={lines} />
    </div>
  );
};

// Two records that disagree, side by side ("sử nhà Trần chép…" | "sử nhà Nguyên lại ghi…").
export const TwoSourceCard: React.FC<Common & {left: string; right: string}> = ({left, right, font, lines = noBreak}) => {
  const f = useCurrentFrame();
  const panel = (text: string, delay: number): React.ReactNode => (
    <div style={{flex: 1, background: PAPER, border: `5px solid ${INK}`, borderRadius: 14, padding: '40px 48px', fontSize: 58, lineHeight: 1.25,
      opacity: fadeIn(f - delay), transform: `translateY(${interpolate(f - delay, [0, 12], [30, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}px)`}}>
      <Lines text={text} lines={lines} />
    </div>
  );
  return (
    <div style={{position: 'absolute', left: 160, right: 160, top: 860, display: 'flex', gap: 60, alignItems: 'stretch', fontFamily: font, color: INK}}>
      {panel(left, 0)}
      <div style={{alignSelf: 'center', fontSize: 90, color: RED, opacity: fadeIn(f - 8)}}>≠</div>
      {panel(right, 14)}
    </div>
  );
};

// Chapter title over a soft dark veil, centred, line drawn out from the middle.
export const ChapterCard: React.FC<Common & {title: string}> = ({title, font, lines = noBreak}) => {
  const f = useCurrentFrame();
  const line = interpolate(f, [10, 34], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', inset: 0, background: `rgba(20, 14, 8, ${0.45 * fadeIn(f, 14)})`, display: 'flex',
      flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: font}}>
      <div style={{fontSize: 132, color: '#f6ecd6', textAlign: 'center', maxWidth: 2000, lineHeight: 1.15, opacity: fadeIn(f - 4, 14)}}>
        <Lines text={title} lines={lines} />
      </div>
      <div style={{height: 8, width: 900 * line, background: '#c9773f', marginTop: 28, borderRadius: 4}} />
    </div>
  );
};
