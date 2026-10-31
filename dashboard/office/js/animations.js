import * as THREE from 'three';
import {
  STAFF,
  ROOMS,
  PIPELINE_ORDER,
  roomById,
  getCorridorPath,
} from './constants.js';

const LAMP_HEX = {
  run: 0xf2a43a,
  done: 0x3fbf7f,
  bad: 0xe0524f,
  wait: 0xe0524f,
  idle: 0x000000,
};

export class HandoffSystem {
  constructor(couriers) {
    this.couriers = couriers;
    this.queue = [];
    this.autoTimer = 0.2; // Start an active courier handoff immediately on load
    this.autoStepIdx = 0;
    this.activePulses = [];
  }

  enqueue({ fromRoom, toRoom, label, isRender = false }) {
    if (!fromRoom || !toRoom || fromRoom === toRoom) return;
    this.queue.push({ fromRoom, toRoom, label, isRender });
  }

  triggerDemoHandoff(channelVideos = []) {
    // Pick either an active video's next transition or cycle through the studio pipeline stages
    const fromId = PIPELINE_ORDER[this.autoStepIdx % (PIPELINE_ORDER.length - 1)];
    const toId = PIPELINE_ORDER[(this.autoStepIdx + 1) % (PIPELINE_ORDER.length - 1)];
    this.autoStepIdx++;

    const rFrom = roomById[fromId];
    const rTo = roomById[toId];
    const vTag = channelVideos.length
      ? `Video ${channelVideos[0].slug.slice(0, 3)}`
      : 'Hồ sơ sản xuất';

    this.enqueue({
      fromRoom: fromId,
      toRoom: toId,
      label: `${vTag}: ${rFrom.name.replace('Phòng ', '')} → ${rTo.name.replace('Phòng ', '')}`,
      isRender: fromId === 'edit',
    });
  }

