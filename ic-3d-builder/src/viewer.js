/* three.js 뷰어 — Anatomy 부품 목록을 메쉬로 바꿔 보여주고 내보낸다.
 * 의존: 전역 THREE (r128). OrbitControls 없이 직접 구현한 정사영 궤도 카메라.
 */
'use strict';

const Viewer = (() => {
  const MAT = {
    body: { color: 0x7d8fa3, metal: 0.55, rough: 0.45 },
    flange: { color: 0x66778a, metal: 0.6, rough: 0.4 },
    bolt: { color: 0x3c4148, metal: 0.7, rough: 0.35 },
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

  let renderer; let scene; let camera; let root; let host; let edgesOn = true;
  let state = { parts: [], groups: new Map(), bbox: null, explode: 0, labels: false, dims: true };
  let orbit = { theta: Math.PI / 4, phi: Math.acos(1 / Math.sqrt(3)), dist: 3000, target: new THREE.Vector3() };
  let onHover = () => {}; let onPick = () => {};
  let dimGroup = null; let grid = null; let hovered = null; let selected = null;
  const labelEls = new Map();

  function init(el, cbs = {}) {
    host = el;
    onHover = cbs.onHover || onHover; onPick = cbs.onPick || onPick;
    renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, alpha: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.outputEncoding = THREE.sRGBEncoding;
    el.appendChild(renderer.domElement);
    scene = new THREE.Scene();
    camera = new THREE.OrthographicCamera(-1, 1, 1, -1, -1e6, 1e6);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x445566, 0.75));
    const d1 = new THREE.DirectionalLight(0xffffff, 0.8); d1.position.set(1, 2, 1.5); scene.add(d1);
    const d2 = new THREE.DirectionalLight(0xffffff, 0.3); d2.position.set(-1.5, 0.5, -1); scene.add(d2);
    root = new THREE.Group(); scene.add(root);
    bindInput(renderer.domElement);
    new ResizeObserver(resize).observe(el);
    resize();
    loop();
  }

  function resize() {
    const w = host.clientWidth || 600; const h = host.clientHeight || 400;
    renderer.setSize(w, h, false);
    renderer.domElement.style.width = '100%'; renderer.domElement.style.height = '100%';
    updateCamera();
  }

  function updateCamera() {
    if (!renderer) return;
    const w = host.clientWidth || 600; const h = host.clientHeight || 400;
    const half = orbit.dist / 2; const asp = w / h;
    camera.left = -half * asp; camera.right = half * asp; camera.top = half; camera.bottom = -half;
    const t = orbit.target;
    camera.position.set(
      t.x + 1e4 * Math.sin(orbit.phi) * Math.sin(orbit.theta),
      t.y + 1e4 * Math.cos(orbit.phi),
      t.z + 1e4 * Math.sin(orbit.phi) * Math.cos(orbit.theta));
    camera.up.set(0, 1, 0);
    camera.lookAt(t);
    camera.updateProjectionMatrix();
  }

  function setBackground(css) { renderer.setClearColor(new THREE.Color(css), 1); }

  // ───────── 도형 → 메쉬 ─────────
  const matCache = new Map();
  function material(key) {
    if (matCache.has(key)) return matCache.get(key);
    const m = MAT[key] || MAT.body;
    const mat = new THREE.MeshStandardMaterial({
      color: m.color, metalness: m.metal, roughness: m.rough,
      transparent: m.opacity != null, opacity: m.opacity ?? 1, depthWrite: m.opacity == null,
      side: m.opacity != null ? THREE.DoubleSide : THREE.FrontSide,
    });
    matCache.set(key, mat);
    return mat;
  }

  const Y = new THREE.Vector3(0, 1, 0);
  function axisQuat(axis) {
    const q = new THREE.Quaternion();
    if (axis === 'x') q.setFromAxisAngle(new THREE.Vector3(0, 0, 1), -Math.PI / 2);
    else if (axis === 'z') q.setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 2);
    return q;
  }

  function primMesh(pr, mat) {
    let geo; const mesh = new THREE.Mesh(undefined, mat);
    switch (pr.k) {
      case 'cyl': {
        geo = new THREE.CylinderGeometry(pr.r2 ?? pr.r, pr.r, Math.max(0.1, pr.h), 40);
        const q = axisQuat(pr.axis);
        if (pr.rotY) q.premultiply(new THREE.Quaternion().setFromAxisAngle(Y, pr.rotY));
        mesh.quaternion.copy(q);
        break;
      }
      case 'box':
        geo = new THREE.BoxGeometry(...pr.s.map((v) => Math.max(0.1, v)));
        if (pr.ry) mesh.rotation.y = pr.ry;
        break;
      case 'sph':
        geo = new THREE.SphereGeometry(pr.r, 36, 24);
        if (pr.scale) mesh.scale.set(...pr.scale);
        break;
      case 'tor':
        geo = new THREE.TorusGeometry(pr.R, pr.r, 12, 48);
        if (pr.axis === 'y') mesh.rotation.x = Math.PI / 2;
        else if (pr.axis === 'x') mesh.rotation.y = Math.PI / 2;
        break;
      case 'tube': {
        const a = new THREE.Vector3(...pr.a); const b = new THREE.Vector3(...pr.b);
        const len = a.distanceTo(b);
        geo = new THREE.CylinderGeometry(pr.r, pr.r, Math.max(0.1, len), 16);
        mesh.position.copy(a.clone().add(b).multiplyScalar(0.5));
        if (len > 0) mesh.quaternion.setFromUnitVectors(Y, b.clone().sub(a).normalize());
        mesh.geometry = geo;
        return mesh;
      }
      default: return null;
    }
    mesh.geometry = geo;
    mesh.position.set(...pr.at);
    return mesh;
  }

  function clear() {
    for (const g of state.groups.values()) {
      g.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
      root.remove(g);
    }
    state.groups.clear();
    for (const el of labelEls.values()) el.remove();
    labelEls.clear();
  }

  /** model = Anatomy.build() 결과 */
  function show(model, { keepView = false } = {}) {
    clear();
    state.parts = model.parts; state.bbox = model.bbox;
    for (const p of model.parts) {
      const g = new THREE.Group(); g.name = p.id; g.userData.part = p;
      const mat = material(p.mat);
      for (const pr of p.prims) {
        const m = primMesh(pr, mat); if (!m) continue;
        m.userData.partId = p.id;
        g.add(m);
        if (edgesOn && !['ghost', 'clear'].includes(p.mat)) {
          const e = new THREE.LineSegments(new THREE.EdgesGeometry(m.geometry, 35),
            new THREE.LineBasicMaterial({ color: 0x1b1f24, transparent: true, opacity: 0.35 }));
          e.position.copy(m.position); e.quaternion.copy(m.quaternion); e.scale.copy(m.scale);
          e.userData.edge = true;
          g.add(e);
        }
      }
      root.add(g); state.groups.set(p.id, g);
      if (state.labels) makeLabel(p);
    }
    applyExplode();
    drawDims();
    if (!keepView) fit();
  }

  function fit(view) {
    const b = state.bbox; if (!b || !isFinite(b.size[0])) return;
    orbit.target.set((b.min[0] + b.max[0]) / 2, (b.min[1] + b.max[1]) / 2, (b.min[2] + b.max[2]) / 2);
    orbit.dist = Math.max(...b.size) * 1.3 + 150;
    if (view) setView(view, true);
    updateCamera();
  }

  function setView(name, silent) {
    const iso = Math.acos(1 / Math.sqrt(3));
    const v = { iso: [Math.PI / 4, iso], iso2: [-Math.PI / 4 + Math.PI, iso], front: [0, Math.PI / 2],
      side: [Math.PI / 2, Math.PI / 2], top: [0, 0.0001], back: [Math.PI, Math.PI / 2] }[name];
    if (!v) return;
    [orbit.theta, orbit.phi] = v;
    if (!silent) updateCamera();
  }

  function setExplode(k) { state.explode = k; applyExplode(); drawDims(); }
  function applyExplode() {
    const b = state.bbox; if (!b) return;
    const s = Math.max(...b.size) * 0.35 * state.explode;
    for (const g of state.groups.values()) {
      const ex = g.userData.part.ex || [0, 0, 0];
      g.position.set(ex[0] * s, ex[1] * s, ex[2] * s);
    }
  }

  function setVisible(id, vis) { const g = state.groups.get(id); if (g) g.visible = vis; }
  function setEdges(on) { edgesOn = on; if (state.parts.length) show({ parts: state.parts, bbox: state.bbox }, { keepView: true }); }
  function setLabels(on) {
    state.labels = on;
    for (const el of labelEls.values()) el.remove();
    labelEls.clear();
    if (on) for (const p of state.parts) if (!['ghost', 'clear'].includes(p.mat)) makeLabel(p);
  }
  function setDims(on) { state.dims = on; drawDims(); }

  function makeLabel(p) {
    if (['ghost', 'clear'].includes(p.mat) || p.id.endsWith('_bolts')) return;
    const el = document.createElement('div');
    el.className = 'v-label'; el.textContent = p.label;
    host.appendChild(el); labelEls.set(p.id, el);
  }

  function partCenter(id) {
    const g = state.groups.get(id); if (!g) return null;
    const box = new THREE.Box3().setFromObject(g);
    return box.getCenter(new THREE.Vector3());
  }

  // ───────── 치수 박스 ─────────
  function textSprite(text, size) {
    const c = document.createElement('canvas'); const ctx = c.getContext('2d');
    const fs = 44; ctx.font = `600 ${fs}px system-ui, sans-serif`;
    const w = ctx.measureText(text).width + 24; c.width = w; c.height = fs + 20;
    ctx.font = `600 ${fs}px system-ui, sans-serif`;
    ctx.fillStyle = 'rgba(20,24,30,0.82)'; ctx.fillRect(0, 0, c.width, c.height);
    ctx.fillStyle = '#ffffff'; ctx.textBaseline = 'middle'; ctx.fillText(text, 12, c.height / 2 + 2);
    const tex = new THREE.CanvasTexture(c); tex.minFilter = THREE.LinearFilter;
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
    sp.scale.set(size * c.width / c.height, size, 1);
    sp.renderOrder = 10;
    return sp;
  }

  function drawDims() {
    if (dimGroup) { dimGroup.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material?.map) o.material.map.dispose(); }); scene.remove(dimGroup); dimGroup = null; }
    if (grid) { scene.remove(grid); grid = null; }
    const b0 = state.bbox; if (!b0 || !isFinite(b0.size[0])) return;
    // 분해 상태를 반영한 실제 경계 (ghost/clear 제외)
    const bb = new THREE.Box3();
    for (const g of state.groups.values()) {
      if (!g.visible || ['ghost', 'clear'].includes(g.userData.part.mat)) continue;
      bb.expandByObject(g);
    }
    if (bb.isEmpty()) return;
    const size = Math.max(...b0.size);
    grid = new THREE.GridHelper(size * 3, 30, 0x8899aa, 0x8899aa);
    grid.material.transparent = true; grid.material.opacity = 0.18;
    grid.position.set((bb.min.x + bb.max.x) / 2, bb.min.y - 0.5, (bb.min.z + bb.max.z) / 2);
    scene.add(grid);
    if (!state.dims) return;
    dimGroup = new THREE.Group();
    const lm = new THREE.LineBasicMaterial({ color: 0xe0a526 });
    const helper = new THREE.Box3Helper(bb, 0xe0a526); helper.material.transparent = true; helper.material.opacity = 0.5;
    dimGroup.add(helper);
    const s = bb.getSize(new THREE.Vector3());
    const ts = size * 0.045;
    const mk = (a, b, label, off) => {
      const g = new THREE.BufferGeometry().setFromPoints([a, b]);
      dimGroup.add(new THREE.Line(g, lm));
      const sp = textSprite(label, ts); sp.position.copy(a.clone().add(b).multiplyScalar(0.5)).add(off);
      dimGroup.add(sp);
    };
    const o = ts * 0.9;
    mk(new THREE.Vector3(bb.min.x, bb.min.y, bb.max.z + o), new THREE.Vector3(bb.max.x, bb.min.y, bb.max.z + o),
      `L ${Math.round(s.x)}`, new THREE.Vector3(0, -o, o));
    mk(new THREE.Vector3(bb.max.x + o, bb.min.y, bb.min.z), new THREE.Vector3(bb.max.x + o, bb.min.y, bb.max.z),
      `W ${Math.round(s.z)}`, new THREE.Vector3(o, -o, 0));
    mk(new THREE.Vector3(bb.max.x + o, bb.min.y, bb.max.z), new THREE.Vector3(bb.max.x + o, bb.max.y, bb.max.z),
      `H ${Math.round(s.y)}`, new THREE.Vector3(o * 2, 0, 0));
    scene.add(dimGroup);
  }

  // ───────── 입력 ─────────
  function bindInput(el) {
    let drag = null;
    el.addEventListener('contextmenu', (e) => e.preventDefault());
    el.addEventListener('pointerdown', (e) => {
      drag = { x: e.clientX, y: e.clientY, btn: e.button, shift: e.shiftKey, moved: false };
      el.setPointerCapture(e.pointerId);
    });
    el.addEventListener('pointermove', (e) => {
      if (!drag) { hoverAt(e); return; }
      const dx = e.clientX - drag.x; const dy = e.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 2) drag.moved = true;
      drag.x = e.clientX; drag.y = e.clientY;
      if (drag.btn === 2 || drag.btn === 1 || drag.shift) {
        const k = orbit.dist / (host.clientHeight || 400);
        const right = new THREE.Vector3().setFromMatrixColumn(camera.matrix, 0);
        const up = new THREE.Vector3().setFromMatrixColumn(camera.matrix, 1);
        orbit.target.addScaledVector(right, -dx * k).addScaledVector(up, dy * k);
      } else {
        orbit.theta -= dx * 0.008;
        orbit.phi = Math.max(0.0001, Math.min(Math.PI - 0.0001, orbit.phi - dy * 0.008));
      }
      updateCamera();
    });
    el.addEventListener('pointerup', (e) => {
      if (drag && !drag.moved && drag.btn === 0) {
        const hit = pick(e); selected = hit; onPick(hit); highlight();
      }
      drag = null;
    });
    el.addEventListener('wheel', (e) => {
      e.preventDefault();
      orbit.dist *= Math.exp(e.deltaY * 0.0012);
      orbit.dist = Math.max(20, Math.min(1e6, orbit.dist));
      updateCamera();
    }, { passive: false });
  }

  const ray = new THREE.Raycaster();
  function pick(e) {
    const r = renderer.domElement.getBoundingClientRect();
    const m = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(m, camera);
    const meshes = [];
    for (const g of state.groups.values()) {
      if (!g.visible || ['ghost', 'clear'].includes(g.userData.part.mat)) continue;
      g.traverse((o) => { if (o.isMesh) meshes.push(o); });
    }
    const hit = ray.intersectObjects(meshes, false)[0];
    return hit ? hit.object.userData.partId : null;
  }
  function hoverAt(e) {
    const id = pick(e);
    if (id !== hovered) { hovered = id; highlight(); onHover(id, e); }
    else if (id) onHover(id, e);
  }
  function select(id) { selected = id; highlight(); }
  function highlight() {
    for (const [id, g] of state.groups) {
      const on = id === hovered || id === selected;
      g.traverse((o) => {
        if (!o.isMesh) return;
        if (on && !o.userData.hl) { o.userData.base = o.material; o.material = o.material.clone(); o.material.emissive = new THREE.Color(id === selected ? 0xe0a526 : 0x335577); o.material.emissiveIntensity = 0.55; o.userData.hl = true; }
        if (!on && o.userData.hl) { o.material.dispose(); o.material = o.userData.base; o.userData.hl = false; }
      });
    }
  }

  function loop() {
    requestAnimationFrame(loop);
    renderer.render(scene, camera);
    if (labelEls.size) {
      const w = host.clientWidth; const h = host.clientHeight;
      for (const [id, el] of labelEls) {
        const g = state.groups.get(id);
        if (!g || !g.visible) { el.style.display = 'none'; continue; }
        const c = partCenter(id); if (!c) continue;
        const p = c.project(camera);
        el.style.display = '';
        el.style.transform = `translate(${(p.x + 1) / 2 * w}px, ${(1 - p.y) / 2 * h}px) translate(-50%, -50%)`;
      }
    }
  }

  // ───────── 내보내기 ─────────
  function exportMeshes(includeRef) {
    const out = [];
    root.updateMatrixWorld(true);
    for (const [id, g] of state.groups) {
      if (!g.visible) continue;
      const mat = g.userData.part.mat;
      if (!includeRef && ['ghost', 'clear'].includes(mat)) continue;
      g.traverse((o) => { if (o.isMesh) out.push({ id, label: g.userData.part.label, mesh: o }); });
    }
    return out;
  }

  function triangles(mesh, cb) {
    const geo = mesh.geometry; const pos = geo.attributes.position; const idx = geo.index;
    const m = mesh.matrixWorld;
    const v = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()];
    const n = idx ? idx.count : pos.count;
    for (let i = 0; i < n; i += 3) {
      for (let k = 0; k < 3; k++) {
        const j = idx ? idx.getX(i + k) : i + k;
        v[k].fromBufferAttribute(pos, j).applyMatrix4(m);
      }
      cb(v[0], v[1], v[2]);
    }
  }

  function toSTL() {
    const tris = [];
    for (const { mesh } of exportMeshes(false)) triangles(mesh, (a, b, c) => tris.push([a.clone(), b.clone(), c.clone()]));
    const buf = new ArrayBuffer(84 + tris.length * 50); const dv = new DataView(buf);
    const head = 'IC-3D-Builder STL (mm)';
    for (let i = 0; i < head.length; i++) dv.setUint8(i, head.charCodeAt(i));
    dv.setUint32(80, tris.length, true);
    let o = 84; const e1 = new THREE.Vector3(); const e2 = new THREE.Vector3();
    for (const [a, b, c] of tris) {
      e1.subVectors(b, a); e2.subVectors(c, a); const nrm = e1.cross(e2).normalize();
      for (const v of [nrm, a, b, c]) { dv.setFloat32(o, v.x, true); dv.setFloat32(o + 4, v.y, true); dv.setFloat32(o + 8, v.z, true); o += 12; }
      dv.setUint16(o, 0, true); o += 2;
    }
    return new Blob([buf], { type: 'model/stl' });
  }

  function toOBJ(name) {
    const L = [`# IC-3D-Builder OBJ, units mm, Y-up`, `o ${name || 'item'}`];
    let base = 1; let cur = null;
    for (const { id, mesh } of exportMeshes(false)) {
      if (id !== cur) { L.push(`g ${id}`); cur = id; }
      const start = base; let cnt = 0; const vs = [];
      triangles(mesh, (a, b, c) => { vs.push(a.clone(), b.clone(), c.clone()); cnt += 3; });
      for (const v of vs) L.push(`v ${v.x.toFixed(2)} ${v.y.toFixed(2)} ${v.z.toFixed(2)}`);
      for (let i = 0; i < cnt; i += 3) L.push(`f ${start + i} ${start + i + 1} ${start + i + 2}`);
      base += cnt;
    }
    return new Blob([L.join('\n')], { type: 'text/plain' });
  }

  function toPNG() { renderer.render(scene, camera); return renderer.domElement.toDataURL('image/png'); }

  const matColor = (k) => '#' + (MAT[k] || MAT.body).color.toString(16).padStart(6, '0');

  return { matColor, init, show, fit, setView, setExplode, setVisible, setEdges, setLabels, setDims, setBackground, select, toSTL, toOBJ, toPNG, updateCamera };
})();
