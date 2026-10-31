import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import {
  WHO,
  ROOMS,
  STAFF,
  ROOM_OF_STEP,
  TAB_OF_STEP,
  roomById,
  addRBox,
  stdMat,
  makeSignTexture,
} from './constants.js';
import { buildOutdoorWorld } from './outdoor.js';
import { buildArchitecture } from './architecture.js';
import { buildAllStaffAndCouriers } from './characters.js';
import {
  HandoffSystem,
  updateStaffAnimations,
  updateRoomPropAnimations,
  updateOutdoorAnimations,
} from './animations.js';
import { setupDispatchModal } from './dispatch.js';

const $ = s => document.querySelector(s);
const esc = s =>
  String(s ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[c]));
const fmt = t => Math.floor(t / 60) + ':' + String(Math.floor(t % 60)).padStart(2, '0');
const now = () => Date.now() / 1000;

// Wait briefly for self-hosted Be Vietnam Pro fonts before painting 3D canvas signs
try {
  await Promise.race([
    Promise.all([
      document.fonts.load('700 48px "Be Vietnam Pro"'),
      document.fonts.load('800 64px "Be Vietnam Pro"'),
    ]),
    new Promise(r => setTimeout(r, 900)),
  ]);
} catch (_) {}

// ------------------------------------------------------------ Renderer & Scene Setup
const app = $('#app');
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.06;
app.appendChild(renderer.domElement);

const labelRenderer = new CSS2DRenderer();
labelRenderer.domElement.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:4';
app.appendChild(labelRenderer.domElement);

const scene = new THREE.Scene();

// Subtle Studio IBL reflections for clay, glass, brass & brushed aluminum
try {
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.38;
  pmrem.dispose();
} catch (_) {}

// Camera & Isometric Controls
const VIEW = 46;
const camera = new THREE.OrthographicCamera(-VIEW, VIEW, VIEW, -VIEW, 0.1, 500);
const HOME = {
  pos: new THREE.Vector3(52, 58, 62),
  target: new THREE.Vector3(11, 0, -1),
  zoom: 0.77,
};
camera.position.copy(HOME.pos);
camera.zoom = HOME.zoom;
camera.updateProjectionMatrix();

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.copy(HOME.target);
controls.enableDamping = true;
controls.dampingFactor = 0.07;
controls.screenSpacePanning = false;
controls.minZoom = 0.52;
controls.maxZoom = 4.2;
controls.minPolarAngle = 0.32;
controls.maxPolarAngle = 1.18;
controls.mouseButtons = {
  LEFT: THREE.MOUSE.PAN,
  MIDDLE: THREE.MOUSE.DOLLY,
  RIGHT: THREE.MOUSE.ROTATE,
};
controls.touches = {
  ONE: THREE.TOUCH.PAN,
  TWO: THREE.TOUCH.DOLLY_ROTATE,
};

// Lighting & Atmosphere System (Day / Sunset / Night)
const hemiLight = new THREE.HemisphereLight(0xfff9ee, 0x7b8876, 1.45);
scene.add(hemiLight);

const sun = new THREE.DirectionalLight(0xfffaf0, 1.75);
sun.position.set(-34, 62, 42);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, {
  left: -72,
  right: 72,
  top: 52,
  bottom: -52,
  near: 4,
  far: 180,
});
sun.shadow.bias = -0.0004;
scene.add(sun);

scene.fog = new THREE.FogExp2(0xdfe5ec, 0.0022);

const pickables = [];
const outdoor = buildOutdoorWorld(scene);
const { archProps } = buildArchitecture(scene, pickables);
const { couriers } = buildAllStaffAndCouriers(scene, pickables);
const handoffSystem = new HandoffSystem(couriers);

// Post-Processing: Subtle Physical Bloom for Emissive Lights & Screens
let composer = null;
let bloomPass = null;
try {
  composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  bloomPass = new UnrealBloomPass(
    new THREE.Vector2(window.innerWidth, window.innerHeight),
    0.18,
    0.45,
    0.88
  );
  composer.addPass(bloomPass);
  composer.addPass(new OutputPass());
} catch (_) {
  composer = null;
}

// Atmosphere Presets
const ATMO_MODES = ['day', 'sunset', 'night'];
const ATMO_LABELS = {
  day: 'Ban ngày',
  sunset: 'Hoàng hôn',
  night: 'Ban đêm',
};
let currentAtmo =
  new URLSearchParams(location.search).get('atmo') ||
  localStorage.getItem('office_atmo') ||
  'day';

