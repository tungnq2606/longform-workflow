// Pure helpers for the Studio UI (no DOM), tested with `node --test studio/static/`.

export const TABS = {overview: 'Tổng quan', script: 'Kịch bản', images: 'Hình ảnh', scenes: 'Cảnh', langs: 'Ngôn ngữ'};
export const TAB_PLAN = {scenes: 5, langs: 6};
const PROJECT_ID = /^\d{3}-[a-z0-9-]+$/;
const ITEM_ID = /^[A-Z]+\d+$/;

export function route(hash) {
  const parts = (hash || '').replace(/^#\/?/, '').split('/').filter(Boolean);
  if (parts[0] === 'library' && parts.length === 1) return {screen: 'library'};
  if (parts[0] === 'p' && PROJECT_ID.test(parts[1] || '')) {
    const r = {screen: 'project', id: parts[1], tab: parts[2] in TABS ? parts[2] : 'overview'};
    if (r.tab === 'images' && ITEM_ID.test(parts[3] || '')) r.item = parts[3];  // deep link to one image
    return r;
  }
  return {screen: 'home'};
}

const STATE_ICONS = {todo: '⬜', doing: '▶', wait: '❓', done: '✅'};
export const stateIcon = (s) => STATE_ICONS[s] || '⬜';

const KIND_ICONS = {
  job_failed: '❌', job_interrupted: '⚠️', image_review: '🖼️', script_approve: '✍️', missing_voice: '🎙️',
  name_pronunciation: '🔤', quota: '⛽',
};
export const kindIcon = (k) => KIND_ICONS[k] || '🔔';

export function progressBar(done, total, width = 7) {
  const n = total ? Math.round((done / total) * width) : 0;
  return '▓'.repeat(n) + '░'.repeat(width - n);
}

export const STATUS_VI = {queued: 'chờ', running: 'đang chạy', done: 'xong', failed: 'hỏng', stopped: 'đã dừng', interrupted: 'bị ngắt'};
const STATUS_ICONS = {queued: '⏳', running: '▶', done: '✅', failed: '❌', stopped: '⏹', interrupted: '⚠️'};
export const jobLine = (job) => `${STATUS_ICONS[job.status] || '•'} ${job.label} · ${STATUS_VI[job.status] || job.status}`;

// Top-bar status: what the queue is actually doing right now.
export function runState(paused, jobs) {
  const running = jobs.filter((j) => j.status === 'running').length;
  const queued = jobs.filter((j) => j.status === 'queued').length;
  const parts = [];
  if (running) parts.push(paused ? `${running} job làm nốt` : `${running} job đang chạy`);
  if (queued) parts.push(`${queued} job chờ`);
  if (paused) return ['🟡 Tạm dừng', ...parts].join(' · ');
  if (!running && !queued) return '⚪ Rảnh: không có job nào';
  return '▶ ' + parts.join(' · ');
}

// Theme toggle: '' follows the system, then forced dark, then forced light.
const THEMES = ['', 'dark', 'light'];
export const nextTheme = (t) => THEMES[(Math.max(0, THEMES.indexOf(t)) + 1) % THEMES.length];
export const THEME_LABEL = {'': '🖥 Theo máy', dark: '🌙 Tối', light: '☀️ Sáng'};

export const clock = (iso) => (iso ? iso.slice(11, 16) : '');

// The 7 steps and who does each (spec §4.3 and the owner's split of work).
export const FLOW = [
  ['Đề tài', 'bạn chọn, số liệu nhu cầu từ scout'],
  ['Kịch bản', 'agy tìm nguồn và viết nháp, Claude soát'],
  ['Hình ảnh', 'agy vẽ và chấm, bạn duyệt ảnh 3/5'],
  ['Cảnh', 'Claude dựng cảnh bằng Remotion'],
  ['Ngôn ngữ', 'agy viết lại cho từng thứ tiếng'],
  ['Render', '1440p cho mỗi ngôn ngữ'],
  ['Upload', 'bạn đăng, Studio soạn sẵn chữ'],
];

// Pause button label, or null to hide it: nothing to pause while the queue is empty.
export function pauseButton(paused, jobs) {
  if (paused) return 'Chạy tiếp';
  return jobs.some((j) => j.status === 'running' || j.status === 'queued') ? 'Tạm dừng' : null;
}

// Script screen (Plan 3).
const FACT_ICONS = {pending: '⏳', verified: '✅', weak: '⚠️', conflict: '⛔', rejected: '✖'};
export const factIcon = (s) => FACT_ICONS[s] || '•';
export const FACT_LABEL = {pending: 'đang kiểm', verified: 'đã kiểm', weak: 'nguồn yếu', conflict: 'vênh nhau', rejected: 'bị loại'};
export const colourClass = (c) => `c-${['red', 'yellow', 'green', 'plain'].includes(c) ? c : 'plain'}`;
export const summaryLine = (r) => `đỏ ${r.red} · vàng ${r.yellow} · xanh ${r.green} · ${r.sentences.length} câu`;
export const canApprove = (r) => Boolean(r && r.sentences && r.sentences.length && r.red === 0);

const STATE_LABEL = {todo: 'chưa làm', doing: 'đang làm', wait: 'chờ bạn', done: 'xong'};
export const stateLabel = (s) => STATE_LABEL[s] || STATE_LABEL.todo;

// Images screen (Plan 4).
const IMAGE_STATE = {queued: 'chờ vẽ', generating: 'đang vẽ', reviewing: 'đang chấm', pass: 'đạt, chờ duyệt', wait: 'cần bạn',
  approved: 'đã duyệt', rejected: 'đã bỏ', failed: 'hỏng'};
export const imageStateLabel = (s) => IMAGE_STATE[s] || s;
export const RUNNING_IMAGE = ['queued', 'generating', 'reviewing'];

export function scoreClass(score) {
  if (score == null) return 'score-none';
  return score >= 4 ? 'score-good' : score === 3 ? 'score-mid' : 'score-bad';
}

// ←/→ through n images with wrap; any other key keeps the index; -1 when there is nothing to show.
export function nextIndex(i, n, key) {
  if (!n) return -1;
  if (key === 'ArrowRight') return (i + 1) % n;
  if (key === 'ArrowLeft') return (i - 1 + n) % n;
  return i;
}

export const needsOwner = (item) => item.state === 'wait';

export const IMAGE_FILTERS = {
  all: ['Tất cả', () => true],
  owner: ['Cần bạn', needsOwner],
  doing: ['Đang làm', (it) => RUNNING_IMAGE.includes(it.state)],
  approved: ['Đã duyệt', (it) => it.state === 'approved'],
};
export const filterImages = (items, f) => items.filter((IMAGE_FILTERS[f] || IMAGE_FILTERS.all)[1]);

// URL of an item's file, versioned by its history so the browser never shows a stale image after a redo.
export function imageSrc(pid, item, which) {
  const files = item.files || {};
  const has = which === 'thumb' ? files.cutout || files.final || files.raw : files[which];
  if (!has) return null;
  return `/api/projects/${pid}/images/${encodeURIComponent(item.id)}/${which}?v=${(item.history || []).length}`;
}
