import * as THREE from 'three';
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import {
  COLORS,
  STAFF,
  roomById,
  stdMat,
  addRBox,
  addBox,
  addCyl,
  makeSignTexture,
} from './constants.js';

const SKIN_TONES = [0xf4cbb2, 0xeec0a4, 0xf6d2bc, 0xe5b598];
const HAIR_TONES = [0x231c18, 0x3b2a22, 0x1d2228, 0x4a3429];

export function createDesignerCharacter(spec, index = 0) {
  const root = new THREE.Group();
  const primaryColor = COLORS[spec.who] || 0x2d6cdf;
  const jacketMat = stdMat(primaryColor, 0.52, 0.04);
  const shirtMat = stdMat(0xf7f4ee, 0.65, 0.02);
  const pantsMat = stdMat(0x28303b, 0.72, 0.04);
  const shoeMat = stdMat(0x1b2026, 0.6, 0.08);
  const soleMat = stdMat(0xf2efe9, 0.7, 0.02);
  const skinMat = stdMat(SKIN_TONES[index % SKIN_TONES.length], 0.58, 0.02);
  const hairMat = stdMat(HAIR_TONES[index % HAIR_TONES.length], 0.68, 0.03);
  const darkMat = stdMat(0x181c22, 0.35, 0.15);
  const whiteMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const cheekMat = stdMat(0xeb8f82, 0.7, 0.0);

  // 1. Articulated Legs & Two-Tone Sneakers
  const legs = [];
  for (const s of [-1, 1]) {
    const legPivot = new THREE.Group();
    legPivot.position.set(s * 0.24, 0.72, 0);
    root.add(legPivot);

    addRBox(legPivot, 0.3, 0.62, 0.32, pantsMat, 0, -0.26, 0, 0.1);
    addRBox(legPivot, 0.33, 0.2, 0.46, shoeMat, 0, -0.58, 0.06, 0.08);
    addRBox(legPivot, 0.35, 0.07, 0.48, soleMat, 0, -0.68, 0.06, 0.03);
    legs.push(legPivot);
  }

  // 2. Sculpted Rounded Torso + Layered Shirt Collar / Jacket / Apron
  const bodyGroup = new THREE.Group();
  bodyGroup.position.y = 1.32;
  root.add(bodyGroup);

  const torso = addRBox(bodyGroup, 1.02, 1.12, 0.68, jacketMat, 0, 0, 0, 0.26);
  // Inner shirt V-neck / collar insert
  addRBox(bodyGroup, 0.46, 0.38, 0.71, shirtMat, 0, 0.32, 0.01, 0.08);
  // Subtle belt / hem trim
  addRBox(bodyGroup, 1.04, 0.12, 0.7, pantsMat, 0, -0.48, 0, 0.04);

  // Pocket badge or studio lanyard
  const badgeColor = spec.who === 'owner' ? 0xf2c94c : 0xffffff;
  addRBox(bodyGroup, 0.2, 0.14, 0.05, stdMat(badgeColor, 0.3, 0.3), 0.26, 0.18, 0.35, 0.02);

  // 3. Articulated Arms + Sleeves + Hands + Role Tool
  const arms = [];
  for (const s of [-1, 1]) {
    const armPivot = new THREE.Group();
    armPivot.position.set(s * 0.64, 1.72, 0);
    root.add(armPivot);

    // Rounded sleeve
    addRBox(armPivot, 0.28, 0.72, 0.28, jacketMat, 0, -0.28, 0, 0.12);
    // Shirt cuff
    addRBox(armPivot, 0.26, 0.1, 0.26, shirtMat, 0, -0.64, 0, 0.04);
    // Sculpted hand
    const hand = new THREE.Mesh(new THREE.SphereGeometry(0.16, 14, 12), skinMat);
    hand.position.set(0, -0.78, 0.04);
    hand.castShadow = true;
    armPivot.add(hand);

    // Attach Role Prop to Right Hand (s === 1)
    if (s === 1 && spec.prop) {
      attachRoleProp(hand, spec.prop);
    }

    armPivot.rotation.z = s * 0.16;
    arms.push(armPivot);
  }

  // 4. Sculpted Head + Ears + Blinking Eyes + Headgear/Hair
  const head = new THREE.Group();
  head.position.set(0, 2.42, 0);
  root.add(head);

  const cranium = addRBox(head, 1.08, 0.98, 0.96, skinMat, 0, 0, 0, 0.36);
  // Ears
  for (const s of [-1, 1]) {
    const ear = new THREE.Mesh(new THREE.SphereGeometry(0.14, 10, 10), skinMat);
    ear.position.set(s * 0.55, -0.02, 0);
    head.add(ear);
  }
  // Cute button nose
  const nose = new THREE.Mesh(new THREE.SphereGeometry(0.09, 10, 10), skinMat);
  nose.position.set(0, -0.02, 0.5);
  head.add(nose);

  // Rosy cheeks
  for (const s of [-1, 1]) {
    const cheek = new THREE.Mesh(new THREE.SphereGeometry(0.08, 8, 8), cheekMat);
    cheek.scale.set(1.2, 0.7, 0.4);
    cheek.position.set(s * 0.31, -0.11, 0.46);
    head.add(cheek);
  }

  // Expressive Eyes with Specular Catchlights + Eyebrows
  const eyes = [];
  for (const s of [-1, 1]) {
    const eyeGroup = new THREE.Group();
    eyeGroup.position.set(s * 0.22, 0.08, 0.48);
    head.add(eyeGroup);

    const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.075, 12, 10), darkMat);
    pupil.scale.set(1, 1.15, 0.6);
    eyeGroup.add(pupil);

    const catchlight = new THREE.Mesh(new THREE.SphereGeometry(0.026, 8, 8), whiteMat);
    catchlight.position.set(0.025, 0.03, 0.045);
    eyeGroup.add(catchlight);

    const brow = addRBox(head, 0.18, 0.045, 0.04, hairMat, s * 0.22, 0.24, 0.48, 0.015, false, false);
    brow.rotation.z = s * -0.08;
    eyes.push(eyeGroup);
  }

  // Gentle smile
  const smile = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.024, 8, 16, Math.PI), darkMat);
  smile.position.set(0, -0.16, 0.47);
  smile.rotation.z = Math.PI;
  head.add(smile);

  // Hair & Role Headwear
  buildHeadgear(head, spec.hat || 'hair_glasses', hairMat, jacketMat, darkMat);

  return {
    g: root,
    arms,
    legs,
    head,
    body: torso,
    cranium,
    eyes,
    isRobot: false,
  };
}

