import * as THREE from 'three';
import {
  ROOMS,
  stdMat,
  addRBox,
  addBox,
  addCyl,
  makeSignTexture,
  makeRugTexture,
} from './constants.js';

export function buildArchitecture(scene, pickables) {
  const building = new THREE.Group();
  building.name = 'StudioBuilding';
  scene.add(building);

  const archProps = {
    globeMesh: null,
    scoutBars: [],
    cintiqScreens: [],
    onAirMat: null,
    eqBars: [],
    renderFans: [],
    serverLeds: [],
    timelinePlayhead: null,
    uplinkDish: null,
    steamPuffs: [],
    roomLights: [],
    signMeshes: [],
    flowPulses: [],
  };

  // Architectural Palette
  const slabMat = stdMat(0xc5bdb0, 0.82, 0.04);
  const corridorFloorMat = stdMat(0xd7c5ac, 0.72, 0.05);
  const corridorStripMat = stdMat(0xc1ab8c, 0.75, 0.05);
  const wallOuterMat = stdMat(0xf3efe8, 0.78, 0.02);
  const wallInnerMat = stdMat(0xebe5dc, 0.8, 0.02);
  const wallCapMat = stdMat(0x2c333c, 0.55, 0.2);
  const timberPortalMat = stdMat(0x8c5c38, 0.62, 0.08);
  const brassMat = stdMat(0xc9a259, 0.35, 0.65);
  const darkMetalMat = stdMat(0x252b33, 0.45, 0.45);
  const walnutMat = stdMat(0x6e472b, 0.58, 0.06);
  const oakMat = stdMat(0xc8a374, 0.64, 0.05);
  const glassMat = new THREE.MeshPhysicalMaterial({
    color: 0xd8eef8,
    transparent: true,
    opacity: 0.34,
    roughness: 0.1,
    metalness: 0.05,
  });

  // 1. Main Building Structural Slab & Central Skylit Atrium Corridor (z = -6 to +6)
  addRBox(building, 94, 0.36, 52, slabMat, 0, -0.18, 0, 0.1, false, true);
  addBox(building, 92, 0.08, 12, corridorFloorMat, 0, 0.02, 0, false, true);

  // Corridor herringbone runner strips & guide inlays
  for (let x = -43; x <= 43; x += 4.0) {
    addBox(building, 1.8, 0.09, 3.4, corridorStripMat, x, 0.025, 0, false, true);
  }
  addBox(building, 88, 0.095, 0.22, brassMat, 0, 0.03, -2.1, false, true);
  addBox(building, 88, 0.095, 0.22, brassMat, 0, 0.03, 2.1, false, true);

  // Illuminated Pipeline Flow Nodes along the Central Corridor Spine
  for (let i = 0; i < 14; i++) {
    const fx = -36 + i * 5.5;
    const nodeMat = new THREE.MeshStandardMaterial({
      color: 0x38ef7d,
      emissive: 0x1f7a54,
      emissiveIntensity: 0.4,
      roughness: 0.25,
    });
    const node = addRBox(building, 0.95, 0.06, 0.28, nodeMat, fx, 0.055, 0, 0.02, false, false);
    archProps.flowPulses.push({ mesh: node, mat: nodeMat, index: i });
  }

  // West & East Atrium Glass Entry Portals (x = -46 and x = +46)
  for (const side of [-1, 1]) {
    const gx = side * 46;
    const portal = new THREE.Group();
    portal.position.set(gx, 0, 0);
    building.add(portal);
    addRBox(portal, 0.45, 4.2, 0.45, darkMetalMat, 0, 2.1, -5.8, 0.05);
    addRBox(portal, 0.45, 4.2, 0.45, darkMetalMat, 0, 2.1, 5.8, 0.05);
    addRBox(portal, 0.55, 0.45, 12.0, darkMetalMat, 0, 4.1, 0, 0.06);
    addBox(portal, 0.12, 3.8, 3.6, glassMat, 0, 1.9, -3.9, false, false);
    addBox(portal, 0.12, 3.8, 3.6, glassMat, 0, 1.9, 3.9, false, false);
  }

  // Central Atrium Lounge: Espresso & Matcha Bar (x = -41, z = 0) + Planters + Kanban Board
  const cafeBar = new THREE.Group();
  cafeBar.position.set(-41.5, 0, 0);
  building.add(cafeBar);
  addRBox(cafeBar, 2.2, 1.05, 5.2, walnutMat, 0, 0.52, 0, 0.1);
  addRBox(cafeBar, 2.4, 0.12, 5.4, stdMat(0xf4f0e8, 0.35, 0.05), 0, 1.1, 0, 0.05);
  // Espresso Machine
  addRBox(cafeBar, 0.9, 0.75, 1.2, stdMat(0xb84335, 0.3, 0.4), -0.2, 1.5, -1.1, 0.08);
  addRBox(cafeBar, 0.85, 0.15, 1.1, brassMat, -0.2, 1.92, -1.1, 0.04);
  // Rising steam puffs
  const steamMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.45 });
  for (let i = 0; i < 3; i++) {
    const sp = new THREE.Mesh(new THREE.SphereGeometry(0.14 + i * 0.04, 8, 8), steamMat.clone());
    sp.position.set(-0.2, 2.1 + i * 0.25, -1.1);
    cafeBar.add(sp);
    archProps.steamPuffs.push({ mesh: sp, baseY: 2.05, phase: i * 2.1 });
  }

  // Indoor Olive Trees & Bench Planters along the Atrium Corridor
  const planterXs = [-25, -2, 22, 42];
  const potMat = stdMat(0x9e6f4a, 0.75, 0.04);
  const leafMat = stdMat(0x528f5a, 0.72, 0.02);
  for (const px of planterXs) {
    const pg = new THREE.Group();
    pg.position.set(px, 0, 0);
    building.add(pg);
    addRBox(pg, 2.6, 0.52, 1.3, oakMat, 0, 0.26, 0, 0.08);
    addCyl(pg, 0.48, 0.38, 0.75, 12, potMat, -0.65, 0.62, 0);
    addCyl(pg, 0.08, 0.11, 1.2, 8, walnutMat, -0.65, 1.35, 0);
    const canopy = new THREE.Mesh(new THREE.DodecahedronGeometry(0.82, 1), leafMat);
    canopy.position.set(-0.65, 2.1, 0);
    canopy.castShadow = true;
    pg.add(canopy);
  }

  // 2. Build all 7 Department Rooms with Integrated Architectural Signage
  for (const r of ROOMS) {
    const g = new THREE.Group();
    g.position.set(r.x, 0, r.z);
    building.add(g);
    r.group = g;

    // Room Floor Tile (Pickable)
    const floor = addBox(g, r.w - 0.2, 0.12, r.d - 0.2, stdMat(r.floor, 0.78, 0.02), 0, 0.04, 0, false, true);
    floor.userData = { type: 'room', id: r.id };
    pickables.push(floor);

    // Woven Department Area Rug with Room Code
    const rugTex = makeRugTexture(r.code, r.rug, r.accent);
    const rugW = Math.min(r.w * 0.56, 16);
    const rugD = r.d * 0.52;
    const rugMesh = new THREE.Mesh(
      new THREE.PlaneGeometry(rugW, rugD),
      new THREE.MeshStandardMaterial({ map: rugTex, roughness: 0.9, metalness: 0.0 })
    );
    rugMesh.rotation.x = -Math.PI / 2;
    rugMesh.position.set(r.id === 'art' ? 2 : -1.2, 0.11, 0);
    rugMesh.receiveShadow = true;
    g.add(rugMesh);

    // Warm Interior Room Light
    const rLight = new THREE.PointLight(0xfff1d6, 0.55, 26, 1.4);
    rLight.position.set(0, 4.2, 0);
    g.add(rLight);
    archProps.roomLights.push(rLight);

    const wallT = 0.34;
    const backH = 4.5;
    const sideH = 3.2;
    const corrH = 2.65;
    const doorW = 4.4;
    const doorX = r.doorLocalX || 0;

    if (r.wing === 'north') {
      // North Wing: Back wall at -r.d/2 (tall, with windows & main wall signboard facing South/+Z)
      const backZ = -r.d / 2;
      addBox(g, r.w, backH, wallT, wallOuterMat, 0, backH / 2, backZ);
      addBox(g, r.w + 0.1, 0.14, wallT + 0.1, wallCapMat, 0, backH + 0.07, backZ);

      // Panoramic window cutouts with mullions on upper North wall (left/right of center signboard)
      const winOffsets = r.w > 30 ? [-17, 17] : [-r.w * 0.32, r.w * 0.32];
      for (const wx of winOffsets) {
        addBox(g, 3.8, 1.85, wallT + 0.06, darkMetalMat, wx, 2.75, backZ);
        addBox(g, 3.5, 1.55, wallT + 0.1, glassMat, wx, 2.75, backZ, false, false);
      }

      // Main Architectural Wall Signboard mounted on the North Back Wall (facing +Z toward camera!)
      const signW = r.w > 30 ? 10.5 : 8.4;
      const signH = 2.15;
      const signGroup = new THREE.Group();
      signGroup.position.set(0, 3.25, backZ + 0.26);
      g.add(signGroup);
      // Walnut backing frame
      addRBox(signGroup, signW + 0.36, signH + 0.32, 0.16, walnutMat, 0, 0, -0.04, 0.06);
      // Brass sconce light bar above sign
      addRBox(signGroup, signW * 0.65, 0.12, 0.28, brassMat, 0, signH / 2 + 0.24, 0.08, 0.04);

      const wallSignTex = makeSignTexture({
        code: r.code,
        title: r.signTitle,
        subtitle: r.signSub,
        accent: r.accent,
        bg: '#1b222c',
        fg: '#f8f6f0',
        subFg: '#b4c0ce',
        border: '#cfa968',
      });
      const signPlane = new THREE.Mesh(
        new THREE.PlaneGeometry(signW, signH),
        new THREE.MeshBasicMaterial({ map: wallSignTex })
      );
      signPlane.position.z = 0.06;
      signPlane.userData = { type: 'room', id: r.id };
      signGroup.add(signPlane);
      pickables.push(signPlane);
      archProps.signMeshes.push(signPlane);

      // Corridor Front Wall at +r.d/2 with Open Doorway Portal(s)
      const frontZ = r.d / 2;
      buildWallWithDoorways(g, r, frontZ, corrH, wallT, wallInnerMat, wallCapMat, timberPortalMat, brassMat, true, pickables);
    } else {
      // South Wing: Corridor Wall is at -r.d/2 (North side of room, facing +Z toward the camera!)
      const corrZ = -r.d / 2;
      buildWallWithDoorways(g, r, corrZ, 3.6, wallT, wallInnerMat, wallCapMat, timberPortalMat, brassMat, false, pickables);

      // Mount the Main Architectural Wall Signboard right above the North/Corridor Portal facing +Z toward the camera!
      const signW = 8.8;
      const signH = 2.15;
      const signGroup = new THREE.Group();
      signGroup.position.set(doorX, 4.15, corrZ + 0.26);
      signGroup.rotation.x = -0.14; // Tilted slightly upward toward the isometric camera
      g.add(signGroup);
      addRBox(signGroup, signW + 0.36, signH + 0.32, 0.18, walnutMat, 0, 0, -0.04, 0.06);
      addRBox(signGroup, signW * 0.65, 0.12, 0.28, brassMat, 0, signH / 2 + 0.22, 0.08, 0.04);

      const wallSignTex = makeSignTexture({
        code: r.code,
        title: r.signTitle,
        subtitle: r.signSub,
        accent: r.accent,
        bg: '#1b222c',
        fg: '#f8f6f0',
        subFg: '#b4c0ce',
        border: '#cfa968',
      });
      const signPlane = new THREE.Mesh(
        new THREE.PlaneGeometry(signW, signH),
        new THREE.MeshBasicMaterial({ map: wallSignTex })
      );
      signPlane.position.z = 0.07;
      signPlane.userData = { type: 'room', id: r.id };
      signGroup.add(signPlane);
      pickables.push(signPlane);
      archProps.signMeshes.push(signPlane);

      // South Exterior Facade at +r.d/2: Cutaway Low Parapet (height 1.05) + Clear Glass Curtain Wall
      // so the camera has a completely unobstructed cutaway view inside South Wing rooms!
      const southZ = r.d / 2;
      addBox(g, r.w, 1.05, wallT, wallOuterMat, 0, 0.525, southZ);
      addBox(g, r.w + 0.06, 0.1, wallT + 0.08, wallCapMat, 0, 1.08, southZ);
      addBox(g, r.w - 0.6, 1.35, 0.08, glassMat, 0, 1.78, southZ, false, false);

      // Exterior Facade Architectural Plaque on the South Parapet (readable from the street!)
      const extSignW = 6.4;
      const extSignH = 0.82;
      const extTex = makeSignTexture({
        code: r.code,
        title: r.signTitle,
        subtitle: '',
        accent: r.accent,
        bg: '#1c232d',
        fg: '#f6f4ef',
        border: '#cfa968',
        width: 768,
        height: 160,
        compact: true,
      });
      const extPlaque = new THREE.Mesh(
        new THREE.PlaneGeometry(extSignW, extSignH),
        new THREE.MeshBasicMaterial({ map: extTex })
      );
      extPlaque.position.set(0, 0.56, southZ + wallT / 2 + 0.03);
      extPlaque.userData = { type: 'room', id: r.id };
      g.add(extPlaque);
      pickables.push(extPlaque);
    }

    // Left & Right Partition Walls (stepped height so side views stay open)
    for (const side of [-1, 1]) {
      const sx = (side * r.w) / 2;
      addBox(g, wallT, sideH, r.d, wallInnerMat, sx, sideH / 2, 0);
      addBox(g, wallT + 0.06, 0.1, r.d, wallCapMat, sx, sideH + 0.05, 0);
    }

    // Handoff Inbox/Outbox Table near the Room Doorway (where video folders sit and couriers deliver!)
    r.table = new THREE.Vector3(r.tableLocal[0], 0, r.tableLocal[2]);
    const tGroup = new THREE.Group();
    tGroup.position.set(r.table.x, 0, r.table.z);
    g.add(tGroup);
    // Table top & legs
    addRBox(tGroup, 3.8, 0.14, 2.2, oakMat, 0, 0.88, 0, 0.05);
    addRBox(tGroup, 3.5, 0.78, 1.9, stdMat(0xe6dfd3, 0.75, 0.03), 0, 0.42, 0, 0.06);
    // Brass inbox tray rim
    addBox(tGroup, 3.4, 0.05, 0.06, brassMat, 0, 0.96, -0.92);
    addBox(tGroup, 3.4, 0.05, 0.06, brassMat, 0, 0.96, 0.92);
    // Subtle glowing delivery pad ring on table
    const padRing = new THREE.Mesh(
      new THREE.RingGeometry(0.45, 0.62, 24),
      new THREE.MeshBasicMaterial({ color: 0x1f7a54, transparent: true, opacity: 0.25, side: THREE.DoubleSide })
    );
    padRing.rotation.x = -Math.PI / 2;
    padRing.position.set(1.1, 0.96, 0);
    tGroup.add(padRing);
    r.deliveryRing = padRing;

    // Populate Department-Specific Architectural Props & Equipment
    populateRoomInterior(r, g, archProps, {
      walnutMat,
      oakMat,
      brassMat,
      darkMetalMat,
      glassMat,
    });
  }

  return { building, archProps };
}

