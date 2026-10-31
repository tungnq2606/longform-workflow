// Scene pieces (same drawings as tools/kit/scene_kit.py), with optional motion.
// Pieces that animate take `at` (frame inside the beat where their motion starts).
import React from 'react';
import {Easing, interpolate, useCurrentFrame} from 'remotion';
import {Circle, Line, Poly, Rect, T, useProgress, useSpring} from './draw';
import {Figure} from './Figure';
import {PROP_SVG} from './propsSvg';
import {ACC, ACC_L, GOLD, GREEN, GREY, INK, SKY, WHITE} from './theme';

type Pt = [number, number];

export const Ground: React.FC<{y?: number; c?: string}> = ({y = 930, c = SKY}) => <Line x1={40} y1={y} x2={1880} y2={y} w={5} c={c} />;

/** One prop icon (house, car, cash, ...), drawn around (x, y). */
/** `swap` recolours the icon, e.g. ['#FBD9C6', ACC] paints a house roof full orange. */
export const Prop: React.FC<{name: string; x: number; y: number; s?: number; label?: string; arg?: string | number; rot?: number; swap?: [string, string]}> = ({name, x, y, s = 1, label, arg, rot = 0, swap}) => {
  let body: React.ReactNode;
  if (name === 'calendar') body = <Calendar label={String(arg ?? '2026')} />;
  else if (name === 'pie') body = <PieIcon share={Number(arg ?? 30)} />;
  else body = <g dangerouslySetInnerHTML={{__html: swap ? PROP_SVG[name].split(swap[0]).join(swap[1]) : PROP_SVG[name]}} />;
  return (
    <>
      <g transform={`translate(${x},${y}) rotate(${rot}) scale(${s})`}>{body}</g>
      {label && <T x={x} y={y + 125 * s} size={28} fill={GREY}>{label}</T>}
    </>
  );
};
const Calendar: React.FC<{label: string}> = ({label}) => (
  <>
    <Rect x={-60} y={-55} w={120} h={115} fill={WHITE} sw={7} r={8} />
    <Rect x={-60} y={-55} w={120} h={30} fill={ACC} sw={7} r={8} />
    <Line x1={-30} y1={-70} x2={-30} y2={-45} w={7} />
    <Line x1={30} y1={-70} x2={30} y2={-45} w={7} />
    <T x={0} y={30} size={36} bold>{label}</T>
  </>
);
const PieIcon: React.FC<{share: number}> = ({share}) => {
  const a = (share / 100) * 2 * Math.PI;
  return (
    <>
      <Circle cx={0} cy={0} r={70} />
      <path d={`M0 0 L0 -70 A70 70 0 ${share > 50 ? 1 : 0} 1 ${(70 * Math.sin(a)).toFixed(1)} ${(-70 * Math.cos(a)).toFixed(1)} Z`} fill={ACC} stroke={INK} strokeWidth={6} />
    </>
  );
};

/** Speech or thought bubble; text lines split by "|". Pops out of its tail at `at`. */
export const Bubble: React.FC<{x: number; y: number; w: number; h: number; text: string; size?: number; think?: boolean; tail?: 'left' | 'right'; at?: number; children?: React.ReactNode}> = ({x, y, w, h, text, size = 38, think = false, tail = 'left', at = 0, children}) => {
  const p = useSpring(at, 11);
  const f = useCurrentFrame();
  if (f < at) return null;
  const tx = tail === 'left' ? x + 70 : x + w - 70;
  const d = tail === 'left' ? -1 : 1;
  const lines = text ? text.split('|') : [];
  const y0 = y + h / 2 - ((lines.length - 1) * (size + 10)) / 2 + size * 0.35;
  return (
    <g transform={`translate(${tx},${y + h}) scale(${p}) translate(${-tx},${-(y + h)})`}>
      <Rect x={x} y={y} w={w} h={h} fill={WHITE} sw={6} r={40} />
      {think ? (
        <>
          <circle cx={tx} cy={y + h + 32} r={17} fill="#fff" stroke={INK} strokeWidth={5} />
          <circle cx={tail === 'left' ? tx - 28 : tx + 28} cy={y + h + 68} r={10} fill="#fff" stroke={INK} strokeWidth={5} />
        </>
      ) : (
        <Poly pts={[[tx - 25, y + h - 3], [tx + d * 35, y + h + 55], [tx + 25, y + h - 3]]} w={6} fill={WHITE} />
      )}
      {lines.map((t, i) => <T key={i} x={x + w / 2} y={y0 + i * (size + 10)} size={size}>{t}</T>)}
      {children}
    </g>
  );
};

