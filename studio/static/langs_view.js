// Languages tab (Plan 6): one tab per language (VI is the source, read-only here) plus "+".
// Per language: script panel (beat goal + fact chips | that language's sentences, coloured, with flags and
// back-translations), voice panel (parts to copy, file names, drop zone), render panel (Plan 5 route) and upload panel
// (texts with copy buttons, chapters, thumbnail). Mounted once per visit; polls its own data. Text via textContent only.
import {colourClass, summaryLine, canApprove} from './lib.js';
import {voiceSummary, langTabState, partFileName, beatRows, copyLabel} from './langs_lib.js';

export function mountLangs(pid, {h, api}) {
  const st = {lang: null, project: null, data: null, all: [], keys: {}, msg: ''};
  const root = h('div', {class: 'lv'});
  const tabs = h('nav', {class: 'lv-tabs'});
  const msg = h('p', {class: 'lv-msg', hidden: ''});
  const scriptCard = h('section', {class: 'card lv-script'});
  const voiceCard = h('section', {class: 'card lv-voice'});
  const renderCard = h('section', {class: 'card lv-render'});
  const uploadCard = h('section', {class: 'card lv-upload'});
  const thumbBox = h('div', {class: 'lv-thumbprev'});
  const thumbForm = buildThumbForm();
  root.append(tabs, msg, scriptCard, h('div', {class: 'lv-grid'}, voiceCard, h('div', {}, renderCard, uploadCard)));

  const changed = (name, value) => {
    const k = JSON.stringify(value);
    if (st.keys[name] === k) return false;
    st.keys[name] = k;
    return true;
  };
  const base = () => `/api/projects/${pid}/langs/${st.lang}`;
  function say(text, bad) {
    msg.hidden = !text;
    msg.className = 'lv-msg' + (bad ? ' error' : '');
    msg.textContent = text || '';
  }
  async function act(fn, done) {
    try { await fn(); say(done || ''); await load(); } catch (e) { say(e.message, true); }
  }
  async function copy(btn, text) {
    try { await navigator.clipboard.writeText(text); btn.textContent = copyLabel(true); } catch (e) { say('Không copy được: ' + e.message, true); }
    setTimeout(() => { btn.textContent = copyLabel(false); }, 1500);
  }

  // ---------------------------------------------------------------- tabs
  function renderTabs() {
    const p = st.project;
    if (!p) return;
    const src = p.project.source_lang || 'vi';
    const missing = st.all.filter((l) => !p.project.languages.includes(l.code));
    const sel = h('select', {'aria-label': 'Thêm ngôn ngữ'}, missing.map((l) => h('option', {value: l.code}, `${l.code.toUpperCase()} · ${l.name}`)));
    const add = h('span', {class: 'lv-add'}, sel, h('button', {class: 'ghost small', onclick: () => act(async () => {
      await api(`/api/projects/${pid}/languages`, {add: sel.value});
      st.lang = sel.value;
    }, 'Đã thêm ngôn ngữ')}, '+'));
    tabs.replaceChildren(...p.progress.langs.map((l) => {
      const t = langTabState(l, src);
      return h('a', {class: `lv-tab ${t.state} ${t.code === st.lang ? 'cur' : ''}`, title: t.title, href: `#/p/${pid}/langs`,
        onclick: (e) => { e.preventDefault(); st.lang = t.code; st.keys = {}; load(); }},
        h('i', {class: `ldot ${t.state}`}), t.label, t.source ? h('span', {class: 'muted'}, ' gốc') : null);
    }), missing.length ? add : null);
  }

  // ---------------------------------------------------------------- script
  function renderScript() {
    const d = st.data;
    const s = d.script, c = d.check || {};
    const head = h('div', {class: 'lv-bar'});
    const ver = s ? `v${s.version}${s.approved ? ` · ✅ đã chốt (${s.approved_by || ''})` : ''}` : 'chưa có kịch bản';
    if (d.source) {
      head.append(h('div', {}, h('b', {}, `Kịch bản VI ${ver}`), h('span', {class: 'muted'}, ' · bản gốc, sửa ở tab Kịch bản')));
    } else {
      const approve = h('button', {onclick: () => act(() => api(`${base()}/approve`, {}), 'Đã chốt')}, 'Chốt');
      if (!s || s.approved || !canApprove(c.report) || (c.problems || []).length) approve.disabled = true;
      const rewrite = h('button', {class: 'ghost', title: d.outline ? '' : 'Chốt kịch bản tiếng Việt trước',
        onclick: () => act(() => api(`${base()}/rewrite`, {}), 'Đã giao agy viết lại')}, '✍️ Viết lại (agy)');
      rewrite.disabled = !d.outline;
      head.append(
        h('div', {}, h('b', {}, `Kịch bản ${st.lang.toUpperCase()} ${ver}`),
          c.report && c.report.sentences.length ? h('span', {class: 'muted'}, ' · ' + summaryLine(c.report)) : null,
          c.glossary_misses ? h('span', {class: 'muted'}, ` · tên lệch bảng thuật ngữ ${c.glossary_misses}`) : null),
        h('div', {class: 'row'}, rewrite,
          h('button', {class: 'ghost', onclick: () => act(() => api(`${base()}/review`, {}), 'Đã giao Claude soát')}, '🔍 Soát (Claude)'),
          approve));
    }
    const problems = (c.problems || []).length ? h('p', {class: 'error'}, c.problems.join(' · ')) : null;
    const rows = beatRows(d.outline, s, c.report, c.per_sentence, s && s.flags);
    const body = rows.length ? h('div', {class: 'lv-beats'}, rows.map((r) => h('div', {class: 'lv-beat'},
      h('div', {class: 'lv-left'},
        h('div', {class: 'muted'}, `${r.beat}${r.goal ? ' · ' + r.goal : ''}`),
        h('div', {class: 'chips'}, (r.facts || []).map((fid) => h('span', {class: 'chip', title: (d.facts[fid] || {}).claim || ''}, fid)))),
      h('div', {class: 'lv-right'}, r.sentences.length ? r.sentences.map((x) => h('div', {class: `sv-s ${colourClass(x.colour)}`, title: x.reasons.join('\n')},
        h('span', {class: 'sid muted'}, x.id), ' ', x.text,
        x.facts.length ? h('span', {class: 'chips'}, x.facts.map((f) => h('span', {class: 'chip'}, f))) : null,
        (x.colour === 'red' || x.colour === 'yellow') && x.reasons.length ? h('div', {class: 'reasons'}, x.reasons.join(' · ')) : null,
        x.flag ? h('div', {class: 'lv-flag'}, `🚩 ${x.flag.issue}`, h('div', {class: 'muted'}, `Dịch lại: ${x.flag.back_translation_vi}`)) : null))
        : h('p', {class: 'empty'}, d.source ? '' : 'Chưa có câu cho cảnh này.')))))
      : h('p', {class: 'empty'}, d.outline ? 'Chưa có kịch bản: bấm "Viết lại (agy)".' : 'Chốt kịch bản tiếng Việt trước, rồi agy mới viết lại được.');
    scriptCard.replaceChildren(h('h2', {}, '📝 Kịch bản'), head, problems, body);
  }

  // ---------------------------------------------------------------- voice
  function renderVoice() {
    const v = st.data.voice;
    const prep = h('button', {class: 'ghost', onclick: () => act(() => api(`${base()}/voice/prepare`, {}), 'Đã chuẩn bị phần giọng')},
      v.parts.length ? '↻ Chuẩn bị lại' : 'Chuẩn bị phần giọng');
    const list = h('ul', {class: 'list lv-parts'}, v.parts.map((p) => {
      const btn = h('button', {class: 'ghost small'}, copyLabel(false));
      btn.addEventListener('click', () => act(async () => {
        const r = await fetch(`${base()}/voice/parts/${p.part}.txt`);
        if (!r.ok) throw new Error('không tải được phần ' + p.part);
        await copy(btn, await r.text());
      }));
      return h('li', {}, h('b', {}, p.present ? '✅' : '⬜'), h('span', {class: 'grow'}, `Phần ${p.part}`,
        h('span', {class: 'muted'}, ` · ${p.seconds} s · ${p.chars} ký tự · lưu tên `), h('code', {}, partFileName(p)),
        (p.flags || []).length ? h('div', {class: 'error'}, p.flags.join(' · ')) : null), btn);
    }));
    const input = h('input', {type: 'file', accept: '.mp3,audio/mpeg', multiple: '', hidden: ''});
    const zone = h('label', {class: 'lv-drop'}, '⬇ Kéo thả các file mp3 vào đây (nhiều file một lần), hoặc bấm để chọn', input);
    input.addEventListener('change', () => dropFiles(input.files));
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('over'));
    zone.addEventListener('drop', (e) => { e.preventDefault(); zone.classList.remove('over'); dropFiles(e.dataTransfer.files); });
    voiceCard.replaceChildren(h('h2', {}, '🎙️ Giọng'), h('p', {class: v.stale ? 'error' : 'muted'}, voiceSummary(v)),
      h('div', {class: 'row'}, prep), list, v.parts.length ? zone : null);
  }

  function base64(file) {
    return new Promise((ok, bad) => {
      const r = new FileReader();
      r.onload = () => ok(String(r.result).split(',', 2)[1] || '');
      r.onerror = () => bad(new Error('không đọc được ' + file.name));
      r.readAsDataURL(file);
    });
  }

  async function dropFiles(files) {
    const done = [], errors = [];
    for (const f of Array.from(files || [])) {
      try {
        await api(`${base()}/voice/drop`, {name: f.name, data: await base64(f)});
        done.push(f.name);
      } catch (e) { errors.push(`${f.name}: ${e.message}`); }
    }
    say([done.length ? `Đã nhận ${done.join(', ')}` : '', ...errors].filter(Boolean).join(' · '), errors.length > 0);
    await load();
  }

  // ---------------------------------------------------------------- render (Plan 5 route) + upload
  function renderRender() {
    const d = st.data;
    const out = h('p', {class: 'muted'});
    const btn = h('button', {onclick: async () => {
      try { const j = await api(`/api/projects/${pid}/render/${st.lang}`, {}); out.textContent = `Đã giao render: ${j.label || j.id || 'ok'}`; }
      catch (e) { out.textContent = e.message; out.className = 'error'; }
    }}, `🎬 Render ${st.lang.toUpperCase()}`);
    renderCard.replaceChildren(h('h2', {}, '🎬 Render'),
      h('p', {class: 'muted'}, d.timing ? `Có timing (${Math.round(d.duration || 0)} s)` : 'Chưa có timing: cần đủ phần giọng'),
      h('div', {class: 'row'}, btn), out,
      d.render.length ? h('ul', {class: 'list'}, d.render.map((f) => h('li', {}, '📼 ', h('code', {}, f)))) : null);
  }

  function field(label, text) {
    const btn = h('button', {class: 'ghost small'}, copyLabel(false));
    btn.addEventListener('click', () => copy(btn, text));
    return h('div', {class: 'lv-field'}, h('div', {class: 'row'}, h('b', {class: 'grow'}, label), btn), h('pre', {}, text));
  }

  function renderUpload() {
    const d = st.data, u = d.upload;
    const desc = u ? u.description + (d.chapters ? '\n\n' + d.chapters : '') : '';
    uploadCard.replaceChildren(h('h2', {}, '📤 Upload'),
      h('div', {class: 'row'}, h('button', {class: 'ghost', onclick: () => act(() => api(`${base()}/upload_texts`, {}), 'Đã giao agy viết text upload')},
        u ? '↻ Viết lại text upload (agy)' : '✍️ Viết text upload (agy)')),
      u ? [field('Tiêu đề', u.title), field('Mô tả (kèm chương)', desc), field('Tags', (u.tags || []).join(', '))]
        : h('p', {class: 'empty'}, 'Chưa có text upload.'),
      !u && d.chapters ? field('Chương', d.chapters) : null,
      h('p', {class: 'muted'}, 'Khi upload: đặt nội dung thay đổi/tổng hợp = Có. Không thêm dòng "minh họa bằng AI".'),
      h('h3', {}, 'Thumbnail'), thumbBox, thumbForm);
    thumbBox.replaceChildren(d.thumb ? h('img', {src: `${base()}/thumb.png?t=${Date.now()}`, alt: 'thumbnail', class: 'lv-thumb'})
      : h('p', {class: 'empty'}, 'Chưa có thumbnail.'));
  }

  function buildThumbForm() {
    const bg = h('input', {placeholder: 'Nền đã duyệt, ví dụ BG03'});
    const hero = h('input', {placeholder: 'Tư thế, ví dụ tran-hung-dao/point.determined'});
    const title = h('input', {placeholder: 'Chữ trên thumbnail (tối đa 2 dòng)'});
    return h('div', {class: 'lv-thumbform'}, bg, hero, title,
      h('button', {onclick: () => act(() => api(`${base()}/thumb`, {bg: bg.value.trim(), hero: hero.value.trim(), title: title.value.trim()}),
        'Đã giao vẽ thumbnail')}, '🖼️ Tạo thumbnail'));
  }

  // ---------------------------------------------------------------- data
  async function load() {
    const p = await api(`/api/projects/${pid}`);
    if (!st.all.length) st.all = await api('/api/languages');
    if (!st.lang || !p.project.languages.includes(st.lang)) {
      st.lang = p.project.languages.find((c) => c !== (p.project.source_lang || 'vi')) || p.project.languages[0];
    }
    st.project = p;
    if (changed('tabs', [p.progress.langs, st.lang, p.project.languages])) renderTabs();
    const d = await api(base());
    if (d.lang !== st.lang) return;  // the owner switched tab while this was loading
    st.data = d;
    if (changed('script', [st.lang, d.script, d.check, d.outline, d.facts])) renderScript();
    if (changed('voice', [st.lang, d.voice])) renderVoice();
    if (changed('render', [st.lang, d.timing, d.duration, d.render])) renderRender();
    if (changed('upload', [st.lang, d.upload, d.chapters, d.thumb])) renderUpload();
  }

  load().catch((e) => say(e.message, true));
  const timer = setInterval(() => {
    if (!document.contains(root)) { clearInterval(timer); return; }
    if (document.visibilityState === 'visible') load().catch(() => {});
  }, 3000);
  return root;
}
