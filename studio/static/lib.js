// Pure helpers for the Studio UI (no DOM), tested with `node --test studio/static/`.

export const TABS = {overview: 'Tổng quan', script: 'Kịch bản', images: 'Hình ảnh', scenes: 'Cảnh', langs: 'Ngôn ngữ'};
export const TAB_PLAN = {script: 3, images: 4, scenes: 5, langs: 6};
const PROJECT_ID = /^\d{3}-[a-z0-9-]+$/;

export function route(hash) {
  const parts = (hash || '').replace(/^#\/?/, '').split('/').filter(Boolean);
  if (parts[0] === 'library' && parts.length === 1) return {screen: 'library'};
  if (parts[0] === 'p' && PROJECT_ID.test(parts[1] || '')) {
    return {screen: 'project', id: parts[1], tab: parts[2] in TABS ? parts[2] : 'overview'};
  }
  return {screen: 'home'};
}

const STATE_ICONS = {todo: '⬜', doing: '▶', wait: '❓', done: '✅'};
export const stateIcon = (s) => STATE_ICONS[s] || '⬜';

const KIND_ICONS = {
  job_failed: '❌', job_interrupted: '⚠️', image_review: '🖼️', script_approve: '✍️', missing_voice: '🎙️',
  name_pronunciation: '🔤',
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
