// Images screen (Plan 4): the review grid. Mounted once per visit; polls its own data every 3 s and re-renders only
// what changed, so a typed note or an open image is never interrupted. Cards appear and update as each image is
// drawn and scored. Keys in the large view: A approve, R redraw with a note, X reject, ←/→ move, Esc close.
import {imageStateLabel, scoreClass, nextIndex, filterImages, IMAGE_FILTERS, imageSrc, RUNNING_IMAGE} from './lib.js';
import {put, add} from './lib.js';

const TYPE_LABEL = {bg: 'nền', prop: 'đạo cụ', pose: 'nhân vật'};
const SPEC_FIELDS = ['shot', 'angle', 'layout', 'setting', 'people', 'props', 'light', 'must_not'];
const MAX_LANE = 8;

export function mountImages(pid, {h, api}) {
  const st = {items: [], counts: {}, lanes: {}, filter: 'all', selected: new Set(), open: null, busy: false, keys: {}, msg: ''};
  const root = h('div', {class: 'iv'});
  const bar = h('div', {class: 'iv-bar card'});
  const chips = h('div', {class: 'iv-chips'});
  const grid = h('div', {class: 'iv-grid'});
  const viewer = h('div', {class: 'iv-viewer', hidden: ''});
  add(root, bar, chips, grid, viewer);

  const changed = (name, value) => {
    const k = JSON.stringify(value);
    if (st.keys[name] === k) return false;
    st.keys[name] = k;
    return true;
  };

  async function act(fn) {
    if (st.busy) return;
    st.busy = true;
    renderViewer();
    try { await fn(); } catch (e) { alert(e.message); }
    st.busy = false;
    await load().catch(() => {});
    renderViewer();
  }

  const shown = () => filterImages(st.items, st.filter);

  // ---------------------------------------------------------------- top bar
  function renderBar() {
    const n = st.items.length;
    const c = st.counts;
    const doing = RUNNING_IMAGE.reduce((s, k) => s + (c[k] || 0), 0);
    const agy = st.lanes.agy || 1;
    const setLane = (v) => act(() => api('/api/lanes', {agy: v}));
    const shot = h('button', {class: 'ghost', onclick: () => act(() => api(`/api/projects/${pid}/shotlist`, {}))}, '📋 Lập danh sách ảnh');
    if (n) { shot.disabled = true; shot.title = 'Dự án đã có danh sách ảnh'; }
    const minus = h('button', {class: 'ghost small', title: 'Bớt một luồng', onclick: () => setLane(agy - 1)}, '−');
    const plus = h('button', {class: 'ghost small', title: 'Thêm một luồng', onclick: () => setLane(agy + 1)}, '+');
    minus.disabled = agy <= 1;
    plus.disabled = agy >= MAX_LANE;
    const many = st.selected.size
      ? h('button', {onclick: () => act(async () => {
          const r = await api(`/api/projects/${pid}/images/approve_many`, {ids: [...st.selected]});
          st.selected.clear();
          const errs = Object.entries(r.errors);
          if (errs.length) alert(errs.map(([id, e]) => `${id}: ${e}`).join('\n'));
        })}, `Duyệt ${st.selected.size} ảnh`)
      : null;
    put(bar, 
      h('div', {class: 'iv-summary'},
        h('b', {}, n ? `${n} ảnh` : 'Chưa có danh sách ảnh'),
        n ? h('span', {class: 'muted'}, ` · ${c.wait || 0} cần bạn · ${c.pass || 0} đạt chờ duyệt · ${doing} đang làm · ${c.approved || 0} đã duyệt`
          + (c.failed ? ` · ${c.failed} hỏng` : '')) : null),
      h('div', {class: 'row'},
        shot,
        h('span', {class: 'lane', title: 'Số ảnh agy vẽ/chấm cùng lúc'}, h('span', {class: 'muted'}, 'Luồng agy'), minus,
          h('b', {}, String(agy)), plus),
        h('button', {class: 'ghost', onclick: castSheet}, '👥 Ảnh tổng nhân vật'),
        many));
  }

  function castSheet() {
    act(async () => {
      await api(`/api/projects/${pid}/cast_sheet`, {});
      window.open(`/api/projects/${pid}/cast_sheet?v=${Date.now()}`, '_blank', 'noopener');
    });
  }

  function renderChips() {
    put(chips, ...Object.entries(IMAGE_FILTERS).map(([k, [label]]) => h('button', {
      class: `chip ${st.filter === k ? 'on' : ''}`, onclick: () => { st.filter = k; renderChips(); renderGrid(); }},
      `${label} ${filterImages(st.items, k).length}`)));
  }

  // ---------------------------------------------------------------- grid
  function card(it) {
    const src = imageSrc(pid, it, 'thumb');
    const running = RUNNING_IMAGE.includes(it.state);
    const pic = src && !running
      ? h('img', {src, alt: it.id, loading: 'lazy'})
      : h('div', {class: 'iv-ph'}, running ? h('span', {class: 'spin'}) : null, h('span', {class: 'muted'}, imageStateLabel(it.state)));
    const el = h('div', {class: `iv-card ${it.type} ${st.selected.has(it.id) ? 'sel' : ''} ${it.state}`, tabindex: '0'},
      h('div', {class: 'iv-pic'}, pic),
      h('div', {class: 'iv-meta'},
        h('b', {}, it.id),
        h('span', {class: 'tag'}, TYPE_LABEL[it.type] || it.type),
        it.beat ? h('span', {class: 'muted'}, it.beat) : null,
        h('span', {class: 'grow'}),
        it.score != null ? h('span', {class: `score ${scoreClass(it.score)}`}, `${it.score}/5`) : null),
      h('div', {class: `iv-state s-${it.state}`}, imageStateLabel(it.state),
        it.state === 'wait' && it.problems.length ? h('span', {class: 'muted'}, ` · ${it.problems[0]}`) : null));
    el.addEventListener('click', (e) => {
      if (e.shiftKey) {
        if (st.selected.has(it.id)) st.selected.delete(it.id); else st.selected.add(it.id);
        renderBar();
        renderGrid();
        return;
      }
      openItem(it.id);
    });
    el.addEventListener('keydown', (e) => { if (e.key === 'Enter') openItem(it.id); });
    return el;
  }

  function renderGrid() {
    const list = shown();
    put(grid, ...(list.length ? list.map(card) : [h('p', {class: 'empty'}, st.items.length
      ? 'Không có ảnh ở mục này.'
      : 'Chưa có ảnh. Chốt kịch bản rồi bấm "Lập danh sách ảnh": agy đề xuất nền, đạo cụ và tư thế nhân vật, rồi vẽ và chấm từng ảnh.')]));
  }

  // ---------------------------------------------------------------- large view
  function openItem(id) {
    st.open = id;
    renderViewer();
  }

  function close() {
    st.open = null;
    renderViewer();
    if (/\/images\/[A-Z]+\d+$/.test(location.hash)) history.replaceState(null, '', `#/p/${pid}/images`);
  }

  function move(key) {
    const list = shown();
    const i = list.findIndex((x) => x.id === st.open);
    const j = nextIndex(Math.max(0, i), list.length, key);
    if (j >= 0) openItem(list[j].id);
  }

  const approve = (it) => act(() => api(`/api/projects/${pid}/images/${it.id}/approve`, {}));
  const reject = (it) => act(() => api(`/api/projects/${pid}/images/${it.id}/reject`, {}));
  function redo(it) {
    const note = prompt(`Vẽ lại ${it.id}: cần sửa gì? (ghi chú gửi kèm prompt)`, it.fix || '');
    if (note !== null) act(() => api(`/api/projects/${pid}/images/${it.id}/redo`, {note}));
  }
  function toLibrary(it) {
    const name = prompt('Tên nền trong thư viện (ví dụ: Sông Bạch Đằng lúc triều xuống)');
    if (name && name.trim()) act(async () => {
      const r = await api(`/api/projects/${pid}/images/${it.id}/to_library`, {name: name.trim()});
      alert(`Đã đưa vào thư viện: ${r.id}`);
    });
  }

  function specList(spec) {
    return h('dl', {class: 'iv-spec'}, SPEC_FIELDS.filter((f) => spec && spec[f] != null).map((f) => [
      h('dt', {}, f), h('dd', {}, Array.isArray(spec[f]) ? spec[f].join(' · ') : String(spec[f]))]));
  }

  function renderViewer() {
    const it = st.items.find((x) => x.id === st.open);
    if (!it) { viewer.hidden = true; put(viewer); return; }
    viewer.hidden = false;
    const src = imageSrc(pid, it, it.type === 'pose' ? 'cutout' : 'final') || imageSrc(pid, it, 'raw');
    const decidable = ['pass', 'wait', 'failed'].includes(it.state);
    const btn = (label, fn, ok, cls = 'ghost') => {
      const b = h('button', {class: cls, onclick: () => fn(it)}, label);
      b.disabled = !ok || st.busy;
      return b;
    };
    const list = shown();
    put(viewer, h('div', {class: 'iv-panel', role: 'dialog', 'aria-label': `Ảnh ${it.id}`},
      h('div', {class: `iv-big ${it.type}`}, src ? h('img', {src, alt: it.id}) : h('div', {class: 'iv-ph'},
        RUNNING_IMAGE.includes(it.state) ? h('span', {class: 'spin'}) : null, imageStateLabel(it.state))),
      h('aside', {class: 'iv-side'},
        h('div', {class: 'row iv-head'},
          h('b', {}, it.id), h('span', {class: 'tag'}, TYPE_LABEL[it.type]),
          it.beat ? h('span', {class: 'muted'}, it.beat) : null,
          h('span', {class: 'grow'}),
          h('span', {class: 'muted'}, `${list.findIndex((x) => x.id === it.id) + 1}/${list.length}`),
          h('button', {class: 'ghost small', title: 'Đóng (Esc)', onclick: close}, '✕')),
        h('div', {class: 'row'},
          it.score != null ? h('span', {class: `score ${scoreClass(it.score)}`}, `${it.score}/5`) : null,
          h('span', {class: `iv-state s-${it.state}`}, imageStateLabel(it.state)),
          it.attempts ? h('span', {class: 'muted'}, `vẽ lại ${it.attempts} lần`) : null),
        it.kit ? h('p', {class: 'muted iv-kit'}, `Bộ ${it.kit} · tư thế ${it.pose_key}`) : null,
        it.problems.length ? h('div', {class: 'iv-problems'}, h('h3', {}, 'Lỗi'),
          h('ul', {}, it.problems.map((p) => h('li', {}, p)))) : null,
        h('div', {class: 'row iv-actions'},
          btn('A · Duyệt', approve, decidable, ''),
          btn('R · Vẽ lại', redo, !RUNNING_IMAGE.includes(it.state) && !it.reuse),
          btn('X · Bỏ', reject, !['generating', 'reviewing', 'rejected'].includes(it.state)),
          it.type === 'bg' && it.state === 'approved' && !it.reuse && !it.library ? btn('Đưa vào thư viện', toLibrary, true) : null),
        st.busy ? h('p', {class: 'muted'}, 'Đang làm… (duyệt tư thế mới mất vài giây để tách nền)') : null,
        h('p', {class: 'muted'}, '← → chuyển ảnh · Shift+bấm thẻ để chọn nhiều'),
        it.reuse ? h('p', {class: 'muted'}, `Dùng lại nền thư viện: ${it.reuse}`) : null,
        h('h3', {}, 'Spec'), specList(it.spec),
        h('h3', {}, 'Lịch sử'),
        h('ul', {class: 'iv-hist'}, it.history.slice().reverse().map((x) => h('li', {},
          h('time', {}, (x.at || '').slice(5, 16).replace('T', ' ')), ' ', imageStateLabel(x.event),
          x.score != null ? ` · ${x.score}/5` : '', x.note ? h('span', {class: 'muted'}, ` · ${x.note}`) : null))))));
  }

  viewer.addEventListener('click', (e) => { if (e.target === viewer) close(); });

  function onKey(e) {
    if (!document.contains(root)) { document.removeEventListener('keydown', onKey); return; }
    if (!st.open || e.metaKey || e.ctrlKey || e.altKey) return;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target.tagName || '').toUpperCase())) return;
    const it = st.items.find((x) => x.id === st.open);
    if (!it) return;
    const k = e.key.toLowerCase();
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') move(e.key);
    else if (k === 'a' && ['pass', 'wait', 'failed'].includes(it.state)) approve(it);
    else if (k === 'r' && !RUNNING_IMAGE.includes(it.state) && !it.reuse) redo(it);
    else if (k === 'x') reject(it);
    else return;
    e.preventDefault();
  }
  document.addEventListener('keydown', onKey);

  // ---------------------------------------------------------------- data
  async function load() {
    const d = await api(`/api/projects/${pid}/images`);
    let any = false;
    if (changed('items', d.items)) {
      st.items = d.items;
      const ids = new Set(d.items.map((x) => x.id));
      for (const id of [...st.selected]) if (!ids.has(id)) st.selected.delete(id);
      any = true;
    }
    if (changed('meta', [d.counts, d.lanes])) { st.counts = d.counts; st.lanes = d.lanes; any = true; }
    if (any) { renderBar(); renderChips(); renderGrid(); if (!st.busy) renderViewer(); }
  }

  root.openItem = openItem;  // deep link #/p/<id>/images/<item> (an inbox line) opens the large view
  renderBar();
  renderChips();
  renderGrid();
  load().catch(() => {});
  const timer = setInterval(() => {
    if (!document.contains(root)) { clearInterval(timer); document.removeEventListener('keydown', onKey); return; }
    if (document.visibilityState === 'visible') load().catch(() => {});
  }, 3000);
  return root;
}
