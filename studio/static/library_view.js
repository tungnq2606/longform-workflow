// Library screen (Plan 4): hero kits with their poses (+ new pose), reusable backgrounds, code-drawn crowd factions
// and the style lock. Mounted once per visit; reloads every 5 s without touching an open new-pose form.

const COLOUR = /^#[0-9a-f]{3,8}$/i;
const POSE_KEY = /^[a-z0-9-]+\.[a-z0-9-]+$/;
const FACTION_VI = {daiviet: 'Đại Việt', nguyen: 'quân Nguyên'};
const LOOK_VI = {round: 'tròn', cone: 'nón nhọn', spear: 'giáo', sword: 'kiếm'};
const vi = (w) => LOOK_VI[w] || w;

export function mountLibrary({h, api}) {
  const st = {kits: [], home: null, factions: [], form: null, keys: {}, note: ''};
  const root = h('div', {class: 'lv'});
  const kitsEl = h('section', {class: 'card'});
  const bgEl = h('section', {class: 'card'});
  const crowdEl = h('section', {class: 'card'});
  const styleEl = h('section', {class: 'card'});
  root.append(h('div', {class: 'lv-grid'}, h('div', {}, kitsEl, bgEl), h('div', {}, crowdEl, styleEl)));

  const changed = (name, value) => {
    const k = JSON.stringify(value);
    if (st.keys[name] === k) return false;
    st.keys[name] = k;
    return true;
  };

  function poseForm(kit) {
    const key = h('input', {placeholder: 'tu-the.bieu-cam, ví dụ point.determined', required: ''});
    const desc = h('textarea', {rows: '3', placeholder: 'Tả tư thế bằng tiếng Anh: "pointing ahead with the right arm, calm face"'});
    const projects = (st.home && st.home.projects) || [];
    const proj = h('select', {}, projects.map((p) => h('option', {value: p.id}, `${p.id} · ${p.title}`)));
    const err = h('p', {class: 'error', hidden: ''});
    const submit = async (e) => {
      e.preventDefault();
      err.hidden = true;
      if (!POSE_KEY.test(key.value.trim())) { err.textContent = 'Tên tư thế phải dạng tu-the.bieu-cam (chữ thường, không dấu).'; err.hidden = false; return; }
      try {
        const it = await api(`/api/library/kits/${encodeURIComponent(kit.id)}/new_pose`,
          {project: proj.value, pose_key: key.value.trim(), description: desc.value});
        st.form = null;
        st.note = `Đã xếp hàng ${it.id} (${kit.id} · ${it.pose_key}) ở dự án ${proj.value}: agy vẽ từ model sheet, rồi chấm; bạn duyệt ở tab Hình ảnh.`;
        renderKits();
      } catch (ex) { err.textContent = ex.message; err.hidden = false; }
    };
    const form = h('form', {class: 'lv-form'},
      h('label', {}, 'Tên tư thế', key), h('label', {}, 'Mô tả', desc), h('label', {}, 'Dự án', proj), err,
      h('div', {class: 'row end'}, h('button', {type: 'button', class: 'ghost', onclick: () => { st.form = null; renderKits(); }}, 'Huỷ'),
        h('button', {type: 'submit'}, 'Vẽ tư thế mới')));
    if (!projects.length) form.replaceChildren(h('p', {class: 'muted'}, 'Cần một dự án trước: tư thế mới được vẽ và duyệt trong dự án.'));
    form.addEventListener('submit', submit);
    return form;
  }

  function renderKits() {
    kitsEl.replaceChildren(...[h('h2', {}, 'Nhân vật quan trọng', h('span', {class: 'count'}, String(st.kits.length))),
      st.note ? h('p', {class: 'lv-note'}, st.note) : null,
      st.kits.length ? h('div', {class: 'lv-kits'}, st.kits.map((k) => h('div', {class: 'lv-kit'},
        h('div', {class: 'row lv-kithead'}, h('b', {}, k.name), h('span', {class: 'muted'}, `${k.id} · ${k.poses.length} tư thế · cao ${k.height} px`),
          h('span', {class: 'grow'}),
          h('button', {class: 'ghost small', onclick: () => { st.form = st.form === k.id ? null : k.id; renderKits(); }}, '+ Tư thế mới')),
        st.form === k.id ? poseForm(k) : null,
        h('div', {class: 'lv-poses'}, k.poses.map((p) => h('figure', {},
          h('img', {src: p.thumb, alt: p.key, loading: 'lazy'}), h('figcaption', {}, p.key)))))))
        : h('p', {class: 'empty'}, 'Chưa có bộ nhân vật nào.'),
      h('p', {class: 'muted'}, 'Tư thế mới: agy sửa từ model sheet đã duyệt → agy chấm so với bộ → bạn duyệt → thêm vào bộ.')].filter(Boolean));
  }

  function renderBackgrounds() {
    const bgs = st.home ? st.home.library.backgrounds : [];
    bgEl.replaceChildren(h('h2', {}, 'Nền dùng lại', h('span', {class: 'count'}, String(bgs.length))),
      bgs.length ? h('div', {class: 'lv-bgs'}, bgs.map((b) => h('figure', {},
        h('img', {src: `/api/thumb/bg/${encodeURIComponent(b.id)}`, alt: b.id, loading: 'lazy'}), h('figcaption', {}, b.id))))
        : h('p', {class: 'empty'}, 'Chưa có nền nào. Nền đã duyệt trong dự án có nút "Đưa vào thư viện".'));
  }

  function swatch(colour, label) {
    const s = h('span', {class: 'lv-swatch', title: `${label} ${colour}`});
    if (COLOUR.test(colour || '')) s.style.background = colour;
    return s;
  }

  function renderCrowds() {
    crowdEl.replaceChildren(h('h2', {}, 'Đám đông (người que, Remotion vẽ)'),
      st.factions.length ? h('ul', {class: 'list'}, st.factions.map((f) => h('li', {},
        swatch(f.tunic, 'áo'), swatch(f.skin, 'da'), h('b', {}, FACTION_VI[f.id] || f.id),
        h('span', {class: 'grow muted'}, `mũ ${vi(f.helmet)} · ${vi(f.weapon)}${f.shield === 'true' ? ' · khiên' : ''}`))))
        : h('p', {class: 'empty'}, 'Chưa có phe nào.'),
      h('p', {class: 'muted'}, 'Chỉ xem: phe sửa trong tools/anim/src/longform/factions.ts (Phần 5).'));
  }

  function renderStyle() {
    const styles = st.home ? st.home.library.styles : [];
    styleEl.replaceChildren(h('h2', {}, 'Style lock'),
      styles.length ? h('ul', {class: 'list'}, styles.map((s) => h('li', {},
        h('span', {}, s.approved ? '✅' : '⏳'), h('b', {}, s.id), h('span', {class: 'grow muted'}, s.approved ? 'đã khóa, dùng cho mọi prompt ảnh' : 'chưa duyệt'))))
        : h('p', {class: 'empty'}, 'Chưa có style lock.'));
  }

  async function load() {
    const [kits, home, factions] = await Promise.all([api('/api/library/kits'), api('/api/home'), api('/api/library/factions')]);
    st.home = home;
    if (changed('home', [home.library, home.projects.map((p) => p.id)])) { renderBackgrounds(); renderStyle(); }
    if (st.form === null && changed('kits', kits)) { st.kits = kits; renderKits(); }
    if (changed('factions', factions)) { st.factions = factions; renderCrowds(); }
  }

  renderKits();
  renderBackgrounds();
  renderCrowds();
  renderStyle();
  load().catch(() => {});
  const timer = setInterval(() => {
    if (!document.contains(root)) { clearInterval(timer); return; }
    if (document.visibilityState === 'visible') load().catch(() => {});
  }, 5000);
  return root;
}
