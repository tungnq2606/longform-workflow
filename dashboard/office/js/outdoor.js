import * as THREE from 'three';
import { stdMat, addRBox, addBox, addCyl, makeSignTexture } from './constants.js';

export function buildOutdoorWorld(scene) {
  const world = new THREE.Group();
  world.name = 'OutdoorWorld';
  scene.add(world);

  const trees = [];
  const vehicles = [];
  const clouds = [];
  const birds = [];
  const ripples = [];
  const streetLights = [];
  const koiFish = [];
  const pedestrians = [];

  // 1. Diorama Base & Layered Grounds
  const plinthMat = stdMat(0x8e9985, 0.92, 0.02);
  const grassMainMat = stdMat(0xa8be96, 0.88, 0.02);
  const grassRichMat = stdMat(0x93ae80, 0.86, 0.02);
  const stonePlazaMat = stdMat(0xd6d0c4, 0.82, 0.04);
  const pathStoneMat = stdMat(0xc8c1b4, 0.84, 0.03);

  // Deep diorama plinth
  addBox(world, 320, 4, 260, plinthMat, 0, -2.5, 0, false, true);
  // Main grass expanse
  addRBox(world, 280, 0.5, 220, grassMainMat, 0, -0.35, 0, 0.2, false, true);
  // Inner manicured campus lawn
  addRBox(world, 176, 0.16, 118, grassRichMat, 0, -0.12, -2, 0.06, false, true);

  // Building architectural stone terrace foundation
  addRBox(world, 102, 0.24, 60, stonePlazaMat, 0, -0.08, 0, 0.08, false, true);

  // West & East Atrium Entrance Plazas
  addRBox(world, 18, 0.18, 16, stonePlazaMat, -54, -0.06, 0, 0.06, false, true);
  addRBox(world, 18, 0.18, 16, stonePlazaMat, 54, -0.06, 0, 0.06, false, true);

  // 2. Distant Rolling Hills (North, West, East)
  const hillColors = [0x8aa678, 0x7d996c, 0x97b185];
  const hillDefs = [
    { x: -75, z: -68, rx: 36, ry: 9.5, rz: 22, c: 0 },
    { x: -24, z: -74, rx: 44, ry: 12.5, rz: 24, c: 1 },
    { x: 32, z: -72, rx: 48, ry: 11.0, rz: 25, c: 2 },
    { x: 82, z: -64, rx: 38, ry: 10.0, rz: 24, c: 0 },
    { x: -95, z: -22, rx: 24, ry: 8.0, rz: 36, c: 1 },
    { x: 96, z: -18, rx: 26, ry: 8.5, rz: 38, c: 2 },
  ];
  for (const h of hillDefs) {
    const hillGeo = new THREE.SphereGeometry(1, 24, 16);
    const hill = new THREE.Mesh(hillGeo, stdMat(hillColors[h.c], 0.9, 0.01));
    hill.scale.set(h.rx, h.ry, h.rz);
    hill.position.set(h.x, -1.8, h.z);
    hill.receiveShadow = true;
    world.add(hill);
  }

  // 3. South Boulevard, Sidewalk Promenade, Crosswalk & Street Furniture
  const roadMat = stdMat(0x3a4048, 0.88, 0.05);
  const curbMat = stdMat(0xc4bdb0, 0.8, 0.04);
  const stripeMat = stdMat(0xf2efe9, 0.5, 0.02);

  // North sidewalk along building front (z = 26 to 32)
  addRBox(world, 190, 0.22, 6.2, curbMat, 0, -0.04, 29.2, 0.06, false, true);
  // Asphalt avenue (z = 32.3 to 43.7)
  addBox(world, 240, 0.14, 11.4, roadMat, 0, -0.09, 38.0, false, true);
  // South parkway sidewalk (z = 43.8 to 48.0)
  addRBox(world, 190, 0.22, 4.2, curbMat, 0, -0.04, 46.0, 0.06, false, true);

  // Dashed lane divider stripes
  for (let x = -104; x <= 104; x += 7.5) {
    if (Math.abs(x - -22) < 4.5 || Math.abs(x - 22) < 4.5) continue;
    addBox(world, 3.4, 0.04, 0.26, stripeMat, x, 0.0, 38.0, false, true);
  }

  // Two Zebra Crosswalks (at x = -22 and x = +22) + entry walkways to building
  for (const cx of [-22, 22]) {
    for (let z = 33.4; z <= 42.6; z += 1.3) {
      addBox(world, 3.2, 0.05, 0.65, stripeMat, cx, 0.0, z, false, true);
    }
  }

  // Exterior Campus Monument Sign at Front Plaza (x = 0, z = 28.8)
  const monGroup = new THREE.Group();
  monGroup.position.set(0, 0, 28.6);
  world.add(monGroup);
  addRBox(monGroup, 8.6, 0.45, 1.3, stdMat(0x525860, 0.7, 0.15), 0, 0.22, 0, 0.08);
  addRBox(monGroup, 7.8, 1.85, 0.55, stdMat(0x1f252d, 0.45, 0.25), 0, 1.25, 0, 0.08);
  const monTex = makeSignTexture({
    code: '3D',
    title: 'STUDIO VĂN PHÒNG',
    subtitle: 'CREATIVE CAMPUS · 1440P PIPELINE',
    accent: '#1f7a54',
    bg: '#181e26',
    fg: '#f7f5f0',
    border: '#d4af6a',
    width: 1024,
    height: 256,
  });
  const monFace = new THREE.Mesh(
    new THREE.PlaneGeometry(7.4, 1.55),
    new THREE.MeshBasicMaterial({ map: monTex })
  );
  monFace.position.set(0, 1.25, 0.29);
  monGroup.add(monFace);

  // Streetlamps along promenade & parkway
  const poleMat = stdMat(0x2c333b, 0.5, 0.4);
  const lampXs = [-56, -36, -12, 12, 36, 56];
  for (const lx of lampXs) {
    for (const lz of [31.5, 44.5]) {
      const lg = new THREE.Group();
      lg.position.set(lx, 0, lz);
      world.add(lg);
      addCyl(lg, 0.11, 0.16, 4.4, 10, poleMat, 0, 2.2, 0);
      addRBox(lg, 0.9, 0.12, 0.22, poleMat, 0, 4.35, lz < 35 ? 0.35 : -0.35, 0.04);
      const bulbMat = new THREE.MeshStandardMaterial({
        color: 0xfff3d1,
        emissive: 0xffb84d,
        emissiveIntensity: 0.7,
        roughness: 0.2,
      });
      const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.24, 12, 10), bulbMat);
      bulb.position.set(0, 4.2, lz < 35 ? 0.65 : -0.65);
      lg.add(bulb);
      streetLights.push(bulbMat);
    }
  }

  // Park benches & flower planters on front promenade
  const woodBenchMat = stdMat(0xb87d4b, 0.68, 0.05);
  for (const bx of [-44, -16, 16, 44]) {
    const bg = new THREE.Group();
    bg.position.set(bx, 0, 27.6);
    world.add(bg);
    addRBox(bg, 2.4, 0.12, 0.65, woodBenchMat, 0, 0.48, 0, 0.04);
    addRBox(bg, 2.4, 0.5, 0.1, woodBenchMat, 0, 0.78, -0.28, 0.04);
    addBox(bg, 0.14, 0.46, 0.55, poleMat, -0.95, 0.24, 0);
    addBox(bg, 0.14, 0.46, 0.55, poleMat, 0.95, 0.24, 0);
  }

  // Modern Glass Bus Stop Shelter (at x = 30, z = 45.8)
  const shelter = new THREE.Group();
  shelter.position.set(30, 0, 45.8);
  world.add(shelter);
  addRBox(shelter, 5.2, 0.16, 2.2, poleMat, 0, 2.9, 0, 0.05);
  addCyl(shelter, 0.09, 0.09, 2.9, 8, poleMat, -2.3, 1.45, -0.8);
  addCyl(shelter, 0.09, 0.09, 2.9, 8, poleMat, 2.3, 1.45, -0.8);
  const glassShelterMat = new THREE.MeshPhysicalMaterial({
    color: 0xd8ecff,
    transparent: true,
    opacity: 0.42,
    roughness: 0.12,
  });
  addBox(shelter, 4.6, 2.5, 0.08, glassShelterMat, 0, 1.45, 0.85, false, false);
  addRBox(shelter, 3.2, 0.12, 0.55, woodBenchMat, 0, 0.5, 0.35, 0.04);

  // Bike Rack with Stylized Bicycles (at x = -48, z = 28.4)
  const bikeGroup = new THREE.Group();
  bikeGroup.position.set(-48.5, 0, 28.4);
  world.add(bikeGroup);
  for (let i = 0; i < 4; i++) {
    const rx = (i - 1.5) * 0.9;
    const hoop = new THREE.Mesh(new THREE.TorusGeometry(0.38, 0.04, 8, 16, Math.PI), poleMat);
    hoop.position.set(rx, 0.4, 0);
    bikeGroup.add(hoop);
    if (i < 3) {
      const bCol = [0x1f7a54, 0xd96b43, 0x2d6cdf][i];
      const bMat = stdMat(bCol, 0.4, 0.3);
      for (const wz of [-0.42, 0.42]) {
        const wheel = new THREE.Mesh(new THREE.TorusGeometry(0.28, 0.045, 8, 16), poleMat);
        wheel.rotation.y = Math.PI / 2;
        wheel.position.set(rx + 0.18, 0.32, wz);
        bikeGroup.add(wheel);
      }
      addCyl(bikeGroup, 0.035, 0.035, 0.85, 6, bMat, rx + 0.18, 0.52, 0).rotation.x = Math.PI / 2;
    }
  }

  // 4. West Zen Garden, Reflection Koi Pond & Café Deck (x = -68, z = -2)
  const pondGroup = new THREE.Group();
  pondGroup.position.set(-64, 0, -3);
  world.add(pondGroup);

  // Stone border & water basin
  const waterMat = new THREE.MeshStandardMaterial({
    color: 0x3f8f8b,
    roughness: 0.18,
    metalness: 0.15,
  });
  const pondRimMat = stdMat(0x9a9589, 0.85, 0.04);
  const rim = new THREE.Mesh(new THREE.CylinderGeometry(11.5, 12.2, 0.32, 32), pondRimMat);
  rim.scale.set(1.0, 1, 1.35);
  rim.position.y = 0.02;
  rim.receiveShadow = true;
  pondGroup.add(rim);

  const water = new THREE.Mesh(new THREE.CylinderGeometry(10.6, 10.6, 0.36, 32), waterMat);
  water.scale.set(1.0, 1, 1.35);
  water.position.y = 0.03;
  water.receiveShadow = true;
  pondGroup.add(water);

  // Animated concentric water ripples
  for (let i = 0; i < 3; i++) {
    const rMat = new THREE.MeshBasicMaterial({
      color: 0xc8f4f0,
      transparent: true,
      opacity: 0.45,
      side: THREE.DoubleSide,
    });
    const rMesh = new THREE.Mesh(new THREE.RingGeometry(0.5, 0.65, 28), rMat);
    rMesh.rotation.x = -Math.PI / 2;
    rMesh.position.set((i - 1) * 2.6, 0.23, (i - 1) * 3.1);
    pondGroup.add(rMesh);
    ripples.push({ mesh: rMesh, mat: rMat, phase: i * 2.1 });
  }

  // Lily pads & lotus blooms
  const padMat = stdMat(0x4d8a54, 0.75, 0.02);
  const lotusMat = stdMat(0xf49cbb, 0.5, 0.05);
  const padCoords = [
    [-4.2, -5.5], [-2.8, -4.2], [3.5, 4.8], [4.8, 3.2], [-3.5, 6.2], [2.4, -6.4],
  ];
  for (const [px, pz] of padCoords) {
    const pad = new THREE.Mesh(new THREE.CylinderGeometry(0.65, 0.65, 0.05, 16), padMat);
    pad.position.set(px, 0.22, pz);
    pondGroup.add(pad);
    const flower = new THREE.Mesh(new THREE.OctahedronGeometry(0.22, 0), lotusMat);
    flower.position.set(px, 0.32, pz);
    pondGroup.add(flower);
  }

  // Animated Koi Fish swimming in the reflection pond
  const koiColors = [0xff6b35, 0xf7c548, 0xffffff, 0xe84855, 0xff8c42];
  for (let i = 0; i < 5; i++) {
    const kg = new THREE.Group();
    pondGroup.add(kg);
    const kMat = stdMat(koiColors[i], 0.35, 0.05);
    const body = new THREE.Mesh(new THREE.ConeGeometry(0.14, 0.62, 10), kMat);
    body.rotation.x = Math.PI / 2;
    kg.add(body);
    const tail = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.2, 0.22), kMat);
    tail.position.z = -0.34;
    kg.add(tail);
    koiFish.push({
      group: kg,
      tail,
      angle: i * 1.25,
      rx: 4.2 + (i % 3) * 1.6,
      rz: 5.5 + (i % 2) * 2.4,
      speed: 0.45 + (i % 3) * 0.12,
    });
  }

  // Arched Cedar Footbridge over the pond
  const bridgeMat = stdMat(0xb85d3b, 0.65, 0.06);
  const bridgeGroup = new THREE.Group();
  bridgeGroup.position.set(0, 0.2, 0);
  pondGroup.add(bridgeGroup);
  for (let i = -6; i <= 6; i++) {
    const bx = i * 1.65;
    const archY = Math.cos((i / 6) * (Math.PI / 2)) * 1.15;
    addRBox(bridgeGroup, 1.4, 0.14, 3.2, bridgeMat, bx, archY, 0, 0.04);
    if (i % 2 === 0) {
      addCyl(bridgeGroup, 0.08, 0.08, 1.1, 8, bridgeMat, bx, archY + 0.55, -1.45);
      addCyl(bridgeGroup, 0.08, 0.08, 1.1, 8, bridgeMat, bx, archY + 0.55, 1.45);
    }
  }
  addRBox(bridgeGroup, 21.5, 0.1, 0.12, bridgeMat, 0, 1.45, -1.45, 0.03);
  addRBox(bridgeGroup, 21.5, 0.1, 0.12, bridgeMat, 0, 1.45, 1.45, 0.03);

  // West Outdoor Timber Café Deck (x = -54, z = 14)
  const deckGroup = new THREE.Group();
  deckGroup.position.set(-55, 0, 15);
  world.add(deckGroup);
  addRBox(deckGroup, 12, 0.22, 14, woodBenchMat, 0, 0.06, 0, 0.08);
  const umbColors = [0x1f7a54, 0xc86446];
  for (let i = 0; i < 2; i++) {
    const tz = (i - 0.5) * 6.2;
    addCyl(deckGroup, 1.35, 1.35, 0.1, 20, stdMat(0xf5f1ea, 0.5, 0.05), 0, 0.92, tz);
    addCyl(deckGroup, 0.12, 0.18, 0.9, 10, poleMat, 0, 0.46, tz);
    addCyl(deckGroup, 0.06, 0.06, 2.7, 8, poleMat, 0, 1.5, tz);
    const canopy = new THREE.Mesh(new THREE.ConeGeometry(2.3, 0.85, 12), stdMat(umbColors[i], 0.65, 0.03));
    canopy.position.set(0, 2.95, tz);
    canopy.castShadow = true;
    deckGroup.add(canopy);
    for (const a of [0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2]) {
      addRBox(deckGroup, 0.65, 0.48, 0.65, woodBenchMat, Math.cos(a) * 1.95, 0.36, tz + Math.sin(a) * 1.95, 0.08);
    }
  }

  // 5. East Garden Pergola & Stepping Stones (x = 60, z = 0)
  const eastGarden = new THREE.Group();
  eastGarden.position.set(60, 0, 0);
  world.add(eastGarden);
  for (let i = 0; i < 6; i++) {
    addCyl(eastGarden, 0.85, 0.9, 0.12, 12, pathStoneMat, -6 + i * 2.2, 0.02, Math.sin(i) * 0.8, false);
  }
  const perg = new THREE.Group();
  perg.position.set(8, 0, 0);
  eastGarden.add(perg);
  addRBox(perg, 9, 0.2, 9, stonePlazaMat, 0, 0.05, 0, 0.08);
  for (const px of [-3.8, 3.8]) {
    for (const pz of [-3.8, 3.8]) {
      addRBox(perg, 0.35, 3.8, 0.35, woodBenchMat, px, 1.9, pz, 0.05);
    }
  }
  for (let b = -3.6; b <= 3.6; b += 1.2) {
    addRBox(perg, 8.6, 0.18, 0.22, woodBenchMat, 0, 3.85, b, 0.04);
  }

  // 6. Stylized Multi-Tier Trees (Oak, Pine, Blossom, Cypress)
  const trunkMat = stdMat(0x7c583b, 0.85, 0.02);
  const foliagePalettes = [
    [0x4b8b55, 0x5ea166, 0x72b578], // Lush Emerald Oak
    [0x3b7548, 0x4b8958, 0x5c9c69], // Pine Forest
    [0xd98a6c, 0xe6a182, 0xf0b89b], // Warm Autumn / Blossom Accent
    [0x568c44, 0x6ba356, 0x82b86a], // Meadow Sage
  ];

  function spawnTree(x, z, scale = 1.0, style = 0) {
    const tg = new THREE.Group();
    tg.position.set(x, 0, z);
    tg.scale.setScalar(scale);
    world.add(tg);

    // Trunk
    addCyl(tg, 0.22, 0.36, 2.2, 8, trunkMat, 0, 1.1, 0);

    const crown = new THREE.Group();
    crown.position.y = 2.0;
    tg.add(crown);

    const pal = foliagePalettes[style % foliagePalettes.length];
    if (style % 4 === 1) {
      // Layered Pine Cone tiers
      for (let t = 0; t < 3; t++) {
        const cone = new THREE.Mesh(
          new THREE.ConeGeometry(1.75 - t * 0.38, 1.9, 10),
          stdMat(pal[t], 0.78, 0.02)
        );
        cone.position.y = t * 1.15 + 0.6;
        cone.castShadow = true;
        cone.receiveShadow = true;
        crown.add(cone);
      }
    } else {
      // Sculpted Cloud/Rounded Canopy Clusters
      const puffs = [
        [0, 0.9, 0, 1.45, pal[0]],
        [-0.85, 0.55, 0.45, 1.05, pal[1]],
        [0.85, 0.6, -0.4, 1.1, pal[1]],
        [0.15, 1.65, 0.1, 1.12, pal[2]],
        [-0.4, 0.5, -0.75, 0.95, pal[0]],
      ];
      for (const [px, py, pz, r, col] of puffs) {
        const sp = new THREE.Mesh(
          new THREE.DodecahedronGeometry(r, 1),
          stdMat(col, 0.76, 0.02)
        );
        sp.position.set(px, py, pz);
        sp.castShadow = true;
        sp.receiveShadow = true;
        crown.add(sp);
      }
    }

    trees.push({ crown, phase: (x * 0.17 + z * 0.23) % 6.28 });
  }

  const treeCoords = [
    // North forest line behind building
    [-56, -34, 1.25, 0], [-44, -38, 1.4, 1], [-31, -35, 1.15, 2], [-18, -39, 1.35, 0],
    [-4, -36, 1.2, 3], [11, -38, 1.45, 1], [25, -35, 1.2, 0], [39, -39, 1.35, 2],
    [52, -34, 1.3, 1], [64, -32, 1.15, 3],
    // West garden & pond perimeter
    [-78, -22, 1.3, 1], [-82, -6, 1.4, 0], [-79, 10, 1.25, 2], [-74, 22, 1.15, 3],
    [-54, -20, 1.1, 2], [-56, 25, 1.05, 0],
    // East garden & pergola perimeter
    [55, -20, 1.15, 0], [72, -16, 1.35, 1], [78, 2, 1.3, 2], [74, 16, 1.2, 3],
    [56, 20, 1.1, 0], [64, 26, 1.25, 1],
    // South boulevard parkway trees
    [-72, 50, 1.25, 0], [-50, 51, 1.3, 3], [-30, 50, 1.15, 2], [-8, 51, 1.25, 0],
    [14, 50, 1.2, 3], [42, 51, 1.3, 2], [66, 50, 1.2, 1],
  ];
  for (const [tx, tz, sc, st] of treeCoords) {
    spawnTree(tx, tz, sc, st);
  }

  // 7. Animated Vehicles on South Boulevard (2 lanes: z = 35.4 going East, z = 40.6 going West)
  const carSpecs = [
    { x: -75, z: 35.4, dir: 1, speed: 9.5, color: 0x2d6cdf, kind: 'van' },
    { x: -18, z: 35.4, dir: 1, speed: 9.5, color: 0xd96b43, kind: 'coupe' },
    { x: 42, z: 35.4, dir: 1, speed: 9.5, color: 0x1f7a54, kind: 'hatch' },
    { x: 68, z: 40.6, dir: -1, speed: 8.8, color: 0xe6b44c, kind: 'van' },
    { x: 10, z: 40.6, dir: -1, speed: 8.8, color: 0x4b5563, kind: 'coupe' },
    { x: -48, z: 40.6, dir: -1, speed: 8.8, color: 0xc84b59, kind: 'hatch' },
  ];

  const tireMat = stdMat(0x1e2228, 0.8, 0.1);
  const winMat = stdMat(0x9bc5e8, 0.2, 0.5);
  const headLightMat = new THREE.MeshBasicMaterial({ color: 0xfff6cc });
  const tailLightMat = new THREE.MeshBasicMaterial({ color: 0xff4040 });

  for (const cs of carSpecs) {
    const cg = new THREE.Group();
    cg.position.set(cs.x, 0.05, cs.z);
    if (cs.dir < 0) cg.rotation.y = Math.PI;
    world.add(cg);

    const bodyMat = stdMat(cs.color, 0.38, 0.18);
    const len = cs.kind === 'van' ? 4.2 : 3.5;
    const h = cs.kind === 'van' ? 1.55 : 1.15;

    // Lower chassis
    addRBox(cg, len, 0.65, 1.85, bodyMat, 0, 0.52, 0, 0.16);
    // Cabin
    addRBox(
      cg,
      cs.kind === 'van' ? len * 0.72 : len * 0.56,
      h * 0.55,
      1.62,
      bodyMat,
      cs.kind === 'van' ? 0.2 : -0.15,
      0.85 + h * 0.22,
      0,
      0.16
    );
    // Windshield
    addBox(cg, 0.08, h * 0.42, 1.44, winMat, cs.kind === 'van' ? 1.72 : 0.85, 0.92 + h * 0.18, 0);

    // Headlights & Taillights
    for (const sz of [-0.62, 0.62]) {
      addBox(cg, 0.08, 0.18, 0.28, headLightMat, len / 2 + 0.02, 0.54, sz, false, false);
      addBox(cg, 0.08, 0.18, 0.28, tailLightMat, -len / 2 - 0.02, 0.54, sz, false, false);
    }

    // 4 Wheels
    const wheels = [];
    for (const wx of [-len * 0.32, len * 0.32]) {
      for (const wz of [-0.92, 0.92]) {
        const wMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.34, 0.24, 14), tireMat);
        wMesh.rotation.x = Math.PI / 2;
        wMesh.position.set(wx, 0.34, wz);
        cg.add(wMesh);
        wheels.push(wMesh);
      }
    }

    vehicles.push({ group: cg, wheels, dir: cs.dir, speed: cs.speed });
  }

  // 8. Fluffy 3D Clouds & Soaring Bird Flock
  const cloudMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.92,
    metalness: 0.0,
  });
  for (let i = 0; i < 10; i++) {
    const cl = new THREE.Group();
    const cx = -115 + i * 24 + (i % 3) * 3;
    const cz = -62 - (i % 3) * 14;
    const cy = 18 + (i % 3) * 2.5;
    cl.position.set(cx, cy, cz);
    world.add(cl);

    const puffs = [
      [0, 0, 0, 2.4],
      [-1.9, -0.25, 0.3, 1.7],
      [1.9, -0.2, -0.2, 1.85],
      [0.6, 0.7, 0.4, 1.5],
    ];
    for (const [px, py, pz, r] of puffs) {
      const m = new THREE.Mesh(new THREE.SphereGeometry(r, 12, 10), cloudMat);
      m.scale.y = 0.62;
      m.position.set(px, py, pz);
      cl.add(m);
    }
    clouds.push({ group: cl, speed: 0.65 + (i % 4) * 0.18 });
  }

  // Flock of birds circling high above the West & North gardens
  const birdMat = stdMat(0x2d3748, 0.6, 0.1);
  for (let i = 0; i < 7; i++) {
    const bg = new THREE.Group();
    world.add(bg);
    const lw = addBox(bg, 0.45, 0.05, 0.18, birdMat, -0.22, 0, 0, false, false);
    const rw = addBox(bg, 0.45, 0.05, 0.18, birdMat, 0.22, 0, 0, false, false);
    birds.push({
      group: bg,
      lw,
      rw,
      angle: i * 0.9,
      radius: 26 + (i % 3) * 6,
      center: new THREE.Vector3(-18, 22 + (i % 3) * 1.6, -24),
      speed: 0.38 + (i % 2) * 0.08,
    });
  }

  // Strolling Pedestrians along the South Sidewalk Promenade (z = 29.8 and z = 45.2)
  const pedSpecs = [
    { x: -32, z: 29.6, dir: 1, speed: 2.3, coat: 0x1f7a54, hair: 0x231c18 },
    { x: 18, z: 29.9, dir: -1, speed: 2.1, coat: 0xc86446, hair: 0x3b2a22 },
    { x: -12, z: 45.4, dir: 1, speed: 2.4, coat: 0x2d6cdf, hair: 0x1d2228 },
  ];
  const skinMatPed = stdMat(0xf2c6ac, 0.6, 0.02);
  const pantsMatPed = stdMat(0x28303b, 0.75, 0.03);
  for (const ps of pedSpecs) {
    const pg = new THREE.Group();
    pg.position.set(ps.x, 0.06, ps.z);
    pg.rotation.y = ps.dir > 0 ? Math.PI / 2 : -Math.PI / 2;
    world.add(pg);

    const legL = addRBox(pg, 0.22, 0.48, 0.24, pantsMatPed, -0.14, 0.26, 0, 0.06);
    const legR = addRBox(pg, 0.22, 0.48, 0.24, pantsMatPed, 0.14, 0.26, 0, 0.06);
    addRBox(pg, 0.68, 0.78, 0.46, stdMat(ps.coat, 0.55), 0, 0.88, 0, 0.16);
    const armL = addRBox(pg, 0.2, 0.55, 0.2, stdMat(ps.coat, 0.55), -0.44, 0.86, 0, 0.08);
    const armR = addRBox(pg, 0.2, 0.55, 0.2, stdMat(ps.coat, 0.55), 0.44, 0.86, 0, 0.08);
    addRBox(pg, 0.68, 0.64, 0.62, skinMatPed, 0, 1.62, 0, 0.22);
    addRBox(pg, 0.72, 0.26, 0.66, stdMat(ps.hair, 0.7), 0, 1.88, -0.02, 0.12);

    pedestrians.push({
      group: pg,
      legL,
      legR,
      armL,
      armR,
      dir: ps.dir,
      speed: ps.speed,
      phase: Math.random() * 6,
    });
  }

  return {
    world,
    trees,
    vehicles,
    clouds,
    birds,
    ripples,
    streetLights,
    koiFish,
    pedestrians,
  };
}
