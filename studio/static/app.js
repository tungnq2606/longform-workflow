// Studio UI: hash router, polling, job bar, Claude box. User text only ever goes in via textContent.
import {mountScript} from './script_view.js';
import {mountImages} from './images_view.js';
import {mountLibrary} from './library_view.js';
import {route, stateIcon, kindIcon, jobLine, runState, pauseButton, nextTheme, clock, stateLabel, THEME_LABEL, FLOW, TABS, TAB_PLAN} from './lib.js';

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
let isPaused = false;
let lastJobs = [];

function showRunState() {
  $('runstate').textContent = runState(isPaused, lastJobs);
  $('runstate').classList.toggle('paused', isPaused);
  const label = pauseButton(isPaused, lastJobs);
  $('pause').hidden = !label;
  if (label) $('pause').textContent = label;
}
let lastClaudeJobs = '';
let viewData = null;
let lastViewKey = '';

function applyTheme(t) {
  if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme;
  $('theme').textContent = THEME_LABEL[t];
  try { if (t) localStorage.setItem('studio-theme', t); else localStorage.removeItem('studio-theme'); } catch { /* private mode */ }
}

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

const STEP_NAMES = FLOW.map(([name]) => name);
const thumb = (kind, id) => `/api/thumb/${kind}/${encodeURIComponent(id)}`;

function stat(n, label) {
  return h('div', {class: 'stat'}, h('b', {}, String(n)), h('span', {}, label));
}

function renderHero(d) {
  const lib = d.library, bg = lib.backgrounds[0], hero = lib.characters[0];
  const running = lastJobs.filter((j) => j.status === 'running').length;
  const langs = new Set(d.projects.flatMap((p) => p.languages));
  const el = h('section', {class: 'hero'},
    hero ? h('img', {class: 'figure', src: thumb('char', hero.id), alt: ''}) : null,
    h('div', {class: 'hero-body'},
      h('div', {class: 'kicker'}, 'Công Trường Lịch Sử'),
      h('h1', {}, 'Công xưởng video dài'),
      h('p', {}, 'Video lịch sử 10–15 phút · một bộ hình, nhiều thứ tiếng · không câu nào thiếu nguồn'),
      h('div', {class: 'stats'},
        stat(d.projects.length, 'dự án'),
        stat(d.inbox.length, 'việc chờ bạn'),
        stat(running, 'job đang chạy'),
        stat(langs.size || 0, 'ngôn ngữ đang làm')),
      h('button', {onclick: openNew}, '+ Video mới')));
  if (bg) el.style.backgroundImage = `url("${thumb('bg', bg.id)}")`;
  return el;
}

function projectCard(p) {
  return h('div', {class: 'pcard', onclick: () => { location.hash = `#/p/${p.id}`; }},
    h('div', {class: 'num'}, `VIDEO ${p.id.slice(0, 3)}`),
    h('div', {class: 'title'}, p.title),
    h('div', {class: 'dots'}, p.steps.map((st, i) => h('span', {class: `dot ${st}`, title: `${STEP_NAMES[i]}: ${stateIcon(st)}`}))),
    h('div', {class: 'foot'}, h('span', {}, `${p.done}/${p.total} bước`),
      h('span', {class: 'tag'}, p.languages.map((c) => c.toUpperCase()).join(' '))));
}

function renderActivity() {
  const ended = lastJobs.filter((j) => j.status !== 'running' && j.status !== 'queued').slice(0, 6);
  return h('section', {class: 'card'}, h('h2', {}, 'Hoạt động gần đây'),
    ended.length
      ? h('ul', {class: 'list activity'}, ended.map((j) => h('li', {},
          h('time', {}, clock(j.ended)), h('span', {class: 'grow'}, jobLine(j)))))
      : h('p', {class: 'empty'}, 'Chưa có job nào xong.'));
}

function renderLibraryCard(lib) {
  const style = lib.styles.find((s) => s.approved);
  return h('section', {class: 'card'}, h('h2', {}, 'Thư viện'),
    lib.characters.length
      ? h('div', {class: 'lib-chars'}, lib.characters.map((c) => h('div', {class: 'lib-char'},
          h('img', {src: thumb('char', c.id), alt: ''}),
          h('div', {}, h('b', {}, c.name), h('div', {class: 'muted'}, `${c.poses} tư thế`)))))
      : h('p', {class: 'empty'}, 'Chưa có nhân vật nào.'),
    lib.backgrounds.length
      ? h('div', {class: 'lib-bgs'}, lib.backgrounds.slice(0, 6).map((b) => h('img', {src: thumb('bg', b.id), alt: b.id, title: b.id})))
      : null,
    h('p', {class: 'muted'}, `${lib.backgrounds.length} nền dùng lại · style ${style ? style.id + ' ✅ đã khóa' : 'chưa khóa'} · `,
      h('a', {href: '#/library'}, 'mở thư viện')));
}

function renderFlow() {
  return h('section', {class: 'card'}, h('h2', {}, 'Quy trình 7 bước'),
    h('ol', {class: 'flow'}, FLOW.map(([name, who]) => h('li', {}, h('div', {}, h('b', {}, name), h('span', {}, who))))));
}

