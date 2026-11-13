// Presentation animations. Everything here is drawing only: the slides read fine without it.
// It reuses the real game (jugar/game.js) and the real gesture network (jugar/models.json).
import { Game } from "./jugar/game.js";
import { normalize, indexFeatures, pinchFeatures, decodeModels, CONNECTIONS } from "./jugar/gestures.js";

window.deckReady = true;
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const ease = (x) => x * x * (3 - 2 * x);
const C = { ink: "#16101f", panel: "#221634", line: "#5a4682", gold: "#ffd63c", leaf: "#6ee66e", sky: "#54a0ec", red: "#ff5a6e", soft: "#d4cbe6", muted: "#a89cc2", skin: "#c98f6a" };

// ---------- pixel sprites ----------
const MONKEY_PAL = { k: "#2e180c", b: "#965c2c", f: "#f0c896", F: "#d2a576", w: "#ffffff", e: "#161010", m: "#aa3c32" };
const MONKEY = ["....kkkkkkkk....", "...kbbbbbbbbk...", ".kkbbbbbbbbbbkk.", "kfkbbffffffbbkfk", "kfkbfwwffwwfbkfk", ".kkfwweffewwfkk.", "...kffffffffk...",
  "...kfffmmfffk...", "....kFffffFk....", "...kkbbbbbbkk...", "..kbbbffffbbbk..", ".kbkbffffffbkbk.", ".kbkbFffffFbkbk.", "..k.kbbbbbbk.k..", "....kbbkkbbk....", "....kkk..kkk...."];
const BANANA_PAL = { k: "#603e08", y: "#ffde40", Y: "#e2a61c", h: "#fffabe", g: "#60781e" };
const BANANA = ["..........gk", ".........kyk", "........kyYk", "k......kyyYk", "kk....kyyyYk", "khk..kyyyYk.", ".khyyyyyyYk.", "..kkhyyyYk..", "....kkkkk..."];
const ICONS = {
  cam: { pal: { k: "#16101f", g: "#a89cc2", w: "#d4cbe6", b: "#54a0ec", s: "#ffffff", r: "#ff5a6e" }, grid: [
    "................", "....kkkkk.......", "...kgggggk......", ".kkkkkkkkkkkkkk.", ".kwwwwwwwwwwwwk.", ".kwwwkkkkkwwrwk.", ".kwwkbbbbbkwwwk.", ".kwkbbsbbbbkwwk.",
    ".kwkbsbbbbbkwwk.", ".kwkbbbbbbbkwwk.", ".kwkbbbbbbbkwwk.", ".kwwkbbbbbkwwwk.", ".kwwwkkkkkwwwwk.", ".kwwwwwwwwwwwwk.", ".kkkkkkkkkkkkkk.", "................"] },
  brain: { pal: { k: "#16101f", p: "#ff9ec4", P: "#d86a98", y: "#ffd63c" }, grid: [
    "................", ".....kkkkkk.....", "...kkppppppkk...", "..kpppPpppPppk..", ".kppPppppppPppk.", ".kpppppPppppppk.", "kppPpppppPpppPpk", "kpppppPppppppppk",
    "kppPpppppppPpppk", ".kpppPpppPppppk.", ".kppppppppppPpk.", "..kkpppPppppkk..", "....kkkkkkkk....", "......kyyk......", ".....kyyyyk.....", "......kkkk......"] },
  pad: { pal: { k: "#16101f", g: "#5a4682", G: "#342452", w: "#d4cbe6", r: "#ff5a6e", y: "#ffd63c" }, grid: [
    "................", "................", "................", "..kkkkkkkkkkkk..", ".kggggggggggggk.", "kggwggggggggyggk", "kgwwwgggggrggygk", "kggwgggggggrgggk",
    "kgggggGGGGgggggk", "kggggkkkkkkggggk", ".kgggk....kgggk.", "..kkk......kkk..", "................", "................", "................", "................"] },
};
function grid2canvas(grid, pal, c = document.createElement("canvas")) {
  c.width = grid[0].length; c.height = grid.length;
  const g = c.getContext("2d");
  grid.forEach((row, y) => [...row].forEach((ch, x) => { if (pal[ch]) { g.fillStyle = pal[ch]; g.fillRect(x, y, 1, 1); } }));
  return c;
}
const monkeyImg = grid2canvas(MONKEY, MONKEY_PAL);
const bananaImg = grid2canvas(BANANA, BANANA_PAL);
$$("canvas.sprite").forEach((c) => grid2canvas(MONKEY, MONKEY_PAL, c));
$$("canvas.icon").forEach((c) => { const ic = ICONS[c.dataset.icon]; grid2canvas(ic.grid, ic.pal, c); });

