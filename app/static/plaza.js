/* 가상 광장 — 부서원이 캐릭터로 돌아다니며 말풍선으로 대화한다.
 *
 * 그림은 전부 이 파일이 그린다 (그림 파일 0 · 외부 요청 0).  지도와 소품은 처음에 한 번 그려 두고
 * 매 틀마다 붙인다.  사람이 적은 글(이름 · 말)은 canvas 글자와 textContent 로만 그린다.
 * 서버(app/plaza.py)는 칸 좌표 · 말 · 이름만 들고 있다.
 */
(() => {
"use strict";
const T = 32, W = 56, H = 32;               // 칸 크기 · 지도 칸 수 (서버 MAP_W/MAP_H 와 같다)
const STEP_MS = 190;                        // 한 칸 걷는 시간
const PX = 2;                               // 캐릭터 한 점 = 2px
const ATK_MS = 280, HIT_MS = 520;          // 휘두르기 · 맞은 표시 시간
const $ = s => document.querySelector(s);
const Q = new URLSearchParams(location.search);
const EMBED = Q.get("embed") === "1";

// ── 씨앗 있는 난수 (지도는 누구에게나 같다) ─────────────────────────────
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0;
  let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
  return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function hash(s) { let h = 2166136261; for (const ch of String(s)) { h ^= ch.codePointAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }

// ── 지도 ───────────────────────────────────────────────────────────────
const GRASS = 0, DIRT = 1, STONE = 2, WATER = 3, FLOWER = 4, SAND = 5;
const ground = new Uint8Array(W * H), solid = new Uint8Array(W * H);
const at = (x, y) => y * W + x;
const inside = (x, y) => x >= 0 && y >= 0 && x < W && y < H;
function fill(t, x0, y0, x1, y1) { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (inside(x, y)) ground[at(x, y)] = t; }
function block(x0, y0, x1, y1) { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (inside(x, y)) solid[at(x, y)] = 1; }
const props = [];                           // {x, y(바닥 px), img, dx, dy}

const R = rng(20261015);
fill(DIRT, 0, 15, W - 1, 16);               // 큰길
fill(DIRT, 27, 0, 28, H - 1);
fill(STONE, 21, 11, 34, 20);                // 광장
for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {   // 연못
  const dx = (x + .5 - 10.5) / 7.2, dy = (y + .5 - 25.5) / 4.6, d = dx * dx + dy * dy;
  if (d < 1) ground[at(x, y)] = WATER; else if (d < 1.42 && ground[at(x, y)] === GRASS) ground[at(x, y)] = SAND;
}
for (let i = 0; i < W * H; i++) if (ground[i] === GRASS && R() < .07) ground[i] = FLOWER;
for (let i = 0; i < W * H; i++) if (ground[i] === WATER) solid[i] = 1;

// ── 그림 도구 ───────────────────────────────────────────────────────────
function canvas(w, h) { const c = document.createElement("canvas"); c.width = w; c.height = h; return c; }
function shade(hex, k) {                    // k<0 어둡게 · k>0 밝게
  const n = parseInt(hex.slice(1), 16), f = v => Math.max(0, Math.min(255, Math.round(k < 0 ? v * (1 + k) : v + (255 - v) * k)));
  return "#" + [n >> 16 & 255, n >> 8 & 255, n & 255].map(v => f(v).toString(16).padStart(2, "0")).join("");
}
function ell(g, x, y, rx, ry, c) { g.fillStyle = c; g.beginPath(); g.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2); g.fill(); }

// ── 땅 (한 번 그린다) ────────────────────────────────────────────────────
const groundImg = canvas(W * T, H * T);
(function drawGround() {
  const g = groundImg.getContext("2d"), r = rng(7);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const t = ground[at(x, y)], X = x * T, Y = y * T;
    if (t === GRASS || t === FLOWER) {
      g.fillStyle = (x + y) % 2 ? "#66ab47" : "#63a744"; g.fillRect(X, Y, T, T);
      for (let i = 0; i < 9; i++) { g.fillStyle = r() < .5 ? "#4f9135" : "#7cc258";
        const px = X + Math.floor(r() * 15) * 2, py = Y + Math.floor(r() * 15) * 2; g.fillRect(px, py, 2, 2); g.fillRect(px + 2, py - 2, 2, 2); }
      if (t === FLOWER) for (let i = 0; i < 3; i++) { const c = ["#f4e04d", "#ffffff", "#ef6f8f", "#f59a3c"][Math.floor(r() * 4)];
        const px = X + 4 + Math.floor(r() * 12) * 2, py = Y + 4 + Math.floor(r() * 12) * 2;
        g.fillStyle = c; g.fillRect(px - 2, py, 2, 2); g.fillRect(px + 2, py, 2, 2); g.fillRect(px, py - 2, 2, 2); g.fillRect(px, py + 2, 2, 2);
        g.fillStyle = "#f7c531"; g.fillRect(px, py, 2, 2); }
    } else if (t === DIRT) {
      g.fillStyle = "#cfa96c"; g.fillRect(X, Y, T, T);
      for (let i = 0; i < 7; i++) { g.fillStyle = r() < .6 ? "#b8925a" : "#e0bf85";
        g.fillRect(X + Math.floor(r() * 15) * 2, Y + Math.floor(r() * 15) * 2, 2, 2); }
      if (r() < .25) { g.fillStyle = "#9f8a6d"; g.fillRect(X + 8 + Math.floor(r() * 8) * 2, Y + 8 + Math.floor(r() * 8) * 2, 4, 2); }
    } else if (t === STONE) {
      const s = r(); g.fillStyle = s < .3 ? "#b4ae9e" : s < .7 ? "#bdb7a7" : "#c6c0b0"; g.fillRect(X, Y, T, T);
      g.fillStyle = "#958f7f"; g.fillRect(X, Y, T, 2); g.fillRect(X, Y, 2, T);
      g.fillRect(X + (y % 2 ? 16 : 0), Y + 16, 2, 16); g.fillRect(X, Y + 16, T, 2);
      g.fillStyle = "#d6d0c0"; g.fillRect(X + 2, Y + 2, 12, 2);
    } else if (t === SAND) {
      g.fillStyle = "#d8c690"; g.fillRect(X, Y, T, T);
      for (let i = 0; i < 6; i++) { g.fillStyle = r() < .5 ? "#c4b179" : "#e6d6a6"; g.fillRect(X + Math.floor(r() * 15) * 2, Y + Math.floor(r() * 15) * 2, 2, 2); }
    } else if (t === WATER) {
      g.fillStyle = "#3f7fc2"; g.fillRect(X, Y, T, T);
      for (let i = 0; i < 4; i++) { g.fillStyle = "#3572b3"; g.fillRect(X + Math.floor(r() * 12) * 2, Y + Math.floor(r() * 15) * 2, 8, 2); }
    }
  }
  // 물가 · 길가를 부드럽게 (이웃이 다르면 그 변에 띠를 두른다)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const t = ground[at(x, y)], X = x * T, Y = y * T;
    const nb = (dx, dy) => inside(x + dx, y + dy) ? ground[at(x + dx, y + dy)] : t;
    if (t === WATER) {
      g.fillStyle = "#9fd0ef";
      if (nb(0, -1) !== WATER) g.fillRect(X, Y, T, 4);
      if (nb(-1, 0) !== WATER) g.fillRect(X, Y, 4, T);
      if (nb(1, 0) !== WATER) g.fillRect(X + T - 4, Y, 4, T);
      if (nb(0, 1) !== WATER) { g.fillStyle = "#2f6aa6"; g.fillRect(X, Y + T - 4, T, 4); }
    }
    if (t === DIRT) for (const [dx, dy] of [[0, -1], [0, 1], [-1, 0], [1, 0]]) {
      const n = nb(dx, dy); if (n !== GRASS && n !== FLOWER) continue;
      g.fillStyle = "#63a744";
      for (let i = 0; i < 16; i += 2) { if (r() < .55) continue;
        if (dy) g.fillRect(X + i * 2, dy < 0 ? Y : Y + T - 2, 4, 2); else g.fillRect(dx < 0 ? X : X + T - 2, Y + i * 2, 2, 4); }
    }
  }
  // 연꽃
  const lr = rng(11);
  for (let i = 0; i < 9; i++) { const x = 4 + Math.floor(lr() * 13), y = 22 + Math.floor(lr() * 7);
    if (ground[at(x, y)] !== WATER || ground[at(x - 1, y)] !== WATER || ground[at(x + 1, y)] !== WATER) continue;
    const X = x * T + 8, Y = y * T + 10; ell(g, X + 8, Y + 6, 10, 6, "#3e8d48"); ell(g, X + 6, Y + 5, 3, 2, "#5aa95b");
    if (lr() < .5) { ell(g, X + 10, Y + 2, 4, 4, "#f4a6c1"); ell(g, X + 10, Y + 1, 2, 2, "#fbe0ea"); } }
})();