/** Thought bubble with icons that pop in one after another. */
export const ThinkIcons: React.FC<{x: number; y: number; w: number; h: number; icons: string[]; at?: number; every?: number}> = ({x, y, w, h, icons, at = 0, every = 6}) => {
  const step = w / (icons.length + 1);
  return (
    <Bubble x={x} y={y} w={w} h={h} text="" think at={at}>
      {icons.map((n, i) => <PopAt key={n} at={at + 8 + i * every} x={x + step * (i + 1)} y={y + h / 2 + 5}><Prop name={n} x={x + step * (i + 1)} y={y + h / 2 + 5} s={0.62} /></PopAt>)}
    </Bubble>
  );
};
const PopAt: React.FC<{at: number; x: number; y: number; children: React.ReactNode}> = ({at, x, y, children}) => {
  const p = useSpring(at, 10);
  if (useCurrentFrame() < at) return null;
  return <g transform={`translate(${x},${y}) scale(${p}) translate(${-x},${-y})`}>{children}</g>;
};

export const Big: React.FC<{x: number; y: number; children: React.ReactNode; size?: number; fill?: string}> = ({x, y, children, size = 110, fill = ACC}) => <T x={x} y={y} size={size} fill={fill} bold>{children}</T>;

/** Sticky note, lines split by "|". */
export const Note: React.FC<{x: number; y: number; text: string; w?: number; rot?: number; size?: number}> = ({x, y, text, w = 330, rot = -3, size = 30}) => {
  const lines = text.split('|');
  const h = 40 + lines.length * (size + 10);
  return (
    <g transform={`rotate(${rot} ${x} ${y})`}>
      <Rect x={x - w / 2} y={y - h / 2} w={w} h={h} fill="#fff3b0" sw={4} r={4} />
      {lines.map((t, i) => <T key={i} x={x} y={y - h / 2 + 30 + size * 0.8 + i * (size + 10)} size={size}>{t}</T>)}
    </g>
  );
};

/** Rubber stamp; slams down at `at` (if given). */
export const Stamp: React.FC<{x: number; y: number; text: string; rot?: number; size?: number; c?: string; at?: number}> = ({x, y, text, rot = -10, size = 52, c = ACC, at}) => {
  const f = useCurrentFrame();
  const p = useSpring(at ?? -100, 9);
  if (at !== undefined && f < at) return null;
  const k = at === undefined ? 1 : 2.4 - 1.4 * p;
  const w = text.length * size * 0.62 + 50;
  return (
    <g transform={`translate(${x},${y}) scale(${k}) rotate(${rot}) translate(${-x},${-y})`} opacity={Math.min(1, p * 2)}>
      <Rect x={x - w / 2} y={y - size * 0.9} w={w} h={size * 1.4} c={c} sw={7} r={8} />
      <T x={x} y={y + size * 0.3} size={size} fill={c} bold>{text}</T>
    </g>
  );
};

export const Check: React.FC<{x: number; y: number; w?: number; h?: number; amount?: React.ReactNode; sub?: string}> = ({x, y, w = 620, h = 260, amount = '$60,320', sub = 'a year, before tax'}) => (
  <>
    <Rect x={x} y={y} w={w} h={h} fill={GREEN} sw={7} r={12} />
    <T x={x + 30} y={y + 55} size={30} anchor="start" fill={GREY}>PAY TO: our median worker</T>
    {typeof amount === 'string' ? <T x={x + w / 2} y={y + 150} size={84} bold>{amount}</T> : amount}
    <T x={x + w / 2} y={y + 210} size={32} fill={GREY}>{sub}</T>
    <Line x1={x + 30} y1={y + h - 30} x2={x + w - 30} y2={y + h - 30} w={3} c={GREY} />
  </>
);

export const Bill: React.FC<{x: number; y: number; w?: number; h?: number; title?: string; amount?: React.ReactNode; sub?: string}> = ({x, y, w = 420, h = 300, title = 'RENT + UTILITIES', amount = '$1,487', sub = 'a month (2024 median)'}) => (
  <>
    <Rect x={x} y={y} w={w} h={h} fill={WHITE} sw={7} r={10} />
    <Rect x={x} y={y} w={w} h={60} fill={ACC} sw={7} r={10} />
    <T x={x + w / 2} y={y + 42} size={32} fill="#fff" bold>{title}</T>
    {typeof amount === 'string' ? <T x={x + w / 2} y={y + 170} size={76} bold>{amount}</T> : amount}
    <T x={x + w / 2} y={y + 230} size={28} fill={GREY}>{sub}</T>
  </>
);