export function createRobotCharacter(spec) {
  const root = new THREE.Group();
  const metalShellMat = stdMat(0xe6e9ed, 0.32, 0.35);
  const slateTrimMat = stdMat(0x3a434e, 0.45, 0.45);
  const copperMat = stdMat(0xd48b45, 0.35, 0.65);
  const screenGlassMat = stdMat(0x121820, 0.18, 0.25);

  const eyeHex =
    spec.robotType === 'render'
      ? 0x38ef7d
      : spec.robotType === 'voice'
      ? 0x38bdf8
      : spec.robotType === 'checker'
      ? 0xf59e0b
      : 0x60a5fa;
  const ledMat = new THREE.MeshStandardMaterial({
    color: eyeHex,
    emissive: eyeHex,
    emissiveIntensity: 0.95,
    roughness: 0.2,
  });

  // 1. Articulated Mechanical Biped/Hover Legs
  const legs = [];
  for (const s of [-1, 1]) {
    const legPivot = new THREE.Group();
    legPivot.position.set(s * 0.26, 0.68, 0);
    root.add(legPivot);

    addCyl(legPivot, 0.11, 0.11, 0.48, 12, slateTrimMat, 0, -0.22, 0);
    addRBox(legPivot, 0.36, 0.22, 0.48, metalShellMat, 0, -0.56, 0.04, 0.08);
    legs.push(legPivot);
  }

  // 2. Brushed Ceramic & Titanium Rounded Chassis + Chest Telemetry Screen
  const bodyGroup = new THREE.Group();
  bodyGroup.position.y = 1.3;
  root.add(bodyGroup);

  const torso = addRBox(bodyGroup, 1.08, 1.08, 0.76, metalShellMat, 0, 0, 0, 0.22);
  addRBox(bodyGroup, 0.72, 0.52, 0.06, screenGlassMat, 0, 0.08, 0.37, 0.06);
  // 3 glowing chest telemetry bars
  for (let i = -1; i <= 1; i++) {
    addBox(bodyGroup, 0.48 - Math.abs(i) * 0.1, 0.06, 0.07, ledMat, 0, 0.08 + i * 0.13, 0.38, false, false);
  }

  // 3. Articulated Mechanical Arms
  const arms = [];
  for (const s of [-1, 1]) {
    const armPivot = new THREE.Group();
    armPivot.position.set(s * 0.68, 1.66, 0);
    root.add(armPivot);

    // Copper shoulder joint
    const joint = new THREE.Mesh(new THREE.SphereGeometry(0.15, 12, 10), copperMat);
    armPivot.add(joint);
    addRBox(armPivot, 0.24, 0.64, 0.24, metalShellMat, 0, -0.34, 0, 0.08);
    const claw = new THREE.Mesh(new THREE.SphereGeometry(0.15, 12, 10), slateTrimMat);
    claw.position.set(0, -0.74, 0.04);
    armPivot.add(claw);

    if (s === 1 && spec.prop) {
      attachRoleProp(claw, spec.prop);
    }

    armPivot.rotation.z = s * 0.15;
    arms.push(armPivot);
  }

  // 4. Wide CRT/Visor Robot Head + Glowing Pixel Eyes + Spinning Copper Antenna
  const head = new THREE.Group();
  head.position.set(0, 2.38, 0);
  root.add(head);

  const cranium = addRBox(head, 1.18, 0.88, 0.92, metalShellMat, 0, 0, 0, 0.24);
  // Dark Glass Visor Faceplate
  addRBox(head, 0.96, 0.56, 0.08, screenGlassMat, 0, 0.02, 0.44, 0.12);

  // Side Ear Pods
  for (const s of [-1, 1]) {
    addCyl(head, 0.18, 0.18, 0.16, 14, copperMat, s * 0.62, 0.02, 0).rotation.z = Math.PI / 2;
  }

  // Glowing LED Visor Eyes
  const eyes = [];
  for (const s of [-1, 1]) {
    const eye = addRBox(head, 0.22, 0.24, 0.06, ledMat, s * 0.23, 0.04, 0.47, 0.06, false, false);
    eyes.push(eye);
  }

  // Top Spinning Telemetry Antenna
  const antenna = new THREE.Group();
  antenna.position.set(0, 0.46, 0);
  head.add(antenna);
  addCyl(antenna, 0.04, 0.06, 0.34, 8, copperMat, 0, 0.17, 0);
  addBox(antenna, 0.42, 0.05, 0.08, copperMat, 0, 0.28, 0);
  const tip = new THREE.Mesh(new THREE.SphereGeometry(0.1, 10, 10), ledMat);
  tip.position.y = 0.38;
  antenna.add(tip);

  return {
    g: root,
    arms,
    legs,
    head,
    body: torso,
    cranium,
    eyes,
    antenna,
    ledMat,
    isRobot: true,
  };
}