// ── 소품 그림 ──────────────────────────────────────────────────────────
function treeImg(seed, big) {
  const r = rng(seed), w = big ? 112 : 64, h = big ? 132 : 84, c = canvas(w, h), g = c.getContext("2d"), cx = w / 2;
  ell(g, cx, h - 6, big ? 34 : 20, big ? 9 : 6, "rgba(0,0,0,.22)");
  g.fillStyle = "#6d4426"; g.fillRect(cx - (big ? 8 : 5), h - (big ? 48 : 32), big ? 16 : 10, big ? 44 : 28);
  g.fillStyle = "#583419"; g.fillRect(cx - (big ? 8 : 5), h - (big ? 48 : 32), big ? 4 : 3, big ? 44 : 28);
  if (big) {   // 당산나무 금줄
    g.fillStyle = "#e8d7a0"; g.fillRect(cx - 10, h - 30, 20, 3);
    for (let i = 0; i < 4; i++) { g.fillStyle = "#ffffff"; g.fillRect(cx - 8 + i * 5, h - 27, 3, 6); }
  }
  const pine = !big && r() < .35, base = pine ? ["#2f6b3a", "#3c8046", "#4d9653"] : ["#3f8a3c", "#55a346", "#73bd57"];
  const blobs = big ? 16 : 9, cy = big ? 46 : 30, sr = big ? 44 : 26;
  for (let k = 0; k < 3; k++) for (let i = 0; i < blobs; i++) {
    const a = r() * Math.PI * 2, d = r() * sr * (1 - k * .28);
    const bx = cx + Math.cos(a) * d * .9, by = cy + Math.sin(a) * d * .62 - k * 4, rr = (big ? 18 : 11) - k * 2 + r() * 4;
    ell(g, bx, by, rr, rr * .85, base[k]);
  }
  for (let i = 0; i < (big ? 14 : 6); i++) { g.fillStyle = "rgba(255,255,255,.18)";
    g.fillRect(Math.round(cx - sr * .6 + r() * sr * 1.2), Math.round(cy - sr * .45 + r() * sr * .4), 4, 2); }
  return c;
}

function roof(g, x, y, w, h, col) {         // 기와 지붕 — 처마 끝이 올라간다
  g.fillStyle = col; g.beginPath();
  g.moveTo(x - 14, y + h - 16); g.quadraticCurveTo(x + 2, y + h + 2, x + 26, y + h);
  g.lineTo(x + w - 26, y + h); g.quadraticCurveTo(x + w - 2, y + h + 2, x + w + 14, y + h - 16);
  g.lineTo(x + w - 20, y + 12); g.lineTo(x + 20, y + 12); g.closePath(); g.fill();
  g.save(); g.clip();
  g.fillStyle = shade(col, -.25); for (let i = x - 14; i < x + w + 14; i += 6) g.fillRect(i, y + 12, 2, h);
  g.fillStyle = "rgba(255,255,255,.08)"; g.fillRect(x - 14, y + 12, w + 28, 10);
  g.restore();
  g.fillStyle = shade(col, -.45); g.fillRect(x + 14, y + 4, w - 28, 10);         // 용마루
  g.beginPath(); g.moveTo(x + 14, y + 14); g.quadraticCurveTo(x + 4, y + 10, x + 6, y - 2); g.lineTo(x + 16, y + 4); g.fill();
  g.beginPath(); g.moveTo(x + w - 14, y + 14); g.quadraticCurveTo(x + w - 4, y + 10, x + w - 6, y - 2); g.lineTo(x + w - 16, y + 4); g.fill();
  g.fillStyle = "#e2ddd0"; g.fillRect(x + 16, y + 8, w - 32, 2);
  for (let i = x + 26; i < x + w - 26; i += 8) { ell(g, i, y + h - 1, 3, 3, shade(col, .25)); ell(g, i, y + h - 1, 1.5, 1.5, shade(col, .55)); }
}