/** Paycheck strip; the cut slices grow from the right end starting at `at`. */
export const Strip: React.FC<{x: number; y: number; w: number; cuts: [number, string, string][]; label: string; amount: string; h?: number; at?: number}> = ({x, y, w, cuts, label, amount, h = 150, at}) => {
  const p = useProgress(at ?? -100, 16, Easing.out(Easing.cubic));
  let right = x + w;
  return (
    <>
      <Rect x={x} y={y} w={w} h={h} fill={GREEN} sw={7} r={10} />
      <T x={x + 30} y={y + 55} size={30} anchor="start" fill={GREY}>{label}</T>
      <T x={x + 30} y={y + 115} size={48} anchor="start" bold>{amount}</T>
      {cuts.map(([share, col, t], i) => {
        const cw = w * share * p;
        right -= w * share;
        const rx = right + w * share - cw;
        const parts = t.split('|');
        return (
          <g key={i}>
            {cw > 1 && <Rect x={rx} y={y} w={cw} h={h} fill={col} c={ACC} sw={6} r={8} />}
            {cw > 1 && <Line x1={rx} y1={y - 30} x2={rx} y2={y + h + 30} w={5} dash="12 9" />}
            {p > 0.6 && parts.map((pt, k) => {
              // wide slice: label inside; narrow slice: label below, staggered so neighbours do not collide
              const narrow = w * share < 220;
              const ly = narrow
                ? y + h + 55 + k * 36 + (cuts.length > 1 && (right - x) / w > 0.9 ? 90 : 0)
                : y + h / 2 + 12 + (k - (parts.length - 1) / 2) * 36;
              return <T key={k} x={rx + cw / 2} y={ly} size={30} fill={ACC} bold opacity={(p - 0.6) / 0.4}>{pt}</T>;
            })}
          </g>
        );
      })}
    </>
  );
};

/** Scissors; snip open/close while `at` <= frame < `at + dur`. */
export const Scissors: React.FC<{x: number; y: number; s?: number; at?: number; dur?: number}> = ({x, y, s = 1, at = -100, dur = 16}) => {
  const f = useCurrentFrame();
  const k = f - at;
  const snip = k >= 0 && k < dur ? Math.abs(Math.sin(k * 0.6)) * 14 : 0;
  return (
    <g transform={`translate(${x},${y}) scale(${s}) rotate(-20)`}>
      <g transform={`rotate(${-snip} -22 0)`}>
        <circle cx={-40} cy={30} r={22} fill="none" stroke={INK} strokeWidth={7} />
        <Line x1={-22} y1={20} x2={70} y2={-18} w={7} />
      </g>
      <g transform={`rotate(${snip} -22 0)`}>
        <circle cx={-40} cy={-30} r={22} fill="none" stroke={INK} strokeWidth={7} />
        <Line x1={-22} y1={-20} x2={70} y2={18} w={7} />
      </g>
    </g>
  );
};

/** Year track for races; `shade` = [i, j] marks a stretch. Shade wipes in at `shadeAt`. */
export const Track: React.FC<{years?: string[]; shade?: [number, number]; y?: number; shadeAt?: number}> = ({years = ['2019', '2022', '2024', '2026'], shade, y = 900, shadeAt}) => {
  const p = useProgress(shadeAt ?? -100, 14);
  const xs = years.map((_, k) => 220 + k * 500);
  return (
    <>
      <Ground y={y} />
      {shade && <rect x={xs[shade[0]]} y={y - 380} width={(xs[shade[1]] - xs[shade[0]]) * p} height={380} fill={ACC_L} opacity={0.65} />}
      {xs.map((x, k) => (
        <g key={k}>
          <Line x1={x} y1={y - 20} x2={x} y2={y + 20} w={6} />
          <T x={x} y={y + 62} size={34} fill={GREY}>{years[k]}</T>
        </g>
      ))}
    </>
  );
};

export const Pie: React.FC<{x: number; y: number; r: number; shares: number[]; labels?: string[]; at?: number}> = ({x, y, r, shares, labels, at}) => {
  const p = useProgress(at ?? -100, 20, Easing.out(Easing.cubic));
  const cols = [ACC, '#f2a679', GOLD, '#a8cfa0'];
  let a0 = 0;
  return (
    <>
      <Circle cx={x} cy={y} r={r} />
      {shares.map((sh, i) => {
        const a1 = a0 + (sh / 100) * 2 * Math.PI * p;
        const d = `M${x} ${y} L${(x + r * Math.sin(a0)).toFixed(1)} ${(y - r * Math.cos(a0)).toFixed(1)} A${r} ${r} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${(x + r * Math.sin(a1)).toFixed(1)} ${(y - r * Math.cos(a1)).toFixed(1)} Z`;
        const am = (a0 + a1) / 2;
        const el = (
          <g key={i}>
            <path d={d} fill={cols[i % 4]} stroke={INK} strokeWidth={6} />
            {labels && p > 0.9 && <T x={x + (r + 70) * Math.sin(am)} y={y - (r + 70) * Math.cos(am) + 12} size={32} bold>{labels[i]}</T>}
          </g>
        );
        a0 = a1;
        return el;
      })}
    </>
  );
};

