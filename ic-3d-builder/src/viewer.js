/* Anatomy-style 3D viewer — no external library (no three.js, no CDN), works offline.
 *
 * Follows the anatomy skill's drawing rules: orthographic (isometric by default) projection,
 * four-tone shading from one key light tied to the camera, painter's order (faces sorted by depth),
 * crease lines and silhouettes as fine ink, numbered balloons with callout columns.
 * Each part is turned into planar faces once (lathes, prisms, rounded boxes, tubes, springs …),
 * then re-projected and re-shaded every frame on a plain Canvas 2D.
 *
 * Interaction:
 *   wheel in   → first explodes the assembly step by step (camera keeps everything framed);
 *                once fully exploded, zooms toward the cursor
 *   wheel out  → zooms back out to the framed view, then re-assembles
 *   drag → orbit · right / shift-drag → pan · click → select · double-click → isolate
 */
'use strict';

const Viewer = (() => {
  const LOOK = {
    body: { color: 0x7d8fa3, metal: 0.55, rough: 0.45 },
    flange: { color: 0x66778a, metal: 0.6, rough: 0.4 },
    bolt: { color: 0x3c4148, metal: 0.7, rough: 0.35 },
    steel: { color: 0xb9c1ca, metal: 0.85, rough: 0.25 },
    trim: { color: 0xc9a227, metal: 0.7, rough: 0.3 },
    seat: { color: 0xe8e2d0, metal: 0.1, rough: 0.6 },
    rubber: { color: 0x2b2d31, metal: 0.0, rough: 0.9 },
    spring: { color: 0x3f8f5f, metal: 0.6, rough: 0.35 },
    bore: { color: 0x15181c, metal: 0.2, rough: 0.8 },
    act: { color: 0x2f6db5, metal: 0.25, rough: 0.5 },
    wheel: { color: 0xc23b2a, metal: 0.2, rough: 0.5 },
    tx: { color: 0xd9dde2, metal: 0.2, rough: 0.55 },
    accent: { color: 0xe0a526, metal: 0.3, rough: 0.5 },
    tube: { color: 0xb8bec6, metal: 0.8, rough: 0.25 },
    cab: { color: 0xd6d6cf, metal: 0.1, rough: 0.7 },
    door: { color: 0xcfd0c8, metal: 0.1, rough: 0.7 },
    cabframe: { color: 0x9a9b95, metal: 0.3, rough: 0.6 },
    plinth: { color: 0x3a3b3d, metal: 0.2, rough: 0.7 },
    plate: { color: 0xe7e3d6, metal: 0.4, rough: 0.5 },
    ghost: { color: 0x9aa5b1, metal: 0, rough: 1, opacity: 0.22 },
    clear: { color: 0x2fae66, metal: 0, rough: 1, opacity: 0.1 },
  };
  /**
   * Realistic finishes (style 'real'): painted castings with an orange-peel bump, machined and
   * polished steel, stainless trim, bronze nuts, PTFE, rubber, painted actuators. Physically based,
   * lit by a studio environment map — the anatomy skill's "materials on the subject, kit tones on the ground".
   */
  const REAL = {
    body: { color: 0x4a525b, metal: 0.2, rough: 0.55, clear: 0.2, bump: 'cast' },
    flange: { color: 0x4a525b, metal: 0.2, rough: 0.5, clear: 0.2, bump: 'cast' },
    bolt: { color: 0x2b2d31, metal: 0.85, rough: 0.38 },
    steel: { color: 0xd3d7dc, metal: 1.0, rough: 0.16, rmap: 'brushed' },
    trim: { color: 0xc7cbcf, metal: 1.0, rough: 0.24, rmap: 'brushed' },
    seat: { color: 0xf1eee6, metal: 0.0, rough: 0.55 },
    rubber: { color: 0x1d1f22, metal: 0.0, rough: 0.92 },
    spring: { color: 0x2d5f45, metal: 0.4, rough: 0.35, clear: 0.6 },
    bore: { color: 0x101215, metal: 0.3, rough: 0.7 },
    act: { color: 0x1d4f9a, metal: 0.1, rough: 0.4, clear: 0.6, bump: 'paint' },
    wheel: { color: 0xa9241c, metal: 0.1, rough: 0.35, clear: 0.6 },
    tx: { color: 0xaeb5bd, metal: 0.25, rough: 0.42, clear: 0.3, bump: 'paint' },
    accent: { color: 0xe3a51c, metal: 0.05, rough: 0.4, clear: 0.4 },
    bronze: { color: 0xb4823e, metal: 1.0, rough: 0.32 },
    tube: { color: 0xd0d4d8, metal: 1.0, rough: 0.2 },
    cab: { color: 0xd5d6d0, metal: 0.05, rough: 0.5, bump: 'paint' },
    door: { color: 0xd2d3cc, metal: 0.05, rough: 0.48, bump: 'paint' },
    cabframe: { color: 0x8c8e8a, metal: 0.2, rough: 0.55 },
    plinth: { color: 0x34363a, metal: 0.1, rough: 0.7 },
    plate: { color: 0xb8bcc1, metal: 0.85, rough: 0.42, rmap: 'brushed' },
    glass: { color: 0x0f1a22, metal: 0.0, rough: 0.05, clear: 1.0 },
    ghost: { color: 0x8a96a3, metal: 0, rough: 1, opacity: 0.14 },
    clear: { color: 0x2fae66, metal: 0, rough: 1, opacity: 0.1 },
  };

  LOOK.bronze = { color: 0xb4823e, metal: 0.7, rough: 0.35 };
  LOOK.glass = { color: 0x1a2630, metal: 0.1, rough: 0.2 };
  LOOK.dial = { color: 0xf4f2ec, metal: 0, rough: 0.6 };
  REAL.dial = { color: 0xf4f2ec, metal: 0, rough: 0.6 };

  // ───────── procedural images (plain canvas, no library) ─────────
  const texCache = new Map();
  function canvasTex(key, w, h, paint) {
    if (texCache.has(key)) return texCache.get(key);
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    paint(c.getContext('2d'), w, h);
    texCache.set(key, c);
    return c;
  }
  function textTex(lines, style, w, h) {
    const key = `txt|${style}|${w}x${h}|${lines.join('¦')}`;
    return canvasTex(key, w, h, (g) => {
      if (style === 'lcd') {
        const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#0d2a2a'); gr.addColorStop(1, '#06171a');
        g.fillStyle = gr; g.fillRect(0, 0, w, h);
        g.fillStyle = '#7dffd6'; g.textAlign = 'center'; g.textBaseline = 'middle';
        lines.forEach((t, i) => { g.font = `${i === 0 ? 700 : 500} ${Math.round(h / (lines.length + 1) * (i === 0 ? 0.95 : 0.6))}px monospace`; g.fillText(t, w / 2, h * (i + 0.75) / (lines.length + 0.5)); });
        return;
      }
      const gr = g.createLinearGradient(0, 0, w, h); gr.addColorStop(0, '#d9dcdf'); gr.addColorStop(0.5, '#b9bdc2'); gr.addColorStop(1, '#cfd2d5');
      g.fillStyle = gr; g.fillRect(0, 0, w, h);
      g.strokeStyle = '#6d7276'; g.lineWidth = Math.max(2, w * 0.008); g.strokeRect(w * 0.03, h * 0.06, w * 0.94, h * 0.88);
      g.fillStyle = '#5f6468';
      for (const [x, y] of [[0.06, 0.15], [0.94, 0.15], [0.06, 0.85], [0.94, 0.85]]) { g.beginPath(); g.arc(w * x, h * y, h * 0.045, 0, 7); g.fill(); }
      g.fillStyle = '#26292c'; g.textBaseline = 'middle';
      lines.forEach((t, i) => {
        const fs = i === 0 ? h * 0.2 : h * 0.13;
        g.font = `${i === 0 ? 700 : 600} ${fs}px Arial, sans-serif`;
        g.fillText(t, w * 0.11, h * (0.27 + i * (0.62 / Math.max(1, lines.length - 1 || 1))));
      });
    });
  }
  const dialTex = () => canvasTex('dial', 256, 256, (g, w) => {
    const c = w / 2;
    g.fillStyle = '#f4f2ec'; g.beginPath(); g.arc(c, c, c, 0, 7); g.fill();
    g.strokeStyle = '#222';
    for (let i = 0; i <= 40; i++) {
      const a = Math.PI * 0.75 + i / 40 * Math.PI * 1.5; const r0 = i % 5 ? c * 0.78 : c * 0.7;
      g.lineWidth = i % 5 ? 2 : 4; g.beginPath(); g.moveTo(c + Math.cos(a) * r0, c + Math.sin(a) * r0); g.lineTo(c + Math.cos(a) * c * 0.88, c + Math.sin(a) * c * 0.88); g.stroke();
    }
    g.strokeStyle = '#c0281e'; g.lineWidth = 3; g.beginPath(); g.arc(c, c, c * 0.62, Math.PI * 1.9, Math.PI * 2.25); g.stroke();
    g.strokeStyle = '#111'; g.lineWidth = 6; g.beginPath(); g.moveTo(c, c); g.lineTo(c + Math.cos(Math.PI * 1.55) * c * 0.72, c + Math.sin(Math.PI * 1.55) * c * 0.72); g.stroke();
    g.fillStyle = '#111'; g.beginPath(); g.arc(c, c, c * 0.07, 0, 7); g.fill();
    g.font = `600 ${w * 0.08}px Arial`; g.textAlign = 'center'; g.fillText('bar', c, c * 1.45);
  });
  const haloTex = () => canvasTex('halo', 256, 256, (g, w) => {
    const gr = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2);
    gr.addColorStop(0, 'rgba(0,0,0,0.42)'); gr.addColorStop(0.45, 'rgba(0,0,0,0.16)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gr; g.fillRect(0, 0, w, w);
  });

  /** cutaway section removes the front half (z > 0) of shells / housings (these looks and part ids) */
  const CUT_LOOKS = new Set(['body', 'flange', 'act', 'cab', 'door', 'cabframe', 'plinth', 'ghost']);
  const CUT_IDS = new Set(['cage', 'guide', 'liner', 'bonnet', 'gland', 'packing', 'body_connector', 'mounting_pad', 'thrust_base', 'lower_casing', 'upper_casing', 'gearcase']);
  const REF = new Set(['ghost', 'clear']);

  // ───────── small vector / matrix kit ─────────
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const mul = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const unit = (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
  const I3 = [1, 0, 0, 0, 1, 0, 0, 0, 1];
  const rotX = (a) => { const c = Math.cos(a); const s = Math.sin(a); return [1, 0, 0, 0, c, -s, 0, s, c]; };
  const rotY = (a) => { const c = Math.cos(a); const s = Math.sin(a); return [c, 0, s, 0, 1, 0, -s, 0, c]; };
  const rotZ = (a) => { const c = Math.cos(a); const s = Math.sin(a); return [c, -s, 0, s, c, 0, 0, 0, 1]; };
  const mm = (A, B) => { const o = []; for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) o.push(A[r * 3] * B[c] + A[r * 3 + 1] * B[3 + c] + A[r * 3 + 2] * B[6 + c]); return o; };
  const mv = (M, v) => [M[0] * v[0] + M[1] * v[1] + M[2] * v[2], M[3] * v[0] + M[4] * v[1] + M[5] * v[2], M[6] * v[0] + M[7] * v[1] + M[8] * v[2]];
  const axisM = (axis) => axis === 'x' ? rotZ(-Math.PI / 2) : axis === 'z' ? rotX(Math.PI / 2) : I3;
  const FACE_M = { z: I3, '-z': rotY(Math.PI), x: rotY(Math.PI / 2), '-x': rotY(-Math.PI / 2), y: rotX(-Math.PI / 2) };
  /** rotation taking +Y onto unit vector d */
  function fromY(d) {
    const y = [0, 1, 0]; const c = dot(y, d);
    if (c > 0.99999) return I3;
    if (c < -0.99999) return rotX(Math.PI);
    const k = unit(cross(y, d)); const s = Math.sqrt(1 - c * c); const t = 1 - c;
    const [x, yy, z] = k;
    return [t * x * x + c, t * x * yy - s * z, t * x * z + s * yy, t * x * yy + s * z, t * yy * yy + c, t * yy * z - s * x, t * x * z - s * yy, t * yy * z + s * x, t * z * z + c];
  }

  // ───────── solids → faces ─────────
  // A face: { p: [[x,y,z]…], n: [x,y,z], look, cr: [bool per edge] (crease lines), sil: [[edge, neighbourNormal]…],
  //           tex: {img, tl, tr, bl}, round: true (no crease on its rim) }
  /** profile [[s, r, smooth?]…] around local +Y; creases at every knot not marked smooth */
  function latheFaces(prof, look, M, at, seg = 48) {
    let pts = prof.map((p) => [p[0], Math.max(0, p[1]), p[2]]);
    if (pts[pts.length - 1][0] < pts[0][0]) pts = pts.slice().reverse();
    const out = []; const n = pts.length;
    const ang = (j) => (j % seg) / seg * Math.PI * 2;
    const V = (i, j) => { const a = ang(j); return add(mv(M, [pts[i][1] * Math.sin(a), pts[i][0], pts[i][1] * Math.cos(a)]), at); };
    const crease = (i) => i === 0 || i === n - 1 || !pts[i][2];
    for (let i = 0; i < n - 1; i++) {
      const dr = pts[i + 1][1] - pts[i][1]; const ds = pts[i + 1][0] - pts[i][0];
      if (Math.abs(dr) < 1e-6 && Math.abs(ds) < 1e-6) continue;
      if (pts[i][1] < 1e-6 && pts[i + 1][1] < 1e-6) continue;
      const nl = Math.hypot(dr, ds); const nr = ds / nl; const ns = -dr / nl;
      const N = (j) => { const a = ang(j + 0.5); return unit(mv(M, [nr * Math.sin(a), ns, nr * Math.cos(a)])); };
      for (let j = 0; j < seg; j++) {
        const f = { p: [V(i, j), V(i, j + 1), V(i + 1, j + 1), V(i + 1, j)], n: N(j), look,
          cr: [crease(i), false, crease(i + 1), false] };
        f.sil = [[1, N(j + 1)], [3, N(j - 1 + seg)]];
        out.push(f);
      }
    }
    return out;
  }
  function boxFaces(s, look, M, at) {
    const [w, h, d] = s.map((v) => Math.max(0.1, v) / 2);
    const P = (x, y, z) => add(mv(M, [x * w, y * h, z * d]), at);
    const q = (a, b, c, e, n) => ({ p: [a, b, c, e], n: unit(mv(M, n)), look, cr: [true, true, true, true] });
    return [
      q(P(-1, -1, 1), P(1, -1, 1), P(1, 1, 1), P(-1, 1, 1), [0, 0, 1]), q(P(1, -1, -1), P(-1, -1, -1), P(-1, 1, -1), P(1, 1, -1), [0, 0, -1]),
      q(P(1, -1, 1), P(1, -1, -1), P(1, 1, -1), P(1, 1, 1), [1, 0, 0]), q(P(-1, -1, -1), P(-1, -1, 1), P(-1, 1, 1), P(-1, 1, -1), [-1, 0, 0]),
      q(P(-1, 1, 1), P(1, 1, 1), P(1, 1, -1), P(-1, 1, -1), [0, 1, 0]), q(P(-1, -1, -1), P(1, -1, -1), P(1, -1, 1), P(-1, -1, 1), [0, -1, 0]),
    ];
  }
  /** rounded rectangle (x-y) extruded along z with a chamfered rim */
  function rboxFaces(s, r, look, M, at) {
    const bev = Math.max(0, Math.min(r * 0.5, s[2] / 2 - 0.05, s[0] / 2 - 0.05, s[1] / 2 - 0.05, 3));
    const ring = (inset) => {
      const w = s[0] / 2 - inset; const h = s[1] / 2 - inset; const cr = Math.max(0.01, Math.min(r - inset * 0.5, w - 0.01, h - 0.01));
      const pts = []; const st = 5;
      for (const [cx, cy, a0] of [[w - cr, h - cr, 0], [-w + cr, h - cr, 90], [-w + cr, -h + cr, 180], [w - cr, -h + cr, 270]]) {
        for (let k = 0; k <= st; k++) { const a = (a0 + k * 90 / st) * Math.PI / 180; pts.push([cx + cr * Math.cos(a), cy + cr * Math.sin(a)]); }
      }
      return pts;
    };
    const z1 = s[2] / 2; const rings = bev > 0.05 ? [[ring(bev), -z1], [ring(0), -z1 + bev], [ring(0), z1 - bev], [ring(bev), z1]] : [[ring(0), -z1], [ring(0), z1]];
    const P = (xy, z) => add(mv(M, [xy[0], xy[1], z]), at);
    const out = [];
    for (let k = 0; k < rings.length - 1; k++) {
      const [A, za] = rings[k]; const [B, zb] = rings[k + 1]; const m = A.length;
      const mid = rings.length === 4 && k === 1;
      for (let i = 0; i < m; i++) {
        const i2 = (i + 1) % m;
        const e = [B[i2][0] - B[i][0], B[i2][1] - B[i][1]];
        let nl = [e[1], -e[0], 0];
        if (!mid) { const t = sub([B[i][0], B[i][1], zb], [A[i][0], A[i][1], za]); nl = cross([e[0], e[1], 0], t); if (dot(nl, [A[i][0], A[i][1], 0]) < 0) nl = mul(nl, -1); }
        const flat = (i % 6 === 5);   // straight run between corner arcs
        out.push({ p: [P(A[i], za), P(A[i2], za), P(B[i2], zb), P(B[i], zb)], n: unit(mv(M, unit(nl))), look,
          cr: [true, flat ? false : false, true, false], sil: [] });
      }
    }
    const cap = (R, z, sgn) => ({ p: (sgn > 0 ? R : R.slice().reverse()).map((xy) => P(xy, z)), n: unit(mv(M, [0, 0, sgn])), look, cr: null, round: true });
    out.push(cap(rings[0][0], -z1, -1), cap(rings[rings.length - 1][0], z1, 1));
    return out;
  }
  function sphFaces(r, scale, look, at) {
    const sc = scale || [1, 1, 1]; const out = []; const U = 28; const W = 16;
    const P = (i, j) => { const th = i / U * Math.PI * 2; const ph = j / W * Math.PI; return [Math.sin(ph) * Math.sin(th), Math.cos(ph), Math.sin(ph) * Math.cos(th)]; };
    for (let j = 0; j < W; j++) for (let i = 0; i < U; i++) {
      const u = [P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)];
      const c = unit(u.reduce((a, b) => add(a, b), [0, 0, 0]));
      out.push({ p: u.map((v) => add([v[0] * r * sc[0], v[1] * r * sc[1], v[2] * r * sc[2]], at)), n: unit([c[0] / sc[0], c[1] / sc[1], c[2] / sc[2]]), look, cr: null, round: true });
    }
    return out;
  }
  /** tube along a polyline of centre points */
  function sweepFaces(path, rad, look, sides = 10, caps = true) {
    const out = []; const rings = [];
    let prevN = null;
    for (let i = 0; i < path.length; i++) {
      const T = unit(sub(path[Math.min(path.length - 1, i + 1)], path[Math.max(0, i - 1)]));
      let N = prevN ? unit(sub(prevN, mul(T, dot(prevN, T)))) : unit(Math.abs(T[1]) < 0.9 ? cross(T, [0, 1, 0]) : cross(T, [1, 0, 0]));
      prevN = N; const B = cross(T, N);
      const ring = [];
      for (let k = 0; k < sides; k++) { const a = k / sides * Math.PI * 2; const d = add(mul(N, Math.cos(a)), mul(B, Math.sin(a))); ring.push([add(path[i], mul(d, rad)), d]); }
      rings.push(ring);
    }
    for (let i = 0; i < rings.length - 1; i++) for (let k = 0; k < sides; k++) {
      const k2 = (k + 1) % sides; const A = rings[i]; const B = rings[i + 1];
      out.push({ p: [A[k][0], A[k2][0], B[k2][0], B[k][0]], n: unit(add(A[k][1], A[k2][1])), look, cr: null, round: true,
        sil: [[1, unit(add(A[k2][1], A[(k2 + 1) % sides][1]))], [3, unit(add(A[k][1], A[(k - 1 + sides) % sides][1]))]] });
    }
    if (caps) {
      const T0 = unit(sub(path[0], path[1])); const T1 = unit(sub(path[path.length - 1], path[path.length - 2]));
      out.push({ p: rings[0].map((v) => v[0]).reverse(), n: T0, look, cr: rings[0].map(() => true) });
      out.push({ p: rings[rings.length - 1].map((v) => v[0]), n: T1, look, cr: rings[0].map(() => true) });
    }
    return out;
  }
  function torFaces(R, r, look, M, at) {
    const out = []; const U = 40; const V = 12;
    const P = (i, j) => { const u = i / U * Math.PI * 2; const v = j / V * Math.PI * 2; return [(R + r * Math.cos(v)) * Math.cos(u), (R + r * Math.cos(v)) * Math.sin(u), r * Math.sin(v)]; };
    const Nn = (i, j) => { const u = i / U * Math.PI * 2; const v = j / V * Math.PI * 2; return [Math.cos(v) * Math.cos(u), Math.cos(v) * Math.sin(u), Math.sin(v)]; };
    for (let i = 0; i < U; i++) for (let j = 0; j < V; j++) {
      out.push({ p: [P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)].map((v) => add(mv(M, v), at)), n: unit(mv(M, Nn(i + 0.5, j + 0.5))), look, cr: null, round: true });
    }
    return out;
  }

  function primFaces(pr, look) {
    const at = pr.at || [0, 0, 0];
    switch (pr.k) {
      case 'lathe': return latheFaces(pr.pts, look, axisM(pr.axis), at, 48);
      case 'cyl': {
        const hh = Math.max(0.1, pr.h) / 2; const seg = pr.seg || 40;
        let M = axisM(pr.axis); if (pr.rotY) M = mm(rotY(pr.rotY), M);
        const f = latheFaces([[-hh, 0], [-hh, pr.r], [hh, pr.r2 ?? pr.r], [hh, 0]], look, M, at, seg);
        if (seg <= 8) for (const x of f) { x.cr = [true, true, true, true]; x.sil = []; }
        return f;
      }
      case 'ring': { const hh = Math.max(0.1, pr.h) / 2; return latheFaces([[-hh, pr.ri], [-hh, pr.ro], [hh, pr.ro], [hh, pr.ri], [-hh, pr.ri]], look, axisM(pr.axis), at, 40); }
      case 'box': return boxFaces(pr.s, look, pr.ry ? rotY(pr.ry) : I3, at);
      case 'rbox': return rboxFaces(pr.s, pr.r ?? 4, look, pr.ry ? rotY(pr.ry) : I3, at);
      case 'sph': return sphFaces(pr.r, pr.scale, look, at);
      case 'tor': return torFaces(pr.R, pr.r, look, pr.axis === 'y' ? rotX(Math.PI / 2) : pr.axis === 'x' ? rotY(Math.PI / 2) : I3, at);
      case 'helix': {
        const M = axisM(pr.axis); const n = Math.max(24, Math.round(pr.turns * 24)); const path = [];
        for (let i = 0; i <= n; i++) { const t = i / n; const a = t * pr.turns * Math.PI * 2; path.push(add(mv(M, [pr.R * Math.cos(a), (t - 0.5) * pr.h, pr.R * Math.sin(a)]), at)); }
        return sweepFaces(path, pr.r, look, 8, true);
      }
      case 'tube': {
        const a = pr.a; const b = pr.b; const len = Math.hypot(...sub(b, a));
        if (len < 1e-6) return [];
        const hh = len / 2;
        return latheFaces([[-hh, 0], [-hh, pr.r], [hh, pr.r], [hh, 0]], look, fromY(unit(sub(b, a))), mul(add(a, b), 0.5), 16);
      }
      case 'plate': {
        const [w, h, t] = pr.s; const M = FACE_M[pr.face || 'z'];
        const f = boxFaces([w, h, Math.max(0.2, t)], look, M, at);
        const z = Math.max(0.2, t) / 2; const P = (x, y) => add(mv(M, [x, y, z]), at);
        f[0].tex = { img: textTex(pr.lines || [], pr.style || 'plate', 512, Math.max(64, Math.round(512 * h / w))), tl: P(-w / 2, h / 2), tr: P(w / 2, h / 2), bl: P(-w / 2, -h / 2) };
        f[0].look = pr.style === 'lcd' ? 'glass' : 'plate';
        return f;
      }
      case 'gauge': {
        const r = pr.r; let M = axisM(pr.axis); if (pr.flip) M = mm(M, rotX(Math.PI));
        const f = latheFaces([[-r * 0.25, 0], [-r * 0.25, r], [r * 0.25, r, 1], [r * 0.25, r * 0.92], [r * 0.25, 0]], 'steel', M, at, 40);
        const R = r * 0.86; const y = r * 0.252; const P = (x, z) => add(mv(M, [x, y, z]), at);
        const circ = []; for (let i = 0; i < 40; i++) { const a = i / 40 * Math.PI * 2; circ.push(P(R * Math.sin(a), R * Math.cos(a))); }
        f.push({ p: circ, n: unit(mv(M, [0, 1, 0])), look: 'dial', cr: null, round: true, tex: { img: dialTex(), tl: P(-R, -R), tr: P(R, -R), bl: P(-R, R) } });
        return f;
      }
      case 'arrow': {
        const L = pr.len; const W = pr.w; let M = FACE_M[pr.face || 'z']; if (pr.dir < 0) M = mm(M, rotZ(Math.PI));
        const sh = [[-L / 2, -W * 0.22], [L * 0.18, -W * 0.22], [L * 0.18, -W / 2], [L / 2, 0], [L * 0.18, W / 2], [L * 0.18, W * 0.22], [-L / 2, W * 0.22]];
        const P = (xy, z) => add(mv(M, [xy[0], xy[1], z]), at); const out = []; const t = pr.t;
        // two convex pieces for the caps: shaft and head
        const shaft = [sh[0], sh[1], sh[5], sh[6]]; const head = [sh[2], sh[3], sh[4]];
        for (const poly of [shaft, head]) out.push({ p: poly.map((v) => P(v, t)), n: unit(mv(M, [0, 0, 1])), look, cr: poly.map(() => true) });
        for (let i = 0; i < sh.length; i++) {
          const a = sh[i]; const b = sh[(i + 1) % sh.length]; const e = [b[0] - a[0], b[1] - a[1]];
          out.push({ p: [P(a, 0), P(b, 0), P(b, t), P(a, t)], n: unit(mv(M, unit([e[1], -e[0], 0]))), look, cr: [true, true, true, true] });
        }
        return out;
      }
      default: return [];
    }
  }

  // ───────── state ─────────
  let host; let canvas; let ctx; let overlay; let dpr = 1;
  const opts = { edges: false, labels: 'auto', dims: false, section: false, autoExplode: true, insetRight: 0, style: 'real' };
  const S = { parts: [], groups: new Map(), bbox: null, e: 0, eT: 0, focus: null, hovered: null, selected: null };
  const ISO_PHI = Math.acos(1 / Math.sqrt(3));
  const orbit = { theta: Math.PI / 4, phi: ISO_PHI, dist: 3000, target: [0, 0, 0] };
  const goal = { dist: 3000, target: [0, 0, 0], follow: true, refit: true, fitDist: 3000 };
  let cb = { onHover() {}, onPick() {}, onExplode() {}, onFocus() {} };
  let dirty = true; let drawn = [];
  const balloons = new Map();
  const cam = { d: [0, 0, 1], right: [1, 0, 0], up: [0, 1, 0], k: 1, W: 600, H: 400, L: [0, 0, 1] };

  function init(el, callbacks = {}) {
    host = el; cb = { ...cb, ...callbacks };
    canvas = document.createElement('canvas'); canvas.className = 'anat-canvas';
    canvas.style.width = '100%'; canvas.style.height = '100%';
    ctx = canvas.getContext('2d');
    el.appendChild(canvas);
    overlay = document.createElement('div'); overlay.className = 'v-overlay'; el.appendChild(overlay);
    applyStyle();
    bindInput(canvas);
    if (typeof ResizeObserver !== 'undefined') new ResizeObserver(() => { resize(); goal.refit = true; }).observe(el);
    resize();
    loop();
  }
  function applyStyle() { host.classList.toggle('real', opts.style === 'real'); dirty = true; }
  function resize() {
    dpr = Math.min(2, window.devicePixelRatio || 1);
    cam.W = host.clientWidth || 600; cam.H = host.clientHeight || 400;
    canvas.width = Math.round(cam.W * dpr); canvas.height = Math.round(cam.H * dpr);
    updateCamera();
  }
  function updateCamera() {
    const { theta, phi } = orbit;
    cam.d = [Math.sin(phi) * Math.sin(theta), Math.cos(phi), Math.sin(phi) * Math.cos(theta)];
    let r = cross([0, 1, 0], cam.d); if (Math.hypot(...r) < 1e-6) r = [Math.cos(theta), 0, -Math.sin(theta)];
    cam.right = unit(r); cam.up = unit(cross(cam.d, cam.right));
    cam.k = (cam.H || 400) / orbit.dist;
    cam.L = unit(add(add(mul(cam.right, -0.42), mul(cam.up, 0.78)), mul(cam.d, 0.62)));   // key light: upper left, toward the viewer
    dirty = true;
  }
  /** world → canvas pixels (orthographic, anatomy-style) and depth (larger = nearer) */
  function proj(p) {
    const q = sub(p, orbit.target);
    return [(cam.W / 2 + dot(q, cam.right) * cam.k) * dpr, (cam.H / 2 - dot(q, cam.up) * cam.k) * dpr, dot(q, cam.d)];
  }
  let bgCss = '#e9edf1';
  function setBackground(css) { bgCss = css || bgCss; dirty = true; }

  // ───────── model ─────────
  const isCut = (p) => opts.section && (CUT_LOOKS.has(p.look) || CUT_IDS.has(p.id));
  function clipZ(f) {
    // keep z ≤ 0 (the cutaway removes the front half)
    const out = []; const P = f.p; const n = P.length;
    for (let i = 0; i < n; i++) {
      const a = P[i]; const b = P[(i + 1) % n]; const ia = a[2] <= 0; const ib = b[2] <= 0;
      if (ia) out.push(a);
      if (ia !== ib) { const t = a[2] / (a[2] - b[2]); out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, 0]); }
    }
    if (out.length < 3) return null;
    return { ...f, p: out, cr: null, sil: null, tex: out.length === n ? f.tex : null, two: true };
  }
  function clear() { S.groups.clear(); clearBalloons(); }
  function show(model, { keepView = false } = {}) {
    clear();
    S.parts = model.parts; S.bbox = model.bbox;
    if (S.focus && !model.parts.some((p) => p.id === S.focus)) S.focus = null;
    for (const p of model.parts) {
      let faces = [];
      for (const pr of p.prims) faces.push(...primFaces(pr, pr.look || p.look));
      if (isCut(p)) faces = faces.map(clipZ).filter(Boolean);
      const bb = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
      for (const f of faces) for (const v of f.p) for (let i = 0; i < 3; i++) { bb.min[i] = Math.min(bb.min[i], v[i]); bb.max[i] = Math.max(bb.max[i], v[i]); }
      S.groups.set(p.id, { part: p, faces, bb, visible: true, off: [0, 0, 0] });
      if (!REF.has(p.look)) makeBalloon(p);
    }
    applyExplode();
    if (!keepView) { goal.follow = true; frame(true); } else if (goal.follow) goal.refit = true;
    dirty = true;
  }

  // ───────── explode ─────────
  const smooth = (x) => x * x * (3 - 2 * x);
  /** stage 0 parts move first, stage 2 (internals) last */
  const stageK = (e, stage) => smooth(Math.max(0, Math.min(1, (e - stage * 0.18) / 0.64)));
  function applyExplode() {
    for (const g of S.groups.values()) { const k = stageK(S.e, g.part.stage ?? 1); g.off = mul(g.part.ex || [0, 0, 0], k); }
    dirty = true;
  }
  function setExplode(k, instant) {
    S.eT = Math.max(0, Math.min(1, k));
    goal.follow = true; goal.refit = true;
    cb.onExplode(S.eT);
    if (instant) { S.e = S.eT; applyExplode(); frame(true); }
  }
  const getExplode = () => S.eT;

  /** bounds of the visible parts; atTarget = where they will be once the explode animation ends */
  function liveBox(ids, atTarget) {
    const bb = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity], empty: true };
    for (const [id, g] of S.groups) {
      if (!g.visible || REF.has(g.part.look) || !g.faces.length) continue;
      if (ids && !ids.includes(id)) continue;
      const off = atTarget ? mul(g.part.ex || [0, 0, 0], stageK(S.eT, g.part.stage ?? 1)) : g.off;
      for (let i = 0; i < 3; i++) { bb.min[i] = Math.min(bb.min[i], g.bb.min[i] + off[i]); bb.max[i] = Math.max(bb.max[i], g.bb.max[i] + off[i]); }
      bb.empty = false;
    }
    return bb;
  }
  const corners8 = (bb) => { const o = []; for (const x of [bb.min[0], bb.max[0]]) for (const y of [bb.min[1], bb.max[1]]) for (const z of [bb.min[2], bb.max[2]]) o.push([x, y, z]); return o; };
  function frame(instant) {
    // fit where the parts are going (not where the animation currently is), so a fast scroll
    // never leaves exploded parts outside the picture
    const bb = liveBox(S.focus ? [S.focus] : null, true);
    if (bb.empty) return;
    updateCamera();
    const w = cam.W; const h = cam.H;
    // named callouts sit in a column either side of the model: keep that room free
    const named = !S.focus && (opts.labels === 'on' || (opts.labels === 'auto' && S.eT > 0.45));
    const side = named ? Math.min(150, w * 0.26) : 0;
    let x0 = Infinity; let x1 = -Infinity; let y0 = Infinity; let y1 = -Infinity;
    for (const c of corners8(bb)) { const a = dot(c, cam.right); const b = dot(c, cam.up); x0 = Math.min(x0, a); x1 = Math.max(x1, a); y0 = Math.min(y0, b); y1 = Math.max(y1, b); }
    const aw = Math.max(160, w - opts.insetRight - side * 2);
    const need = Math.max((y1 - y0) * 1.12, (x1 - x0) * h / aw * 1.06) + 30;
    goal.dist = need; goal.fitDist = need;
    goal.target = mul(add(bb.min, bb.max), 0.5);
    if (opts.insetRight) goal.target = add(goal.target, mul(cam.right, opts.insetRight / 2 * need / h));
    goal.target = add(goal.target, mul(cam.up, -0.02 * need));   // a little head-room under the toolbar
    if (instant) { orbit.dist = goal.dist; orbit.target = goal.target.slice(); updateCamera(); }
  }
  function setView(name) {
    const v = { iso: [Math.PI / 4, ISO_PHI], iso2: [Math.PI * 0.75, ISO_PHI], front: [0, Math.PI / 2],
      side: [Math.PI / 2, Math.PI / 2], top: [0, 0.0001], back: [Math.PI, Math.PI / 2] }[name];
    if (!v) return;
    [orbit.theta, orbit.phi] = v;
    goal.follow = true; frame(true);
  }
  function fit() { goal.follow = true; frame(true); }

  function focus(id) {
    S.focus = id && S.focus !== id ? id : null;
    goal.follow = true; goal.refit = true; dirty = true;
    cb.onFocus(S.focus);
  }
  function setVisible(id, vis) { const g = S.groups.get(id); if (g) { g.visible = vis; dirty = true; } }
  function setOption(k, v) {
    opts[k] = v;
    if (k === 'style') applyStyle();
    if (k === 'section') show({ parts: S.parts, bbox: S.bbox }, { keepView: true });
    if ((k === 'insetRight' || k === 'labels') && goal.follow) goal.refit = true;
    dirty = true;
  }

  // ───────── shading: anatomy four tones + material response ─────────
  const rgbOf = (hex) => [(hex >> 16) & 255, (hex >> 8) & 255, hex & 255];
  function lookOf(look) { return (opts.style === 'real' ? REAL[look] : LOOK[look]) || (opts.style === 'real' ? REAL.body : LOOK.body); }
  const BANDS = [1.14, 0.96, 0.78, 0.6];
  function shade(f, n, id, ghost) {
    const m = ghost ? lookOf('ghost') : lookOf(f.look);
    let c = rgbOf(m.color);
    const s = dot(n, cam.L);
    let out;
    if (opts.style === 'real') {
      const amb = 0.36 + 0.1 * n[1];
      const dif = Math.max(0, s) * 0.72;
      let k = amb + dif;
      const H = unit(add(cam.L, cam.d)); const sp = Math.pow(Math.max(0, dot(n, H)), 10 + (1 - m.rough) * 50) * (0.15 + m.metal * 0.75) * (1.1 - m.rough * 0.6);
      const rim = Math.pow(1 - Math.abs(dot(n, cam.d)), 3) * 0.12;
      out = c.map((v) => v * k + 255 * (sp + rim));
    } else {
      const band = s > 0.55 ? 0 : s > 0.18 ? 1 : s > -0.2 ? 2 : 3;
      out = c.map((v) => v * BANDS[band]);
    }
    if (id === S.selected) out = out.map((v, i) => v * 0.6 + [224, 165, 38][i] * 0.4);
    else if (id === S.hovered) out = out.map((v, i) => v * 0.72 + [70, 120, 190][i] * 0.28);
    return `rgb(${out.map((v) => Math.max(0, Math.min(255, Math.round(v)))).join(',')})`;
  }

  // ───────── render (painter's order) ─────────
  function render() {
    const W = canvas.width; const H = canvas.height;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, W, H);
    if (opts.style !== 'real') { ctx.fillStyle = bgCss; ctx.fillRect(0, 0, W, H); }
    if (!S.bbox) { drawn = []; return; }
    const real = opts.style === 'real';
    const live = liveBox();
    if (!live.empty) drawGround(live, real);
    const list = [];
    for (const [id, g] of S.groups) {
      if (!g.visible) continue;
      const refLook = REF.has(g.part.look);
      const ghost = !!S.focus && id !== S.focus;
      for (const f of g.faces) {
        let n = f.n; const front = dot(n, cam.d) > 0;
        const translucent = refLook || ghost;
        if (!front && !f.two && !translucent) continue;
        if (!front) n = mul(n, -1);
        const P = f.p.map((v) => proj(add(v, g.off)));
        let z = 0; for (const q of P) z += q[2]; z /= P.length;
        list.push({ f, P, z, id, n, back: !front, ghost, translucent, alpha: ghost ? 0.14 : refLook ? (lookOf(g.part.look).opacity ?? 0.2) : 1, g });
      }
    }
    list.sort((a, b) => a.z - b.z);
    const lineA = real ? 0.16 : (opts.edges ? 0.55 : 0.32);
    const silA = real ? 0.38 : 0.7;
    const lw = Math.max(0.6, 0.9 * dpr);
    for (const it of list) {
      const { f, P } = it;
      ctx.globalAlpha = it.alpha;
      ctx.beginPath(); ctx.moveTo(P[0][0], P[0][1]);
      for (let i = 1; i < P.length; i++) ctx.lineTo(P[i][0], P[i][1]);
      ctx.closePath();
      let col = shade(f, it.n, it.id, it.ghost);
      if (it.back) col = col.replace(/rgb\((\d+),(\d+),(\d+)\)/, (m, r, g, b) => `rgb(${r * 0.55 | 0},${g * 0.55 | 0},${b * 0.55 | 0})`);
      ctx.fillStyle = col; ctx.fill();
      if (!it.translucent) { ctx.strokeStyle = col; ctx.lineWidth = 0.7; ctx.stroke(); }   // hide anti-alias seams
      if (f.tex && !it.back && !it.translucent) drawTex(f, it.g.off, P);
      if (it.translucent) { ctx.globalAlpha = 1; continue; }
      // crease lines and silhouettes (the kit's linework)
      ctx.lineWidth = lw; ctx.strokeStyle = `rgba(18,22,28,${lineA})`;
      ctx.beginPath(); let any = false;
      const n = P.length;
      if (f.cr) for (let i = 0; i < n; i++) if (f.cr[i]) { ctx.moveTo(P[i][0], P[i][1]); ctx.lineTo(P[(i + 1) % n][0], P[(i + 1) % n][1]); any = true; }
      if (any) ctx.stroke();
      if (f.sil && f.sil.length && !it.back) {
        ctx.beginPath(); any = false; ctx.strokeStyle = `rgba(18,22,28,${silA})`;
        for (const [e, n2] of f.sil) if (dot(n2, cam.d) <= 0) { ctx.moveTo(P[e][0], P[e][1]); ctx.lineTo(P[(e + 1) % n][0], P[(e + 1) % n][1]); any = true; }
        if (any) ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
    drawn = list;
    drawDims(live);
  }
  function drawTex(f, off, P) {
    const A = proj(add(f.tex.tl, off)); const B = proj(add(f.tex.tr, off)); const C = proj(add(f.tex.bl, off));
    const img = f.tex.img;
    ctx.save();
    ctx.beginPath(); ctx.moveTo(P[0][0], P[0][1]); for (let i = 1; i < P.length; i++) ctx.lineTo(P[i][0], P[i][1]); ctx.closePath(); ctx.clip();
    ctx.setTransform((B[0] - A[0]) / img.width, (B[1] - A[1]) / img.width, (C[0] - A[0]) / img.height, (C[1] - A[1]) / img.height, A[0], A[1]);
    const shadeK = Math.max(0.55, 0.62 + 0.45 * dot(f.n, cam.L));
    ctx.globalAlpha = 1; ctx.drawImage(img, 0, 0);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (shadeK < 1) { ctx.fillStyle = `rgba(0,0,0,${(1 - shadeK) * 0.6})`; ctx.fill(); }
    ctx.restore();
  }
  /** pedestal + soft contact shadow (real), or a faint ground grid (tech) */
  function drawGround(live, real) {
    const b0 = S.bbox;
    const cx = (b0.min[0] + b0.max[0]) / 2; const cz = (b0.min[2] + b0.max[2]) / 2;
    const foot = Math.max(b0.size[0], b0.size[2]);
    const y0 = Math.min(b0.min[1], live.min[1]) - 2;
    if (cam.d[1] <= 0.02) return;   // seen from below: no ground
    if (real) {
      const R = foot * 0.62 + 40; const Hh = Math.max(14, foot * 0.04);
      const top = []; const bot = [];
      for (let i = 0; i < 72; i++) { const a = i / 72 * Math.PI * 2; top.push(proj([cx + R * Math.sin(a), y0, cz + R * Math.cos(a)])); bot.push(proj([cx + R * 1.03 * Math.sin(a), y0 - Hh, cz + R * 1.03 * Math.cos(a)])); }
      // side band then the top disc
      ctx.fillStyle = 'rgba(160,158,152,0.9)';
      ctx.beginPath(); bot.forEach((q, i) => (i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1]))); ctx.closePath(); ctx.fill();
      for (let i = 0; i < 72; i++) {
        const j = (i + 1) % 72; ctx.beginPath(); ctx.moveTo(top[i][0], top[i][1]); ctx.lineTo(top[j][0], top[j][1]); ctx.lineTo(bot[j][0], bot[j][1]); ctx.lineTo(bot[i][0], bot[i][1]); ctx.closePath();
        const a = (i + 0.5) / 72 * Math.PI * 2; const s = dot([Math.sin(a), 0, Math.cos(a)], cam.L);
        const v = Math.round(150 + 55 * Math.max(0, s)); ctx.fillStyle = `rgb(${v},${v - 2},${v - 6})`; ctx.fill(); ctx.strokeStyle = ctx.fillStyle; ctx.lineWidth = 0.7; ctx.stroke();
      }
      ctx.fillStyle = '#d9d7d2'; ctx.beginPath(); top.forEach((q, i) => (i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1]))); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = 'rgba(18,22,28,0.25)'; ctx.lineWidth = dpr; ctx.stroke();
      // contact shadow (halo) mapped onto the top plane
      const s = foot * 0.66 + 30; const img = haloTex();
      const A = proj([cx - s, y0, cz - s]); const B = proj([cx + s, y0, cz - s]); const C = proj([cx - s, y0, cz + s]);
      ctx.save(); ctx.setTransform((B[0] - A[0]) / img.width, (B[1] - A[1]) / img.width, (C[0] - A[0]) / img.height, (C[1] - A[1]) / img.height, A[0], A[1]);
      ctx.drawImage(img, 0, 0); ctx.restore();
    } else {
      const size = Math.max(...b0.size) * 2; const n = 20;
      ctx.strokeStyle = 'rgba(136,153,170,0.22)'; ctx.lineWidth = dpr; ctx.beginPath();
      for (let i = -n; i <= n; i++) {
        const t = i / n * size;
        let a = proj([cx + t, y0, cz - size]); let b = proj([cx + t, y0, cz + size]); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]);
        a = proj([cx - size, y0, cz + t]); b = proj([cx + size, y0, cz + t]); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]);
      }
      ctx.stroke();
    }
  }
  /** assembled envelope L × W × H */
  function drawDims() {
    if (!opts.dims || S.e > 0.02 || S.focus || !S.bbox) return;
    const b = S.bbox; const s = b.size; const o = Math.max(...s) * 0.04;
    const C = corners8(b);
    ctx.strokeStyle = 'rgba(224,165,38,0.5)'; ctx.lineWidth = dpr; ctx.beginPath();
    for (let i = 0; i < 8; i++) for (let j = i + 1; j < 8; j++) {
      const diff = [0, 1, 2].filter((k) => C[i][k] !== C[j][k]).length;
      if (diff === 1) { const a = proj(C[i]); const c = proj(C[j]); ctx.moveTo(a[0], a[1]); ctx.lineTo(c[0], c[1]); }
    }
    ctx.stroke();
    const mk = (a, c, label) => {
      const A = proj(a); const B = proj(c);
      ctx.strokeStyle = '#e0a526'; ctx.lineWidth = 1.4 * dpr; ctx.beginPath(); ctx.moveTo(A[0], A[1]); ctx.lineTo(B[0], B[1]); ctx.stroke();
      const mx = (A[0] + B[0]) / 2; const my = (A[1] + B[1]) / 2;
      ctx.font = `600 ${12 * dpr}px system-ui, sans-serif`; const tw = ctx.measureText(label).width + 10 * dpr;
      ctx.fillStyle = 'rgba(20,24,30,0.82)'; ctx.fillRect(mx - tw / 2, my - 9 * dpr, tw, 18 * dpr);
      ctx.fillStyle = '#fff'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(label, mx, my + dpr);
    };
    mk([b.min[0], b.min[1], b.max[2] + o], [b.max[0], b.min[1], b.max[2] + o], `L ${Math.round(s[0])}`);
    mk([b.max[0] + o, b.min[1], b.min[2]], [b.max[0] + o, b.min[1], b.max[2]], `W ${Math.round(s[2])}`);
    mk([b.max[0] + o, b.min[1], b.max[2]], [b.max[0] + o, b.max[1], b.max[2]], `H ${Math.round(s[1])}`);
  }

  // ───────── balloons & callouts ─────────
  let svg = null;
  function makeBalloon(p) {
    if (!svg) { svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('class', 'v-leaders'); overlay.appendChild(svg); }
    const dotEl = document.createElement('button');
    dotEl.type = 'button'; dotEl.className = 'balloon'; dotEl.textContent = p.no ?? '';
    dotEl.setAttribute('aria-label', `${p.no ?? ''} ${p.dwgName || p.name}`);
    const label = document.createElement('button');
    label.type = 'button'; label.className = 'callout';
    label.innerHTML = '<b></b> <span></span>';
    label.querySelector('b').textContent = p.no ?? '';
    label.querySelector('span').textContent = p.dwgName || p.name;
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    svg.appendChild(line);
    for (const el of [dotEl, label]) {
      el.addEventListener('click', (ev) => { ev.stopPropagation(); select(p.id); cb.onPick(p.id); });
      el.addEventListener('dblclick', (ev) => { ev.stopPropagation(); focus(p.id); });
      el.addEventListener('pointerenter', () => { S.hovered = p.id; dirty = true; });
      el.addEventListener('pointerleave', () => { S.hovered = null; dirty = true; });
      el.addEventListener('wheel', (ev) => { ev.preventDefault(); onWheel(ev); }, { passive: false });
      overlay.appendChild(el);
    }
    balloons.set(p.id, { dot: dotEl, label, line, w: 0 });
  }
  function clearBalloons() {
    for (const b of balloons.values()) { b.dot.remove(); b.label.remove(); b.line.remove(); }
    balloons.clear();
  }
  function placeBalloons() {
    const w = cam.W; const h = cam.H;
    svg.setAttribute('width', w); svg.setAttribute('height', h);
    const named = opts.labels === 'on' || (opts.labels === 'auto' && S.e > 0.45);
    const dotsOn = opts.labels !== 'off' && (opts.labels === 'on' || S.e > 0.12);
    const items = []; let xmin = Infinity; let xmax = -Infinity;
    for (const [id, b] of balloons) {
      const g = S.groups.get(id);
      const vis = g && g.visible && g.faces.length && (!S.focus || S.focus === id);
      const showDot = vis && (dotsOn || id === S.selected || id === S.hovered);
      b.dot.style.display = showDot ? '' : 'none';
      b.dot.classList.toggle('sel', id === S.selected);
      if (!showDot) { b.label.style.display = 'none'; b.line.style.display = 'none'; continue; }
      const bb = { min: add(g.bb.min, g.off), max: add(g.bb.max, g.off) };
      const c = proj(mul(add(bb.min, bb.max), 0.5)); const x = c[0] / dpr; const y = c[1] / dpr;
      b.dot.style.transform = `translate(${x}px, ${y}px)`;
      for (const q of corners8(bb)) { const sx = proj(q)[0] / dpr; xmin = Math.min(xmin, sx); xmax = Math.max(xmax, sx); }
      items.push({ id, b, x, y, named: named || id === S.selected || id === S.hovered });
    }
    const mid = (xmin + xmax) / 2; const cols = { L: [], R: [] }; let alt = 0;
    for (const it of items.filter((i) => i.named).sort((a, c) => a.y - c.y)) {
      const side = it.x < mid - 6 ? 'L' : it.x > mid + 6 ? 'R' : (alt++ % 2 ? 'L' : 'R');
      cols[side].push(it);
    }
    const LH = 21; const pad = 8;
    for (const side of ['L', 'R']) {
      const list = cols[side];
      let y = -Infinity;
      for (const it of list) { it.ly = Math.max(it.y, y + LH); y = it.ly; }
      let lim = h - pad;
      for (let i = list.length - 1; i >= 0; i--) { list[i].ly = Math.min(list[i].ly, lim); lim = list[i].ly - LH; }
      for (const it of list) {
        it.ly = Math.max(pad + LH / 2, it.ly);
        const bl = it.b;
        bl.label.style.display = '';
        if (!bl.w) bl.w = bl.label.offsetWidth || 120;
        let lx = side === 'L' ? xmin - 28 : xmax + 28;
        if (side === 'L') lx = Math.max(bl.w + pad, Math.min(lx, w * 0.5 - 20)); else lx = Math.min(w - bl.w - pad, Math.max(lx, w * 0.5 + 20));
        bl.label.style.transform = side === 'L' ? `translate(${lx - bl.w}px, ${it.ly - LH / 2 + 1}px)` : `translate(${lx}px, ${it.ly - LH / 2 + 1}px)`;
        bl.label.classList.toggle('sel', it.id === S.selected);
        bl.line.style.display = '';
        const kx = side === 'L' ? lx + 6 : lx - 6;
        bl.line.setAttribute('points', `${it.x},${it.y} ${kx},${it.ly} ${lx},${it.ly}`);
        bl.line.setAttribute('class', it.id === S.selected ? 'sel' : '');
      }
    }
    for (const it of items.filter((i) => !i.named)) { it.b.label.style.display = 'none'; it.b.line.style.display = 'none'; }
  }

  // ───────── input ─────────
  function local(e) { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
  function worldAt(e) {
    const [x, y] = local(e);
    return add(add(orbit.target, mul(cam.right, (x - cam.W / 2) / cam.k)), mul(cam.up, (cam.H / 2 - y) / cam.k));
  }
  const MIN_VIEW = 3;   // mm of visible height at the closest zoom
  function zoomCamera(e, f) {
    if (goal.follow) frame(false);
    orbit.dist = goal.dist; orbit.target = goal.target.slice(); updateCamera();
    const before = goal.dist;
    const nd = Math.max(MIN_VIEW, Math.min(Math.max(goal.fitDist * 2, MIN_VIEW), before * f));   // zoom-out stops at half the fitted size
    const p = worldAt(e);
    goal.target = add(goal.target, mul(sub(p, goal.target), 1 - nd / before));
    goal.dist = nd; goal.follow = false;
  }
  let detentUntil = 0;
  function onWheel(e) {
    if (performance.now() < detentUntil) return;
    const steps = Math.max(-3, Math.min(3, e.deltaY / 100));
    if (!steps) return;
    const st = Math.abs(steps); const f = Math.exp(steps * 0.3);
    const auto = opts.autoExplode && !S.focus;
    if (steps < 0) {
      if (auto && goal.follow && S.eT < 1) {
        S.eT = Math.min(1, S.eT + 0.22 * st); goal.refit = true; cb.onExplode(S.eT);
        if (S.eT >= 1) detentUntil = performance.now() + 450;
      } else {
        const wasOut = goal.dist > goal.fitDist * 1.001;
        zoomCamera(e, f);
        if (auto && wasOut && goal.dist <= goal.fitDist) { goal.follow = true; goal.refit = true; }
      }
    } else if (!goal.follow) {
      zoomCamera(e, f);
      if (auto && S.eT > 0 && goal.dist >= goal.fitDist) { goal.follow = true; goal.refit = true; }
    } else if (auto && S.eT > 0) {
      S.eT = Math.max(0, S.eT - 0.22 * st); goal.refit = true; cb.onExplode(S.eT);
      if (S.eT <= 0) detentUntil = performance.now() + 250;
    } else zoomCamera(e, f);
  }
  function bindInput(el) {
    let drag = null; let lastClick = { t: 0, id: null };
    el.addEventListener('contextmenu', (e) => e.preventDefault());
    el.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY, btn: e.button, shift: e.shiftKey, moved: false }; try { el.setPointerCapture(e.pointerId); } catch (_) {} });
    el.addEventListener('pointermove', (e) => {
      if (!drag) { hoverAt(e); return; }
      const dx = e.clientX - drag.x; const dy = e.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 2) drag.moved = true;
      drag.x = e.clientX; drag.y = e.clientY;
      if (drag.btn === 2 || drag.btn === 1 || drag.shift) {
        orbit.target = add(add(orbit.target, mul(cam.right, -dx / cam.k)), mul(cam.up, dy / cam.k));
        goal.follow = false;
      } else {
        orbit.theta -= dx * 0.008;
        orbit.phi = Math.max(0.0001, Math.min(Math.PI - 0.0001, orbit.phi - dy * 0.008));
      }
      goal.target = orbit.target.slice(); goal.dist = orbit.dist;
      updateCamera();
    });
    el.addEventListener('pointerup', (e) => {
      if (drag && !drag.moved && drag.btn === 0) {
        const id = pick(e); const now = performance.now();
        if (id && now - lastClick.t < 350 && lastClick.id === id) focus(id);
        else { select(id); cb.onPick(id); }
        lastClick = { t: now, id };
      } else if (drag && drag.moved && goal.follow) goal.refit = true;
      drag = null;
    });
    el.addEventListener('wheel', (e) => { e.preventDefault(); onWheel(e); }, { passive: false });
  }
  function inside(P, x, y) {
    let c = false;
    for (let i = 0, j = P.length - 1; i < P.length; j = i++) {
      const a = P[i]; const b = P[j];
      if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
    }
    return c;
  }
  function pick(e) {
    const [lx, ly] = local(e); const x = lx * dpr; const y = ly * dpr;
    for (let i = drawn.length - 1; i >= 0; i--) {
      const it = drawn[i];
      if (it.translucent) continue;
      if (inside(it.P, x, y)) return it.id;
    }
    return null;
  }
  function hoverAt(e) {
    const id = pick(e);
    if (id !== S.hovered) { S.hovered = id; dirty = true; }
    cb.onHover(id, e);
  }
  function select(id) { S.selected = id; dirty = true; }

  // ───────── frame loop: redraw only when something changed ─────────
  function loop() {
    requestAnimationFrame(loop);
    if (Math.abs(S.e - S.eT) > 1e-4) {
      S.e += (S.eT - S.e) * 0.16; if (Math.abs(S.e - S.eT) < 2e-3) S.e = S.eT;
      applyExplode(); if (goal.follow) goal.refit = true;
    }
    if (goal.follow && goal.refit) { frame(false); goal.refit = false; }
    const dd = goal.dist - orbit.dist; const dt = sub(goal.target, orbit.target);
    if (Math.abs(dd) > 0.5 || dot(dt, dt) > 0.25) {
      orbit.dist += dd * 0.22; orbit.target = add(orbit.target, mul(dt, 0.22)); updateCamera();
    }
    if (!dirty) return;
    dirty = false;
    render();
    if (balloons.size && svg) placeBalloons();
  }

  // ───────── export ─────────
  function tris(includeRef, fn) {
    for (const [id, g] of S.groups) {
      if (!g.visible) continue;
      if (!includeRef && REF.has(g.part.look)) continue;
      for (const f of g.faces) {
        const P = f.p.map((v) => add(v, g.off));
        for (let i = 1; i < P.length - 1; i++) {
          let t = [P[0], P[i], P[i + 1]];
          if (dot(cross(sub(t[1], t[0]), sub(t[2], t[0])), f.n) < 0) t = [t[0], t[2], t[1]];
          fn(id, t, f.n);
        }
      }
    }
  }
  function toSTL() {
    const T = []; tris(false, (id, t, n) => T.push([n, ...t]));
    const buf = new ArrayBuffer(84 + T.length * 50); const dv = new DataView(buf);
    const head = 'IC-3D-Builder STL (mm)';
    for (let i = 0; i < head.length; i++) dv.setUint8(i, head.charCodeAt(i));
    dv.setUint32(80, T.length, true);
    let o = 84;
    for (const t of T) { for (const v of t) { dv.setFloat32(o, v[0], true); dv.setFloat32(o + 4, v[1], true); dv.setFloat32(o + 8, v[2], true); o += 12; } dv.setUint16(o, 0, true); o += 2; }
    return new Blob([buf], { type: 'model/stl' });
  }
  function toOBJ(name) {
    const L = ['# IC-3D-Builder OBJ, units mm, Y-up', `o ${name || 'item'}`];
    let base = 1; let cur = null;
    tris(false, (id, t) => {
      if (id !== cur) { const p = S.groups.get(id).part; L.push(`g ${p.no ?? ''}_${id}`); cur = id; }
      for (const v of t) L.push(`v ${v[0].toFixed(2)} ${v[1].toFixed(2)} ${v[2].toFixed(2)}`);
      L.push(`f ${base} ${base + 1} ${base + 2}`); base += 3;
    });
    return new Blob([L.join('\n')], { type: 'text/plain' });
  }
  function toPNG() {
    render();
    const c = document.createElement('canvas'); c.width = canvas.width; c.height = canvas.height;
    const g = c.getContext('2d'); g.fillStyle = opts.style === 'real' ? '#eceef0' : bgCss; g.fillRect(0, 0, c.width, c.height); g.drawImage(canvas, 0, 0);
    return c.toDataURL('image/png');
  }
  const lookColor = (k) => '#' + (LOOK[k] || LOOK.body).color.toString(16).padStart(6, '0');

  return { init, show, fit, setView, setExplode, getExplode, setVisible, setOption, setBackground, select, focus,
    toSTL, toOBJ, toPNG, lookColor, state: S, opts, render: () => { dirty = true; } };
})();
window.Viewer = Viewer;
