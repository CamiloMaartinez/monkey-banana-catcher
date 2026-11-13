// Gesture pipeline for the browser. Same steps as the Python version:
// camera -> MediaPipe HandLandmarker (21 points) -> normalize -> hand features
// -> small MLP (weights exported from models/*_mlp.pt) -> majority vote -> command.

const MP_VERSION = "0.10.14";
const MP_URL = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MP_VERSION}`;
const HAND_MODEL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";

export const SURE = 0.7;          // below this the vote counts the "do nothing" gesture
const MIN_SIDE_SCORE = 0.7;       // two-hand mode: MediaPipe must be this sure about left / right
const IDLE = { Left: "NEUTRAL", Right: "OPEN" };
const MOVE = { TILT_LEFT: -1, NEUTRAL: 0, TILT_RIGHT: 1 };

export const CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12], [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [17, 18], [18, 19], [19, 20], [0, 17],
];

// ---------- same math as gestures/landmarks.py and gestures/features.py ----------

export function normalize(lm, w, h) {
  // pixel proportions, wrist at (0,0,0), divided by wrist -> middle-finger-base distance
  const p = lm.map((q) => [q.x * w, q.y * h, q.z * w]);
  const [wx, wy, wz] = p[0];
  for (const q of p) { q[0] -= wx; q[1] -= wy; q[2] -= wz; }
  const s = Math.hypot(p[9][0], p[9][1]) || 1;
  for (const q of p) { q[0] /= s; q[1] /= s; q[2] /= s; }
  return p;
}

function unit(ax, ay) { const n = Math.hypot(ax, ay) + 1e-6; return [ax / n, ay / n]; }
const d2 = (P, a, b) => Math.hypot(P[a][0] - P[b][0], P[a][1] - P[b][1]);

export function indexFeatures(P) {   // left hand: direction of the index finger (8 numbers)
  const v = (a, b) => unit(P[a][0] - P[b][0], P[a][1] - P[b][1]);
  return [...v(8, 5), ...v(8, 6), ...v(7, 5), ...v(6, 5)];
}

export function pinchFeatures(P) {   // right hand: fingertip distances / palm size (10 numbers)
  const palm = d2(P, 9, 0) + 1e-6;
  const pairs = [[4, 8], [4, 7], [3, 8], [4, 6], [4, 12], [8, 12], [4, 5], [8, 5], [12, 9]];
  const f = pairs.map(([a, b]) => d2(P, a, b) / palm);
  f.push(Math.hypot(P[4][0] - P[8][0], P[4][1] - P[8][1], P[4][2] - P[8][2]) / palm);
  return f;
}

// models.json stores each weight matrix as int8 (base64) + one scale per row: 4x smaller
// than float32 and the same predictions on the recorded data.
export function decodeModels(raw) {
  for (const m of Object.values(raw)) {
    for (const L of m.layers) {
      if (typeof L.W !== "string") continue;
      const [rows, cols] = L.shape, bin = atob(L.W);
      L.W = Array.from({ length: rows }, (_, i) => Float32Array.from({ length: cols }, (_, j) => {
        const v = bin.charCodeAt(i * cols + j);
        return (v > 127 ? v - 256 : v) * L.s[i];
      }));
    }
  }
  return raw;
}

export function forward(model, x) {  // BatchNorm is already folded into the Linear layers
  for (const L of model.layers) {
    const y = new Array(L.b.length);
    for (let i = 0; i < L.b.length; i++) {
      const row = L.W[i];
      let s = L.b[i];
      for (let j = 0; j < row.length; j++) s += row[j] * x[j];
      y[i] = L.relu && s < 0 ? 0 : s;
    }
    x = y;
  }
  const m = Math.max(...x);
  const e = x.map((v) => Math.exp(v - m));
  const sum = e.reduce((a, b) => a + b, 0);
  return e.map((v) => v / sum);
}

export function classify(models, hand, P) {
  const m = models[hand];
  const p = forward(m, hand === "Left" ? indexFeatures(P) : pinchFeatures(P));
  let i = 0;
  for (let k = 1; k < p.length; k++) if (p[k] > p[i]) i = k;
  return { label: m.classes[i], conf: p[i] };
}

class Smoother {   // majority vote over the last `n` frames (one wrong frame cannot change the command)
  constructor(idle, n) { this.idle = idle; this.h = new Array(n).fill(idle); }
  update(label, conf) {
    this.h.shift();
    this.h.push(label && conf >= SURE ? label : this.idle);
    const c = {};
    let best = this.idle, bc = 0;
    for (const l of this.h) { c[l] = (c[l] || 0) + 1; if (c[l] > bc) { bc = c[l]; best = l; } }
    return best;
  }
}

// ---------- live controller ----------

export class GestureController {
  constructor({ preview, onError }) {
    this.preview = preview;          // canvas to show the camera + hand skeleton
    this.onError = onError;
    this.mode = "one";               // "one" = one hand does both; "two" = like the PC game
    this.move = 0;
    this.jumpEvent = false;
    this.labels = { ...IDLE };
    this.raw = {};
    this.fps = 0;
    this.running = false;
    this.smooth = { Left: new Smoother("NEUTRAL", 5), Right: new Smoother("OPEN", 3) };
    this.prevRight = "OPEN";
  }

  // Camera FIRST, right inside the tap: some phones (iOS, in-app browsers) only show the
  // permission prompt when it is asked during the user's gesture, and the player sees the
  // live picture at once instead of "camera off" while the AI downloads (~10 MB).
  async start(onStatus, onCamera) {
    onStatus?.("Pidiendo permiso para la cámara…");
    const cam = navigator.mediaDevices.getUserMedia({
      audio: false, video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
    });
    this.stream = await cam;
    this.video = document.createElement("video");
    this.video.playsInline = true; this.video.muted = true; this.video.autoplay = true;
    this.video.setAttribute("playsinline", ""); this.video.setAttribute("muted", "");
    // iOS Safari plays a camera stream more reliably when the <video> is in the page.
    this.video.style.cssText = "position:fixed;left:0;top:0;width:2px;height:2px;opacity:0;pointer-events:none";
    document.body.appendChild(this.video);
    this.video.srcObject = this.stream;
    await this.video.play().catch(() => {});
    this.work = document.createElement("canvas");   // mirrored frame (selfie view), like cv2.flip in Python
    this.wctx = this.work.getContext("2d");
    this.running = true;
    this.lastVideoTime = -1;
    this.lastTs = 0;
    this.loop();                                     // shows the camera now; hands appear once the AI is ready
    onCamera?.();

    onStatus?.("Cámara lista. Cargando la red neuronal…");
    this.models = decodeModels(await fetch("models.json").then((r) => r.json()));
    onStatus?.("Cámara lista. Cargando MediaPipe (puede tardar unos segundos)…");
    const { FilesetResolver, HandLandmarker } = await import(`${MP_URL}/vision_bundle.mjs`);
    const files = await FilesetResolver.forVisionTasks(`${MP_URL}/wasm`);
    const opts = (delegate) => ({
      baseOptions: { modelAssetPath: HAND_MODEL, delegate },
      runningMode: "VIDEO", numHands: 2,
      minHandDetectionConfidence: 0.5, minHandPresenceConfidence: 0.5, minTrackingConfidence: 0.5,
    });
    let lm;
    try { lm = await HandLandmarker.createFromOptions(files, opts("GPU")); }
    catch { lm = await HandLandmarker.createFromOptions(files, opts("CPU")); }
    if (!this.running) { lm.close(); return; }
    this.landmarker = lm;
  }

  stop() {
    this.running = false;
    this.stream?.getTracks().forEach((t) => t.stop());
    this.video?.remove();
    this.landmarker?.close();
    this.landmarker = null;
  }

  consumeJump() { const j = this.jumpEvent; this.jumpEvent = false; return j; }

  loop = () => {
    if (!this.running) return;
    requestAnimationFrame(this.loop);
    const v = this.video;
    if (v.readyState < 2 || v.currentTime === this.lastVideoTime) return;
    this.lastVideoTime = v.currentTime;
    // Downscale to max 480 px wide: enough for the landmarks, faster on phones.
    const k = Math.min(1, 480 / v.videoWidth);
    const w = Math.round(v.videoWidth * k), h = Math.round(v.videoHeight * k);
    if (this.work.width !== w || this.work.height !== h) { this.work.width = w; this.work.height = h; }
    const c = this.wctx;
    c.setTransform(-1, 0, 0, 1, w, 0);
    c.drawImage(v, 0, 0, w, h);
    c.setTransform(1, 0, 0, 1, 0, 0);
    if (!this.landmarker) { this.draw({ landmarks: [] }, w, h); return; }   // AI still loading: just the picture
    let ts = performance.now();
    if (ts <= this.lastTs) ts = this.lastTs + 1;
    this.lastTs = ts;
    let res;
    try { res = this.landmarker.detectForVideo(this.work, ts); }
    catch (e) { this.onError?.(e); return; }
    this.process(res, w, h);
    const dt = ts - (this.prevTs || ts);
    this.prevTs = ts;
    if (dt > 0) this.fps = this.fps * 0.9 + (1000 / dt) * 0.1;
    this.draw(res, w, h);
  };

  process(res, w, h) {
    const sides = res.handedness || res.handednesses || [];
    const hands = res.landmarks.map((lm, i) => ({ lm, side: sides[i]?.[0]?.categoryName, score: sides[i]?.[0]?.score ?? 0 }));
    this.raw = {};
    let left = null, right = null;
    if (this.mode === "one") {
      // Phone in one hand, the other hand plays: the same hand tilts (move) and pinches (jump).
      const hnd = hands.sort((a, b) => b.score - a.score)[0];
      if (hnd) left = right = normalize(hnd.lm, w, h);
    } else {
      for (const hnd of hands) {
        if (hnd.score < MIN_SIDE_SCORE) continue;
        if (hnd.side === "Left" && !left) left = normalize(hnd.lm, w, h);
        if (hnd.side === "Right" && !right) right = normalize(hnd.lm, w, h);
      }
    }
    if (right) this.raw.Right = classify(this.models, "Right", right);
    if (left) this.raw.Left = classify(this.models, "Left", left);

    const pinching = this.mode === "one" && this.raw.Right?.label === "PINCH";
    // In one-hand mode a pinch bends the index, so we keep the last move while pinching.
    this.labels.Left = pinching
      ? this.smooth.Left.update(this.labels.Left, 1)
      : this.smooth.Left.update(this.raw.Left?.label, this.raw.Left?.conf ?? 0);
    this.labels.Right = this.smooth.Right.update(this.raw.Right?.label, this.raw.Right?.conf ?? 0);
    this.move = MOVE[this.labels.Left];
    if (this.labels.Right === "PINCH" && this.prevRight !== "PINCH") this.jumpEvent = true;  // only a NEW pinch
    this.prevRight = this.labels.Right;
    this.handsSeen = hands.length;
  }

  draw(res, w, h) {
    const cv = this.preview;
    if (!cv) return;
    const W = cv.clientWidth * (window.devicePixelRatio || 1);
    if (!W) return;
    const H = Math.round(W * h / w);
    if (cv.width !== Math.round(W) || cv.height !== H) { cv.width = Math.round(W); cv.height = H; }
    const g = cv.getContext("2d");
    g.drawImage(this.work, 0, 0, cv.width, cv.height);
    g.lineWidth = Math.max(2, cv.width / 160);
    res.landmarks.forEach((lm, i) => {
      const side = (res.handedness || res.handednesses)?.[i]?.[0]?.categoryName;
      const col = this.mode === "one" ? "#ffd63c" : side === "Left" ? "#6ee66e" : "#54a0ec";
      g.strokeStyle = col; g.fillStyle = "#fff";
      g.beginPath();
      for (const [a, b] of CONNECTIONS) {
        g.moveTo(lm[a].x * cv.width, lm[a].y * cv.height);
        g.lineTo(lm[b].x * cv.width, lm[b].y * cv.height);
      }
      g.stroke();
      for (const p of lm) g.fillRect(p.x * cv.width - 2, p.y * cv.height - 2, 4, 4);
    });
  }
}