function applyAtmosphere(mode) {
  currentAtmo = ATMO_MODES.includes(mode) ? mode : 'day';
  localStorage.setItem('office_atmo', currentAtmo);
  document.documentElement.setAttribute('data-atmo', currentAtmo);

  const btn = $('#atmo-btn');
  if (btn) btn.textContent = ATMO_LABELS[currentAtmo];

  if (currentAtmo === 'day') {
    scene.background = new THREE.Color(0xdfe5ec);
    scene.fog.color.setHex(0xdfe5ec);
    hemiLight.color.setHex(0xfff9ee);
    hemiLight.groundColor.setHex(0x7b8876);
    hemiLight.intensity = 1.45;
    sun.color.setHex(0xfffaf0);
    sun.intensity = 1.75;
    sun.position.set(-34, 62, 42);
    for (const rl of archProps.roomLights) rl.intensity = 0.45;
    for (const sl of outdoor.streetLights) sl.emissiveIntensity = 0.25;
    if (bloomPass) bloomPass.strength = 0.16;
  } else if (currentAtmo === 'sunset') {
    scene.background = new THREE.Color(0x2d2235);
    scene.fog.color.setHex(0x2d2235);
    hemiLight.color.setHex(0xffbfa0);
    hemiLight.groundColor.setHex(0x4a3946);
    hemiLight.intensity = 1.15;
    sun.color.setHex(0xff9452);
    sun.intensity = 1.65;
    sun.position.set(-55, 34, 38);
    for (const rl of archProps.roomLights) rl.intensity = 1.35;
    for (const sl of outdoor.streetLights) sl.emissiveIntensity = 1.2;
    if (bloomPass) bloomPass.strength = 0.28;
  } else {
    scene.background = new THREE.Color(0x11161f);
    scene.fog.color.setHex(0x11161f);
    hemiLight.color.setHex(0x7a96b8);
    hemiLight.groundColor.setHex(0x1d2530);
    hemiLight.intensity = 0.85;
    sun.color.setHex(0x9ab8e6);
    sun.intensity = 0.72;
    sun.position.set(-28, 54, 30);
    for (const rl of archProps.roomLights) rl.intensity = 1.85;
    for (const sl of outdoor.streetLights) sl.emissiveIntensity = 1.6;
    if (bloomPass) bloomPass.strength = 0.34;
  }
}
applyAtmosphere(currentAtmo);

$('#atmo-btn')?.addEventListener('click', () => {
  const nextIdx = (ATMO_MODES.indexOf(currentAtmo) + 1) % ATMO_MODES.length;
  applyAtmosphere(ATMO_MODES[nextIdx]);
});

// ------------------------------------------------------------ Stage Dock (Room Quick-Jump Bar)
const stageCore = $('#stage-dock-core');
if (stageCore) {
  const allBtn = `<button class="room-pill active" data-jump="all">Toàn cảnh</button>`;
  const roomBtns = ROOMS.map(
    r =>
      `<button class="room-pill" data-jump="${esc(r.id)}"><span class="code">${esc(r.code)}</span> ${esc(
        r.name.replace('Phòng ', '')
      )}</button>`
  ).join('');
  stageCore.innerHTML = allBtn + roomBtns;

  stageCore.querySelectorAll('[data-jump]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.jump;
      if (id === 'all') select(null);
      else select({ type: 'room', id });
    });
  });
}

function updateStageDockActive() {
  if (!stageCore) return;
  const activeRoomId =
    S.sel?.type === 'room'
      ? S.sel.id
      : S.sel?.type === 'staff'
      ? STAFF.find(x => x.id === S.sel.id)?.room
      : null;
  stageCore.querySelectorAll('[data-jump]').forEach(btn => {
    const j = btn.dataset.jump;
    btn.classList.toggle('active', activeRoomId ? j === activeRoomId : j === 'all');
  });
}

// ------------------------------------------------------------ Live Data State & Polling
const S = {
  state: null,
  ch: new URLSearchParams(location.search).get('ch') || localStorage.getItem('ch') || 'fossil-receipts',
  sel: null,
  folders: [],
  zenMode: false,
  prevRunningIds: new Map(),
  prevVideoRooms: new Map(),
};

