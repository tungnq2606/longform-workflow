import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

export const COLORS = {
  claude: 0xc86446,
  gemini: 0x2d6cdf,
  code: 0x5c6672,
  owner: 0x1f7a54,
};

export const WHO = {
  claude: 'Claude',
  gemini: 'Gemini',
  code: 'Máy (code)',
  owner: 'Bạn',
};

// Expanded 94x52 Studio Building:
// North Wing: z = -15.5 (depth 19, back wall z = -25, corridor wall z = -6)
// Central Skylit Atrium Corridor: z = -6 to +6 (depth 12, width 92)
// South Wing: z = +15.5 (depth 19, corridor wall z = +6, front glass wall z = +25)
export const ROOMS = [
  {
    id: 'boss',
    code: '00',
    name: 'Phòng Giám đốc',
    signTitle: 'PHÒNG GIÁM ĐỐC',
    signSub: 'CREATIVE DIRECTOR SUITE',
    wing: 'south',
    x: -34.5,
    z: 15.5,
    w: 23,
    d: 19,
    doorLocalX: 0,
    tableLocal: [7.2, 0, -5.8],
    floor: 0xd9ccb8,
    rug: 0x295f48,
    accent: '#1f7a54',
    tab: 'script',
  },
  {
    id: 'research',
    code: '01',
    name: 'Phòng Nghiên cứu',
    signTitle: 'PHÒNG NGHIÊN CỨU',
    signSub: 'RESEARCH & SCOUT LAB',
    wing: 'north',
    x: -35.5,
    z: -15.5,
    w: 21,
    d: 19,
    doorLocalX: 0,
    tableLocal: [6.4, 0, 5.8],
    floor: 0xcfdac9,
    rug: 0x3b6e5c,
    accent: '#2d6cdf',
    tab: 'script',
  },
  {
    id: 'script',
    code: '02',
    name: 'Phòng Kịch bản',
    signTitle: 'PHÒNG KỊCH BẢN',
    signSub: 'STORY & RETENTION ROOM',
    wing: 'north',
    x: -14.5,
    z: -15.5,
    w: 21,
    d: 19,
    doorLocalX: 0,
    tableLocal: [6.4, 0, 5.8],
    floor: 0xdcd3e2,
    rug: 0x7c5243,
    accent: '#c86446',
    tab: 'script',
  },
  {
    id: 'art',
    code: '03',
    name: 'Phòng Mỹ thuật',
    signTitle: 'XƯỞNG MỸ THUẬT',
    signSub: 'CHARACTER & SCENE STUDIO',
    wing: 'north',
    x: 21,
    z: -15.5,
    w: 50,
    d: 19,
    doorLocalX: -12,
    secondDoorLocalX: 12,
    tableLocal: [-6.2, 0, 5.8],
    floor: 0xe7d8c5,
    rug: 0x345995,
    accent: '#2d6cdf',
    tab: 'shots',
  },
  {
    id: 'voice',
    code: '04',
    name: 'Phòng Thu âm',
    signTitle: 'PHÒNG THU ÂM',
    signSub: 'VOCAL & FOLEY BOOTH',
    wing: 'south',
    x: -12.5,
    z: 15.5,
    w: 21,
    d: 19,
    doorLocalX: 0,
    tableLocal: [6.4, 0, -5.8],
    floor: 0xc8d5e1,
    rug: 0x3d5467,
    accent: '#5c6672',
    tab: 'voice',
  },
  {
    id: 'edit',
    code: '05',
    name: 'Phòng Dựng phim',
    signTitle: 'PHÒNG DỰNG PHIM',
    signSub: 'REMOTION 1440P RENDER BAY',
    wing: 'south',
    x: 10,
    z: 15.5,
    w: 24,
    d: 19,
    doorLocalX: 0,
    tableLocal: [7.4, 0, -5.8],
    floor: 0xd5cfc5,
    rug: 0x454d59,
    accent: '#5c6672',
    tab: 'preview',
  },
  {
    id: 'publish',
    code: '06',
    name: 'Phòng Phát hành',
    signTitle: 'PHÒNG PHÁT HÀNH',
    signSub: 'PACKAGING & THUMBNAIL LAB',
    wing: 'south',
    x: 34,
    z: 15.5,
    w: 24,
    d: 19,
    doorLocalX: 0,
    tableLocal: [-7.4, 0, -5.8],
    floor: 0xe3d4d0,
    rug: 0x8c4a3c,
    accent: '#c86446',
    tab: 'upload',
  },
];