  update(dt, t, reduced, channelVideos = []) {
    if (reduced) return;

    // Periodic ambient studio handoff so the decorative office always shows inter-department collaboration
    const anyBusy = this.couriers.some(c => c.task !== null);
    if (!anyBusy && this.queue.length === 0) {
      this.autoTimer -= dt;
      if (this.autoTimer <= 0) {
        this.autoTimer = 11.0;
        this.triggerDemoHandoff(channelVideos);
      }
    }

    // Assign queued handoffs to free couriers
    if (this.queue.length > 0) {
      const freeCourier = this.couriers.find(c => c.task === null);
      if (freeCourier) {
        const job = this.queue.shift();
        const path = getCorridorPath(job.fromRoom, job.toRoom);
        // Waypoints: current pos -> corridor entry near fromRoom -> fromRoom door -> fromRoom table
        const startPos = freeCourier.fig.g.position.clone();
        const pickupWaypoints = [
          startPos,
          new THREE.Vector3(startPos.x, 0.08, 0),
          path[2].clone().setY(0.08),
          path[1].clone().setY(0.08),
          path[0].clone().setY(0.08),
        ];
        const deliverWaypoints = path.map(p => p.clone().setY(0.08));

        freeCourier.task = {
          phase: 'to_pickup',
          job,
          waypoints: pickupWaypoints,
          deliverWaypoints,
          segIdx: 0,
          segProgress: 0,
          pauseTimer: 0,
        };
        freeCourier.bubble.visible = false;
        freeCourier.carryGroup.visible = false;
      }
    }

    // Animate each courier
    for (const c of this.couriers) {
      const f = c.fig;
      if (!c.task) {
        // Return smoothly to home station in the atrium corridor if not there
        const distHome = f.g.position.distanceTo(c.home);
        if (distHome > 0.25) {
          this.moveAlongStep(c, f.g.position, c.home, dt, t, 5.2, false);
        } else {
          // Gentle idle breathing in atrium
          f.legs[0].rotation.x = 0;
          f.legs[1].rotation.x = 0;
          f.arms[0].rotation.x = Math.sin(t * 2 + c.phase) * 0.08;
          f.arms[1].rotation.x = -Math.sin(t * 2 + c.phase) * 0.08;
          f.head.rotation.y = Math.sin(t * 0.9 + c.phase) * 0.22;
          f.g.position.y = 0.08;
        }
        continue;
      }

      const task = c.task;
      if (task.pauseTimer > 0) {
        task.pauseTimer -= dt;
        f.g.position.y = 0.08 + Math.abs(Math.sin(t * 10)) * 0.12;
        continue;
      }

      const pts = task.waypoints;
      if (task.segIdx >= pts.length - 1) {
        if (task.phase === 'to_pickup') {
          // Reached source room's table: pick up the folder and start delivery!
          task.phase = 'carrying';
          task.waypoints = task.deliverWaypoints;
          task.segIdx = 0;
          task.segProgress = 0;
          task.pauseTimer = 0.35;

          c.carryGroup.visible = true;
          c.folderCase.material.color.setHex(task.job.isRender ? 0x38ef7d : 0xf5d372);
          c.bubble.element.textContent = task.job.label;
          c.bubble.visible = true;

          // Pulse source room's delivery ring
          const rFrom = roomById[task.job.fromRoom];
          if (rFrom?.deliveryRing) {
            this.activePulses.push({ ring: rFrom.deliveryRing, t: 0, color: 0xf2a43a });
          }
        } else if (task.phase === 'carrying') {
          // Reached destination room's table: place the folder down!
          c.carryGroup.visible = false;
          c.bubble.element.textContent = 'Đã giao hồ sơ!';
          const rTo = roomById[task.job.toRoom];
          if (rTo?.deliveryRing) {
            this.activePulses.push({ ring: rTo.deliveryRing, t: 0, color: 0x3fbf7f });
          }

          // Walk back out to corridor home
          const cur = f.g.position.clone();
          const doorOut = task.deliverWaypoints[task.deliverWaypoints.length - 2].clone();
          const corrOut = task.deliverWaypoints[task.deliverWaypoints.length - 3].clone();
          task.phase = 'returning';
          task.waypoints = [cur, doorOut, corrOut, new THREE.Vector3(c.home.x, 0.08, 0), c.home.clone()];
          task.segIdx = 0;
          task.segProgress = 0;
          task.pauseTimer = 0.65;
        } else {
          // Finished returning to atrium
          c.bubble.visible = false;
          c.task = null;
        }
        continue;
      }

      const pA = pts[task.segIdx];
      const pB = pts[task.segIdx + 1];
      const segLen = Math.max(0.001, pA.distanceTo(pB));
      const speed = task.phase === 'carrying' ? 8.2 : 7.0;
      task.segProgress += (dt * speed) / segLen;

      if (task.segProgress >= 1) {
        f.g.position.copy(pB);
        task.segIdx++;
        task.segProgress = 0;
      } else {
        f.g.position.lerpVectors(pA, pB, task.segProgress);
      }

      // Orient courier along movement direction & animate walking stride
      const dx = pB.x - pA.x;
      const dz = pB.z - pA.z;
      if (Math.hypot(dx, dz) > 0.05) {
        const targetYaw = Math.atan2(dx, dz);
        let diff = targetYaw - f.g.rotation.y;
        while (diff > Math.PI) diff -= Math.PI * 2;
        while (diff < -Math.PI) diff += Math.PI * 2;
        f.g.rotation.y += diff * Math.min(1, dt * 14);
      }

      const stride = t * 15 + c.phase;
      f.legs[0].rotation.x = Math.sin(stride) * 0.55;
      f.legs[1].rotation.x = -Math.sin(stride) * 0.55;
      f.g.position.y = 0.08 + Math.abs(Math.cos(stride)) * 0.09;

      if (task.phase === 'carrying') {
        // Both arms raised holding the production folder case
        f.arms[0].rotation.x = -1.15 + Math.sin(stride) * 0.06;
        f.arms[1].rotation.x = -1.15 - Math.sin(stride) * 0.06;
      } else {
        f.arms[0].rotation.x = -Math.sin(stride) * 0.42;
        f.arms[1].rotation.x = Math.sin(stride) * 0.42;
      }
    }

    // Update table delivery pulse rings
    for (let i = this.activePulses.length - 1; i >= 0; i--) {
      const p = this.activePulses[i];
      p.t += dt * 1.8;
      if (p.t >= 1) {
        p.ring.scale.setScalar(1);
        p.ring.material.opacity = 0.25;
        p.ring.material.color.setHex(0x1f7a54);
        this.activePulses.splice(i, 1);
      } else {
        const sc = 1 + p.t * 1.4;
        p.ring.scale.setScalar(sc);
        p.ring.material.color.setHex(p.color);
        p.ring.material.opacity = (1 - p.t) * 0.85;
      }
    }
  }