// ---------- real hands: median hand of each gesture in our recordings (0..100 box) ----------
const POSES = {"TILT_LEFT":[84,90,66,83,52,69,52,52,55,39,45,46,32,30,23,20,16,10,58,41,51,27,55,43,59,54,71,41,66,31,68,48,70,58,84,43,80,34,78,47,78,55],"NEUTRAL":[52,90,40,82,32,69,34,58,43,53,39,48,36,30,35,20,35,10,49,50,47,42,45,56,44,63,59,54,56,50,52,63,52,68,68,60,65,56,61,65,60,69],"TILT_RIGHT":[33,90,26,76,26,59,34,49,43,46,44,42,56,26,66,17,74,10,54,48,56,42,45,53,37,61,61,57,59,54,48,64,40,70,66,68,65,64,56,69,50,74],"OPEN":[37,90,51,84,63,73,72,64,80,60,54,51,61,36,64,27,67,19,45,48,48,30,49,19,50,10,36,51,36,34,36,24,37,15,27,56,23,44,21,36,20,29],"PINCH":[28,90,43,83,55,73,66,66,74,59,47,52,58,44,66,48,71,54,41,47,50,31,57,20,64,12,34,48,38,30,43,19,47,10,27,52,26,38,28,29,30,20]};
const lerpPose = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
const toLm = (p) => Array.from({ length: 21 }, (_, i) => ({ x: p[2 * i] / 100, y: p[2 * i + 1] / 100, z: 0 }));

let models = null;
fetch("jugar/models.json").then((r) => r.json()).then((m) => { models = decodeModels(m); }).catch(() => {});

// forward pass that also returns the hidden activations (for the network drawing)
function run(model, x) {
  const acts = [x];
  for (const L of model.layers) {
    const y = L.b.map((b, i) => { let s = b; const row = L.W[i]; for (let j = 0; j < row.length; j++) s += row[j] * x[j]; return L.relu && s < 0 ? 0 : s; });
    acts.push(y); x = y;
  }
  const m = Math.max(...x), e = x.map((v) => Math.exp(v - m)), sum = e.reduce((a, b) => a + b, 0);
  return { acts, probs: e.map((v) => v / sum) };
}
function classifyPose(hand, pose) {
  if (!models) return null;
  const P = normalize(toLm(pose), 100, 100);
  const feats = hand === "Left" ? indexFeatures(P) : pinchFeatures(P);
  const r = run(models[hand], feats);
  let k = 0; r.probs.forEach((p, i) => { if (p > r.probs[k]) k = i; });
  return { ...r, feats, label: models[hand].classes[k], conf: r.probs[k] };
}

function drawHand(g, pose, W, { color = C.leaf, dot = "#fff", lw = 4, hi = [4, 8], count = 21, skin = false } = {}) {
  const P = (i) => [pose[2 * i] / 100 * W, pose[2 * i + 1] / 100 * W];
  if (skin) {   // a soft "real hand" silhouette for the camera picture
    g.strokeStyle = C.skin; g.fillStyle = C.skin; g.lineCap = "round"; g.lineJoin = "round"; g.lineWidth = W * .075;
    g.beginPath(); [0, 1, 5, 9, 13, 17].forEach((i, k) => { const [x, y] = P(i); k ? g.lineTo(x, y) : g.moveTo(x, y); }); g.closePath(); g.fill(); g.stroke();
    g.beginPath(); for (const [a, b] of CONNECTIONS) { g.moveTo(...P(a)); g.lineTo(...P(b)); } g.stroke();
    return;
  }
  g.strokeStyle = color; g.lineWidth = lw; g.lineCap = "round";
  g.beginPath();
  for (const [a, b] of CONNECTIONS) if (a < count && b < count) { g.moveTo(...P(a)); g.lineTo(...P(b)); }
  g.stroke();
  for (let i = 0; i < count; i++) {
    const [x, y] = P(i), big = hi.includes(i), s = big ? lw * 2.4 : lw * 1.7;
    g.fillStyle = big ? C.gold : dot; g.fillRect(Math.round(x - s / 2), Math.round(y - s / 2), s, s);
  }
}
function gridBg(g, W, H, step = 20) {
  g.fillStyle = C.ink; g.fillRect(0, 0, W, H);
  g.fillStyle = C.panel; for (let i = 0; i < Math.max(W, H); i += step) { g.fillRect(i, 0, 1, H); g.fillRect(0, i, W, 1); }
}

