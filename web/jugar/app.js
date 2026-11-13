// Glue: explainer page <-> game screen, input (gestures + touch + keyboard), sound, HUD.
import { Game, RUN_TIME } from "./game.js";
import { GestureController } from "./gestures.js";

const $ = (id) => document.getElementById(id);
const BEST_KEY = "mbc-best";
const loadBest = () => { try { return +localStorage.getItem(BEST_KEY) || 0; } catch { return 0; } };
const saveBest = (v) => { try { localStorage.setItem(BEST_KEY, String(v)); } catch { /* private mode */ } };

// ---------- gesture drawings: median hand of each class in the recorded data ----------
const POSES = {"TILT_LEFT":[84,90,66,83,52,69,52,52,55,39,45,46,32,30,23,20,16,10,58,41,51,27,55,43,59,54,71,41,66,31,68,48,70,58,84,43,80,34,78,47,78,55],"NEUTRAL":[52,90,40,82,32,69,34,58,43,53,39,48,36,30,35,20,35,10,49,50,47,42,45,56,44,63,59,54,56,50,52,63,52,68,68,60,65,56,61,65,60,69],"TILT_RIGHT":[33,90,26,76,26,59,34,49,43,46,44,42,56,26,66,17,74,10,54,48,56,42,45,53,37,61,61,57,59,54,48,64,40,70,66,68,65,64,56,69,50,74],"OPEN":[37,90,51,84,63,73,72,64,80,60,54,51,61,36,64,27,67,19,45,48,48,30,49,19,50,10,36,51,36,34,36,24,37,15,27,56,23,44,21,36,20,29],"PINCH":[28,90,43,83,55,73,66,66,74,59,47,52,58,44,66,48,71,54,41,47,50,31,57,20,64,12,34,48,38,30,43,19,47,10,27,52,26,38,28,29,30,20]};
const BONES = [[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[17,18],[18,19],[19,20],[0,17]];
document.querySelectorAll("svg[data-pose]").forEach((svg) => {
  const k = svg.dataset.pose, p = POSES[k], pinch = k === "OPEN" || k === "PINCH";
  const hi = pinch ? [4, 8] : [5, 6, 7, 8];
  const lines = BONES.map(([a, b]) => `<line x1="${p[2 * a]}" y1="${p[2 * a + 1]}" x2="${p[2 * b]}" y2="${p[2 * b + 1]}"/>`).join("");
  const dots = Array.from({ length: 21 }, (_, i) => `<circle cx="${p[2 * i]}" cy="${p[2 * i + 1]}" r="${hi.includes(i) ? 3.2 : 2.2}" fill="${hi.includes(i) ? "#ffd63c" : "#fff"}"/>`).join("");
  svg.innerHTML = `<g stroke="${pinch ? "#54a0ec" : "#6ee66e"}" stroke-width="2.4" stroke-linecap="round">${lines}</g>${dots}`;
});

// ---------- attract mode on the hero: an autopilot monkey ----------
const attract = new Game($("attract"));
attract.start();
attract.hooks.onOver = () => attract.start();
let attractOn = true;

function autopilot(g) {
  const m = g.m;
  let target = null, best = 1e9;
  for (const b of g.bananas) {
    const t = (176 - 12 - b.y) / b.v;                    // time until it reaches the hands
    const need = Math.abs(b.x - m.x) / 120;
    if (t > need - 0.2 && t < best) { best = t; target = b; }
  }
  const move = target ? (Math.abs(target.x - m.x) < 4 ? 0 : Math.sign(target.x - m.x)) : 0;
  const jump = g.rollers.some((r) => r.delay <= 0 && Math.abs(r.x - m.x) < 26 && Math.sign(m.x - r.x) === Math.sign(r.v));
  return { move, jump };
}

// ---------- sound (tiny WebAudio bleeps, no files) ----------
let actx = null;
function beep(freq, dur = 0.08, type = "square", vol = 0.05, slide = 0) {
  if (!actx) return;
  const o = actx.createOscillator(), g = actx.createGain();
  o.type = type; o.frequency.value = freq;
  if (slide) o.frequency.linearRampToValueAtTime(freq + slide, actx.currentTime + dur);
  g.gain.value = vol; g.gain.exponentialRampToValueAtTime(0.0001, actx.currentTime + dur);
  o.connect(g).connect(actx.destination); o.start(); o.stop(actx.currentTime + dur);
}


// Plain-language reason + what to do, for each way the camera can fail on a phone.
const IN_APP = /Instagram|FBAN|FBAV|FB_IAB|TikTok|musical_ly|BytedanceWebview|Line\/|Snapchat/i.test(navigator.userAgent);
const IOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
function cameraError(e, camWorked) {
  if (camWorked) return "La cámara funciona, pero no se pudo descargar la IA (revisa tu conexión a internet). Toca Empezar para reintentar o juega con botones.";
  if (IN_APP || e?.name === "NoCamApi") return `Este navegador no deja usar la cámara (pasa con el lector de QR o el navegador de otras apps). Abre el enlace en ${IOS ? "Safari" : "Chrome"}: toca ⋮ o el ícono de compartir y elige "Abrir en el navegador".`;
  if (e?.name === "NotAllowedError" || e?.name === "SecurityError") return IOS
    ? "El permiso de cámara está bloqueado. En Safari toca \"aA\" en la barra de direcciones → Configuración del sitio web → Cámara → Permitir. Luego toca Empezar otra vez."
    : "El permiso de cámara está bloqueado. Toca el candado junto a la dirección → Permisos → Cámara → Permitir. Luego toca Empezar otra vez.";
  if (e?.name === "NotReadableError" || e?.name === "AbortError") return "Otra app está usando la cámara. Ciérrala y toca Empezar otra vez.";
  if (e?.name === "NotFoundError" || e?.name === "OverconstrainedError") return "No encontramos una cámara frontal en este equipo. Puedes jugar con botones.";
  return "No se pudo abrir la cámara en este navegador. Prueba en Chrome o Safari actualizado, o juega con botones.";
}
if (IN_APP) {
  const s = document.getElementById("status");
  if (s) s.innerHTML = `<span class="err">Para usar la cámara abre esta página en ${IOS ? "Safari" : "Chrome"} (menú ⋮ o compartir → "Abrir en el navegador").</span>`;
}


// ---------- full screen (Android / desktop: Fullscreen API; iPhone has none, so we show a tip) ----------
const rootEl = document.documentElement;
const canFs = !!(rootEl.requestFullscreen || rootEl.webkitRequestFullscreen);
const fsEl = () => document.fullscreenElement || document.webkitFullscreenElement;
function enterFs() {
  if (!canFs || fsEl()) return;
  try { const p = (rootEl.requestFullscreen || rootEl.webkitRequestFullscreen).call(rootEl, { navigationUI: "hide" }); p?.catch?.(() => {}); } catch { /* blocked: keep playing in the page */ }
}
function exitFs() { if (fsEl()) (document.exitFullscreen || document.webkitExitFullscreen)?.call(document)?.catch?.(() => {}); }
const fsBtn = $("fsBtn");
if (!canFs) fsBtn.hidden = true;
fsBtn.addEventListener("click", () => (fsEl() ? exitFs() : enterFs()));
const STANDALONE = matchMedia("(display-mode: standalone)").matches || navigator.standalone;
if (IOS && !canFs && !STANDALONE) $("iosTip").hidden = false;

// ---------- game screen ----------
const play = $("play");
let game = null, gestures = null, mode = "one";
const input = { touch: 0, keys: new Set(), jump: false };

const banner = $("banner");
let bannerTimer = 0;
function showBanner(text, ms = 1600) {
  banner.textContent = text; banner.classList.add("show");
  clearTimeout(bannerTimer); bannerTimer = setTimeout(() => banner.classList.remove("show"), ms);
}

function openGame() {
  enterFs();   // runs inside the tap on "Jugar ahora", which browsers require
  play.classList.add("on");
  document.body.style.overflow = "hidden";
  history.pushState({ play: true }, "", "#jugar");
  attractOn = false;
  if (!game) {
    game = new Game($("screen"), {
      onScore: (gold) => beep(gold ? 1320 : 880, 0.07, "square", 0.04, gold ? 400 : 200),
      onJump: () => beep(330, 0.12, "square", 0.035, 300),
      onHurt: () => { beep(140, 0.25, "sawtooth", 0.06, -80); navigator.vibrate?.(120); },
      onStage: (name, i) => { if (i > 0) { showBanner(`Nivel ${i + 1}: ${name}`); beep(660, 0.25, "triangle", 0.05, 330); } },
      onOver: over,
    });
  }
  $("overOv").classList.remove("on");
  $("startOv").classList.add("on");
  if (!IN_APP) $("status").textContent = "";
}

function closeGame(fromHistory = false) {
  exitFs();
  play.classList.remove("on");
  document.body.style.overflow = "";
  gestures?.stop(); gestures = null;
  $("preview").style.display = "none"; $("camOff").style.display = "";
  $("camOff").textContent = "La cámara se enciende al tocar «Empezar»";
  if (game) game.state = "idle";
  attractOn = true;
  if (!fromHistory && location.hash === "#jugar") history.back();
}
window.addEventListener("popstate", () => { if (play.classList.contains("on")) closeGame(true); });
document.querySelectorAll("[data-play]").forEach((b) => b.addEventListener("click", openGame));
$("closeBtn").addEventListener("click", () => closeGame());
$("exitBtn").addEventListener("click", () => closeGame());
$("againBtn").addEventListener("click", () => { $("overOv").classList.remove("on"); countdown(); });

$("goBtn").addEventListener("click", async () => {
  actx ??= new (window.AudioContext || window.webkitAudioContext)();
  actx.resume?.();
  mode = document.querySelector("input[name=mode]:checked").value;
  const status = $("status");
  const btn = $("goBtn");
  if (mode !== "touch" && !gestures) {
    btn.disabled = true;
    gestures = new GestureController({ preview: $("preview"), onError: (e) => console.warn(e) });
    gestures.mode = mode;
    const showCam = () => { $("preview").style.display = "block"; $("camOff").style.display = "none"; };
    try {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) throw Object.assign(new Error("nocam"), { name: "NoCamApi" });
      await gestures.start((s) => { status.textContent = s; }, showCam);
    } catch (e) {
      console.warn(e);
      const camWorked = !!gestures?.stream;
      gestures?.stop(); gestures = null;
      $("preview").style.display = "none"; $("camOff").style.display = "";
      btn.disabled = false;
      status.innerHTML = `<span class="err">${cameraError(e, camWorked)}</span>`;
      $("camOff").textContent = "Cámara no disponible";
      document.querySelector("input[value=touch]").checked = true;
      return;
    }
    btn.disabled = false;
  } else if (gestures) {
    gestures.mode = mode;
  }
  $("startOv").classList.remove("on");
  countdown();
});