function houseImg(seed, wTiles, roofCol) {
  const r = rng(seed), w = wTiles * T, h = 4 * T + 56, c = canvas(w + 40, h), g = c.getContext("2d"), ox = 20;
  ell(g, ox + w / 2, h - 8, w / 2 + 6, 10, "rgba(0,0,0,.22)");
  g.fillStyle = "#a8a296"; g.fillRect(ox, h - 30, w, 22);                          // 기단
  for (let i = 0; i < w; i += 16) { g.fillStyle = (i / 16) % 2 ? "#9a9488" : "#b3ad9f"; g.fillRect(ox + i, h - 30 + ((i / 16) % 2) * 11, 16, 11); }
  g.fillStyle = "#7d776a"; g.fillRect(ox, h - 30, w, 2);
  const wallTop = h - 88;
  g.fillStyle = "#efe6d0"; g.fillRect(ox + 6, wallTop, w - 12, 58);
  const posts = Math.max(3, Math.round(w / 48));
  for (let i = 0; i <= posts; i++) { const px = ox + 6 + Math.round((w - 18) * i / posts);
    g.fillStyle = "#6e4527"; g.fillRect(px, wallTop - 4, 6, 62); g.fillStyle = "#5a361c"; g.fillRect(px, wallTop - 4, 2, 62); }
  g.fillStyle = "#6e4527"; g.fillRect(ox + 6, wallTop - 6, w - 12, 6); g.fillRect(ox + 6, wallTop + 30, w - 12, 4);
  for (let i = 0; i < posts; i++) {                                                  // 창살문
    const x0 = ox + 14 + Math.round((w - 18) * i / posts), ww = Math.round((w - 18) / posts) - 14;
    if (r() < .25) continue;
    g.fillStyle = "#f6efdc"; g.fillRect(x0, wallTop + 2, ww, 26);
    g.fillStyle = "#8b5a32"; g.strokeStyle = "#8b5a32";
    for (let k = 0; k <= ww; k += 6) g.fillRect(x0 + k, wallTop + 2, 1, 26);
    for (let k = 0; k <= 26; k += 6) g.fillRect(x0, wallTop + 2 + k, ww, 1);
    g.fillRect(x0, wallTop + 2, ww, 2); g.fillRect(x0, wallTop + 26, ww, 2);
  }
  roof(g, ox, 0, w, wallTop + 6, roofCol);
  return c;
}

function pavilionImg() {
  const w = 3 * T, h = 3 * T + 60, c = canvas(w + 40, h), g = c.getContext("2d"), ox = 20;
  ell(g, ox + w / 2, h - 8, w / 2 + 4, 9, "rgba(0,0,0,.22)");
  g.fillStyle = "#8a5a33"; g.fillRect(ox + 4, h - 34, w - 8, 14); g.fillStyle = "#a8743f"; g.fillRect(ox + 4, h - 34, w - 8, 4);
  for (const px of [ox + 8, ox + w - 16]) { g.fillStyle = "#b5352a"; g.fillRect(px, h - 96, 8, 66); g.fillStyle = "#8f261e"; g.fillRect(px, h - 96, 2, 66); }
  g.fillStyle = "#2f7a6b"; g.fillRect(ox + 4, h - 100, w - 8, 8);                  // 단청
  for (let i = ox + 6; i < ox + w - 6; i += 8) { g.fillStyle = i % 16 ? "#e0b24b" : "#c8423a"; g.fillRect(i, h - 98, 4, 4); }
  roof(g, ox, 2, w, h - 102, "#55606b");
  return c;
}

function wellImg() {
  const c = canvas(72, 80), g = c.getContext("2d");
  ell(g, 36, 70, 30, 8, "rgba(0,0,0,.22)");
  g.fillStyle = "#6e4527"; g.fillRect(8, 6, 6, 52); g.fillRect(58, 6, 6, 52); g.fillRect(4, 4, 64, 6);
  g.fillStyle = "#4b4b4b"; g.fillRect(34, 10, 2, 22); g.fillStyle = "#8a5a33"; g.fillRect(28, 30, 14, 10);
  ell(g, 36, 56, 28, 14, "#9a9488"); ell(g, 36, 54, 22, 9, "#2a4256"); ell(g, 33, 52, 6, 2, "rgba(255,255,255,.25)");
  for (let i = 0; i < 8; i++) { g.fillStyle = i % 2 ? "#aaa497" : "#86806f"; g.fillRect(10 + i * 7, 60 + Math.round(Math.sin(i) * 2), 7, 6); }
  return c;
}
function lanternImg() {
  const c = canvas(28, 72), g = c.getContext("2d");
  ell(g, 14, 66, 9, 3, "rgba(0,0,0,.22)");
  g.fillStyle = "#5a361c"; g.fillRect(12, 14, 4, 54); g.fillRect(4, 12, 20, 3);
  g.fillStyle = "#c8323a"; g.fillRect(6, 18, 16, 10); g.fillStyle = "#2e5ea8"; g.fillRect(6, 28, 16, 8);
  g.fillStyle = "#f2c94c"; g.fillRect(6, 16, 16, 2); g.fillRect(6, 36, 16, 2);
  return c;
}
function jangseungImg(top) {
  const c = canvas(28, 84), g = c.getContext("2d");
  ell(g, 14, 78, 10, 3, "rgba(0,0,0,.25)");
  g.fillStyle = "#9b6a3f"; g.fillRect(6, 10, 16, 68); g.fillStyle = "#7d522d"; g.fillRect(6, 10, 3, 68);
  g.fillStyle = "#1e1e1e"; g.fillRect(4, 4, 20, 8); g.fillRect(9, 0, 10, 6);           // 관모
  g.fillStyle = "#f2efe6"; g.fillRect(9, 16, 4, 3); g.fillRect(15, 16, 4, 3);
  g.fillStyle = "#111"; g.fillRect(10, 17, 2, 2); g.fillRect(16, 17, 2, 2);
  g.fillStyle = "#b8332d"; g.fillRect(12, 22, 4, 6); g.fillStyle = "#f2efe6"; g.fillRect(9, 30, 10, 3);
  g.fillStyle = "#111"; g.font = "bold 9px serif"; g.textAlign = "center";
  [...(top ? "天下大將軍" : "地下女將軍")].forEach((ch, i) => g.fillText(ch, 14, 44 + i * 8));
  return c;
}
function signImg(text) {
  const c = canvas(96, 64), g = c.getContext("2d");
  ell(g, 48, 58, 30, 5, "rgba(0,0,0,.22)");
  g.fillStyle = "#5a361c"; g.fillRect(14, 22, 6, 36); g.fillRect(76, 22, 6, 36);
  g.fillStyle = "#a8743f"; g.fillRect(4, 4, 88, 28); g.fillStyle = "#7d522d"; g.fillRect(4, 4, 88, 3); g.fillRect(4, 29, 88, 3);
  g.fillStyle = "#2a1a10"; g.font = "bold 13px 'Malgun Gothic','Apple SD Gothic Neo','WenQuanYi Zen Hei',sans-serif";
  g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(text, 48, 19);
  return c;
}
function wallImg(len) {
  const c = canvas(len * T, 44), g = c.getContext("2d"), r = rng(len * 97);
  g.fillStyle = "rgba(0,0,0,.2)"; g.fillRect(2, 38, len * T - 4, 5);
  for (let y = 10; y < 40; y += 8) for (let x = -(y % 16) / 2; x < len * T; x += 12) {
    g.fillStyle = ["#9e9789", "#8b8576", "#b0aa9b", "#7c7668"][Math.floor(r() * 4)];
    g.fillRect(Math.max(0, x), y, 11, 7);
  }
  g.fillStyle = "#4b5560"; g.fillRect(0, 2, len * T, 9); g.fillStyle = "#3a434d"; for (let x = 0; x < len * T; x += 6) g.fillRect(x, 4, 2, 7);
  g.fillStyle = "#2f363e"; g.fillRect(0, 0, len * T, 3);
  return c;
}
function stallImg() {
  const w = 3 * T, c = canvas(w + 8, 92), g = c.getContext("2d");
  ell(g, w / 2 + 4, 84, w / 2, 7, "rgba(0,0,0,.22)");
  g.fillStyle = "#6e4527"; g.fillRect(8, 18, 5, 66); g.fillRect(w - 5, 18, 5, 66);
  for (let i = 0; i < w; i += 12) { g.fillStyle = (i / 12) % 2 ? "#f2ead3" : "#c7423a"; g.fillRect(4 + i, 8, 12, 20); }
  g.fillStyle = "#8b5a32"; g.fillRect(4, 56, w, 14); g.fillStyle = "#a8743f"; g.fillRect(4, 56, w, 4);
  [["#d65a2f", 20], ["#e8b83a", 36], ["#7fb24b", 52], ["#9c5530", 70]].forEach(([col, x]) => { ell(g, x, 52, 7, 6, col); ell(g, x - 2, 49, 2, 2, "rgba(255,255,255,.4)"); });
  return c;
}