function buildHeadgear(head, hatType, hairMat, accentMat, darkMat) {
  // Base sculpted hair cap & sideburns
  addRBox(head, 1.12, 0.36, 1.0, hairMat, 0, 0.38, -0.02, 0.16);
  addRBox(head, 1.1, 0.65, 0.45, hairMat, 0, 0.06, -0.32, 0.16);

  if (hatType === 'hair_glasses' || hatType === 'glasses') {
    // Swept front hair fringe
    addRBox(head, 0.92, 0.22, 0.35, hairMat, 0.08, 0.44, 0.36, 0.09).rotation.z = -0.08;
    // Designer Eyeglasses Frame
    const frameMat = hatType === 'hair_glasses' ? stdMat(0x4a2f1d, 0.3, 0.2) : darkMat;
    for (const s of [-1, 1]) {
      const rim = new THREE.Mesh(new THREE.TorusGeometry(0.15, 0.024, 8, 20), frameMat);
      rim.position.set(s * 0.22, 0.08, 0.49);
      head.add(rim);
    }
    addBox(head, 0.16, 0.025, 0.03, frameMat, 0, 0.09, 0.49);
  } else if (hatType === 'beret') {
    // Classic tilted Artist/Writer Beret
    const beret = new THREE.Group();
    beret.position.set(-0.08, 0.52, 0.02);
    beret.rotation.z = 0.18;
    head.add(beret);
    const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.58, 0.48, 0.22, 20), accentMat);
    cap.castShadow = true;
    beret.add(cap);
    addCyl(beret, 0.03, 0.03, 0.14, 6, accentMat, 0, 0.15, 0);
  } else if (hatType === 'visor') {
    // Illustrator Cap & Visor Brim
    const cap = addRBox(head, 1.12, 0.28, 1.0, accentMat, 0, 0.42, 0, 0.12);
    const brim = addRBox(head, 0.96, 0.07, 0.48, accentMat, 0, 0.34, 0.55, 0.03);
    brim.rotation.x = 0.12;
  } else if (hatType === 'headphones') {
    // Studio Over-Ear Headphones
    const hpMat = stdMat(0x1f252e, 0.35, 0.4);
    const band = new THREE.Mesh(new THREE.TorusGeometry(0.6, 0.055, 10, 24, Math.PI), hpMat);
    band.position.set(0, 0.05, 0);
    head.add(band);
    for (const s of [-1, 1]) {
      const cup = addCyl(head, 0.2, 0.2, 0.16, 16, accentMat, s * 0.6, -0.02, 0);
      cup.rotation.z = Math.PI / 2;
    }
  }
}