  moveAlongStep(c, curPos, targetPos, dt, t, speed, carrying) {
    const f = c.fig;
    const dir = targetPos.clone().sub(curPos);
    const dist = dir.length();
    if (dist < 0.05) return;
    dir.normalize();
    curPos.addScaledVector(dir, Math.min(dist, dt * speed));

    const targetYaw = Math.atan2(dir.x, dir.z);
    f.g.rotation.y = targetYaw;
    const stride = t * 13 + c.phase;
    f.legs[0].rotation.x = Math.sin(stride) * 0.45;
    f.legs[1].rotation.x = -Math.sin(stride) * 0.45;
    f.arms[0].rotation.x = carrying ? -1.1 : -Math.sin(stride) * 0.35;
    f.arms[1].rotation.x = carrying ? -1.1 : Math.sin(stride) * 0.35;
  }
}

export function updateStaffAnimations({
  dt,
  t,
  reduced,
  currentFn,
  ownerTodoFn,
  nowFn,
  fmtFn,
  escFn,
}) {
  for (const s of STAFF) {
    const c = currentFn(s);
    const f = s.fig;
    let state = c.job ? 'run' : c.last ? (c.last.status === 'done' ? 'done' : 'bad') : 'idle';
    if (s.id === 'owner' && !c.job && ownerTodoFn().length) state = 'wait';

    if (!reduced) {
      // Natural random eye blinking for every character
      s.blinkTimer -= dt;
      if (s.blinkTimer <= 0) {
        s.blinkTimer = 2.6 + ((s.phase * 1.7) % 2.8);
      }
      const blinkScale = s.blinkTimer < 0.13 ? 0.12 : 1.0;
      for (const eye of f.eyes) {
        eye.scale.y = blinkScale;
      }

      if (state === 'run') {
        // High-energy active task choreography
        if (s.painter) {
          // Painter sweeping stylus across digital canvas
          f.arms[1].rotation.x = -0.95 + Math.sin(t * 11 + s.phase) * 0.28;
          f.arms[1].rotation.z = 0.18 + Math.cos(t * 7 + s.phase) * 0.22;
          f.arms[0].rotation.x = -0.65 + Math.sin(t * 5 + s.phase) * 0.1;
          f.head.rotation.y = Math.cos(t * 5 + s.phase) * 0.18;
          f.head.rotation.x = 0.15;
        } else {
          // Rapid dual-hand typing / operating console
          f.arms[0].rotation.x = -0.92 + Math.sin(t * 15 + s.phase) * 0.26;
          f.arms[1].rotation.x = -0.92 + Math.sin(t * 15 + s.phase + 1.6) * 0.26;
          f.head.rotation.y = Math.sin(t * 3.5 + s.phase) * 0.16;
          f.head.rotation.x = 0.08 + Math.sin(t * 7 + s.phase) * 0.05;
        }
        f.head.position.y = (f.isRobot ? 2.38 : 2.42) + Math.sin(t * 7 + s.phase) * 0.04;
        if (f.isRobot && f.antenna) {
          f.antenna.rotation.y += dt * 8.5;
        }
      } else {
        // Lively continuous studio routine (never frozen!)
        const routineWave = Math.sin(t * 1.8 + s.phase);
        const typingPulse = Math.sin(t * 6.5 + s.phase);
        const isTypingBeat = Math.sin(t * 0.65 + s.phase) > -0.2;

        if (s.painter && isTypingBeat) {
          f.arms[1].rotation.x = -0.78 + Math.sin(t * 5.2 + s.phase) * 0.16;
          f.arms[1].rotation.z = 0.16 + Math.cos(t * 3.8 + s.phase) * 0.14;
          f.arms[0].rotation.x = -0.45;
        } else if (isTypingBeat) {
          f.arms[0].rotation.x = -0.72 + typingPulse * 0.11;
          f.arms[1].rotation.x = -0.72 - typingPulse * 0.11;
        } else {
          f.arms[0].rotation.x = -0.28 + routineWave * 0.08;
          f.arms[1].rotation.x = -0.35 - routineWave * 0.08;
        }

        f.head.rotation.y = Math.sin(t * 1.1 + s.phase) * 0.22;
        f.head.rotation.x = isTypingBeat ? 0.08 : 0.02;
        f.head.position.y = (f.isRobot ? 2.38 : 2.42) + Math.sin(t * 2.2 + s.phase) * 0.022;

        if (f.isRobot && f.antenna) {
          f.antenna.rotation.y += dt * 1.8;
        }
      }

      // Subtle chair swivel & floating creative spark motes
      if (s.chair) {
        s.chair.rotation.y = f.head.rotation.y * 0.45;
      }
      if (s.sparks) {
        const sparkSpeed = state === 'run' ? 1.35 : 0.48;
        for (const sp of s.sparks) {
          const cyc = ((t * sparkSpeed + sp.phase) % 1.6) / 1.6;
          sp.mesh.position.y = 1.25 + cyc * (state === 'run' ? 1.15 : 0.55);
          sp.mesh.rotation.y += dt * 2.5;
          sp.mesh.material.opacity = (1 - cyc) * (state === 'run' ? 0.85 : 0.32);
        }
      }
    }

    // Workstation Lamp & Floor Ring state
    s.lamp.material.emissive.setHex(LAMP_HEX[state] ?? 0x000000);
    s.lamp.material.emissiveIntensity = state === 'run' ? 0.85 + Math.sin(t * 5) * 0.35 : 0.9;
    s.screenMat.emissiveIntensity = state === 'run' ? 0.55 + Math.sin(t * 6 + s.phase) * 0.2 : 0.24;

    s.ring.material.color.setHex(
      state === 'run'
        ? 0xf2a43a
        : state === 'done'
        ? 0x3fbf7f
        : state === 'bad' || state === 'wait'
        ? 0xe0524f
        : 0x9aa3ab
    );
    s.ring.material.opacity = state === 'idle' ? 0.35 : 0.85;

    // Throttled Task Status Bubble DOM update (only mutate DOM when text/second changes!)
    const el = s.bubble.element;
    let nextCls = 'bubble';
    let nextHtml = '';
    if (state === 'run') {
      nextCls = 'bubble run';
      nextHtml = `${escFn(c.job.label)}<span class="t">${fmtFn(nowFn() - c.job.started)}</span>`;
    } else if (state === 'done') {
      nextCls = 'bubble done';
      nextHtml = 'Xong: ' + escFn(c.last.label);
    } else if (state === 'bad') {
      nextCls = 'bubble bad';
      nextHtml = (c.last.status === 'stopped' ? 'Đã dừng: ' : 'Lỗi: ') + escFn(c.last.label);
    } else if (state === 'wait') {
      const n = ownerTodoFn().length;
      nextCls = 'bubble bad';
      nextHtml = `${n} video chờ bạn duyệt`;
    }
    const bubbleKey = `${nextCls}|${nextHtml}`;
    if (s._lastBubbleKey !== bubbleKey) {
      s._lastBubbleKey = bubbleKey;
      el.className = nextCls;
      el.innerHTML = nextHtml;
    }
    s.bubble.visible = state !== 'idle';
  }
}