function staffJobs(s) {
  const jobs = (S.state?.jobs || []).filter(
    j => s.actions && (s.actions.includes(j.action) || (!j.action && s.actions.includes(j.kind)))
  );
  return {
    running: jobs.filter(j => j.status === 'running'),
    recent: jobs.filter(j => j.status !== 'running'),
  };
}

function workersOf(j) {
  const m = /--workers (\d+)/.exec(j.cmd || '');
  return m ? +m[1] : j.action === 'redo' ? 1 : 4;
}

function current(s) {
  const { running, recent } = staffJobs(s);
  let j = running[0];
  if (j && s.painter && s.painter > workersOf(j)) j = null;
  const last = recent[0];
  const fresh = last && last.ended && now() - last.ended < (last.status === 'done' ? 25 : 180);
  return { job: j, last: fresh ? last : null };
}

function ownerTodo() {
  const c = (S.state?.channels || []).find(c => c.id === S.ch);
  return c ? c.list.filter(v => !v.published && /Bạn/i.test(v.next_who)) : [];
}

function channelVideos() {
  const c = (S.state?.channels || []).find(c => c.id === S.ch);
  return c ? c.list.filter(v => !v.published) : [];
}

async function poll() {
  try {
    S.state = await (await fetch('/api/state')).json();
  } catch (_) {
    $('#run-status').innerHTML = '<span class="muted">Mất kết nối server</span>';
    setTimeout(poll, 4000);
    return;
  }

  const sel = $('#ch');
  if (sel.options.length !== S.state.channels.length) {
    sel.innerHTML = S.state.channels
      .map(c => `<option value="${esc(c.id)}">${esc(c.name)}</option>`)
      .join('');
  }
  if (!S.state.channels.some(c => c.id === S.ch)) {
    const preferFossil = S.state.channels.find(c => c.id === 'fossil-receipts');
    S.ch = (preferFossil || S.state.channels[0]).id;
  }
  sel.value = S.ch;

  const running = S.state.jobs.filter(j => j.status === 'running');
  const runHtml = running.length
    ? `<span class="status-pulse busy"></span>${running.length} việc đang chạy`
    : `<span class="status-pulse"></span>Nhịp sống văn phòng`;
  if (S._lastRunHtml !== runHtml) {
    S._lastRunHtml = runHtml;
    $('#run-status').innerHTML = runHtml;
  }

  const feedHtml =
    S.state.jobs
      .slice(0, 6)
      .map(
        j =>
          `<div class="feed-row"><span class="chip ${esc(j.status)}">${esc(j.status)}</span><span>${esc(
            j.label
          )}</span></div>`
      )
      .join('') || '<div class="muted small">Đang chạy mô phỏng nhịp làm việc giữa các phòng ban.</div>';
  if (S._lastFeedHtml !== feedHtml) {
    S._lastFeedHtml = feedHtml;
    $('#feed-list').innerHTML = feedHtml;
  }

  detectRealHandoffs();
  layoutFolders();
  renderPanel();
  setTimeout(poll, running.length ? 1500 : 4000);
}

function detectRealHandoffs() {
  if (!S.state) return;
  // 1. Check if a video changed its next-step room
  for (const ch of S.state.channels || []) {
    for (const v of ch.list || []) {
      if (v.published) continue;
      const key = `${ch.id}/${v.slug}`;
      const newRoom = ROOM_OF_STEP[v.next] || 'publish';
      const oldRoom = S.prevVideoRooms.get(key);
      if (oldRoom && oldRoom !== newRoom) {
        const rFrom = roomById[oldRoom];
        const rTo = roomById[newRoom];
        handoffSystem.enqueue({
          fromRoom: oldRoom,
          toRoom: newRoom,
          label: `Video ${v.slug.slice(0, 3)}: ${rFrom.name.replace('Phòng ', '')} → ${rTo.name.replace('Phòng ', '')}`,
          isRender: oldRoom === 'edit',
        });
      }
      S.prevVideoRooms.set(key, newRoom);
    }
  }

  // 2. Check if a running job just finished (running -> done)
  const currentRunning = new Map();
  for (const j of S.state.jobs || []) {
    if (j.status === 'running') {
      const worker = STAFF.find(
        s => s.actions && (s.actions.includes(j.action) || (!j.action && s.actions.includes(j.kind)))
      );
      if (worker) currentRunning.set(j.id, { room: worker.room, job: j });
    } else if (j.status === 'done' && S.prevRunningIds.has(j.id)) {
      const prev = S.prevRunningIds.get(j.id);
      const nextRoom =
        prev.room === 'edit'
          ? 'publish'
          : prev.room === 'research'
          ? 'script'
          : prev.room === 'script'
          ? 'art'
          : prev.room === 'art'
          ? 'voice'
          : prev.room === 'voice'
          ? 'edit'
          : 'boss';
      handoffSystem.enqueue({
        fromRoom: prev.room,
        toRoom: nextRoom,
        label: `Xong: ${j.label}`,
        isRender: j.kind === 'render' || j.action === 'render',
      });
    }
  }
  S.prevRunningIds = currentRunning;
}