// ---------- slide tracking: entrance animations + only animate the visible slide ----------
const slides = $$(".slide");
slides.forEach((s) => $$("[data-a]", s).forEach((el, i) => el.style.setProperty("--i", i)));
let active = 0;
const enterT = new Array(slides.length).fill(0);
const onEnter = [];
const io = new IntersectionObserver((entries) => {
  for (const e of entries) {
    const i = slides.indexOf(e.target);
    if (e.isIntersecting) {
      active = i; updateNav();
      if (!e.target.classList.contains("in")) { e.target.classList.add("in"); }
      enterT[i] = performance.now();
      onEnter[i]?.();
    }
  }
}, { rootMargin: "-45% 0px -45% 0px", threshold: 0 });
slides.forEach((s) => io.observe(s));

// ---------- 1 cover: the real game playing itself + banana rain ----------
const demo = new Game(document.getElementById("demo"));
demo.start(); demo.hooks.onOver = () => demo.start();
function autopilot(g) {
  const m = g.m; let target = null, best = 1e9;
  for (const b of g.bananas) { const t = (176 - 12 - b.y) / b.v, need = Math.abs(b.x - m.x) / 120; if (t > need - 0.2 && t < best) { best = t; target = b; } }
  const move = target ? (Math.abs(target.x - m.x) < 4 ? 0 : Math.sign(target.x - m.x)) : 0;
  const jump = g.rollers.some((r) => r.delay <= 0 && Math.abs(r.x - m.x) < 26 && Math.sign(m.x - r.x) === Math.sign(r.v));
  return { move, jump };
}
const rain = document.getElementById("rain"), rctx = rain.getContext("2d");
let drops = [];
function sizeRain() {
  rain.width = Math.ceil(rain.clientWidth / 3); rain.height = Math.ceil(rain.clientHeight / 3);
  drops = Array.from({ length: 16 }, () => ({ x: Math.random() * rain.width, y: Math.random() * rain.height, v: 8 + Math.random() * 14, r: Math.random() * 6 }));
}
sizeRain(); addEventListener("resize", sizeRain);
function drawCover(dt, t) {
  const a = autopilot(demo); demo.update(dt, a.move, a.jump); demo.draw();
  rctx.clearRect(0, 0, rain.width, rain.height);
  for (const d of drops) {
    d.y += d.v * dt; if (d.y > rain.height) { d.y = -10; d.x = Math.random() * rain.width; }
    rctx.save(); rctx.translate(Math.round(d.x) + 6, Math.round(d.y) + 4); rctx.rotate(Math.sin(t / 600 + d.r) * .3); rctx.drawImage(bananaImg, -6, -4); rctx.restore();
  }
}

// ---------- 2 idea: the data path lights up step by step ----------
const flow = $$(".flow span");
function drawIdea(dt, t) { const k = Math.floor(t / 700) % (flow.length + 1); flow.forEach((s, i) => s.classList.toggle("on", i === k)); }

