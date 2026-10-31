// Pure geometry for long-form scenes (no React, tested with `node --test src/longform/`).
export type Pt = [number, number];

// Position at fraction t (0..1) of the polyline's length; zero-length segments are skipped.
export function pointAt(path: Pt[], t: number): {x: number; y: number; angle: number} {
  const segs: {a: Pt; b: Pt; len: number}[] = [];
  for (let i = 1; i < path.length; i++) {
    const len = Math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]);
    if (len > 0) segs.push({a: path[i - 1], b: path[i], len});
  }
  if (segs.length === 0) return {x: path[0]?.[0] ?? 0, y: path[0]?.[1] ?? 0, angle: 0};
  const total = segs.reduce((s, g) => s + g.len, 0);
  let d = Math.min(1, Math.max(0, t)) * total;
  for (const g of segs) {
    if (d <= g.len || g === segs[segs.length - 1]) {
      const f = Math.min(1, d / g.len);
      return {x: g.a[0] + (g.b[0] - g.a[0]) * f, y: g.a[1] + (g.b[1] - g.a[1]) * f, angle: Math.atan2(g.b[1] - g.a[1], g.b[0] - g.a[0])};
    }
    d -= g.len;
  }
  throw new Error('unreachable');
}

// Figure scale for screen height y: minS at the horizon, maxS at the ground line, clamped.
export function depthScale(y: number, horizonY: number, groundY: number, minS: number, maxS: number): number {
  const f = Math.min(1, Math.max(0, (y - horizonY) / (groundY - horizonY)));
  return minS + (maxS - minS) * f;
}
