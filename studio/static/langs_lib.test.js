import {test} from 'node:test';
import assert from 'node:assert/strict';
import {voiceSummary, langTabState, partFileName, beatRows, copyLabel} from './langs_lib.js';

test('voiceSummary', () => {
  assert.equal(voiceSummary({parts: [], missing: [], stale: false}), 'chưa chuẩn bị phần giọng');
  assert.equal(voiceSummary({parts: [{part: '01', present: true}, {part: '02', present: false}, {part: '03', present: false}],
    missing: ['02', '03'], stale: false}), '3 phần · có 1 · thiếu 02, 03');
  assert.equal(voiceSummary({parts: [{part: '01', present: true}], missing: [], stale: false}), '1 phần · đủ giọng');
  assert.equal(voiceSummary({parts: [{part: '01', present: true}], missing: [], stale: true}), 'phần giọng cũ, chuẩn bị lại');
  assert.equal(voiceSummary(null), 'chưa chuẩn bị phần giọng');
});

test('langTabState', () => {
  assert.deepEqual(langTabState({code: 'vi', parts: {script: 'done', voice: 'todo', render: 'todo'}}, 'vi'),
    {code: 'vi', label: 'VI', source: true, state: 'doing', title: 'VI (gốc, chỉ xem) · kịch bản: xong · giọng: chưa làm · render: chưa làm'});
  assert.equal(langTabState({code: 'en', parts: {script: 'wait', voice: 'todo', render: 'todo'}}, 'vi').state, 'wait');
  assert.equal(langTabState({code: 'en', parts: {script: 'done', voice: 'done', render: 'done'}}, 'vi').state, 'done');
  assert.equal(langTabState({code: 'en', parts: {script: 'todo', voice: 'todo', render: 'todo'}}, 'vi').state, 'todo');
  assert.equal(langTabState({code: 'ja', parts: {}}, 'vi').source, false);
});

test('partFileName', () => {
  assert.equal(partFileName({part: '03', file: 'parts/03.mp3'}), '03.mp3');
  assert.equal(partFileName({part: '07'}), '07.mp3');
});

test('beatRows pairs the outline with the language sentences and their report rows', () => {
  const outline = [{beat: 'B01', goal: 'hook', facts: ['F001'], chapter: 'C01'}, {beat: 'B02', goal: 'g', facts: [], chapter: 'C01'}];
  const script = {chapters: [{id: 'C01', title: 'T', beats: [{id: 'B01', sentences: [{id: 's001', text: 'Hi', facts: []}]}]}]};
  const report = {sentences: [{id: 's001', beat: 'B01', colour: 'yellow', reasons: ['x']}]};
  const rows = beatRows(outline, script, report, {s001: ['glossary']}, [{sentence: 's001', issue: 'i', back_translation_vi: 'b'}]);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].beat, 'B01');
  assert.deepEqual(rows[0].sentences[0], {id: 's001', text: 'Hi', facts: [], colour: 'yellow', reasons: ['x'],
    flag: {sentence: 's001', issue: 'i', back_translation_vi: 'b'}});
  assert.deepEqual(rows[1].sentences, []);
  assert.deepEqual(beatRows(null, script, report, {}, []).map((r) => r.beat), ['B01']);
});

test('copyLabel', () => {
  assert.equal(copyLabel(false), 'Copy');
  assert.equal(copyLabel(true), 'Đã copy ✓');
});
