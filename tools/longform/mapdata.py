"""Map data for Remotion: Natural Earth coastline and land (public domain) cropped to one region and simplified.

  python -m tools.longform.mapdata tools/maps/vendor/ne_10m_coastline.geojson tools/maps/vendor/ne_10m_land.geojson \
      library/maps/vn_region.json

The downloads stay in tools/maps/vendor/ (gitignored, untrusted input: parsed here as JSON only); only the small
cropped file is committed. Output: {"bbox": [lon0, lat0, lon1, lat1], "coast": [[[lon, lat], ...]], "land": [...]}.
"""
import json
import os
import sys

VN_BBOX = (100, 7, 125, 26)


def _geoms(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for feat in data.get("features") or []:
        g = (feat or {}).get("geometry") or {}
        t, c = g.get("type"), g.get("coordinates")
        if t == "LineString":
            yield "line", [c]
        elif t == "MultiLineString":
            yield "line", c
        elif t == "Polygon":
            yield "poly", c
        elif t == "MultiPolygon":
            for poly in c:
                yield "poly", poly


def _clip_segment(a, b, bbox):
    """Liang–Barsky: the part of segment a-b inside bbox, or None."""
    x0, y0, x1, y1 = bbox
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                return None
            continue
        r = q / p
        if p < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return None
    return [a[0] + t0 * dx, a[1] + t0 * dy], [a[0] + t1 * dx, a[1] + t1 * dy]


def clip_line(line, bbox):
    pieces, cur = [], []
    for a, b in zip(line, line[1:]):
        seg = _clip_segment(a, b, bbox)
        if seg is None:
            if len(cur) > 1:
                pieces.append(cur)
            cur = []
            continue
        p, q = seg
        if cur and cur[-1] == p:
            cur.append(q)
        else:
            if len(cur) > 1:
                pieces.append(cur)
            cur = [p, q]
    if len(cur) > 1:
        pieces.append(cur)
    return pieces


def clip_ring(ring, bbox):
    """Sutherland–Hodgman clip of one polygon ring to the bbox rectangle."""
    x0, y0, x1, y1 = bbox
    edges = ((lambda p: p[0] >= x0, lambda a, b: _at_x(a, b, x0)), (lambda p: p[0] <= x1, lambda a, b: _at_x(a, b, x1)),
             (lambda p: p[1] >= y0, lambda a, b: _at_y(a, b, y0)), (lambda p: p[1] <= y1, lambda a, b: _at_y(a, b, y1)))
    out = [list(p) for p in ring]
    if len(out) > 1 and out[0] == out[-1]:
        out = out[:-1]
    for inside, cross in edges:
        src, out = out, []
        if not src:
            break
        prev = src[-1]
        for p in src:
            if inside(p):
                if not inside(prev):
                    out.append(cross(prev, p))
                out.append(p)
            elif inside(prev):
                out.append(cross(prev, p))
            prev = p
    return out if len(out) >= 3 else []


def _at_x(a, b, x):
    t = (x - a[0]) / (b[0] - a[0])
    return [x, a[1] + t * (b[1] - a[1])]


def _at_y(a, b, y):
    t = (y - a[1]) / (b[1] - a[1])
    return [a[0] + t * (b[0] - a[0]), y]


def _dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx == 0 and dy == 0:
        return ((p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return ((p[0] - a[0] - t * dx) ** 2 + (p[1] - a[1] - t * dy) ** 2) ** 0.5


def simplify(points, tolerance):
    """Douglas–Peucker (iterative, pure Python). Keeps the first and last point."""
    if tolerance <= 0 or len(points) < 3:
        return [list(p) for p in points]
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        best, idx = 0.0, None
        for k in range(i + 1, j):
            d = _dist(points[k], points[i], points[j])
            if d > best:
                best, idx = d, k
        if idx is not None and best > tolerance:
            keep[idx] = True
            stack += [(i, idx), (idx, j)]
    return [list(p) for p, k in zip(points, keep) if k]


def _round(points):
    return [[round(x, 3), round(y, 3)] for x, y in points]


def crop(geojson_path, bbox=VN_BBOX, tolerance=0.01, land_path=None):
    """Coast lines from geojson_path (and land polygons from it, or from land_path when given), clipped to bbox."""
    coast, land = [], []
    for path in [geojson_path] + ([land_path] if land_path else []):
        for kind, parts in _geoms(path):
            if kind == "line":
                for line in parts:
                    for piece in clip_line(line, bbox):
                        s = simplify(piece, tolerance)
                        if len(s) > 1:
                            coast.append(_round(s))
            else:
                for ring in parts[:1]:  # outer ring only: holes (lakes) are not drawn
                    c = clip_ring(ring, bbox)
                    s = simplify(c + c[:1], tolerance)[:-1] if c else []
                    if len(s) >= 3:
                        land.append(_round(s))
    return {"bbox": list(bbox), "coast": coast, "land": land}


def main(argv):
    coast_path, land_path, out = argv
    data = crop(coast_path, land_path=land_path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    print("%s: %d coast lines, %d land rings, %d KB" % (out, len(data["coast"]), len(data["land"]), os.path.getsize(out) // 1024))


if __name__ == "__main__":
    main(sys.argv[1:])