// ── 소품 놓기 ───────────────────────────────────────────────────────────
function place(img, tx, ty, opts = {}) {   // img 바닥 가운데를 (tx..tx+fw-1, ty 행 바닥)에 맞춘다
  const fw = opts.fw || 1;
  props.push({ img, x: tx * T + fw * T / 2 - img.width / 2, y: (ty + 1) * T + (opts.dy || 0) });
  if (opts.solid) block(...opts.solid);
}
const HOUSES = [[4, 4, 6, "#4b5560"], [13, 3, 6, "#56606a"], [36, 4, 6, "#4b5560"], [45, 5, 6, "#5d4b45"],
                [38, 23, 6, "#56606a"], [47, 23, 6, "#4b5560"], [4, 4, 0, 0]].slice(0, 6);
HOUSES.forEach(([x, y, w, col], i) => place(houseImg(100 + i, w, col), x, y + 3, { fw: w, solid: [x, y, x + w - 1, y + 3] }));
place(pavilionImg(), 18, 25, { fw: 3, solid: [18, 23, 20, 25] });
place(wellImg(), 23, 13, { fw: 2, solid: [23, 12, 24, 13], dy: -4 });
place(treeImg(77, true), 32, 13, { fw: 2, solid: [32, 13, 33, 13] });
for (const [x, y] of [[21, 11], [34, 11], [21, 20], [34, 20]]) place(lanternImg(), x, y, { solid: [x, y, x, y] });
place(jangseungImg(true), 2, 14, { solid: [2, 14, 2, 14] });
place(jangseungImg(false), 2, 17, { solid: [2, 17, 2, 17] });
place(signImg("계장 마을 광장"), 30, 21, { fw: 2, solid: [30, 21, 31, 21] });
place(wallImg(4), 3, 9, { fw: 4, solid: [3, 9, 6, 9] }); place(wallImg(3), 8, 9, { fw: 3, solid: [8, 9, 10, 9] });
place(wallImg(3), 35, 10, { fw: 3, solid: [35, 10, 37, 10] }); place(wallImg(3), 39, 10, { fw: 3, solid: [39, 10, 41, 10] });
place(stallImg(), 31, 24, { fw: 3, solid: [31, 23, 33, 24] });
place(stallImg(), 22, 24, { fw: 3, solid: [22, 23, 24, 24] });
(function trees() {                         // 숲 테두리 + 흩어진 나무
  const r = rng(99);
  const free = (x, y) => inside(x, y) && !solid[at(x, y)] && ground[at(x, y)] !== DIRT && ground[at(x, y)] !== STONE && ground[at(x, y)] !== WATER;
  const put = (x, y) => { if (!free(x, y)) return; place(treeImg(1000 + x * 64 + y, false), x, y, { solid: [x, y, x, y] }); };
  for (let x = 0; x < W; x += 2) { put(x + (r() < .5 ? 0 : 1), 0); put(x + (r() < .5 ? 0 : 1), 1); put(x, H - 1); }
  for (let y = 2; y < H - 1; y += 2) { put(0, y + (r() < .5 ? 0 : 1)); put(1, y); put(W - 1, y + (r() < .5 ? 0 : 1)); put(W - 2, y); }
  for (let i = 0; i < 70; i++) { const x = 3 + Math.floor(r() * (W - 6)), y = 3 + Math.floor(r() * (H - 6));
    let ok = true; for (let yy = y - 1; yy <= y + 1 && ok; yy++) for (let xx = x - 1; xx <= x + 1; xx++) if (!free(xx, yy)) { ok = false; break; }
    if (ok && !(x >= 20 && x <= 35 && y >= 10 && y <= 21)) put(x, y); }
})();

// ── 캐릭터 ─────────────────────────────────────────────────────────────
const CLOTH = ["#c23b2e", "#2e6db4", "#2f8c58", "#d9a520", "#7a4ea3", "#e0789a", "#34507a", "#9c5530", "#efe7d2", "#1f8a8a"];
const PANTS = ["#f1e9d4", "#55597a", "#e6d29f", "#6b705c", "#8a8f99"];
const HAIRC = ["#1d1612", "#2d1d14", "#3b2416"], SKIN = ["#f6d3b0", "#efc49c", "#e8b98d"];
function lookOf(n) { return { cloth: CLOTH[n % 10], pants: PANTS[(n >> 4) % 5], style: (n >> 8) % 5,
  hair: HAIRC[(n >> 11) % 3], skin: SKIN[(n >> 13) % 3], ribbon: ["#c0262d", "#7a1fa2", "#d9480f"][(n >> 15) % 3] }; }
