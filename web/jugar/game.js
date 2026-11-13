// Browser port of the retro game (simplified arcade run): same world size (264 x 200),
// sprites, physics and themes as retro/*.py. One run = 90 s or 5 hearts; the scenery
// and difficulty change every 10 bananas (the 5 levels of the PC game).

export const WORLD_W = 264, WORLD_H = 200, GROUND_Y = 176;
const SPEED = 120, ACCEL = 900, JUMP_V = -235, GRAVITY = 720, JUMP_BUFFER = 0.2;
export const RUN_TIME = 90, HEARTS = 5, PER_STAGE = 10;

// ---------- sprites (same text grids as retro/sprites.py) ----------
const rgb = (a) => `rgb(${a[0]},${a[1]},${a[2]})`;
const MONKEY_PAL = { k: [46, 24, 12], b: [150, 92, 44], B: [112, 66, 30], f: [240, 200, 150], F: [210, 165, 118], w: [255, 255, 255], e: [22, 16, 16], m: [170, 60, 50] };
const HEAD = ["....kkkkkkkk....", "...kbbbbbbbbk...", ".kkbbbbbbbbbbkk.", "kfkbbffffffbbkfk", "kfkbfwwffwwfbkfk", ".kkfwweffewwfkk.", "...kffffffffk..."];
const HEAD_BLINK = [...HEAD.slice(0, 4), "kfkbffffffffbkfk", ".kkfkkkffkkkfkk.", "...kffffffffk..."];
const BODY = ["...kfffmmfffk...", "....kFffffFk....", "...kkbbbbbbkk...", "..kbbbffffbbbk..", ".kbkbffffffbkbk.", ".kbkbFffffFbkbk.", "..k.kbbbbbbk.k.."];
const LEGS = { idle: ["....kbbkkbbk....", "....kkk..kkk...."], runA: ["....kbbkkbbk....", "...kkk....kk...."], runB: ["....kbbkkbbk....", "....kk....kkk..."] };
const JUMP = [...HEAD.slice(0, 6), "kk.kffffffffk.kk", "kbk.kffmmffk.kbk", ".kbkkFffffFkkbk.", "..kbbbffffbbbk..", "...kbffffffbk...", "...kbFffffFbk...", "...kbbbbbbbbk...", "..kbbk....kbbk..", "..kkk......kkk.."];
const BANANA = ["..........gk", ".........kyk", "........kyYk", "k......kyyYk", "kk....kyyyYk", "khk..kyyyYk.", ".khyyyyyyYk.", "..kkhyyyYk..", "....kkkkk..."];
const BANANA_PAL = { k: [96, 62, 8], y: [255, 222, 64], Y: [226, 166, 28], h: [255, 250, 190], g: [96, 120, 30] };
const GOLD_PAL = { k: [120, 60, 0], y: [255, 186, 40], Y: [226, 120, 10], h: [255, 255, 255], g: [180, 120, 20] };
const COCONUT = ["...kkkk...", ".kkhhcckk.", ".khhcccCk.", "khccdccCCk", "kcccccdcCk", "kcdcccccCk", "kccccCcCCk", ".kcccCCCk.", ".kkCCCCkk.", "...kkkk..."];
const COCONUT_PAL = { k: [40, 22, 10], c: [126, 76, 36], C: [90, 52, 24], h: [176, 120, 64], d: [34, 18, 8] };

function make(grid, pal, tint) {
  const c = document.createElement("canvas");
  c.width = grid[0].length; c.height = grid.length;
  const g = c.getContext("2d");
  grid.forEach((row, y) => [...row].forEach((ch, x) => {
    if (ch === ".") return;
    g.fillStyle = tint || rgb(pal[ch]);
    g.fillRect(x, y, 1, 1);
  }));
  return c;
}
function rotated(src, quarter) {
  const c = document.createElement("canvas");
  c.width = src.height; c.height = src.width;
  const g = c.getContext("2d");
  g.translate(c.width / 2, c.height / 2); g.rotate(quarter * Math.PI / 2);
  g.drawImage(src, -src.width / 2, -src.height / 2);
  return c;
}
let SPR = null;
function sprites() {
  if (SPR) return SPR;
  const coco = make(COCONUT, COCONUT_PAL);
  SPR = {
    idle: make([...HEAD, ...BODY, ...LEGS.idle], MONKEY_PAL),
    blink: make([...HEAD_BLINK, ...BODY, ...LEGS.idle], MONKEY_PAL),
    runA: make([...HEAD, ...BODY, ...LEGS.runA], MONKEY_PAL),
    runB: make([...HEAD, ...BODY, ...LEGS.runB], MONKEY_PAL),
    jump: make(JUMP, MONKEY_PAL),
    hit: make([...HEAD, ...BODY, ...LEGS.idle], MONKEY_PAL, "rgb(255,90,90)"),
    banana: make(BANANA, BANANA_PAL),
    golden: make(BANANA, GOLD_PAL),
    coconut: [0, 1, 2, 3].map((q) => rotated(coco, q)),
  };
  return SPR;
}
export function monkeySprite() { return sprites().idle; }
export function bananaSprite() { return sprites().banana; }