$('#ch').onchange = e => {
  S.ch = e.target.value;
  localStorage.setItem('ch', S.ch);
  S.sel = null;
  layoutFolders();
  renderPanel();
  updateStageDockActive();
};

// ------------------------------------------------------------ 3D Video Folders on Room Handoff Tables (No floating HTML tags!)
const folderPlateGeo = new THREE.PlaneGeometry(1.02, 0.66);
let folderKey = '';
function layoutFolders() {
  const c = (S.state?.channels || []).find(c => c.id === S.ch);
  const key = c
    ? S.ch + JSON.stringify(c.list.map(v => [v.slug, v.next, v.next_who, v.published]))
    : '';
  if (key === folderKey) return;
  folderKey = key;

  for (const f of S.folders) {
    f.mesh.parent.remove(f.mesh);
    f.topMat?.dispose();
    f.topTex?.dispose();
  }
  S.folders = [];
  if (!c) return;

  const perRoom = {};
  for (const v of c.list.filter(v => !v.published)) {
    const r = roomById[ROOM_OF_STEP[v.next] || 'publish'];
    const k = (perRoom[r.id] = (perRoom[r.id] || 0) + 1);
    const wait = /Bạn/i.test(v.next_who);

    const folderGroup = new THREE.Group();
    folderGroup.position.set(
      r.table.x - 1.05 + ((k - 1) % 2) * 1.35,
      0.98 + Math.floor((k - 1) / 2) * 0.22,
      r.table.z
    );
    r.group.add(folderGroup);

    const binderMat = stdMat(wait ? 0xe87b64 : 0xf2c955, 0.48, 0.08);
    const binder = addRBox(folderGroup, 1.15, 0.16, 0.82, binderMat, 0, 0, 0, 0.04);
    binder.userData = { type: 'video', slug: v.slug };
    pickables.push(binder);

    // Crisp 3D top label plaque printed directly onto the binder cover
    const topTex = makeSignTexture({
      code: v.slug.slice(0, 3),
      title: wait ? 'CHỜ BẠN' : 'HỒ SƠ',
      subtitle: '',
      accent: wait ? '#cf3f3f' : '#1f7a54',
      bg: '#1c232d',
      fg: '#ffffff',
      border: '#cfa968',
      width: 512,
      height: 160,
      compact: true,
    });
    const topMat = new THREE.MeshBasicMaterial({ map: topTex });
    const topPlate = new THREE.Mesh(folderPlateGeo, topMat);
    topPlate.rotation.x = -Math.PI / 2;
    topPlate.position.y = 0.085;
    topPlate.userData = { type: 'video', slug: v.slug };
    folderGroup.add(topPlate);
    pickables.push(topPlate);

    S.folders.push({ mesh: folderGroup, binder, topMat, topTex, v, room: r });
  }

  for (let i = pickables.length - 1; i >= 0; i--) {
    if (
      pickables[i].userData.type === 'video' &&
      !S.folders.some(f => f.binder === pickables[i] || f.mesh.children.includes(pickables[i]))
    ) {
      pickables.splice(i, 1);
    }
  }
}

// ------------------------------------------------------------ Side Inspector Panel & Quick Dispatch Modal
const dispatchModal = setupDispatchModal({
  getState: () => S.state,
  getChannel: () => S.ch,
  onDispatched: staff => {
    select({ type: 'staff', id: staff.id });
    poll();
  },
});

function openLink(v, step) {
  return `/#v/${encodeURIComponent(S.ch)}/${encodeURIComponent(v)}/${TAB_OF_STEP[step] || 'script'}`;
}
function jobVideoLink(j) {
  if (!j.video) return '';
  const [ch, slug] = j.video.split('/');
  return `/#v/${encodeURIComponent(ch)}/${encodeURIComponent(slug)}/script`;
}