const OL = "#2a1a12";
const spriteCache = new Map();
// dir: 0 아래 · 1 위 · 2 왼쪽 · 3 오른쪽 / frame: 0 섬 · 1 · 2 걸음
function charSprite(look, dir, frame) {
  const key = `${look}|${dir}|${frame}`; if (spriteCache.has(key)) return spriteCache.get(key);
  const L = lookOf(look), c = canvas(16 * PX + 4, 24 * PX + 4), g = c.getContext("2d");
  const flip = dir === 3, side = dir >= 2;
  const parts = [];                         // [x, y, w, h, 색, 둥근가, 테두리]
  const P = (x, y, w, h, col, rnd = false, ol = true) => parts.push([x, y, w, h, col, rnd, ol]);
  const step = frame === 1 ? 1 : frame === 2 ? -1 : 0;
  // 다리 · 신
  if (!side) {
    P(5, 19 - (step > 0 ? 1 : 0), 2, 3, L.pants); P(9, 19 - (step < 0 ? 1 : 0), 2, 3, L.pants);
    P(5, 22 - (step > 0 ? 1 : 0), 2, 1, "#3a2a20"); P(9, 22 - (step < 0 ? 1 : 0), 2, 1, "#3a2a20");
  } else {
    P(6 - step, 19, 2, 3, L.pants); P(8 + step, 19, 2, 3, L.pants);
    P(5 - step, 22, 3, 1, "#3a2a20"); P(8 + step, 22, 3, 1, "#3a2a20");
  }
  // 몸 (저고리) · 팔
  if (!side) {
    P(4, 13, 8, 6, L.cloth, true);
    P(2, 14 + (step > 0 ? -1 : step < 0 ? 1 : 0), 2, 4, L.cloth); P(12, 14 + (step < 0 ? -1 : step > 0 ? 1 : 0), 2, 4, L.cloth);
    P(2, 18 + (step > 0 ? -1 : step < 0 ? 1 : 0), 2, 1, L.skin, false, false); P(12, 18 + (step < 0 ? -1 : step > 0 ? 1 : 0), 2, 1, L.skin, false, false);
  } else {
    P(5, 13, 6, 6, L.cloth, true);
    P(7 + step, 14, 2, 4, shadeOk(L.cloth)); P(7 + step, 18, 2, 1, L.skin, false, false);
  }
  // 머리
  if (L.style === 3 && dir !== 0) P(dir === 1 ? 6 : 11, 8, 4, 4, L.hair, true);                  // 쪽머리
  if (L.style === 2 && dir !== 0) P(dir === 1 ? 7 : 11, 11, 2, 7, L.hair);                         // 댕기머리
  P(3, 3, 10, 10, dir === 1 ? L.hair : L.skin, true);
  if (L.style === 0) P(side ? 7 : 6, 0, side ? 3 : 4, 3, L.hair, true);                           // 상투
  if (L.style === 1) { P(5, 0, 6, 5, "#161616", true); P(0, 4, 16, 2, "#161616"); }                // 갓
  // 그리기 — 테두리 먼저, 그다음 색
  const rect = (x, y, w, h, col) => { g.fillStyle = col; g.fillRect(2 + (flip ? (16 - x - w) : x) * PX, 2 + y * PX, w * PX, h * PX); };
  for (const [x, y, w, h, , rnd, ol] of parts) if (ol) {
    if (rnd) { rect(x, y - 1, w, h + 2, OL); rect(x - 1, y, w + 2, h, OL); } else rect(x - 1, y - 1, w + 2, h + 2, OL);
  }
  for (const [x, y, w, h, col, rnd] of parts) {
    if (rnd && w > 2 && h > 2) { rect(x + 1, y, w - 2, h, col); rect(x, y + 1, w, h - 2, col); } else rect(x, y, w, h, col);
  }
  // 얼굴 · 머리카락 · 옷 무늬 (테두리 없음)
  const px = (x, y, w, h, col) => rect(x, y, w, h, col);
  if (dir === 0) {
    px(3, 2, 10, 3, L.hair); px(4, 2, 8, 1, L.hair); px(3, 5, 1, 4, L.hair); px(12, 5, 1, 4, L.hair); px(4, 5, 3, 1, L.hair); px(9, 5, 3, 1, L.hair);
    px(5, 8, 1, 2, "#1a1a1a"); px(10, 8, 1, 2, "#1a1a1a"); px(4, 10, 1, 1, "#f19a8f"); px(11, 10, 1, 1, "#f19a8f"); px(7, 11, 2, 1, "#a8483f");
    px(7, 13, 2, 1, L.skin); px(6, 13, 1, 1, "#fbf6ea"); px(7, 14, 1, 1, "#fbf6ea"); px(9, 13, 1, 1, "#fbf6ea"); px(8, 14, 1, 1, "#fbf6ea");
    px(8, 15, 1, 3, L.ribbon); px(9, 15, 1, 2, L.ribbon); px(4, 18, 8, 1, shadeOk(L.cloth));
  } else if (dir === 1) {
    px(5, 12, 6, 1, L.skin); px(4, 4, 2, 1, shade(L.hair, .2)); px(4, 18, 8, 1, shadeOk(L.cloth));
    if (L.style === 2) px(7, 17, 2, 2, L.ribbon);
    if (L.style === 3) px(3, 9, 10, 1, "#d4af37");
  } else {
    px(3, 2, 10, 3, L.hair); px(8, 4, 5, 6, L.hair); px(11, 9, 2, 2, L.hair); px(3, 5, 2, 1, L.hair);
    px(4, 8, 1, 2, "#1a1a1a"); px(4, 10, 1, 1, "#f19a8f"); px(3, 9, 1, 1, L.skin);
    px(5, 13, 1, 1, "#fbf6ea"); px(6, 14, 1, 1, "#fbf6ea"); px(5, 18, 6, 1, shadeOk(L.cloth));
    if (L.style === 2) px(11, 17, 2, 2, L.ribbon);
    if (L.style === 3) px(10, 9, 5, 1, "#d4af37");
  }
  if (L.style === 1) { px(5, 4, 6, 1, "#6b4a2a"); if (dir !== 1) { px(3, 10, 1, 3, "#7a4a24"); if (!side) px(12, 10, 1, 3, "#7a4a24"); } }
  spriteCache.set(key, c); return c;
}
function shadeOk(c) { return shade(c, -.22); }
const tintCache = new WeakMap();
function tinted(img) {                      // 맞은 순간 — 붉게 번쩍
  let c = tintCache.get(img); if (c) return c;
  c = canvas(img.width, img.height); const g = c.getContext("2d");
  g.drawImage(img, 0, 0); g.globalCompositeOperation = "source-atop"; g.fillStyle = "rgba(255,70,50,.65)"; g.fillRect(0, 0, c.width, c.height);
  tintCache.set(img, c); return c;
}
// 목검을 휘두른다 — 바라보는 쪽으로 반원을 긋고 흰 칼바람을 남긴다
const BASE_ANG = { 0: Math.PI / 2, 1: -Math.PI / 2, 2: Math.PI, 3: 0 };
function drawSwing(g, sx, sy, dir, k) {
  const px = sx + 16 + (dir === 2 ? -4 : dir === 3 ? 4 : 0), py = sy + 6 + (dir === 0 ? 2 : dir === 1 ? -4 : 0);
  const side = dir === 2 ? -1 : 1, span = 1.35, base = BASE_ANG[dir];
  const ease = 1 - Math.pow(1 - k, 3), ang = base - side * span + side * 2 * span * ease;
  g.save();
  g.globalAlpha = .75 * (1 - k * .6); g.strokeStyle = "#ffffff"; g.lineWidth = 5; g.lineCap = "round";
  g.beginPath(); g.arc(px, py, 22, Math.min(base - side * span, ang), Math.max(base - side * span, ang)); g.stroke();
  g.globalAlpha = .35 * (1 - k); g.lineWidth = 9; g.strokeStyle = "#cfe9ff";
  g.beginPath(); g.arc(px, py, 19, Math.min(base - side * span, ang), Math.max(base - side * span, ang)); g.stroke();
  g.globalAlpha = 1; g.translate(px, py); g.rotate(ang);
  g.fillStyle = "#2a1a12"; g.fillRect(3, -3, 25, 6);                       // 테두리
  g.fillStyle = "#d8b07a"; g.fillRect(9, -2, 18, 4); g.fillStyle = "#f0d3a2"; g.fillRect(9, -2, 18, 1);   // 목검 날
  g.fillStyle = "#2a1a12"; g.fillRect(8, -5, 3, 10);                       // 코등이
  g.fillStyle = "#6e4527"; g.fillRect(3, -2, 5, 4);                        // 손잡이
  g.restore();
}