// ---------- themes and stages (retro/levels.py) ----------
const THEMES = [
  { name: "Selva", sky: [[84, 160, 236], [120, 190, 244], [168, 216, 246], [214, 238, 240]], sun: [[255, 242, 170], 214, 38, 12], clouds: [255, 255, 255], far: [76, 150, 112], near: [44, 124, 70], ground: [[116, 192, 64], [72, 140, 42], [132, 86, 46], [98, 60, 30]] },
  { name: "Playa", sky: [[56, 150, 232], [104, 194, 244], [164, 226, 250], [228, 244, 240]], sun: [[255, 250, 204], 54, 34, 14], clouds: [255, 255, 255], far: [40, 136, 206], near: [62, 128, 52], ground: [[246, 222, 152], [224, 190, 120], [236, 206, 136], [212, 176, 110]] },
  { name: "Cañón", sky: [[64, 36, 104], [164, 68, 112], [238, 118, 82], [255, 190, 104]], sun: [[255, 232, 150], 132, 86, 20], clouds: [255, 170, 140], far: [156, 72, 82], near: [112, 46, 52], ground: [[204, 112, 62], [162, 80, 46], [150, 82, 52], [114, 56, 36]] },
  { name: "Noche", sky: [[8, 10, 36], [18, 28, 66], [32, 48, 96], [52, 70, 120]], sun: [[240, 240, 216], 204, 36, 10], clouds: [64, 74, 116], far: [26, 52, 72], near: [16, 42, 44], ground: [[44, 96, 64], [26, 66, 46], [46, 36, 42], [30, 22, 28]] },
  { name: "Volcán", sky: [[38, 10, 22], [88, 20, 26], [160, 50, 30], [222, 102, 42]], sun: null, clouds: [92, 72, 72], far: [62, 30, 36], near: [42, 26, 30], ground: [[76, 58, 58], [52, 38, 42], [46, 30, 32], [30, 20, 22]] },
];
// Slightly easier than the PC levels: first-time players on a phone.
const STAGES = [
  { every: 1.5, speed: 42, coco: null, cocoSpeed: 0, gold: 0.06, bounce: 0 },
  { every: 1.35, speed: 50, coco: 5.5, cocoSpeed: 60, gold: 0.08, bounce: 0 },
  { every: 1.2, speed: 58, coco: 4.5, cocoSpeed: 72, gold: 0.1, bounce: 0.2 },
  { every: 1.05, speed: 66, coco: 3.8, cocoSpeed: 84, gold: 0.12, bounce: 0.35 },
  { every: 0.95, speed: 74, coco: 3.4, cocoSpeed: 92, gold: 0.15, bounce: 0.45 },
];

const rand = (a, b) => a + Math.random() * (b - a);
const hit = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

export class Game {
  constructor(canvas, hooks = {}) {
    this.canvas = canvas;
    this.g = canvas.getContext("2d");
    this.hooks = hooks;           // onScore, onOver, onStage, onHurt
    this.spr = sprites();
    this.clouds = Array.from({ length: 4 }, (_, i) => ({ x: i * 72 + rand(0, 30), y: rand(14, 60), w: rand(18, 30) }));
    this.reset();
    this.state = "idle";
  }

  reset() {
    this.m = { x: WORLD_W / 2, y: GROUND_Y, vx: 0, vy: 0, ground: true, invuln: 0, anim: 0, t: 0, buffer: 0 };
    this.bananas = []; this.rollers = []; this.pops = [];
    this.score = 0; this.caught = 0; this.hearts = HEARTS; this.time = RUN_TIME;
    this.nextBanana = 0.6; this.nextCoco = 3; this.stage = 0; this.t = 0; this.combo = 0;
  }

  start() { this.reset(); this.state = "play"; this.hooks.onStage?.(THEMES[0].name, 0); }