export function updateRoomPropAnimations(archProps, dt, t, reduced) {
  if (reduced) return;

  // 1. Rotating Terrestrial Globe in Research Lab
  if (archProps.globeMesh) {
    archProps.globeMesh.rotation.y += dt * 0.45;
  }

  // 2. Animated 3D Scout Bar Chart Columns in Research Lab
  for (const b of archProps.scoutBars) {
    const hScale = 0.55 + (Math.sin(t * 2.4 + b.phase) * 0.5 + 0.5) * 0.95;
    b.mesh.scale.y = hScale;
    b.mesh.position.y = -0.8 + hScale * 0.5;
  }

  // 3. Pulsing Digital Cintiq Tablets in Art Studio
  for (const cs of archProps.cintiqScreens) {
    cs.mat.emissiveIntensity = 0.28 + Math.sin(t * 3.2 + cs.index) * 0.14;
  }

  // 4. Vocal Booth "ON AIR" Light & Audio Mixing Console EQ Bars
  if (archProps.onAirMat) {
    archProps.onAirMat.emissiveIntensity = 0.75 + Math.sin(t * 4.0) * 0.35;
  }
  for (const eq of archProps.eqBars) {
    const sc = 0.4 + Math.abs(Math.sin(t * 7.5 + eq.phase)) * 1.4;
    eq.mesh.scale.z = sc;
  }

  // 5. 1440p Render Bay Cooling Fans, Server Blade LEDs & Timeline Playhead
  for (const fan of archProps.renderFans) {
    fan.rotation.y += dt * 9.5;
  }
  for (const led of archProps.serverLeds) {
    led.mat.emissiveIntensity = Math.sin(t * 8 + led.phase) > 0 ? 1.0 : 0.25;
  }
  if (archProps.timelinePlayhead) {
    archProps.timelinePlayhead.position.x = Math.sin(t * 1.1) * 2.3;
  }

  // 6. Publishing Room Satellite Uplink Dish
  if (archProps.uplinkDish) {
    archProps.uplinkDish.rotation.y = Math.sin(t * 0.55) * 0.65;
  }

  // 7. Central Atrium Espresso Machine Rising Steam Puffs & Corridor Flow Pulses
  for (const sp of archProps.steamPuffs) {
    const cycle = ((t * 0.65 + sp.phase) % 1.8) / 1.8;
    sp.mesh.position.y = sp.baseY + cycle * 0.95;
    sp.mesh.scale.setScalar(0.7 + cycle * 0.9);
    sp.mesh.material.opacity = (1 - cycle) * 0.42;
  }
  if (archProps.flowPulses) {
    for (const fp of archProps.flowPulses) {
      const wave = Math.sin(t * 4.2 - fp.index * 0.55);
      fp.mat.emissiveIntensity = wave > 0.35 ? 1.1 : 0.22;
    }
  }
}