// ── 상태 ───────────────────────────────────────────────────────────────
const S = { id: null, name: "", look: 0, me: null, others: new Map(), logSeq: 0, typing: false, keys: new Set(), lastDir: 0 };
const cv = $("#pz-map"), ctx = cv.getContext("2d");

function newActor(p) { return { id: p.id, name: p.name, look: p.look, tx: p.x, ty: p.y, x: p.x * T, y: p.y * T,
  dir: p.dir || 0, gx: p.x, gy: p.y, from: null, t0: 0, moving: false, steps: 0, bubble: null, sayseq: p.say_seq || 0,
  actseq: p.act_seq || 0, hitseq: p.hit_seq || 0, attack: 0, hit: null }; }

function walkable(x, y) { return inside(x, y) && !solid[at(x, y)]; }
function spawn() {                          // 이름마다 늘 같은 자리에서 시작한다
  const r = rng(hash(S.name || "x"));
  for (let i = 0; i < 200; i++) { const x = 22 + Math.floor(r() * 12), y = 14 + Math.floor(r() * 5); if (walkable(x, y)) return [x, y]; }
  return [27, 15];
}

// ── 서버 ───────────────────────────────────────────────────────────────
async function post(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), keepalive: true });
  if (!r.ok) { const e = new Error(String(r.status)); e.status = r.status; throw e; }
  return r.json();
}
let es = null, joining = null;
async function join() {
  if (joining) return joining;
  joining = (async () => {
    const [sx, sy] = S.me ? [S.me.tx, S.me.ty] : spawn();
    const res = await post("/plaza/api/join", { name: S.name, look: S.look, x: sx, y: sy });
    S.id = res.id;
    if (!S.me) S.me = newActor({ id: res.id, name: res.name, look: S.look, x: sx, y: sy, dir: 0 });
    S.me.id = res.id;
    if (es) es.close();
    es = new EventSource(`/plaza/api/stream?id=${encodeURIComponent(S.id)}`);
    es.onmessage = ev => { try { applySnapshot(JSON.parse(ev.data)); } catch (_) { /* 한 틀 건너뜀 */ } };
    window.__plaza = S;
  })();
  try { await joining; } finally { joining = null; }
}
function sendMove() {
  if (!S.id || !S.me) return;
  post("/plaza/api/move", { id: S.id, x: S.me.tx, y: S.me.ty, dir: S.me.dir }).catch(e => { if (e.status === 404) join().catch(() => {}); });
}
setInterval(sendMove, 15000);
window.addEventListener("pagehide", () => { if (S.id) navigator.sendBeacon("/plaza/api/leave", JSON.stringify({ id: S.id })); });

function applySnapshot(s) {
  const seen = new Set();
  for (const p of s.players) {
    seen.add(p.id);
    const tnow = performance.now();
    if (p.id === S.id) {
      if (p.say && p.say_seq !== S.me.sayseq) S.me.sayseq = p.say_seq;
      if (p.hit_seq !== S.me.hitseq) { S.me.hitseq = p.hit_seq; if (p.hit_age < .8) S.me.hit = { t0: tnow - p.hit_age * 1000, by: p.hit_by }; }
      continue;
    }
    let a = S.others.get(p.id);
    if (!a) { a = newActor(p); S.others.set(p.id, a); }
    a.name = p.name; a.look = p.look;
    a.gx = p.x; a.gy = p.y;
    if (Math.abs(p.x - a.tx) + Math.abs(p.y - a.ty) > 3) { a.tx = p.x; a.ty = p.y; a.x = p.x * T; a.y = p.y * T; a.moving = false; }
    if (!a.moving && a.tx === a.gx && a.ty === a.gy) a.dir = p.dir;
    if (p.act_seq !== a.actseq) { a.actseq = p.act_seq; if (p.act_age < .6) a.attack = tnow - p.act_age * 1000; }
    if (p.hit_seq !== a.hitseq) { a.hitseq = p.hit_seq; if (p.hit_age < .8) a.hit = { t0: tnow - p.hit_age * 1000, by: p.hit_by }; }
    if (p.say && p.say_seq !== a.sayseq) { a.sayseq = p.say_seq; a.bubble = { text: p.say, until: performance.now() + p.say_left * 1000 }; }
  }
  for (const id of [...S.others.keys()]) if (!seen.has(id)) S.others.delete(id);
  $("#pz-online").textContent = `접속 ${s.online}명`;
  const who = $("#pz-who"); who.textContent = "";
  const b = document.createElement("b"); b.textContent = "광장에 있는 사람"; who.append(b);
  for (const p of s.players) { const d = document.createElement("div"); d.textContent = p.name; if (p.id === S.id) { d.className = "me"; d.textContent += " (나)"; } who.append(d); }
  const log = $("#pz-log");
  for (const m of s.log) {
    if (m.seq <= S.logSeq) continue; S.logSeq = m.seq;
    const d = document.createElement("div");
    const t = document.createElement("span"); t.className = "t"; t.textContent = m.at; d.append(t);
    if (m.sys) { d.className = "sys"; d.append(document.createTextNode(m.text)); }
    else { const n = document.createElement("span"); n.className = "n"; n.textContent = m.name + " :"; d.append(n, document.createTextNode(m.text));
      if (m.name === S.name) d.classList.add("mine"); }
    log.append(d); while (log.childElementCount > 40) log.firstElementChild.remove();
  }
}

// ── 이동 ───────────────────────────────────────────────────────────────
const DIRV = { 0: [0, 1], 1: [0, -1], 2: [-1, 0], 3: [1, 0] };
const KEYDIR = { ArrowDown: 0, ArrowUp: 1, ArrowLeft: 2, ArrowRight: 3, s: 0, w: 1, a: 2, d: 3, S: 0, W: 1, A: 2, D: 3,
  "ㄴ": 0, "ㅈ": 1, "ㅁ": 2, "ㅇ": 3 };