  update(dt, move, jump) {
    this.t += dt;
    for (const c of this.clouds) { c.x -= dt * 4; if (c.x < -40) c.x = WORLD_W + 10; }
    if (this.state !== "play") return;
    const st = STAGES[this.stage];
    this.time -= dt;
    this.updateMonkey(dt, move, jump);

    this.nextBanana -= dt;
    if (this.nextBanana <= 0) {
      this.nextBanana = st.every * rand(0.8, 1.2);
      this.bananas.push({ x: rand(12, WORLD_W - 12), y: -8, v: st.speed * rand(0.9, 1.15), gold: Math.random() < st.gold, ph: rand(0, 6.28) });
    }
    if (st.coco) {
      this.nextCoco -= dt;
      if (this.nextCoco <= 0) {
        this.nextCoco = st.coco * rand(0.85, 1.25);
        const dir = Math.random() < 0.5 ? 1 : -1;
        this.rollers.push({ dir, x: dir === 1 ? -8 : WORLD_W + 8, v: st.cocoSpeed * dir, delay: 0.9, dist: 0, bounce: Math.random() < st.bounce });
      }
    }

    const m = this.m;
    const catchR = { x: m.x - 8, y: m.y - 17, w: 16, h: 12 };
    const hurtR = { x: m.x - 5, y: m.y - 12, w: 10, h: 12 };
    for (const b of this.bananas) {
      b.y += b.v * dt; b.ph += dt * 3;
      const bx = b.x + Math.sin(b.ph) * 2;
      if (!b.done && hit(catchR, { x: bx - 5, y: b.y - 4, w: 10, h: 8 })) {
        b.done = true;
        const pts = b.gold ? 5 : 1;
        this.combo++;
        const bonus = this.combo >= 5 ? 1 : 0;
        this.score += pts + bonus; this.caught++;
        this.pops.push({ x: bx, y: b.y, txt: `+${pts + bonus}`, t: 0.8, gold: b.gold });
        this.hooks.onScore?.(b.gold);
        const stage = Math.min(STAGES.length - 1, Math.floor(this.caught / PER_STAGE));
        if (stage !== this.stage) { this.stage = stage; this.hooks.onStage?.(THEMES[stage].name, stage); }
      } else if (!b.done && b.y > GROUND_Y + 4) { b.done = true; this.combo = 0; }
    }
    this.bananas = this.bananas.filter((b) => !b.done);

    for (const r of this.rollers) {
      if (r.delay > 0) { r.delay -= dt; continue; }
      r.x += r.v * dt; r.dist += Math.abs(r.v * dt);
      r.lift = r.bounce ? Math.round(Math.abs(Math.sin(r.dist / 14)) * 20) : 0;
      if (!r.done && m.invuln <= 0 && hit(hurtR, { x: r.x - 4, y: GROUND_Y - 9 - r.lift, w: 8, h: 8 })) {
        r.done = true; this.hearts--; m.invuln = 1.2; this.combo = 0;
        this.hooks.onHurt?.();
      }
    }
    this.rollers = this.rollers.filter((r) => r.x > -20 && r.x < WORLD_W + 20);
    for (const p of this.pops) { p.t -= dt; p.y -= dt * 18; }
    this.pops = this.pops.filter((p) => p.t > 0);

    if (this.hearts <= 0 || this.time <= 0) {
      this.time = Math.max(0, this.time);
      this.state = "over";
      this.hooks.onOver?.({ score: this.score, caught: this.caught, reason: this.hearts <= 0 ? "hearts" : "time" });
    }
  }

  updateMonkey(dt, move, jump) {
    const m = this.m;
    const target = move * SPEED;
    const step = (move ? ACCEL : ACCEL * 1.6) * dt;
    m.vx += Math.max(-step, Math.min(step, target - m.vx));
    m.x += m.vx * dt;
    if (m.x < 8 || m.x > WORLD_W - 8) { m.x = Math.max(8, Math.min(WORLD_W - 8, m.x)); m.vx = 0; }
    // Gestures arrive a little late, so a jump asked for just before landing still counts.
    m.buffer = jump ? JUMP_BUFFER : Math.max(0, m.buffer - dt);
    if (m.buffer > 0 && m.ground) { m.vy = JUMP_V; m.ground = false; m.buffer = 0; this.hooks.onJump?.(); }
    m.vy += GRAVITY * dt; m.y += m.vy * dt;
    if (m.y >= GROUND_Y) { m.y = GROUND_Y; m.vy = 0; m.ground = true; }
    m.invuln = Math.max(0, m.invuln - dt);
    m.anim += dt * Math.abs(m.vx) / SPEED * 9;
    m.t += dt;
  }