function buildWallWithDoorways(
  g,
  r,
  zPos,
  wallH,
  wallT,
  wallMat,
  capMat,
  portalMat,
  brassMat,
  isNorthWing,
  pickables
) {
  const doors = [r.doorLocalX || 0];
  if (typeof r.secondDoorLocalX === 'number') doors.push(r.secondDoorLocalX);
  doors.sort((a, b) => a - b);

  const doorW = 4.6;
  const halfW = r.w / 2;
  let cursor = -halfW;

  for (const dx of doors) {
    const leftEdge = dx - doorW / 2;
    const rightEdge = dx + doorW / 2;
    const segW = leftEdge - cursor;
    if (segW > 0.2) {
      const cx = cursor + segW / 2;
      addBox(g, segW, wallH, wallT, wallMat, cx, wallH / 2, zPos);
      addBox(g, segW, 0.1, wallT + 0.06, capMat, cx, wallH + 0.05, zPos);
    }

    // Timber & Bronze Doorway Portal Frame + Overhead Doorway Transom Sign
    const portal = new THREE.Group();
    portal.position.set(dx, 0, zPos);
    g.add(portal);
    const pH = 3.25;
    addRBox(portal, 0.28, pH, wallT + 0.18, portalMat, -doorW / 2, pH / 2, 0, 0.04);
    addRBox(portal, 0.28, pH, wallT + 0.18, portalMat, doorW / 2, pH / 2, 0, 0.04);
    addRBox(portal, doorW + 0.45, 0.32, wallT + 0.24, portalMat, 0, pH + 0.1, 0, 0.05);

    // Overhead Doorway Lintel Sign (for North Wing rooms; South Wing rooms have the grand portal sign just above)
    if (isNorthWing) {
      const lintelW = 4.4;
      const lintelH = 0.86;
      const lintelTex = makeSignTexture({
        code: r.code,
        title: r.signTitle,
        subtitle: '',
        accent: r.accent,
        bg: '#1c232d',
        fg: '#f8f6f0',
        border: '#cfa968',
        width: 768,
        height: 160,
        compact: true,
      });
      const lintelGroup = new THREE.Group();
      lintelGroup.position.set(0, pH + 0.65, 0.18);
      lintelGroup.rotation.x = -0.22; // Tilted toward isometric camera
      portal.add(lintelGroup);
      addRBox(lintelGroup, lintelW + 0.2, lintelH + 0.16, 0.12, portalMat, 0, 0, -0.04, 0.04);
      const lintelFace = new THREE.Mesh(
        new THREE.PlaneGeometry(lintelW, lintelH),
        new THREE.MeshBasicMaterial({ map: lintelTex })
      );
      lintelFace.position.z = 0.04;
      lintelFace.userData = { type: 'room', id: r.id };
      lintelGroup.add(lintelFace);
      pickables.push(lintelFace);
    }

    cursor = rightEdge;
  }

  const tailW = halfW - cursor;
  if (tailW > 0.2) {
    const cx = cursor + tailW / 2;
    addBox(g, tailW, wallH, wallT, wallMat, cx, wallH / 2, zPos);
    addBox(g, tailW, 0.1, wallT + 0.06, capMat, cx, wallH + 0.05, zPos);
  }
}