function heldDir() { const ks = [...S.keys]; return ks.length ? KEYDIR[ks[ks.length - 1]] : null; }
function stepActor(a, now, mine) {
  if (a.moving) {
    const k = Math.min(1, (now - a.t0) / STEP_MS);
    a.x = (a.from[0] + (a.tx - a.from[0]) * k) * T; a.y = (a.from[1] + (a.ty - a.from[1]) * k) * T;
    if (k >= 1) { a.moving = false; a.steps++; }
  }
  if (!a.moving && mine && !(a.attack && now - a.attack < ATK_MS)) {
    const d = heldDir();
    if (d != null && !S.typing) {
      const [dx, dy] = DIRV[d]; const changed = a.dir !== d; a.dir = d;
      if (walkable(a.tx + dx, a.ty + dy)) { a.from = [a.tx, a.ty]; a.tx += dx; a.ty += dy; a.t0 = now; a.moving = true; sendMove(); }
      else if (changed) sendMove();
    }
  }
  if (!a.moving && !mine && (a.tx !== a.gx || a.ty !== a.gy)) {   // 남의 캐릭터 — 서버 칸으로 한 칸씩
    const dx = Math.sign(a.gx - a.tx), dy = dx ? 0 : Math.sign(a.gy - a.ty);
    a.from = [a.tx, a.ty]; a.tx += dx; a.ty += dy; a.t0 = now; a.moving = true;
    a.dir = dx > 0 ? 3 : dx < 0 ? 2 : dy > 0 ? 0 : 1;
  }
}