function attachRoleProp(handMesh, propKind) {
  const brassMat = stdMat(0xd4a656, 0.35, 0.65);
  const darkMat = stdMat(0x20262e, 0.4, 0.3);
  const whiteMat = stdMat(0xf8f6f2, 0.5, 0.05);

  if (propKind === 'stylus' || propKind === 'pen') {
    const pen = addCyl(handMesh, 0.028, 0.02, 0.52, 8, propKind === 'stylus' ? whiteMat : brassMat, 0, -0.05, 0.18);
    pen.rotation.x = Math.PI / 3;
  } else if (propKind === 'mug') {
    const mug = addCyl(handMesh, 0.11, 0.09, 0.24, 12, whiteMat, 0, -0.04, 0.16);
    mug.rotation.x = Math.PI / 2;
  } else if (propKind === 'loupe') {
    const handle = addCyl(handMesh, 0.025, 0.025, 0.35, 8, brassMat, 0, -0.04, 0.18);
    handle.rotation.x = Math.PI / 2;
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.14, 0.028, 8, 18), brassMat);
    ring.position.set(0, -0.04, 0.38);
    handMesh.add(ring);
  } else if (propKind === 'clapboard' || propKind === 'tablet') {
    addRBox(handMesh, 0.38, 0.28, 0.04, darkMat, 0, -0.05, 0.2, 0.02);
  }
}