// ---------- 3 gestures: hand -> real network -> monkey ----------
const poseCv = Object.fromEntries($$("canvas.pose").map((c) => [c.dataset.pose, c]));
const laneCv = Object.fromEntries($$("canvas.lane").map((c) => [c.dataset.lane, c]));
const outEl = Object.fromEntries($$("[data-out]").map((e) => [e.dataset.out, e]));
const lanes = { tilt: { x: 35, y: 0, vy: 0, prev: "" }, neutral: { x: 35, y: 0, vy: 0 }, pinch: { x: 35, y: 0, vy: 0, prev: "OPEN" } };
const NAMES = { TILT_LEFT: "◀ IZQUIERDA", NEUTRAL: "● QUIETO", TILT_RIGHT: "DERECHA ▶", OPEN: "MANO ABIERTA", PINCH: "¡PINZA! SALTA" };
function gesturePose(kind, t) {
  if (kind === "tilt") { const s = Math.sin(t / 1100); return s < 0 ? lerpPose(POSES.NEUTRAL, POSES.TILT_LEFT, ease(clamp(-s * 1.25))) : lerpPose(POSES.NEUTRAL, POSES.TILT_RIGHT, ease(clamp(s * 1.25))); }
  if (kind === "neutral") { const j = Math.sin(t / 500) * .8; return POSES.NEUTRAL.map((v, i) => v + (i % 2 ? 0 : j)); }
  return lerpPose(POSES.OPEN, POSES.PINCH, ease(clamp(.5 + Math.sin(t / 750) * .9)));
}
function drawLane(kind, label, dt) {
  const c = laneCv[kind], g = c.getContext("2d"), L = lanes[kind];
  g.fillStyle = "#78bef4"; g.fillRect(0, 0, 70, 26);
  g.fillStyle = "#74c040"; g.fillRect(0, 22, 70, 2); g.fillStyle = "#845630"; g.fillRect(0, 24, 70, 2);
  const move = label === "TILT_LEFT" ? -1 : label === "TILT_RIGHT" ? 1 : 0;
  if (kind === "tilt") { L.x = clamp(L.x + move * 30 * dt, 8, 62); }
  if (kind === "pinch" && label === "PINCH" && L.prev !== "PINCH" && L.y === 0) L.vy = -70;
  L.prev = label;
  L.vy += 260 * dt; L.y = Math.min(0, L.y + L.vy * dt); if (L.y === 0) L.vy = 0;
  if (kind === "pinch") g.drawImage(bananaImg, 29, 1);
  g.save(); g.translate(Math.round(L.x), 0); if (move < 0) g.scale(-1, 1);
  g.drawImage(monkeyImg, -8, 6 + Math.round(L.y)); g.restore();
}
function drawGestures(dt, t) {
  for (const kind of ["tilt", "neutral", "pinch"]) {
    const c = poseCv[kind], g = c.getContext("2d"), W = c.width, pose = gesturePose(kind, t);
    gridBg(g, W, W, 21);
    drawHand(g, pose, W, { color: kind === "pinch" ? C.gold : C.leaf, hi: kind === "pinch" ? [4, 8] : [5, 6, 7, 8], lw: 4 });
    const r = classifyPose(kind === "pinch" ? "Right" : "Left", pose);
    const label = r ? r.label : kind === "pinch" ? "OPEN" : "NEUTRAL";
    outEl[kind].textContent = r ? `${NAMES[label]} · ${Math.round(r.conf * 100)} %` : "";
    drawLane(kind, label, dt);
  }
}

