import {test} from 'node:test';
import assert from 'node:assert/strict';
import {CLOSING, OPENING, fitTitle, lines, wordLines} from './jabreak.ts';

const TEXTS = [
  'あいうえお、かきくけこ。さしすせそ',
  'あいうえ「かきくけこ」さしすせそ！たちつてと？',
  'チャン・フン・ダオはなぜ勝ったのか？バクダン川の秘密',
  '元朝の大艦隊、「白藤江」に沈む。',
  'ーーーーー。。。」」',
];

test('no line starts with closing punctuation', () => {
  for (const t of TEXTS) {
    for (const max of [2, 3, 4, 5, 6, 8]) {
      const out = lines(t, max);
      assert.equal(out.join(''), t.replace(/\s+/g, ''), `${t} @${max}`);
      out.slice(1).forEach((l) => assert.ok(!CLOSING.has(l[0]), `"${l}" starts with closing (${t} @${max})`));
    }
  }
});

test('no line ends with opening bracket', () => {
  for (const t of [...TEXTS, 'あいうえ「かきくけこ」', 'あ「「「「かき']) {
    for (const max of [2, 3, 4, 5, 6]) {
      const out = lines(t, max);
      out.forEach((l) => assert.ok(!OPENING.has(l[l.length - 1]) || out.length === 1, `"${l}" ends with opening (${t} @${max})`));
    }
  }
  assert.deepEqual(lines('あいうえ「かきくけこ」', 5), ['あいうえ', '「かきくけ', 'こ」']);
});

test('latin words not split', () => {
  const out = lines('これはRemotionで作るAI動画です', 4);
  assert.ok(out.some((l) => l.includes('Remotion')), out.join('|'));
  assert.ok(out.some((l) => l.includes('AI')), out.join('|'));
  assert.equal(out.join(''), 'これはRemotionで作るAI動画です');
});

test('breaks between characters within the width', () => {
  assert.deepEqual(lines('あいうえおかきくけこ', 5), ['あいうえお', 'かきくけこ']);
  assert.deepEqual(lines('', 5), []);
});

test('word lines break at spaces', () => {
  assert.deepEqual(wordLines('How Vietnam beat the Mongol fleet', 12), ['How Vietnam', 'beat the', 'Mongol fleet']);
});

test('fitTitle shrinks long titles to two lines', () => {
  const short = fitTitle('バクダン川の戦い', 'ja', 2, 10);
  assert.deepEqual(short.lines, ['バクダン川の戦い']);
  assert.equal(short.maxChars, 10);
  const long = fitTitle('チャン・フン・ダオはなぜ元朝の大艦隊に勝てたのか？バクダン川に隠された杭の秘密', 'ja', 2, 10);
  assert.ok(long.lines.length <= 2);
  assert.ok(long.maxChars > 10);
  long.lines.slice(1).forEach((l) => assert.ok(!CLOSING.has(l[0])));
  const en = fitTitle('How Vietnam Beat the Mongol Fleet Twice With Wooden Stakes', 'en', 2, 16);
  assert.ok(en.lines.length <= 2);
});
