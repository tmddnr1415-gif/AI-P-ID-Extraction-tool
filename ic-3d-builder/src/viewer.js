/* three.js viewer for Anatomy part lists.
 *
 * Interaction model (anatomy-style):
 *   wheel in   → first explodes the assembly step by step (camera keeps everything framed);
 *                once fully exploded, zooms the camera toward the cursor
 *   wheel out  → zooms back out to the framed view, then re-assembles
 *   drag → orbit · right / shift-drag → pan · click → select · double-click → isolate
 * Numbered balloons (item no. + part name) follow each part on screen.
 * Depends on global THREE (r128).
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

  // ───────── procedural textures (canvas) ─────────
  const texCache = new Map();
  function canvasTex(key, w, h, paint, { srgb = false, repeat = null } = {}) {
    if (texCache.has(key)) return texCache.get(key);
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    paint(c.getContext('2d'), w, h);
    const t = new THREE.CanvasTexture(c);
    if (srgb) t.encoding = THREE.sRGBEncoding;
    if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...repeat); }
    t.anisotropy = 4;
    texCache.set(key, t);
    return t;
  }
  /** orange-peel / sand-cast bump */
  const castTex = () => canvasTex('cast', 256, 256, (g, w, h) => {
    const img = g.createImageData(w, h);
    for (let i = 0; i < w * h; i++) { const v = 128 + (Math.random() - 0.5) * 70; img.data.set([v, v, v, 255], i * 4); }
    g.putImageData(img, 0, 0); g.filter = 'blur(1.4px)'; g.drawImage(g.canvas, 0, 0);
  }, { repeat: [3, 3] });
  const paintTex = () => canvasTex('paint', 256, 256, (g, w, h) => {
    const img = g.createImageData(w, h);
    for (let i = 0; i < w * h; i++) { const v = 128 + (Math.random() - 0.5) * 30; img.data.set([v, v, v, 255], i * 4); }
    g.putImageData(img, 0, 0); g.filter = 'blur(2px)'; g.drawImage(g.canvas, 0, 0);
  }, { repeat: [2, 2] });
  /** machined / brushed roughness streaks */
  const brushedTex = () => canvasTex('brushed', 256, 256, (g, w, h) => {
    g.fillStyle = '#7a7a7a'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 900; i++) {
      const y = Math.random() * h; const a = 0.04 + Math.random() * 0.1;
      g.strokeStyle = Math.random() < 0.5 ? `rgba(255,255,255,${a})` : `rgba(0,0,0,${a})`;
      g.lineWidth = 0.6 + Math.random(); g.beginPath(); g.moveTo(0, y); g.lineTo(w, y + (Math.random() - 0.5) * 2); g.stroke();
    }
  }, { repeat: [1, 1] });
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
      // engraved stainless nameplate
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
    }, { srgb: true });
  }
  const dialTex = () => canvasTex('dial', 256, 256, (g, w) => {
    const c = w / 2;
    g.fillStyle = '#f4f2ec'; g.beginPath(); g.arc(c, c, c, 0, 7); g.fill();
    g.strokeStyle = '#222'; g.lineWidth = 3;
    for (let i = 0; i <= 40; i++) {
      const a = Math.PI * 0.75 + i / 40 * Math.PI * 1.5; const r0 = i % 5 ? c * 0.78 : c * 0.7;
      g.lineWidth = i % 5 ? 2 : 4; g.beginPath(); g.moveTo(c + Math.cos(a) * r0, c + Math.sin(a) * r0); g.lineTo(c + Math.cos(a) * c * 0.88, c + Math.sin(a) * c * 0.88); g.stroke();
    }
    g.strokeStyle = '#c0281e'; g.lineWidth = 3; g.beginPath(); g.arc(c, c, c * 0.62, Math.PI * 1.9, Math.PI * 2.25); g.stroke();
    g.strokeStyle = '#111'; g.lineWidth = 6; g.beginPath(); g.moveTo(c, c); g.lineTo(c + Math.cos(Math.PI * 1.55) * c * 0.72, c + Math.sin(Math.PI * 1.55) * c * 0.72); g.stroke();
    g.fillStyle = '#111'; g.beginPath(); g.arc(c, c, c * 0.07, 0, 7); g.fill();
    g.font = `600 ${w * 0.08}px Arial`; g.textAlign = 'center'; g.fillText('bar', c, c * 1.45);
  }, { srgb: true });
  const haloTex = () => canvasTex('halo', 256, 256, (g, w) => {
    const gr = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2);
    gr.addColorStop(0, 'rgba(0,0,0,0.55)'); gr.addColorStop(0.45, 'rgba(0,0,0,0.22)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gr; g.fillRect(0, 0, w, w);
  });

  /** cutaway section removes the front half of shells / housings (these looks and part ids) */
  const CUT_LOOKS = new Set(['body', 'flange', 'act', 'cab', 'door', 'cabframe', 'plinth', 'ghost']);
  const CUT_IDS = new Set(['cage', 'guide', 'liner', 'bonnet', 'gland', 'packing', 'body_connector', 'mounting_pad', 'thrust_base', 'lower_casing', 'upper_casing', 'gearcase']);
  const REF = new Set(['ghost', 'clear']);

  let renderer; let scene; let camera; let root; let host; let overlay;
  let ortho; let persp; let keyLight; let stage; let shadowCatcher; let halo; let pedestal; let envMap = null;
  const FOV = 28;
  const opts = { edges: false, labels: 'auto', dims: false, section: false, autoExplode: true, insetRight: 0, style: 'real' };
  const S = { parts: [], groups: new Map(), bbox: null, e: 0, eT: 0, focus: null, hovered: null, selected: null };
  const orbit = { theta: Math.PI / 4, phi: Math.acos(1 / Math.sqrt(3)), dist: 3000, target: new THREE.Vector3() };
  const goal = { dist: 3000, target: new THREE.Vector3(), follow: true, refit: true, fitDist: 3000 };
  let cb = { onHover() {}, onPick() {}, onExplode() {}, onFocus() {} };
  let dimGroup = null; let grid = null; let dirtyDims = true;
  const balloons = new Map();
  const clipPlane = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);

  function init(el, callbacks = {}) {
    host = el; cb = { ...cb, ...callbacks };
    renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, alpha: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.localClippingEnabled = true;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    el.appendChild(renderer.domElement);
    overlay = document.createElement('div'); overlay.className = 'v-overlay'; el.appendChild(overlay);
    scene = new THREE.Scene();
    ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, -1e6, 1e6);
    persp = new THREE.PerspectiveCamera(FOV, 1, 1, 1e6);
    camera = opts.style === 'real' ? persp : ortho;
    // studio rig: soft sky/ground fill, warm key (casts shadows), cool fill, rim
    scene.add(new THREE.HemisphereLight(0xffffff, 0x3a3f46, 0.35));
    keyLight = new THREE.DirectionalLight(0xfff4e8, 1.6);
    keyLight.castShadow = true; keyLight.shadow.mapSize.set(2048, 2048); keyLight.shadow.bias = -0.0004; keyLight.shadow.normalBias = 0.6;
    keyLight.shadow.radius = 4;
    scene.add(keyLight); scene.add(keyLight.target);
    const fill = new THREE.DirectionalLight(0xe4ecff, 0.45); fill.position.set(-1.6, 0.6, 1.2); scene.add(fill);
    const rim = new THREE.DirectionalLight(0xffffff, 0.55); rim.position.set(-0.8, 1.2, -1.6); scene.add(rim);
    root = new THREE.Group(); scene.add(root);
    stage = new THREE.Group(); scene.add(stage);
    shadowCatcher = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.ShadowMaterial({ opacity: 0.22 }));
    shadowCatcher.rotation.x = -Math.PI / 2; shadowCatcher.receiveShadow = true; shadowCatcher.visible = false; stage.add(shadowCatcher);   // the pedestal catches shadows; nothing floats
    halo = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: haloTex(), transparent: true, depthWrite: false, toneMapped: false }));
    halo.rotation.x = -Math.PI / 2; halo.renderOrder = 1; stage.add(halo);
    pedestal = new THREE.Mesh(new THREE.CylinderGeometry(1, 1.03, 1, 96), new THREE.MeshStandardMaterial({ color: new THREE.Color(0xd8d6d1).convertSRGBToLinear(), roughness: 0.8, metalness: 0 }));
    pedestal.receiveShadow = true; stage.add(pedestal);
    envMap = buildEnv();
    applyStyle();
    bindInput(renderer.domElement);
    new ResizeObserver(() => { resize(); goal.refit = true; }).observe(el);
    resize();
    loop();
  }

  /** studio environment: soft gradient sky with two softbox strips → PMREM, for metal reflections */
  function buildEnv() {
    const c = document.createElement('canvas'); c.width = 512; c.height = 256; const g = c.getContext('2d');
    const gr = g.createLinearGradient(0, 0, 0, 256);
    gr.addColorStop(0, '#8e949c'); gr.addColorStop(0.46, '#6b7179'); gr.addColorStop(0.54, '#3c4148'); gr.addColorStop(1, '#1d2024');
    g.fillStyle = gr; g.fillRect(0, 0, 512, 256);
    // softboxes: a big key box, a strip light and a small warm kicker
    g.fillStyle = '#ffffff'; g.fillRect(70, 46, 80, 46); g.fillRect(340, 34, 110, 18);
    g.fillStyle = '#ffe9d0'; g.fillRect(210, 80, 30, 20);
    const t = new THREE.CanvasTexture(c); t.mapping = THREE.EquirectangularReflectionMapping; t.encoding = THREE.sRGBEncoding;
    const pm = new THREE.PMREMGenerator(renderer);
    const env = pm.fromEquirectangular(t).texture; pm.dispose(); t.dispose();
    return env;
  }
  function applyStyle() {
    const real = opts.style === 'real';
    camera = real ? persp : ortho;
    renderer.toneMapping = real ? THREE.ACESFilmicToneMapping : THREE.NoToneMapping;
    renderer.toneMappingExposure = 1.1;
    scene.environment = real ? envMap : null;
    keyLight.intensity = real ? 1.5 : 0.8;
    keyLight.castShadow = real;
    stage.visible = real;
    host.classList.toggle('real', real);
    for (const m of matCache.values()) m.dispose();
    matCache.clear();
  }
  /** pedestal, halo and shadow camera sized to the (exploded) model */
  function placeStage() {
    if (!S.bbox || !isFinite(S.bbox.size[0])) return;
    const live = liveBox();
    const b = live.isEmpty() ? new THREE.Box3(new THREE.Vector3(...S.bbox.min), new THREE.Vector3(...S.bbox.max)) : live;
    const sz = b.getSize(new THREE.Vector3()); const c = b.getCenter(new THREE.Vector3());
    const assembledMin = S.bbox.min[1];
    const foot = Math.max(S.bbox.size[0], S.bbox.size[2]);
    const R = foot * 0.62 + 40; const H = Math.max(14, foot * 0.04);
    const y0 = Math.min(assembledMin, b.min.y) - 2;
    pedestal.scale.set(R, H, R); pedestal.position.set((S.bbox.min[0] + S.bbox.max[0]) / 2, y0 - H / 2, (S.bbox.min[2] + S.bbox.max[2]) / 2);
    shadowCatcher.scale.set(R * 6, R * 6, 1); shadowCatcher.position.set(pedestal.position.x, y0 + 0.4, pedestal.position.z);
    halo.scale.set(foot * 1.25 + 60, foot * 1.25 + 60, 1); halo.position.set(pedestal.position.x, y0 + 0.8, pedestal.position.z);
    const span = Math.max(sz.x, sz.y, sz.z) * 0.9 + 200;
    keyLight.position.set(c.x + span * 0.45, c.y + span * 2.4, c.z + span * 0.7);   // high key: shadows land on the pedestal
    keyLight.target.position.copy(c);
    const sc = keyLight.shadow.camera;
    sc.left = -span; sc.right = span; sc.top = span; sc.bottom = -span; sc.near = 1; sc.far = span * 5;
    sc.updateProjectionMatrix();
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
    const t = orbit.target;
    const dir = new THREE.Vector3(Math.sin(orbit.phi) * Math.sin(orbit.theta), Math.cos(orbit.phi), Math.sin(orbit.phi) * Math.cos(orbit.theta));
    // orthographic: orbit.dist is the visible height; perspective: the same height at the target plane
    ortho.left = -half * asp; ortho.right = half * asp; ortho.top = half; ortho.bottom = -half;
    ortho.position.copy(t).addScaledVector(dir, 1e4);
    const D = half / Math.tan(FOV * Math.PI / 360);
    persp.aspect = asp; persp.near = Math.max(1, D * 0.02); persp.far = D * 50;
    persp.position.copy(t).addScaledVector(dir, D);
    for (const cam of [ortho, persp]) { cam.up.set(0, 1, 0); cam.lookAt(t); cam.updateProjectionMatrix(); cam.updateMatrixWorld(); }
  }

  let bgCss = '#e9edf1';
  function setBackground(css) { bgCss = css || bgCss; renderer.setClearColor(new THREE.Color(bgCss), opts.style === 'real' ? 0 : 1); }

  // ───────── materials & meshes ─────────
  const matCache = new Map();
  function material(look, cut) {
    const key = `${look}|${cut ? 1 : 0}`;
    if (matCache.has(key)) return matCache.get(key);
    if (opts.style === 'real') {
      const m = REAL[look] || REAL.body;
      const mat = new THREE.MeshPhysicalMaterial({
        color: new THREE.Color(m.color).convertSRGBToLinear(), metalness: m.metal, roughness: m.rough, clearcoat: m.clear || 0, clearcoatRoughness: 0.25,
        envMapIntensity: m.metal > 0.6 ? 1.15 : 0.55,
        transparent: m.opacity != null, opacity: m.opacity ?? 1, depthWrite: m.opacity == null,
        side: (m.opacity != null || cut) ? THREE.DoubleSide : THREE.FrontSide,
        clippingPlanes: cut ? [clipPlane] : [],
      });
      if (m.bump === 'cast') { mat.bumpMap = castTex(); mat.bumpScale = 0.9; }
      if (m.bump === 'paint') { mat.bumpMap = paintTex(); mat.bumpScale = 0.35; }
      if (m.rmap === 'brushed') { mat.roughnessMap = brushedTex(); }
      matCache.set(key, mat);
      return mat;
    }
    const m = LOOK[look] || LOOK.body;
    const mat = new THREE.MeshStandardMaterial({
      color: m.color, metalness: m.metal, roughness: m.rough,
      transparent: m.opacity != null, opacity: m.opacity ?? 1, depthWrite: m.opacity == null,
      side: (m.opacity != null || cut) ? THREE.DoubleSide : THREE.FrontSide,
      clippingPlanes: cut ? [clipPlane] : [],
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

  class Helix extends THREE.Curve {
    constructor(R, h, turns) { super(); this.R = R; this.h = h; this.turns = turns; }
    getPoint(t, out = new THREE.Vector3()) {
      const a = t * this.turns * Math.PI * 2;
      return out.set(this.R * Math.cos(a), (t - 0.5) * this.h, this.R * Math.sin(a));
    }
  }

  /** profile [[s, r, smooth?]…] → turned solid; creases at every knot not marked smooth */
  function latheObj(pr, mat) {
    let pts = pr.pts.map((p) => [p[0], Math.max(0, p[1]), p[2]]);
    if (pts[pts.length - 1][0] < pts[0][0]) pts = pts.slice().reverse();
    const g = new THREE.Group();
    let run = [pts[0]];
    const flush = () => {
      if (run.length >= 2) {
        const geo = new THREE.LatheGeometry(run.map(([s, r]) => new THREE.Vector2(r, s)), 64);
        const m = new THREE.Mesh(geo, mat); g.add(m);
      }
    };
    for (let i = 1; i < pts.length; i++) {
      run.push(pts[i]);
      if (!pts[i][2] || i === pts.length - 1) { flush(); run = [pts[i]]; }
    }
    g.quaternion.copy(axisQuat(pr.axis));
    g.position.set(...pr.at);
    return g;
  }
  function rboxGeo(s, r) {
    const bev = Math.min(r, s[2] / 2 - 0.05, s[0] / 2 - 0.05, s[1] / 2 - 0.05);
    const w = s[0] - 2 * bev; const h = s[1] - 2 * bev; const cr = Math.max(0.01, Math.min(r, w / 2 - 0.01, h / 2 - 0.01));
    const sh = new THREE.Shape();
    sh.moveTo(-w / 2 + cr, -h / 2); sh.lineTo(w / 2 - cr, -h / 2); sh.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + cr);
    sh.lineTo(w / 2, h / 2 - cr); sh.quadraticCurveTo(w / 2, h / 2, w / 2 - cr, h / 2); sh.lineTo(-w / 2 + cr, h / 2);
    sh.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - cr); sh.lineTo(-w / 2, -h / 2 + cr); sh.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + cr, -h / 2);
    const depth = Math.max(0.1, s[2] - 2 * bev);
    const geo = new THREE.ExtrudeGeometry(sh, { depth, bevelEnabled: bev > 0.05, bevelThickness: bev, bevelSize: bev, bevelSegments: 3, curveSegments: 5 });
    geo.translate(0, 0, -depth / 2);
    return geo;
  }
  const FACE_Q = {
    z: new THREE.Quaternion(), '-z': new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI),
    x: new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI / 2), '-x': new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -Math.PI / 2),
    y: new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2),
  };
  function primMesh(pr, mat) {
    let geo; const mesh = new THREE.Mesh(undefined, mat);
    switch (pr.k) {
      case 'lathe': return latheObj(pr, mat);
      case 'rbox':
        geo = rboxGeo(pr.s, pr.r ?? 4);
        if (pr.ry) mesh.rotation.y = pr.ry;
        break;
      case 'plate': {
        // thin plate whose front face carries an engraved nameplate or an LCD
        const [w, h, t] = pr.s;
        const tex = textTex(pr.lines || [], pr.style || 'plate', 512, Math.max(64, Math.round(512 * h / w)));
        const front = new THREE.MeshStandardMaterial({ map: tex, metalness: pr.style === 'lcd' ? 0 : 0.6, roughness: pr.style === 'lcd' ? 0.15 : 0.4,
          emissive: pr.style === 'lcd' ? 0xffffff : 0x000000, emissiveMap: pr.style === 'lcd' ? tex : null, emissiveIntensity: pr.style === 'lcd' ? 0.55 : 0 });
        const side = mat;
        const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, Math.max(0.2, t)), [side, side, side, side, front, side]);
        m.quaternion.copy(FACE_Q[pr.face || 'z']);
        m.position.set(...pr.at);
        return m;
      }
      case 'gauge': {
        // pressure gauge: case, white dial, glass — dial faces +axis
        const g = new THREE.Group();
        const r = pr.r;
        const cas = new THREE.Mesh(new THREE.CylinderGeometry(r, r, r * 0.5, 40), material('steel', false));
        g.add(cas);
        const face = new THREE.Mesh(new THREE.CircleGeometry(r * 0.86, 40), new THREE.MeshStandardMaterial({ map: dialTex(), roughness: 0.5 }));
        face.rotation.x = -Math.PI / 2; face.position.y = r * 0.251; g.add(face);
        const glass = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.9, r * 0.9, r * 0.04, 40), new THREE.MeshPhysicalMaterial({ color: 0xffffff, transparent: true, opacity: 0.15, roughness: 0.02, metalness: 0, clearcoat: 1 }));
        glass.position.y = r * 0.27; g.add(glass);
        g.quaternion.copy(axisQuat(pr.axis)); if (pr.flip) g.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI));
        g.position.set(...pr.at);
        return g;
      }
      case 'arrow': {
        // cast flow arrow on a body side
        const L = pr.len; const W = pr.w; const sh = new THREE.Shape();
        sh.moveTo(-L / 2, -W * 0.22); sh.lineTo(L * 0.18, -W * 0.22); sh.lineTo(L * 0.18, -W / 2); sh.lineTo(L / 2, 0);
        sh.lineTo(L * 0.18, W / 2); sh.lineTo(L * 0.18, W * 0.22); sh.lineTo(-L / 2, W * 0.22); sh.closePath();
        geo = new THREE.ExtrudeGeometry(sh, { depth: pr.t, bevelEnabled: true, bevelThickness: pr.t * 0.3, bevelSize: pr.t * 0.3, bevelSegments: 2 });
        mesh.geometry = geo;
        mesh.quaternion.copy(FACE_Q[pr.face || 'z']);
        if (pr.dir < 0) mesh.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), Math.PI));
        mesh.position.set(...pr.at);
        return mesh;
      }
      case 'cyl': {
        geo = new THREE.CylinderGeometry(pr.r2 ?? pr.r, pr.r, Math.max(0.1, pr.h), pr.seg || 40);
        if (pr.seg && pr.seg <= 8) { geo = geo.toNonIndexed(); geo.computeVertexNormals(); }
        const q = axisQuat(pr.axis);
        if (pr.rotY) q.premultiply(new THREE.Quaternion().setFromAxisAngle(Y, pr.rotY));
        mesh.quaternion.copy(q);
        break;
      }
      case 'ring': {
        const hh = Math.max(0.1, pr.h) / 2;
        const pts = [[pr.ri, -hh], [pr.ro, -hh], [pr.ro, hh], [pr.ri, hh], [pr.ri, -hh]].map(([x, y]) => new THREE.Vector2(x, y));
        geo = new THREE.LatheGeometry(pts, 48);
        mesh.quaternion.copy(axisQuat(pr.axis));
        break;
      }
      case 'helix':
        geo = new THREE.TubeGeometry(new Helix(pr.R, pr.h, pr.turns), Math.round(pr.turns * 40), pr.r, 10, false);
        mesh.quaternion.copy(axisQuat(pr.axis));
        break;
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
        mesh.geometry = new THREE.CylinderGeometry(pr.r, pr.r, Math.max(0.1, len), 16);
        mesh.position.copy(a.clone().add(b).multiplyScalar(0.5));
        if (len > 0) mesh.quaternion.setFromUnitVectors(Y, b.clone().sub(a).normalize());
        return mesh;
      }
      default: return null;
    }
    mesh.geometry = geo;
    mesh.position.set(...pr.at);
    return mesh;
  }

  const isCut = (p) => opts.section && (CUT_LOOKS.has(p.look) || CUT_IDS.has(p.id));

  function clear() {
    for (const g of S.groups.values()) { g.traverse((o) => { if (o.geometry) o.geometry.dispose(); }); root.remove(g); }
    S.groups.clear();
    clearBalloons();
  }

  function show(model, { keepView = false } = {}) {
    clear();
    S.parts = model.parts; S.bbox = model.bbox;
    if (S.focus && !model.parts.some((p) => p.id === S.focus)) S.focus = null;
    for (const p of model.parts) {
      const g = new THREE.Group(); g.name = p.id; g.userData.part = p;
      const cut = isCut(p);
      const real = opts.style === 'real';
      for (const pr of p.prims) {
        const m = primMesh(pr, material(pr.look || p.look, cut)); if (!m) continue;
        m.traverse((o) => {
          if (!o.isMesh) return;
          o.userData.partId = p.id;
          o.castShadow = real && !REF.has(p.look); o.receiveShadow = real && !REF.has(p.look);
        });
        g.add(m);
        if (opts.edges && !REF.has(p.look) && m.isMesh && !Array.isArray(m.material) && pr.k !== 'helix' && !cut) {
          const e = new THREE.LineSegments(new THREE.EdgesGeometry(m.geometry, 35),
            new THREE.LineBasicMaterial({ color: 0x1b1f24, transparent: true, opacity: real ? 0.18 : 0.32 }));
          e.position.copy(m.position); e.quaternion.copy(m.quaternion); e.scale.copy(m.scale);
          e.userData.edge = true; g.add(e);
        }
      }
      root.add(g); S.groups.set(p.id, g);
      if (!REF.has(p.look)) makeBalloon(p);
    }
    applyExplode();
    applyFocus();
    highlight();
    placeStage();
    dirtyDims = true;
    if (!keepView) { goal.follow = true; frame(true); } else if (goal.follow) goal.refit = true;
  }

  // ───────── explode ─────────
  const smooth = (x) => x * x * (3 - 2 * x);
  /** stage 0 parts move first, stage 2 (internals) last */
  const stageK = (e, stage) => smooth(Math.max(0, Math.min(1, (e - stage * 0.18) / 0.64)));
  function applyExplode() {
    for (const g of S.groups.values()) {
      const p = g.userData.part; const k = stageK(S.e, p.stage ?? 1);
      g.position.set(p.ex[0] * k, p.ex[1] * k, p.ex[2] * k);
    }
  }
  function setExplode(k, instant) {
    S.eT = Math.max(0, Math.min(1, k));
    goal.follow = true; goal.refit = true;
    cb.onExplode(S.eT);
    if (instant) { S.e = S.eT; applyExplode(); frame(true); dirtyDims = true; }
  }
  const getExplode = () => S.eT;

  /** world bounds of the visible, non-reference parts as currently placed */
  function liveBox(ids) {
    const bb = new THREE.Box3();
    for (const [id, g] of S.groups) {
      if (!g.visible || REF.has(g.userData.part.look)) continue;
      if (ids && !ids.includes(id)) continue;
      bb.expandByObject(g);
    }
    return bb;
  }

  function projectedExtent(bb) {
    const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
    const up = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 1);
    let x0 = Infinity; let x1 = -Infinity; let y0 = Infinity; let y1 = -Infinity;
    const p = new THREE.Vector3();
    for (const xi of [bb.min.x, bb.max.x]) for (const yi of [bb.min.y, bb.max.y]) for (const zi of [bb.min.z, bb.max.z]) {
      p.set(xi, yi, zi);
      const a = p.dot(right); const b = p.dot(up);
      x0 = Math.min(x0, a); x1 = Math.max(x1, a); y0 = Math.min(y0, b); y1 = Math.max(y1, b);
    }
    return { w: x1 - x0, h: y1 - y0 };
  }

  /** frame the current (possibly exploded / isolated) model */
  function frame(instant) {
    const bb = liveBox(S.focus ? [S.focus] : null);
    if (bb.isEmpty()) return;
    updateCamera();
    const w = host.clientWidth || 600; const h = host.clientHeight || 400;
    const pe = projectedExtent(bb);
    const aw = Math.max(200, w - opts.insetRight);           // width left free by overlays (info card)
    const need = Math.max(pe.h, pe.w * h / aw) * 1.2 + 40;
    goal.dist = need; goal.fitDist = need;
    bb.getCenter(goal.target);
    if (opts.insetRight) {
      const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
      goal.target.addScaledVector(right, opts.insetRight / 2 * need / h);
    }
    if (instant) { orbit.dist = goal.dist; orbit.target.copy(goal.target); updateCamera(); }
  }

  function setView(name) {
    const iso = Math.acos(1 / Math.sqrt(3));
    const v = { iso: [Math.PI / 4, iso], iso2: [Math.PI * 0.75, iso], front: [0, Math.PI / 2],
      side: [Math.PI / 2, Math.PI / 2], top: [0, 0.0001], back: [Math.PI, Math.PI / 2] }[name];
    if (!v) return;
    [orbit.theta, orbit.phi] = v;
    goal.follow = true; frame(true); dirtyDims = true;
  }
  function fit() { goal.follow = true; frame(true); }

  // ───────── focus / isolate ─────────
  function focus(id) {
    S.focus = id && S.focus !== id ? id : null;
    applyFocus(); goal.follow = true; goal.refit = true;
    cb.onFocus(S.focus);
  }
  function applyFocus() {
    for (const [id, g] of S.groups) {
      const dim = !!S.focus && id !== S.focus;
      g.traverse((o) => {
        if (o.userData.edge) { o.visible = !dim; return; }
        if (!o.isMesh) return;
        if (dim && !o.userData.dimmed) { o.userData.base = o.material; o.material = material('ghost', false); o.userData.dimmed = true; }
        if (!dim && o.userData.dimmed) { o.material = o.userData.base; o.userData.dimmed = false; }
      });
    }
  }

  function setVisible(id, vis) { const g = S.groups.get(id); if (g) { g.visible = vis; dirtyDims = true; } }
  function setOption(k, v) {
    opts[k] = v;
    if (k === 'style') { applyStyle(); updateCamera(); setBackground(); }
    if (k === 'edges' || k === 'section' || k === 'style') show({ parts: S.parts, bbox: S.bbox }, { keepView: true });
    if (k === 'dims') dirtyDims = true;
    if (k === 'insetRight' && goal.follow) goal.refit = true;
  }

  // ───────── balloons & callouts ─────────
  // A numbered dot sits on each part. When names are shown they go into two callout columns
  // either side of the model (like an exploded parts drawing), joined by leader lines and
  // spaced so they never overlap.
  let svg = null;
  function makeBalloon(p) {
    if (!svg) {
      svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('class', 'v-leaders'); overlay.appendChild(svg);
    }
    const dot = document.createElement('button');
    dot.type = 'button'; dot.className = 'balloon'; dot.textContent = p.no ?? '';
    dot.setAttribute('aria-label', `${p.no ?? ''} ${p.dwgName || p.name}`);
    const label = document.createElement('button');
    label.type = 'button'; label.className = 'callout';
    label.innerHTML = '<b></b> <span></span>';
    label.querySelector('b').textContent = p.no ?? '';
    label.querySelector('span').textContent = p.dwgName || p.name;
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    svg.appendChild(line);
    for (const el of [dot, label]) {
      el.addEventListener('click', (ev) => { ev.stopPropagation(); select(p.id); cb.onPick(p.id); });
      el.addEventListener('dblclick', (ev) => { ev.stopPropagation(); focus(p.id); });
      el.addEventListener('pointerenter', () => { S.hovered = p.id; highlight(); });
      el.addEventListener('pointerleave', () => { S.hovered = null; highlight(); });
      el.addEventListener('wheel', (ev) => { ev.preventDefault(); onWheel(ev); }, { passive: false });
      overlay.appendChild(el);
    }
    balloons.set(p.id, { dot, label, line, w: 0 });
  }
  function clearBalloons() {
    for (const b of balloons.values()) { b.dot.remove(); b.label.remove(); b.line.remove(); }
    balloons.clear();
  }
  const _v = new THREE.Vector3(); const _b = new THREE.Box3();
  function placeBalloons() {
    const w = host.clientWidth; const h = host.clientHeight;
    svg.setAttribute('width', w); svg.setAttribute('height', h);
    const named = opts.labels === 'on' || (opts.labels === 'auto' && S.e > 0.45);
    const dotsOn = opts.labels !== 'off' && (opts.labels === 'on' || S.e > 0.12);
    const items = [];
    let xmin = Infinity; let xmax = -Infinity;
    for (const [id, b] of balloons) {
      const g = S.groups.get(id);
      const vis = g && g.visible && (!S.focus || S.focus === id);
      const showDot = vis && (dotsOn || id === S.selected || id === S.hovered);
      b.dot.style.display = showDot ? '' : 'none';
      b.dot.classList.toggle('sel', id === S.selected);
      if (!showDot) { b.label.style.display = 'none'; b.line.style.display = 'none'; continue; }
      _b.setFromObject(g); _b.getCenter(_v); _v.project(camera);
      const x = (_v.x + 1) / 2 * w; const y = (1 - _v.y) / 2 * h;
      b.dot.style.transform = `translate(${x}px, ${y}px)`;
      // model extent on screen (part boxes) for the callout columns
      for (const cx of [_b.min.x, _b.max.x]) for (const cy of [_b.min.y, _b.max.y]) for (const cz of [_b.min.z, _b.max.z]) {
        const q = new THREE.Vector3(cx, cy, cz).project(camera); const sx = (q.x + 1) / 2 * w;
        xmin = Math.min(xmin, sx); xmax = Math.max(xmax, sx);
      }
      items.push({ id, b, x, y, named: named || id === S.selected || id === S.hovered });
    }
    const mid = (xmin + xmax) / 2;
    const cols = { L: [], R: [] };
    let alt = 0;
    for (const it of items.filter((i) => i.named).sort((a, c) => a.y - c.y)) {
      const side = it.x < mid - 6 ? 'L' : it.x > mid + 6 ? 'R' : (alt++ % 2 ? 'L' : 'R');
      cols[side].push(it);
    }
    const LH = 21; const pad = 8;
    for (const side of ['L', 'R']) {
      const list = cols[side];
      // de-overlap: forward pass pushes down, backward pass pulls up from the bottom edge
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
        if (side === 'L') lx = Math.max(bl.w + pad, lx); else lx = Math.min(w - bl.w - pad, lx);
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

  // ───────── assembled envelope dimensions ─────────
  function textSprite(text, size) {
    const c = document.createElement('canvas'); const ctx = c.getContext('2d');
    const fs = 44; ctx.font = `600 ${fs}px system-ui, sans-serif`;
    c.width = ctx.measureText(text).width + 24; c.height = fs + 20;
    ctx.font = `600 ${fs}px system-ui, sans-serif`;
    ctx.fillStyle = 'rgba(20,24,30,0.82)'; ctx.fillRect(0, 0, c.width, c.height);
    ctx.fillStyle = '#ffffff'; ctx.textBaseline = 'middle'; ctx.fillText(text, 12, c.height / 2 + 2);
    const tex = new THREE.CanvasTexture(c); tex.minFilter = THREE.LinearFilter;
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
    sp.scale.set(size * c.width / c.height, size, 1); sp.renderOrder = 10;
    return sp;
  }
  function drawDims() {
    dirtyDims = false;
    if (dimGroup) { dimGroup.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material?.map) o.material.map.dispose(); }); scene.remove(dimGroup); dimGroup = null; }
    if (grid) { scene.remove(grid); grid = null; }
    if (!S.bbox || !isFinite(S.bbox.size[0])) return;
    const b0 = S.bbox;
    const bb = new THREE.Box3(new THREE.Vector3(...b0.min), new THREE.Vector3(...b0.max));
    const live = liveBox();
    const size = Math.max(...b0.size);
    grid = new THREE.GridHelper(size * 4, 40, 0x8899aa, 0x8899aa);
    grid.visible = opts.style !== 'real';
    grid.material.transparent = true; grid.material.opacity = 0.16;
    grid.position.set((bb.min.x + bb.max.x) / 2, Math.min(bb.min.y, live.isEmpty() ? bb.min.y : live.min.y) - 0.5, (bb.min.z + bb.max.z) / 2);
    scene.add(grid);
    if (!opts.dims || S.e > 0.02 || S.focus) return;
    dimGroup = new THREE.Group();
    const lm = new THREE.LineBasicMaterial({ color: 0xe0a526 });
    const helper = new THREE.Box3Helper(bb, 0xe0a526); helper.material.transparent = true; helper.material.opacity = 0.45;
    dimGroup.add(helper);
    const s = bb.getSize(new THREE.Vector3()); const ts = size * 0.045; const o = ts * 0.9;
    const mk = (a, b, label, off) => {
      dimGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([a, b]), lm));
      const sp = textSprite(label, ts); sp.position.copy(a.clone().add(b).multiplyScalar(0.5)).add(off); dimGroup.add(sp);
    };
    mk(new THREE.Vector3(bb.min.x, bb.min.y, bb.max.z + o), new THREE.Vector3(bb.max.x, bb.min.y, bb.max.z + o), `L ${Math.round(s.x)}`, new THREE.Vector3(0, -o, o));
    mk(new THREE.Vector3(bb.max.x + o, bb.min.y, bb.min.z), new THREE.Vector3(bb.max.x + o, bb.min.y, bb.max.z), `W ${Math.round(s.z)}`, new THREE.Vector3(o, -o, 0));
    mk(new THREE.Vector3(bb.max.x + o, bb.min.y, bb.max.z), new THREE.Vector3(bb.max.x + o, bb.max.y, bb.max.z), `H ${Math.round(s.y)}`, new THREE.Vector3(o * 2, 0, 0));
    scene.add(dimGroup);
  }

  // ───────── input ─────────
  function ndc(e) {
    const r = renderer.domElement.getBoundingClientRect();
    return new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  }
  /** world point under the cursor on the plane through the orbit target */
  function worldAt(e) {
    const rc = new THREE.Raycaster(); rc.setFromCamera(ndc(e), camera);
    const dir = new THREE.Vector3(); camera.getWorldDirection(dir);
    const plane = new THREE.Plane().setFromNormalAndCoplanarPoint(dir, orbit.target);
    return rc.ray.intersectPlane(plane, new THREE.Vector3()) || orbit.target.clone();
  }

  function zoomCamera(e, f) {
    const before = goal.dist;
    const nd = Math.max(15, Math.min(1e6, before * f));
    const p = worldAt(e);
    goal.target.add(p.sub(goal.target).multiplyScalar(1 - nd / before));
    goal.dist = nd;
    goal.follow = false;
  }

  let detentUntil = 0;
  function onWheel(e) {
    if (performance.now() < detentUntil) return;
    const steps = Math.max(-3, Math.min(3, e.deltaY / 100));
    if (!steps) return;
    const st = Math.abs(steps); const f = Math.exp(steps * 0.18);
    const auto = opts.autoExplode && !S.focus;
    if (steps < 0) {                                     // wheel in
      if (auto && goal.follow && S.eT < 1) {
        S.eT = Math.min(1, S.eT + 0.14 * st); goal.refit = true; cb.onExplode(S.eT);
        if (S.eT >= 1) detentUntil = performance.now() + 450;   // pause so a continuous scroll stops at the full exploded view
      } else {
        const wasOut = goal.dist > goal.fitDist * 1.001;
        zoomCamera(e, f);
        if (auto && wasOut && goal.dist <= goal.fitDist) { goal.follow = true; goal.refit = true; }
      }
    } else {                                             // wheel out
      if (!goal.follow) {
        zoomCamera(e, f);
        if (auto && S.eT > 0 && goal.dist >= goal.fitDist) { goal.follow = true; goal.refit = true; }
      } else if (auto && S.eT > 0) {
        S.eT = Math.max(0, S.eT - 0.14 * st); goal.refit = true; cb.onExplode(S.eT);
        if (S.eT <= 0) detentUntil = performance.now() + 450;
      } else {
        zoomCamera(e, f);
      }
    }
  }

  function bindInput(el) {
    let drag = null; let lastClick = { t: 0, id: null };
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
        goal.follow = false;
      } else {
        orbit.theta -= dx * 0.008;
        orbit.phi = Math.max(0.0001, Math.min(Math.PI - 0.0001, orbit.phi - dy * 0.008));
      }
      goal.target.copy(orbit.target); goal.dist = orbit.dist;
      updateCamera(); dirtyDims = true;
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

  const ray = new THREE.Raycaster();
  function pick(e) {
    ray.setFromCamera(ndc(e), camera);
    const meshes = [];
    for (const g of S.groups.values()) {
      if (!g.visible || REF.has(g.userData.part.look)) continue;
      if (S.focus && g.name !== S.focus) continue;
      g.traverse((o) => { if (o.isMesh) meshes.push(o); });
    }
    const hits = ray.intersectObjects(meshes, false);
    const hit = hits.find((h) => !h.object.material.clippingPlanes?.length || clipPlane.distanceToPoint(h.point) >= 0);
    return hit ? hit.object.userData.partId : null;
  }
  function hoverAt(e) {
    const id = pick(e);
    if (id !== S.hovered) { S.hovered = id; highlight(); }
    cb.onHover(id, e);
  }
  function select(id) { S.selected = id; highlight(); }
  function highlight() {
    for (const [id, g] of S.groups) {
      const on = id === S.hovered || id === S.selected;
      g.traverse((o) => {
        if (!o.isMesh || o.userData.dimmed) return;
        if (on && !o.userData.hl) {
          o.userData.base0 = o.material;
          const glow = (m) => { const c = m.clone(); c.emissive = new THREE.Color(id === S.selected ? 0xe0a526 : 0x335577); c.emissiveIntensity = 0.45; return c; };
          o.material = Array.isArray(o.material) ? o.material.map(glow) : glow(o.material); o.userData.hl = true;
        }
        if (!on && o.userData.hl) { [].concat(o.material).forEach((m) => m.dispose()); o.material = o.userData.base0; o.userData.hl = false; }
      });
    }
  }

  // ───────── frame loop ─────────
  function loop() {
    requestAnimationFrame(loop);
    let moved = false;
    if (Math.abs(S.e - S.eT) > 1e-4) {
      S.e += (S.eT - S.e) * 0.16; if (Math.abs(S.e - S.eT) < 2e-3) S.e = S.eT;
      applyExplode(); moved = true; dirtyDims = true; placeStage();
    }
    if (goal.follow && (moved || goal.refit)) { frame(false); goal.refit = false; }
    const dd = goal.dist - orbit.dist; const dt = goal.target.clone().sub(orbit.target);
    if (Math.abs(dd) > 0.5 || dt.lengthSq() > 0.25) {
      orbit.dist += dd * 0.22; orbit.target.addScaledVector(dt, 0.22); updateCamera();
    }
    if (dirtyDims) drawDims();
    renderer.render(scene, camera);
    if (balloons.size && svg) placeBalloons();
  }

  // ───────── export ─────────
  function exportMeshes(includeRef) {
    const out = [];
    root.updateMatrixWorld(true);
    for (const [id, g] of S.groups) {
      if (!g.visible) continue;
      if (!includeRef && REF.has(g.userData.part.look)) continue;
      g.traverse((o) => { if (o.isMesh) out.push({ id, mesh: o }); });
    }
    return out;
  }
  function triangles(mesh, fn) {
    const geo = mesh.geometry; const pos = geo.attributes.position; const idx = geo.index; const m = mesh.matrixWorld;
    const v = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()];
    const n = idx ? idx.count : pos.count;
    for (let i = 0; i < n; i += 3) {
      for (let k = 0; k < 3; k++) v[k].fromBufferAttribute(pos, idx ? idx.getX(i + k) : i + k).applyMatrix4(m);
      fn(v[0], v[1], v[2]);
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
    const L = ['# IC-3D-Builder OBJ, units mm, Y-up', `o ${name || 'item'}`];
    let base = 1; let cur = null;
    for (const { id, mesh } of exportMeshes(false)) {
      if (id !== cur) { const p = S.groups.get(id).userData.part; L.push(`g ${p.no ?? ''}_${id}`); cur = id; }
      const vs = []; triangles(mesh, (a, b, c) => vs.push(a.clone(), b.clone(), c.clone()));
      for (const v of vs) L.push(`v ${v.x.toFixed(2)} ${v.y.toFixed(2)} ${v.z.toFixed(2)}`);
      for (let i = 0; i < vs.length; i += 3) L.push(`f ${base + i} ${base + i + 1} ${base + i + 2}`);
      base += vs.length;
    }
    return new Blob([L.join('\n')], { type: 'text/plain' });
  }
  function toPNG() { renderer.render(scene, camera); return renderer.domElement.toDataURL('image/png'); }
  const lookColor = (k) => '#' + (LOOK[k] || LOOK.body).color.toString(16).padStart(6, '0');

  return { init, show, fit, setView, setExplode, getExplode, setVisible, setOption, setBackground, select, focus,
    toSTL, toOBJ, toPNG, lookColor, state: S, opts };
})();