/** Two-way signpost; arms swing in at `at`. */
export const Signpost: React.FC<{x: number; y: number; a: string; b: string; at?: number}> = ({x, y, a, b, at}) => {
  const p1 = useSpring(at ?? -100, 10);
  const p2 = useSpring((at ?? -100) + 8, 10);
  return (
    <>
      <Line x1={x} y1={y} x2={x} y2={y + 330} w={9} />
      <g transform={`translate(${x},${y + 55}) scale(${p1},1) translate(${-x},${-(y + 55)})`}>
        <Poly pts={[[x - 10, y + 10], [x + 430, y + 10], [x + 480, y + 55], [x + 430, y + 100], [x - 10, y + 100]]} w={7} fill={WHITE} />
        <T x={x + 220} y={y + 70} size={34} bold>{a}</T>
      </g>
      <g transform={`translate(${x},${y + 185}) scale(${p2},1) translate(${-x},${-(y + 185)})`}>
        <Poly pts={[[x + 10, y + 140], [x - 430, y + 140], [x - 480, y + 185], [x - 430, y + 230], [x + 10, y + 230]]} w={7} fill={ACC_L} />
        <T x={x - 220} y={y + 200} size={34} bold>{b}</T>
      </g>
    </>
  );
};

export const Chalkboard: React.FC<{x: number; y: number; w: number; h: number; text: string; size?: number}> = ({x, y, w, h, text, size = 60}) => (
  <>
    <Rect x={x} y={y} w={w} h={h} fill="#2f4a3a" c="#6b4f2c" sw={14} r={6} />
    <T x={x + w / 2} y={y + h / 2 + size * 0.35} size={size} fill="#f4f1e6" bold>{text}</T>
    <Line x1={x + 40} y1={y + h + 10} x2={x + w - 40} y2={y + h + 10} w={6} c="#6b4f2c" />
  </>
);

export const Gavel: React.FC<{x: number; y: number; s?: number; at?: number}> = ({x, y, s = 1, at}) => {
  const f = useCurrentFrame();
  const k = f - (at ?? -100);
  const swing = at !== undefined && k >= 0 && k < 18 ? -40 * Math.abs(Math.sin(k * 0.35)) : 0;
  return (
    <g transform={`translate(${x},${y}) scale(${s}) rotate(${-30 + swing})`}>
      <Rect x={-60} y={-30} w={120} h={60} fill="#c79a4a" sw={6} r={8} />
      <Rect x={-8} y={30} w={16} h={120} fill="#c79a4a" sw={5} r={4} />
    </g>
  );
};

export const Table: React.FC<{x: number; y: number; w: number}> = ({x, y, w}) => (
  <>
    <Rect x={x} y={y} w={w} h={24} fill="#c79a4a" sw={6} r={4} />
    <Line x1={x + 30} y1={y + 24} x2={x + 30} y2={y + 150} w={7} />
    <Line x1={x + w - 30} y1={y + 24} x2={x + w - 30} y2={y + 150} w={7} />
  </>
);

export const Stairs: React.FC<{x: number; y: number; n?: number; step?: number; rise?: number}> = ({x, y, n = 3, step = 140, rise = 80}) => {
  const pts: Pt[] = [[x, y]];
  for (let k = 0; k < n; k++) pts.push([x + k * step, y - (k + 1) * rise], [x + (k + 1) * step, y - (k + 1) * rise]);
  pts.push([x + n * step, y]);
  return <Poly pts={pts} w={7} fill={WHITE} />;
};

/** Tightrope between two poles; the rope sags a little and sways. */
export const Tightrope: React.FC<{x0: number; x1: number; y: number; label: string}> = ({x0, x1, y, label}) => {
  const f = useCurrentFrame();
  const sag = 10 + Math.sin(f / 9) * 4;
  return (
    <>
      <Line x1={x0} y1={y - 220} x2={x0} y2={y + 160} w={9} />
      <Line x1={x1} y1={y - 220} x2={x1} y2={y + 160} w={9} />
      <path d={`M${x0} ${y - 200} Q${(x0 + x1) / 2} ${y - 200 + sag * 2} ${x1} ${y - 200}`} fill="none" stroke={INK} strokeWidth={5} />
      <T x={x1 + 20} y={y - 210} size={34} anchor="start" fill={ACC} bold>{label}</T>
    </>
  );
};

