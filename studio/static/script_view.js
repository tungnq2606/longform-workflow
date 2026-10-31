// Script screen (Plan 3): Chat (agy) | Ngân hàng dữ kiện | Kịch bản. Mounted once per visit; polls its own data and
// re-renders only the parts that changed, so typing in the chat or editing a sentence is never interrupted.
import {factIcon, FACT_LABEL, colourClass, summaryLine, canApprove} from './lib.js';

const STATUSES = ['verified', 'weak', 'conflict', 'pending', 'rejected'];

export function mountScript(pid, {h, api}) {
  const st = {facts: {}, sources: {}, script: null, report: null, chat: [], rules: [], filter: '', selected: null,
    editing: null, col: 'script', keys: {}};
  const root = h('div', {class: 'sv'});
  const bar = h('div', {class: 'sv-bar card'});
  const rules = h('div', {class: 'sv-rules'});
  const colTabs = h('nav', {class: 'sv-coltabs'});
  const chatList = h('div', {class: 'sv-chatlist'});
  const chatBox = h('textarea', {rows: '3', placeholder: 'Nhắn agy: "viết lại câu s012 cho vui hơn", "tìm thêm về Vân Đồn"… (Ctrl+Enter)'});
  const chatCol = h('section', {class: 'card sv-col sv-chat', 'data-col': 'chat'}, h('h2', {}, '💬 Chat với agy'), chatList,
    h('form', {class: 'sv-chatform'}, chatBox, h('div', {class: 'row'}, h('button', {type: 'submit'}, 'Gửi'))));
  const factDetail = h('div', {class: 'sv-detail'});
  const factFilter = h('div', {class: 'sv-filter'});
  const factList = h('ul', {class: 'list sv-facts'});
  const factCol = h('section', {class: 'card sv-col', 'data-col': 'facts'}, h('h2', {}, '📚 Ngân hàng dữ kiện'),
    factFilter, factDetail, factList,
    h('div', {class: 'row'}, h('button', {class: 'ghost', onclick: addSource}, '+ Thêm nguồn (link)'),
      h('label', {class: 'ghost upload'}, '⬆ Tải file', h('input', {type: 'file', accept: '.pdf,.jpg,.jpeg,.png,.txt', hidden: ''}))));
  const scriptBody = h('div', {class: 'sv-script'});
  const scriptCol = h('section', {class: 'card sv-col', 'data-col': 'script'}, h('h2', {}, '📝 Kịch bản'), scriptBody);
  root.append(bar, rules, colTabs, h('div', {class: 'sv-cols'}, chatCol, factCol, scriptCol));

  chatCol.querySelector('form').addEventListener('submit', sendChat);
  chatBox.addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) sendChat(e); });
  factCol.querySelector('input[type=file]').addEventListener('change', upload);

  const changed = (name, value) => {
    const k = JSON.stringify(value);
    if (st.keys[name] === k) return false;
    st.keys[name] = k;
    return true;
  };

  async function act(fn) {
    try { await fn(); await load(); } catch (e) { alert(e.message); }
  }

  // ---------------------------------------------------------------- top bar
  function renderBar() {
    const r = st.report;
    const v = st.script ? `v${st.script.version}${st.script.approved ? ' · ✅ đã chốt' : ''}` : 'chưa có kịch bản';
    const approve = h('button', {onclick: () => act(() => api(`/api/projects/${pid}/script/approve`, {}))}, 'Chốt kịch bản');
    if (!canApprove(r) || (st.script && st.script.approved)) approve.disabled = true;
    approve.title = r && r.red ? 'Còn câu đỏ: sửa hoặc gắn dữ kiện đã kiểm trước' : '';
    bar.replaceChildren(
      h('div', {class: 'sv-summary'}, h('b', {}, `Kịch bản ${v}`), r && r.sentences.length ? h('span', {class: 'muted'}, ' · ' + summaryLine(r)) : null),
      h('div', {class: 'row'},
        h('button', {class: 'ghost', onclick: () => ask('Tìm tư liệu về gì?', 'research')}, '🔎 Tìm tư liệu'),
        h('button', {class: 'ghost', onclick: () => ask('Viết nháp thế nào? (dàn ý, độ dài, giọng)', 'draft')}, '✍️ Viết nháp'),
        h('button', {class: 'ghost', onclick: () => act(() => api(`/api/projects/${pid}/review`, {}))}, '🔍 Soát lại (Claude)'),
        approve));
  }

  function ask(question, what) {
    const request = prompt(question);
    if (request && request.trim()) act(() => api(`/api/projects/${pid}/${what}`, {request: request.trim()}));
  }

  function renderRules() {
    rules.replaceChildren(...st.rules.filter((r) => r.status === 'proposed').map((r) => h('div', {class: 'card sv-rule'},
      h('span', {class: 'grow'}, '📏 Quy tắc văn phong mới: ', h('b', {}, r.text)),
      h('button', {class: 'small', onclick: () => act(() => api(`/api/stylebook/vi/${r.id}/decide`, {keep: true}))}, 'Giữ'),
      h('button', {class: 'ghost small', onclick: () => act(() => api(`/api/stylebook/vi/${r.id}/decide`, {keep: false}))}, 'Bỏ'))));
  }

  function renderColTabs() {
    const names = {chat: 'Chat', facts: 'Dữ kiện', script: 'Kịch bản'};
    colTabs.replaceChildren(...Object.entries(names).map(([k, label]) =>
      h('a', {href: 'javascript:void 0', class: st.col === k ? 'cur' : '', onclick: () => { st.col = k; renderColTabs(); }}, label)));
    root.dataset.col = st.col;
  }

  // ---------------------------------------------------------------- chat
  function renderChat() {
    const who = {owner: 'Bạn', agy: 'agy', system: 'Studio'};
    chatList.replaceChildren(...(st.chat.length ? st.chat.map((m) => h('p', {class: `msg ${m.role}`},
      h('b', {}, who[m.role] || m.role), h('span', {class: 'muted'}, ` ${m.at}`), h('br'), m.text))
      : [h('p', {class: 'empty'}, 'Nhắn agy để tìm tư liệu, viết hoặc sửa câu. agy chỉ được dùng dữ kiện đã có trong ngân hàng.')]));
    chatList.scrollTop = chatList.scrollHeight;
  }

  async function sendChat(e) {
    e.preventDefault();
    const message = chatBox.value.trim();
    if (!message) return;
    await act(async () => { await api(`/api/projects/${pid}/chat`, {message}); chatBox.value = ''; });
  }

  // ---------------------------------------------------------------- facts
  function renderFacts() {
    const all = Object.values(st.facts);
    const count = (s) => all.filter((f) => f.status === s).length;
    factFilter.replaceChildren(
      h('button', {class: `chip ${st.filter ? '' : 'on'}`, onclick: () => { st.filter = ''; renderFacts(); }}, `Tất cả ${all.length}`),
      ...STATUSES.map((s) => h('button', {class: `chip ${st.filter === s ? 'on' : ''}`, title: FACT_LABEL[s],
        onclick: () => { st.filter = s; renderFacts(); }}, `${factIcon(s)} ${count(s)}`)));
    const shown = all.filter((f) => !st.filter || f.status === st.filter);
    factList.replaceChildren(...(shown.length ? shown.map((f) => h('li', {class: `click ${st.selected === f.id ? 'sel' : ''}`,
      onclick: () => { st.selected = f.id; renderFacts(); }},
      h('span', {}, factIcon(f.status)), h('b', {class: 'fid'}, f.id), h('span', {class: 'grow'}, f.claim),
      h('span', {class: 'tag'}, f.grade || '?')))
      : [h('li', {class: 'muted'}, all.length ? 'Không có dữ kiện ở mục này.' : 'Ngân hàng trống. Bấm "Tìm tư liệu" để agy đi gom nguồn.')]));
    renderDetail();
  }

  function renderDetail() {
    const f = st.facts[st.selected];
    if (!f) { factDetail.replaceChildren(); return; }
    const src = st.sources[f.source] || {};
    const page = (f.page_file || src.page_file || '').match(/(\d{3})\.txt$/);
    const set = (status) => act(() => api(`/api/projects/${pid}/facts/${f.id}/status`, {status, note: 'chủ kênh chỉnh tay'}));
    factDetail.replaceChildren(h('div', {class: 'sv-fact'},
      h('div', {class: 'row'}, h('b', {}, `${factIcon(f.status)} ${f.id}`), h('span', {class: 'muted'}, FACT_LABEL[f.status] || f.status),
        h('span', {class: 'grow'}), h('button', {class: 'ghost small', onclick: () => { st.selected = null; renderFacts(); }}, '✕')),
      h('p', {}, f.claim),
      h('blockquote', {}, f.quote),
      h('p', {class: 'muted'}, 'Nguồn: ', /^https?:/.test(src.url || '') ? h('a', {href: src.url, target: '_blank', rel: 'noopener'}, src.title || src.url) : (src.title || src.url || '?'),
        ` · hạng ${f.grade || '?'}`, f.location ? ` · ${f.location}` : '', f.reports ? ` · ${f.reports} ghi` : '',
        f.legend ? ' · truyền thuyết' : '', f.conflicts_with && f.conflicts_with.length ? ` · vênh với ${f.conflicts_with.join(', ')}` : ''),
      f.checked_by ? h('p', {class: 'muted'}, `Kiểm bởi ${f.checked_by}: ${f.check_note || ''}`) : null,
      h('div', {class: 'row'},
        page ? h('a', {class: 'ghost btnlink', href: `/api/projects/${pid}/pages/${page[1]}`, target: '_blank'}, 'Xem trang đã lưu') : null,
        h('span', {class: 'grow'}),
        h('button', {class: 'ghost small', title: 'Đánh dấu đã kiểm', onclick: () => set('verified')}, '✅'),
        h('button', {class: 'ghost small', title: 'Nguồn yếu', onclick: () => set('weak')}, '⚠️'),
        h('button', {class: 'ghost small', title: 'Loại', onclick: () => set('rejected')}, '✖'))));
  }

  function addSource() {
    const url = prompt('Dán link nguồn (agy sẽ đọc và rút dữ kiện):');
    if (url && url.trim()) act(() => api(`/api/projects/${pid}/research`, {request: `Đọc trang này và rút dữ kiện: ${url.trim()}`}));
  }

  function upload(e) {
    const file = e.target.files[0];
    e.target.value = '';
    if (!file) return;
    if (file.size > 30 * 1024 * 1024) { alert('File lớn quá 30 MB'); return; }
    const reader = new FileReader();
    reader.onload = () => act(() => api(`/api/projects/${pid}/sources/upload`,
      {name: file.name, data: String(reader.result).split(',')[1] || ''}));
    reader.readAsDataURL(file);
  }

  // ---------------------------------------------------------------- script
  function renderScript() {
    const s = st.script;
    if (!s) {
      scriptBody.replaceChildren(h('p', {class: 'empty'}, 'Chưa có kịch bản. Khi ngân hàng có dữ kiện đã kiểm, bấm "Viết nháp": agy viết, rồi Claude tự soát.'));
      return;
    }
    const rep = Object.fromEntries((st.report ? st.report.sentences : []).map((r) => [r.id, r]));
    const notes = Object.fromEntries((s.review_notes || []).map((n) => [n.sentence, n.note]));
    scriptBody.replaceChildren(...s.chapters.map((ch) => h('div', {class: 'sv-chapter'},
      h('h3', {}, `${ch.id} · ${ch.title}`),
      ch.beats.map((b) => h('div', {class: 'sv-beat'},
        h('div', {class: 'sv-beathead muted'}, `${b.id}${b.goal ? ' · ' + b.goal : ''}`),
        b.sentences.map((x) => sentence(x, rep[x.id] || {}, notes[x.id])))))));
  }

  function sentence(x, r, note) {
    if (st.editing === x.id) return editor(x);
    return h('div', {class: `sv-s ${colourClass(r.colour)}`, title: (r.reasons || []).join('\n'), onclick: () => { st.editing = x.id; renderScript(); }},
      h('span', {class: 'sid muted'}, x.id), ' ', x.text,
      x.facts.length ? h('span', {class: 'chips'}, x.facts.map((fid) => h('button', {class: 'chip', onclick: (e) => {
        e.stopPropagation(); st.selected = fid; st.col = 'facts'; renderColTabs(); renderFacts();
      }}, `${factIcon((st.facts[fid] || {}).status)} ${fid}`))) : null,
      r.colour === 'red' || r.colour === 'yellow' ? h('div', {class: 'reasons'}, (r.reasons || []).join(' · ')) : null,
      note ? h('div', {class: 'reasons muted'}, `Claude: ${note}`) : null);
  }

  function editor(x) {
    const text = h('textarea', {rows: '3'});
    text.value = x.text;
    const facts = h('input', {placeholder: 'F001, F004'});
    facts.value = x.facts.join(', ');
    const save = () => act(async () => {
      await api(`/api/projects/${pid}/script/sentence`,
        {id: x.id, text: text.value, facts: facts.value.split(/[\s,]+/).filter(Boolean)});
      st.editing = null;
    });
    return h('div', {class: 'sv-edit card'}, h('b', {}, `Sửa ${x.id}`), text, h('label', {class: 'muted'}, 'Dữ kiện: ', facts),
      h('div', {class: 'row end'}, h('button', {class: 'ghost', onclick: () => { st.editing = null; renderScript(); }}, 'Huỷ'),
        h('button', {onclick: save}, 'Lưu')));
  }

  // ---------------------------------------------------------------- data
  async function load() {
    const [fb, sc, ch, book] = await Promise.all([
      api(`/api/projects/${pid}/facts`), api(`/api/projects/${pid}/script`), api(`/api/projects/${pid}/chat`),
      api('/api/stylebook/vi')]);
    if (changed('facts', fb)) { st.facts = fb.facts; st.sources = fb.sources; renderFacts(); }
    if (changed('script', sc)) { st.script = sc.script; st.report = sc.report; renderBar(); if (!st.editing) renderScript(); }
    if (changed('chat', ch)) { st.chat = ch; renderChat(); }
    if (changed('rules', book.rules)) { st.rules = book.rules; renderRules(); }
  }

  renderColTabs();
  renderBar();
  load().catch(() => {});
  const timer = setInterval(() => {
    if (!document.contains(root)) { clearInterval(timer); return; }
    if (document.visibilityState === 'visible') load().catch(() => {});
  }, 3000);
  return root;
}