function countdown() {
  game.reset(); game.state = "ready";
  let n = 3;
  const tick = () => {
    if (!play.classList.contains("on")) return;
    if (n === 0) { showBanner("¡YA!", 700); beep(990, 0.2); game.start(); return; }
    showBanner(String(n), 900); beep(520, 0.1); n--; setTimeout(tick, 800);
  };
  showBanner(mode === "touch" ? "Usa los botones" : mode === "one" ? "Índice = mover · Pinza = saltar" : "Izq. mueve · Der. salta", 1400);
  setTimeout(tick, 1400);
}

function over({ score, caught, reason }) {
  const best = loadBest();
  if (score > best) saveBest(score);
  $("overWhy").textContent = reason === "hearts" ? "¡Te quedaste sin corazones!" : "¡Se acabó el tiempo!";
  $("overScore").textContent = score;
  $("overInfo").textContent = `${caught} bananas atrapadas · Récord en este celular: ${Math.max(score, best)}${score > best ? " (¡nuevo!)" : ""}`;
  $("overOv").classList.add("on");
  beep(220, 0.4, "triangle", 0.06, -110);
}

// touch buttons (pointer events: work with fingers and mouse; hold to keep moving)
document.querySelectorAll(".pad button").forEach((b) => {
  const down = (e) => {
    e.preventDefault(); b.classList.add("down"); b.setPointerCapture?.(e.pointerId);
    if (b.dataset.move) input.touch = +b.dataset.move; else input.jump = true;
  };
  const up = () => { b.classList.remove("down"); if (b.dataset.move && input.touch === +b.dataset.move) input.touch = 0; };
  b.addEventListener("pointerdown", down);
  b.addEventListener("pointerup", up); b.addEventListener("pointercancel", up); b.addEventListener("lostpointercapture", up);
  b.addEventListener("contextmenu", (e) => e.preventDefault());
});
const KEYS = { a: -1, arrowleft: -1, d: 1, arrowright: 1 };
addEventListener("keydown", (e) => {
  if (!play.classList.contains("on")) return;
  const k = e.key.toLowerCase();
  if (k in KEYS) { input.keys.add(k); e.preventDefault(); }
  if (k === " " || k === "w" || k === "arrowup") { if (!e.repeat) input.jump = true; e.preventDefault(); }
  if (k === "escape") closeGame();
});
addEventListener("keyup", (e) => input.keys.delete(e.key.toLowerCase()));