/** Line chart; lines draw left to right from `at`. series = [{year: value}] */
export const LineChart: React.FC<{series: Record<number, number>[]; x0: number; y0: number; w: number; h: number; ymin: number; ymax: number; years: number[]; colors: string[]; labels: string[]; shade?: [number, number]; at?: number; dur?: number; fmt?: (v: number) => string}> = ({series, x0, y0, w, h, ymin, ymax, years, colors, labels, shade, at, dur = 40, fmt = (v) => v.toFixed(0)}) => {
  const p = useProgress(at ?? -100, dur, Easing.inOut(Easing.quad));
  const xs = (yr: number) => x0 + (w * (yr - years[0])) / (years[years.length - 1] - years[0]);
  const ys = (v: number) => y0 + h - (h * (v - ymin)) / (ymax - ymin);
  const ticks: number[] = [];
  for (let t = ymin; t <= ymax; t += (ymax - ymin) / 4) ticks.push(t);
  const cut = x0 + w * p;
  return (
    <>
      {shade && <rect x={xs(shade[0])} y={y0} width={xs(shade[1]) - xs(shade[0])} height={h} fill={ACC_L} opacity={0.8} />}
      <Line x1={x0} y1={y0 + h} x2={x0 + w} y2={y0 + h} w={6} />
      <Line x1={x0} y1={y0} x2={x0} y2={y0 + h} w={6} />
      {years.map((yr) => <T key={yr} x={xs(yr)} y={y0 + h + 40} size={28} fill={GREY}>{yr}</T>)}
      {ticks.map((t) => (
        <g key={t}>
          <Line x1={x0 - 8} y1={ys(t)} x2={x0} y2={ys(t)} w={4} />
          <T x={x0 - 16} y={ys(t) + 10} size={26} anchor="end" fill={GREY}>{fmt(t)}</T>
        </g>
      ))}
      {series.map((s, i) => {
        const pts: Pt[] = years.filter((yr) => yr in s).map((yr) => [xs(yr), ys(s[yr])]);
        const shown = pts.filter((q) => q[0] <= cut + 0.5);
        const last = pts[pts.length - 1];
        return (
          <g key={i}>
            <Poly pts={pts} c={colors[i]} w={9} draw={p} />
            {shown.map((q, k) => <circle key={k} cx={q[0]} cy={q[1]} r={8} fill={colors[i]} />)}
            {p > 0.98 && <T x={last[0] + 18} y={last[1] + 8} size={30} anchor="start" fill={colors[i]} bold>{labels[i]}</T>}
          </g>
        );
      })}
    </>
  );
};

/** Row of small figures (a population); `mark` puts the "median" tag under one of them. */
export const CrowdLine: React.FC<{x: number; y: number; heights: number[]; gap?: number; mark?: number; at?: number}> = ({x, y, heights, gap = 110, mark, at = 0}) => (
  <>
    {heights.map((hgt, i) => {
      const s = 0.32 + hgt * 0.06;
      return <Figure key={i} x={x + i * gap} y={y - 120 * s} s={s} seed={i + 3} />;
    })}
    {mark !== undefined && (
      <>
        <Line x1={x + mark * gap} y1={y + 30} x2={x + mark * gap} y2={y + 90} w={6} c={ACC} />
        <T x={x + mark * gap} y={y + 130} size={32} fill={ACC} bold>median</T>
      </>
    )}
  </>
);

/** Chapter card shown in silence before a voice block. The figure presents, the title writes on. */
export const Card: React.FC<{index: number; title: string}> = ({index, title}) => {
  const f = useCurrentFrame();
  const size = Math.min(92, Math.floor(1050 / (title.length * 0.56)));
  const ul = interpolate(f, [8, 26], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const shown = Math.ceil(title.length * interpolate(f, [4, 22], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  return (
    <>
      <Ground y={930} />
      <Figure x={380} y={470} s={1.4} pose="neutral" brows="raise" eyes="right" mouth="smirk" keys={[{at: 2, pose: 'present'}]} />
      <T x={760} y={470} size={44} anchor="start" fill={GREY}>{`Part ${index}`}</T>
      <T x={760} y={570} size={size} anchor="start" bold>{title.slice(0, shown)}</T>
      <Line x1={760} y1={600} x2={760 + Math.min(1060, title.length * size * 0.56) * ul} y2={600} w={10} c={ACC} />
    </>
  );
};