  // ---------- drawing ----------
  draw() {
    const g = this.g, th = THEMES[this.stage];
    g.imageSmoothingEnabled = false;
    // sky in 4 hard bands with a 1-row dither between them (pixel-art gradient)
    const bandH = GROUND_Y / th.sky.length;
    th.sky.forEach((c, i) => { g.fillStyle = rgb(c); g.fillRect(0, Math.floor(i * bandH), WORLD_W, Math.ceil(bandH) + 1); });
    if (th.sun) { const [c, x, y, r] = th.sun; g.fillStyle = rgb(c); this.disc(x, y, r); }
    if (this.stage === 3) { g.fillStyle = "#fff"; for (let i = 0; i < 30; i++) g.fillRect((i * 97) % WORLD_W, (i * 53) % 90, 1, 1); }
    g.fillStyle = rgb(th.clouds);
    for (const c of this.clouds) { g.fillRect(Math.round(c.x), Math.round(c.y), c.w, 4); g.fillRect(Math.round(c.x) + 4, Math.round(c.y) - 3, c.w - 10, 3); }
    // far hills
    g.fillStyle = rgb(th.far);
    for (let x = 0; x < WORLD_W; x += 2) {
      const h = 28 + Math.sin(x / 23 + this.stage) * 10 + Math.sin(x / 9) * 3;
      g.fillRect(x, GROUND_Y - h, 2, h);
    }
    // near bushes / rocks
    g.fillStyle = rgb(th.near);
    for (let x = 0; x < WORLD_W; x += 2) {
      const h = Math.max(0, 10 + Math.sin(x / 13 + 2) * 9 + Math.sin(x / 5) * 2);
      g.fillRect(x, GROUND_Y - h, 2, h);
    }
    const [top, topD, dirt, dirtD] = th.ground;
    g.fillStyle = rgb(dirt); g.fillRect(0, GROUND_Y, WORLD_W, WORLD_H - GROUND_Y);
    g.fillStyle = rgb(dirtD); for (let x = 3; x < WORLD_W; x += 11) g.fillRect(x, GROUND_Y + 8 + (x % 7), 2, 1);
    g.fillStyle = rgb(top); g.fillRect(0, GROUND_Y, WORLD_W, 3);
    g.fillStyle = rgb(topD); g.fillRect(0, GROUND_Y + 3, WORLD_W, 1);

    for (const b of this.bananas) {
      g.drawImage(b.gold ? this.spr.golden : this.spr.banana, Math.round(b.x + Math.sin(b.ph) * 2) - 6, Math.round(b.y) - 5);
    }
    for (const r of this.rollers) {
      if (r.delay > 0) {
        if (Math.floor(this.t * 8) % 2) {
          const x = r.dir === 1 ? 3 : WORLD_W - 12;
          g.fillStyle = r.bounce ? "rgb(255,150,40)" : "rgb(255,84,84)"; g.fillRect(x, GROUND_Y - 20, 9, 11);
          g.fillStyle = "#fff"; g.fillRect(x + 4, GROUND_Y - 18, 1, 5); g.fillRect(x + 4, GROUND_Y - 12, 1, 1);
        }
        continue;
      }
      const f = Math.floor(r.dist / 4) % 4;
      g.drawImage(this.spr.coconut[r.dir === 1 ? f : (4 - f) % 4], Math.round(r.x) - 5, GROUND_Y - 10 - (r.lift || 0));
    }
    // monkey + shadow
    const m = this.m;
    const w = Math.max(6, 14 - Math.floor((GROUND_Y - m.y) / 6));
    g.fillStyle = "rgba(0,0,0,.25)"; g.fillRect(Math.round(m.x) - (w >> 1), GROUND_Y - 1, w, 2);
    let img = !m.ground ? this.spr.jump : Math.abs(m.vx) > 25 ? (Math.floor(m.anim) % 2 ? this.spr.runA : this.spr.runB) : (m.t % 3.2 < 0.12 ? this.spr.blink : this.spr.idle);
    if (m.invuln && Math.floor(m.invuln * 14) % 2) img = this.spr.hit;
    const bob = img === this.spr.runA ? 1 : 0;
    g.drawImage(img, Math.round(m.x) - 8, Math.round(m.y) - 16 - bob);

    g.font = "8px 'Press Start 2P', monospace"; g.textAlign = "center";
    for (const p of this.pops) {
      g.fillStyle = "#000"; g.fillText(p.txt, Math.round(p.x) + 1, Math.round(p.y) + 1);
      g.fillStyle = p.gold ? "#ffba28" : "#fff"; g.fillText(p.txt, Math.round(p.x), Math.round(p.y));
    }
  }

  disc(cx, cy, r) {
    for (let y = -r; y <= r; y++) {
      const hw = Math.round(Math.sqrt(r * r - y * y));
      this.g.fillRect(cx - hw, cy + y, hw * 2, 1);
    }
  }
}
