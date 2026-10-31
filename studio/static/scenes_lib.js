// Pure helpers for the scene board (Plan 5); tested with `node --test studio/static/`.

// Problems of one beat, without the "B01: " prefix the validator adds.
export const beatProblems = (problems, bid) =>
  (problems || []).filter((p) => p.startsWith(bid + ': ')).map((p) => p.slice(bid.length + 2));

export function beatStatus(problems, hasPreview, previewing) {
  if (problems.length) return {cls: 'bad', text: `${problems.length} lỗi`};
  if (hasPreview) return {cls: 'ok', text: 'sẵn sàng'};
  return {cls: 'todo', text: previewing ? 'đang xem trước…' : 'chưa xem trước'};
}

export function sfxChips(sfx, audio) {
  const known = new Set(((audio && audio.sfx) || []).map((e) => e.id));
  return (sfx || []).map((s, i) => ({i, id: s.id, label: `${s.id} · ${s.sentence}${s.offset ? ` +${s.offset}s` : ''}`, missing: !known.has(s.id)}));
}

// Every (tag, sfx) pair, sorted by tag, for the "+" picker.
export function sfxChoices(audio) {
  const out = [];
  for (const e of (audio && audio.sfx) || []) for (const t of e.tags || []) out.push({tag: t, id: e.id, label: `${t} · ${e.id}`});
  return out.sort((a, b) => a.label.localeCompare(b.label));
}

export function camText(cam) {
  if (!cam || !cam.from || !cam.to) return '—';
  const parts = [`zoom ${cam.from.zoom}→${cam.to.zoom}`];
  if (cam.from.x !== cam.to.x) parts.push(`x ${cam.from.x}→${cam.to.x}`);
  if (cam.from.y !== cam.to.y) parts.push(`y ${cam.from.y}→${cam.to.y}`);
  return parts.join(' · ');
}

const RENDER_LABEL = {missing_timing: 'chưa dò thời điểm', ready: 'Render', rendering: 'đang render…', done: 'Render lại', blocked: 'chưa render được'};
export const renderLabel = (r) => RENDER_LABEL[r && r.state] || '—';

export const short = (text, n) => (text.length <= n ? text : text.slice(0, n - 1) + '…');
