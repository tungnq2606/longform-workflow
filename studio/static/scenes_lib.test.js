import test from 'node:test';
import assert from 'node:assert/strict';
import {beatStatus, beatProblems, sfxChips, camText, renderLabel, short, sfxChoices} from './scenes_lib.js';

const audio = {music: [{id: 'open-01', mood: 'opening'}], sfx: [{id: 'oar-01', tags: ['oar', 'water']}, {id: 'sword-01', tags: ['sword']}]};

test('beatProblems', () => {
  const all = ['B01: không có tư thế x', 'B010: y', 'C01: không có nhạc z', 'B02: w'];
  assert.deepEqual(beatProblems(all, 'B01'), ['không có tư thế x']);
  assert.deepEqual(beatProblems(all, 'B03'), []);
});

test('beatStatus', () => {
  assert.deepEqual(beatStatus(['a', 'b'], true, false), {cls: 'bad', text: '2 lỗi'});
  assert.deepEqual(beatStatus([], true, false), {cls: 'ok', text: 'sẵn sàng'});
  assert.deepEqual(beatStatus([], false, false), {cls: 'todo', text: 'chưa xem trước'});
  assert.deepEqual(beatStatus([], false, true), {cls: 'todo', text: 'đang xem trước…'});
});

test('sfxChips', () => {
  const chips = sfxChips([{sentence: 's002', id: 'oar-01', offset: 0.3, gain: 0.4}, {sentence: 's003', id: 'gone-01', gain: 0.2}], audio);
  assert.deepEqual(chips, [
    {i: 0, id: 'oar-01', label: 'oar-01 · s002 +0.3s', missing: false},
    {i: 1, id: 'gone-01', label: 'gone-01 · s003', missing: true},
  ]);
  assert.deepEqual(sfxChips(undefined, audio), []);
});

test('sfxChoices groups by tag', () => {
  assert.deepEqual(sfxChoices(audio).map((c) => c.label), ['oar · oar-01', 'sword · sword-01', 'water · oar-01']);
});

test('camText', () => {
  assert.equal(camText({from: {zoom: 1, x: 0, y: 0}, to: {zoom: 1.1, x: -40, y: 0}}), 'zoom 1→1.1 · x 0→-40');
  assert.equal(camText(undefined), '—');
});

test('renderLabel', () => {
  assert.equal(renderLabel({state: 'missing_timing'}), 'chưa dò thời điểm');
  assert.equal(renderLabel({state: 'ready'}), 'Render');
  assert.equal(renderLabel({state: 'rendering'}), 'đang render…');
  assert.equal(renderLabel({state: 'done'}), 'Render lại');
  assert.equal(renderLabel({state: 'blocked'}), 'chưa render được');
});

test('short', () => {
  assert.equal(short('abc', 5), 'abc');
  assert.equal(short('abcdefgh', 5), 'abcd…');
});
