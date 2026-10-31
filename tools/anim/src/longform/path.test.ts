import {test} from 'node:test';
import assert from 'node:assert/strict';
import {depthScale, pointAt} from './path.ts';

test('midpoint of straight line', () => {
  const p = pointAt([[0, 0], [100, 0]], 0.5);
  assert.equal(p.x, 50);
  assert.equal(p.y, 0);
});
test('arc length across uneven segments', () => {
  const p = pointAt([[0, 0], [10, 0], [10, 30]], 0.5);
  assert.deepEqual([p.x, p.y], [10, 10]);
});
test('zero-length segment', () => {
  const p = pointAt([[0, 0], [0, 0], [0, 40]], 0.25);
  assert.ok(Number.isFinite(p.y));
  assert.equal(p.y, 10);
});
test('t clamped', () => {
  assert.equal(pointAt([[0, 0], [10, 0]], 2).x, 10);
  assert.equal(pointAt([[0, 0], [10, 0]], -1).x, 0);
});
test('angle follows the segment', () => {
  assert.equal(pointAt([[0, 0], [0, 10]], 0.5).angle, Math.PI / 2);
});
test('clamp above horizon and below ground', () => {
  assert.equal(depthScale(100, 300, 1400, 0.12, 1), 0.12);
  assert.equal(depthScale(1500, 300, 1400, 0.12, 1), 1);
  assert.ok(Math.abs(depthScale(850, 300, 1400, 0.2, 1) - 0.6) < 1e-9);
});
