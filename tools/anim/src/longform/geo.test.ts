import {test} from 'node:test';
import assert from 'node:assert/strict';
import {pathD, project} from './geo.ts';

const bbox: [number, number, number, number] = [100, 10, 110, 20];

test('project corners', () => {
  const [x0, y0] = project([100, 20], bbox, 2560, 1440);  // north-west -> top left of the drawn area
  const [x1, y1] = project([110, 10], bbox, 2560, 1440);  // south-east -> bottom right
  assert.ok(x0 < x1 && y0 < y1);
  // the box keeps its shape (cos(lat) correction) and is centred: equal margins on both sides
  const w = x1 - x0, h = y1 - y0;
  assert.ok(Math.abs(w / h - Math.cos((15 * Math.PI) / 180)) < 1e-9);
  assert.ok(Math.abs(x0 - (2560 - x1)) < 1e-6);
  assert.ok(Math.abs(y0 - (1440 - y1)) < 1e-6);
  assert.ok(y0 >= 0 && y1 <= 1440);
  const [cx, cy] = project([105, 15], bbox, 2560, 1440);
  assert.ok(Math.abs(cx - 1280) < 1e-6 && Math.abs(cy - 720) < 1e-6);
});

test('pathD', () => {
  const d = pathD([[100, 20], [110, 10]], bbox, 100, 100);
  assert.match(d, /^M[\d.]+ [\d.]+L[\d.]+ [\d.]+$/);
  assert.ok(pathD([[100, 20], [110, 10], [100, 10]], bbox, 100, 100, true).endsWith('Z'));
  assert.equal(pathD([], bbox, 100, 100), '');
});
