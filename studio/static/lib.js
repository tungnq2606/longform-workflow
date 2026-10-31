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
