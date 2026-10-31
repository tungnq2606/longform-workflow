// Scene board (Plan 5): one row per beat — sentences, background, heroes, crowds, camera, sound, status, preview —
// plus "Claude dựng cảnh" and a render button per language. Mounted once per visit; polls its own data and redraws
// only when it changed, so an open "+" sound picker is not wiped by a poll. Text goes in via textContent only (h()).
import {beatProblems, beatStatus, sfxChips, sfxChoices, camText, renderLabel, short} from './scenes_lib.js';
import {put, add} from './lib.js';

export function mountScenes(pid, {h, api}) {
  const st = {data: null, audio: {music: [], sfx: []}, key: '', adding: null};
  const root = h('div', {class: 'scb'});
  const bar = h('section', {class: 'card scb-bar'});
  const notes = h('div', {class: 'scb-notes'});
  const table = h('div', {class: 'scb-wrap'});
  add(root, bar, notes, table);

  async function act(fn) {
    try { await fn(); await load(true); } catch (e) { alert(e.message); }
  }

  // ---------------------------------------------------------------- top bar
  function renderBar() {
    const d = st.data;
    const sc = d.scenes;
    const write = h('button', {onclick: () => act(() => api(`/api/projects/${pid}/scenes/write`, {}))},
      d.writing ? '⏳ Claude đang dựng cảnh…' : '🎬 Claude dựng cảnh');
    write.disabled = Boolean(d.writing);
    const renders = Object.entries(d.renders || {}).map(([lang, r]) => {
      const b = h('button', {class: r.state === 'ready' || r.state === 'done' ? 'small' : 'ghost small',
        onclick: () => act(() => api(`/api/projects/${pid}/render/${lang}`, {}))}, `${lang.toUpperCase()}: ${renderLabel(r)}`);
      b.disabled = !(r.state === 'ready' || r.state === 'done');
      b.title = r.problems && r.problems.length ? r.problems.join('\n') : (r.file || '');
      return h('span', {class: `scb-render ${r.state}`}, b, r.file ? h('span', {class: 'muted scb-file'}, r.file) : null);
    });
    put(bar, 
      h('div', {class: 'scb-head'},
        h('b', {}, sc ? `File cảnh v${sc.version}` : 'Chưa có file cảnh'),
        sc ? h('span', {class: d.problems.length ? 'scb-count bad' : 'scb-count ok'},
          d.problems.length ? `${d.problems.length} lỗi` : 'không có lỗi') : null,
        h('span', {class: 'grow'}), write),
      renders.length ? h('div', {class: 'scb-renders'}, h('span', {class: 'muted'}, 'Render'), renders) : null);
  }

  function renderNotes() {
    const d = st.data;
    const other = d.problems.filter((p) => !/^B\d+: /.test(p));
    put(notes, 
      ...d.warnings.map((w) => h('div', {class: 'scb-warn'}, '⚠ ', w)),
      ...other.map((p) => h('div', {class: 'scb-err'}, '✖ ', p)));
  }

  // ---------------------------------------------------------------- table
  const chip = (text, cls = '') => h('span', {class: `chip ${cls}`}, text);

  function sound(row, beat, firstOfChapter) {
    const sfx = beat.sfx || [];
    const save = (list) => act(() => api(`/api/projects/${pid}/scenes/beat/${row.id}`, {sfx: list}));
    const cell = [h('div', {class: 'scb-chips'},
      sfxChips(sfx, st.audio).map((c) => h('span', {class: `chip ${c.missing ? 'bad' : ''}`, title: c.missing ? 'không có trong thư viện âm thanh' : ''},
        '🔊 ', c.label,
        h('button', {class: 'scb-x', title: 'Bỏ hiệu ứng này', onclick: () => save(sfx.filter((_, i) => i !== c.i))}, '✕'))),
      sfx.length < 3 ? h('button', {class: 'ghost small', title: 'Thêm hiệu ứng âm thanh',
        onclick: () => { st.adding = st.adding === row.id ? null : row.id; draw(); }}, '+') : null)];
    if (st.adding === row.id) {
      const pick = h('select', {'aria-label': 'Hiệu ứng'}, sfxChoices(st.audio).map((c) => h('option', {value: c.id}, c.label)));
      const when = h('select', {'aria-label': 'Câu'}, row.sentences.map((s) => h('option', {value: s.id}, `${s.id}: ${short(s.text, 28)}`)));
      const add = h('button', {class: 'small', onclick: () => {
        if (!pick.value) return;
        st.adding = null;
        save([...sfx, {sentence: when.value, id: pick.value, offset: 0, gain: 0.35}]);
      }}, 'Thêm');
      cell.push(st.audio.sfx.length ? h('div', {class: 'scb-add'}, pick, when, add)
        : h('div', {class: 'muted'}, 'Thư viện hiệu ứng trống'));
    }
    if (firstOfChapter) {
      const ch = (st.data.scenes.chapters || []).find((c) => c.id === row.chapter) || {};
      const music = h('select', {'aria-label': 'Nhạc chương'}, h('option', {value: ''}, 'không nhạc'),
        st.audio.music.map((m) => h('option', {value: m.id}, `${m.mood} · ${m.id}`)));
      music.value = ch.music || '';
      music.addEventListener('change', () => act(() => api(`/api/projects/${pid}/scenes/beat/${row.id}`, {music: music.value || null})));
      cell.push(h('label', {class: 'scb-music'}, `🎵 ${row.chapter} `, music));
    }
    return cell;
  }

  function beatRow(row, firstOfChapter) {
    const d = st.data;
    const beat = d.scenes.beats[row.id];
    if (!beat) return h('tr', {class: 'scb-missing'}, h('td', {}, h('b', {}, row.id)), h('td', {colspan: '8', class: 'error'}, 'Chưa có cảnh cho beat này'));
    const probs = beatProblems(d.problems, row.id);
    const pv = d.previews[row.id];
    const status = beatStatus(probs, Boolean(pv), d.previewing.includes(row.id));
    const bgRef = (beat.background || {}).id || '';
    const thumb = d.bg_thumbs[bgRef];
    const previewBtn = h('button', {class: 'ghost small', onclick: () => act(() => api(`/api/projects/${pid}/scenes/preview/${row.id}`, {}))},
      pv ? 'Làm lại' : 'Xem trước');
    previewBtn.disabled = d.previewing.includes(row.id);
    return h('tr', {class: probs.length ? 'bad' : ''},
      h('td', {class: 'scb-id'}, h('b', {}, row.id), h('div', {class: 'muted'}, row.goal)),
      h('td', {class: 'scb-sent'}, row.sentences.map((s) => h('div', {title: s.text}, h('span', {class: 'muted'}, s.id + ' '), short(s.text, 70)))),
      h('td', {class: 'scb-bg'}, thumb ? h('img', {src: thumb, alt: bgRef, loading: 'lazy'}) : null, h('div', {class: 'muted'}, bgRef)),
      h('td', {}, h('div', {class: 'scb-chips'}, (beat.heroes || []).map((hr) => h('span', {class: 'chip', title: (hr.keys || []).map((k) => `${k.sentence} → ${k.key}`).join('\n')},
        hr.key, (hr.keys || []).length ? ` (+${hr.keys.length})` : '')))),
      h('td', {}, h('div', {class: 'scb-chips'}, (beat.crowds || []).map((c) => chip(`${c.faction} ×${c.count}`)), beat.map ? chip('🗺 bản đồ') : null)),
      h('td', {class: 'muted'}, camText((beat.background || {}).camera)),
      h('td', {class: 'scb-sound'}, sound(row, beat, firstOfChapter)),
      h('td', {}, h('span', {class: `scb-status ${status.cls}`}, status.text), probs.length ? h('ul', {class: 'scb-probs'}, probs.map((p) => h('li', {}, p))) : null),
      h('td', {class: 'scb-pv'}, pv ? h('a', {href: `/api/projects/${pid}/scenes/preview/${row.id}?t=${pv}`, target: '_blank', rel: 'noopener'},
        h('img', {src: `/api/projects/${pid}/scenes/preview/${row.id}?t=${pv}`, alt: `Xem trước ${row.id}`, loading: 'lazy'})) : null, previewBtn));
  }

  function renderTable() {
    const d = st.data;
    if (!d.scenes) {
      put(table, h('p', {class: 'empty'}, d.script.length
        ? 'Chưa có file cảnh. Bấm "Claude dựng cảnh" khi kịch bản đã chốt và có ảnh đã duyệt.'
        : 'Chưa có kịch bản.'));
      return;
    }
    let lastChapter = null;
    const rows = d.script.map((row) => {
      const first = row.chapter !== lastChapter;
      lastChapter = row.chapter;
      return beatRow(row, first);
    });
    put(table, h('table', {class: 'scb-table'},
      h('thead', {}, h('tr', {}, ['Cảnh', 'Câu', 'Nền', 'Nhân vật', 'Đám đông', 'Chuyển động', 'Âm thanh', 'Trạng thái', 'Xem trước'].map((t) => h('th', {}, t)))),
      h('tbody', {}, rows)));
  }

  function draw() {
    renderBar();
    renderNotes();
    renderTable();
  }

  async function load(force) {
    try {
      const [d, audio] = await Promise.all([api(`/api/projects/${pid}/scenes`), api('/api/audio')]);
      const key = JSON.stringify([d, audio]);
      if (!force && key === st.key) return;
      st.key = key;
      st.data = d;
      st.audio = audio;
      if (!st.adding) draw();
      else renderBar();
    } catch (e) {
      put(bar, h('p', {class: 'error'}, `Không tải được bảng cảnh: ${e.message}`));
    }
  }

  load(true);
  const timer = setInterval(() => {
    if (!document.contains(root)) { clearInterval(timer); return; }
    load(false);
  }, 3000);
  return root;
}