export const STAFF = [
  {
    id: 'owner',
    name: 'Bạn',
    plaque: 'GIÁM ĐỐC',
    role: 'Giám đốc sáng tạo: duyệt kịch bản, tạo ảnh key trên Flow, thu giọng',
    who: 'owner',
    room: 'boss',
    at: [-4.8, 0.8],
    prop: 'mug',
    hat: 'hair_glasses',
  },
  {
    id: 'assistant',
    name: 'Claude',
    plaque: 'TRỢ LÝ ĐIỀU HÀNH',
    role: 'Trợ lý điều hành: thực hiện yêu cầu từ ô chat Bảng điều khiển',
    who: 'claude',
    room: 'boss',
    at: [2.2, -1.8],
    actions: ['claude'],
    prop: 'tablet',
    hat: 'glasses',
  },
  {
    id: 'researcher',
    name: 'Gemini',
    plaque: 'NHÀ NGHIÊN CỨU',
    role: 'Nhà nghiên cứu: tìm chủ đề, nguồn học thuật, phân tích đối thủ, gợi ý cụm từ',
    who: 'gemini',
    room: 'research',
    at: [-4.2, -1.8],
    actions: ['research_topic', 'competitors', 'suggest_phrases', 'gemini'],
    prop: 'loupe',
    hat: 'headphones',
  },
  {
    id: 'scout',
    name: 'Máy đo',
    plaque: 'MÁY ĐO YT-DLP',
    role: 'Máy đo dữ liệu: đo nhu cầu tìm kiếm và độ cạnh tranh trên YouTube (yt-dlp)',
    who: 'code',
    room: 'research',
    at: [3.2, -1.2],
    actions: ['scout'],
    prop: 'scanner',
    robotType: 'scout',
  },
  {
    id: 'writer',
    name: 'Claude',
    plaque: 'BIÊN KỊCH CHÍNH',
    role: 'Biên kịch: viết và chỉnh sửa kịch bản, đối chiếu bảng nguồn dữ liệu',
    who: 'claude',
    room: 'script',
    at: [-4.2, -1.8],
    actions: ['write_script', 'fix_script'],
    prop: 'pen',
    hat: 'beret',
  },
  {
    id: 'viewer',
    name: 'Gemini',
    plaque: 'KHÁN GIẢ THỬ',
    role: 'Khán giả thử nghiệm: đọc nháp kịch bản, mô phỏng giữ chân và góp ý',
    who: 'gemini',
    room: 'script',
    at: [2.8, -1.2],
    actions: ['simulate'],
    prop: 'tablet',
    hat: 'headphones',
  },
  {
    id: 'director',
    name: 'Claude',
    plaque: 'ĐẠO DIỄN HÌNH',
    role: 'Đạo diễn hình ảnh: thiết kế nhân vật, bối cảnh và chia cảnh chi tiết',
    who: 'claude',
    room: 'art',
    at: [-18.5, -2.5],
    actions: ['make_shots', 'claude_shot'],
    prop: 'clapboard',
    hat: 'beret',
  },
  {
    id: 'checker',
    name: 'Máy kiểm',
    plaque: 'MÁY KIỂM PROMPT',
    role: 'Máy kiểm định: lắp ghép và kiểm tra prompt đúng chuẩn style khóa',
    who: 'code',
    room: 'art',
    at: [-16.5, 3.4],
    actions: ['prompts', 'check_prompts'],
    prop: 'stamp',
    robotType: 'checker',
  },
  {
    id: 'p1',
    name: 'Gemini',
    plaque: 'HỌA SĨ CẢNH 01',
    role: 'Họa sĩ 1: vẽ minh họa cảnh kịch bản độ phân giải cao',
    who: 'gemini',
    room: 'art',
    at: [-7.5, -2.4],
    actions: ['generate', 'redo', 'redo_many'],
    painter: 1,
    prop: 'stylus',
    hat: 'visor',
  },
  {
    id: 'p2',
    name: 'Gemini',
    plaque: 'HỌA SĨ CẢNH 02',
    role: 'Họa sĩ 2: vẽ minh họa cảnh kịch bản độ phân giải cao',
    who: 'gemini',
    room: 'art',
    at: [0.5, -2.4],
    actions: ['generate', 'redo', 'redo_many'],
    painter: 2,
    prop: 'stylus',
    hat: 'visor',
  },
  {
    id: 'p3',
    name: 'Gemini',
    plaque: 'HỌA SĨ CẢNH 03',
    role: 'Họa sĩ 3: vẽ minh họa cảnh kịch bản độ phân giải cao',
    who: 'gemini',
    room: 'art',
    at: [8.5, -2.4],
    actions: ['generate', 'redo', 'redo_many'],
    painter: 3,
    prop: 'stylus',
    hat: 'visor',
  },
  {
    id: 'p4',
    name: 'Gemini',
    plaque: 'HỌA SĨ CẢNH 04',
    role: 'Họa sĩ 4: vẽ minh họa cảnh kịch bản độ phân giải cao',
    who: 'gemini',
    room: 'art',
    at: [16.5, -2.4],
    actions: ['generate', 'redo', 'redo_many'],
    painter: 4,
    prop: 'stylus',
    hat: 'visor',
  },
  {
    id: 'reviewer',
    name: 'Gemini',
    plaque: 'KIỂM DUYỆT ẢNH',
    role: 'Kiểm duyệt mỹ thuật: đối chiếu từng ảnh cảnh với cast sheet và prompt',
    who: 'gemini',
    room: 'art',
    at: [9.5, 4.2],
    actions: ['review'],
    prop: 'loupe',
    hat: 'glasses',
  },
  {
    id: 'voicebot',
    name: 'Máy tách lời',
    plaque: 'KỸ SƯ ÂM THANH',
    role: 'Kỹ sư âm thanh: chuẩn bị văn bản phát âm và tách đoạn cho ElevenLabs',
    who: 'code',
    room: 'voice',
    at: [-3.8, -1.2],
    actions: ['voice_text'],
    prop: 'headphones',
    robotType: 'voice',
  },
  {
    id: 'render',
    name: 'Máy dựng',
    plaque: 'KỸ SƯ DỰNG 1440P',
    role: 'Kỹ sư dựng phim Remotion: ghép cảnh, âm thanh, phụ đề thành MP4 1440p',
    who: 'code',
    room: 'edit',
    at: [-2.5, -1.6],
    actions: ['render', 'studio'],
    prop: 'reel',
    robotType: 'render',
  },
  {
    id: 'publisher',
    name: 'Claude',
    plaque: 'BIÊN TẬP PHÁT HÀNH',
    role: 'Biên tập xuất bản: soạn hồ sơ đăng tải, chương mục, mô tả và nguồn trích dẫn',
    who: 'claude',
    room: 'publish',
    at: [-3.2, -1.8],
    actions: ['write_upload'],
    prop: 'pen',
    hat: 'glasses',
  },
  {
    id: 'marketer',
    name: 'Gemini',
    plaque: 'THIẾT KẾ THUMBNAIL',
    role: 'Thiết kế đóng gói: phát triển bố cục thumbnail và phương án tiêu đề',
    who: 'gemini',
    room: 'publish',
    at: [4.2, 1.4],
    actions: ['titles', 'thumb'],
    prop: 'stylus',
    hat: 'headphones',
  },
];