export function buildAllStaffAndCouriers(scene, pickables) {
  // Build the 17 department workers at their workstations
  const deskWoodMat = stdMat(0xd5bc98, 0.64, 0.04);
  const deskLegMat = stdMat(0x2e353e, 0.5, 0.35);
  const chairMat = stdMat(0x454e59, 0.68, 0.1);
  const monitorMat = stdMat(0x232931, 0.42, 0.3);
  const walnutMat = stdMat(0x6e472b, 0.58, 0.06);

  STAFF.forEach((s, idx) => {
    const r = roomById[s.room];
    const g = new THREE.Group();
    g.position.set(s.at[0], 0, s.at[1]);
    r.group.add(g);
    s.group = g;

    // 1. Ergonomic Rounded Desk (in front of character at z = +1.15)
    addRBox(g, 2.75, 0.12, 1.35, deskWoodMat, 0, 0.88, 1.15, 0.05);
    for (const lx of [-1.2, 1.2]) {
      for (const lz of [0.62, 1.68]) {
        addCyl(g, 0.055, 0.055, 0.86, 8, deskLegMat, lx, 0.43, lz);
      }
    }
    // Keyboard & Mouse Pad on Desk + Mini Potted Desk Succulent
    addRBox(g, 0.72, 0.03, 0.26, deskLegMat, -0.1, 0.95, 0.92, 0.01, false, true);
    addRBox(g, 0.22, 0.025, 0.26, stdMat(0x88929e, 0.6), 0.48, 0.95, 0.92, 0.01, false, true);
    addCyl(g, 0.11, 0.08, 0.16, 8, stdMat(0xc86446, 0.7), -1.12, 1.02, 0.78, false);
    addRBox(g, 0.16, 0.14, 0.16, stdMat(0x4b8f56, 0.7), -1.12, 1.15, 0.78, 0.05, false, false);

    // 2. Angled Studio Monitor (offset left so character face, hands & tools are clearly visible) + Status Light Bar
    const monGroup = new THREE.Group();
    monGroup.position.set(-0.68, 0, 1.24);
    monGroup.rotation.y = 0.32;
    g.add(monGroup);

    const monitor = addRBox(monGroup, 1.28, 0.78, 0.11, monitorMat, 0, 1.34, 0, 0.05);
    const screenGlowMat = new THREE.MeshStandardMaterial({
      color: 0xdbeafe,
      emissive: COLORS[s.who],
      emissiveIntensity: 0.28,
      roughness: 0.2,
    });
    const screenFace = new THREE.Mesh(new THREE.PlaneGeometry(1.16, 0.66), screenGlowMat);
    screenFace.position.set(0, 1.34, -0.065);
    screenFace.rotation.y = Math.PI;
    monGroup.add(screenFace);
    s.screenMat = screenGlowMat;

    // Glowing Interactive Work Pad / Tablet on Center-Right of Desk (visible from top-down camera!)
    const padFace = new THREE.Mesh(
      new THREE.PlaneGeometry(0.88, 0.56),
      screenGlowMat
    );
    padFace.rotation.x = -Math.PI / 2 + 0.12;
    padFace.position.set(0.32, 0.96, 1.08);
    g.add(padFace);

    // Monitor Stand
    addCyl(monGroup, 0.055, 0.075, 0.28, 8, deskLegMat, 0, 1.0, 0.02);
    addRBox(monGroup, 0.4, 0.04, 0.28, deskLegMat, 0, 0.95, 0.02, 0.02);

    // Top Status Light Bar on Monitor
    s.lamp = addRBox(
      monGroup,
      1.05,
      0.1,
      0.14,
      new THREE.MeshStandardMaterial({ color: 0x4b5563, emissive: 0x000000, roughness: 0.3 }),
      0,
      1.79,
      0,
      0.04
    );

    // 3. Physical 3D Architectural Desk Nameplate on Front-Right of Desk (No floating employee name tags!)
    const plaqueW = 1.95;
    const plaqueH = 0.46;
    const plaqueGroup = new THREE.Group();
    plaqueGroup.position.set(0.35, 1.06, 1.76);
    plaqueGroup.rotation.x = -0.45; // Angled toward camera
    g.add(plaqueGroup);
    addRBox(plaqueGroup, plaqueW + 0.08, plaqueH + 0.06, 0.12, walnutMat, 0, 0, -0.03, 0.03);

    const plaqueHex = `#${new THREE.Color(COLORS[s.who]).getHexString()}`;
    const plaqueTex = makeSignTexture({
      code: '',
      title: s.plaque || s.name.toUpperCase(),
      subtitle: '',
      accent: plaqueHex,
      bg: '#1c232d',
      fg: '#f6f4ef',
      border: '#cfa968',
      width: 512,
      height: 128,
      compact: true,
    });
    const plaqueFace = new THREE.Mesh(
      new THREE.PlaneGeometry(plaqueW, plaqueH),
      new THREE.MeshBasicMaterial({ map: plaqueTex })
    );
    plaqueFace.position.z = 0.04;
    plaqueFace.userData = { type: 'staff', id: s.id };
    plaqueGroup.add(plaqueFace);
    pickables.push(plaqueFace);
    s.plaqueGroup = plaqueGroup;

    // 4. Ergonomic Studio Chair behind Character
    const chair = new THREE.Group();
    chair.position.set(0, 0, -0.58);
    g.add(chair);
    addCyl(chair, 0.35, 0.42, 0.08, 12, deskLegMat, 0, 0.06, 0);
    addCyl(chair, 0.06, 0.06, 0.42, 8, deskLegMat, 0, 0.26, 0);
    addRBox(chair, 0.95, 0.12, 0.92, chairMat, 0, 0.48, 0, 0.05);
    addRBox(chair, 0.92, 0.95, 0.14, chairMat, 0, 0.98, -0.4, 0.06);
    s.chair = chair;

    // Rising creative spark motes over desk
    s.sparks = [];
    const sparkMat = new THREE.MeshBasicMaterial({
      color: COLORS[s.who],
      transparent: true,
      opacity: 0.65,
    });
    for (let sp = 0; sp < 2; sp++) {
      const m = new THREE.Mesh(new THREE.OctahedronGeometry(0.08, 0), sparkMat.clone());
      m.position.set(-0.2 + sp * 0.55, 1.35, 1.05);
      g.add(m);
      s.sparks.push({ mesh: m, phase: idx * 1.1 + sp * 2.2 });
    }

    // 5. Build Character Figure (Designer Mascot OR Studio Robot - zero stick figures!)
    const fig =
      s.who === 'code'
        ? createRobotCharacter(s)
        : createDesignerCharacter(s, idx);
    fig.g.position.set(0, 0, -0.15);
    g.add(fig.g);
    s.fig = fig;

    // 6. Subtle Floor Status Halo Ring
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.82, 1.02, 36),
      new THREE.MeshBasicMaterial({
        color: 0x9aa3ab,
        transparent: true,
        opacity: 0.55,
        side: THREE.DoubleSide,
      })
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(0, 0.13, -0.15);
    g.add(ring);
    s.ring = ring;

    // 7. Task Activity Pill (only shown when actively running/done/error)
    const bubbleEl = document.createElement('div');
    bubbleEl.className = 'bubble';
    const bubbleObj = new CSS2DObject(bubbleEl);
    bubbleObj.position.set(0, 3.65, -0.15);
    bubbleObj.visible = false;
    g.add(bubbleObj);
    s.bubble = bubbleObj;

    // Register pickable meshes for raycasting
    for (const m of [fig.body, fig.cranium, monitor]) {
      m.userData = { type: 'staff', id: s.id };
      pickables.push(m);
    }

    s.phase = idx * 0.85 + 0.4;
    s.blinkTimer = 1.5 + (idx % 4) * 0.9;
  });

  // 8. Build 2 Dedicated Studio Courier Mascots in the Central Atrium Corridor for Folder Handoffs!
  const couriers = [];
  const courierConfigs = [
    { id: 'courier_1', who: 'gemini', hat: 'visor', homeX: -18, homeZ: 0 },
    { id: 'courier_2', who: 'claude', hat: 'beret', homeX: 16, homeZ: 0 },
  ];

  courierConfigs.forEach((cc, i) => {
    const fig = createDesignerCharacter({ who: cc.who, hat: cc.hat, prop: null }, i + 10);
    fig.g.position.set(cc.homeX, 0.08, cc.homeZ);
    scene.add(fig.g);

    // Held 3D Production Folder / Film Case in the courier's hands
    const carryGroup = new THREE.Group();
    carryGroup.position.set(0, 1.28, 0.62);
    carryGroup.visible = false;
    fig.g.add(carryGroup);

    const folderCase = addRBox(
      carryGroup,
      0.86,
      0.16,
      0.62,
      new THREE.MeshStandardMaterial({
        color: 0xf5d372,
        emissive: 0xd9822b,
        emissiveIntensity: 0.25,
        roughness: 0.4,
      }),
      0,
      0,
      0,
      0.04
    );
    // Brass clasp on carried folder
    addBox(carryGroup, 0.24, 0.18, 0.66, stdMat(0x1f7a54, 0.4), 0, 0, 0);

    // Floating status pill above courier during delivery
    const cBubbleEl = document.createElement('div');
    cBubbleEl.className = 'bubble handoff';
    const cBubble = new CSS2DObject(cBubbleEl);
    cBubble.position.set(0, 3.55, 0);
    cBubble.visible = false;
    fig.g.add(cBubble);

    couriers.push({
      id: cc.id,
      fig,
      carryGroup,
      folderCase,
      bubble: cBubble,
      home: new THREE.Vector3(cc.homeX, 0.08, cc.homeZ),
      task: null,
      phase: i * 3.14,
    });
  });

  return { couriers };
}
