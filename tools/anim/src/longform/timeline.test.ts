import {test} from 'node:test';
import assert from 'node:assert/strict';
import {build, camera, sentenceFrame, TAIL} from './timeline.ts';
import type {Timing} from './timeline.ts';

const scenes = {beats: {B01: {}, B02: {}}};
const vi: Timing = {lang: 'vi', duration: 10, beats: [
  {id: 'B01', start: 0.2, end: 4, sentences: [{id: 's001', start: 0.2, end: 2}, {id: 's002', start: 2.5, end: 4}]},
  {id: 'B02', start: 4.4, end: 10, sentences: [{id: 's003', start: 4.4, end: 10}]},
]};
// Same beats, rewritten in English: longer, three sentences in B01 with their own ids.
const en: Timing = {lang: 'en', duration: 16, beats: [
  {id: 'B01', start: 0, end: 9, sentences: [{id: 'e1', start: 0, end: 3}, {id: 'e2', start: 3.4, end: 6}, {id: 'e3', start: 6.4, end: 9}]},
  {id: 'B02', start: 9.4, end: 16, sentences: [{id: 'e4', start: 9.4, end: 16}]},
]};
const anchors = {s001: {beat: 'B01', index: 0, count: 2}, s002: {beat: 'B01', index: 1, count: 2}, s003: {beat: 'B02', index: 0, count: 1}};

test('beat frames follow timing', () => {
  const tl = build(scenes, vi, 30);
  assert.equal(tl.durationInFrames, 300 + TAIL);
  assert.deepEqual(tl.beats.map((b) => [b.id, b.from, b.durationInFrames]), [['B01', 0, 132], ['B02', 132, 315 - 132]]);
  assert.deepEqual(tl.beats[0].sentences.map((s) => s.from), [6, 75]);
});

test('scales with language timing', () => {
  const a = build(scenes, vi, 30, anchors);
  const b = build(scenes, en, 30, anchors);
  assert.equal(b.durationInFrames, 480 + TAIL);
  assert.equal(b.beats[1].from, 282);
  assert.ok(b.beats[0].durationInFrames > a.beats[0].durationInFrames);
  // the hero key on vi sentence s002 (2nd of 2) lands on the 2nd half of the English beat: e2 starts at 3.4 s
  assert.equal(sentenceFrame(a, 's002'), 75);
  assert.equal(sentenceFrame(b, 's002'), 102);
  assert.equal(sentenceFrame(b, 's001'), 0);
  assert.equal(sentenceFrame(b, 's003'), 282);
});

test('sentenceFrame', () => {
  const tl = build(scenes, vi, 30);
  assert.equal(sentenceFrame(tl, 's003'), 132);  // no anchors: exact id
  assert.equal(sentenceFrame(tl, 'nope'), -1);
});

test('beats without a scene are left out, the duration stays', () => {
  const tl = build({beats: {B02: {}}}, vi, 30);
  assert.deepEqual(tl.beats.map((b) => b.id), ['B02']);
  assert.equal(tl.beats[0].from, 0);
});

test('camera eases from to', () => {
  const from = {zoom: 1, x: 0, y: 0};
  const to = {zoom: 1.2, x: -100, y: 20};
  assert.deepEqual(camera(0, from, to), from);
  assert.deepEqual(camera(1, from, to), to);
  const mid = camera(0.5, from, to);
  assert.ok(Math.abs(mid.zoom - 1.1) < 1e-9);
  assert.ok(camera(0.1, from, to).zoom - 1 < 0.02 * 0.1 * 10);  // eased: slow start
});