// ---------- HUD ----------
const hud = { score: $("hudScore"), bananas: $("hudBananas"), hearts: $("hudHearts"), time: $("hudTime") };
const NAMES = { TILT_LEFT: "◀ IZQUIERDA", NEUTRAL: "● QUIETO", TILT_RIGHT: "DERECHA ▶", OPEN: "MANO ABIERTA", PINCH: "¡PINZA!" };
let last = {};
function setText(el, key, v) { if (last[key] !== v) { last[key] = v; el.textContent = v; } }
function updateHud() {
  setText(hud.score, "s", String(game.score));
  setText(hud.bananas, "b", String(game.caught));
  setText(hud.hearts, "h", "♥".repeat(Math.max(0, game.hearts)) + "♡".repeat(Math.max(0, 5 - game.hearts)));
  setText(hud.time, "t", game.state === "play" ? String(Math.ceil(game.time)) : String(RUN_TIME));
  if (gestures?.running) {
    const L = gestures.raw.Left, R = gestures.raw.Right;
    setText($("valMove"), "vm", L ? NAMES[gestures.labels.Left] : "sin mano");
    setText($("valJump"), "vj", R ? NAMES[gestures.labels.Right] : "sin mano");
    $("barMove").style.width = `${Math.round((L?.conf ?? 0) * 100)}%`;
    $("barJump").style.width = `${Math.round((R?.conf ?? 0) * 100)}%`;
    $("readMove").classList.toggle("active", gestures.move !== 0);
    $("readJump").classList.toggle("active", gestures.labels.Right === "PINCH");
    setText($("fps"), "f", `${Math.round(gestures.fps)} cuadros/s · ${gestures.mode === "one" ? "una mano" : "dos manos"}`);
  } else {
    setText($("valMove"), "vm", "botones"); setText($("valJump"), "vj", "botones");
    setText($("fps"), "f", "");
  }
}

// ---------- main loop ----------
let prev = performance.now();
function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min(0.05, (now - prev) / 1000);
  prev = now;
  if (attractOn) {
    const a = autopilot(attract);
    attract.update(dt, a.move, a.jump);
    attract.draw();
  }
  if (game && play.classList.contains("on")) {
    let move = input.touch;
    for (const k of input.keys) move = KEYS[k];
    if (!move && gestures?.running) move = gestures.move;
    let jump = input.jump; input.jump = false;
    if (gestures?.consumeJump()) jump = true;
    game.update(dt, game.state === "play" ? move : 0, game.state === "play" && jump);
    game.draw();
    updateHud();
  }
}
requestAnimationFrame(frame);

// Respect reduced motion: freeze the hero demo after one frame.
if (matchMedia("(prefers-reduced-motion: reduce)").matches) setTimeout(() => { attractOn = false; }, 300);
// Opened directly with #jugar (e.g. shared link): show the game screen.
if (location.hash === "#jugar") { history.replaceState(null, "", location.pathname); openGame(); }
