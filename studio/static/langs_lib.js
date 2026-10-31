// Pure helpers for the languages tab (Plan 6), tested with `node --test studio/static/`.

const PART_VI = {script: 'kịch bản', voice: 'giọng', render: 'render'};
const STATE_VI = {todo: 'chưa làm', doing: 'đang làm', wait: 'chờ bạn', done: 'xong'};

export function voiceSummary(v) {
  if (!v || !v.parts || !v.parts.length) return 'chưa chuẩn bị phần giọng';
  if (v.stale) return 'phần giọng cũ, chuẩn bị lại';
  const n = v.parts.length, have = v.parts.filter((p) => p.present).length;
  if (!v.missing.length) return `${n} phần · đủ giọng`;
  return `${n} phần · có ${have} · thiếu ${v.missing.join(', ')}`;
}

// One language tab: its label, whether it is the read-only source, and one state for its dot
// (wait if anything waits for the owner, done when all parts are done, todo when nothing started).
export function langTabState(l, sourceCode) {
  const states = Object.values(l.parts || {});
  let state = 'doing';
  if (states.includes('wait')) state = 'wait';
  else if (states.length && states.every((s) => s === 'done')) state = 'done';
  else if (!states.length || states.every((s) => s === 'todo')) state = 'todo';
  const source = l.code === sourceCode;
  const label = l.code.toUpperCase();
  const title = [label + (source ? ' (gốc, chỉ xem)' : ''),
    ...Object.entries(l.parts || {}).map(([k, v]) => `${PART_VI[k] || k}: ${STATE_VI[v] || v}`)].join(' · ');
  return {code: l.code, label, source, state, title};
}

export const partFileName = (p) => (p.file ? p.file.split('/').pop() : `${p.part}.mp3`);

// Beat by beat: the outline (goal + fact ids) on the left, that language's sentences with colour, reasons and flags.
export function beatRows(outline, script, report, perSentence, flags) {
  const rep = Object.fromEntries(((report && report.sentences) || []).map((r) => [r.id, r]));
  const flagOf = Object.fromEntries((flags || []).map((f) => [f.sentence, f]));
  const sentences = {};
  for (const ch of (script && script.chapters) || []) {
    for (const b of ch.beats || []) sentences[b.id] = b.sentences || [];
  }
  const beats = outline || Object.keys(sentences).map((id) => ({beat: id, goal: '', facts: [], chapter: ''}));
  return beats.map((b) => ({
    beat: b.beat, goal: b.goal, facts: b.facts, chapter: b.chapter,
    sentences: (sentences[b.beat] || []).map((s) => {
      const r = rep[s.id] || {};
      const row = {id: s.id, text: s.text, facts: s.facts || [], colour: r.colour || 'plain',
        reasons: r.reasons || (perSentence && perSentence[s.id]) || []};
      if (flagOf[s.id]) row.flag = flagOf[s.id];
      return row;
    }),
  }));
}

export const copyLabel = (done) => (done ? 'Đã copy ✓' : 'Copy');
