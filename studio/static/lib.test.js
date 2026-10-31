import test from 'node:test';
import assert from 'node:assert/strict';
import {route, stateIcon, kindIcon, progressBar, jobLine, runState, pauseButton, nextTheme, clock} from './lib.js';

test('route', () => {
  assert.deepEqual(route(''), {screen: 'home'});
  assert.deepEqual(route('#/'), {screen: 'home'});
  assert.deepEqual(route('#/p/001-x'), {screen: 'project', id: '001-x', tab: 'overview'});
  assert.deepEqual(route('#/p/001-x/images'), {screen: 'project', id: '001-x', tab: 'images'});
  assert.deepEqual(route('#/p/001-x/nope'), {screen: 'project', id: '001-x', tab: 'overview'});
  assert.deepEqual(route('#/library'), {screen: 'library'});
  assert.deepEqual(route('#/p/../etc'), {screen: 'home'});
  assert.deepEqual(route('#/whatever'), {screen: 'home'});
});

test('stateIcon', () => {
  assert.equal(stateIcon('todo'), '⬜');
  assert.equal(stateIcon('doing'), '▶');
  assert.equal(stateIcon('wait'), '❓');
  assert.equal(stateIcon('done'), '✅');
});

test('kindIcon', () => {
  assert.equal(kindIcon('job_failed'), '❌');
  assert.equal(kindIcon('job_interrupted'), '⚠️');
  assert.equal(kindIcon('image_review'), '🖼️');
  assert.equal(kindIcon('script_approve'), '✍️');
  assert.equal(kindIcon('missing_voice'), '🎙️');
  assert.equal(kindIcon('name_pronunciation'), '🔤');
  assert.equal(kindIcon('something_new'), '🔔');
});

test('progressBar', () => {
  assert.equal(progressBar(3, 7), '▓▓▓░░░░');
  assert.equal(progressBar(0, 7), '░░░░░░░');
  assert.equal(progressBar(7, 7), '▓▓▓▓▓▓▓');
  assert.equal(progressBar(1, 2, 4), '▓▓░░');
});

test('jobLine', () => {
  const words = {queued: 'chờ', running: 'đang chạy', done: 'xong', failed: 'hỏng', stopped: 'đã dừng', interrupted: 'bị ngắt'};
  for (const [status, vi] of Object.entries(words)) {
    const line = jobLine({label: 'Claude: x', status});
    assert.ok(line.endsWith(`Claude: x · ${vi}`), line);
  }
});

test('runState', () => {
  const j = (status) => ({status});
  assert.equal(runState(false, []), '⚪ Rảnh: không có job nào');
  assert.equal(runState(false, [j('running'), j('done')]), '▶ 1 job đang chạy');
  assert.equal(runState(false, [j('running'), j('queued'), j('queued')]), '▶ 1 job đang chạy · 2 job chờ');
  assert.equal(runState(true, []), '🟡 Tạm dừng');
  assert.equal(runState(true, [j('running'), j('queued')]), '🟡 Tạm dừng · 1 job làm nốt · 1 job chờ');
});

test('nextTheme cycles auto → dark → light → auto', () => {
  assert.equal(nextTheme(''), 'dark');
  assert.equal(nextTheme('dark'), 'light');
  assert.equal(nextTheme('light'), '');
  assert.equal(nextTheme('weird'), 'dark');
});

test('clock', () => {
  assert.equal(clock('2026-10-31T21:36:05'), '21:36');
  assert.equal(clock(null), '');
});

test('pauseButton hidden when idle', () => {
  const j = (status) => ({status});
  assert.equal(pauseButton(false, []), null);
  assert.equal(pauseButton(false, [j('done'), j('failed')]), null);
  assert.equal(pauseButton(false, [j('queued')]), 'Tạm dừng');
  assert.equal(pauseButton(false, [j('running')]), 'Tạm dừng');
  assert.equal(pauseButton(true, []), 'Chạy tiếp');
});