async function renderPanel() {
  const p = $('#panel-core');
  const sel = S.sel;
  if (!S.state || !p) return;

  if (!sel) {
    const todo = ownerTodo();
    const activeVids = channelVideos();
    const runningCount = S.state.jobs.filter(j => j.status === 'running').length;

    p.innerHTML = `
      <div class="panel-top-row">
        <h2>Toàn cảnh Studio</h2>
        <span class="chip">${esc(ROOMS.length)} phòng ban</span>
      </div>
      <div class="muted small">Bấm vào nhân vật để xem chi tiết, hoặc <b>bấm đúp</b> vào nhân vật để giao việc nhanh.</div>
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-val">${STAFF.length}</div><div class="stat-lbl">Nhân sự</div></div>
        <div class="stat-card"><div class="stat-val">${activeVids.length}</div><div class="stat-lbl">Hồ sơ mở</div></div>
        <div class="stat-card"><div class="stat-val">${runningCount}</div><div class="stat-lbl">Việc chạy</div></div>
      </div>
      ${
        todo.length
          ? `<h3>Đang chờ bạn duyệt (${todo.length})</h3>
             <ul class="list">${todo
               .map(
                 v =>
                   `<li data-video="${esc(v.slug)}"><span class="folder-badge wait">Video ${esc(
                     v.slug.slice(0, 3)
                   )}</span><span style="flex:1">${esc(v.next_label)}</span></li>`
               )
               .join('')}</ul>`
          : ''
      }
      <h3>Các phòng ban sản xuất</h3>
      <ul class="list">
        ${ROOMS.map(r => {
          const rStaff = STAFF.filter(s => s.room === r.id);
          const busy = rStaff.some(s => current(s).job);
          const vCount = S.folders.filter(f => f.room.id === r.id).length;
          return `<li data-room="${esc(r.id)}">
            <span class="chip">${esc(r.code)}</span>
            <span style="flex:1"><b>${esc(r.name)}</b> <span class="muted small">(${rStaff.length} người)</span></span>
            ${
              busy
                ? '<span class="chip running">đang làm</span>'
                : vCount
                ? `<span class="folder-badge">${vCount} hồ sơ</span>`
                : '<span class="chip">nhịp thường</span>'
            }
          </li>`;
        }).join('')}
      </ul>
      <h3>Danh sách nhân sự (${STAFF.length})</h3>
      <ul class="list">
        ${STAFF.map(s => {
          const c = current(s);
          return `<li data-staff="${esc(s.id)}" title="Bấm đúp để giao việc nhanh">
            <span class="role-swatch" style="background:var(--${esc(s.who)})"></span>
            <span style="flex:1"><b>${esc(s.plaque)}</b> <span class="muted small">(${esc(s.name)})</span></span>
            ${
              c.job
                ? '<span class="chip running">đang làm</span>'
                : c.last
                ? `<span class="chip ${esc(c.last.status)}">${c.last.status === 'done' ? 'vừa xong' : 'lỗi'}</span>`
                : '<span class="chip">trực ca</span>'
            }
          </li>`;
        }).join('')}
      </ul>
    `;
  } else if (sel.type === 'staff') {
    const s = STAFF.find(x => x.id === sel.id);
    const c = current(s);
    const { recent } = staffJobs(s);
    const j = c.job;
    let log = '';
    if (j) {
      try {
        const r = await (await fetch('/api/job?id=' + j.id)).json();
        log = r.text
          .split('\n')
          .filter(l => l && !l.startsWith('$'))
          .slice(-14)
          .join('\n');
      } catch (_) {}
    }
    if (S.sel !== sel) return;

    p.innerHTML = `
      <div class="panel-top-row">
        <button id="back">Toàn công ty</button>
        <span class="chip">${esc(roomById[s.room].name)}</span>
      </div>
      <h2>${esc(s.plaque)}</h2>
      <div class="muted small">${esc(WHO[s.who])} · ${esc(s.role)}</div>
      <div class="row" style="margin-top:10px">
        <button class="pri" data-dispatch="${esc(s.id)}">Giao việc cho ${esc(s.plaque)} <span class="btn-trail">↗</span></button>
      </div>
      <h3>Trạng thái hiện tại</h3>
      ${
        j
          ? `<div><b>${esc(j.label)}</b> <span class="chip running">${fmt(now() - j.started)}</span>${
              j.video ? `<div class="muted small">Video: ${esc(j.video)}</div>` : ''
            }</div>
            <div class="row" style="margin-top:8px">
              <button data-stop="${esc(j.id)}">Dừng việc</button>
              ${j.video ? `<a class="btn pri" href="${jobVideoLink(j)}">Mở video</a>` : ''}
            </div>
            <pre>${esc(log || 'Đang xử lý...')}</pre>`
          : s.id === 'owner'
          ? ownerHtml()
          : '<div class="muted small">Đang thực hiện công việc thường nhật tại bàn. Bấm nút Giao việc ở trên hoặc bấm đúp trực tiếp vào nhân vật 3D để giao tác vụ mới.</div>'
      }
      <h3>Lịch sử việc gần đây</h3>
      <ul class="list">
        ${
          recent
            .slice(0, 8)
            .map(r => `<li><span class="chip ${esc(r.status)}">${esc(r.status)}</span><span>${esc(r.label)}</span></li>`)
            .join('') || '<li class="muted small">Chưa có tác vụ nào trong phiên này.</li>'
        }
      </ul>
    `;
  } else if (sel.type === 'room') {
    const r = roomById[sel.id];
    const folders = S.folders.filter(f => f.room === r);
    p.innerHTML = `
      <div class="panel-top-row">
        <button id="back">Toàn công ty</button>
        <span class="chip">Phòng ${esc(r.code)}</span>
      </div>
      <h2>${esc(r.name)}</h2>
      <div class="muted small">${esc(r.signSub)}</div>
      <h3>Nhân viên trong phòng</h3>
      <ul class="list">
        ${STAFF.filter(s => s.room === r.id)
          .map(
            s =>
              `<li data-staff="${esc(s.id)}" title="Bấm đúp để giao việc nhanh">
                <span class="role-swatch" style="background:var(--${esc(s.who)})"></span>
                <span style="flex:1"><b>${esc(s.plaque)}</b> <span class="muted small">(${esc(s.name)})</span></span>
                ${current(s).job ? '<span class="chip running">đang làm</span>' : '<span class="chip">trực ca</span>'}
              </li>`
          )
          .join('')}
      </ul>
      <h3>Hồ sơ video tại bàn giao nhận</h3>
      <ul class="list">
        ${
          folders
            .map(
              f =>
                `<li data-video="${esc(f.v.slug)}">
                  <span class="folder-badge${/Bạn/i.test(f.v.next_who) ? ' wait' : ''}">Video ${esc(
                  f.v.slug.slice(0, 3)
                )}</span>
                  <span style="flex:1">${esc(f.v.title)}</span>
                </li>`
            )
            .join('') || '<li class="muted small">Chưa có hồ sơ video nào nằm ở phòng này.</li>'
        }
      </ul>
    `;
  } else if (sel.type === 'video') {
    const f = S.folders.find(f => f.v.slug === sel.slug);
    if (!f) {
      S.sel = null;
      return renderPanel();
    }
    const v = f.v;
    const pct = Math.round((100 * v.done_steps) / Math.max(1, v.total_steps));
    p.innerHTML = `
      <div class="panel-top-row">
        <button id="back">Toàn công ty</button>
        <span class="folder-badge">Video ${esc(v.slug.slice(0, 3))}</span>
      </div>
      <h2>${esc(v.title)}</h2>
      <h3>Tiến độ dây chuyền</h3>
      <div class="small">${v.done_steps}/${v.total_steps} bước hoàn tất · đang đặt tại <b>${esc(f.room.name)}</b></div>
      <div style="height:7px;border-radius:99px;background:var(--surface-subtle);border:1px solid var(--line);margin-top:6px;overflow:hidden">
        <div style="height:100%;width:${pct}%;background:var(--ok)"></div>
      </div>
      <h3>Bước tiếp theo</h3>
      <div><b>${esc(v.next_label)}</b> · phụ trách: ${esc(v.next_who)}</div>
      <div class="row" style="margin-top:12px">
        <a class="btn pri" href="${openLink(v.slug, v.next)}">Mở trên Bảng điều khiển <span class="btn-trail">↗</span></a>
        ${
          v.render
            ? `<a class="btn" href="/#v/${encodeURIComponent(S.ch)}/${encodeURIComponent(
                v.slug
              )}/preview">Xem bản dựng</a>`
            : ''
        }
      </div>
    `;
  }

  p.querySelector('#back')?.addEventListener('click', () => select(null));
  p.querySelectorAll('[data-room]').forEach(el => (el.onclick = () => select({ type: 'room', id: el.dataset.room })));
  p.querySelectorAll('[data-staff]').forEach(el => {
    el.onclick = () => select({ type: 'staff', id: el.dataset.staff });
    el.ondblclick = () => {
      const s = STAFF.find(x => x.id === el.dataset.staff);
      if (s) dispatchModal.open(s);
    };
  });
  p.querySelectorAll('[data-dispatch]').forEach(btn => {
    btn.onclick = () => {
      const s = STAFF.find(x => x.id === btn.dataset.dispatch);
      if (s) dispatchModal.open(s);
    };
  });
  p.querySelectorAll('[data-video]').forEach(
    el => (el.onclick = () => select({ type: 'video', slug: el.dataset.video }))
  );
  p.querySelectorAll('[data-stop]').forEach(
    b =>
      (b.onclick = async () => {
        await fetch('/api/action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'stop', job: b.dataset.stop }),
        });
      })
  );
}

function ownerHtml() {
  const todo = ownerTodo();
  return todo.length
    ? `<div class="small">${todo.length} video đang chờ bạn quyết định:</div>
       <ul class="list" style="margin-top:6px">${todo
         .map(
           v =>
             `<li data-video="${esc(v.slug)}"><span class="folder-badge wait">Video ${esc(
               v.slug.slice(0, 3)
             )}</span><span>${esc(v.next_label)}</span></li>`
         )
         .join('')}</ul>`
    : '<div class="muted small">Không có việc nào đang tồn đọng chờ bạn.</div>';
}

// ------------------------------------------------------------ Camera Fly-To & Selection
let fly = null;
function flyTo(target, zoom) {
  fly = {
    from: controls.target.clone(),
    to: target.clone(),
    z0: camera.zoom,
    z1: zoom,
    t: 0,
  };
}

function select(sel) {
  S.sel = sel;
  if (sel && $('#panel-shell')?.classList.contains('collapsed')) {
    $('#panel-shell').classList.remove('collapsed');
  }
  if (!sel) {
    flyTo(HOME.target, HOME.zoom);
  } else if (sel.type === 'room') {
    const r = roomById[sel.id];
    flyTo(new THREE.Vector3(r.x, 0, r.z), r.w > 30 ? 1.55 : 2.15);
  } else if (sel.type === 'staff') {
    const s = STAFF.find(x => x.id === sel.id);
    const p = new THREE.Vector3();
    s.group.getWorldPosition(p);
    flyTo(p, 3.1);
  } else if (sel.type === 'video') {
    const f = S.folders.find(f => f.v.slug === sel.slug);
    if (f) {
      const p = new THREE.Vector3();
      f.mesh.getWorldPosition(p);
      flyTo(p, 2.9);
    }
  }
  updateStageDockActive();
  renderPanel();
}

$('#home-btn').onclick = () => select(null);

$('#handoff-btn').onclick = () => {
  handoffSystem.triggerDemoHandoff(channelVideos());
};

$('#drawer-btn').onclick = () => {
  const shell = $('#panel-shell');
  shell.classList.toggle('collapsed');
};

$('#zen-btn').onclick = e => {
  S.zenMode = !S.zenMode;
  document.body.classList.toggle('zen-mode', S.zenMode);
  e.currentTarget.classList.toggle('active-toggle', S.zenMode);
  if (S.zenMode) select(null);
};

// ------------------------------------------------------------ Raycasting Hover & Click
const ray = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const hoverCard = $('#hover-card');
let downPos = null;

renderer.domElement.addEventListener('pointerdown', e => {
  downPos = [e.clientX, e.clientY];
});

renderer.domElement.addEventListener('pointerup', e => {
  if (!downPos || Math.hypot(e.clientX - downPos[0], e.clientY - downPos[1]) > 5) return;
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(pickables, false)[0];
  if (!hit) return;
  const u = hit.object.userData;
  if (u.type === 'staff') select({ type: 'staff', id: u.id });
  else if (u.type === 'video') select({ type: 'video', slug: u.slug });
  else if (u.type === 'room') select({ type: 'room', id: u.id });
});

renderer.domElement.addEventListener('dblclick', e => {
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(pickables, false)[0];
  if (!hit) return;
  const u = hit.object.userData;
  if (u.type === 'staff') {
    const s = STAFF.find(x => x.id === u.id);
    if (s) {
      select({ type: 'staff', id: s.id });
      dispatchModal.open(s);
    }
  }
});

renderer.domElement.addEventListener('pointermove', e => {
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(pickables, false)[0];

  if (!hit) {
    renderer.domElement.style.cursor = 'grab';
    hoverCard.classList.remove('show');
    return;
  }

  const u = hit.object.userData;
  renderer.domElement.style.cursor = 'pointer';

  if (u.type === 'staff') {
    const s = STAFF.find(x => x.id === u.id);
    if (s) {
      hoverCard.textContent = `${s.plaque} · ${WHO[s.who]} (Bấm đúp giao việc)`;
      hoverCard.style.left = `${Math.min(innerWidth - 260, e.clientX + 14)}px`;
      hoverCard.style.top = `${Math.max(14, e.clientY - 34)}px`;
      hoverCard.classList.add('show');
    }
  } else if (u.type === 'video') {
    const f = S.folders.find(f => f.v.slug === u.slug);
    if (f) {
      hoverCard.textContent = `Video ${f.v.slug.slice(0, 3)} · ${f.v.next_label}`;
      hoverCard.style.left = `${Math.min(innerWidth - 240, e.clientX + 14)}px`;
      hoverCard.style.top = `${Math.max(14, e.clientY - 34)}px`;
      hoverCard.classList.add('show');
    }
  } else if (u.type === 'room') {
    const r = roomById[u.id];
    if (r) {
      hoverCard.textContent = `${r.code} · ${r.name}`;
      hoverCard.style.left = `${Math.min(innerWidth - 220, e.clientX + 14)}px`;
      hoverCard.style.top = `${Math.max(14, e.clientY - 34)}px`;
      hoverCard.classList.add('show');
    }
  }
});

// ------------------------------------------------------------ Viewport Resize & Main 60fps Loop
function resize() {
  const w = window.innerWidth;
  const h = window.innerHeight;
  const a = w / h;
  camera.left = (-VIEW * a) / 1.55;
  camera.right = (VIEW * a) / 1.55;
  camera.top = VIEW / 1.55;
  camera.bottom = -VIEW / 1.55;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
  composer?.setSize(w, h);
  labelRenderer.setSize(w, h);
}
window.addEventListener('resize', resize);
resize();

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const clock = new THREE.Clock();

function tick() {
  requestAnimationFrame(tick);
  if (document.hidden) return; // Pause simulation while tab is hidden

  const dt = Math.min(0.05, clock.getDelta());
  const t = clock.elapsedTime;

  // Smooth Camera Fly-To Interpolation
  if (fly) {
    fly.t = Math.min(1, fly.t + dt * 2.1);
    const k = 1 - Math.pow(1 - fly.t, 3);
    const nt = fly.from.clone().lerp(fly.to, k);
    const shift = nt.clone().sub(controls.target);
    controls.target.add(shift);
    camera.position.add(shift);
    camera.zoom = fly.z0 + (fly.z1 - fly.z0) * k;
    camera.updateProjectionMatrix();
    if (fly.t >= 1) fly = null;
  } else if (S.zenMode && !reduced) {
    // Gentle decorative camera orbit in Showcase / Zen Mode
    const angle = Math.sin(t * 0.12) * 0.18;
    const radius = 78;
    const baseAngle = 0.72 + angle;
    const targetPos = new THREE.Vector3(
      controls.target.x + Math.sin(baseAngle) * radius,
      56,
      controls.target.z + Math.cos(baseAngle) * radius
    );
    camera.position.lerp(targetPos, dt * 1.5);
  }

  updateStaffAnimations({
    dt,
    t,
    reduced,
    currentFn: current,
    ownerTodoFn: ownerTodo,
    nowFn: now,
    fmtFn: fmt,
    escFn: esc,
  });
  updateRoomPropAnimations(archProps, dt, t, reduced);
  updateOutdoorAnimations(outdoor, dt, t, reduced);
  handoffSystem.update(dt, t, reduced, channelVideos());

  controls.update();
  if (composer) composer.render();
  else renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
}

poll();
renderPanel();
tick();