export function updateOutdoorAnimations(outdoor, dt, t, reduced) {
  if (reduced) return;

  // 1. Gently swaying tree canopies
  for (const tr of outdoor.trees) {
    tr.crown.rotation.z = Math.sin(t * 1.35 + tr.phase) * 0.035;
    tr.crown.rotation.x = Math.cos(t * 1.1 + tr.phase) * 0.025;
  }

  // 2. Vehicles cruising along South Boulevard with spinning wheels
  for (const v of outdoor.vehicles) {
    v.group.position.x += v.dir * v.speed * dt;
    if (v.dir > 0 && v.group.position.x > 110) v.group.position.x = -110;
    if (v.dir < 0 && v.group.position.x < -110) v.group.position.x = 110;

    for (const w of v.wheels) {
      w.rotation.z -= dt * v.speed * 2.2;
    }
  }

  // 3. Drifting fluffy clouds across the sky
  for (const cl of outdoor.clouds) {
    cl.group.position.x += cl.speed * dt;
    if (cl.group.position.x > 130) cl.group.position.x = -130;
  }

  // 4. Flock of birds soaring & flapping wings
  for (const b of outdoor.birds) {
    const a = t * b.speed + b.angle;
    const nx = b.center.x + Math.cos(a) * b.radius;
    const nz = b.center.z + Math.sin(a * 1.3) * (b.radius * 0.65);
    const dx = -Math.sin(a) * b.radius * b.speed;
    const dz = Math.cos(a * 1.3) * (b.radius * 0.65) * b.speed * 1.3;

    b.group.position.set(nx, b.center.y + Math.sin(t * 1.5 + b.angle) * 0.6, nz);
    b.group.rotation.y = Math.atan2(dx, dz);

    const flap = Math.sin(t * 11 + b.angle * 3) * 0.48;
    b.lw.rotation.z = flap;
    b.rw.rotation.z = -flap;
  }

  // 5. Pond concentric water ripples & swimming Koi fish
  for (const rp of outdoor.ripples) {
    const cyc = ((t * 0.45 + rp.phase) % 2.4) / 2.4;
    const sc = 0.6 + cyc * 3.8;
    rp.mesh.scale.setScalar(sc);
    rp.mat.opacity = (1 - cyc) * 0.42;
  }
  if (outdoor.koiFish) {
    for (const k of outdoor.koiFish) {
      const a = t * k.speed + k.angle;
      const kx = Math.cos(a) * k.rx;
      const kz = Math.sin(a * 1.4) * k.rz;
      const dx = -Math.sin(a) * k.rx * k.speed;
      const dz = Math.cos(a * 1.4) * k.rz * k.speed * 1.4;
      k.group.position.set(kx, 0.21, kz);
      k.group.rotation.y = Math.atan2(dx, dz);
      k.tail.rotation.y = Math.sin(t * 12 + k.angle) * 0.38;
    }
  }

  // 6. Strolling pedestrians along the South Promenade
  if (outdoor.pedestrians) {
    for (const p of outdoor.pedestrians) {
      p.group.position.x += p.dir * p.speed * dt;
      if (p.dir > 0 && p.group.position.x > 68) p.group.position.x = -68;
      if (p.dir < 0 && p.group.position.x < -68) p.group.position.x = 68;
      const st = t * 8.5 + p.phase;
      p.legL.rotation.x = Math.sin(st) * 0.42;
      p.legR.rotation.x = -Math.sin(st) * 0.42;
      p.armL.rotation.x = -Math.sin(st) * 0.32;
      p.armR.rotation.x = Math.sin(st) * 0.32;
    }
  }
}
