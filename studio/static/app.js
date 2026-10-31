// Studio UI: hash router, polling, job bar, Claude box. User text only ever goes in via textContent.
import {route, stateIcon, kindIcon, progressBar, jobLine, TABS, TAB_PLAN} from './lib.js';

const $ = (id) => document.getElementById(id);

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'onclick') el.addEventListener('click', v);
    else if (k === 'class') el.className = v;
    else el.setAttribute(k, v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

async function api(path, body) {
  const opt = body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)};
  const r = await fetch(path, opt);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `lỗi ${r.status}`);
  return data;
}

let current = route(location.hash);
let claudeProject = undefined;
let openLog = null;          // {id, offset}
let lastClaudeJobs = '';

// ---------------------------------------------------------------- views
function inboxList(items, showProject) {
  if (!items.length) return h('p', {class: 'empty'}, 'Không có việc nào chờ bạn.');
  return h('ul', {class: 'list'}, items.map((it) => h('li', {class: 'click', onclick: () => {
    location.hash = it.project ? `#/p/${it.project}${it.screen ? '/' + it.screen : ''}` : '#/';
  }},
    h('span', {}, kindIcon(it.kind)),
    h('span', {class: 'grow'}, it.text, showProject && it.project ? h('span', {class: 'muted'}, ` · ${it.project}`) : null),
    h('button', {class: 'ghost small', onclick: async (e) => { e.stopPropagation(); await api(`/api/inbox/${it.id}/done`, {}); refresh(); }}, 'Xong'),
  )));
}

function renderHome(d) {
  const projects = d.projects.length
    ? h('ul', {class: 'list'}, d.projects.map((p) => h('li', {class: 'click', onclick: () => { location.hash = `#/p/${p.id}`; }},
        h('span', {class: 'grow'}, h('b', {}, p.id.slice(0, 3)), ' ', p.title),
        h('span', {class: 'bar'}, progressBar(p.done, p.total)),
        h('span', {class: 'muted'}, `${p.done}/${p.total}`),
        h('span', {class: 'tag'}, p.languages.map((c) => c.toUpperCase()).join(' ')))))
    : h('p', {class: 'empty'}, 'Chưa có dự án.');
  return [
    h('section', {class: 'card'}, h('h2', {}, `🔔 Cần bạn (${d.inbox.length})`), inboxList(d.inbox, true)),
    h('section', {class: 'card'}, h('h2', {}, 'Dự án'), projects,
      h('div', {class: 'row'}, h('button', {onclick: openNew}, '+ Video mới'))),
  ];
}

function renderProject(d, tab) {
  const p = d.project, g = d.progress, tabOf = {topic: 'overview', script: 'script', images: 'images', scenes: 'scenes', langs: 'langs'};
  const steps = h('div', {class: 'steps'}, g.steps.map((s, i) => [
    i ? h('span', {class: 'arrow'}, '→') : null,
    h('a', {href: `#/p/${p.id}/${tabOf[s.id] || 'overview'}`, class: tabOf[s.id] === tab ? 'cur' : ''}, `${stateIcon(s.state)} ${s.label}`),
  ]));
  const partVi = {script: 'kịch bản', voice: 'giọng', render: 'render'};
  const langs = h('div', {class: 'langs'}, g.langs.map((l, i) => [
    i ? ' · ' : null, h('b', {}, l.code.toUpperCase()), ' ',
    Object.entries(l.parts).map(([k, v]) => `${stateIcon(v)} ${partVi[k]}`).join(' '),
  ]));
  const tabs = h('nav', {class: 'tabs'}, Object.entries(TABS).map(([k, label]) =>
    h('a', {href: `#/p/${p.id}/${k}`, class: k === tab ? 'cur' : ''}, label)));
  const body = tab === 'overview'
    ? h('section', {class: 'card'}, h('h2', {}, `🔔 Cần bạn (${d.inbox.length})`), inboxList(d.inbox, false))
    : h('p', {class: 'soon'}, `Màn hình ${TABS[tab]} làm ở Phần ${TAB_PLAN[tab]}.`);
  return [
    h('h1', {}, `${p.id.slice(0, 3)} · ${p.title}`),
    h('section', {class: 'card'}, steps, langs),
    tabs, body,
  ];
}

function renderLibrary() {
  return [h('h1', {}, 'Thư viện'), h('p', {class: 'soon'}, 'Nhân vật, đám đông, nền dùng lại: làm ở Phần 4.')];
}

async function refresh() {
  current = route(location.hash);
  let nodes, paused;
  try {
    if (current.screen === 'project') {
      const d = await api(`/api/projects/${current.id}`);
      nodes = renderProject(d, current.tab);
      paused = (await api('/api/home')).paused;
    } else {
      const d = await api('/api/home');
      paused = d.paused;
      nodes = current.screen === 'library' ? renderLibrary() : renderHome(d);
    }
  } catch (e) {
    nodes = [h('p', {class: 'error'}, `Không tải được: ${e.message}`), h('a', {href: '#/'}, '← Trang chủ')];
  }
  $('view').replaceChildren(...nodes.flat());
  if (paused) {
    $('pause').textContent = paused.on ? '▶ Chạy tiếp' : '⏸ Tạm dừng';
    $('pause').dataset.on = paused.on ? '1' : '';
    $('pausebar').hidden = !paused.on;
    $('pausebar').textContent = paused.on ? `Đang tạm dừng: job đang chạy sẽ làm nốt, job mới chưa bắt đầu. (${paused.reason || ''})` : '';
  }
  const proj = current.screen === 'project' ? current.id : null;
  if (proj !== claudeProject) { claudeProject = proj; loadHistory(); }
}

