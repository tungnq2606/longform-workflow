import json
import math
import os
import shutil
import tempfile
import unittest

from tools.longform import mapdata


class MapdataTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d)

    def geo(self, features):
        p = os.path.join(self.d, "x.geojson")
        with open(p, "w") as f:
            json.dump({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": g} for g in features]}, f)
        return p

    def test_crop_keeps_bbox(self):
        p = self.geo([
            {"type": "LineString", "coordinates": [[95, 10], [105, 10], [110, 12], [130, 12]]},   # crosses both sides
            {"type": "MultiLineString", "coordinates": [[[0, 0], [1, 1]]]},                         # far away: dropped
            {"type": "Polygon", "coordinates": [[[98, 5], [112, 5], [112, 15], [98, 15], [98, 5]]]},  # overlaps the corner
            {"type": "MultiPolygon", "coordinates": [[[[-10, -10], [-5, -10], [-5, -5], [-10, -10]]]]},
        ])
        out = mapdata.crop(p, bbox=(100, 7, 125, 26), tolerance=0)
        self.assertEqual(out["bbox"], [100, 7, 125, 26])
        self.assertEqual(len(out["coast"]), 1)
        self.assertEqual(len(out["land"]), 1)
        for ring in out["coast"] + out["land"]:
            for lon, lat in ring:
                self.assertTrue(100 - 1e-6 <= lon <= 125 + 1e-6 and 7 - 1e-6 <= lat <= 26 + 1e-6, (lon, lat))
        coast = out["coast"][0]
        self.assertEqual(coast[0], [100, 10])     # clipped where it enters
        self.assertEqual(coast[-1], [125, 12])    # and where it leaves
        land = out["land"][0]
        xs, ys = [q[0] for q in land], [q[1] for q in land]
        self.assertEqual((min(xs), max(xs), min(ys), max(ys)), (100, 112, 7, 15))

    def test_simplify_reduces_points(self):
        line = [[100 + i * 0.01, 10 + 0.0001 * math.sin(i)] for i in range(500)] + [[106, 14]]
        out = mapdata.simplify(line, 0.01)
        self.assertLess(len(out), 10)
        self.assertEqual(out[0], line[0])
        self.assertEqual(out[-1], line[-1])
        self.assertIn([104.99, 10.0], [[round(x, 2), round(y, 2)] for x, y in out])  # the corner survives

    def test_output_small(self):
        line = [[100 + i * 0.001, 10 + (i % 7) * 0.0003] for i in range(20000)]
        p = self.geo([{"type": "LineString", "coordinates": line}])
        out = mapdata.crop(p)
        self.assertLess(len(json.dumps(out)), 400 * 1024)


if __name__ == "__main__":
    unittest.main()
