// Map projection for MapView (pure; tested with `node --test src/longform/`).
// Equirectangular with a cos(latitude) correction at the box's middle latitude, fitted inside w x h and centred.
export type LonLat = [number, number];
export type BBox = [number, number, number, number]; // [lon0, lat0, lon1, lat1]

export function project([lon, lat]: LonLat | number[], bbox: BBox, w: number, h: number): [number, number] {
  const [lon0, lat0, lon1, lat1] = bbox;
  const k = Math.cos((((lat0 + lat1) / 2) * Math.PI) / 180);
  const s = Math.min(w / ((lon1 - lon0) * k), h / (lat1 - lat0));
  const ox = (w - (lon1 - lon0) * k * s) / 2;
  const oy = (h - (lat1 - lat0) * s) / 2;
  return [ox + (lon - lon0) * k * s, oy + (lat1 - lat) * s];
}

export function pathD(points: (LonLat | number[])[], bbox: BBox, w: number, h: number, close = false): string {
  if (points.length === 0) return '';
  const d = points.map((p, i) => {
    const [x, y] = project(p, bbox, w, h);
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join('');
  return close ? `${d}Z` : d;
}