function renderHome(d) {
  const projects = h('div', {class: 'projects'},
    d.projects.map(projectCard),
    h('div', {class: 'pcard newcard', onclick: openNew}, d.projects.length ? '+ Video mới' : '+ Bắt đầu video đầu tiên'));
  return [
    renderHero(d),
    h('div', {class: 'home-grid'},
      h('div', {},
        h('section', {class: 'card'}, h('h2', {}, '🔔 Cần bạn', h('span', {class: 'count'}, String(d.inbox.length))),
          inboxList(d.inbox, true)),
        h('section', {class: 'card'}, h('h2', {}, 'Dự án', h('span', {class: 'count'}, String(d.projects.length))), projects)),
      h('div', {}, renderActivity(), renderLibraryCard(d.library), renderFlow())),
  ];
}

function renderProject(d, tab) {
  const p = d.project, g = d.progress, tabOf = {topic: 'overview', script: 'script', images: 'images', scenes: 'scenes', langs: 'langs'};
  const steps = h('ol', {class: 'stepper'}, g.steps.map((s, i) => h('li', {class: `step ${s.state} ${tabOf[s.id] === tab ? 'cur' : ''}`},
    h('a', {href: `#/p/${p.id}/${tabOf[s.id] || 'overview'}`, title: `${s.label}: ${stateLabel(s.state)}`},
      h('span', {class: 'dotnum'}, s.state === 'done' ? '✓' : String(i + 1)),
      h('span', {class: 'slabel'}, s.label),
      h('span', {class: 'sstate'}, stateLabel(s.state))))));
  const partVi = {script: 'Kịch bản', voice: 'Giọng', render: 'Render'};
  const langs = h('div', {class: 'langchips'},
    h('span', {class: 'muted'}, 'Ngôn ngữ'),
    g.langs.map((l) => h('span', {class: 'langchip', title: Object.entries(l.parts).map(([k, v]) => `${partVi[k]}: ${stateLabel(v)}`).join('\n')},
      h('b', {}, l.code.toUpperCase()),
      Object.entries(l.parts).map(([k, v]) => h('i', {class: `ldot ${v}`, title: `${partVi[k]}: ${stateLabel(v)}`})))),
    h('span', {class: 'legend muted'}, 'chấm: kịch bản · giọng · render'));
  const tabs = h('nav', {class: 'tabs'}, Object.entries(TABS).map(([k, label]) =>
    h('a', {href: `#/p/${p.id}/${k}`, class: k === tab ? 'cur' : ''}, label)));
  const head = [h('h1', {}, `${p.id.slice(0, 3)} · ${p.title}`), h('section', {class: 'card phead'}, steps, langs), tabs];
  if (tab === 'script' || tab === 'images') return head;  // these screens are mounted once below the header (mounted())
  const body = tab === 'overview'
    ? h('section', {class: 'card'}, h('h2', {}, `🔔 Cần bạn (${d.inbox.length})`), inboxList(d.inbox, false))
    : h('p', {class: 'soon'}, `Màn hình ${TABS[tab]} làm ở Phần ${TAB_PLAN[tab]}.`);
  return [...head, body];
}

let mount = null;  // {key, el}: a screen with its own polling, kept across polls so typing and open views are never interrupted

function mounted() {
  let key = null, make = null;
  if (current.screen === 'project' && viewData && viewData.project && (current.tab === 'script' || current.tab === 'images')) {
    key = `${current.tab}:${current.id}`;
    make = () => (current.tab === 'script' ? mountScript : mountImages)(current.id, {h, api});
  } else if (current.screen === 'library') {
    key = 'library';
    make = () => mountLibrary({h, api});
  }
  if (!key) { mount = null; return null; }
  if (!mount || mount.key !== key) mount = {key, el: make()};
  if (current.item && mount.el.openItem && mount.item !== current.item) mount.el.openItem(current.item);
  mount.item = current.item;
  return mount.el;
}

function renderLibrary() {
  return [h('h1', {}, 'Thư viện'), h('p', {class: 'muted lv-lead'}, 'Dùng chung cho mọi video: nhân vật quan trọng, nền dùng lại, đám đông, style.')];
}

async function refresh() {
  current = route(location.hash);
  let nodes, paused;
  try {
    if (current.screen === 'project') {
      const d = await api(`/api/projects/${current.id}`);
      viewData = d;
      nodes = renderProject(d, current.tab);
      paused = (await api('/api/home')).paused;
    } else {
      const d = await api('/api/home');
      viewData = d;
      paused = d.paused;
      nodes = current.screen === 'library' ? renderLibrary() : renderHome(d);
    }
  } catch (e) {
    nodes = [h('p', {class: 'error'}, `Không tải được: ${e.message}`), h('a', {href: '#/'}, '← Trang chủ')];
  }
  const key = JSON.stringify([location.hash, viewData, current.screen === 'home' ? lastJobs.map((j) => j.id + j.status) : 0]);
  const sv = mounted();
  if (sv) {
    // header re-renders when its data changes; the mounted screen is never torn down
    const headEl = $('phead') || h('div', {id: 'phead'});
    if (key !== lastViewKey || $('view').firstChild !== headEl || headEl.nextSibling !== sv) {
      lastViewKey = key;
      headEl.replaceChildren(...nodes.flat());
      if ($('view').firstChild !== headEl || headEl.nextSibling !== sv) $('view').replaceChildren(headEl, sv);
    }
  } else if (key !== lastViewKey) {
    lastViewKey = key;
    $('view').replaceChildren(...nodes.flat());
  }
  if (paused) {
    isPaused = paused.on;
    showRunState();
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
  lastJobs = list;
  showRunState();
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
applyTheme(document.documentElement.dataset.theme || '');
$('theme').addEventListener('click', () => applyTheme(nextTheme(document.documentElement.dataset.theme || '')));
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