export const ROOM_OF_STEP = {
  research: 'research',
  script: 'script',
  sim: 'script',
  shots: 'art',
  sheets: 'art',
  scenes: 'art',
  review: 'art',
  voice: 'voice',
  render: 'edit',
  upload: 'publish',
};

export const TAB_OF_STEP = {
  research: 'script',
  script: 'script',
  sim: 'script',
  shots: 'shots',
  sheets: 'shots',
  scenes: 'shots',
  review: 'shots',
  voice: 'voice',
  render: 'preview',
  upload: 'upload',
};

export const PIPELINE_ORDER = ['research', 'script', 'art', 'voice', 'edit', 'publish', 'boss'];

export const roomById = Object.fromEntries(ROOMS.map(r => [r.id, r]));

// Shared cached materials & geometry helpers
const matCache = new Map();
export function stdMat(color, roughness = 0.72, metalness = 0.04, extra = {}) {
  const key = `${color}_${roughness}_${metalness}_${JSON.stringify(extra)}`;
  if (!matCache.has(key)) {
    matCache.set(key, new THREE.MeshStandardMaterial({ color, roughness, metalness, ...extra }));
  }
  return matCache.get(key);
}

const rBoxCache = new Map();
export function rBoxGeo(w, h, d, radius = 0.08, segments = 3) {
  const r = Math.min(radius, w * 0.45, h * 0.45, d * 0.45);
  const key = `${w.toFixed(3)}_${h.toFixed(3)}_${d.toFixed(3)}_${r.toFixed(3)}_${segments}`;
  if (!rBoxCache.has(key)) {
    rBoxCache.set(key, new RoundedBoxGeometry(w, h, d, segments, r));
  }
  return rBoxCache.get(key);
}