function populateRoomInterior(r, g, archProps, mats) {
  const { walnutMat, oakMat, brassMat, darkMetalMat, glassMat } = mats;
  const bookColors = [0xc86446, 0x2d6cdf, 0x1f7a54, 0xe0a94b, 0x5c6672, 0x9b4d6a];

  if (r.id === 'boss') {
    // Executive Lounge Sofa + Coffee Table + Award Frames + Indoor Palm
    const lounge = new THREE.Group();
    lounge.position.set(-6.8, 0, -4.8);
    g.add(lounge);
    const leatherMat = stdMat(0x523a2c, 0.55, 0.08);
    addRBox(lounge, 4.4, 0.48, 1.8, leatherMat, 0, 0.32, 0, 0.12);
    addRBox(lounge, 4.4, 0.75, 0.42, leatherMat, 0, 0.78, -0.7, 0.12);
    addRBox(lounge, 0.42, 0.65, 1.8, leatherMat, -2.0, 0.62, 0, 0.1);
    addRBox(lounge, 0.42, 0.65, 1.8, leatherMat, 2.0, 0.62, 0, 0.1);
    // Coffee Table
    addRBox(lounge, 2.6, 0.08, 1.2, walnutMat, 0, 0.45, 1.65, 0.04);
    addBox(lounge, 0.8, 0.06, 0.55, stdMat(0x1f7a54, 0.5), -0.4, 0.52, 1.65);

    // Executive Credenza on Left Wall
    addRBox(g, 1.1, 1.1, 6.2, walnutMat, -9.8, 0.55, 1.2, 0.08);
    addCyl(g, 0.45, 0.35, 0.7, 10, stdMat(0x9b6b43, 0.7), 9.4, 0.35, 6.8);
    const palm = new THREE.Mesh(new THREE.DodecahedronGeometry(0.95, 1), stdMat(0x4b8f56, 0.72));
    palm.position.set(9.4, 1.45, 6.8);
    g.add(palm);
  } else if (r.id === 'research') {
    // Wall-to-Wall Reference Bookcases + Rotating Terrestrial Globe + Scout Bar Chart Terminal
    for (const bx of [-7.2, 7.2]) {
      const shelf = new THREE.Group();
      shelf.position.set(bx, 0, -8.4);
      g.add(shelf);
      addRBox(shelf, 4.2, 3.2, 0.75, walnutMat, 0, 1.6, 0, 0.06);
      for (let row = 0; row < 4; row++) {
        for (let b = 0; b < 7; b++) {
          const bc = bookColors[(row * 7 + b) % bookColors.length];
          addBox(shelf, 0.38, 0.52, 0.55, stdMat(bc, 0.65), -1.45 + b * 0.48, 0.45 + row * 0.72, 0.08, false, true);
        }
      }
    }

    // Rotating Terrestrial Globe on Brass Pedestal
    const globeGroup = new THREE.Group();
    globeGroup.position.set(-7.6, 0, 4.2);
    g.add(globeGroup);
    addCyl(globeGroup, 0.42, 0.55, 0.14, 16, brassMat, 0, 0.07, 0);
    addCyl(globeGroup, 0.08, 0.08, 1.25, 10, brassMat, 0, 0.7, 0);
    const globeMesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.68, 20, 16),
      stdMat(0x2d6cdf, 0.45, 0.1)
    );
    globeMesh.position.y = 1.65;
    globeMesh.castShadow = true;
    globeGroup.add(globeMesh);
    // Landmass patches on globe
    const landMat = stdMat(0x4d9b60, 0.6, 0.05);
    addBox(globeMesh, 0.55, 0.45, 0.3, landMat, 0.42, 0.15, 0.32);
    addBox(globeMesh, 0.4, 0.5, 0.35, landMat, -0.38, -0.1, -0.35);
    archProps.globeMesh = globeMesh;

    // Live yt-dlp Scout 3D Bar Chart Board on Right Wall
    const chartBoard = new THREE.Group();
    chartBoard.position.set(9.8, 2.2, -1.5);
    chartBoard.rotation.y = -Math.PI / 2;
    g.add(chartBoard);
    addRBox(chartBoard, 5.2, 2.4, 0.16, darkMetalMat, 0, 0, 0, 0.06);
    for (let i = 0; i < 6; i++) {
      const barCol = i % 2 === 0 ? 0x2d6cdf : 0x1f7a54;
      const bar = addBox(
        chartBoard,
        0.48,
        1.0,
        0.14,
        new THREE.MeshStandardMaterial({ color: barCol, emissive: barCol, emissiveIntensity: 0.35 }),
        -1.75 + i * 0.7,
        -0.3,
        0.12
      );
      archProps.scoutBars.push({ mesh: bar, phase: i * 0.9 });
    }
  } else if (r.id === 'script') {
    // 13-Block Storyboard Timeline Board on Left Wall + Cozy Reading Lounge
    const storyBoard = new THREE.Group();
    storyBoard.position.set(-9.9, 2.2, -1.5);
    storyBoard.rotation.y = Math.PI / 2;
    g.add(storyBoard);
    addRBox(storyBoard, 6.4, 2.3, 0.16, walnutMat, 0, 0, 0, 0.06);
    addBox(storyBoard, 6.0, 1.95, 0.18, stdMat(0xf5efe4, 0.85), 0, 0, 0.02);
    for (let row = 0; row < 2; row++) {
      for (let col = 0; col < 6; col++) {
        const cardCol = bookColors[(row * 6 + col) % bookColors.length];
        addBox(storyBoard, 0.76, 0.55, 0.06, stdMat(cardCol, 0.6), -2.3 + col * 0.92, 0.42 - row * 0.82, 0.12);
      }
    }

    // Writers' Reference Shelf & Reading Lamp Corner
    addRBox(g, 4.4, 3.1, 0.75, walnutMat, -6.8, 1.55, -8.4, 0.06);
    addCyl(g, 0.35, 0.42, 0.1, 14, brassMat, 7.6, 0.05, -6.5);
    addCyl(g, 0.05, 0.05, 2.4, 8, brassMat, 7.6, 1.25, -6.5);
    const shade = new THREE.Mesh(
      new THREE.ConeGeometry(0.55, 0.6, 14, 1, true),
      new THREE.MeshStandardMaterial({ color: 0xfff0cc, emissive: 0xffb84d, emissiveIntensity: 0.4, side: THREE.DoubleSide })
    );
    shade.position.set(7.6, 2.55, -6.5);
    g.add(shade);
  } else if (r.id === 'art') {
    // Grand Art & Animation Wing:
    // 1. Tripod Easel with Master Cast Sheet near Art Director (x = -21.5, z = -5.5)
    const easel = new THREE.Group();
    easel.position.set(-22.2, 0, -5.8);
    easel.rotation.y = 0.38;
    g.add(easel);
    addCyl(easel, 0.06, 0.06, 2.9, 8, oakMat, -0.65, 1.45, 0).rotation.z = -0.12;
    addCyl(easel, 0.06, 0.06, 2.9, 8, oakMat, 0.65, 1.45, 0).rotation.z = 0.12;
    addCyl(easel, 0.06, 0.06, 2.9, 8, oakMat, 0, 1.45, -0.55).rotation.x = 0.22;
    addRBox(easel, 2.3, 1.65, 0.12, stdMat(0xfdfbf7, 0.6), 0, 1.85, 0.12, 0.04);
    // Cast sheet character silhouettes on easel
    for (let c = -2; c <= 2; c++) {
      addBox(easel, 0.22, 0.65, 0.04, stdMat(0x1d2329, 0.5), c * 0.38, 1.8, 0.19);
    }

    // 2. Four Digital Cintiq Drawing Tablets on Painters' Desks (tracked for live brush glow)
    const painterXs = [-7.5, 0.5, 8.5, 16.5];
    const artColors = [0x2d6cdf, 0xc86446, 0x1f7a54, 0xd9822b];
    for (let i = 0; i < 4; i++) {
      const px = painterXs[i];
      const padMat = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        emissive: artColors[i],
        emissiveIntensity: 0.28,
        roughness: 0.25,
      });
      const pad = addRBox(g, 1.55, 0.08, 1.05, padMat, px, 1.12, -1.55, 0.03);
      pad.rotation.x = 0.42;
      archProps.cintiqScreens.push({ mesh: pad, mat: padMat, baseColor: artColors[i], index: i + 1 });
    }

    // 3. Backlit QA Light-Table & Scene Gallery Wall for Reviewer (East side of Art Studio)
    const lightTable = new THREE.Group();
    lightTable.position.set(17.5, 0, 4.2);
    g.add(lightTable);
    addRBox(lightTable, 4.6, 0.88, 2.4, darkMetalMat, 0, 0.44, 0, 0.08);
    const glassTop = new THREE.Mesh(
      new THREE.PlaneGeometry(4.1, 1.95),
      new THREE.MeshStandardMaterial({ color: 0xeaf6ff, emissive: 0x99d1ff, emissiveIntensity: 0.45 })
    );
    glassTop.rotation.x = -Math.PI / 2;
    glassTop.position.y = 0.9;
    lightTable.add(glassTop);

    // Framed Scene Prints on East Wall of Art Studio
    for (let row = 0; row < 2; row++) {
      for (let col = 0; col < 4; col++) {
        const fc = bookColors[(row * 4 + col) % bookColors.length];
        addRBox(g, 0.14, 0.95, 1.45, walnutMat, 24.6, 1.65 + row * 1.2, -5.5 + col * 3.4, 0.03);
        addBox(g, 0.16, 0.75, 1.25, stdMat(fc, 0.5), 24.55, 1.65 + row * 1.2, -5.5 + col * 3.4);
      }
    }
  } else if (r.id === 'voice') {
    // Glass-Enclosed Acoustic Vocal Booth + Condenser Mic + Pulsing "ON AIR" Sign + Mixing Console
    const booth = new THREE.Group();
    booth.position.set(4.8, 0, 2.2);
    g.add(booth);

    const boothW = 6.8;
    const boothD = 6.8;
    const boothH = 3.2;
    const foamMat = stdMat(0x28303a, 0.92, 0.05);

    // Acoustic back & right walls inside booth
    addBox(booth, boothW, boothH, 0.25, foamMat, 0, boothH / 2, boothD / 2);
    addBox(booth, 0.25, boothH, boothD, foamMat, boothW / 2, boothH / 2, 0);
    // Acoustic pyramid tiles pattern
    for (let tx = -2.4; tx <= 2.4; tx += 1.2) {
      for (let ty = 0.8; ty <= 2.4; ty += 0.8) {
        addBox(booth, 0.85, 0.55, 0.14, stdMat(0x394452, 0.9), tx, ty, boothD / 2 - 0.18);
      }
    }
    // Glass front & left walls of Vocal Booth
    addBox(booth, boothW, boothH, 0.12, glassMat, 0, boothH / 2, -boothD / 2, false, false);
    addBox(booth, 0.12, boothH, boothD, glassMat, -boothW / 2, boothH / 2, 0, false, false);
    addRBox(booth, boothW + 0.2, 0.18, boothD + 0.2, darkMetalMat, 0, boothH + 0.09, 0, 0.05);

    // Condenser Microphone on Boom Stand inside Vocal Booth
    addCyl(booth, 0.45, 0.5, 0.1, 14, darkMetalMat, 0, 0.05, 0);
    addCyl(booth, 0.05, 0.05, 2.1, 8, darkMetalMat, 0, 1.1, 0);
    addCyl(booth, 0.14, 0.14, 0.42, 12, brassMat, 0, 2.2, 0);
    // Music/Script stand
    addBox(booth, 0.95, 0.65, 0.06, oakMat, 0, 1.55, -0.85).rotation.x = -0.35;

    // Glowing Red "ON AIR" Lightbox mounted on top of the Vocal Booth
    const onAirMat = new THREE.MeshStandardMaterial({
      color: 0xff3b3b,
      emissive: 0xff2222,
      emissiveIntensity: 0.9,
      roughness: 0.2,
    });
    addRBox(booth, 2.5, 0.62, 0.45, darkMetalMat, 0, boothH + 0.48, -boothD / 2, 0.06);
    addBox(booth, 2.2, 0.42, 0.48, onAirMat, 0, boothH + 0.48, -boothD / 2);
    archProps.onAirMat = onAirMat;

    // Audio Mixing Console with 8 Animated EQ Bars on Left Side
    const mixer = new THREE.Group();
    mixer.position.set(-7.2, 0, 3.2);
    g.add(mixer);
    addRBox(mixer, 3.4, 0.9, 1.8, darkMetalMat, 0, 0.45, 0, 0.08);
    for (let i = 0; i < 8; i++) {
      const eqCol = i < 5 ? 0x2ecb71 : i < 7 ? 0xf2a43a : 0xe0524f;
      const eqBar = addBox(
        mixer,
        0.22,
        0.12,
        0.65,
        new THREE.MeshStandardMaterial({ color: eqCol, emissive: eqCol, emissiveIntensity: 0.7 }),
        -1.22 + i * 0.35,
        0.95,
        0
      );
      archProps.eqBars.push({ mesh: eqBar, phase: i * 0.65 });
    }
  } else if (r.id === 'edit') {
    // 1440p GPU Render Server Racks (2 Towers with Spinning Cooling Fans & Blinking LEDs)
    for (let t = 0; t < 2; t++) {
      const rack = new THREE.Group();
      rack.position.set(5.4 + t * 3.4, 0, 2.8);
      g.add(rack);
      addRBox(rack, 2.6, 3.5, 2.2, darkMetalMat, 0, 1.75, 0, 0.08);

      // Server Blade LED rows
      for (let row = 0; row < 6; row++) {
        const ledColor = row % 2 === 0 ? 0x2ecb71 : 0x2d6cdf;
        const ledMat = new THREE.MeshStandardMaterial({
          color: ledColor,
          emissive: ledColor,
          emissiveIntensity: 0.85,
        });
        addBox(rack, 1.8, 0.1, 0.06, ledMat, 0, 0.65 + row * 0.44, -1.11);
        archProps.serverLeds.push({ mat: ledMat, phase: t * 2 + row * 0.8 });
      }

      // 2 Spinning Cooling Fans on top of each GPU Server Tower
      for (const fx of [-0.6, 0.6]) {
        const fanGroup = new THREE.Group();
        fanGroup.position.set(fx, 3.54, 0);
        rack.add(fanGroup);
        addBox(fanGroup, 0.85, 0.05, 0.18, brassMat, 0, 0, 0);
        addBox(fanGroup, 0.18, 0.05, 0.85, brassMat, 0, 0, 0);
        archProps.renderFans.push(fanGroup);
      }
    }

    // Wide NLE Timeline Wall Display with Moving Playhead
    const nleWall = new THREE.Group();
    nleWall.position.set(-11.6, 2.15, 1.5);
    nleWall.rotation.y = Math.PI / 2;
    g.add(nleWall);
    addRBox(nleWall, 6.2, 2.2, 0.16, darkMetalMat, 0, 0, 0, 0.06);
    // Track bars
    addBox(nleWall, 5.4, 0.28, 0.06, stdMat(0x2d6cdf, 0.4), 0, 0.45, 0.1);
    addBox(nleWall, 4.8, 0.28, 0.06, stdMat(0x1f7a54, 0.4), -0.3, 0.0, 0.1);
    addBox(nleWall, 5.1, 0.28, 0.06, stdMat(0xc86446, 0.4), 0.1, -0.45, 0.1);
    // Moving Vertical Playhead
    const playhead = addBox(
      nleWall,
      0.08,
      1.65,
      0.12,
      new THREE.MeshBasicMaterial({ color: 0xffd15c }),
      0,
      0,
      0.14
    );
    archProps.timelinePlayhead = playhead;
  } else if (r.id === 'publish') {
    // 1. Hall of Published Videos Trophy Shelf & Golden Play Plaques
    const trophyShelf = new THREE.Group();
    trophyShelf.position.set(11.4, 0, 0.5);
    trophyShelf.rotation.y = -Math.PI / 2;
    g.add(trophyShelf);
    addRBox(trophyShelf, 5.8, 2.8, 0.85, walnutMat, 0, 1.4, 0, 0.08);
    for (let i = -1; i <= 1; i++) {
      addRBox(trophyShelf, 1.15, 0.85, 0.14, brassMat, i * 1.65, 2.1, 0.42, 0.04);
    }

    // 2. Thumbnail Preview Wall Board
    const thumbWall = new THREE.Group();
    thumbWall.position.set(-11.6, 2.15, 1.8);
    thumbWall.rotation.y = Math.PI / 2;
    g.add(thumbWall);
    addRBox(thumbWall, 5.8, 2.3, 0.16, darkMetalMat, 0, 0, 0, 0.06);
    addBox(thumbWall, 2.4, 1.45, 0.08, stdMat(0xd96b43, 0.45), -1.35, 0, 0.1);
    addBox(thumbWall, 2.4, 1.45, 0.08, stdMat(0x2d6cdf, 0.45), 1.35, 0, 0.1);

    // 3. Rotating Satellite Uplink Dish on Pedestal
    const dishBase = new THREE.Group();
    dishBase.position.set(8.2, 0, 6.2);
    g.add(dishBase);
    addCyl(dishBase, 0.5, 0.65, 1.2, 12, darkMetalMat, 0, 0.6, 0);
    const dishHead = new THREE.Group();
    dishHead.position.y = 1.55;
    dishBase.add(dishHead);
    const bowl = new THREE.Mesh(
      new THREE.ConeGeometry(1.15, 0.55, 18, 1, true),
      stdMat(0xecf0f4, 0.35, 0.3, { side: THREE.DoubleSide })
    );
    bowl.rotation.x = -0.75;
    dishHead.add(bowl);
    archProps.uplinkDish = dishHead;
  }
}