// ---------- 4 pipeline: one hand travels through all five steps ----------
const pc = [0, 1, 2, 3, 4].map((i) => document.getElementById("p" + i).getContext("2d"));
const stations = $$(".st");
const PERIOD = 7000;
function pinchAmount(t) {
  const u = (t % PERIOD) / 1000;
  if (u < 1.5) return 0; if (u < 2.3) return ease((u - 1.5) / .8); if (u < 4.8) return 1; if (u < 5.6) return 1 - ease((u - 4.8) / .8); return 0;
}
const vote = { h: ["OPEN", "OPEN", "OPEN"], last: 0, cmd: "OPEN", y: 0, vy: 0, flash: 0 };
function drawPipeline(dt, t) {
  const since = t - enterT[3];
  stations.forEach((s, i) => s.classList.toggle("on", Math.floor(t / 450) % 6 === i));
  const amt = pinchAmount(t), pose = lerpPose(POSES.OPEN, POSES.PINCH, amt);
  const r = classifyPose("Right", pose);
  const P = normalize(toLm(pose), 100, 100), feats = r ? r.feats : pinchFeatures(P);
  const probs = r ? r.probs : [1 - amt, amt];

  // 1 camera picture
  let g = pc[0];
  g.fillStyle = "#2a2036"; g.fillRect(0, 0, 200, 200);
  g.fillStyle = "#3a2e4a"; g.fillRect(0, 140, 200, 60);
  for (let i = 0; i < 60; i++) { g.fillStyle = `rgba(255,255,255,${Math.random() * .06})`; g.fillRect(Math.random() * 200 | 0, Math.random() * 200 | 0, 2, 2); }
  g.save(); g.translate(10, 4); drawHand(g, pose, 180, { skin: true }); g.restore();
  const sy = (t / 8) % 200; g.fillStyle = "rgba(110,230,110,.18)"; g.fillRect(0, sy, 200, 6);
  if (Math.floor(t / 500) % 2) { g.fillStyle = C.red; g.fillRect(10, 10, 10, 10); }
  g.fillStyle = "#fff"; g.font = "10px Silkscreen, monospace"; g.fillText("REC 30 FPS", 26, 19);

  // 2 MediaPipe: the 21 points appear one by one when the slide opens
  g = pc[1]; gridBg(g, 200, 200);
  g.save(); g.translate(10, 4); g.globalAlpha = .25; drawHand(g, pose, 180, { skin: true }); g.globalAlpha = 1;
  const n = reduce ? 21 : clamp(Math.floor((since - 300) / 70), 0, 21);
  drawHand(g, pose, 180, { color: C.leaf, lw: 3, count: n });
  g.restore();
  g.fillStyle = C.gold; g.font = "12px Silkscreen, monospace"; g.fillText(`${n} / 21 PUNTOS`, 10, 192);

  // 3 the 10 numbers (fingertip distances / palm size)
  g = pc[2]; gridBg(g, 200, 200);
  feats.forEach((f, i) => {
    const y = 12 + i * 18, w = clamp(f / 2.2) * 150;
    g.fillStyle = "#120c1a"; g.fillRect(36, y, 150, 12);
    g.fillStyle = i === 0 ? C.gold : C.sky; g.fillRect(36, y, Math.round(w), 12);
    g.fillStyle = C.muted; g.font = "10px Silkscreen, monospace"; g.fillText(String(i + 1).padStart(2, "0"), 10, y + 10);
  });
  g.fillStyle = C.gold; g.font = "10px Silkscreen, monospace"; g.fillText(`PULGAR-INDICE ${feats[0].toFixed(2)}`, 10, 196);

  // 4 the network: real activations, a few neurons per layer
  g = pc[3]; gridBg(g, 200, 200);
  const shown = [10, 10, 8, 2];
  const acts = r ? r.acts : [feats, [], [], probs];
  const xs = [22, 75, 128, 180];
  const pos = shown.map((k, l) => Array.from({ length: k }, (_, i) => [xs[l], 100 + (i - (k - 1) / 2) * (l === 3 ? 60 : 17)]));
  const val = (l, i) => { const a = acts[l]?.[i] ?? 0; return l === 3 ? probs[i] : l === 0 ? clamp(a / 2) : a / (1 + a); };
  g.lineWidth = 1;
  for (let l = 0; l < 3; l++) for (const [ax, ay] of pos[l]) for (const [bx, by] of pos[l + 1]) { g.strokeStyle = "rgba(90,70,130,.45)"; g.beginPath(); g.moveTo(ax, ay); g.lineTo(bx, by); g.stroke(); }
  const ph = (t / 900) % 1;   // signal pulses moving left -> right
  for (let l = 0; l < 3; l++) pos[l].forEach(([ax, ay], i) => {
    const [bx, by] = pos[l + 1][(i * 3 + Math.floor(t / 900)) % pos[l + 1].length];
    const q = (ph + i * .07) % 1; g.fillStyle = C.gold; g.fillRect(ax + (bx - ax) * q - 1.5, ay + (by - ay) * q - 1.5, 3, 3);
  });
  pos.forEach((col, l) => col.forEach(([x, y], i) => {
    const v = clamp(val(l, i)), s = l === 3 ? 16 : 9;
    g.fillStyle = C.ink; g.fillRect(x - s / 2 - 1, y - s / 2 - 1, s + 2, s + 2);
    g.fillStyle = `rgba(110,230,110,${.15 + v * .85})`; if (l === 3) g.fillStyle = i === 1 ? `rgba(255,214,60,${.15 + v * .85})` : `rgba(84,160,236,${.15 + v * .85})`;
    g.fillRect(x - s / 2, y - s / 2, s, s);
  }));
  g.fillStyle = C.muted; g.font = "9px Silkscreen, monospace";
  g.fillText("ENTRADA", 2, 196); g.fillText("OCULTAS", 78, 196); g.fillText("SALIDA", 160, 196);

  // 5 decision: probability, 70 % line, majority vote, and the monkey jumps
  g = pc[4]; gridBg(g, 200, 200);
  const lab = ["ABIERTA", "PINZA"];
  probs.forEach((p, i) => {
    const y = 14 + i * 30;
    g.fillStyle = "#120c1a"; g.fillRect(10, y + 12, 180, 12);
    g.fillStyle = i ? C.gold : C.sky; g.fillRect(10, y + 12, Math.round(180 * p), 12);
    g.fillStyle = "#fff"; g.font = "10px Silkscreen, monospace"; g.fillText(`${lab[i]} ${Math.round(p * 100)}%`, 10, y + 9);
  });
  g.strokeStyle = "#fff"; g.setLineDash([3, 3]); g.beginPath(); g.moveTo(10 + 180 * .7, 20); g.lineTo(10 + 180 * .7, 76); g.stroke(); g.setLineDash([]);
  if (t - vote.last > 160) {   // a new "frame" for the vote
    vote.last = t; vote.h.shift(); vote.h.push(probs[1] >= .7 ? "PINCH" : "OPEN");
    const cmd = vote.h.filter((v) => v === "PINCH").length >= 2 ? "PINCH" : "OPEN";
    if (cmd === "PINCH" && vote.cmd !== "PINCH" && vote.y === 0) { vote.vy = -150; vote.flash = 900; }
    vote.cmd = cmd;
  }
  g.fillStyle = C.muted; g.font = "10px Silkscreen, monospace"; g.fillText("VOTO", 10, 98);
  vote.h.forEach((v, i) => { g.fillStyle = v === "PINCH" ? C.gold : C.line; g.fillRect(52 + i * 22, 86, 16, 16); });
  vote.vy += 420 * dt; vote.y = Math.min(0, vote.y + vote.vy * dt); if (vote.y === 0) vote.vy = 0;
  vote.flash = Math.max(0, vote.flash - dt * 1000);
  g.fillStyle = "#78bef4"; g.fillRect(10, 112, 180, 70); g.fillStyle = "#74c040"; g.fillRect(10, 172, 180, 4); g.fillStyle = "#845630"; g.fillRect(10, 176, 180, 6);
  g.imageSmoothingEnabled = false; g.drawImage(bananaImg, 94, 116, 24, 18);
  g.drawImage(monkeyImg, 84, 140 + Math.round(vote.y), 32, 32);
  if (vote.flash > 0) { g.fillStyle = C.gold; g.font = "12px 'Press Start 2P', monospace"; g.fillText("¡SALTA!", 52, 196); }
  else { g.fillStyle = C.muted; g.font = "10px Silkscreen, monospace"; g.fillText("ESPERANDO PINZA", 40, 194); }
}

