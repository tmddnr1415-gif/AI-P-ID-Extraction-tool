/* 계측제어 Item 3D Anatomy 뷰어 — 자체 생성 개념 모델(제조사 도면 아님, 치수 미확인).
   마우스 드래그=회전, 휠=확대/축소, 우클릭·Shift 드래그=이동, 더블클릭=리셋, 부품 hover=이름, 클릭=점멸. */
(function (G) {
  "use strict";
  /* ---------- 벡터 ---------- */
  const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const mul = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const len = (a) => Math.hypot(a[0], a[1], a[2]);
  const nrm = (a) => { const l = len(a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
  const AX = { x: [1, 0, 0], y: [0, 1, 0], z: [0, 0, 1], "-x": [-1, 0, 0], "-y": [0, -1, 0], "-z": [0, 0, -1] };
  const basis = (a) => { a = nrm(Array.isArray(a) ? a : AX[a]); const t = Math.abs(a[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0]; const u = nrm(cross(a, t)); return [a, u, cross(a, u)]; };

  // 부품 자세: {sc:[origin,[sx,sy,sz]], rot:[axis,origin,angle], tr:[x,y,z], col:[r,g,b], glow:0..1, gcol:[r,g,b], hide}
  function rotP(p, k, o, a) { const v = sub(p, o), c = Math.cos(a), s = Math.sin(a); const r = add(add(mul(v, c), mul(cross(k, v), s)), mul(k, dot(k, v) * (1 - c))); return add(r, o); }
  function rotN(n, k, a) { const c = Math.cos(a), s = Math.sin(a); return add(add(mul(n, c), mul(cross(k, n), s)), mul(k, dot(k, n) * (1 - c))); }
  function poseP(p, q) {
    if (q.sc) { const [o, f] = q.sc; p = [o[0] + (p[0] - o[0]) * f[0], o[1] + (p[1] - o[1]) * f[1], o[2] + (p[2] - o[2]) * f[2]]; }
    if (q.rot) p = rotP(p, nrm(q.rot[0]), q.rot[1], q.rot[2]);
    if (q.rot2) p = rotP(p, nrm(q.rot2[0]), q.rot2[1], q.rot2[2]);
    if (q.tr) p = add(p, q.tr);
    return p;
  }
  function poseN(n, q) { if (q.rot) n = rotN(n, nrm(q.rot[0]), q.rot[2]); if (q.rot2) n = rotN(n, nrm(q.rot2[0]), q.rot2[2]); return n; }

  /* ---------- 색 ---------- */
  const C = {
    steel: [178, 184, 194], body: [150, 157, 170], dark: [84, 90, 102], black: [44, 46, 52], white: [244, 245, 247],
    blue: [52, 78, 168], yellow: [226, 178, 36], red: [204, 52, 46], green: [46, 150, 96], cab: [214, 218, 225],
    brass: [196, 160, 80], concrete: [205, 205, 200], orange: [228, 120, 36], cable: [60, 62, 70], navy: [30, 44, 110],
    glass: [190, 214, 236], lcd: [70, 110, 150], copper: [190, 110, 70],
  };

  /* ---------- 모델 빌더 ---------- */
  function Builder() {
    const faces = []; const MAXS = 14;
    const face = (part, col, pts, n, o = {}) => faces.push({ part, col, pts, n: nrm(n), a: o.a == null ? 1 : o.a });
    // 축대칭 회전체. prof=[[t,r],...] (t 증가 방향, 재료는 축 쪽). opt.cap0/cap1, capCol
    function lathe(part, col, axis, o, prof, seg = 24, opt = {}) {
      const [a, u, v] = basis(axis); const P = [];
      for (let i = 0; i < prof.length - 1; i++) { // 긴 구간 분할(정렬 정확도)
        const [t0, r0] = prof[i], [t1, r1] = prof[i + 1]; const n = Math.max(1, Math.ceil(Math.hypot(t1 - t0, r1 - r0) / MAXS));
        for (let k = 0; k < n; k++) P.push([t0 + (t1 - t0) * k / n, r0 + (r1 - r0) * k / n]);
      }
      P.push(prof[prof.length - 1]);
      const ph = opt.phase || 0; const ring = (t, r, j) => { const g = ph + (j / seg) * Math.PI * 2; return add(o, add(mul(a, t), add(mul(u, Math.cos(g) * r), mul(v, Math.sin(g) * r)))); };
      for (let i = 0; i < P.length - 1; i++) {
        const [t0, r0] = P[i], [t1, r1] = P[i + 1]; const dt = t1 - t0, dr = r1 - r0; if (Math.abs(dt) + Math.abs(dr) < 1e-6) continue;
        for (let j = 0; j < seg; j++) {
          const gm = ph + ((j + 0.5) / seg) * Math.PI * 2; const rad = add(mul(u, Math.cos(gm)), mul(v, Math.sin(gm)));
          face(part, col, [ring(t0, r0, j), ring(t1, r1, j), ring(t1, r1, j + 1), ring(t0, r0, j + 1)], add(mul(a, -dr), mul(rad, dt)), opt);
        }
      }
      const cap = (t, r, s, cc) => { if (r <= 0.01) return; const c = add(o, mul(a, t)); for (let j = 0; j < seg; j++) face(part, cc || col, [c, ring(t, r, j), ring(t, r, j + 1)], mul(a, s), opt); };
      if (opt.cap0 !== false) cap(prof[0][0], prof[0][1], -1, opt.capCol0);
      if (opt.cap1 !== false) cap(prof[prof.length - 1][0], prof[prof.length - 1][1], 1, opt.capCol);
    }
    const cyl = (part, col, axis, o, r, l, seg = 20, opt = {}) => lathe(part, col, axis, o, [[0, r], [l, r]], seg, opt);
    const hex = (part, col, axis, o, r, l, opt = {}) => lathe(part, col, axis, o, [[0, r], [l, r]], 6, Object.assign({ phase: Math.PI / 6 }, opt));
    const sphere = (part, col, o, r, seg = 20, opt = {}) => { const p = []; for (let i = 0; i <= 10; i++) { const g = -Math.PI / 2 + Math.PI * i / 10; p.push([Math.sin(g) * r, Math.cos(g) * r]); } lathe(part, col, opt.axis || "y", o, p, seg, Object.assign({ cap0: false, cap1: false }, opt)); };
    // 직육면체 (중심, 크기) — 면 분할
    function box(part, col, c, s, opt = {}) {
      const [cx, cy, cz] = c, [w, h, d] = s; const hx = w / 2, hy = h / 2, hz = d / 2;
      const F = [[[1, 0, 0], [0, 0, -1], [0, 1, 0], hx, d, h], [[-1, 0, 0], [0, 0, 1], [0, 1, 0], hx, d, h], [[0, 1, 0], [1, 0, 0], [0, 0, -1], hy, w, d], [[0, -1, 0], [1, 0, 0], [0, 0, 1], hy, w, d], [[0, 0, 1], [1, 0, 0], [0, 1, 0], hz, w, h], [[0, 0, -1], [-1, 0, 0], [0, 1, 0], hz, w, h]];
      for (const [n, e1, e2, off, L1, L2] of F) {
        if (opt.skip && opt.skip.some((q) => dot(q, n) > 0.9)) continue;
        const n1 = Math.max(1, Math.ceil(L1 / (MAXS * 1.4))), n2 = Math.max(1, Math.ceil(L2 / (MAXS * 1.4)));
        const fc = add(c, mul(n, off)); const cc = opt.faceCol && opt.faceCol(n) || col;
        for (let i = 0; i < n1; i++) for (let j = 0; j < n2; j++) {
          const p = (a, b) => add(fc, add(mul(e1, (-0.5 + a / n1) * L1), mul(e2, (-0.5 + b / n2) * L2)));
          face(part, cc, [p(i, j), p(i + 1, j), p(i + 1, j + 1), p(i, j + 1)], n, opt);
        }
      }
    }
    // 평면 다각형(판·눈금·바늘) — pts 는 world 좌표
    const quad = (part, col, pts, n, opt) => face(part, col, pts, n, opt);
    // 배관/케이블: 꺾은선 경로를 원통으로
    function tube(part, col, pts, r, seg = 10, opt = {}) {
      for (let i = 0; i < pts.length - 1; i++) {
        const d = sub(pts[i + 1], pts[i]); const l = len(d); if (l < 1e-6) continue;
        cyl(part, col, d, pts[i], r, l, seg, { cap0: i === 0 && opt.ends !== false, cap1: i === pts.length - 2 && opt.ends !== false, a: opt.a });
        if (i > 0 && opt.joints !== false) sphere(part, col, pts[i], r, seg, { a: opt.a });
      }
    }
    // 원 위 볼트(축 방향 원통)
    function bolts(part, col, axis, o, R, n, r, l, ph = 0) {
      const [a, u, v] = basis(axis);
      for (let i = 0; i < n; i++) { const g = ph + i / n * Math.PI * 2; hex(part, col, a, add(o, add(mul(u, Math.cos(g) * R), mul(v, Math.sin(g) * R))), r, l); }
    }
    // 플랜지 + 배관 스텁: o=플랜지 시작점, dir=바깥 방향
    function flange(part, o, dir, rp = 9, rf = 22, th = 8, stub = 18, nb = 8) {
      lathe(part, C.steel, dir, o, [[0, rp + 3], [4, rp + 3], [4, rf], [4 + th, rf], [4 + th, rp], [4 + th + stub, rp]], 28, { capCol: C.dark });
      lathe(part, C.steel, dir, add(o, mul(nrm(AX[dir] || dir), 4 + th)), [[0, rf], [th * 0.9, rf], [th * 0.9, rp + 2]], 28, { cap0: false });
      bolts(part, C.dark, dir, add(o, mul(nrm(AX[dir] || dir), 2)), rf - 3.5, nb, 1.7, th * 1.9 + 4);
    }
    return { faces, lathe, cyl, hex, sphere, box, quad, tube, bolts, flange };
  }

  /* ---------- 공통: 캐비닛 ---------- */
  function cabinet(b, x0, mods) {
    const W = 80, H = 200, D = 60, cx = x0;
    b.box("cabinet", C.dark, [cx, 5, 0], [W, 10, D]);
    b.box("cabinet", C.cab, [cx, 105, -D / 2 + 1], [W, 190, 2]);
    b.box("cabinet", C.cab, [cx - W / 2 + 1, 105, 0], [2, 190, D]);
    b.box("cabinet", C.cab, [cx + W / 2 - 1, 105, 0], [2, 190, D]);
    b.box("cabinet", C.cab, [cx, 202, 0], [W + 2, 4, D + 2]);
    b.box("cabinet", C.cab, [cx - W / 2 - 1, 105, D / 2 + 38], [2, 186, 76]); // 열린 문
    b.box("cabinet", C.dark, [cx - W / 2 - 3, 110, D / 2 + 70], [2, 14, 3]);
    b.box("cabinet", C.steel, [cx, 105, -D / 2 + 3], [W - 10, 186, 2]); // 마운팅 판
    mods(b, cx);
  }
  const led = (b, part, x, y, z, col) => b.box(part, col, [x, y, z], [1.6, 1.6, 0.6]);

  /* ---------- 모델 정의 ---------- */
  const MODELS = {};
  const M = (id, title, parts, shell, fn) => (MODELS[id] = { id, title, parts, shell, fn });
  const SIM = (id, sim) => { MODELS[id].sim = sim; };

  M("ball-valve", "Ball Valve — ESDV (트러니언 볼 + 스프링리턴 액추에이터)", {
    "process-conn": "Process connection(플랜지)", body: "Body(2-piece)", ball: "Ball(Full bore)", seat: "Seat ring", stem: "Stem(Blow-out proof)",
    bracket: "Mounting bracket(ISO 5211)", actuator: "Actuator(Scotch-yoke, 공압 실린더)", spring: "Spring cartridge(Fail-close)", solenoid: "SOV(Solenoid valve)",
    "limit-switch": "Limit switch box", pst: "PST device/Smart positioner", support: "Pipe support",
  }, ["body"], (b) => {
    b.flange("process-conn", [-38, 0, 0], "-x"); b.flange("process-conn", [38, 0, 0], "x");
    b.lathe("body", C.body, "x", [-38, 0, 0], [[0, 12], [8, 22], [16, 27], [60, 27], [68, 22], [76, 12]], 28);
    b.lathe("body", C.body, "x", [-4, 0, 0], [[0, 27], [0, 31], [8, 31], [8, 27]], 28, { cap0: false, cap1: false });
    b.bolts("body", C.dark, "x", [-6, 0, 0], 29, 10, 1.5, 12);
    b.lathe("body", C.body, "y", [0, 20, 0], [[0, 15], [10, 15], [10, 18], [14, 18], [14, 8]], 24);
    b.lathe("body", C.body, "-y", [0, -20, 0], [[0, 12], [8, 12], [8, 14], [11, 14]], 24);
    b.sphere("ball", C.white, [0, 0, 0], 21, 24);
    b.cyl("ball", C.black, "x", [-20.2, 0, 0], 8.5, 40.4, 20);
    b.lathe("seat", C.brass, "x", [-24, 0, 0], [[0, 12], [0, 22], [3, 22], [3, 12], [0, 12]], 24, { cap0: false, cap1: false });
    b.lathe("seat", C.brass, "x", [21, 0, 0], [[0, 12], [0, 22], [3, 22], [3, 12], [0, 12]], 24, { cap0: false, cap1: false });
    b.cyl("stem", C.steel, "y", [0, 20, 0], 4, 34, 16);
    b.box("bracket", C.dark, [0, 36, 0], [34, 3, 34]);
    for (const [x, z] of [[-14, -14], [14, -14], [-14, 14], [14, 14]]) b.cyl("bracket", C.dark, "y", [x, 36, z], 1.8, 16, 8);
    b.box("bracket", C.dark, [0, 53, 0], [34, 3, 34]);
    b.box("actuator", C.blue, [0, 68, 0], [40, 28, 34]);
    b.lathe("actuator", C.blue, "z", [0, 68, 17], [[0, 13], [3, 15], [38, 15], [42, 13]], 24);
    b.box("actuator", C.blue, [0, 68, 61], [30, 30, 4]);
    b.lathe("spring", C.yellow, "-z", [0, 68, -17], [[0, 14], [4, 17], [50, 17], [56, 12]], 24);
    for (const [x, y] of [[-12, 56], [12, 56], [-12, 80], [12, 80]]) b.cyl("spring", C.dark, "z", [x, y, 17], 1.2, 46, 6);
    b.box("limit-switch", C.dark, [0, 90, 0], [24, 14, 20]);
    b.lathe("limit-switch", C.yellow, "y", [0, 97, 0], [[0, 9], [3, 9], [6, 7], [8, 0]], 20);
    b.box("solenoid", C.dark, [26, 66, 22], [12, 18, 12]);
    b.cyl("solenoid", C.black, "y", [26, 75, 22], 5, 12, 16);
    b.tube("solenoid", C.copper, [[26, 60, 28], [26, 60, 40], [12, 60, 40]], 1.1, 8);
    b.box("pst", C.navy, [-28, 70, 14], [14, 24, 16]);
    b.cyl("pst", C.glass, "-x", [-35, 74, 14], 4, 1.5, 16);
    b.box("support", C.dark, [-62, -22, 0], [10, 26, 30]); b.box("support", C.dark, [62, -22, 0], [10, 26, 30]);
    b.box("support", C.concrete, [0, -38, 0], [160, 6, 50]);
  });

  M("globe-valve", "Globe Valve — Control Valve (공압 다이어프램 + Positioner)", {
    "process-conn": "Process connection(플랜지)", body: "Body(Globe)", trim: "Trim/Plug", seat: "Seat ring", bonnet: "Bonnet(Packing)", stem: "Stem",
    yoke: "Yoke", actuator: "Diaphragm actuator", positioner: "Positioner(Smart, HART)",
  }, ["body", "bonnet"], (b) => {
    b.flange("process-conn", [-30, 0, 0], "-x"); b.flange("process-conn", [30, 0, 0], "x");
    b.lathe("body", C.body, "x", [-30, 0, 0], [[0, 12], [8, 22], [16, 28], [44, 28], [52, 22], [60, 12]], 28);
    b.lathe("body", C.body, "y", [0, 18, 0], [[0, 18], [6, 18], [6, 22], [10, 22], [10, 15]], 24);
    b.bolts("body", C.dark, "y", [0, 22, 0], 19, 8, 1.6, 9);
    b.lathe("seat", C.brass, "y", [0, -8, 0], [[0, 9], [0, 14], [3, 14], [3, 9], [0, 9]], 24, { cap0: false, cap1: false });
    b.lathe("trim", C.white, "y", [0, -5, 0], [[0, 0.01], [2, 8], [6, 10], [24, 10]], 24);
    b.lathe("bonnet", C.steel, "y", [0, 28, 0], [[0, 14], [6, 13], [26, 10], [30, 13], [34, 13]], 24);
    b.cyl("stem", C.white, "y", [0, 19, 0], 2.4, 86, 12);
    b.lathe("yoke", C.dark, "y", [0, 62, 0], [[0, 14], [4, 14]], 24);
    b.box("yoke", C.dark, [-14, 79, 0], [5, 30, 9]); b.box("yoke", C.dark, [14, 79, 0], [5, 30, 9]);
    b.lathe("yoke", C.dark, "y", [0, 94, 0], [[0, 16], [4, 16]], 24);
    b.lathe("actuator", C.blue, "y", [0, 98, 0], [[0, 10], [4, 30], [9, 37], [11, 38], [13, 37], [18, 30], [24, 12], [26, 6]], 32);
    b.bolts("actuator", C.dark, "y", [0, 106, 0], 37, 14, 1.2, 6);
    b.cyl("actuator", C.copper, "y", [0, 124, 0], 2, 6, 10);
    b.box("positioner", C.navy, [0, 80, 24], [24, 22, 12]);
    b.cyl("positioner", C.white, "z", [-6, 84, 30], 3.4, 2.5, 16); b.cyl("positioner", C.white, "z", [6, 84, 30], 3.4, 2.5, 16);
    b.box("positioner", C.dark, [0, 78, 10], [3, 3, 18]);
    b.tube("positioner", C.copper, [[10, 91, 24], [10, 100, 24], [10, 100, 34], [0, 130, 34], [0, 130, 0]], 1, 8);
  });

  M("butterfly-valve", "Butterfly Valve — Triple offset (Rack&Pinion 액추에이터)", {
    "process-conn": "Process connection(플랜지)", body: "Body(Wafer/Lug)", disc: "Disc", shaft: "Shaft", actuator: "Actuator(Rack & Pinion)", positioner: "Positioner/Limit switch",
  }, ["body"], (b) => {
    b.flange("process-conn", [-14, 0, 0], "-x", 26, 42, 7, 16, 12); b.flange("process-conn", [14, 0, 0], "x", 26, 42, 7, 16, 12);
    b.lathe("body", C.body, "x", [-14, 0, 0], [[0, 27], [0, 38], [28, 38], [28, 27], [0, 27]], 32, { cap0: false, cap1: false });
    const g = 35 * Math.PI / 180; b.lathe("disc", C.white, [Math.cos(g), 0, Math.sin(g)], [-3 * Math.cos(g), 0, -3 * Math.sin(g)], [[0, 0.01], [0.5, 22], [2, 26], [4, 26], [5.5, 22], [6, 0.01]], 32);
    b.cyl("shaft", C.steel, "y", [0, -30, 0], 3.4, 82, 12);
    b.cyl("body", C.body, "y", [0, 36, 0], 8, 16, 16); b.cyl("body", C.body, "-y", [0, -36, 0], 7, 8, 16);
    b.box("actuator", C.dark, [0, 55, 0], [30, 4, 30]);
    b.box("actuator", C.blue, [0, 70, 0], [56, 24, 28]);
    b.lathe("actuator", C.blue, "x", [28, 70, 0], [[0, 12], [3, 12], [4, 9]], 20); b.lathe("actuator", C.blue, "-x", [-28, 70, 0], [[0, 12], [3, 12], [4, 9]], 20);
    b.box("positioner", C.navy, [0, 90, 0], [24, 14, 18]);
    b.lathe("positioner", C.yellow, "y", [0, 97, 0], [[0, 8], [3, 8], [5, 6], [7, 0]], 20);
  });

  M("psv", "PSV — Conventional spring-loaded (Lifting lever)", {
    "process-conn": "Inlet/Outlet flange", body: "Body", nozzle: "Nozzle", disc: "Disc", bonnet: "Bonnet", spring: "Spring", stem: "Spindle", cap: "Cap", lever: "Lifting lever",
  }, ["body", "bonnet"], (b) => {
    b.flange("process-conn", [0, -26, 0], "-y", 11, 24, 8, 14, 8);
    b.lathe("body", C.red, "y", [0, -26, 0], [[0, 14], [8, 20], [34, 20], [40, 15]], 28);
    b.lathe("body", C.red, "x", [12, -6, 0], [[0, 15], [20, 15]], 28, { cap0: false });
    b.flange("process-conn", [32, -6, 0], "x", 15, 30, 8, 14, 8);
    b.lathe("nozzle", C.steel, "y", [0, -30, 0], [[0, 9], [26, 9], [28, 11], [30, 11]], 20, { cap1: false });
    b.lathe("disc", C.white, "y", [0, 0, 0], [[0, 12], [4, 12], [6, 6]], 20);
    b.lathe("body", C.red, "y", [0, 14, 0], [[0, 22], [5, 22]], 28);
    b.bolts("body", C.dark, "y", [0, 11, 0], 19, 8, 1.5, 10);
    b.lathe("bonnet", C.red, "y", [0, 19, 0], [[0, 16], [8, 13], [56, 11], [60, 13], [64, 13]], 24);
    const sp = []; for (let i = 0; i <= 72; i++) { const g = i / 72 * Math.PI * 2 * 8; sp.push([Math.cos(g) * 8, 28 + i / 72 * 44, Math.sin(g) * 8]); }
    b.tube("spring", C.yellow, sp, 1.4, 6, { ends: false, joints: false });
    b.lathe("spring", C.dark, "y", [0, 25, 0], [[0, 10], [3, 10]], 20); b.lathe("spring", C.dark, "y", [0, 72, 0], [[0, 10], [3, 10]], 20);
    b.cyl("stem", C.steel, "y", [0, 6, 0], 2, 96, 10);
    b.lathe("cap", C.dark, "y", [0, 83, 0], [[0, 9], [14, 9], [18, 5], [20, 0.01]], 20);
    b.box("lever", C.dark, [14, 96, 0], [30, 3, 4]); b.cyl("lever", C.dark, "z", [0, 96, -3], 2.4, 6, 10);
  });

  M("field-gauge", "Field Gauge — Bourdon 압력계(100 mm, Bottom 연결)", {
    case: "Case(SS, Solid front)", dial: "Dial(눈금판)", needle: "Pointer", bezel: "Bezel/Window", socket: "Socket(Hex)", "process-conn": "Process connection(1/2\" NPT)", blowout: "Blow-out disc",
  }, [], (b) => {
    b.lathe("case", C.steel, "z", [0, 0, -14], [[0, 46], [2, 50], [24, 50]], 40, { cap1: false });
    b.lathe("bezel", C.steel, "z", [0, 0, 10], [[0, 50], [2, 51], [5, 49], [5, 46]], 40, { cap0: false, capCol: C.glass, a: 1 });
    b.cyl("dial", C.white, "z", [0, 0, 8], 46, 0.5, 40);
    for (let i = 0; i <= 50; i++) {
      const g = (225 - i * 270 / 50) * Math.PI / 180, ma = i % 5 === 0; const r1 = 41, r0 = ma ? 34 : 37.5, w = ma ? 0.8 : 0.4; const c = Math.cos(g), s = Math.sin(g), px = -s * w, py = c * w;
      b.quad("dial", C.black, [[c * r0 + px, s * r0 + py, 8.8], [c * r1 + px, s * r1 + py, 8.8], [c * r1 - px, s * r1 - py, 8.8], [c * r0 - px, s * r0 - py, 8.8]], [0, 0, 1]);
    }
    for (let i = 0; i < 12; i++) { const g = (225 - 270 * (i / 12)) * Math.PI / 180; }
    const g = 120 * Math.PI / 180, c = Math.cos(g), s = Math.sin(g);
    b.quad("needle", C.red, [[-c * 6 - s * 1.6, -s * 6 + c * 1.6, 9.6], [c * 38, s * 38, 9.6], [-c * 6 + s * 1.6, -s * 6 - c * 1.6, 9.6]], [0, 0, 1]);
    b.cyl("needle", C.black, "z", [0, 0, 8.8], 3, 1.6, 16);
    b.cyl("blowout", C.dark, "-z", [0, 0, -14], 14, 1.5, 24);
    b.lathe("socket", C.brass, "y", [0, -62, -2], [[0, 5], [6, 5]], 12);
    b.hex("socket", C.brass, "y", [0, -56, -2], 9, 7);
    b.cyl("socket", C.brass, "y", [0, -49, -2], 5, 4, 12);
    b.lathe("process-conn", C.brass, "-y", [0, -62, -2], [[0, 5], [12, 4.4]], 16);
    b.hex("process-conn", C.steel, "-y", [0, -78, -2], 8, 8);
    b.cyl("process-conn", C.steel, "-y", [0, -86, -2], 6, 20, 16, { capCol: C.dark });
  });

  M("transmitter", "Transmitter — DP Coplanar + 3-valve manifold", {
    housing: "Electronics housing(Dual compartment)", cover: "Cover", display: "LCD display", sensor: "Sensor module", flange: "Coplanar flange", manifold: "3-valve manifold", "process-conn": "Impulse line connection", conduit: "Conduit entry(M20/½\"NPT)",
  }, [], (b) => {
    b.lathe("housing", C.blue, "x", [-22, 64, 0], [[0, 15], [44, 15]], 28);
    b.lathe("cover", C.blue, "-x", [-22, 64, 0], [[0, 16], [6, 16], [8, 14]], 28, { capCol: C.lcd });
    b.lathe("cover", C.blue, "x", [22, 64, 0], [[0, 16], [6, 16], [8, 14]], 28);
    b.cyl("display", C.glass, "-x", [-30, 64, 0], 10, 0.6, 24);
    b.cyl("conduit", C.dark, "z", [-10, 58, 12], 3.6, 10, 12); b.cyl("conduit", C.dark, "z", [10, 58, 12], 3.6, 10, 12);
    b.hex("conduit", C.steel, "z", [-10, 58, 20], 4.6, 3); b.cyl("conduit", C.cable, "z", [-10, 58, 23], 2.4, 20, 10);
    b.cyl("sensor", C.steel, "y", [0, 46, 0], 6, 6, 16);
    b.lathe("sensor", C.steel, "y", [0, 10, 0], [[0, 15], [34, 15], [36, 10]], 28);
    b.box("flange", C.steel, [0, 3, 0], [48, 14, 32]);
    for (const [x, z] of [[-18, -10], [18, -10], [-18, 10], [18, 10]]) b.hex("flange", C.dark, "y", [x, 10, z], 2.6, 4);
    b.box("manifold", C.steel, [0, -16, 0], [62, 22, 30]);
    for (const x of [-22, 0, 22]) { b.cyl("manifold", C.steel, "z", [x, -16, 15], 3, 12, 12); b.box("manifold", x === 0 ? C.green : C.red, [x, -16, 29], [22, 4, 4]); }
    b.cyl("process-conn", C.steel, "-y", [-11, -27, 0], 3.5, 10, 12); b.cyl("process-conn", C.steel, "-y", [11, -27, 0], 3.5, 10, 12);
    b.hex("process-conn", C.steel, "-y", [-11, -37, 0], 5, 6); b.hex("process-conn", C.steel, "-y", [11, -37, 0], 5, 6);
    b.tube("process-conn", C.steel, [[-11, -43, 0], [-11, -70, 0], [-40, -70, 0]], 2, 8); b.tube("process-conn", C.steel, [[11, -43, 0], [11, -60, 0], [40, -60, 0]], 2, 8);
  });

  M("bulk-material", "Bulk Material — JB · Gland · Cable tray · Tubing/Fitting", {
    jb: "Junction box(Ex e)", gland: "Cable gland(Ex d/e)", cable: "Instrument cable", tray: "Cable tray(Ladder)", tubing: "Instrument tubing(SS 316)", fitting: "Compression fitting/Valve", support: "Support(Angle)",
  }, [], (b) => {
    b.box("support", C.dark, [-10, 30, -8], [4, 120, 4]); b.box("support", C.dark, [-10, -29, -8], [24, 2, 24]);
    b.box("jb", C.cab, [-10, 60, 4], [56, 56, 18]); b.box("jb", C.cab, [-10, 60, 14], [58, 58, 2]);
    for (const [x, y] of [[-36, 86], [16, 86], [-36, 34], [16, 34]]) b.cyl("jb", C.steel, "z", [x, y, 15], 1.4, 1.6, 8);
    b.box("jb", C.steel, [-10, 60, 15.6], [20, 8, 0.4]);
    const gx = [-28, -16, -4, 8];
    gx.forEach((x, i) => {
      b.cyl("gland", C.brass, "-y", [x, 32, 4], 3.2, 4, 12); b.hex("gland", C.brass, "-y", [x, 28, 4], 4.4, 4); b.cyl("gland", C.brass, "-y", [x, 24, 4], 3.4, 4, 12);
      b.tube("cable", i % 2 ? C.cable : C.navy, [[x, 20, 4], [x, -4, 4], [x, -18, 4 + i * 4], [x + 90, -18, 4 + i * 4]], 2, 8);
    });
    b.box("tray", C.steel, [40, -23, 10], [140, 1.5, 34]);
    b.box("tray", C.steel, [40, -18, -7], [140, 10, 1.5]); b.box("tray", C.steel, [40, -18, 27], [140, 10, 1.5]);
    for (let x = -24; x <= 104; x += 16) b.box("tray", C.dark, [x, -22, 10], [3, 1.2, 32]);
    b.tube("tubing", C.steel, [[50, 80, 20], [50, 50, 20], [80, 50, 20], [80, 10, 20]], 1.6, 10);
    b.hex("fitting", C.steel, "-y", [50, 86, 20], 3.2, 6); b.hex("fitting", C.steel, "y", [50, 74, 20], 2.8, 4);
    b.hex("fitting", C.steel, "x", [62, 50, 20], 3, 5); b.hex("fitting", C.steel, "x", [68, 50, 20], 3, 5);
    b.box("fitting", C.steel, [80, 30, 20], [10, 12, 10]); b.cyl("fitting", C.steel, "z", [80, 30, 25], 1.8, 8, 10); b.box("fitting", C.red, [80, 30, 34], [16, 3, 3]);
    b.box("support", C.dark, [94, 30, 20], [4, 100, 4]); b.box("support", C.dark, [87, 50, 20], [14, 3, 6]);
  });

  M("dcs", "DCS — System cabinet + Operator console", {
    cabinet: "System cabinet", controller: "Controller(Redundant)", io: "I/O card", psu: "Power supply(Redundant)", network: "Control network switch", terminal: "Terminal/Marshalling", hmi: "Operator console(HMI)",
  }, ["cabinet"], (b) => {
    cabinet(b, 0, (b, cx) => {
      for (const x of [-16, 8]) { b.box("controller", C.black, [cx + x, 176, -24], [20, 26, 10]); led(b, "controller", cx + x - 5, 184, -18.8, C.green); led(b, "controller", cx + x - 1, 184, -18.8, C.green); }
      b.box("network", C.navy, [cx, 154, -25], [56, 8, 8]); for (let i = 0; i < 8; i++) led(b, "network", cx - 22 + i * 6, 154, -20.8, C.green);
      b.tube("network", C.yellow, [[cx - 16, 158, -21], [cx - 16, 163, -16], [cx - 16, 168, -19]], 0.8, 6); b.tube("network", C.blue, [[cx + 8, 158, -21], [cx + 8, 163, -16], [cx + 8, 168, -19]], 0.8, 6);
      for (const y of [126, 96]) { b.box("io", C.dark, [cx, y - 15, -26], [70, 3, 4]); for (let i = 0; i < 9; i++) { b.box("io", C.black, [cx - 30 + i * 7.5, y, -24], [5.5, 26, 10]); led(b, "io", cx - 30 + i * 7.5, y + 10, -18.8, i === 6 ? C.orange : C.green); } }
      b.box("terminal", C.steel, [cx, 64, -26], [70, 2, 3]); for (let i = 0; i < 22; i++) b.box("terminal", i % 6 === 5 ? C.orange : C.blue, [cx - 31.5 + i * 3, 66, -23], [2.4, 9, 7]);
      for (const x of [-14, 14]) { b.box("psu", C.steel, [cx + x, 32, -23], [22, 26, 12]); led(b, "psu", cx + x, 40, -16.8, C.green); }
    });
    b.box("hmi", C.dark, [130, 70, 10], [80, 4, 50]);
    for (const x of [96, 164]) b.box("hmi", C.dark, [x, 34, 10], [4, 68, 44]);
    for (const x of [112, 148]) { b.box("hmi", C.black, [x, 98, -8], [32, 22, 2]); b.box("hmi", C.lcd, [x, 98, -6.8], [29, 19, 0.4]); b.box("hmi", C.dark, [x, 80, -8], [4, 14, 4]); }
    b.box("hmi", C.cab, [130, 73, 18], [40, 2, 12]);
    b.tube("network", C.yellow, [[0, 204, 0], [0, 220, 0], [130, 220, 0], [130, 72, -14]], 1, 6);
  });

  M("ips", "IPS — SIS cabinet(TMR) + ESD Matrix panel", {
    cabinet: "SIS cabinet", controller: "Safety controller(TMR, 2oo3)", io: "Safety I/O", psu: "Power supply", network: "Safety network", "bypass-panel": "Bypass/Reset key panel", "esd-pb": "ESD push button",
  }, ["cabinet"], (b) => {
    cabinet(b, 0, (b, cx) => {
      for (const x of [-24, 0, 24]) { b.box("controller", C.red, [cx + x, 176, -24], [18, 26, 10]); led(b, "controller", cx + x - 4, 184, -18.8, C.green); led(b, "controller", cx + x, 184, -18.8, C.green); }
      b.box("network", C.navy, [cx, 154, -25], [56, 8, 8]);
      for (const y of [126, 96]) for (let i = 0; i < 8; i++) { b.box("io", C.black, [cx - 28 + i * 8, y, -24], [6, 26, 10]); led(b, "io", cx - 28 + i * 8, y + 10, -18.8, C.green); }
      for (const x of [-14, 14]) { b.box("psu", C.steel, [cx + x, 40, -23], [22, 26, 12]); led(b, "psu", cx + x, 48, -16.8, C.green); }
    });
    b.box("bypass-panel", C.cab, [125, 60, 0], [70, 120, 30]);
    b.box("bypass-panel", C.steel, [125, 74, 15.5], [62, 70, 1]);
    for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) { b.cyl("bypass-panel", C.dark, "z", [102 + c * 15, 100 - r * 16, 16], 3.4, 3, 14); b.box("bypass-panel", C.white, [102 + c * 15, 100 - r * 16, 19.5], [1.2, 4, 0.6]); led(b, "bypass-panel", 102 + c * 15 + 6, 100 - r * 16 + 4, 16.4, r === 1 && c === 2 ? C.orange : C.green); }
    b.box("esd-pb", C.yellow, [125, 28, 16], [26, 26, 2]);
    b.lathe("esd-pb", C.red, "z", [125, 28, 17], [[0, 6], [3, 6], [4, 10], [8, 10], [9, 6]], 24);
    b.tube("network", C.red, [[0, 204, 0], [0, 216, 0], [125, 216, 0], [125, 120, 0]], 1, 6);
  });

  M("mms", "MMS — 축 진동·변위 감시(API 670) + Monitor rack", {
    shaft: "Shaft/Coupling hub", bearing: "Bearing housing", probe: "Radial proximity probe(X/Y)", "probe-axial": "Axial(Thrust) probe", keyphasor: "Keyphasor probe", rtd: "Bearing RTD", cable: "Extension cable", "monitor-rack": "Monitor rack",
  }, ["bearing"], (b) => {
    b.lathe("shaft", C.steel, "x", [-100, 0, 0], [[0, 8], [20, 8], [20, 14], [26, 14], [26, 8], [190, 8]], 24);
    b.lathe("shaft", C.dark, "x", [70, 0, 0], [[0, 18], [16, 18]], 28);
    b.box("shaft", C.black, [-77, 14, 0], [4, 1.4, 3]);
    for (const x of [-40, 40]) {
      b.lathe("bearing", C.body, "x", [x - 10, 0, 0], [[0, 9], [0, 22], [20, 22], [20, 9]], 28, { cap0: false, cap1: false });
      b.box("bearing", C.body, [x, -24, 0], [24, 14, 46]); b.box("bearing", C.dark, [x, -32, 0], [34, 3, 56]);
      for (const s of [1, -1]) { const d = [0, Math.SQRT1_2, s * Math.SQRT1_2]; b.cyl("probe", C.dark, d, mul(d, 20), 2.2, 20, 12); b.hex("probe", C.steel, d, mul(d, 30), 3.2, 3); b.tube("cable", C.cable, [mul(d, 40), add(mul(d, 46), [0, 10, 0]), [x, 64, -40]], 0.9, 6, { ends: false }); }
      b.cyl("rtd", C.copper, "y", [x + 6, 22, 0], 1.6, 10, 8);
    }
    b.cyl("keyphasor", C.orange, "-y", [-77, 40, 0], 2.2, 22, 12); b.hex("keyphasor", C.steel, "y", [-77, 28, 0], 3.2, 3);
    b.cyl("probe-axial", C.orange, "x", [-120, 10, 0], 2.2, 15, 12); b.box("probe-axial", C.dark, [-122, 0, 0], [4, 28, 10]);
    b.box("monitor-rack", C.dark, [0, 80, -50], [80, 34, 22]);
    for (let i = 0; i < 9; i++) { b.box("monitor-rack", C.black, [-34 + i * 8.5, 80, -38.6], [7, 30, 0.6]); led(b, "monitor-rack", -34 + i * 8.5, 90, -38, i === 4 ? C.orange : C.green); b.box("monitor-rack", C.blue, [-34 + i * 8.5, 74, -38], [2, 8 + (i % 3) * 3, 0.4]); }
  });

  M("ccs", "CCS — 원심 압축기 Anti-surge 루프", {
    compressor: "Centrifugal compressor", driver: "Driver(Motor/Turbine)", asv: "Anti-surge valve", "recycle-line": "Recycle line", "flow-element": "Flow element(Suction)", ft: "Flow(DP) transmitter", "pt-tt": "PT/TT (Suction/Discharge)", controller: "CCS controller", signal: "Control signal cable",
  }, [], (b) => {
    b.box("compressor", C.dark, [0, -46, 0], [240, 6, 90]);
    b.lathe("compressor", C.body, "x", [-40, 0, 0], [[0, 22], [8, 36], [72, 36], [80, 22]], 32);
    b.box("compressor", C.body, [0, -36, 0], [70, 14, 50]);
    for (const x of [-25, 25]) { b.cyl("compressor", C.body, "y", [x, 30, 0], 10, 14, 20); b.flange("compressor", [x, 44, 0], "y", 9, 15, 4, 0, 8); }
    b.lathe("driver", C.blue, "-x", [-50, 0, 0], [[0, 6], [10, 6], [10, 26], [70, 26], [74, 18]], 28);
    b.cyl("driver", C.dark, "x", [-50, 0, 0], 8, 10, 16);
    b.box("driver", C.dark, [-85, -32, 0], [60, 22, 40]);
    const S = [[-25, 56, 0], [-25, 80, 0], [-25, 80, -80]], D = [[25, 56, 0], [25, 80, 0], [25, 80, 80]];
    b.tube("recycle-line", C.steel, S, 7, 16); b.tube("recycle-line", C.steel, D, 7, 16);
    b.tube("recycle-line", C.orange, [[25, 80, 44], [25, 118, 44], [25, 118, 0], [-25, 118, 0], [-25, 118, -44], [-25, 80, -44]], 4, 12);
    b.sphere("asv", C.body, [0, 118, 0], 9, 20); b.cyl("asv", C.steel, "y", [0, 126, 0], 2, 12, 10);
    b.lathe("asv", C.blue, "y", [0, 136, 0], [[0, 6], [3, 18], [6, 20], [9, 18], [13, 6]], 24);
    b.box("asv", C.navy, [0, 130, 12], [12, 10, 6]);
    b.lathe("flow-element", C.steel, "z", [-25, 80, -62], [[0, 12], [4, 12]], 24);
    b.box("ft", C.blue, [-25, 100, -64], [10, 10, 8]); b.tube("ft", C.steel, [[-29, 92, -62], [-29, 86, -62]], 0.8, 6); b.tube("ft", C.steel, [[-21, 92, -66], [-21, 86, -66]], 0.8, 6);
    b.cyl("pt-tt", C.steel, "y", [-25, 87, -30], 1.6, 8, 8); b.box("pt-tt", C.blue, [-25, 98, -30], [8, 8, 8]);
    b.cyl("pt-tt", C.steel, "y", [25, 87, 30], 1.6, 8, 8); b.box("pt-tt", C.blue, [25, 98, 30], [8, 8, 8]);
    b.box("controller", C.cab, [120, 20, -50], [40, 130, 30]); b.box("controller", C.black, [120, 50, -34.6], [26, 16, 0.6]);
    for (let i = 0; i < 4; i++) led(b, "controller", 110 + i * 6, 64, -34.4, i === 2 ? C.orange : C.green);
    b.tube("signal", C.cable, [[0, 130, 15], [0, 150, 15], [120, 150, 15], [120, 86, -40]], 0.9, 6, { ends: false });
    b.tube("signal", C.cable, [[-25, 105, -64], [-25, 150, -64], [120, 150, -64]], 0.9, 6, { ends: false });
  });

  M("fgs", "FGS — 공정 구역 화재·가스 감지", {
    vessel: "Process vessel(참고)", "gas-detector": "Point gas detector(IR)", "op-gas": "Open-path gas detector", "flame-detector": "Flame detector(IR3)", mac: "Manual alarm call point", beacon: "Beacon/Horn", "fgs-panel": "FGS panel", cable: "Field cable",
  }, [], (b) => {
    b.box("vessel", C.concrete, [0, -3, 0], [240, 6, 170]);
    b.lathe("vessel", C.body, "y", [0, 0, 0], [[0, 0.01], [0, 30], [70, 30], [82, 18], [86, 0.01]], 28);
    b.box("vessel", C.dark, [0, 4, 0], [70, 8, 70]);
    for (const [x, z] of [[-80, -55], [80, -55], [-80, 55], [80, 55]]) {
      b.box("cable", C.dark, [x, 30, z], [3, 60, 3]);
      b.lathe("gas-detector", C.yellow, "-y", [x, 34, z + 4], [[0, 5], [10, 5], [12, 7], [16, 7]], 16);
    }
    b.box("op-gas", C.yellow, [-110, 18, 0], [8, 10, 10]); b.box("op-gas", C.yellow, [110, 18, 0], [8, 10, 10]);
    b.cyl("op-gas", C.red, "x", [-106, 18, 0], 0.5, 212, 6, { a: 0.45 });
    for (const [x, z, d] of [[-100, -70, [1, -0.4, 0.8]], [100, 70, [-1, -0.4, -0.8]]]) {
      b.box("flame-detector", C.dark, [x, 50, z], [3, 100, 3]);
      b.box("flame-detector", C.red, [x, 100, z], [12, 12, 12]); b.cyl("flame-detector", C.glass, d, [x, 100, z], 4, 8, 14);
    }
    b.box("mac", C.dark, [60, 20, 80], [3, 40, 3]); b.box("mac", C.red, [60, 42, 82], [10, 10, 4]); b.box("mac", C.white, [60, 42, 84.2], [6, 6, 0.4]);
    b.box("beacon", C.dark, [-60, 40, 80], [3, 80, 3]);
    b.lathe("beacon", C.red, "y", [-60, 80, 80], [[0, 5], [2, 5], [8, 4], [10, 0.01]], 16); b.lathe("beacon", C.dark, "z", [-60, 74, 82], [[0, 2], [5, 5]], 14);
    b.box("fgs-panel", C.cab, [150, 40, -70], [40, 80, 24]); b.box("fgs-panel", C.black, [150, 56, -57.6], [26, 14, 0.6]);
    for (let i = 0; i < 6; i++) led(b, "fgs-panel", 140 + i * 4, 40, -57.4, i === 3 ? C.red : C.green);
    b.tube("cable", C.cable, [[80, 60, -55], [80, 70, -70], [150, 70, -70]], 0.9, 6, { ends: false });
  });

  const DEVICE = ["ball-valve", "globe-valve", "butterfly-valve", "psv", "field-gauge", "transmitter", "bulk-material"];
  function build(id) {
    const m = MODELS[id]; if (!m) return null; if (m.faces) return m;
    const b = Builder(); m.fn(b); m.faces = b.faces;
    let lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
    for (const f of m.faces) for (const p of f.pts) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], p[k]); hi[k] = Math.max(hi[k], p[k]); }
    m.center = mul(add(lo, hi), 0.5); m.radius = len(sub(hi, lo)) / 2;
    return m;
  }

  /* ---------- 뷰어 ---------- */
  function Viewer(canvas, opts = {}) {
    const ctx = canvas.getContext("2d");
    const st = { yaw: -0.65, pitch: 0.42, zoom: 1, pan: [0, 0], model: null, xray: false, auto: true, hover: null, blink: {}, call: null, lastUser: 0, drawn: [] };
    const L = nrm([-0.45, 0.75, 0.55]);
    let raf = 0, dirty = true, W = 0, H = 0, dpr = 1;
    function resize() { const r = canvas.getBoundingClientRect(); dpr = Math.min(2, window.devicePixelRatio || 1); W = r.width; H = r.height; canvas.width = W * dpr; canvas.height = H * dpr; dirty = true; }
    function load(id) { const m = build(id); if (!m) return false; st.model = m; st.simS = m.sim ? JSON.parse(JSON.stringify(m.sim.init)) : null; st.zoom = 1; st.pan = [0, 0]; st.yaw = -0.65; st.pitch = 0.42; st.hover = null; dirty = true; opts.onLoad && opts.onLoad(m); return true; }
    function project() {
      const m = st.model; const cy = Math.cos(st.yaw), sy = Math.sin(st.yaw), cp = Math.cos(st.pitch), sp = Math.sin(st.pitch);
      const s = Math.min(W, H) * 0.44 / m.radius * st.zoom; const D = m.radius * 5; const c = m.center;
      const tr = (p) => { const x = p[0] - c[0], y = p[1] - c[1], z = p[2] - c[2]; const x1 = cy * x + sy * z, z1 = -sy * x + cy * z; const y2 = cp * y - sp * z1, z2 = sp * y + cp * z1; const f = D / (D - z2); return [W / 2 + st.pan[0] + x1 * s * f, H / 2 + st.pan[1] - y2 * s * f, z2]; };
      const rn = (n) => { const x1 = cy * n[0] + sy * n[2], z1 = -sy * n[0] + cy * n[2]; return [x1, cp * n[1] - sp * z1, sp * n[1] + cp * z1]; };
      return { tr, rn, s };
    }
    function draw(t) {
      const m = st.model; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
      const g = ctx.createRadialGradient(W / 2, H * 0.45, 10, W / 2, H / 2, Math.max(W, H) * 0.7); const cs = getComputedStyle(canvas); g.addColorStop(0, cs.getPropertyValue("--v3a").trim() || "#FFFFFF"); g.addColorStop(1, cs.getPropertyValue("--v3b").trim() || "#EEF1F7"); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      if (!m) return;
      const { tr, rn } = project();
      // 바닥 격자
      const fy = m.center[1] - m.radius * 0.62, R = m.radius * 1.1; ctx.lineWidth = 1; ctx.strokeStyle = "rgba(20,40,160,.07)";
      for (let i = -6; i <= 6; i++) { const k = i / 6 * R; let a = tr([m.center[0] + k, fy, m.center[2] - R]), b = tr([m.center[0] + k, fy, m.center[2] + R]); ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); a = tr([m.center[0] - R, fy, m.center[2] + k]); b = tr([m.center[0] + R, fy, m.center[2] + k]); ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); }
      const list = [];
      const shell = st.xray ? m.shell : [];
      const poses = m.sim && st.simS ? m.sim.pose(st.simS, t / 1000) || {} : {};
      for (const f of m.faces) {
        const q = poses[f.part]; if (q && q.hide) continue;
        const n = rn(q ? poseN(f.n, q) : f.n); const xr = shell.includes(f.part);
        if (n[2] < -0.12 && !xr) continue;
        const P = (q ? f.pts.map((p) => poseP(p, q)) : f.pts).map(tr); let z = 0; for (const p of P) z += p[2]; z /= P.length;
        list.push([z, f, P, n, xr, q]);
      }
      list.sort((a, b) => a[0] - b[0]);
      const drawn = []; const cp = [];
      for (const [, f, P, n, xr, q] of list) {
        if (st.call && f.part === st.call.part && !xr) { let cx = 0, cy2 = 0; for (const p of P) { cx += p[0]; cy2 += p[1]; } cp.push([cx / P.length, cy2 / P.length]); }
        let li = 0.42 + 0.58 * Math.max(0, n[0] * L[0] + n[1] * L[1] + n[2] * L[2]); li += 0.12 * Math.pow(Math.max(0, n[2]), 6);
        let [r, gg, bb] = (q && q.col) || f.col; r *= li; gg *= li; bb *= li;
        if (q && q.glow) { const gc = q.gcol || [255, 140, 30], k = Math.min(1, q.glow); r = r * (1 - k) + gc[0] * k; gg = gg * (1 - k) + gc[1] * k; bb = bb * (1 - k) + gc[2] * k; }
        const bl = st.blink[f.part]; let a = xr ? 0.16 : f.a;
        if (bl) { const k = 0.5 + 0.5 * Math.sin((t - bl) / 140); r = r * (1 - k) + 40 * k; gg = gg * (1 - k) + 110 * k; bb = bb * (1 - k) + 255 * k; a = Math.max(a, 0.9); }
        else if (st.hover === f.part) { r = r * 0.7 + 20 * 0.3; gg = gg * 0.7 + 40 * 0.3; bb = bb * 0.7 + 160 * 0.3 + 30; }
        const c = `rgba(${r | 0},${gg | 0},${Math.min(255, bb) | 0},${a})`;
        const path = new Path2D(); path.moveTo(P[0][0], P[0][1]); for (let i = 1; i < P.length; i++) path.lineTo(P[i][0], P[i][1]); path.closePath();
        ctx.fillStyle = c; ctx.fill(path); if (a > 0.6) { ctx.strokeStyle = c; ctx.lineWidth = 0.6; ctx.stroke(path); }
        drawn.push([path, f.part, xr]);
      }
      st.drawn = drawn;
      if (st.call && cp.length) {
        let mx = 0, my = 0; for (const c of cp) { mx += c[0]; my += c[1]; } mx /= cp.length; my /= cp.length;
        let tip = cp[0], bd = 1e18; for (const c of cp) { const d = (c[0] - mx) ** 2 + (c[1] - my) ** 2; if (d < bd) { bd = d; tip = c; } }
        const age = (t - st.call.t) / 1000; const al = age > 8 ? Math.max(0, 1 - (age - 8) / 1.5) : 1;
        if (al <= 0) st.call = null; else {
          const txt = (m.parts[st.call.part] || st.call.part); ctx.save(); ctx.globalAlpha = al; ctx.font = "600 13px 'Malgun Gothic',system-ui,sans-serif";
          const tw = ctx.measureText(txt).width + 20, th = 26, bob = Math.sin(t / 220) * 3;
          const right = tip[0] < W * 0.55; const lx = right ? Math.min(W - tw - 6, tip[0] + 60) : Math.max(6, tip[0] - 60 - tw);
          const ly = Math.max(6, Math.min(H - th - 6, tip[1] - 70)); const ax = right ? lx : lx + tw, ay = ly + th / 2;
          const ex = tip[0] + (ax < tip[0] ? -3 : 3) * 0 , ey = tip[1] - bob * 0;
          const ang = Math.atan2(ey - ay, ex - ax), hx = ex - Math.cos(ang) * 4 - Math.cos(ang) * bob, hy = ey - Math.sin(ang) * 4 - Math.sin(ang) * bob;
          ctx.strokeStyle = "#ff3b30"; ctx.fillStyle = "#ff3b30"; ctx.lineWidth = 2.5; ctx.lineCap = "round";
          ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(hx, hy); ctx.stroke();
          ctx.beginPath(); ctx.moveTo(hx, hy); ctx.lineTo(hx - 13 * Math.cos(ang - 0.4), hy - 13 * Math.sin(ang - 0.4)); ctx.lineTo(hx - 13 * Math.cos(ang + 0.4), hy - 13 * Math.sin(ang + 0.4)); ctx.closePath(); ctx.fill();
          ctx.beginPath(); ctx.arc(ex, ey, 3, 0, 7); ctx.fill();
          ctx.beginPath(); if (ctx.roundRect) ctx.roundRect(lx, ly, tw, th, 7); else ctx.rect(lx, ly, tw, th); ctx.fillStyle = "#ff3b30"; ctx.fill();
          ctx.fillStyle = "#fff"; ctx.textBaseline = "middle"; ctx.fillText(txt, lx + 10, ly + th / 2 + 1); ctx.restore();
        }
      }
      if (m.sim && m.sim.overlay && st.simS) { ctx.save(); m.sim.overlay(ctx, W, H, st.simS, getComputedStyle(canvas)); ctx.restore(); }
    }
    let lastT = 0, lastRO = 0;
    function frame(t) {
      raf = 0; const now = t; const dt = Math.min(0.05, lastT ? (t - lastT) / 1000 : 0.016); lastT = t;
      const sim = st.model && st.model.sim && st.simS;
      if (sim) { st.model.sim.update(st.simS, dt, now / 1000); dirty = true; if (now - lastRO > 120) { lastRO = now; opts.onSim && opts.onSim(st.model.sim.readout(st.simS)); } }
      const blinking = Object.keys(st.blink).some((k) => now - st.blink[k] < 2600 || (delete st.blink[k], false));
      const idle = st.auto && now - st.lastUser > 3500;
      if (idle) { st.yaw += 0.0035; dirty = true; }
      if (dirty || blinking || st.call) { draw(now); dirty = false; }
      if ((idle || blinking || sim || st.call) && visible()) raf = requestAnimationFrame(frame); else lastT = 0;
    }
    const visible = () => canvas.offsetParent !== null;
    const kick = () => { dirty = true; if (!raf) raf = requestAnimationFrame(frame); };
    function pick(x, y) { ctx.setTransform(dpr, 0, 0, dpr, 0, 0); for (let i = st.drawn.length - 1; i >= 0; i--) { const [p, part, xr] = st.drawn[i]; if (xr) continue; if (ctx.isPointInPath(p, x * dpr, y * dpr)) return part; } return null; }
    // 입력
    let drag = null;
    canvas.addEventListener("contextmenu", (e) => e.preventDefault());
    canvas.addEventListener("pointerdown", (e) => { canvas.setPointerCapture(e.pointerId); drag = { x: e.clientX, y: e.clientY, b: e.button, sh: e.shiftKey, moved: 0 }; st.lastUser = performance.now(); });
    canvas.addEventListener("pointermove", (e) => {
      const r = canvas.getBoundingClientRect();
      if (drag) {
        const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY; drag.moved += Math.abs(dx) + Math.abs(dy);
        if (drag.b === 2 || drag.sh) { st.pan[0] += dx; st.pan[1] += dy; } else { st.yaw += dx * 0.009; st.pitch = Math.max(-1.45, Math.min(1.45, st.pitch + dy * 0.009)); }
        st.lastUser = performance.now(); kick();
      } else {
        const p = pick(e.clientX - r.left, e.clientY - r.top); if (p !== st.hover) { st.hover = p; kick(); opts.onHover && opts.onHover(p, e.clientX - r.left, e.clientY - r.top); }
        else if (p) opts.onHover && opts.onHover(p, e.clientX - r.left, e.clientY - r.top);
      }
    });
    canvas.addEventListener("pointerup", (e) => { if (drag && drag.moved < 4) { const r = canvas.getBoundingClientRect(); const p = pick(e.clientX - r.left, e.clientY - r.top); if (p) { blink(p); opts.onPick && opts.onPick(p); } } drag = null; });
    canvas.addEventListener("pointerleave", () => { if (st.hover) { st.hover = null; kick(); opts.onHover && opts.onHover(null); } });
    canvas.addEventListener("wheel", (e) => { e.preventDefault(); st.zoom = Math.max(0.35, Math.min(6, st.zoom * Math.exp(-e.deltaY * 0.0015))); st.lastUser = performance.now(); kick(); }, { passive: false });
    canvas.addEventListener("dblclick", () => { st.zoom = 1; st.pan = [0, 0]; st.yaw = -0.65; st.pitch = 0.42; kick(); });
    function blink(part) { st.blink[part] = performance.now(); st.call = { part, t: performance.now() }; st.lastUser = performance.now(); kick(); }
    new ResizeObserver(() => { resize(); kick(); }).observe(canvas);
    resize();
    return {
      load: (id) => { const ok = load(id); kick(); return ok; }, blink, kick,
      set xray(v) { st.xray = v; kick(); }, get xray() { return st.xray; },
      set auto(v) { st.auto = v; st.lastUser = 0; kick(); }, get auto() { return st.auto; },
      reset: () => { st.zoom = 1; st.pan = [0, 0]; st.yaw = -0.65; st.pitch = 0.42; kick(); },
      zoomBy: (k) => { st.zoom = Math.max(0.35, Math.min(6, st.zoom * k)); kick(); },
      get model() { return st.model; },
      get sim() { return st.simS; },
      simSet: (k, v) => { if (st.simS) { st.simS[k] = v; kick(); } },
      simAct: (a) => { const m = st.model; if (m && m.sim && m.sim.act && m.sim.act[a]) { m.sim.act[a](st.simS); kick(); } },
    };
  }
  G.V3D = { MODELS, build, Viewer, DEVICE };
})(typeof window !== "undefined" ? window : globalThis);
