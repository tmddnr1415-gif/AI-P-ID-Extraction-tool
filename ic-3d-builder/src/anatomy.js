/* Anatomy — parametric, part-by-part 3D definitions of I&C items.
 *
 * One item = parameter list + build(values) → list of parts.
 * One part = named primitives + engineering data (item no., function, typical
 * material, qty, size-linked dimensions) + explode offset/stage.
 * Pure data, no three.js: shared by the browser viewer, Node CLI and the Claude skill.
 *
 * Coordinates: mm, Y up.
 *   valve   — origin = valve centre on the pipe centreline, pipe axis = X
 *   cabinet — origin = floor level, front-bottom-centre of the first bay, front = +Z
 *   hookup  — origin = floor (Y=0) under the process tap, process pipe axis = X
 *
 * Dimension sources:
 *   drawing  — read from the GA / dimensional drawing (with evidence)
 *   user     — typed by the user
 *   standard — built-in reference table (RefData) — not yet verified against the source standard
 *   estimate — proportional estimate; shape reference only
 */
'use strict';

const Anatomy = (() => {
  const R = (typeof RefData !== 'undefined') ? RefData
    : (typeof require !== 'undefined' ? require('./refdata.js') : null);

  // ───────────────────────── primitives ─────────────────────────
  const cyl = (axis, r, h, at, extra = {}) => ({ k: 'cyl', axis, r, h, at, ...extra });
  const cone = (axis, r, r2, h, at) => ({ k: 'cyl', axis, r, r2, h, at });
  const ring = (axis, ri, ro, h, at) => ({ k: 'ring', axis, ri, ro, h, at });
  const helix = (axis, Rh, r, h, turns, at) => ({ k: 'helix', axis, R: Rh, r, h, turns, at });
  const box = (s, at, extra = {}) => ({ k: 'box', s, at, ...extra });
  const sph = (r, at, scale) => ({ k: 'sph', r, at, ...(scale ? { scale } : {}) });
  const tor = (R0, r, axis, at) => ({ k: 'tor', R: R0, r, axis, at });
  const tube = (a, b, r) => ({ k: 'tube', a, b, r });
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const r1 = (x) => Math.round(x * 10) / 10;

  /**
   * Part constructor.
   * o: { group, stage (0 moves first … 2 last), ex [dx,dy,dz] explode offset in mm,
   *      fn (function), material (typical), qty, dims [{k, v, unit, src}], note }
   */
  function P(id, name, look, prims, o = {}) {
    return {
      id, name, look, prims,
      group: o.group || '', stage: o.stage ?? 1, ex: o.ex || [0, 0, 0],
      fn: o.fn || '', material: o.material || '', qty: o.qty ?? 1, dims: o.dims || [], note: o.note || '',
      no: null,
    };
  }
  const D = (k, v, unit = 'mm', src = 'estimate') => ({ k, v: typeof v === 'number' ? r1(v) : v, unit, src });

  const AX = { x: [1, 0, 0], y: [0, 1, 0], z: [0, 0, 1] };
  const along = (axis, d, base = [0, 0, 0]) => base.map((b, i) => b + AX[axis][i] * d);
  const perp = { x: [[0, 1, 0], [0, 0, 1]], y: [[1, 0, 0], [0, 0, 1]], z: [[1, 0, 0], [0, 1, 0]] };
  /** n points on a circle of radius rc around `axis` through `c` */
  function circle(axis, rc, n, c, phase = 0.5) {
    const [u, w] = perp[axis];
    const out = [];
    for (let i = 0; i < n; i++) {
      const a = (i + phase) / n * Math.PI * 2;
      out.push([0, 1, 2].map((j) => c[j] + (u[j] * Math.cos(a) + w[j] * Math.sin(a)) * rc));
    }
    return out;
  }

  const FRAC = { 0.5: '1/2', 0.75: '3/4', 1: '1', 1.5: '1-1/2', 2: '2', 2.5: '2-1/2', 3: '3', 4: '4', 6: '6', 8: '8', 10: '10', 12: '12' };
  const npsTxt = (n) => `${FRAC[n] || n}"`;
  const inch = (mm) => `${Math.round(mm / 25.4 * 8) / 8}"`;

  // ───────────────────────── bounding boxes ─────────────────────────
  function primBox(pr) {
    if (pr.k === 'tube') {
      return [[0, 1, 2].map((i) => Math.min(pr.a[i], pr.b[i]) - pr.r), [0, 1, 2].map((i) => Math.max(pr.a[i], pr.b[i]) + pr.r)];
    }
    let e;
    if (pr.k === 'box') {
      const ry = pr.ry || 0;
      e = [Math.abs(Math.cos(ry)) * pr.s[0] / 2 + Math.abs(Math.sin(ry)) * pr.s[2] / 2, pr.s[1] / 2,
        Math.abs(Math.sin(ry)) * pr.s[0] / 2 + Math.abs(Math.cos(ry)) * pr.s[2] / 2];
    } else if (pr.k === 'cyl' || pr.k === 'ring' || pr.k === 'helix') {
      const r = pr.k === 'ring' ? pr.ro : pr.k === 'helix' ? pr.R + pr.r : Math.max(pr.r, pr.r2 ?? pr.r);
      e = [r, r, r]; e['xyz'.indexOf(pr.axis)] = pr.h / 2 + (pr.k === 'helix' ? pr.r : 0);
    } else if (pr.k === 'sph') {
      const s = pr.scale || [1, 1, 1]; e = s.map((k) => pr.r * k);
    } else if (pr.k === 'tor') {
      const o = pr.R + pr.r; e = [o, o, o]; e['xyz'.indexOf(pr.axis)] = pr.r;
    }
    return [pr.at.map((c, i) => c - e[i]), pr.at.map((c, i) => c + e[i])];
  }
  function partBox(p) {
    const lo = [Infinity, Infinity, Infinity]; const hi = [-Infinity, -Infinity, -Infinity];
    for (const pr of p.prims) {
      const [a, b] = primBox(pr);
      for (let i = 0; i < 3; i++) { lo[i] = Math.min(lo[i], a[i]); hi[i] = Math.max(hi[i], b[i]); }
    }
    return { min: lo, max: hi };
  }
  function bboxOf(parts, filter = (p) => p.look !== 'ghost' && p.look !== 'clear', exploded = 0) {
    const lo = [Infinity, Infinity, Infinity]; const hi = [-Infinity, -Infinity, -Infinity];
    for (const p of parts) {
      if (!filter(p)) continue;
      const b = partBox(p); const off = p.ex.map((x) => x * exploded);
      for (let i = 0; i < 3; i++) { lo[i] = Math.min(lo[i], b.min[i] + off[i]); hi[i] = Math.max(hi[i], b.max[i] + off[i]); }
    }
    return { min: lo, max: hi, size: hi.map((h, i) => h - lo[i]) };
  }

  /** Lay parts out in an exploded column along `axis` starting at `start` with `gap` between them (sets p.ex). */
  function stack(parts, axis, start, gap, sign = 1) {
    const i = 'xyz'.indexOf(axis);
    let cur = start;
    for (const p of parts) {
      const b = partBox(p);
      const len = b.max[i] - b.min[i];
      const c = (b.max[i] + b.min[i]) / 2;
      p.ex = p.ex.slice(); p.ex[i] += cur + sign * len / 2 - c;
      cur += sign * (len + gap);
    }
    return cur;
  }

  // ───────────────────────── parameters ─────────────────────────
  const BODY = ['globe', 'gate', 'ball', 'butterfly', 'psv'];
  const OPERATOR = ['handwheel', 'lever', 'gear', 'pneumatic_diaphragm', 'pneumatic_rotary', 'electric', 'spring'];
  const flg = (v) => R.flangeOf(v.nps, v.cls);
  const pipeID = (nps) => { const od = R.pipeOD[R.nearestNps(nps)]; return od - 2 * clamp(0.055 * od + 1.5, 2.8, 12.7); };

  const VALVE_PARAMS = [
    { key: 'tag', label: 'Tag No.', type: 'text', default: '', group: 'Identification' },
    { key: 'body', label: 'Body type', type: 'enum', options: BODY, default: 'globe', group: 'Configuration',
      desc: 'globe / gate / ball / butterfly / psv (angle-pattern spring-loaded safety valve)' },
    { key: 'operator', label: 'Operator', type: 'enum', options: OPERATOR, default: 'pneumatic_diaphragm', group: 'Configuration',
      desc: 'handwheel, lever, gear (worm gear), pneumatic_diaphragm (spring & diaphragm CV), pneumatic_rotary (rack & pinion / scotch yoke), electric (MOV), spring (PSV)' },
    { key: 'service', label: 'Service', type: 'enum', options: ['control', 'on_off'], default: 'control', group: 'Configuration',
      desc: 'control → globe face-to-face per ISA-75.08.01 and cage-guided trim' },
    { key: 'nps', label: 'Size NPS (inlet)', unit: 'in', type: 'num', default: 4, min: 0.5, max: 12, step: 0.25, group: 'Configuration' },
    { key: 'cls', label: 'Pressure class (inlet)', type: 'enum', options: ['150', '300'], default: '150', group: 'Configuration' },
    { key: 'outlet_nps', label: 'Outlet NPS', unit: 'in', type: 'num', group: 'Configuration', when: (v) => v.body === 'psv',
      est: (v) => R.NPS.map(Number).find((n) => n >= v.nps * 1.5) || 12 },
    { key: 'outlet_cls', label: 'Outlet class', type: 'enum', options: ['150', '300'], default: '150', group: 'Configuration',
      when: (v) => v.body === 'psv' },
    { key: 'bore', label: 'Ball bore', type: 'enum', options: ['full', 'reduced'], default: 'full', group: 'Configuration',
      when: (v) => v.body === 'ball' },

    { key: 'ftf', label: 'Face-to-face', unit: 'mm', type: 'num', group: 'Body', when: (v) => v.body !== 'psv',
      std: (v) => {
        const kind = v.body === 'globe' && v.service === 'control' ? 'control_globe' : v.body;
        const val = R.ftfOf(kind, v.nps, v.cls);
        return val ? { value: val, ref: R.SOURCES[kind] } : null;
      }, desc: 'Flange face to flange face' },
    { key: 'cti', label: 'Centre to inlet face', unit: 'mm', type: 'num', group: 'Body', when: (v) => v.body === 'psv',
      est: (v) => Math.round(85 + 28 * v.nps), desc: 'Outlet centreline to inlet flange face (vertical)' },
    { key: 'cto', label: 'Centre to outlet face', unit: 'mm', type: 'num', group: 'Body', when: (v) => v.body === 'psv',
      est: (v) => Math.round(95 + 32 * v.nps), desc: 'Inlet centreline to outlet flange face (horizontal)' },
    { key: 'body_h', label: 'Body height (CL → bonnet face)', unit: 'mm', type: 'num', group: 'Body',
      est: (v) => {
        const f = flg(v);
        return Math.round({ globe: 0.55 * f.od + 20, gate: 0.85 * f.od + 20, ball: 0.62 * f.od + 25,
          butterfly: 0.55 * f.od + 60, psv: 1.0 * f.od }[v.body]);
      } },
    { key: 'body_w', label: 'Body max. width', unit: 'mm', type: 'num', group: 'Body',
      est: (v) => {
        const f = flg(v);
        return Math.round({ globe: 0.95 * f.od, gate: 0.75 * f.od, ball: 1.0 * f.od, butterfly: 0.95 * f.od, psv: 0.9 * f.od }[v.body]);
      } },
    { key: 'bonnet_h', label: 'Bonnet / neck height', unit: 'mm', type: 'num', group: 'Body',
      est: (v) => Math.round({ globe: 70 + 25 * v.nps, gate: 90 + 45 * v.nps, ball: 40 + 12 * v.nps,
        butterfly: 40 + 10 * v.nps, psv: 160 + 70 * v.nps }[v.body]),
      desc: 'Bonnet flange to yoke/operator mounting face (PSV: spring bonnet height)' },
    { key: 'port_d', label: 'Port / seat bore', unit: 'mm', type: 'num', group: 'Trim',
      est: (v) => {
        const id = pipeID(v.nps);
        return Math.round({ globe: v.service === 'control' ? 0.78 * id : 0.85 * id, gate: id,
          ball: v.bore === 'reduced' ? 0.72 * id : id, butterfly: id, psv: 0.5 * id }[v.body]);
      }, desc: 'Seat ring bore / ball bore / nozzle bore' },
    { key: 'stem_d', label: 'Stem / shaft diameter', unit: 'mm', type: 'num', group: 'Trim',
      est: (v) => Math.round({ globe: clamp(9.5 + 3.2 * v.nps, 9.5, 50), gate: clamp(16 + 4 * v.nps, 16, 70),
        ball: clamp(12 + 4.5 * v.nps, 12, 90), butterfly: clamp(12 + 4 * v.nps, 12, 90), psv: clamp(12 + 5 * v.nps, 12, 60) }[v.body]) },
    { key: 'pipe_stub', label: 'Reference pipe length', unit: 'mm', type: 'num', default: 150, group: 'Body', desc: '0 = hide' },

    { key: 'yoke_h', label: 'Yoke / bracket height', unit: 'mm', type: 'num', group: 'Operator',
      when: (v) => ['pneumatic_diaphragm', 'pneumatic_rotary', 'electric', 'handwheel', 'gear'].includes(v.operator),
      est: (v) => Math.round({ pneumatic_diaphragm: 150 + 45 * v.nps, pneumatic_rotary: 60 + 10 * v.nps,
        electric: 90 + 25 * v.nps, handwheel: v.body === 'gate' ? 120 + 70 * v.nps : 60 + 20 * v.nps,
        gear: 50 + 10 * v.nps }[v.operator] || 100) },
    { key: 'act_d', label: 'Actuator diameter / width', unit: 'mm', type: 'num', group: 'Operator',
      when: (v) => ['pneumatic_diaphragm', 'pneumatic_rotary', 'electric', 'gear'].includes(v.operator),
      est: (v) => Math.round({ pneumatic_diaphragm: clamp(200 + 55 * v.nps, 220, 600),
        pneumatic_rotary: clamp(80 + 18 * v.nps, 90, 320), electric: clamp(230 + 15 * v.nps, 240, 450),
        gear: clamp(110 + 18 * v.nps, 120, 340) }[v.operator]) },
    { key: 'act_h', label: 'Actuator height', unit: 'mm', type: 'num', group: 'Operator',
      when: (v) => ['pneumatic_diaphragm', 'electric', 'gear'].includes(v.operator),
      est: (v) => Math.round({ pneumatic_diaphragm: clamp(110 + 30 * v.nps, 130, 380),
        electric: clamp(300 + 18 * v.nps, 320, 560), gear: clamp(90 + 12 * v.nps, 100, 260) }[v.operator]) },
    { key: 'act_l', label: 'Cylinder length (rotary)', unit: 'mm', type: 'num', group: 'Operator',
      when: (v) => v.operator === 'pneumatic_rotary', est: (v) => Math.round(clamp(240 + 60 * v.nps, 260, 900)) },
    { key: 'hw_d', label: 'Handwheel diameter', unit: 'mm', type: 'num', group: 'Operator',
      when: (v) => ['handwheel', 'electric', 'gear'].includes(v.operator) || (v.operator === 'pneumatic_diaphragm' && v.cv_handwheel),
      est: (v) => Math.round(clamp(100 + 40 * v.nps, 100, 610)) },
    { key: 'lever_l', label: 'Lever length', unit: 'mm', type: 'num', group: 'Operator',
      when: (v) => v.operator === 'lever', est: (v) => Math.round(clamp(120 + 60 * v.nps, 120, 700)) },
    { key: 'stem_ext', label: 'Stem rise (rising stem, open)', unit: 'mm', type: 'num', group: 'Operator',
      when: (v) => v.operator === 'handwheel' && v.body === 'gate', est: (v) => Math.round(25.4 * v.nps * 1.05) },
    { key: 'positioner', label: 'Positioner', type: 'bool', default: true, group: 'Operator',
      when: (v) => ['pneumatic_diaphragm', 'pneumatic_rotary'].includes(v.operator) },
    { key: 'cv_handwheel', label: 'Top-mounted handwheel', type: 'bool', default: false, group: 'Operator',
      when: (v) => v.operator === 'pneumatic_diaphragm' },
    { key: 'psv_lever', label: 'Lifting lever', type: 'bool', default: false, group: 'Operator', when: (v) => v.body === 'psv' },
    { key: 'overall_h', label: 'Overall height (CL → top)', unit: 'mm', type: 'num', group: 'Check',
      desc: 'If the drawing only gives the overall height, enter it here: estimated heights are scaled to match' },
  ];

  const CAB_PARAMS = [
    { key: 'tag', label: 'Cabinet No.', type: 'text', default: '', group: 'Identification' },
    { key: 'bays', label: 'Number of bays', type: 'num', default: 1, min: 1, max: 10, step: 1, group: 'Envelope' },
    { key: 'w', label: 'Width W (per bay)', unit: 'mm', type: 'num', default: 800, group: 'Envelope' },
    { key: 'h', label: 'Height H (excl. plinth)', unit: 'mm', type: 'num', default: 2000, group: 'Envelope' },
    { key: 'd', label: 'Depth D', unit: 'mm', type: 'num', default: 800, group: 'Envelope' },
    { key: 'plinth_h', label: 'Plinth height', unit: 'mm', type: 'num', default: 100, group: 'Envelope' },
    { key: 'doors', label: 'Front doors per bay', type: 'enum', options: ['1', '2'], default: '1', group: 'Doors',
      est: (v) => (v.w >= 1000 ? '2' : '1') },
    { key: 'rear_door', label: 'Rear door', type: 'bool', default: true, group: 'Doors' },
    { key: 'door_open', label: 'Door opening angle', unit: '°', type: 'num', default: 0, min: 0, max: 180, step: 5, group: 'Doors' },
    { key: 'louvers', label: 'Door louvres / filter fans', type: 'bool', default: true, group: 'Accessories' },
    { key: 'fan', label: 'Roof fan', type: 'bool', default: false, group: 'Accessories' },
    { key: 'lifting_eyes', label: 'Lifting eye bolts', type: 'bool', default: true, group: 'Accessories' },
    { key: 'mounting_plate', label: 'Mounting plate', type: 'bool', default: true, group: 'Interior' },
    { key: 'modules', label: 'DIN rail / I/O rows', type: 'num', default: 4, min: 0, max: 12, step: 1, group: 'Interior' },
    { key: 'gland_plate', label: 'Bottom gland plate', type: 'bool', default: true, group: 'Accessories' },
    { key: 'clearance', label: 'Front maintenance clearance', unit: 'mm', type: 'num', default: 1000, group: 'Check', desc: '0 = hide' },
  ];

  const HOOK_PARAMS = [
    { key: 'tag', label: 'Tag No.', type: 'text', default: '', group: 'Identification' },
    { key: 'inst', label: 'Instrument', type: 'enum', options: ['PT', 'DPT', 'LT_DP', 'FT_DP'], default: 'PT', group: 'Configuration',
      desc: 'PT = pressure, DPT = differential pressure, LT_DP = DP level (two vessel nozzles), FT_DP = DP flow (orifice taps)' },
    { key: 'service', label: 'Fluid', type: 'enum', options: ['gas', 'liquid', 'steam'], default: 'liquid', group: 'Configuration',
      desc: 'gas → instrument above tap; liquid/steam → instrument below tap' },
    { key: 'proc_nps', label: 'Process pipe NPS', unit: 'in', type: 'num', default: 6, min: 0.5, max: 24, group: 'Process' },
    { key: 'pipe_el', label: 'Pipe centreline elevation', unit: 'mm', type: 'num', default: 2500, group: 'Process' },
    { key: 'tap', label: 'Tap orientation', type: 'enum', options: ['top', 'side', 'bottom', 'side45'], group: 'Process',
      est: (v) => (v.service === 'gas' ? 'top' : 'side') },
    { key: 'tap_sep', label: 'HP–LP tap separation', unit: 'mm', type: 'num', group: 'Process',
      when: (v) => v.inst !== 'PT', est: (v) => (v.inst === 'LT_DP' ? 2000 : 110),
      desc: 'DP flow: orifice flange tap spacing; DP level: nozzle elevation difference' },
    { key: 'mount', label: 'Mounting', type: 'enum', options: ['stand', 'close_coupled'], default: 'stand', group: 'Installation' },
    { key: 'stand_h', label: 'Stand height', unit: 'mm', type: 'num', default: 1200, group: 'Installation', when: (v) => v.mount === 'stand' },
    { key: 'stand_dx', label: 'Stand offset X (along pipe)', unit: 'mm', type: 'num', default: 600, group: 'Installation', when: (v) => v.mount === 'stand' },
    { key: 'stand_dz', label: 'Stand offset Z (from pipe)', unit: 'mm', type: 'num', default: 700, group: 'Installation', when: (v) => v.mount === 'stand' },
    { key: 'tube_od', label: 'Impulse tube OD', unit: 'mm', type: 'num', default: 12.7, group: 'Tubing' },
    { key: 'slope', label: 'Tubing slope', unit: '1:x', type: 'num', default: 12, group: 'Tubing', desc: 'Minimum slope of horizontal runs; 1:12 is typical' },
    { key: 'root_valve', label: 'Root valve', type: 'bool', default: true, group: 'Valves' },
    { key: 'manifold', label: 'Manifold', type: 'enum', options: ['none', '2V', '3V', '5V'], group: 'Valves',
      est: (v) => (v.inst === 'PT' ? '2V' : '5V') },
    { key: 'drain', label: 'Drain / vent valve', type: 'bool', default: true, group: 'Valves' },
    { key: 'sunshade', label: 'Sunshade', type: 'bool', default: false, group: 'Accessories' },
  ];

  // ───────────────────────── resolve values (with source) ─────────────────────────
  function resolve(typeId, inputs = {}) {
    const T = TYPES[typeId];
    const v = {}; const meta = {};
    const get = (k) => {
      const x = inputs[k];
      if (x === undefined || x === null || x === '') return null;
      if (typeof x === 'object' && 'value' in x) {
        if (x.value === undefined || x.value === null || x.value === '') return null;
        return x;
      }
      return { value: x, src: 'user' };
    };
    const norm = (p, val) => {
      if (p.type === 'num') return Number(val);
      if (p.type === 'bool') return val === true || val === 'true' || val === 1;
      return String(val);
    };
    for (let pass = 0; pass < 2; pass++) {
      for (const p of T.params) {
        const given = get(p.key);
        if (given) {
          v[p.key] = norm(p, given.value);
          meta[p.key] = { src: given.src || 'user', evidence: given.evidence, confidence: given.confidence };
          continue;
        }
        let s = null;
        try { s = p.std ? p.std(v) : null; } catch { s = null; }
        if (s && s.value != null) { v[p.key] = norm(p, s.value); meta[p.key] = { src: 'standard', ref: s.ref }; continue; }
        let e;
        try { e = p.est ? p.est(v) : undefined; } catch { e = undefined; }
        if (e !== undefined && e !== null && !Number.isNaN(e)) { v[p.key] = norm(p, e); meta[p.key] = { src: 'estimate' }; continue; }
        if (p.default !== undefined) { v[p.key] = norm(p, p.default); meta[p.key] = { src: 'default' }; continue; }
        v[p.key] = undefined; meta[p.key] = { src: 'none' };
      }
    }
    for (const p of T.params) meta[p.key].active = !p.when || !!p.when(v);
    if (T.fit) T.fit(v, meta);
    return { values: v, meta };
  }

  /** Scale estimated heights so the model matches an overall height read from the drawing. */
  function fitValve(v, meta) {
    if (!(v.overall_h > 0) || !meta.overall_h || !['drawing', 'user'].includes(meta.overall_h.src)) return;
    const keys = ['body_h', 'bonnet_h', 'yoke_h', 'act_h', 'stem_ext'];
    const top = bboxOf(buildValve(v, meta), () => true).max[1];
    if (!(top > 0)) return;
    const fixed = keys.filter((k) => meta[k]?.active && v[k] > 0 && meta[k].src !== 'estimate').reduce((s, k) => s + v[k], 0);
    const scalable = keys.filter((k) => meta[k]?.active && v[k] > 0 && meta[k].src === 'estimate');
    const scal = scalable.reduce((s, k) => s + v[k], 0);
    const extra = top - fixed - scal;
    if (scal <= 0) return;
    const k = (v.overall_h - fixed - extra) / scal;
    if (!(k > 0.3 && k < 3)) return;
    for (const key of scalable) {
      v[key] = Math.round(v[key] * k);
      meta[key] = { ...meta[key], src: 'estimate', ref: `scaled ×${k.toFixed(2)} to overall height ${v.overall_h}` };
    }
  }

  // ───────────────────────── valve: shared pieces ─────────────────────────
  function handwheelPart(id, at, d, axis = 'y', o = {}) {
    const rim = Math.max(6, d * 0.04);
    const prims = [tor(d / 2 - rim, rim, axis, at), cyl(axis, d * 0.08, rim * 2.4, at)];
    for (const e of circle(axis, d / 2 - rim, 3, at, 0)) prims.push(tube(at, e, rim * 0.55));
    return P(id, o.name || 'Handwheel', 'wheel', prims, {
      group: o.group || 'Manual operator', stage: o.stage ?? 0, ex: o.ex,
      fn: o.fn || 'Manual operation of the valve stem; rim force is kept within MSS SP-91 / EN 12570 limits.',
      material: 'Ductile iron or carbon steel, painted', dims: [D('Diameter', d, 'mm', o.src || 'estimate')],
    });
  }

  function bodyFlanges(prims, axis, sign, face, f) {
    const c = (d) => along(axis, sign * d);
    prims.push(cyl(axis, f.od / 2, f.t, c(face - f.t / 2)));
    prims.push(cyl(axis, f.pipeOD / 2 * 1.35, f.t * 1.1, c(face - f.t - f.t * 0.55)));
  }

  function flangeBolting(id, name, axis, sign, face, f, exDist) {
    const prims = [];
    for (const p of circle(axis, f.bcd / 2, f.n, [0, 0, 0])) {
      const base = along(axis, sign * (face - f.t / 2 + f.bolt * 0.3), p);
      prims.push(cyl(axis, f.bolt / 2, f.t + f.bolt * 1.6, base));
      prims.push(cyl(axis, f.bolt * 0.85, f.bolt * 0.85, along(axis, sign * (f.t / 2 + f.bolt * 0.9), base)));
    }
    return P(id, name, 'bolt', prims, {
      group: 'Piping interface', stage: 0, ex: along(axis, sign * exDist), qty: f.n,
      fn: 'Stud bolts and heavy hex nuts clamping the valve end flange to the mating pipe flange (supplied by piping).',
      material: 'ASTM A193 B7 studs / A194 2H nuts',
      dims: [D('Bolts', `${f.n} × ${inch(f.bolt)}`, '', 'standard'), D('Bolt circle', f.bcd, 'mm', 'standard')],
    });
  }

  /** Bonnet + gasket + bonnet bolting + packing + follower/gland + gland flange & studs. Returns top Y. */
  function bonnetAssembly(v, meta, parts, o) {
    const S = (k) => meta?.[k]?.src || 'estimate';
    const { bw, sd, port } = o;
    const y0 = v.body_h;
    const bfT = Math.max(14, o.f.t * 0.9);
    const yb = y0 + v.bonnet_h;
    const nb = v.nps >= 8 ? 12 : v.nps >= 3 ? 8 : 4;
    const bd = clamp(0.05 * bw + 6, 10, 36);

    parts.push(P('bonnet_gasket', 'Bonnet gasket', 'rubber', [ring('y', port / 2 + 6, bw * 0.38, 3, [0, y0 + 1.5, 0])], {
      group: 'Bonnet assembly', stage: 2,
      fn: 'Seals the body-to-bonnet joint against process pressure.',
      material: o.cv ? 'Flexible graphite / spiral-wound 316 SS + graphite' : 'Spiral-wound 316 SS + graphite (API 600)',
      dims: [D('Gasket OD', bw * 0.76), D('Gasket ID', port + 12)],
    }));
    parts.push(P('bonnet', 'Bonnet', 'body', [
      cyl('y', bw * 0.42, bfT, [0, y0 + 3 + bfT / 2, 0]),
      cone('y', bw * 0.27, bw * 0.18, v.bonnet_h - bfT - 3, [0, y0 + 3 + bfT + (v.bonnet_h - bfT - 3) / 2, 0]),
    ], {
      group: 'Bonnet assembly', stage: 1,
      fn: o.cv
        ? 'Closes the top of the body, guides the stem and houses the packing box. Extension bonnets keep the packing away from hot or cryogenic service.'
        : 'Closes the top of the body, contains the packing box and backseat; carries the yoke.',
      material: o.cv ? 'Same as body (e.g. WCC / CF8M)' : 'ASTM A216 WCB or A351 CF8M',
      dims: [D('Bonnet height', v.bonnet_h, 'mm', S('bonnet_h')), D('Bonnet flange OD', bw * 0.84)],
    }));
    const studs = [];
    for (const p of circle('y', bw * 0.36, nb, [0, y0, 0])) {
      studs.push(cyl('y', bd / 2, bfT + 18 + bd * 1.8, p));
      studs.push(cyl('y', bd * 0.85, bd * 0.85, [p[0], y0 + 3 + bfT + bd * 0.45, p[2]]));
    }
    parts.push(P('bonnet_bolting', 'Bonnet studs & nuts', 'bolt', studs, {
      group: 'Bonnet assembly', stage: 1, qty: nb,
      fn: 'Clamp the bonnet to the body and compress the bonnet gasket.',
      material: 'ASTM A193 B7 / A194 2H (B7M / 2HM for sour service)',
      dims: [D('Studs', `${nb} × ${inch(bd)}`, '', 'estimate')],
    }));
    const pkW = Math.max(5, sd * 0.32);
    const pkH = sd * 1.6;
    parts.push(P('packing', o.cv ? 'Packing set' : 'Gland packing', 'rubber',
      [ring('y', sd / 2, sd / 2 + pkW, pkH, [0, yb - pkH / 2 - 4, 0])], {
        group: 'Bonnet assembly', stage: 2,
        fn: 'Seals the moving stem against process leakage. Live-loaded or ISO 15848 low-emission sets are common.',
        material: o.cv ? 'PTFE V-rings or flexible graphite, with packing spring and box ring' : 'Flexible graphite with anti-extrusion rings',
        dims: [D('Packing bore (= stem)', sd, 'mm', S('stem_d')), D('Cross-section', pkW)],
      }));
    const folH = sd * 0.6;
    parts.push(P('gland', o.cv ? 'Packing follower' : 'Gland', 'body', [ring('y', sd / 2 + 0.5, sd / 2 + pkW, folH, [0, yb + folH / 2 - 2, 0])], {
      group: 'Bonnet assembly', stage: 2,
      fn: 'Transfers the gland-bolt load evenly onto the packing rings.',
      material: '316 SS', dims: [D('Bore', sd + 1)],
    }));
    const gfW = (sd + 2 * pkW) * 2.6; const gfT = Math.max(10, sd * 0.5);
    parts.push(P('gland_flange', o.cv ? 'Packing flange' : 'Gland flange', 'body',
      [box([gfW, gfT, (sd + 2 * pkW) * 1.3], [0, yb + folH + gfT / 2 - 2, 0])], {
        group: 'Bonnet assembly', stage: 2,
        fn: 'Bridge plate pulled down by the gland studs to load the packing.',
        material: 'Carbon steel, zinc plated / 316 SS', dims: [D('Width', gfW)],
      }));
    parts.push(P('gland_studs', o.cv ? 'Packing flange studs & nuts' : 'Gland eyebolts & nuts', 'bolt', [
      cyl('y', Math.max(4, sd * 0.18), folH + gfT + 30, [-gfW * 0.38, yb + 4, 0]),
      cyl('y', Math.max(4, sd * 0.18), folH + gfT + 30, [gfW * 0.38, yb + 4, 0]),
    ], {
      group: 'Bonnet assembly', stage: 2, qty: 2,
      fn: 'Adjust the packing load; re-tighten if the stem weeps.', material: 'ASTM A193 B7 / B8M',
    }));
    return yb + folH + gfT;
  }

  // ───────────────────────── operators ─────────────────────────
  function operator(v, meta, parts, yTop, o) {
    const S = (k) => meta?.[k]?.src || 'estimate';
    const op = v.operator; const sd = o.sd;
    const G = 'Actuator';
    if (op === 'handwheel') {
      if (v.body === 'gate' || v.body === 'globe') {
        const yh = v.yoke_h;
        parts.push(P('yoke', 'Yoke', 'body', [
          box([18, yh, 26], [-v.hw_d * 0.18, yTop + yh / 2, 0]), box([18, yh, 26], [v.hw_d * 0.18, yTop + yh / 2, 0]),
          box([v.hw_d * 0.45, 22, 40], [0, yTop + yh - 11, 0]),
        ], {
          group: 'Manual operator', stage: 1,
          fn: 'Outside screw & yoke (OS&Y): holds the yoke sleeve above the packing so the stem threads stay out of the process.',
          material: 'Integral with bonnet, or WCB', dims: [D('Yoke height', yh, 'mm', S('yoke_h'))],
        }));
        const yt = yTop + yh;
        parts.push(P('yoke_sleeve', 'Yoke sleeve (stem nut)', 'accent', [cyl('y', sd * 1.15, 40, [0, yt + 20, 0])], {
          group: 'Manual operator', stage: 1,
          fn: 'Threaded bronze nut turned by the handwheel; drives the rising stem up and down.',
          material: 'Aluminium bronze / Ni-resist', dims: [D('Thread (= stem)', sd, 'mm', S('stem_d'))],
        }));
        const rise = v.body === 'gate' ? v.stem_ext : 25.4 * v.nps * 0.35;
        const base = o.stemBase;
        parts.push(P('stem', 'Stem (rising)', 'steel', [cyl('y', sd / 2, yt + rise + 60 - base, [0, (base + yt + rise + 60) / 2, 0])], {
          group: 'Trim', stage: 2,
          fn: 'Connects the closure member to the handwheel; trapezoidal (ACME) thread at the top, polished through the packing.',
          material: '13Cr (A182 F6a) or 316 SS', dims: [D('Diameter', sd, 'mm', S('stem_d')), D('Stem rise (open)', rise, 'mm', S('stem_ext'))],
        }));
        parts.push(handwheelPart('handwheel', [0, yt + 30, 0], v.hw_d, 'y', { src: S('hw_d') }));
        parts.push(P('hw_nut', 'Handwheel nut', 'bolt', [cyl('y', sd * 0.9, 20, [0, yt + 52, 0])], {
          group: 'Manual operator', stage: 0, fn: 'Retains the handwheel on the yoke sleeve.', material: 'Carbon steel',
        }));
      } else {
        parts.push(P('stem_ext', 'Stem extension', 'steel', [cyl('y', 10, v.yoke_h, [0, yTop + v.yoke_h / 2, 0])], { group: 'Manual operator', stage: 1 }));
        parts.push(handwheelPart('handwheel', [0, yTop + v.yoke_h, 0], v.hw_d, 'y', { src: S('hw_d') }));
      }
      return;
    }
    if (op === 'lever') {
      parts.push(P('lever_head', 'Wrench head & stop plate', 'bolt', [cyl('y', sd * 1.2, 24, [0, yTop + 12, 0]), box([sd * 3, 4, sd * 3], [0, yTop + 2, 0])], {
        group: 'Manual operator', stage: 0, fn: 'Engages the stem flats; the stop plate limits travel to 90°. Lockable open/closed.', material: 'Carbon steel',
      }));
      parts.push(P('lever', 'Lever handle', 'wheel', [
        box([v.lever_l, 10, 34], [v.lever_l / 2 - 20, yTop + 30, 0]),
        box([v.lever_l * 0.3, 22, 40], [v.lever_l * 0.82, yTop + 30, 0]),
      ], {
        group: 'Manual operator', stage: 0,
        fn: 'Quarter-turn manual operation. Lever parallel to the pipe = open.',
        material: 'Carbon steel, vinyl grip', dims: [D('Lever length', v.lever_l, 'mm', S('lever_l'))],
      }));
      return;
    }
    if (op === 'gear') {
      parts.push(P('bracket', 'Mounting adaptor', 'body', [cyl('y', o.f.pipeOD * 0.35, v.yoke_h, [0, yTop + v.yoke_h / 2, 0])], {
        group: G, stage: 1, fn: 'Adapts the valve ISO 5211 top flange to the gearbox flange; houses the stem coupling.', material: 'Carbon steel',
        dims: [D('Height', v.yoke_h, 'mm', S('yoke_h'))],
      }));
      const y = yTop + v.yoke_h;
      parts.push(P('gearbox', 'Worm gearbox', 'act', [box([v.act_d, v.act_h, v.act_d * 0.8], [0, y + v.act_h / 2, 0])], {
        group: G, stage: 0, fn: 'Self-locking worm and quadrant gear reduces handwheel effort for quarter-turn valves.',
        material: 'Ductile iron housing, bronze quadrant', dims: [D('Width', v.act_d, 'mm', S('act_d')), D('Height', v.act_h, 'mm', S('act_h'))],
      }));
      parts.push(P('gear_indicator', 'Position indicator', 'accent', [cyl('y', v.act_d * 0.2, 14, [0, y + v.act_h + 7, 0])], {
        group: G, stage: 0, fn: 'Shows open/closed position on top of the gearbox.', material: 'Aluminium / polycarbonate',
      }));
      parts.push(P('input_shaft', 'Input shaft', 'steel', [cyl('z', v.act_d * 0.06, v.act_d * 0.7, [0, y + v.act_h * 0.5, v.act_d * 0.75])], {
        group: G, stage: 0, ex: [0, 0, v.act_d * 0.3], fn: 'Worm shaft driven by the handwheel.', material: 'Alloy steel',
      }));
      parts.push(handwheelPart('handwheel', [0, y + v.act_h * 0.5, v.act_d * 1.1], v.hw_d, 'z', { src: S('hw_d'), ex: [0, 0, v.act_d * 0.6] }));
      return;
    }
    if (op === 'pneumatic_rotary') {
      const yh = v.yoke_h; const Dd = v.act_d; const L = v.act_l;
      parts.push(P('bracket', 'Mounting bracket', 'body', [box([Dd * 0.9, yh, Dd * 0.9], [0, yTop + yh / 2, 0])], {
        group: G, stage: 1, fn: 'Bolts the actuator to the valve ISO 5211 flange.', material: 'Carbon steel, painted',
        dims: [D('Height', yh, 'mm', S('yoke_h'))],
      }));
      parts.push(P('coupling', 'Drive coupling', 'steel', [cyl('y', sd * 0.9, yh * 0.8, [0, yTop + yh / 2, 0])], {
        group: G, stage: 2, ex: [0, 0, Dd * 0.9], fn: 'Square / double-D adaptor transmitting torque from the pinion to the valve stem.', material: 'Alloy steel',
      }));
      const y = yTop + yh;
      parts.push(P('actuator', 'Actuator housing (rack & pinion)', 'act', [box([L, Dd * 1.05, Dd * 1.1], [0, y + Dd * 0.53, 0])], {
        group: G, stage: 0, fn: 'Twin pistons drive racks that turn the central pinion 90°. Spring-return units fail open or closed on air loss.',
        material: 'Extruded aluminium, hard anodised', dims: [D('Length', L, 'mm', S('act_l')), D('Body width', Dd, 'mm', S('act_d'))],
      }));
      for (const s of [-1, 1]) {
        parts.push(P(s < 0 ? 'end_cap_l' : 'end_cap_r', `End cap / spring cartridge (${s < 0 ? 'left' : 'right'})`, 'act',
          [cyl('x', Dd * 0.48, 18, [s * (L / 2 + 9), y + Dd * 0.53, 0])], {
            group: G, stage: 1, ex: [s * Dd * 0.8, 0, 0],
            fn: 'Closes the cylinder bore; on spring-return units it contains the preloaded spring cartridges.', material: 'Die-cast aluminium',
          }));
      }
      parts.push(P('indicator', 'Visual position indicator', 'accent', [cyl('y', Dd * 0.3, 30, [0, y + Dd * 1.05 + 15, 0])], {
        group: 'Accessories', stage: 0, fn: 'Shows valve position (open / closed) on the pinion top.', material: 'Polycarbonate',
      }));
      if (v.positioner) {
        parts.push(P('positioner', 'Positioner / limit switch box', 'tx', [box([120, 110, 100], [0, y + Dd * 1.05 + 85, 0])], {
          group: 'Accessories', stage: 0, fn: 'Positioner for modulating duty, or limit switch box (ZSO / ZSC) for on-off duty.',
          material: 'Aluminium, Ex d / Ex ia', dims: [D('Envelope', '120 × 110 × 100', 'mm', 'estimate')],
        }));
      }
      parts.push(P('solenoid', 'Solenoid valve (NAMUR)', 'tx', [box([60, 70, 50], [0, y + Dd * 0.5, Dd * 0.55 + 25])], {
        group: 'Accessories', stage: 0, ex: [0, 0, Dd * 0.5], fn: '3/2 or 5/2 solenoid on the NAMUR pad; trips the actuator on loss of signal.', material: 'SS body, Ex d coil',
      }));
      return;
    }
    if (op === 'electric') {
      const yh = v.yoke_h; const W = v.act_d; const H = v.act_h;
      const multi = v.body === 'gate' || v.body === 'globe';
      parts.push(P('thrust_base', multi ? 'Thrust base (type A)' : 'Mounting bracket & coupling', 'body', [
        cyl('y', W * 0.25, yh, [0, yTop + yh / 2, 0]), cyl('y', W * 0.34, 16, [0, yTop + yh - 8, 0]),
      ], {
        group: G, stage: 1,
        fn: multi ? 'Takes the stem thrust through its thrust bearings, so the valve rather than the gearcase carries the axial load (ISO 5210).'
          : 'Adapts the valve ISO 5211 flange to the part-turn actuator and transmits torque.',
        material: 'Ductile iron / carbon steel',
        dims: [D(multi ? 'Flange (ISO 5210)' : 'Flange (ISO 5211)', `F${Math.round(clamp(10 + v.nps * 2.5, 10, 30))}`, '', 'estimate'), D('Height', yh, 'mm', S('yoke_h'))],
      }));
      if (multi) {
        parts.push(P('drive_bush', 'Drive bush (stem nut)', 'accent', [ring('y', sd / 2, sd / 2 + 10, yh * 0.6, [0, yTop + yh * 0.55, 0])], {
          group: G, stage: 2, ex: [0, 0, W * 0.9],
          fn: 'Bronze nut machined to the stem thread; converts output-sleeve rotation into stem lift.',
          material: 'Aluminium bronze', dims: [D('Bore (= stem)', sd, 'mm', S('stem_d'))],
        }));
      }
      const y = yTop + yh;
      parts.push(P('gearcase', 'Main gearcase (worm drive)', 'act', [cyl('y', W * 0.38, H * 0.55, [0, y + H * 0.275, 0])], {
        group: G, stage: 0, fn: 'Motor drives a worm and wheel to the output sleeve. Self-locking; houses torque sensing and the position encoder.',
        material: 'Aluminium alloy, IP68, Ex d', dims: [D('Width', W, 'mm', S('act_d')), D('Height', H, 'mm', S('act_h'))],
      }));
      parts.push(P('control_unit', 'Control unit & display', 'tx', [
        box([W * 0.75, H * 0.38, W * 0.7], [0, y + H * 0.55 + H * 0.19, 0]),
        cyl('z', W * 0.2, W * 0.06, [0, y + H * 0.74, W * 0.35 + W * 0.03]),
        cyl('z', 16, 30, [-W * 0.2, y + H * 0.6, W * 0.35 + 15]), cyl('z', 16, 30, [W * 0.2, y + H * 0.6, W * 0.35 + 15]),
      ], {
        group: G, stage: 0,
        fn: 'Motor starter, controls, LCD display and Local/Remote + Open/Close selector knobs (non-intrusive setup).',
        material: 'Aluminium, Ex d',
      }));
      parts.push(P('motor', 'Motor', 'act', [
        cyl('x', W * 0.24, W * 0.55, [-(W * 0.38 + W * 0.27), y + H * 0.3, 0]),
        cyl('x', W * 0.26, 14, [-(W * 0.38 + W * 0.55), y + H * 0.3, 0]),
      ], {
        group: G, stage: 0, ex: [-W * 0.6, 0, 0],
        fn: '3-phase squirrel-cage motor, S2-15 min / S4 rated, with winding thermostats.', material: 'Class F insulation, Ex d enclosure',
      }));
      parts.push(P('declutch', 'Declutch lever', 'wheel', [box([14, 70, 14], [W * 0.3, y + H * 0.15, -W * 0.3], { ry: 0.4 })], {
        group: G, stage: 0, ex: [W * 0.3, 0, -W * 0.3], fn: 'Engages the handwheel drive; a motor start re-engages motor drive automatically.', material: 'Ductile iron',
      }));
      parts.push(P('hw_shaft', 'Handwheel shaft', 'steel', [cyl('x', 12, 60, [W * 0.38 + 30, y + H * 0.3, 0])], { group: G, stage: 0, ex: [W * 0.45, 0, 0], material: 'Alloy steel' }));
      parts.push(handwheelPart('handwheel', [W * 0.38 + 60, y + H * 0.3, 0], v.hw_d, 'x', {
        name: 'Handwheel (emergency)', group: G, src: S('hw_d'), ex: [W * 0.8, 0, 0],
        fn: 'Manual operation on loss of power; mechanically independent of the motor drive.',
      }));
      parts.push(P('terminal_cover', 'Terminal compartment & cable entries', 'bolt', [
        box([W * 0.3, H * 0.25, 14], [0, y + H * 0.74, -W * 0.35 - 7]),
        cyl('x', 12, 40, [W * 0.375 + 20, y + H * 0.74, -W * 0.15]), cyl('x', 12, 40, [W * 0.375 + 20, y + H * 0.74, W * 0.05]),
      ], {
        group: G, stage: 0, ex: [0, 0, -W * 0.6],
        fn: 'Separately sealed terminal box, so the internals stay protected when it is opened for site cabling. Typically 3 × M25 / M40 entries.',
        material: 'Aluminium, Ex e / Ex d',
      }));
      if (multi) {
        const st = 25.4 * v.nps * 1.05 + 40;
        parts.push(P('stem_cover', 'Stem protection tube', 'steel', [cyl('y', W * 0.1, st, [0, y + H * 0.93 + st / 2, 0])], {
          group: G, stage: 0, fn: 'Covers the rising stem above the actuator; length ≥ valve stroke.', material: 'Steel tube, painted',
          dims: [D('Stroke (≈ port)', 25.4 * v.nps * 1.05)],
        }));
      }
      return;
    }
    if (op === 'pneumatic_diaphragm') {
      const yh = v.yoke_h; const Dd = v.act_d; const H = v.act_h;
      parts.push(P('yoke', 'Yoke', 'body', [
        cyl('y', Dd * 0.16, 22, [0, yTop + 11, 0]),
        box([20, yh, 30], [-Dd * 0.17, yTop + yh / 2, 0]), box([20, yh, 30], [Dd * 0.17, yTop + yh / 2, 0]),
        cyl('y', Dd * 0.2, 24, [0, yTop + yh - 12, 0]),
      ], {
        group: G, stage: 1, fn: 'Rigid frame joining actuator and bonnet; the open window gives access to the stem connector and packing.',
        material: 'Ductile iron / cast steel', dims: [D('Yoke height', yh, 'mm', S('yoke_h'))],
      }));
      parts.push(P('stem_connector', 'Stem connector', 'steel', [box([42, 30, 32], [0, yTop + yh * 0.45, 0])], {
        group: G, stage: 2, ex: [0, 0, Dd * 0.6],
        fn: 'Split clamp joining actuator stem and valve stem; sets plug seating and travel.', material: 'Zinc-plated steel',
      }));
      parts.push(P('travel_indicator', 'Travel indicator & scale', 'accent', [
        box([4, yh * 0.3, 36], [Dd * 0.17 + 12, yTop + yh * 0.45, 0]), box([30, 4, 6], [16, yTop + yh * 0.45, 0]),
      ], { group: G, stage: 2, ex: [Dd * 0.35, 0, 0], fn: 'Pointer on the stem connector against a scale on the yoke — shows % open of rated travel.', material: 'Stainless steel' }));
      const asL = yh * 0.55 + H * 0.42;
      parts.push(P('actuator_stem', 'Actuator stem', 'steel', [cyl('y', sd * 0.7, asL, [0, yTop + yh * 0.45 + asL / 2, 0])], {
        group: G, stage: 1, fn: 'Transmits diaphragm force to the valve stem.', material: 'Chrome-plated steel',
      }));
      const ya = yTop + yh;
      parts.push(P('lower_casing', 'Lower diaphragm casing', 'act', [cone('y', Dd * 0.22, Dd / 2, H * 0.42, [0, ya + H * 0.21, 0])], {
        group: G, stage: 0, fn: 'Lower pressure chamber, bolted to the yoke; houses the actuator spring.', material: 'Pressed steel, painted',
        dims: [D('Casing OD', Dd, 'mm', S('act_d'))],
      }));
      parts.push(P('spring', 'Actuator spring', 'spring', [helix('y', Dd * 0.2, Math.max(3, Dd * 0.018), H * 0.36, 6, [0, ya + H * 0.2, 0])], {
        group: G, stage: 0, ex: [0, 0, Dd * 0.75],
        fn: 'Opposes the air load and drives the valve to its fail position (FC / FO) on loss of air. The spring range sets the bench set.',
        material: 'Chrome-silicon / alloy spring steel', dims: [D('Mean coil Ø', Dd * 0.4)],
      }));
      parts.push(P('diaphragm_plate', 'Diaphragm plate (head)', 'steel', [cyl('y', Dd * 0.38, 8, [0, ya + H * 0.42 - 6, 0])], {
        group: G, stage: 0, fn: 'Rigid plate behind the diaphragm; transfers air force to the actuator stem.', material: 'Steel',
      }));
      parts.push(P('diaphragm', 'Diaphragm', 'rubber', [cyl('y', Dd / 2 + 5, 3, [0, ya + H * 0.42 + 1.5, 0])], {
        group: G, stage: 0, fn: 'Flexible membrane converting signal air pressure into thrust: effective area × pressure = actuator force.',
        material: 'Nitrile (NBR) with nylon fabric reinforcement', dims: [D('Effective area ≈', `${Math.round(Math.PI * (Dd * 0.45) ** 2 / 100)} cm²`, '', 'estimate')],
      }));
      parts.push(P('upper_casing', 'Upper diaphragm casing', 'act', [cone('y', Dd / 2, Dd * 0.25, H * 0.5, [0, ya + H * 0.42 + 3 + H * 0.25, 0]), cyl('y', 8, 30, [0, ya + H * 0.92 + 18, 0])], {
        group: G, stage: 0, fn: 'Upper pressure chamber with the loading connection (signal air in).', material: 'Pressed steel, painted',
        dims: [D('Loading connection', '1/4" NPT', '', 'estimate')],
      }));
      parts.push(P('casing_bolts', 'Casing cap screws & nuts', 'bolt', circle('y', Dd / 2 + 2, 16, [0, ya + H * 0.42, 0]).map((p) => cyl('y', 4, 24, p)), {
        group: G, stage: 0, qty: 16, fn: 'Clamp the two casings together and seal the diaphragm bead. Never remove with spring preload applied.',
        material: 'Zinc-plated steel',
      }));
      if (v.positioner) {
        const px = Dd * 0.17 + 75; const py = yTop + yh * 0.55;
        parts.push(P('positioner_bracket', 'Positioner mounting bracket', 'steel', [box([90, 16, 20], [Dd * 0.17 + 18, py, 0])], {
          group: 'Accessories', stage: 1, ex: [Dd * 0.2, 0, 0], material: '316 SS',
        }));
        parts.push(P('positioner', 'Digital valve positioner', 'tx', [box([110, 150, 85], [px, py, 0]), cyl('z', 34, 14, [px, py + 5, 48])], {
          group: 'Accessories', stage: 0, ex: [Dd * 0.5, 0, 0],
          fn: 'Compares the 4–20 mA / HART setpoint with stem-travel feedback and adjusts actuator air to hold position.',
          material: 'Aluminium, Ex d / Ex ia', dims: [D('Envelope', '110 × 150 × 85', 'mm', 'estimate')],
        }));
        parts.push(P('airset', 'Air filter regulator', 'tx', [cyl('y', 28, 110, [px, py - 150, 0]), cyl('y', 34, 30, [px, py - 80, 0])], {
          group: 'Accessories', stage: 0, ex: [Dd * 0.5, -60, 0], fn: 'Filters and regulates the instrument air supply to the positioner (typ. 1.4–4 bar).', material: 'Aluminium / SS',
        }));
        parts.push(P('tubing', 'Instrument tubing', 'tube', [
          tube([px, py - 95, 0], [px, py - 75, 0], 3), tube([px + 55, py + 40, 0], [px + 55, ya + H * 0.92 + 30, 0], 3),
          tube([px + 55, ya + H * 0.92 + 30, 0], [8, ya + H * 0.92 + 30, 0], 3),
        ], { group: 'Accessories', stage: 0, ex: [Dd * 0.5, 0, 0], fn: 'Supply and output air lines (positioner → actuator loading connection).', material: '316 SS tube 1/4" or 3/8"' }));
      }
      if (v.cv_handwheel) {
        parts.push(handwheelPart('handwheel', [0, ya + H + 120, 0], v.hw_d, 'y', { group: G, src: S('hw_d'), fn: 'Top-mounted handwheel: manual override and adjustable travel stop.' }));
      }
    }
  }

  // ───────────────────────── valve build ─────────────────────────
  function buildValve(v, meta) {
    const S = (k) => meta?.[k]?.src || 'estimate';
    const f = R.flangeOf(v.nps, v.cls);
    if (v.body === 'psv') return buildPSV(v, meta, f);
    const parts = [];
    const stub = v.pipe_stub > 0 ? v.pipe_stub : 0;
    const rating = `${npsTxt(v.nps)} ASME CL${v.cls} RF`;
    const half = v.ftf / 2; const bw = v.body_w; const port = v.port_d; const sd = v.stem_d;
    const U = Math.max(30, f.od * 0.12);
    const cv = v.service === 'control';
    if (stub) {
      parts.push(P('pipe', 'Connecting pipe (reference)', 'ghost', [
        cyl('x', f.pipeOD / 2, stub, [-half - stub / 2 - 2, 0, 0]), cyl('x', f.pipeOD / 2, stub, [half + stub / 2 + 2, 0, 0]),
      ], { group: 'Reference', stage: 0, fn: 'Mating pipe, shown for context only.' }));
    }

    // ── body
    const bp = [];
    const mat = cv ? 'ASTM A216 WCC / A351 CF8M' : 'ASTM A216 WCB / A351 CF8M';
    const neckR = f.pipeOD / 2 * 1.3;
    let stemBase = 0;
    if (v.body === 'globe') {
      bodyFlanges(bp, 'x', -1, half, f); bodyFlanges(bp, 'x', 1, half, f);
      bp.push(sph(bw / 2, [0, 0, 0], [Math.min(1.15, (half - f.t) / (bw / 2)), 0.9, 0.9]));
      bp.push(cyl('x', neckR, 2 * (half - f.t), [0, 0, 0]));
      bp.push(cyl('y', bw * 0.33, v.body_h - bw * 0.2, [0, (v.body_h + bw * 0.2) / 2 - bw * 0.1, 0]));
      bp.push(cyl('y', bw * 0.42, 16, [0, v.body_h - 8, 0]));
    } else if (v.body === 'gate') {
      bodyFlanges(bp, 'x', -1, half, f); bodyFlanges(bp, 'x', 1, half, f);
      bp.push(cyl('x', neckR, 2 * (half - f.t), [0, 0, 0]));
      bp.push(box([bw * 0.55, v.body_h + bw * 0.25, bw], [0, (v.body_h - bw * 0.25) / 2, 0]));
      bp.push(cyl('z', bw / 2, bw * 0.55, [0, -bw * 0.05, 0]));
      bp.push(cyl('y', bw * 0.42, 16, [0, v.body_h - 8, 0]));
    } else if (v.body === 'ball') {
      const split = Math.min(half - f.t * 2.2, bw * 0.3);
      bodyFlanges(bp, 'x', -1, half, f);
      bp.push(sph(bw / 2, [0, 0, 0], [Math.min(1, (half - f.t) / (bw / 2)), 1, 1]));
      bp.push(cyl('x', neckR * 1.1, half - f.t, [-(half - f.t) / 2, 0, 0]));
      bp.push(cyl('x', bw * 0.45, 14, [split - 7, 0, 0]));
      bp.push(cyl('y', f.pipeOD * 0.32, v.body_h - bw * 0.4, [0, bw * 0.4 + (v.body_h - bw * 0.4) / 2, 0]));
      const cp = []; bodyFlanges(cp, 'x', 1, half, f);
      cp.push(cyl('x', bw * 0.45, 14, [split + 7, 0, 0]));
      const cl = Math.max(4, half - f.t - split - 14);
      cp.push(cyl('x', neckR * 1.1, cl, [split + 14 + cl / 2, 0, 0]));
      parts.push(P('body_connector', 'Body connector (end piece)', 'body', cp, {
        group: 'Body', stage: 1, ex: [U * 3, 0, 0],
        fn: 'Second half of the split body; retains the ball and downstream seat and carries the outlet end flange.',
        material: mat, dims: [D('End flange OD × thk', `${f.od} × ${f.t}`, 'mm', 'standard')],
      }));
      parts.push(P('body_bolting', 'Body bolting', 'bolt', circle('x', bw * 0.4, 8, [split, 0, 0]).map((p) => cyl('x', 8, 50, p)), {
        group: 'Body', stage: 1, ex: [U * 5, 0, 0], qty: 8, fn: 'Studs joining body and body connector; part of the pressure boundary.',
        material: 'ASTM A193 B7 / A194 2H',
      }));
    } else if (v.body === 'butterfly') {
      const pid = pipeID(v.nps);
      bp.push(ring('x', pid / 2, f.bcd / 2 - f.bolt, v.ftf, [0, 0, 0]));
      bp.push(cyl('y', f.pipeOD * 0.22, v.body_h - f.bcd / 2, [0, f.bcd / 2 + (v.body_h - f.bcd / 2) / 2 - f.bolt, 0]));
      bp.push(cyl('y', f.pipeOD * 0.2, f.bcd / 2 - pid / 2, [0, -(pid / 2 + (f.bcd / 2 - pid / 2) / 2), 0]));
      parts.push(P('mating_flanges', 'Mating pipe flanges (reference)', 'ghost', [
        cyl('x', f.od / 2, f.t, [-half - f.t / 2, 0, 0]), cyl('x', f.od / 2, f.t, [half + f.t / 2, 0, 0]),
      ], { group: 'Reference', stage: 0, fn: 'Wafer bodies are clamped between the pipe flanges by through-bolts.' }));
    }
    parts.push(P('body', 'Body', 'body', bp, {
      group: 'Body', stage: 2,
      fn: {
        globe: cv ? 'Pressure-retaining casting with an S-shaped flow path through a horizontal seat; provides the end connections and holds the trim.'
          : 'Pressure-retaining globe body; flow turns through a horizontal seat — good for throttling and positive shut-off.',
        gate: 'Pressure-retaining body with a straight-through bore; the wedge seats against two inclined seat rings (on-off duty only).',
        ball: 'Split body (inlet half) holding the ball between two seats; straight-through bore.',
        butterfly: 'Short wafer body clamped between pipe flanges; the disc rotates 90° on a shaft.',
      }[v.body],
      material: mat,
      dims: [
        D('Size / rating', rating, '', S('nps')), D('Face-to-face', v.ftf, 'mm', S('ftf')),
        D('End flange OD × thk', `${f.od} × ${f.t}`, 'mm', 'standard'), D('Flange bolting', `${f.n} × ${inch(f.bolt)} on Ø${f.bcd}`, '', 'standard'),
        D('Body height (CL → top)', v.body_h, 'mm', S('body_h')), D('Port', port, 'mm', S('port_d')),
      ],
      note: v.body === 'butterfly' ? 'Wafer pattern per API 609; class rating per ASME B16.34.'
        : 'End flanges are integral with the body casting (ASME B16.5 dimensions, B16.34 pressure–temperature rating).',
    }));
    if (v.body !== 'butterfly') {
      parts.push(flangeBolting('bolting_in', 'Inlet flange studs & nuts', 'x', -1, half, f, U * 3));
      parts.push(flangeBolting('bolting_out', 'Outlet flange studs & nuts', 'x', 1, half, f, U * (v.body === 'ball' ? 7 : 3)));
    }

    // ── trim & top works
    let yTop = v.body_h;
    if (v.body === 'globe') {
      const srW = Math.max(6, port * 0.14); const srH = Math.max(8, port * 0.16); const seatY = -port * 0.12;
      parts.push(P('seat_ring', 'Seat ring', 'trim', [ring('y', port / 2, port / 2 + srW, srH, [0, seatY - srH / 2, 0])], {
        group: 'Trim', stage: 2,
        fn: 'Replaceable shut-off surface the plug closes against; its bore sets the port size and rated Cv.',
        material: cv ? '316 SS, or 316 SS with Alloy 6 (Stellite) hard-facing' : '13Cr / Stellite hard-faced',
        dims: [D('Port (bore)', port, 'mm', S('port_d')), D('Shut-off class', cv ? 'ANSI/FCI 70-2 Class IV–V' : 'API 598', '', 'estimate')],
      }));
      if (cv) {
        const cr = port / 2 + 3; const cw = Math.max(6, port * 0.1); const ch = v.body_h - seatY - 2;
        parts.push(P('cage', 'Cage', 'trim', [ring('y', cr, cr + cw, ch, [0, seatY + ch / 2, 0])], {
          group: 'Trim', stage: 2,
          fn: 'Guides the plug and clamps the seat ring; the window shape sets the flow characteristic (linear / equal %). Anti-cavitation cages use drilled holes.',
          material: '416 SS / 17-4PH, hardened', dims: [D('Cage bore', 2 * cr), D('Height', ch)],
        }));
      }
      const plH = cv ? Math.max(25, port * 0.6) : Math.max(14, port * 0.28);
      const plR = cv ? port / 2 : port / 2 + srW * 0.6;
      parts.push(P(cv ? 'plug' : 'disc', cv ? 'Valve plug' : 'Disc', 'trim', [cyl('y', plR, plH, [0, seatY + plH / 2, 0])], {
        group: 'Trim', stage: 2,
        fn: cv ? 'Moving closure member; its position in the cage throttles the flow. Balanced plugs with seal rings reduce the actuator force.'
          : 'Closure member lowered onto the seat by the stem for shut-off.',
        material: cv ? '316 SS / hardened 416 SS, seating surface hard-faced' : '13Cr / Stellite faced',
        dims: [D('Plug Ø', 2 * plR), D('Stroke (≈ ¼ port)', port * 0.25)],
      }));
      stemBase = seatY + plH;
      if (cv) {
        const stemTop = v.body_h + v.bonnet_h + v.yoke_h * 0.45;
        parts.push(P('stem', 'Valve stem', 'steel', [cyl('y', sd / 2, stemTop - stemBase, [0, (stemTop + stemBase) / 2, 0])], {
          group: 'Trim', stage: 2, fn: 'Connects plug and actuator stem; polished through the packing for low friction and emissions.',
          material: 'S20910 (Nitronic 50) / 316 SS', dims: [D('Diameter', sd, 'mm', S('stem_d'))],
        }));
      }
      yTop = bonnetAssembly(v, meta, parts, { bw, sd, port, f, cv });
    } else if (v.body === 'gate') {
      const wT = Math.max(18, port * 0.32);
      const srH = Math.max(8, port * 0.12);
      parts.push(P('seat_rings', 'Seat rings', 'trim', [
        ring('x', port / 2, port / 2 + Math.max(6, port * 0.12), srH, [-(wT / 2 + srH / 2), 0, 0]),
        ring('x', port / 2, port / 2 + Math.max(6, port * 0.12), srH, [wT / 2 + srH / 2, 0, 0]),
      ], {
        group: 'Trim', stage: 2, qty: 2, fn: 'Welded-in or threaded rings forming the sealing faces for the wedge.',
        material: 'Hard-faced 13Cr / Stellite 6', dims: [D('Bore', port, 'mm', S('port_d'))],
      }));
      parts.push(P('wedge', 'Wedge (gate)', 'trim', [box([wT, port * 1.2, port * 1.15], [0, port * 0.05, 0])], {
        group: 'Trim', stage: 2, fn: 'Flexible or solid wedge lowered across the bore; seats on both inclined seat rings for tight shut-off.',
        material: 'WCB + 13Cr / Stellite facing (API 600 trim 8)', dims: [D('Wedge width', port * 1.15), D('Bore', port, 'mm', S('port_d'))],
      }));
      stemBase = port * 0.65;
      yTop = bonnetAssembly(v, meta, parts, { bw, sd, port, f, cv: false });
    } else if (v.body === 'ball') {
      const ballR = Math.max(port / 2 + 10, port * 0.72);
      const sW = Math.max(8, port * 0.15);
      parts.push(P('seats', 'Seats', 'seat', [
        ring('x', port / 2 + 2, port / 2 + 2 + sW, 10, [-ballR * 0.82, 0, 0]), ring('x', port / 2 + 2, port / 2 + 2 + sW, 10, [ballR * 0.82, 0, 0]),
      ], {
        group: 'Trim', stage: 2, qty: 2, fn: 'Soft or metal seat rings sealing against the ball; fire-safe design per API 607.',
        material: 'RPTFE / PEEK / Devlon; metal seats for abrasive service', dims: [D('Seat ID', port + 4)],
      }));
      parts.push(P('ball', 'Ball', 'trim', [sph(ballR, [0, 0, 0]), cyl('x', port / 2, ballR * 1.95, [0, 0, 0], { look: 'bore' })], {
        group: 'Trim', stage: 2,
        fn: `Rotating sphere with a ${v.bore} bore; a 90° turn opens or closes the flow path.${v.nps >= 6 ? ' Trunnion-mounted at this size: the ball is held by upper and lower trunnions and the seats float.' : ' Floating ball: line pressure pushes it onto the downstream seat.'}`,
        material: 'A105 + ENP / 316 SS; hard chrome or tungsten-carbide coated for severe service',
        dims: [D('Ball Ø', 2 * ballR), D('Bore', port, 'mm', S('port_d'))],
      }));
      parts.push(P('thrust_washer', 'Stem thrust washer', 'seat', [ring('y', sd / 2, sd / 2 + 8, 4, [0, ballR + 8, 0])], {
        group: 'Trim', stage: 2, fn: 'Blow-out-proof stem: the stem shoulder bears on this washer from inside the body.', material: 'PTFE / PEEK',
      }));
      const sTop = v.body_h + v.bonnet_h + 30; const sBot = ballR * 0.7;
      parts.push(P('stem', 'Stem', 'steel', [cyl('y', sd / 2, sTop - sBot, [0, (sTop + sBot) / 2, 0])], {
        group: 'Trim', stage: 2, fn: 'Anti-blow-out stem with flats or a key transmitting torque to the ball slot.', material: '17-4PH / 316 SS',
        dims: [D('Diameter', sd, 'mm', S('stem_d'))],
      }));
      parts.push(P('stem_seal', 'Stem seals (O-rings / packing)', 'rubber', [ring('y', sd / 2, sd / 2 + 5, sd, [0, v.body_h - sd * 0.8, 0])], {
        group: 'Trim', stage: 2, fn: 'Primary O-rings plus graphite packing as the fire-safe secondary seal.', material: 'FKM / graphite',
      }));
      if (v.nps >= 6) {
        const tl = bw / 2 - ballR + 20;
        parts.push(P('trunnion', 'Lower trunnion & cover', 'steel', [
          cyl('y', sd * 0.55, tl, [0, -ballR - tl / 2 + 10, 0]), cyl('y', sd * 1.5, 12, [0, -bw / 2 - 6, 0]),
        ], { group: 'Trim', stage: 2, ex: [0, -U * 4, 0], fn: 'Supports the ball on its lower axis so the line load goes into the body, not the seats.', material: 'A105 / 316 SS' }));
      }
      parts.push(P('mounting_pad', 'Top flange (ISO 5211 pad)', 'body', [
        cyl('y', f.pipeOD * 0.2 + 6, v.bonnet_h, [0, v.body_h + v.bonnet_h / 2, 0]), box([f.pipeOD * 0.9, 12, f.pipeOD * 0.9], [0, v.body_h + v.bonnet_h - 6, 0]),
      ], {
        group: 'Body', stage: 1, fn: 'Standard mounting interface for levers, gearboxes and actuators (ISO 5211 F-flange).', material: mat,
        dims: [D('ISO 5211 flange', `F${Math.round(clamp(5 + v.nps * 2.5, 5, 25))}`, '', 'estimate')],
      }));
      yTop = v.body_h + v.bonnet_h;
    } else if (v.body === 'butterfly') {
      const pid = pipeID(v.nps);
      parts.push(P('liner', 'Seat liner', 'rubber', [ring('x', pid / 2 - 4, pid / 2, v.ftf * 0.95, [0, 0, 0])], {
        group: 'Trim', stage: 2, fn: 'Resilient (or PTFE / metal) seat; doubles as the flange gasket in resilient-seated designs.',
        material: 'EPDM / NBR / PTFE; metal seat for triple-offset designs', dims: [D('Seat ID', pid - 8)],
      }));
      parts.push(P('disc', 'Disc', 'trim', [cyl('x', pid / 2 - 4, Math.max(8, v.ftf * 0.3), [0, 0, 0], { rotY: Math.PI / 5 })], {
        group: 'Trim', stage: 2,
        fn: 'Rotates 90° on the shaft to throttle or isolate; stays in the flow stream when open (pressure drop, Cv).',
        material: 'CF8M / Al-bronze / duplex SS', dims: [D('Disc Ø', pid - 8), D('Bore (= pipe ID)', pid, 'mm', S('port_d'))],
      }));
      parts.push(P('taper_pins', 'Disc taper pins', 'bolt', [cyl('z', 4, sd * 1.5, [0, pid * 0.25, 0]), cyl('z', 4, sd * 1.5, [0, -pid * 0.25, 0])], {
        group: 'Trim', stage: 2, qty: 2, fn: 'Lock the disc to the shaft (pin-less splined designs also exist).', material: '316 SS',
      }));
      parts.push(P('shaft_lower', 'Lower shaft', 'steel', [cyl('y', sd / 2, f.bcd / 2, [0, -f.bcd / 4, 0])], {
        group: 'Trim', stage: 2, ex: [0, -U * 4, 0], fn: 'Supports the disc on its lower axis.', material: '17-4PH / 410 SS',
      }));
      parts.push(P('bushings', 'Shaft bushings', 'seat', [ring('y', sd / 2, sd / 2 + 4, sd, [0, f.bcd / 2 - f.bolt + sd / 2, 0])], {
        group: 'Trim', stage: 2, fn: 'Bearings supporting the shaft in the body neck.', material: 'PTFE-lined / bronze',
      }));
      parts.push(P('shaft_upper', 'Upper shaft', 'steel', [cyl('y', sd / 2, v.body_h + v.bonnet_h + 30, [0, (v.body_h + v.bonnet_h + 30) / 2, 0])], {
        group: 'Trim', stage: 2, fn: 'Drive shaft carrying operator torque to the disc.', material: '17-4PH / 410 SS', dims: [D('Shaft Ø', sd, 'mm', S('stem_d'))],
      }));
      parts.push(P('mounting_pad', 'Top plate (ISO 5211)', 'body', [
        cyl('y', f.pipeOD * 0.2, v.bonnet_h, [0, v.body_h + v.bonnet_h / 2, 0]), box([v.ftf * 1.4, 12, v.ftf * 1.4], [0, v.body_h + v.bonnet_h - 6, 0]),
      ], { group: 'Body', stage: 1, fn: 'Operator mounting interface (ISO 5211).', material: mat }));
      yTop = v.body_h + v.bonnet_h;
    }
    operator(v, meta, parts, yTop, { sd, f, stemBase });
    explodeValve(v, parts, U);
    return parts;
  }

  /** Exploded layout: internals rise in a column above the body in assembly order; side parts ride along. */
  function explodeValve(v, parts, U) {
    const by = (id) => parts.find((p) => p.id === id);
    const body = by('body');
    const bb = partBox(body);
    const manualRising = v.operator === 'handwheel' && (v.body === 'gate' || v.body === 'globe');
    const order = {
      globe: ['seat_ring', 'cage', 'plug', 'disc', manualRising ? null : 'stem', 'bonnet_gasket', 'bonnet', 'bonnet_bolting', 'packing', 'gland', 'gland_flange', 'gland_studs'],
      gate: ['seat_rings', 'wedge', 'bonnet_gasket', 'bonnet', 'bonnet_bolting', 'packing', 'gland', 'gland_flange', 'gland_studs'],
      ball: ['thrust_washer', 'stem', 'stem_seal', 'mounting_pad'],
      butterfly: ['bushings', 'shaft_upper', 'mounting_pad'],
    }[v.body] || [];
    const opOrder = ['yoke', 'thrust_base', 'bracket', 'stem_ext', 'actuator_stem', 'yoke_sleeve', 'lower_casing', 'diaphragm_plate', 'diaphragm',
      'upper_casing', 'casing_bolts', 'gearcase', 'control_unit', 'actuator', 'indicator', 'positioner', 'gearbox', 'gear_indicator',
      'lever_head', 'lever', 'handwheel', 'hw_nut', 'stem_cover'];
    const seen = new Set();
    const col = [...order, ...opOrder].filter(Boolean).map(by)
      .filter((p) => p && !seen.has(p.id) && seen.add(p.id) && !p.ex[0] && !p.ex[2] && !p.ex[1]);
    stack(col, 'y', bb.max[1] + U * 1.5, U * 1.4);
    if (manualRising) {
      const st = by('stem'); const yk = by('yoke');
      if (st) st.ex = [-(bb.max[0] - bb.min[0]) * 0.5 - U * 2, yk ? yk.ex[1] * 0.6 : U * 6, 0];
    }
    if (v.body === 'ball') stack([by('seats'), by('ball')].filter(Boolean), 'z', bb.max[2] + U, U, 1);
    if (v.body === 'butterfly') {
      const d = by('disc'); const l = by('liner'); const tp = by('taper_pins');
      if (d) d.ex = [0, 0, bb.max[2] + U * 2];
      if (tp) tp.ex = [0, 0, bb.max[2] + U * 5];
      if (l) l.ex = [0, 0, -(bb.max[2] + U * 2)];
    }
    // side parts ride up with the actuator they belong to
    const anchor = by('upper_casing') || by('gearcase') || by('actuator') || by('gearbox') || by('yoke');
    if (!anchor) return;
    const riders = ['positioner', 'positioner_bracket', 'airset', 'tubing', 'travel_indicator', 'motor', 'hw_shaft', 'declutch', 'terminal_cover',
      'solenoid', 'input_shaft', 'coupling', 'drive_bush', 'stem_connector', 'spring', 'end_cap_l', 'end_cap_r', 'handwheel'];
    for (const id of riders) {
      const p = by(id);
      if (!p || col.includes(p)) continue;
      const k = ['drive_bush', 'stem_connector', 'coupling'].includes(id) ? 0.6 : 1;
      p.ex = [p.ex[0], p.ex[1] + anchor.ex[1] * k, p.ex[2]];
    }
  }

  function buildPSV(v, meta, f) {
    const S = (k) => meta?.[k]?.src || 'estimate';
    const parts = [];
    const fo = R.flangeOf(v.outlet_nps, v.outlet_cls);
    const bw = v.body_w; const nb = v.port_d; const sd = v.stem_d;
    const stub = v.pipe_stub > 0 ? v.pipe_stub : 0;
    const U = Math.max(30, f.od * 0.15);
    if (stub) {
      parts.push(P('pipe', 'Inlet / outlet pipe (reference)', 'ghost', [
        cyl('y', f.pipeOD / 2, stub, [0, -v.cti - stub / 2 - 2, 0]), cyl('x', fo.pipeOD / 2, stub, [v.cto + stub / 2 + 2, 0, 0]),
      ], { group: 'Reference', stage: 0 }));
    }
    const bp = [];
    bodyFlanges(bp, 'y', -1, v.cti, f); bodyFlanges(bp, 'x', 1, v.cto, fo);
    bp.push(sph(bw * 0.55, [0, 0, 0], [1, 1, 0.95]));
    bp.push(cyl('y', f.pipeOD / 2 * 1.3, v.cti - f.t, [0, -(v.cti - f.t) / 2, 0]));
    bp.push(cyl('x', fo.pipeOD / 2 * 1.25, v.cto - fo.t, [(v.cto - fo.t) / 2, 0, 0]));
    bp.push(cyl('y', bw * 0.38, v.body_h - bw * 0.3, [0, bw * 0.3 + (v.body_h - bw * 0.3) / 2, 0]));
    bp.push(cyl('y', bw * 0.5, 14, [0, v.body_h - 7, 0]));
    const body = P('body', 'Body (angle pattern)', 'body', bp, {
      group: 'Body', stage: 2, fn: 'Angle-pattern pressure-containing body: inlet from below through the nozzle, discharge to the side outlet.',
      material: 'ASTM A216 WCB / A351 CF8M',
      dims: [D('Inlet', `${npsTxt(v.nps)} CL${v.cls} RF`, '', S('nps')), D('Outlet', `${npsTxt(v.outlet_nps)} CL${v.outlet_cls} RF`, '', S('outlet_nps')),
        D('Centre → inlet face', v.cti, 'mm', S('cti')), D('Centre → outlet face', v.cto, 'mm', S('cto')),
        D('Inlet flange OD × thk', `${f.od} × ${f.t}`, 'mm', 'standard'), D('Outlet flange OD × thk', `${fo.od} × ${fo.t}`, 'mm', 'standard')],
      note: 'API 526 standardises orifice letter, inlet/outlet size and centre-to-face dimensions; the inlet flange may be thicker than B16.5.',
    });
    parts.push(body);
    parts.push(P('nozzle', 'Nozzle', 'trim', [cyl('y', nb / 2 + 6, v.cti + 10, [0, -v.cti / 2 + 5, 0]), ring('y', nb / 2, nb / 2 + 14, 8, [0, 10, 0])], {
      group: 'Trim', stage: 2, ex: [0, -(v.cti + U * 4), 0],
      fn: 'Full-nozzle inlet: the only wetted path in normal operation; its bore is the orifice area (API 526 letters D–T).',
      material: '316 SS', dims: [D('Nozzle bore', nb, 'mm', S('port_d')), D('Orifice', 'API 526 letter (see datasheet)', '', 'estimate')],
    }));
    parts.push(P('adjusting_ring', 'Adjusting (blowdown) ring', 'accent', [ring('y', nb / 2 + 6, nb / 2 + 16, 14, [0, -6, 0])], {
      group: 'Trim', stage: 2, ex: [-U * 4, -U * 2, 0], fn: 'Threaded on the nozzle; its height sets blowdown — raising it increases blowdown and lowers the reseat pressure.',
      material: '316 SS',
    }));
    const col = [];
    col.push(P('disc', 'Disc', 'trim', [cyl('y', nb / 2 + 8, 12, [0, 20, 0])], {
      group: 'Trim', stage: 2, fn: 'Seats on the nozzle; lifts when inlet pressure × seat area exceeds the spring force (set pressure).',
      material: '316 SS / Stellite seat', dims: [D('Disc Ø', nb + 16)],
    }));
    col.push(P('disc_holder', 'Disc holder', 'steel', [cyl('y', nb / 2 + 18, 36, [0, 44, 0])], {
      group: 'Trim', stage: 2, fn: 'Carries the disc; its skirt forms the huddling chamber that gives the "pop" action.', material: '316 SS',
    }));
    col.push(P('guide', 'Guide', 'steel', [ring('y', nb / 2 + 19, nb / 2 + 28, v.body_h - 30, [0, 30 + (v.body_h - 30) / 2, 0])], {
      group: 'Trim', stage: 2, fn: 'Aligns the disc holder so the disc lifts and reseats squarely.', material: '316 SS',
    }));
    col.push(P('bonnet_gasket', 'Bonnet gasket', 'rubber', [ring('y', nb / 2 + 28, bw * 0.45, 3, [0, v.body_h + 1.5, 0])], {
      group: 'Bonnet', stage: 1, fn: 'Seals the body-to-bonnet joint (the bonnet sees back-pressure).', material: 'Graphite / spiral-wound',
    }));
    const yb = v.body_h + 3;
    const bh = v.bonnet_h;
    col.push(P('lower_washer', 'Lower spring washer', 'steel', [cyl('y', bw * 0.22, 10, [0, yb + 22, 0])], { group: 'Bonnet', stage: 1, fn: 'Lower spring button; bears on the spindle.', material: 'Carbon steel' }));
    col.push(P('spring', 'Spring', 'spring', [helix('y', bw * 0.17, Math.max(4, bw * 0.035), bh * 0.7, 7, [0, yb + 27 + bh * 0.35, 0])], {
      group: 'Bonnet', stage: 1, fn: 'Its compression, set by the adjusting screw, determines the set pressure. Selected from the vendor spring chart.',
      material: 'Chrome-alloy steel (high temperature: tungsten / Inconel)', dims: [D('Coil height ≈', bh * 0.7)],
    }));
    col.push(P('upper_washer', 'Upper spring washer', 'steel', [cyl('y', bw * 0.22, 10, [0, yb + 32 + bh * 0.7, 0])], { group: 'Bonnet', stage: 1, fn: 'Upper spring button; loaded by the adjusting screw.', material: 'Carbon steel' }));
    col.push(P('bonnet', 'Bonnet', 'act', [cyl('y', bw * 0.5, 16, [0, yb + 8, 0]), cone('y', bw * 0.42, bw * 0.26, bh, [0, yb + 16 + bh / 2, 0])], {
      group: 'Bonnet', stage: 0, fn: 'Encloses the spring. Closed bonnet for toxic or back-pressure service; open (yoke) bonnet for steam.',
      material: 'WCB / CF8M', dims: [D('Bonnet height', bh, 'mm', S('bonnet_h'))],
    }));
    col.push(P('bonnet_studs', 'Bonnet studs & nuts', 'bolt', circle('y', bw * 0.43, 6, [0, yb + 8, 0]).map((p) => cyl('y', 6, 40, p)), {
      group: 'Bonnet', stage: 0, qty: 6, fn: 'Clamp the bonnet to the body.', material: 'ASTM A193 B7 / A194 2H',
    }));
    const ys = yb + 16 + bh;
    col.push(P('adjusting_screw', 'Adjusting screw & lock nut', 'steel', [cyl('y', sd * 0.6, 70, [0, ys + 20, 0]), cyl('y', sd * 0.9, 12, [0, ys + 6, 0])], {
      group: 'Bonnet', stage: 0, fn: 'Compresses the spring to set the pressure; the lock nut holds the setting (sealed after testing).', material: '416 SS',
    }));
    col.push(P('cap', v.psv_lever ? 'Lifting lever cap' : 'Screwed cap (gas-tight)', 'act', [
      cyl('y', bw * 0.2, 60, [0, ys + 30, 0]),
      ...(v.psv_lever ? [box([bw * 1.1, 14, 22], [bw * 0.4, ys + 45, 0]), sph(14, [bw * 0.95, ys + 45, 0])] : []),
    ], {
      group: 'Bonnet', stage: 0, fn: v.psv_lever ? 'The lever lets operators lift the disc manually for testing (required on air, steam and hot water by ASME VIII).'
        : 'Covers the adjusting screw; sealed to prevent tampering.', material: 'Carbon steel',
    }));
    parts.push(...col);
    parts.push(P('spindle', 'Spindle', 'steel', [cyl('y', sd / 2, ys - 50, [0, 50 + (ys - 50) / 2, 0])], {
      group: 'Trim', stage: 1, ex: [U * 5, U * 3, 0], fn: 'Transmits the spring load to the disc holder; also carries the lifting lever load.', material: '416 SS',
      dims: [D('Diameter', sd, 'mm', S('stem_d'))],
    }));
    stack(col, 'y', partBox(body).max[1] + U * 1.5, U * 1.3);
    parts.push(flangeBolting('bolting_in', 'Inlet flange studs & nuts', 'y', -1, v.cti, f, U * 2));
    parts.push(flangeBolting('bolting_out', 'Outlet flange studs & nuts', 'x', 1, v.cto, fo, U * 2));
    return parts;
  }

  // ───────────────────────── cabinet ─────────────────────────
  function buildCabinet(v) {
    const out = [];
    const { w, h, d } = v; const ph = v.plinth_h; const n = Math.max(1, Math.round(v.bays));
    const totalW = w * n; const x0 = -totalW / 2;
    const post = 40; const skin = 2; const E = Math.max(250, d * 0.6);
    const G1 = 'Enclosure'; const G2 = 'Interior';
    out.push(P('plinth', 'Plinth (base frame)', 'plinth', [box([totalW, ph, d], [0, ph / 2, -d / 2])], {
      group: G1, stage: 0, ex: [0, -E * 0.6, 0], fn: 'Raises the enclosure for bottom cable entry and protects it from floor washing; bolted to the floor / cable trench frame.',
      material: 'Sheet steel, RAL 7022', dims: [D('Height', ph, 'mm', 'user')],
    }));
    const frame = []; const roof = []; const rear = []; const doors = []; const handles = []; const louvers = [];
    const plates = []; const modules = []; const rails = []; const eyes = []; const gland = []; const fans = [];
    const yb = ph;
    for (let b = 0; b < n; b++) {
      const cx = x0 + w * b + w / 2;
      for (const sx of [-1, 1]) for (const sz of [0, 1]) frame.push(box([post, h, post], [cx + sx * (w / 2 - post / 2), yb + h / 2, -post / 2 - sz * (d - post)]));
      frame.push(box([w, post, d], [cx, yb + post / 2, -d / 2]), box([w, post, d], [cx, yb + h - post / 2, -d / 2]));
      roof.push(box([w + 4, 3, d + 4], [cx, yb + h + 1.5, -d / 2]));
      rear.push(box([w - 4, h - 4, v.rear_door ? 20 : skin], [cx, yb + h / 2, -d - (v.rear_door ? 10 : 1)]));
      if (v.mounting_plate) plates.push(box([w - 2 * post - 20, h - 2 * post - 60, 3], [cx, yb + h / 2, -d + 60]));
      const mrows = Math.max(0, Math.round(v.modules));
      for (let m = 0; m < mrows; m++) {
        const my = yb + post + 120 + m * ((h - 2 * post - 240) / Math.max(1, mrows - 1));
        rails.push(box([w - 2 * post - 60, 35, 8], [cx, my, -d + 66]));
        const nmod = Math.floor((w - 2 * post - 80) / 45);
        for (let k = 0; k < nmod; k++) modules.push(box([40, 110, 110], [cx - (w - 2 * post - 80) / 2 + 22 + k * 45, my + 75, -d + 120]));
      }
      if (v.gland_plate) gland.push(box([w - 2 * post - 40, 4, d - 2 * post - 80], [cx, yb + 2, -d / 2]));
      if (v.fan) fans.push(box([w * 0.35, 60, w * 0.35], [cx, yb + h + 33, -d / 2]));
      if (v.lifting_eyes) {
        for (const sx of [-1, 1]) for (const sz of [0, 1]) {
          eyes.push(tor(22, 6, 'z', [cx + sx * (w / 2 - 60), yb + h + 30, -60 - sz * (d - 120)]), cyl('y', 8, 20, [cx + sx * (w / 2 - 60), yb + h + 8, -60 - sz * (d - 120)]));
        }
      }
      const nd = Number(v.doors); const dw = (w - 4) / nd; const dt = 22; const ang = (v.door_open || 0) * Math.PI / 180;
      for (let k = 0; k < nd; k++) {
        const hingeLeft = nd === 1 ? true : k === 0;
        const hx = hingeLeft ? cx - (w - 4) / 2 + k * dw : cx - (w - 4) / 2 + (k + 1) * dw;
        const s = hingeLeft ? 1 : -1;
        const th = s > 0 ? -ang : ang;
        const rot = (lx, lz) => [hx + lx * Math.cos(th) + lz * Math.sin(th), -lx * Math.sin(th) + lz * Math.cos(th)];
        const c0 = rot(s * dw / 2, dt / 2);
        doors.push(box([dw - 4, h - 4, dt], [c0[0], yb + h / 2, c0[1]], { ry: th }));
        const hp = rot(s * (dw - 50), dt + 15);
        handles.push(box([20, 160, 30], [hp[0], yb + h * 0.55, hp[1]], { ry: th }));
        if (v.louvers) for (const ly of [0.12, 0.85]) { const lp = rot(s * dw / 2, dt + 3); louvers.push(box([Math.min(320, dw * 0.5), 260, 8], [lp[0], yb + h * ly, lp[1]], { ry: th })); }
      }
    }
    const env = `${totalW} × ${h} × ${d}`;
    out.push(P('frame', 'Frame', 'cabframe', frame, { group: G1, stage: 2, fn: 'Welded / bolted profile frame carrying all panels and the internal mounting system.', material: 'Sheet steel 2 mm', dims: [D('Envelope W × H × D', env, 'mm', 'user')] }));
    out.push(P('side_panel_l', 'Side panel (left)', 'cab', [box([skin, h, d], [x0 + skin / 2, yb + h / 2, -d / 2])], { group: G1, stage: 1, ex: [-E, 0, 0], fn: 'Removable end panel; omitted between bayed enclosures.', material: 'Sheet steel 1.5 mm, RAL 7035' }));
    out.push(P('side_panel_r', 'Side panel (right)', 'cab', [box([skin, h, d], [x0 + totalW - skin / 2, yb + h / 2, -d / 2])], { group: G1, stage: 1, ex: [E, 0, 0], fn: 'Removable end panel; omitted between bayed enclosures.', material: 'Sheet steel 1.5 mm, RAL 7035' }));
    out.push(P('roof', 'Roof plate', 'cab', roof, { group: G1, stage: 1, ex: [0, E, 0], fn: 'Top cover; cable entry / fan cut-outs optional.', material: 'Sheet steel 1.5 mm' }));
    out.push(P('rear', v.rear_door ? 'Rear door' : 'Rear panel', 'cab', rear, { group: G1, stage: 1, ex: [0, 0, -E], fn: 'Rear access for termination and maintenance.', material: 'Sheet steel 2 mm' }));
    out.push(P('doors', 'Front door(s)', 'door', doors, {
      group: G1, stage: 0, ex: [0, 0, E], qty: Number(v.doors) * n,
      fn: 'Hinged front access; 130° hinges are typical. The swing radius must fit inside the maintenance clearance.',
      material: 'Sheet steel 2 mm, RAL 7035, IP54/55 gasket', dims: [D('Door width', (w - 4) / Number(v.doors)), D('Opening angle', v.door_open, '°', 'user')],
    }));
    out.push(P('handles', 'Handles & locks', 'bolt', handles, { group: G1, stage: 0, ex: [0, 0, E * 1.25], fn: 'Comfort handle with 3-point locking rod system.', material: 'Zinc die-cast' }));
    if (louvers.length) out.push(P('louvers', 'Louvres / filter fans', 'accent', louvers, { group: G1, stage: 0, ex: [0, 0, E * 1.4], fn: 'Ventilation path for heat dissipation; filter mats keep dust out.', material: 'ABS / steel' }));
    if (plates.length) out.push(P('mounting_plate', 'Mounting plate', 'plate', plates, { group: G2, stage: 1, ex: [0, 0, E * 0.55], fn: 'Galvanised plate for DIN rails, ducts and components.', material: 'Galvanised steel 3 mm', dims: [D('Plate W × H', `${w - 2 * post - 20} × ${h - 2 * post - 60}`)] }));
    if (rails.length) out.push(P('din_rails', 'DIN rails & wiring duct', 'steel', rails, { group: G2, stage: 2, ex: [0, 0, E * 0.85], fn: 'TS35 rails and slotted duct for terminals and I/O.', material: 'Steel / PVC' }));
    if (modules.length) out.push(P('modules', 'I/O modules & terminals', 'tx', modules, { group: G2, stage: 2, ex: [0, 0, E * 1.1], fn: 'Control system I/O cards, marshalling terminals, barriers / isolators.', material: '—' }));
    if (gland.length) out.push(P('gland_plate', 'Gland plate', 'bolt', gland, { group: G1, stage: 1, ex: [0, -E * 0.3, 0], fn: 'Removable plate drilled on site for cable glands.', material: 'Aluminium / steel' }));
    if (fans.length) out.push(P('fan', 'Roof fan', 'accent', fans, { group: G1, stage: 0, ex: [0, E * 1.3, 0], fn: 'Forced ventilation (exhaust) for high heat loads.', material: 'Steel housing' }));
    if (eyes.length) out.push(P('lifting_eyes', 'Lifting eye bolts', 'bolt', eyes, { group: G1, stage: 0, ex: [0, E * 1.5, 0], qty: 4 * n, fn: 'Crane lifting points; remove and plug after installation.', material: 'Forged steel, M12' }));
    if (v.clearance > 0) {
      out.push(P('clearance', `Front maintenance clearance ${v.clearance}`, 'clear', [box([totalW, h + ph, v.clearance], [0, (h + ph) / 2, v.clearance / 2 + 1])], {
        group: 'Reference', stage: 0, fn: 'Layout check: nothing may intrude into this volume.',
      }));
    }
    return out;
  }

  // ───────────────────────── instrument hook-up ─────────────────────────
  function polylineTube(points, r) {
    const prims = [];
    for (let i = 0; i < points.length - 1; i++) prims.push(tube(points[i], points[i + 1], r));
    for (let i = 1; i < points.length - 1; i++) prims.push(sph(r * 1.25, points[i]));
    return prims;
  }

  function smallValve(id, name, at, axis, size, ex) {
    const hwAxis = axis === 'y' ? 'z' : 'y';
    const top = along(hwAxis, size * 0.9, at);
    return [P(id, name, 'body', [
      box(axis === 'x' ? [size * 1.5, size * 0.8, size * 0.8] : axis === 'y' ? [size * 0.8, size * 1.5, size * 0.8] : [size * 0.8, size * 0.8, size * 1.5], at),
      cyl(hwAxis, 6, size * 0.9, along(hwAxis, size * 0.45, at)),
    ], { group: 'Valves', stage: 1, ex, fn: 'Primary isolation at the process tap (gate / globe / ball), rated to the piping class.', material: 'A105 / F316' }),
    handwheelPart(`${id}_hw`, top, size * 1.2, hwAxis, { name: `${name} handle`, group: 'Valves', ex })];
  }

  function buildHookup(v) {
    const out = [];
    const procOD = R.pipeOD[R.nearestNps(Math.min(12, v.proc_nps))] * (v.proc_nps > 12 ? v.proc_nps / 12 : 1);
    const pr = procOD / 2; const yP = v.pipe_el; const to = v.tube_od / 2;
    const dp = v.inst !== 'PT';
    const span = 1800 + (dp ? v.tap_sep : 0);
    const E = 300;
    if (v.inst === 'LT_DP') {
      out.push(P('vessel', 'Vessel shell (reference)', 'ghost', [box([2400, v.tap_sep + 1200, 20], [0, yP - v.tap_sep / 2, -pr - 210])], { group: 'Reference', stage: 0 }));
    } else {
      out.push(P('process_pipe', 'Process pipe (reference)', 'ghost', [cyl('x', pr, span, [0, yP, 0])], { group: 'Reference', stage: 0, dims: [D('Size', npsTxt(v.proc_nps), '', 'user')] }));
      if (dp) {
        const f = R.flangeOf(Math.min(12, v.proc_nps), 300);
        out.push(P('orifice', 'Orifice flange set & plate', 'flange', [
          cyl('x', f.od / 2, f.t * 1.4, [-f.t * 0.75, yP, 0]), cyl('x', f.od / 2, f.t * 1.4, [f.t * 0.75, yP, 0]), cyl('x', f.od / 2 - 8, 4, [0, yP, 0]),
        ], {
          group: 'Process', stage: 0, fn: 'Primary element: the plate creates the differential pressure; flange taps 1" each side (ISO 5167 / ASME MFC-3M).',
          material: 'A105 flanges, 316 SS plate', dims: [D('Flange', `CL300 WN, OD ${f.od}`, '', 'standard')],
        }));
      }
    }
    const dir = { top: [0, 1, 0], side: [0, 0, 1], bottom: [0, -1, 0], side45: [0, Math.SQRT1_2, Math.SQRT1_2] }[v.tap] || [0, 0, 1];
    const taps = [];
    if (v.inst === 'PT') taps.push({ name: '', at: [0, yP, 0] });
    else if (v.inst === 'LT_DP') taps.push({ name: 'HP', at: [0, yP - v.tap_sep, -pr - 200] }, { name: 'LP', at: [0, yP, -pr - 200] });
    else { const s = Math.max(40, v.tap_sep / 2); taps.push({ name: 'HP', at: [-s, yP, 0] }, { name: 'LP', at: [s, yP, 0] }); }
    const tapDir = v.inst === 'LT_DP' ? [0, 0, 1] : dir;
    const rTap = v.inst === 'LT_DP' ? 0 : pr;
    const below = v.service !== 'gas';
    let txBase;
    if (v.mount === 'stand') {
      out.push(P('stand', '2" pipe stand', 'cabframe', [
        box([220, 12, 220], [v.stand_dx, 6, v.stand_dz]), cyl('y', 30.15, v.stand_h, [v.stand_dx, v.stand_h / 2, v.stand_dz]),
        cyl('y', 34, 6, [v.stand_dx, v.stand_h + 3, v.stand_dz]),
      ], {
        group: 'Support', stage: 0, ex: [0, -E * 0.3, 0], fn: '2" Sch 40 pipe on a base plate anchored to grating or concrete; transmitter at ~1.2–1.5 m for access.',
        material: 'Galvanised carbon steel / 316 SS', dims: [D('Height', v.stand_h, 'mm', 'user'), D('Base plate', '220 × 220 × 12'), D('Anchors', '4 × M12')],
      }));
      txBase = [v.stand_dx, v.stand_h - 220, v.stand_dz + 60];
      out.push(P('ubolt', 'Mounting bracket & U-bolts', 'bolt', [
        box([70, 120, 8], [v.stand_dx, v.stand_h - 200, v.stand_dz + 36]),
        tor(36, 4, 'y', [v.stand_dx, v.stand_h - 160, v.stand_dz]), tor(36, 4, 'y', [v.stand_dx, v.stand_h - 240, v.stand_dz]),
      ], { group: 'Support', stage: 1, ex: [0, 0, E * 0.4], fn: 'Universal 2" pipe-mount bracket supplied with the transmitter.', material: '316 SS' }));
    } else {
      const t0 = taps[0].at;
      txBase = [t0[0], t0[1] + (below ? -pr - 350 : pr + 250), t0[2] + 150];
    }
    const [mx, my, mz] = txBase;
    const nV = { none: 0, '2V': 2, '3V': 3, '5V': 5 }[v.manifold] || 0;
    if (nV) {
      const prims = [box([dp ? 120 : 60, 70, 60], [mx, my, mz])];
      for (let i = 0; i < nV; i++) {
        const sx = (i / Math.max(1, nV - 1) - 0.5) * (dp ? 100 : 40);
        prims.push(cyl('z', 6, 50, [mx + sx, my - 10, mz + 55]), cyl('x', 16, 6, [mx + sx, my - 10, mz + 82]));
      }
      out.push(P('manifold', `${v.manifold} valve manifold`, 'body', prims, {
        group: 'Valves', stage: 1, ex: [0, -E * 0.2, E * 0.7],
        fn: { 2: '2-valve: block + vent/test, for gauge-pressure transmitters.', 3: '3-valve: two blocks + equalising valve, for DP transmitters.',
          5: '5-valve: two blocks, equalise and two vent/test valves (DP). Never open the equaliser with both blocks open in service.' }[nV],
        material: '316 SS bar stock, PTFE / graphite packing', dims: [D('Process connection', '1/2" NPT', '', 'estimate')],
      }));
    }
    const ty = my + 65;
    out.push(P('transmitter', v.inst === 'PT' ? 'Pressure transmitter' : 'Differential pressure transmitter', 'tx', [
      box([dp ? 110 : 60, 50, 90], [mx, ty, mz]), cyl('y', 42, 90, [mx, ty + 70, mz]),
      cyl('z', 52, 120, [mx, ty + 165, mz]), cyl('z', 50, 18, [mx, ty + 165, mz + 69]), cyl('z', 50, 18, [mx, ty + 165, mz - 69]),
      cyl('x', 11, 30, [mx + 58, ty + 165, mz - 20]),
    ], {
      group: 'Instrument', stage: 0, ex: [0, E * 0.8, E * 0.9],
      fn: '4–20 mA HART transmitter: coplanar flange, sensor module and dual-compartment electronics housing with LCD.',
      material: '316L wetted, aluminium housing, Ex d / Ex ia', dims: [D('Housing', '≈ Ø104 × 240 H')],
    }));
    if (v.sunshade) out.push(P('sunshade', 'Sunshade', 'cab', [box([240, 4, 260], [mx, ty + 300, mz]), box([240, 340, 4], [mx, ty + 130, mz - 130])], { group: 'Support', stage: 0, ex: [0, E * 1.6, 0], fn: 'Limits solar heating of the transmitter.', material: 'GRP / SS' }));
    const slope = 1 / Math.max(1, v.slope);
    taps.forEach((tp, i) => {
      const lbl = tp.name ? ` (${tp.name})` : '';
      const a = tp.at.map((c, j) => c + tapDir[j] * rTap);
      const rv = a.map((c, j) => c + tapDir[j] * 70);
      const ax = Math.abs(tapDir[1]) > 0.9 ? 'y' : 'z';
      if (v.root_valve) out.push(...smallValve(`root_valve${i}`, `Root valve${lbl}`, rv, ax, 36, tapDir.map((d) => d * E * 0.6)));
      const c = rv.map((x, j) => x + tapDir[j] * 70);
      const xOff = dp ? (i === 0 ? -27 : 27) : 0;
      const inlet = [mx + xOff, my - 15, mz - 30];
      const d1 = Math.abs(inlet[0] - c[0]) * slope; const d2 = Math.abs(inlet[2] - c[2]) * slope;
      const sgn = below ? 1 : -1;
      const yH = inlet[1] + sgn * (d1 + d2);
      const pts = [a, c];
      if (Math.abs(yH - c[1]) > 1) pts.push([c[0], yH, c[2]]);
      pts.push([inlet[0], yH - sgn * d1, c[2]]);
      pts.push(inlet);
      const len = pts.slice(1).reduce((s, p, k) => s + Math.hypot(...p.map((q, j) => q - pts[k][j])), 0);
      out.push(P(`tubing${i}`, `Impulse tubing${lbl}`, 'tube', polylineTube(pts, to), {
        group: 'Tubing', stage: 2, fn: `Transmits process pressure to the instrument. Slope 1:${v.slope} ${below ? 'down toward the instrument (liquid fills, gas vents back)' : 'down toward the tap (condensate drains back)'}.`,
        material: '316 SS seamless tube, double-ferrule fittings', dims: [D('Tube OD', v.tube_od, 'mm', 'user'), D('Run length ≈', len)],
      }));
    });
    if (v.drain) out.push(P('drain', below ? 'Drain valve' : 'Vent valve', 'body', [cyl('y', 8, 60, [mx, my - 65, mz - 40]), box([30, 30, 30], [mx, my - 105, mz - 40])], { group: 'Valves', stage: 1, ex: [0, -E * 0.6, 0], fn: 'Blow-down / venting point for maintenance and calibration.', material: '316 SS' }));
    out.push(P('floor', 'Floor / grating (reference)', 'ghost', [box([span + 600, 10, 2200], [0, -5, 300])], { group: 'Reference', stage: 0 }));
    return out;
  }

  // ───────────────────────── checks ─────────────────────────
  function checkHookup(v) {
    const w = [];
    const txY = v.mount === 'stand' ? v.stand_h - 100 : (v.service === 'gas' ? v.pipe_el + 200 : v.pipe_el - 300);
    const tapY = v.inst === 'LT_DP' ? v.pipe_el - v.tap_sep : v.pipe_el;
    if (v.service === 'gas' && txY < tapY) w.push('Gas service with the instrument below the tap — condensate will collect in the impulse lines. Mount above the tap or close-coupled.');
    if (v.service !== 'gas' && txY > tapY) w.push('Liquid/steam service with the instrument above the tap — gas pockets will form.');
    if (v.service !== 'gas' && v.tap === 'top') w.push('Top tap on a liquid/steam line — gas will enter the impulse lines.');
    if (v.service === 'gas' && v.tap === 'bottom') w.push('Bottom tap on a gas line — condensate and debris will enter the impulse lines.');
    if (v.slope < 12) w.push(`Tubing slope 1:${v.slope} is flatter than the usual 1:12.`);
    return w;
  }
  function checkCabinet(v) {
    const w = [];
    const dw = v.w / Number(v.doors);
    if (v.clearance > 0 && v.clearance < dw) w.push(`Front clearance ${v.clearance} is less than the door width ${Math.round(dw)} — the door cannot open 90°.`);
    if (v.h + v.plinth_h > 2400) w.push('Overall height > 2400 — check the transport and access route.');
    return w;
  }
  function checkValve(v) {
    const w = [];
    if (v.body === 'psv' && v.operator !== 'spring') w.push('A PSV operator must be "spring".');
    if (v.body !== 'psv' && v.operator === 'spring') w.push('The "spring" operator is only for PSVs.');
    if (v.operator === 'pneumatic_rotary' && !['ball', 'butterfly'].includes(v.body)) w.push('Rotary actuators are for quarter-turn valves (ball / butterfly).');
    if (v.operator === 'pneumatic_diaphragm' && !['globe', 'gate'].includes(v.body)) w.push('Diaphragm actuators are for linear (sliding-stem) valves.');
    if (v.operator === 'lever' && v.nps > 6) w.push('Lever operation above 6" is impractical — consider a gearbox.');
    if (v.body === 'gate' && v.service === 'control') w.push('Gate valves are not suitable for throttling control.');
    return w;
  }

  // ───────────────────────── registry ─────────────────────────
  const TYPES = {
    valve: { label: 'Valve (CV · MOV · Manual · PSV)', params: VALVE_PARAMS, build: buildValve, fit: fitValve, checks: checkValve },
    cabinet: { label: 'System Cabinet', params: CAB_PARAMS, build: buildCabinet, checks: checkCabinet },
    hookup: { label: 'Instrument Hook-up', params: HOOK_PARAMS, build: buildHookup, checks: checkHookup },
  };

  const PRESETS = [
    { id: 'cv_globe', label: 'Control valve — Globe (spring & diaphragm)', type: 'valve', set: { body: 'globe', operator: 'pneumatic_diaphragm', service: 'control' } },
    { id: 'cv_ball', label: 'Control valve — Ball (pneumatic rotary)', type: 'valve', set: { body: 'ball', operator: 'pneumatic_rotary', service: 'control', nps: 4 } },
    { id: 'cv_bfv', label: 'Control valve — Butterfly (pneumatic rotary)', type: 'valve', set: { body: 'butterfly', operator: 'pneumatic_rotary', service: 'control', nps: 8 } },
    { id: 'mov_gate', label: 'MOV — Gate', type: 'valve', set: { body: 'gate', operator: 'electric', service: 'on_off', nps: 6 } },
    { id: 'mov_globe', label: 'MOV — Globe', type: 'valve', set: { body: 'globe', operator: 'electric', service: 'on_off', nps: 4 } },
    { id: 'mov_ball', label: 'MOV — Ball', type: 'valve', set: { body: 'ball', operator: 'electric', service: 'on_off', nps: 6 } },
    { id: 'mov_bfv', label: 'MOV — Butterfly', type: 'valve', set: { body: 'butterfly', operator: 'electric', service: 'on_off', nps: 10 } },
    { id: 'man_gate', label: 'Manual — Gate (OS&Y handwheel)', type: 'valve', set: { body: 'gate', operator: 'handwheel', service: 'on_off', nps: 4 } },
    { id: 'man_globe', label: 'Manual — Globe (handwheel)', type: 'valve', set: { body: 'globe', operator: 'handwheel', service: 'on_off', nps: 3 } },
    { id: 'man_ball', label: 'Manual — Ball (lever)', type: 'valve', set: { body: 'ball', operator: 'lever', service: 'on_off', nps: 2 } },
    { id: 'man_bfv', label: 'Manual — Butterfly (gear)', type: 'valve', set: { body: 'butterfly', operator: 'gear', service: 'on_off', nps: 8 } },
    { id: 'psv', label: 'PSV — Spring-loaded (angle)', type: 'valve', set: { body: 'psv', operator: 'spring', service: 'on_off', nps: 1.5, cls: '300' } },
    { id: 'cabinet', label: 'System cabinet', type: 'cabinet', set: {} },
    { id: 'hook_pt', label: 'Hook-up — PT on pipe stand', type: 'hookup', set: { inst: 'PT' } },
    { id: 'hook_dpt', label: 'Hook-up — DP flow (orifice, close-coupled)', type: 'hookup', set: { inst: 'FT_DP', service: 'gas', mount: 'close_coupled', tap: 'top' } },
    { id: 'hook_lt', label: 'Hook-up — DP level (vessel)', type: 'hookup', set: { inst: 'LT_DP', pipe_el: 3000, tap_sep: 2000, stand_h: 900, stand_dx: 0, stand_dz: 900 } },
  ];

  /** spec = { type, inputs, parts_list? } → { values, meta, parts, warnings, bbox } */
  function build(spec) {
    const { values, meta } = resolve(spec.type, spec.inputs || {});
    const T = TYPES[spec.type];
    const raw = T.build(values, meta);
    // BOM order: by assembly group, build order within a group; reference geometry last
    const GROUP_ORDER = ['Body', 'Trim', 'Bonnet assembly', 'Bonnet', 'Enclosure', 'Interior', 'Process', 'Instrument', 'Valves', 'Tubing', 'Support',
      'Manual operator', 'Actuator', 'Accessories', 'Piping interface', 'Reference'];
    const rank = (p) => { const i = GROUP_ORDER.indexOf(p.group); return ['ghost', 'clear'].includes(p.look) ? 99 : i < 0 ? 50 : i; };
    const parts = raw.map((p, i) => [p, i]).sort((a, b) => rank(a[0]) - rank(b[0]) || (b[0].id === 'body') - (a[0].id === 'body') || a[1] - b[1]).map(([p]) => p);
    let no = 1;
    for (const p of parts) if (!['ghost', 'clear'].includes(p.look)) p.no = no++;
    // a parts list read from the drawing overrides item numbers / names / materials
    for (const row of spec.parts_list || []) {
      const p = parts.find((x) => x.id === row.part_id);
      if (!p) continue;
      if (row.item_no) p.no = row.item_no;
      if (row.material) p.dwgMaterial = row.material;
      if (row.name) p.dwgName = row.name;
      if (row.qty) p.dwgQty = row.qty;
      p.dwgLinked = true;
    }
    // with a drawing parts list, its item numbers win: renumber the other parts after the highest one
    if ((spec.parts_list || []).some((r) => parts.some((p) => p.dwgLinked && p.id === r.part_id))) {
      const nums = (spec.parts_list || []).map((r) => parseInt(r.item_no, 10)).filter(Number.isFinite);   // every drawing row, linked or not
      let next = (nums.length ? Math.max(...nums) : 0) + 1;
      for (const p of parts) if (p.no != null && !p.dwgLinked) p.no = next++;
      const key = (p) => (p.no == null ? 1e9 : Number.isFinite(parseInt(p.no, 10)) ? parseInt(p.no, 10) : 1e8);
      parts.sort((a, b) => key(a) - key(b));
    }
    const warnings = T.checks ? T.checks(values) : [];
    return { values, meta, parts, warnings, bbox: bboxOf(parts) };
  }

  /** All part ids / names a type can produce (for mapping a drawing parts list). */
  function partCatalog(typeId) {
    const seen = new Map();
    for (const pr of PRESETS.filter((p) => p.type === typeId)) {
      for (const p of build({ type: typeId, inputs: { ...pr.set, positioner: true, cv_handwheel: true, psv_lever: true } }).parts) {
        if (!seen.has(p.id) && !['ghost', 'clear'].includes(p.look)) seen.set(p.id, p.name);
      }
    }
    return [...seen].map(([id, name]) => ({ id, name }));
  }

  function describeSchema(typeId) {
    return TYPES[typeId].params.map((p) => {
      const opt = p.options ? ` [${p.options.join(' | ')}]` : '';
      const u = p.unit ? ` (${p.unit})` : '';
      return `- ${p.key}${u}${opt}: ${p.label}${p.desc ? ' — ' + p.desc : ''}`;
    }).join('\n');
  }

  return { TYPES, PRESETS, resolve, build, bboxOf, partBox, describeSchema, partCatalog };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = Anatomy;