// ---------------------------------------------------------------- jobs bar
async function refreshJobs() {
  let list;
  try { list = await api('/api/jobs'); } catch { return; }
  const live = list.filter((j) => j.status === 'running' || j.status === 'queued');
  const ended = list.filter((j) => j.status !== 'running' && j.status !== 'queued').slice(0, 5);
  const rows = [...live, ...ended].map((j) => h('li', {onclick: () => showLog(j.id)},
    h('span', {class: 'grow', title: j.label}, jobLine(j)),
    (j.status === 'running' || j.status === 'queued')
      ? h('button', {class: 'ghost small', title: 'Dừng', onclick: async (e) => { e.stopPropagation(); await api(`/api/jobs/${j.id}/stop`, {}); refreshJobs(); }}, '⏹')
      : null));
  $('jobs').replaceChildren(...(rows.length ? rows : [h('li', {class: 'muted'}, 'Không có job.')]));
  const claudeKey = list.filter((j) => j.kind === 'claude').map((j) => j.id + j.status).join();
  if (claudeKey !== lastClaudeJobs) { lastClaudeJobs = claudeKey; loadHistory(); }
  if (openLog) pollLog();
}

function showLog(id) {
  if (openLog && openLog.id === id) { openLog = null; $('log').hidden = true; return; }
  openLog = {id, offset: 0};
  $('log').textContent = '';
  $('log').hidden = false;
  pollLog();
}

async function pollLog() {
  const cur = openLog;
  if (!cur) return;
  try {
    const r = await api(`/api/jobs/${cur.id}/log?offset=${cur.offset}`);
    if (openLog !== cur) return;
    cur.offset = r.offset;
    if (r.text) { $('log').append(r.text); $('log').scrollTop = $('log').scrollHeight; }
  } catch { /* job gone */ }
}

// ---------------------------------------------------------------- Claude box
async function loadHistory() {
  $('claude-where').textContent = claudeProject ? `· ${claudeProject}` : '· chung';
  let hist = [];
  try { hist = await api(`/api/claude/history${claudeProject ? '?project=' + claudeProject : ''}`); } catch { /* ignore */ }
  $('history').replaceChildren(...hist.map((m) =>
    h('p', {class: m.role}, h('b', {}, m.role === 'owner' ? 'Bạn' : 'Claude'), ` ${m.at}: `, m.text)));
  $('history').scrollTop = $('history').scrollHeight;
}

async function sendClaude(e) {
  e.preventDefault();
  const message = $('msg').value.trim();
  if (!message) return;
  try {
    await api('/api/claude', {message, project: claudeProject, model: $('model').value || null});
    $('msg').value = '';
    refreshJobs();
  } catch (err) { alert(err.message); }
}

// ---------------------------------------------------------------- Video mới
async function openNew() {
  const langs = await api('/api/languages');
  $('new-langs').replaceChildren(...langs.map((l) => {
    const box = h('input', {type: 'checkbox', value: l.code});
    if (l.code === 'vi') { box.checked = true; box.disabled = true; }
    return h('label', {}, box, `${l.code.toUpperCase()} · ${l.name}`);
  }));
  $('new-title').value = '';
  $('new-error').hidden = true;
  $('new').showModal();
}

async function createNew(e) {
  e.preventDefault();
  const languages = [...$('new-langs').querySelectorAll('input:checked')].map((b) => b.value).filter((c) => c !== 'vi');
  try {
    const {id} = await api('/api/projects', {title: $('new-title').value, languages});
    $('new').close();
    location.hash = `#/p/${id}`;
  } catch (err) {
    $('new-error').textContent = err.message;
    $('new-error').hidden = false;
  }
}

// ---------------------------------------------------------------- start
$('pause').addEventListener('click', async () => { await api('/api/pause', {on: !$('pause').dataset.on}); refresh(); });
$('claude-form').addEventListener('submit', sendClaude);
$('msg').addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) sendClaude(e); });
$('new-form').addEventListener('submit', createNew);
$('new-cancel').addEventListener('click', () => $('new').close());
window.addEventListener('hashchange', refresh);

api('/api/claude/models').then((models) => {
  $('model').replaceChildren(h('option', {value: ''}, 'model mặc định'), ...models.map((m) => h('option', {value: m}, m)));
}).catch(() => {});

refresh();
refreshJobs();
setInterval(() => {
  if (document.visibilityState !== 'visible') return;
  if (!$('new').open) refresh();
  refreshJobs();
}, 2000);
