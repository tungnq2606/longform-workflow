import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DUCK, volumeAt} from './ducking.ts';

const speech = [{start: 1, end: 3}, {start: 3.4, end: 5}, {start: 9, end: 11}];

test('low during speech', () => {
  for (const t of [1.5, 3.2, 4, 10]) assert.ok(volumeAt(t, speech, DUCK) <= 0.25, `t=${t}`);
  assert.equal(volumeAt(2, speech, DUCK), DUCK.low);
});

test('high in long gap', () => {
  assert.equal(volumeAt(7, speech, DUCK), DUCK.high);
  assert.ok(volumeAt(7, speech, DUCK) <= 0.6);
  assert.equal(volumeAt(20, speech, DUCK), DUCK.high);
  assert.equal(volumeAt(0.2, speech, DUCK), DUCK.high);
  assert.equal(volumeAt(1, [], DUCK), DUCK.high);
});

test('short gap stays low', () => {
  assert.equal(volumeAt(3.2, speech, DUCK), DUCK.low);  // 0.4 s gap < 1.5 s
});

test('no jump', () => {
  const step = 1 / 30;
  const most = ((DUCK.high - DUCK.low) * step) / DUCK.ramp + 1e-9;
  let prev = volumeAt(0, speech, DUCK);
  for (let t = step; t < 14; t += step) {
    const v = volumeAt(t, speech, DUCK);
    assert.ok(Math.abs(v - prev) <= most, `jump at ${t.toFixed(2)}: ${prev} -> ${v}`);
    prev = v;
  }
});