export function addRBox(parent, w, h, d, material, x = 0, y = 0, z = 0, radius = 0.08, castShadow = true, receiveShadow = true) {
  const mesh = new THREE.Mesh(rBoxGeo(w, h, d, radius), material);
  mesh.position.set(x, y, z);
  mesh.castShadow = castShadow;
  mesh.receiveShadow = receiveShadow;
  parent.add(mesh);
  return mesh;
}

export function addBox(parent, w, h, d, material, x = 0, y = 0, z = 0, castShadow = true, receiveShadow = true) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
  mesh.position.set(x, y, z);
  mesh.castShadow = castShadow;
  mesh.receiveShadow = receiveShadow;
  parent.add(mesh);
  return mesh;
}

export function addCyl(parent, rt, rb, h, segs, material, x = 0, y = 0, z = 0, castShadow = true) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, segs), material);
  mesh.position.set(x, y, z);
  mesh.castShadow = castShadow;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

// High-DPI Canvas Texture Generator for Architectural Wall Signs, Doorway Lintels & Desk Plaques
export function makeSignTexture({
  code = '',
  title = '',
  subtitle = '',
  accent = '#1f7a54',
  bg = '#1b2129',
  fg = '#f6f4ef',
  subFg = '#a3b0bf',
  border = '#c9a469',
  width = 1024,
  height = 256,
  compact = false,
}) {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');

  // Background plate
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, width, height);

  // Subtle architectural frame
  ctx.strokeStyle = border;
  ctx.lineWidth = compact ? 6 : 8;
  ctx.strokeRect(10, 10, width - 20, height - 20);

  // Left accent bar or code badge
  if (code) {
    const badgeW = compact ? 130 : 168;
    ctx.fillStyle = accent;
    ctx.fillRect(18, 18, badgeW, height - 36);

    ctx.fillStyle = '#ffffff';
    ctx.font = `800 ${compact ? 58 : 74}px "Be Vietnam Pro", sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(code, 18 + badgeW / 2, height / 2 + 2);

    const textX = 18 + badgeW + (compact ? 28 : 38);
    ctx.textAlign = 'left';
    if (subtitle) {
      ctx.fillStyle = fg;
      ctx.font = `800 ${compact ? 54 : 64}px "Be Vietnam Pro", sans-serif`;
      ctx.fillText(title, textX, height * 0.43);

      ctx.fillStyle = subFg;
      ctx.font = `600 ${compact ? 26 : 30}px "Be Vietnam Pro", sans-serif`;
      ctx.fillText(subtitle, textX, height * 0.76);
    } else {
      ctx.fillStyle = fg;
      ctx.font = `800 ${compact ? 58 : 68}px "Be Vietnam Pro", sans-serif`;
      ctx.fillText(title, textX, height * 0.53);
    }
  } else {
    // Desk nameplate or centered sign
    ctx.fillStyle = accent;
    ctx.fillRect(18, 18, 18, height - 36);

    ctx.fillStyle = fg;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = `800 ${compact ? 54 : 62}px "Be Vietnam Pro", sans-serif`;
    ctx.fillText(title, width * 0.52, subtitle ? height * 0.44 : height * 0.52);

    if (subtitle) {
      ctx.fillStyle = subFg;
      ctx.font = `600 28px "Be Vietnam Pro", sans-serif`;
      ctx.fillText(subtitle, width * 0.52, height * 0.76);
    }
  }

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  tex.needsUpdate = true;
  return tex;
}

// Floor zone rug texture with subtle woven pattern & room code
export function makeRugTexture(code, baseHex, accentHex) {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 384;
  const ctx = canvas.getContext('2d');

  const cBase = new THREE.Color(baseHex);
  ctx.fillStyle = `#${cBase.getHexString()}`;
  ctx.fillRect(0, 0, 512, 384);

  // Subtle woven stripes
  ctx.fillStyle = 'rgba(255, 255, 255, 0.04)';
  for (let y = 0; y < 384; y += 8) {
    ctx.fillRect(0, y, 512, 3);
  }

  // Border inset
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.22)';
  ctx.lineWidth = 6;
  ctx.strokeRect(18, 18, 512 - 36, 384 - 36);

  ctx.strokeStyle = accentHex;
  ctx.lineWidth = 3;
  ctx.strokeRect(28, 28, 512 - 56, 384 - 56);

  // Subtle corner code watermark
  if (code) {
    ctx.fillStyle = 'rgba(255, 255, 255, 0.14)';
    ctx.font = '800 54px "Be Vietnam Pro", sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    ctx.fillText(code, 512 - 42, 384 - 34);
  }

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.needsUpdate = true;
  return tex;
}