// ── 그리기 ─────────────────────────────────────────────────────────────
const FONT = "'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR','WenQuanYi Zen Hei',sans-serif";
function wrap(g, text, maxW) {
  const lines = []; let cur = "";
  for (const ch of text) { if (g.measureText(cur + ch).width > maxW && cur) { lines.push(cur); cur = ch.trimStart(); } else cur += ch; }
  if (cur) lines.push(cur);
  if (lines.length > 4) { lines.length = 4; lines[3] = lines[3].slice(0, -1) + "…"; }
  return lines;
}
function bubbleBox(g, cx, top, text) {
  g.font = `12px ${FONT}`;
  const lines = wrap(g, text, 156), lw = Math.max(...lines.map(l => g.measureText(l).width));
  const w = Math.ceil(lw) + 16, h = lines.length * 16 + 10;
  return { lines, w, h, x: Math.round(cx - w / 2), y: Math.round(top - h - 10), cx, tip: top - 2 };
}
function drawBubble(g, b) {                 // 겹치면 위로 올린 자리에서 꼬리를 머리까지 늘인다
  const { x, y, w, h, cx, tip, lines } = b;
  g.font = `12px ${FONT}`;
  g.fillStyle = "rgba(0,0,0,.18)"; roundRect(g, x + 2, y + 3, w, h, 7); g.fill();
  g.fillStyle = "#fffef8"; g.strokeStyle = "#2b2b2b"; g.lineWidth = 1.5;
  const tx = Math.max(x + 10, Math.min(x + w - 10, cx));
  g.beginPath(); g.moveTo(tx - 5, y + h - 1); g.lineTo(cx, tip); g.lineTo(tx + 5, y + h - 1); g.closePath(); g.fill(); g.stroke();
  roundRect(g, x, y, w, h, 7); g.fill(); g.stroke();
  g.fillStyle = "#fffef8"; g.fillRect(tx - 4, y + h - 2, 8, 3);
  g.fillStyle = "#1b1b1b"; g.textAlign = "left"; g.textBaseline = "top";
  lines.forEach((l, i) => g.fillText(l, x + 8, y + 6 + i * 16));
}
function roundRect(g, x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
function nameTag(g, cx, y, name, mine) {
  g.font = `bold 12px ${FONT}`; g.textAlign = "center"; g.textBaseline = "top";
  g.lineWidth = 3; g.strokeStyle = "#111"; g.strokeText(name, cx, y);
  g.fillStyle = mine ? "#ffe066" : "#ffffff"; g.fillText(name, cx, y);
}

function resize() {
  const dpr = window.devicePixelRatio || 1, r = cv.getBoundingClientRect();
  cv.width = Math.max(1, Math.round(r.width * dpr)); cv.height = Math.max(1, Math.round(r.height * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.imageSmoothingEnabled = false;
}
window.addEventListener("resize", resize);

function frame(now) {
  requestAnimationFrame(frame);
  if (!S.me) return;
  stepActor(S.me, now, true);
  for (const a of S.others.values()) stepActor(a, now, false);
  const vw = cv.clientWidth, vh = cv.clientHeight;
  let cx = Math.round(S.me.x + T / 2 - vw / 2), cy = Math.round(S.me.y + T / 2 - vh / 2);
  cx = W * T <= vw ? Math.round((W * T - vw) / 2) : Math.max(0, Math.min(W * T - vw, cx));
  cy = H * T <= vh ? Math.round((H * T - vh) / 2) : Math.max(0, Math.min(H * T - vh, cy));
  ctx.fillStyle = "#24361b"; ctx.fillRect(0, 0, vw, vh);
  ctx.drawImage(groundImg, -cx, -cy);
  // 물결
  const tt = now / 600;
  ctx.fillStyle = "rgba(255,255,255,.35)";
  for (let y = 20; y < 31; y++) for (let x = 2; x < 19; x++) if (ground[at(x, y)] === WATER) {
    const ph = Math.sin(tt + x * 1.7 + y * 2.3); if (ph > .75) ctx.fillRect(x * T + 8 - cx + Math.round(ph * 6), y * T + 14 - cy, 8, 2);
  }
  // 깊이 순서로 소품 · 캐릭터
  const actors = [S.me, ...S.others.values()];
  const items = [];
  for (const p of props) if (p.x - cx < vw + 40 && p.x + p.img.width - cx > -40 && p.y - cy > -10 && p.y - p.img.height - cy < vh + 10) items.push({ y: p.y, p });
  for (const a of actors) items.push({ y: a.y + 28, a });
  items.sort((u, v) => u.y - v.y);
  for (const it of items) {
    if (it.p) { ctx.drawImage(it.p.img, Math.round(it.p.x - cx), Math.round(it.p.y - it.p.img.height - cy)); continue; }
    const a = it.a, k = a.moving ? Math.min(1, (now - a.t0) / STEP_MS) : 0;
    const fr = a.moving && k > .15 && k < .85 ? (a.steps % 2 ? 1 : 2) : 0;
    const sx = Math.round(a.x - cx), sy = Math.round(a.y - cy);
    const atk = a.attack && now - a.attack < ATK_MS ? (now - a.attack) / ATK_MS : -1;
    const hit = a.hit && now - a.hit.t0 < HIT_MS ? (now - a.hit.t0) / HIT_MS : -1;
    let ox = 0, oy = 0;
    if (atk >= 0) { const [dx, dy] = DIRV[a.dir], l = Math.sin(atk * Math.PI) * 3; ox = Math.round(dx * l); oy = Math.round(dy * l); }
    if (hit >= 0 && hit < .5) ox += Math.round(Math.sin(hit * 60) * 2);
    ell(ctx, sx + 16, sy + 28, 10, 4, "rgba(0,0,0,.25)");
    if (atk >= 0 && a.dir === 1) drawSwing(ctx, sx + ox, sy + oy, a.dir, atk);
    const spr = charSprite(a.look, a.dir, atk >= 0 ? 0 : fr);
    ctx.drawImage(hit >= 0 && hit < .6 && Math.floor(hit * 12) % 2 === 0 ? tinted(spr) : spr,
                  sx - 2 + ox, sy + 28 - 46 - 2 - (fr && atk < 0 ? 1 : 0) + oy);
    if (atk >= 0 && a.dir !== 1) drawSwing(ctx, sx + ox, sy + oy, a.dir, atk);
  }
  const boxes = [];
  for (const a of actors) {                 // 이름 · 말풍선은 맨 위
    const sx = Math.round(a.x - cx) + 16, sy = Math.round(a.y - cy);
    nameTag(ctx, sx, sy + 32, a.name, a === S.me);
    if (a.bubble && now < a.bubble.until) boxes.push(bubbleBox(ctx, sx, sy + 28 - 46, a.bubble.text));
    else a.bubble = null;
  }
  boxes.sort((u, v) => v.tip - u.tip);      // 아래 사람부터 자리를 잡고 겹치면 위로
  const placed = [];
  for (const b of boxes) {
    for (let moved = true, k = 0; moved && k < 12; k++) {
      moved = false;
      for (const o of placed) if (b.x < o.x + o.w + 4 && o.x < b.x + b.w + 4 && b.y < o.y + o.h + 4 && o.y < b.y + b.h + 4) {
        b.y = o.y - b.h - 6; moved = true; }
    }
    placed.push(b);
  }
  for (const b of placed) drawBubble(ctx, b);
  for (const a of actors) if (a.hit && now - a.hit.t0 < HIT_MS + 300) {   // 퍽!
    const k = (now - a.hit.t0) / (HIT_MS + 300), sx = Math.round(a.x - cx) + 16, sy = Math.round(a.y - cy);
    ctx.save(); ctx.globalAlpha = Math.max(0, 1 - k * k);
    ctx.font = `bold ${15 + Math.round((1 - k) * 4)}px ${FONT}`; ctx.textAlign = "center"; ctx.textBaseline = "bottom";
    const ty = sy + 2 - Math.round(k * 16), tx = sx + 24;      // 머리 옆 (말풍선 꼬리와 겹치지 않게)
    ctx.lineWidth = 4; ctx.strokeStyle = "#3a0d06"; ctx.strokeText("퍽!", tx, ty);
    ctx.fillStyle = "#ffdf3d"; ctx.fillText("퍽!", tx, ty);
    if (k < .45) for (let i = 0; i < 6; i++) { const ang = i / 6 * Math.PI * 2 + k * 3, r = 10 + k * 24;
      ctx.fillStyle = i % 2 ? "#fff6b0" : "#ff9a3c"; ctx.fillRect(Math.round(sx + Math.cos(ang) * r) - 2, Math.round(sy + 6 + Math.sin(ang) * r * .7) - 2, 4, 4); }
    ctx.restore();
  }
}

// ── 자판 · 대화 ─────────────────────────────────────────────────────────
const input = $("#pz-input"), chatBox = document.querySelector(".pz-chat");
function setTyping(on) { S.typing = on; chatBox.classList.toggle("typing", on); if (on) { S.keys.clear(); input.focus(); } else { input.blur(); cv.focus(); } }
function attack() {                         // 스페이스 — 앞을 휘두른다 (맞은 사람은 서버가 가린다)
  const now = performance.now();
  if (!S.me || !S.id || (S.me.attack && now - S.me.attack < ATK_MS + 20)) return;
  S.me.attack = now;
  post("/plaza/api/attack", { id: S.id }).catch(e => { if (e.status === 404) join().catch(() => {}); });
}
async function say(text) {
  text = text.replace(/\s+/g, " ").trim().slice(0, 80); if (!text || !S.id) return;
  S.me.bubble = { text, until: performance.now() + 7000 };
  try { await post("/plaza/api/say", { id: S.id, text }); }
  catch (e) { if (e.status === 404) { await join(); await post("/plaza/api/say", { id: S.id, text }); } }
}
document.addEventListener("keydown", ev => {
  if (!$("#pz-name").hidden) return;
  if (ev.isComposing || ev.keyCode === 229) return;          // 한글 조합 중
  if (ev.key === "Enter") {
    ev.preventDefault();
    if (!S.typing) { setTyping(true); return; }
    const t = input.value; input.value = ""; setTyping(false); say(t); return;
  }
  if (ev.key === "Escape" && S.typing) { input.value = ""; setTyping(false); return; }
  if (S.typing) return;
  if (ev.key === " " || ev.code === "Space") { ev.preventDefault(); if (!ev.repeat) attack(); return; }
  if (ev.key in KEYDIR) { ev.preventDefault(); S.keys.delete(ev.key); S.keys.add(ev.key); }
});
document.addEventListener("keyup", ev => { S.keys.delete(ev.key); if (ev.key.length === 1) { S.keys.delete(ev.key.toLowerCase()); S.keys.delete(ev.key.toUpperCase()); } });
input.addEventListener("focus", () => { S.typing = true; chatBox.classList.add("typing"); S.keys.clear(); });
input.addEventListener("blur", () => { S.typing = false; chatBox.classList.remove("typing"); });
cv.addEventListener("mousedown", () => { if (S.typing) setTyping(false); cv.focus(); });
function focusHint() { $("#pz-focus").hidden = !S.id || document.hasFocus(); }
window.addEventListener("focus", focusHint); window.addEventListener("blur", () => { S.keys.clear(); focusHint(); });
setInterval(focusHint, 1000);

// ── 이름 ───────────────────────────────────────────────────────────────
function storedName() { try { return (localStorage.getItem("pid.author") || "").trim(); } catch (_) { return ""; } }
function start(name) {
  S.name = name.slice(0, 20); S.look = hash(S.name) % 100000;
  $("#pz-me").textContent = S.name + " :";
  join().then(() => { cv.focus(); focusHint(); }).catch(() => { $("#pz-online").textContent = "광장에 들어가지 못했습니다 — 서버를 확인하세요"; });
}
function askName() {
  const box = $("#pz-name"), inp = $("#pz-namein"); box.hidden = false; inp.focus();
  const go = () => { const n = inp.value.replace(/\s+/g, " ").trim(); if (!n) { inp.focus(); return; }
    try { localStorage.setItem("pid.author", n); } catch (_) { /* 저장 못 해도 들어간다 */ }
    box.hidden = true; start(n); };
  $("#pz-nameok").onclick = go;
  inp.addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); e.stopPropagation(); go(); } });
}
if (EMBED) document.body.classList.add("embed");
resize(); requestAnimationFrame(frame);
const nm = (Q.get("user") || "").trim() || storedName();
if (nm) start(nm); else askName();
})();
