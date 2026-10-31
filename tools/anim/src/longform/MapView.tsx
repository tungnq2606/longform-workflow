// A map drawn by code from Natural Earth (public domain, library/maps/vn_region.json): paper-tinted land, coast drawn
// on, places with labels, marching arrows on their sentence, hatched approximate areas, and the "modern map" note.
// Historical borders appear only when the scene names a fact for them (checked by tools/longform/scenes.py).
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {pathD, project} from './geo';
import type {BBox} from './geo';
import {INK} from './factions';
import {label} from './types';
import type {Labels, MapSpec} from './types';

export type MapData = {bbox: BBox; coast: number[][][]; land: number[][][]};
const W = 2560;
const H = 1440;
const SEA = '#cfd9d0';
const LAND = '#eadcbc';
const RED = '#9a3a24';

let cache: Promise<MapData> | null = null;
const loadMap = (): Promise<MapData> => {
  cache = cache ?? fetch(staticFile('library/maps/vn_region.json')).then((r) => r.json() as Promise<MapData>);
  return cache;
};

export const useMapData = (): MapData | null => {
  const [data, setData] = useState<MapData | null>(null);
  const [handle] = useState(() => delayRender('map data'));
  useEffect(() => {
    loadMap().then((d) => { setData(d); continueRender(handle); }).catch((e) => cancelRender(e));
  }, [handle]);
  return data;
};

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const MapView: React.FC<{map: MapSpec; labels: Labels; lang: string; font: string; arrowsAt: number[]}> = ({map, labels, lang, font, arrowsAt}) => {
  const data = useMapData();
  const f = useCurrentFrame();
  if (!data) return null;
  const bb = map.bbox;
  const pt = (p: number[]) => project(p, bb, W, H);
  const draw = interpolate(f, [0, 20], [0, 1], clamp);
  const note = label(labels, 'modern_map', lang);
  return (
    <AbsoluteFill style={{background: SEA}}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <defs>
          <filter id="paper"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={4} />
            <feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.36  0 0 0 0 0.22  0 0 0 0.10 0" /><feComposite in2="SourceGraphic" operator="in" /></filter>
          <pattern id="hatch" width={22} height={22} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1={0} y1={0} x2={0} y2={22} stroke={RED} strokeWidth={5} strokeOpacity={0.45} />
          </pattern>
          <marker id="head" viewBox="0 0 10 10" refX={6} refY={5} markerWidth={5} markerHeight={5} orient="auto-start-reverse">
            <path d="M0 0L10 5L0 10z" fill={RED} />
          </marker>
        </defs>
        {data.land.map((ring, i) => <path key={`l${i}`} d={pathD(ring, bb, W, H, true)} fill={LAND} />)}
        <g filter="url(#paper)">{data.land.map((ring, i) => <path key={`p${i}`} d={pathD(ring, bb, W, H, true)} fill={LAND} />)}</g>
        {data.coast.map((line, i) => (
          <path key={`c${i}`} d={pathD(line, bb, W, H)} fill="none" stroke={INK} strokeWidth={3} strokeLinejoin="round"
            pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
        ))}
        {(map.areas ?? []).map((a, i) => (
          <path key={`a${i}`} d={pathD(a.points, bb, W, H, true)} fill="url(#hatch)" opacity={interpolate(f, [10, 30], [0, 1], clamp)}
            stroke={a.type === 'border' ? RED : 'none'} strokeWidth={6} strokeDasharray={a.type === 'border' ? '24 14' : undefined} />
        ))}
        {(map.arrows ?? []).map((a, i) => {
          const at = arrowsAt[i] ?? -1;
          if (at < 0 || f < at) return null;
          const [x0, y0] = pt(a.from);
          const [x1, y1] = pt(a.to);
          const [mx, my] = [(x0 + x1) / 2 - (y1 - y0) * 0.15, (y0 + y1) / 2 + (x1 - x0) * 0.15];
          const t = interpolate(f - at, [0, 24], [0, 1], clamp);
          return (
            <path key={`r${i}`} d={`M${x0} ${y0}Q${mx} ${my} ${x1} ${y1}`} fill="none" stroke={RED} strokeWidth={12} strokeLinecap="round"
              pathLength={1} strokeDasharray={`${t} 1`} markerEnd={t > 0.95 ? 'url(#head)' : undefined} />
          );
        })}
        {(map.places ?? []).map((p, i) => {
          const [x, y] = pt([p.lon, p.lat]);
          const o = interpolate(f, [16 + i * 4, 28 + i * 4], [0, 1], clamp);
          return (
            <g key={`n${i}`} opacity={o}>
              <circle cx={x} cy={y} r={14} fill={INK} stroke="#f6ecd6" strokeWidth={5} />
              <text x={x + 26} y={y + 16} fontFamily={font} fontSize={54} fill={INK} stroke="#f6ecd6" strokeWidth={10} paintOrder="stroke">
                {label(labels, p.label_key, lang)}
              </text>
            </g>
          );
        })}
      </svg>
      {note && (
        <div style={{position: 'absolute', right: 60, bottom: 44, fontFamily: font, fontSize: 34, color: INK, opacity: 0.75,
          background: 'rgba(246,236,214,0.8)', padding: '8px 20px', borderRadius: 8}}>{note}</div>
      )}
    </AbsoluteFill>
  );
};