// Compute waypoint path along the central atrium corridor between two rooms
export function getCorridorPath(fromRoomId, toRoomId) {
  const rA = roomById[fromRoomId] || ROOMS[1];
  const rB = roomById[toRoomId] || ROOMS[2];

  const startTable = new THREE.Vector3(
    rA.x + rA.tableLocal[0],
    0,
    rA.z + rA.tableLocal[2] + (rA.wing === 'north' ? -1.1 : 1.1)
  );
  const doorA = new THREE.Vector3(
    rA.x + (rA.doorLocalX || 0),
    0,
    rA.wing === 'north' ? -6.2 : 6.2
  );
  const corrA = new THREE.Vector3(
    rA.x + (rA.doorLocalX || 0),
    0,
    rA.wing === 'north' ? -1.6 : 1.6
  );
  const corrB = new THREE.Vector3(
    rB.x + (rB.doorLocalX || 0),
    0,
    rB.wing === 'north' ? -1.6 : 1.6
  );
  const doorB = new THREE.Vector3(
    rB.x + (rB.doorLocalX || 0),
    0,
    rB.wing === 'north' ? -6.2 : 6.2
  );
  const endTable = new THREE.Vector3(
    rB.x + rB.tableLocal[0],
    0,
    rB.z + rB.tableLocal[2] + (rB.wing === 'north' ? -1.1 : 1.1)
  );

  return [startTable, doorA, corrA, corrB, doorB, endTable];
}