// ---------- 5 game screenshots: spotlight one at a time ----------
const figs = $$(".shots figure");
let hot = -1;
function drawShots(dt, t) { const k = Math.floor(t / 2400) % figs.length; if (k !== hot) { hot = k; figs.forEach((f, i) => f.classList.toggle("hot", i === k)); } }

// ---------- 6 results: count up + pixel meters ----------
const fmt = (v, d) => v.toLocaleString("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });
$$(".meter").forEach((m) => { m.innerHTML = "<i></i>".repeat(20); });
function setNums(p) {
  $$("[data-count]").forEach((b) => { const v = +b.dataset.count, d = +b.dataset.dec; b.textContent = fmt(v * p, d) + (b.dataset.suf || ""); });
  $$(".meter").forEach((m) => { const on = Math.round(+m.dataset.fill / 5 * p); [...m.children].forEach((c, i) => c.classList.toggle("f", i < Math.max(1, on))); });
}
onEnter[5] = () => { if (reduce) return setNums(1); const t0 = performance.now(); const step = (now) => { const p = clamp((now - t0 - 400) / 1400); setNums(1 - Math.pow(1 - p, 3)); if (p < 1) requestAnimationFrame(step); }; setNums(0); requestAnimationFrame(step); };
setNums(1);

// ---------- 8 end: banana confetti ----------
const conf = document.getElementById("confetti"), cctx = conf.getContext("2d");
let bits = [];
onEnter[7] = () => {
  if (reduce) return;
  conf.width = Math.ceil(conf.clientWidth / 3); conf.height = Math.ceil(conf.clientHeight / 3);
  bits = Array.from({ length: 46 }, () => ({ x: conf.width * (.3 + Math.random() * .4), y: conf.height * .55, vx: (Math.random() - .5) * 160, vy: -80 - Math.random() * 140, r: Math.random() * 6, vr: (Math.random() - .5) * 8 }));
};
function drawEnd(dt) {
  if (!bits.length) return;
  cctx.clearRect(0, 0, conf.width, conf.height);
  for (const b of bits) { b.vy += 160 * dt; b.x += b.vx * dt; b.y += b.vy * dt; b.r += b.vr * dt; cctx.save(); cctx.translate(b.x, b.y); cctx.rotate(b.r); cctx.drawImage(bananaImg, -6, -4); cctx.restore(); }
  bits = bits.filter((b) => b.y < conf.height + 20);
}

// ---------- main loop: only the slide on screen is animated ----------
const DRAW = { 0: drawCover, 1: drawIdea, 2: drawGestures, 3: drawPipeline, 4: drawShots, 7: drawEnd };
let prev = performance.now();
function frame(now) {
  const dt = Math.min(.05, (now - prev) / 1000); prev = now;
  DRAW[active]?.(dt, now);
  if (!reduce) requestAnimationFrame(frame);
}
if (reduce) {   // one still frame of each, in a clear state
  drawCover(0, 0); drawGestures(0, 1200); enterT[3] = -1e9; drawPipeline(0, 3000);
} else requestAnimationFrame(frame);
document.fonts?.ready.then(() => { if (reduce) { drawPipeline(0, 3000); } });

// ---------- QR codes (rows of each matrix in hex, built into an SVG path) ----------
$$(".qrp").forEach((p) => p.setAttribute("d", p.dataset.hex.split(",").map((hex, y) => {
  const bits = BigInt("0x" + hex).toString(2).padStart(37, "0");
  return [...bits.matchAll(/1+/g)].map((m) => `M${m.index} ${y}h${m[0].length}v1H${m.index}z`).join("");
}).join("")));

// ---------- navigation ----------
const count = document.getElementById("count"), bar = document.getElementById("progress");
function updateNav() { count.textContent = `${active + 1} / ${slides.length}`; bar.style.width = `${(active + 1) / slides.length * 100}%`; }
const go = (i) => slides[clamp(i, 0, slides.length - 1)].scrollIntoView({ behavior: reduce ? "auto" : "smooth" });
document.getElementById("prev").onclick = () => go(active - 1);
document.getElementById("next").onclick = () => go(active + 1);
const fs = document.getElementById("fs");
const toggleFs = () => (document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen?.())?.catch?.(() => {});
fs.onclick = toggleFs;
if (!document.documentElement.requestFullscreen) fs.hidden = true;
addEventListener("keydown", (e) => {
  if (e.target.closest?.("input, textarea")) return;
  if (["ArrowRight", "ArrowDown", "PageDown", " "].includes(e.key)) { e.preventDefault(); go(active + 1); }
  if (["ArrowLeft", "ArrowUp", "PageUp"].includes(e.key)) { e.preventDefault(); go(active - 1); }
  if (e.key === "Home") { e.preventDefault(); go(0); }
  if (e.key === "End") { e.preventDefault(); go(slides.length - 1); }
  if (e.key === "f" || e.key === "F") toggleFs();
});
updateNav();
