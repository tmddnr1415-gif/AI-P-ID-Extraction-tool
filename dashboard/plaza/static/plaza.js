/* 가상 광장 — 부여성 남쪽.  부서원이 캐릭터로 돌아다니며 말풍선으로 대화하고, Space 로 목검을 휘두른다.
 *
 * 그림은 전부 이 파일이 그린다 (그림 파일 0 · 외부 요청 0).  지도와 소품은 처음에 한 번 그려 두고
 * 매 틀마다 붙인다.  사람이 적은 글(이름 · 말)은 canvas 글자와 textContent 로만 그린다.
 * 서버(app/plaza.py)는 칸 좌표 · 말 · 이름 · 외형 번호 · 역할만 들고 있다.
 * 역할(머리 장식)은 서버가 정한다 — 그룹장 왕관 · 유닛장 사모 · 부서원 관모 · 운영자 노비 차림.
 */
(() => {
"use strict";
const T = 32, W = 56, H = 32;               // 칸 크기 · 지도 칸 수 (서버 MAP_W/MAP_H 와 같다)
const STEP_MS = 190;                        // 한 칸 걷는 시간
const PX = 2;                               // 캐릭터 한 점 = 2px
const ATK_MS = 280, HIT_MS = 520;          // 휘두르기 · 맞은 표시 시간
const FRAME = 14;                           // 화면 둘레 붉은 나무틀 두께
const PLACE = "부여성 남쪽";
const $ = s => document.querySelector(s);
const Q = new URLSearchParams(location.search);
const EMBED = Q.get("embed") === "1";

// ── 씨앗 있는 난수 (지도는 누구에게나 같다) ─────────────────────────────
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0;
  let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
  return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function hash(s) { let h = 2166136261; for (const ch of String(s)) { h ^= ch.codePointAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }

// ── 지도: 부여성 남쪽 — 주황 흙마당 · 생울타리 두른 잔디 · 남문과 성벽 ───────────
const DIRT = 0, LAWN = 1, PAVE = 2;
const ground = new Uint8Array(W * H), solid = new Uint8Array(W * H);
const at = (x, y) => y * W + x;
const inside = (x, y) => x >= 0 && y >= 0 && x < W && y < H;
function fill(t, x0, y0, x1, y1) { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (inside(x, y)) ground[at(x, y)] = t; }
function block(x0, y0, x1, y1) { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (inside(x, y)) solid[at(x, y)] = 1; }
const props = [];                           // {x, y(바닥 px), img}

fill(LAWN, 1, 1, 21, 10);                   // 왼쪽 위 큰 잔디밭
fill(LAWN, 33, 1, 54, 8);                   // 오른쪽 위 (민가)
fill(LAWN, 1, 13, 9, 21);                   // 왼쪽 가운데
fill(LAWN, 44, 12, 54, 25); fill(DIRT, 47, 16, 51, 22);   // 오른쪽 — 가운데가 빈 잔디 테
fill(LAWN, 27, 17, 28, 18);                 // 마당 가운데 작은 화단
fill(LAWN, 1, 24, 13, 28);                  // 왼쪽 아래
fill(PAVE, 25, 23, 30, 28);                 // 남문 앞 돌길
block(0, 0, W - 1, 0); block(0, 0, 0, H - 1); block(W - 1, 0, W - 1, H - 1);   // 지도 가장자리

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
  const isLawn = (x, y) => inside(x, y) && ground[at(x, y)] === LAWN;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const t = ground[at(x, y)], X = x * T, Y = y * T;
    if (t === DIRT) {
      g.fillStyle = "#c8834a"; g.fillRect(X, Y, T, T);
      for (let i = 0; i < 26; i++) { const v = r(); g.fillStyle = v < .4 ? "#b9743c" : v < .75 ? "#d2925a" : "#a9672f";
        g.fillRect(X + Math.floor(r() * 16) * 2, Y + Math.floor(r() * 16) * 2, 2, 2); }
    } else if (t === LAWN) {
      g.fillStyle = "#8d9a4f"; g.fillRect(X, Y, T, T);
      for (let i = 0; i < 30; i++) { const v = r(); g.fillStyle = v < .45 ? "#7b8a42" : v < .8 ? "#9ba85a" : "#6c7a39";
        g.fillRect(X + Math.floor(r() * 16) * 2, Y + Math.floor(r() * 16) * 2, 2, 2); }
    } else if (t === PAVE) {
      g.fillStyle = "#b39a7c"; g.fillRect(X, Y, T, T);
      g.fillStyle = "#937b5f"; g.fillRect(X, Y, T, 2); g.fillRect(X, Y, 2, T); g.fillRect(X + (y % 2 ? 16 : 0), Y + 16, 2, 16); g.fillRect(X, Y + 16, T, 2);
      g.fillStyle = "#c7b091"; g.fillRect(X + 3, Y + 3, 10, 2);
    }
  }
  // 생울타리 — 잔디밭 바깥 둘레에 짙은 덤불 띠 (부여성 남쪽처럼)
  const hedge = ["#3e5524", "#4b6629", "#5a7a31", "#6d8a3a"];
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (!isLawn(x, y)) continue;
    const X = x * T, Y = y * T;
    for (const [dx, dy] of [[0, -1], [0, 1], [-1, 0], [1, 0]]) {
      if (isLawn(x + dx, y + dy) || !inside(x + dx, y + dy)) continue;
      const bx = dx > 0 ? X + T - 12 : X, by = dy > 0 ? Y + T - 12 : Y, bw = dx ? 12 : T, bh = dy ? 12 : T;
      g.fillStyle = "rgba(60,30,10,.35)";                                    // 흙 쪽 그늘
      if (dy > 0) g.fillRect(X, Y + T, T, 3); if (dx > 0) g.fillRect(X + T, Y, 3, T);
      g.fillStyle = hedge[0]; g.fillRect(bx, by, bw, bh);
      for (let i = 0; i < 14; i++) {
        const cx = bx + 2 + r() * (bw - 4), cy = by + 2 + r() * (bh - 4), rr = 3 + r() * 3;
        ell(g, cx, cy, rr, rr * .85, hedge[1 + Math.floor(r() * 3)]);
      }
      for (let i = 0; i < 5; i++) { g.fillStyle = "#86a548"; g.fillRect(Math.round(bx + r() * (bw - 2)), Math.round(by + r() * (bh - 2)), 2, 2); }
    }
  }
  // 마른 풀포기 · 자갈 (흙마당)
  for (let i = 0; i < 260; i++) {
    const x = Math.floor(r() * W), y = Math.floor(r() * H);
    if (ground[at(x, y)] !== DIRT) continue;
    const X = x * T + 6 + Math.floor(r() * 10) * 2, Y = y * T + 8 + Math.floor(r() * 8) * 2;
    if (r() < .7) {
      const c = r() < .5 ? "#8a5a2c" : "#7d7a3c";
      g.fillStyle = c; g.fillRect(X, Y, 2, 6); g.fillRect(X - 4, Y - 2, 2, 4); g.fillRect(X - 2, Y + 1, 2, 2);
      g.fillRect(X + 4, Y - 3, 2, 4); g.fillRect(X + 2, Y, 2, 2); g.fillRect(X - 6, Y + 2, 2, 2);
      g.fillStyle = shade(c, .25); g.fillRect(X, Y, 2, 2); g.fillRect(X + 4, Y - 3, 2, 2);
    } else { g.fillStyle = "#9c8a72"; g.fillRect(X, Y, 4, 3); g.fillStyle = "#c2ae93"; g.fillRect(X, Y, 2, 1); }
  }
})();

// ── 소품 그림 ──────────────────────────────────────────────────────────
function treeImg(seed, big) {               // 바랜 올리브빛 나무 (부여성 잔디밭의 나무)
  const r = rng(seed), w = big ? 120 : 76, h = big ? 136 : 92, c = canvas(w, h), g = c.getContext("2d"), cx = w / 2;
  ell(g, cx + 6, h - 6, big ? 40 : 24, big ? 10 : 7, "rgba(30,25,10,.28)");
  g.fillStyle = "#5e4428"; g.fillRect(cx - (big ? 7 : 4), h - (big ? 50 : 34), big ? 14 : 8, big ? 46 : 30);
  g.fillStyle = "#4a331d"; g.fillRect(cx - (big ? 7 : 4), h - (big ? 50 : 34), 3, big ? 46 : 30);
  g.strokeStyle = "#5e4428"; g.lineWidth = big ? 4 : 3;                    // 뻗은 가지
  for (let i = 0; i < (big ? 5 : 3); i++) { g.beginPath(); g.moveTo(cx, h - (big ? 44 : 30));
    g.lineTo(cx + (r() - .5) * w * .7, h - (big ? 70 : 48) - r() * 20); g.stroke(); }
  const pal = ["#4f5f2c", "#62733a", "#7b8b49", "#93a25a"], blobs = big ? 18 : 10, cy = big ? 48 : 34, sr = big ? 46 : 28;
  for (let k = 0; k < 4; k++) for (let i = 0; i < blobs; i++) {
    const a = r() * Math.PI * 2, d = r() * sr * (1 - k * .22);
    ell(g, cx + Math.cos(a) * d, cy + Math.sin(a) * d * .6 - k * 3, (big ? 15 : 9) - k + r() * 4, ((big ? 15 : 9) - k + r() * 4) * .8, pal[k]);
  }
  if (big) { g.fillStyle = "#e8d7a0"; g.fillRect(cx - 9, h - 28, 18, 3);       // 당산나무 금줄
    for (let i = 0; i < 4; i++) { g.fillStyle = "#ffffff"; g.fillRect(cx - 7 + i * 4, h - 25, 2, 6); } }
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
    g.fillStyle = "#8b5a32";
    for (let k = 0; k <= ww; k += 6) g.fillRect(x0 + k, wallTop + 2, 1, 26);
    for (let k = 0; k <= 26; k += 6) g.fillRect(x0, wallTop + 2 + k, ww, 1);
  }
  roof(g, ox, 0, w, wallTop + 6, roofCol);
  return c;
}

function gateImg() {                        // 잔디밭의 작은 문 (지붕 얹은 두 기둥 — 부여성 남쪽의 그 문)
  const c = canvas(80, 84), g = c.getContext("2d");
  ell(g, 40, 78, 34, 5, "rgba(30,25,10,.25)");
  for (const x of [12, 62]) { g.fillStyle = "#6b6b5a"; g.fillRect(x, 26, 6, 52); g.fillStyle = "#545446"; g.fillRect(x, 26, 2, 52); }
  g.fillStyle = "#6b6b5a"; g.fillRect(10, 34, 60, 4); g.fillRect(14, 52, 52, 3);
  for (let x = 18; x < 62; x += 6) { g.fillStyle = "#7b7b68"; g.fillRect(x, 38, 2, 14); }
  roof(g, 8, 0, 64, 30, "#59604d");
  return c;
}
function fenceImg(len) {                    // 살 울타리
  const c = canvas(len * T, 52), g = c.getContext("2d");
  g.fillStyle = "rgba(30,25,10,.2)"; g.fillRect(2, 46, len * T - 4, 5);
  g.fillStyle = "#6b5a3e"; g.fillRect(0, 10, len * T, 4); g.fillRect(0, 30, len * T, 4);
  for (let x = 2; x < len * T; x += 8) { g.fillStyle = "#7d6a49"; g.fillRect(x, 4, 3, 44); g.fillStyle = "#5a4a31"; g.fillRect(x, 4, 1, 44); }
  for (let x = 0; x < len * T; x += 32) { g.fillStyle = "#4a3c27"; g.fillRect(x, 0, 5, 48); }
  return c;
}
function southGateImg() {                   // 남문 — 돌 기단에 무지개문 · 그 위 문루
  const w = 16 * T, h = 248, c = canvas(w + 48, h), g = c.getContext("2d"), ox = 24, base = h - 112;
  g.fillStyle = "rgba(30,20,10,.3)"; g.fillRect(ox - 6, h - 10, w + 12, 10);
  for (let y = base; y < h - 4; y += 12) for (let x = ox - ((y / 12) % 2) * 12; x < ox + w; x += 24) {   // 성돌
    g.fillStyle = ["#a59d8b", "#968e7c", "#b2aa98", "#8b836f"][Math.floor(((x * 7 + y * 13) % 97) / 25)];
    g.fillRect(Math.max(ox, x), y, Math.min(23, ox + w - Math.max(ox, x)), 11);
  }
  g.fillStyle = "#6d6656"; g.fillRect(ox, base, w, 3);
  const aw = 96, ax = ox + w / 2 - aw / 2;   // 무지개문
  g.fillStyle = "#2a1d14"; g.beginPath(); g.moveTo(ax, h - 4); g.lineTo(ax, base + 50); g.arc(ax + aw / 2, base + 50, aw / 2, Math.PI, 0); g.lineTo(ax + aw, h - 4); g.fill();
  g.fillStyle = "#8b2f1c"; g.fillRect(ax + 6, base + 58, aw / 2 - 8, h - base - 62); g.fillRect(ax + aw / 2 + 2, base + 58, aw / 2 - 8, h - base - 62);
  for (let k = 0; k < 4; k++) { g.fillStyle = "#d9a520"; g.fillRect(ax + 14, base + 70 + k * 10, 3, 3); g.fillRect(ax + aw - 17, base + 70 + k * 10, 3, 3); }
  const top = base - 64;                     // 문루
  g.fillStyle = "#efe6d0"; g.fillRect(ox + 60, top + 14, w - 120, 50);
  for (let x = ox + 60; x <= ox + w - 66; x += 46) { g.fillStyle = "#a8382a"; g.fillRect(x, top + 10, 7, 56); }
  g.fillStyle = "#2f7a6b"; g.fillRect(ox + 56, top + 6, w - 112, 8);          // 단청
  for (let x = ox + 58; x < ox + w - 58; x += 8) { g.fillStyle = x % 16 ? "#e0b24b" : "#c8423a"; g.fillRect(x, top + 8, 4, 4); }
  g.fillStyle = "#2a1a10"; g.fillRect(ox + w / 2 - 44, top + 24, 88, 22);      // 현판
  g.fillStyle = "#e8d39a"; g.font = "bold 14px 'Malgun Gothic','Apple SD Gothic Neo','WenQuanYi Zen Hei',serif"; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText("南 門", ox + w / 2, top + 35);
  roof(g, ox + 30, 0, w - 60, top + 8, "#4a5560");
  return c;
}
function castleWallImg(len) {
  const c = canvas(len * T, 92), g = c.getContext("2d");
  for (let y = 26; y < 92; y += 11) for (let x = -((y / 11) % 2) * 11; x < len * T; x += 22) {
    g.fillStyle = ["#a59d8b", "#968e7c", "#b2aa98", "#8b836f"][Math.floor(((x * 7 + y * 13) % 97) / 25)];
    g.fillRect(Math.max(0, x), y, 21, 10);
  }
  g.fillStyle = "#4b5560"; g.fillRect(0, 12, len * T, 14); g.fillStyle = "#3a434d"; for (let x = 0; x < len * T; x += 6) g.fillRect(x, 14, 2, 12);
  g.fillStyle = "#2f363e"; g.fillRect(0, 8, len * T, 5);
  for (let x = 0; x < len * T; x += 24) { g.fillStyle = "#8b836f"; g.fillRect(x + 4, 0, 14, 10); }   // 여장
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
  g.fillStyle = "#1e1e1e"; g.fillRect(4, 4, 20, 8); g.fillRect(9, 0, 10, 6);
  g.fillStyle = "#f2efe6"; g.fillRect(9, 16, 4, 3); g.fillRect(15, 16, 4, 3);
  g.fillStyle = "#111"; g.fillRect(10, 17, 2, 2); g.fillRect(16, 17, 2, 2);
  g.fillStyle = "#b8332d"; g.fillRect(12, 22, 4, 6); g.fillStyle = "#f2efe6"; g.fillRect(9, 30, 10, 3);
  g.fillStyle = "#111"; g.font = "bold 9px serif"; g.textAlign = "center";
  [...(top ? "天下大將軍" : "地下女將軍")].forEach((ch, i) => g.fillText(ch, 14, 44 + i * 8));
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
place(southGateImg(), 20, 31, { fw: 16, solid: [20, 28, 35, 31] });          // 남문
place(castleWallImg(20), 0, 31, { fw: 20, solid: [0, 30, 19, 31] });
place(castleWallImg(20), 36, 31, { fw: 20, solid: [36, 30, 55, 31] });
place(jangseungImg(true), 23, 26, { solid: [23, 26, 23, 26] });
place(jangseungImg(false), 32, 26, { solid: [32, 26, 32, 26] });
for (const [x, y] of [[24, 22], [31, 22]]) place(lanternImg(), x, y, { solid: [x, y, x, y] });
[[36, 2, 6, "#4b5560"], [45, 2, 6, "#56606a"]].forEach(([x, y, w, col], i) =>
  place(houseImg(100 + i, w, col), x, y + 3, { fw: w, solid: [x, y, x + w - 1, y + 3] }));
place(gateImg(), 10, 10, { fw: 2, solid: [10, 10, 10, 10] });
place(gateImg(), 49, 12, { fw: 2, solid: [49, 12, 49, 12] });
place(gateImg(), 5, 21, { fw: 2, solid: [5, 21, 5, 21] });
place(fenceImg(5), 14, 6, { fw: 5, solid: [14, 6, 18, 6] });
place(fenceImg(4), 3, 26, { fw: 4, solid: [3, 26, 6, 26] });
place(wellImg(), 20, 15, { fw: 2, solid: [20, 14, 21, 15], dy: -4 });
place(stallImg(), 37, 13, { fw: 3, solid: [37, 12, 39, 13] });
place(treeImg(77, true), 27, 18, { fw: 2, solid: [27, 18, 28, 18] });         // 가운데 화단의 당산나무
(function trees() {
  const r = rng(99);
  const free = (x, y) => inside(x, y) && !solid[at(x, y)] && ground[at(x, y)] === LAWN;
  for (let i = 0; i < 90; i++) {
    const x = 2 + Math.floor(r() * (W - 4)), y = 2 + Math.floor(r() * (H - 4));
    let ok = true; for (let yy = y - 1; yy <= y + 1 && ok; yy++) for (let xx = x - 1; xx <= x + 1; xx++) if (!free(xx, yy)) { ok = false; break; }
    if (ok) place(treeImg(1000 + x * 64 + y, false), x, y, { solid: [x, y, x, y] });
  }
})();

// ── 화면 틀 (붉은 꼰 기둥 · 모서리 장식 · 지명 현판) ──────────────────────
function twist(len, horiz) {
  const c = horiz ? canvas(len, FRAME) : canvas(FRAME, len), g = c.getContext("2d");
  g.fillStyle = "#6e1d12"; g.fillRect(0, 0, c.width, c.height);
  for (let i = -FRAME; i < len; i += 10) {
    g.fillStyle = "#b1452c"; g.beginPath();
    if (horiz) { g.moveTo(i, FRAME); g.lineTo(i + 6, FRAME); g.lineTo(i + 6 + FRAME, 0); g.lineTo(i + FRAME, 0); }
    else { g.moveTo(0, i); g.lineTo(0, i + 6); g.lineTo(FRAME, i + 6 + FRAME); g.lineTo(FRAME, i + FRAME); }
    g.fill();
    g.fillStyle = "rgba(255,210,170,.35)"; if (horiz) g.fillRect(i + FRAME, 2, 3, 2); else g.fillRect(2, i + FRAME, 2, 3);
  }
  g.fillStyle = "rgba(0,0,0,.35)"; if (horiz) g.fillRect(0, FRAME - 2, len, 2); else g.fillRect(FRAME - 2, 0, 2, len);
  return c;
}
let frameCache = null;
function frameImg(vw, vh) {
  if (frameCache && frameCache.width === vw && frameCache.height === vh) return frameCache;
  const c = canvas(vw, vh), g = c.getContext("2d");
  g.drawImage(twist(vw, true), 0, 0); g.drawImage(twist(vw, true), 0, vh - FRAME);
  g.drawImage(twist(vh, false), 0, 0); g.drawImage(twist(vh, false), vw - FRAME, 0);
  for (const [x, y] of [[0, 0], [vw - 34, 0], [0, vh - 34], [vw - 34, vh - 34]]) {   // 모서리 — 금빛 구름무늬
    g.fillStyle = "#3a1208"; g.fillRect(x, y, 34, 34);
    g.fillStyle = "#c9932f"; g.beginPath(); g.arc(x + 17, y + 17, 12, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#7a1d10"; g.beginPath(); g.arc(x + 17, y + 17, 8, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#f0c860"; g.beginPath(); g.arc(x + 14, y + 14, 3, 0, Math.PI * 2); g.fill();
    g.strokeStyle = "#c9932f"; g.lineWidth = 2; g.beginPath(); g.arc(x + 17, y + 17, 15, .4, 2.6); g.stroke();
  }
  g.font = `bold 14px ${FONT}`;                // 현판
  const tw = Math.ceil(g.measureText(PLACE).width) + 60, tx = Math.round(vw / 2 - tw / 2);
  g.fillStyle = "#1c120b"; g.beginPath(); g.moveTo(tx, 0); g.lineTo(tx + tw, 0); g.lineTo(tx + tw - 14, 26); g.lineTo(tx + 14, 26); g.closePath(); g.fill();
  g.strokeStyle = "#c9932f"; g.lineWidth = 2; g.stroke();
  g.fillStyle = "#f3ead2"; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(PLACE, vw / 2, 13);
  frameCache = c; return c;
}

// ── 캐릭터 — 외형(얼굴) 표 · 역할 머리 장식 ───────────────────────────────
// 칸의 개수는 서버 LOOK_RANGES 와 같다 (시험이 맞댄다)
const HAIRS = ["상투", "단발", "댕기머리", "쪽머리", "양갈래", "똥머리", "삐죽머리", "긴 생머리", "민머리", "포니테일"];
const HAIRC = ["#1d1612", "#3b2416", "#6b3a1f", "#9c4a28", "#c9a227", "#b8b8c4", "#3d5aa8", "#2f7a4a"];
const SKINS = ["#f6d3b0", "#efc49c", "#e3b086", "#c98f62"];
const EYES = ["점 눈", "큰 눈", "웃는 눈", "매서운 눈", "안경"];
const BEARDS = ["수염 없음", "콧수염", "염소수염", "덥수룩"];
const CLOTHS = ["#8fb06a", "#c23b2e", "#2e6db4", "#2f8c58", "#d9a520", "#7a4ea3", "#e0789a", "#34507a", "#9c5530", "#efe7d2", "#1f8a8a", "#5a5a66"];
const PANTS = ["#f1e9d4", "#55597a", "#e6d29f", "#6b705c", "#8a8f99", "#3b3b44"];
const RANGES = { hair: HAIRS.length, hairc: HAIRC.length, skin: SKINS.length, eyes: EYES.length, beard: BEARDS.length,
  cloth: CLOTHS.length, pants: PANTS.length };
const ROLE_LABEL = { leader: "그룹장", unit: "유닛장", operator: "운영자", member: "" };
const ROLE_COLOR = { leader: "#ffd84a", unit: "#ffb36b", operator: "#d8c59a" };
function defaultFace(name) {                // 처음 들어온 사람 — 이름에서 정한 외형
  const n = hash(name);
  return { hair: n % 10, hairc: (n >>> 4) % 3, skin: (n >>> 7) % 3, eyes: (n >>> 9) % 3, beard: 0,
    cloth: (n >>> 12) % 12, pants: (n >>> 16) % 6 };
}
function faceOf(a) {                       // 서버가 준 값도 범위 밖이면 이름에서 정한 값으로
  const d = defaultFace(a.name), f = a.face || d, out = {};
  for (const k of Object.keys(RANGES)) out[k] = Number.isInteger(f[k]) && f[k] >= 0 && f[k] < RANGES[k] ? f[k] : d[k];
  return out;
}

const OL = "#2a1a12", K = "#161616", OX = 2, OY = 4;   // 장식이 머리 위 · 옆으로 나갈 여백 (점 단위)
const spriteCache = new Map();
// dir: 0 아래 · 1 위 · 2 왼쪽 · 3 오른쪽 / frame: 0 섬 · 1 · 2 걸음 / role: member · unit · leader · operator · bare
function charSprite(F, role, dir, frame) {
  const key = `${JSON.stringify(F)}|${role}|${dir}|${frame}`; if (spriteCache.has(key)) return spriteCache.get(key);
  const c = canvas((16 + OX * 2) * PX, (24 + OY) * PX), g = c.getContext("2d");
  const flip = dir === 3, side = dir >= 2, up = dir === 1, down = dir === 0;
  const H_ = HAIRC[F.hairc], SK = SKINS[F.skin];
  const nobi = role === "operator";
  const CL = nobi ? "#c8b48a" : CLOTHS[F.cloth], PA = nobi ? "#8c7a5a" : PANTS[F.pants];
  const RIB = ["#c0262d", "#7a1fa2", "#d9480f"][F.cloth % 3];
  const rect = (x, y, w, h, col) => { g.fillStyle = col; g.fillRect((OX + (flip ? 16 - x - w : x)) * PX, (OY + y) * PX, w * PX, h * PX); };
  function draw(parts) {                     // 테두리 먼저, 그다음 색
    for (const [x, y, w, h, , rnd, ol] of parts) if (ol !== false) {
      if (rnd) { rect(x, y - 1, w, h + 2, OL); rect(x - 1, y, w + 2, h, OL); } else rect(x - 1, y - 1, w + 2, h + 2, OL);
    }
    for (const [x, y, w, h, col, rnd] of parts) {
      if (rnd && w > 2 && h > 2) { rect(x + 1, y, w - 2, h, col); rect(x, y + 1, w, h - 2, col); } else rect(x, y, w, h, col);
    }
  }
  const step = frame === 1 ? 1 : frame === 2 ? -1 : 0, hs = F.hair;
  const back = [], P = [];
  // 몸 뒤로 늘어지는 머리
  if (hs === 7) back.push(up ? [3, 3, 10, 14, H_] : side ? [8, 4, 5, 12, H_] : [2, 5, 12, 11, H_]);
  if (hs === 4) { if (!side) { back.push([0, 6, 3, 6, H_, true], [13, 6, 3, 6, H_, true]); } else back.push([11, 6, 3, 6, H_, true]); }
  draw(back);
  // 다리 · 신
  if (!side) {
    P.push([5, 19 - (step > 0 ? 1 : 0), 2, 3, PA], [9, 19 - (step < 0 ? 1 : 0), 2, 3, PA],
           [5, 22 - (step > 0 ? 1 : 0), 2, 1, "#3a2a20"], [9, 22 - (step < 0 ? 1 : 0), 2, 1, "#3a2a20"]);
  } else P.push([6 - step, 19, 2, 3, PA], [8 + step, 19, 2, 3, PA], [5 - step, 22, 3, 1, "#3a2a20"], [8 + step, 22, 3, 1, "#3a2a20"]);
  // 몸 · 팔
  if (!side) {
    const la = step > 0 ? -1 : step < 0 ? 1 : 0;
    P.push([4, 13, 8, 6, CL, true], [2, 14 + la, 2, 4, CL], [12, 14 - la, 2, 4, CL],
           [2, 18 + la, 2, 1, SK, false, false], [12, 18 - la, 2, 1, SK, false, false]);
  } else P.push([5, 13, 6, 6, CL, true], [7 + step, 14, 2, 4, shade(CL, -.22)], [7 + step, 18, 2, 1, SK, false, false]);
  // 머리 뒤 장식
  if (hs === 3 && !down) P.push(up ? [6, 8, 4, 4, H_, true] : [11, 6, 4, 4, H_, true]);
  if (hs === 2 && !down) P.push(up ? [7, 11, 2, 7, H_] : [11, 10, 2, 8, H_]);
  if (hs === 9 && !down) P.push(up ? [7, 9, 2, 8, H_] : [12, 5, 3, 7, H_, true]);
  // 머리
  P.push([3, 3, 10, 10, up && hs !== 8 ? H_ : SK, true]);
  if (hs === 5) P.push(side ? [8, 0, 3, 3, H_, true] : [2, 0, 3, 3, H_, true], ...(side ? [] : [[11, 0, 3, 3, H_, true]]));
  if (hs === 0) P.push([side ? 7 : 6, 0, side ? 3 : 4, 3, H_, true]);
  if (hs === 6) P.push([4, 0, 2, 3, H_], [7, -1, 2, 4, H_], [10, 0, 2, 3, H_]);
  if (hs !== 8) P.push([3, 2, 10, 4, H_, true]);
  draw(P);
  // 얼굴 · 머리 결 · 옷 무늬 (테두리 없음)
  const px = rect;
  if (down) {
    if (hs !== 8) { px(3, 5, 1, hs === 1 ? 6 : 4, H_); px(12, 5, 1, hs === 1 ? 6 : 4, H_); px(4, 5, 3, 1, H_); px(9, 5, 3, 1, H_); }
    else px(5, 4, 2, 1, "#fff2d8");
    const e = F.eyes;
    if (e === 1) { px(4, 8, 2, 2, "#fff"); px(5, 8, 1, 2, K); px(10, 8, 2, 2, "#fff"); px(10, 8, 1, 2, K); }
    else if (e === 2) { px(4, 9, 1, 1, K); px(5, 8, 1, 1, K); px(6, 9, 1, 1, K); px(9, 9, 1, 1, K); px(10, 8, 1, 1, K); px(11, 9, 1, 1, K); }
    else if (e === 4) { px(4, 7, 3, 3, "#2a2a2a"); px(5, 8, 1, 1, "#bfe0ff"); px(9, 7, 3, 3, "#2a2a2a"); px(10, 8, 1, 1, "#bfe0ff"); px(7, 8, 2, 1, "#2a2a2a"); }
    else { px(5, 8, 1, 2, K); px(10, 8, 1, 2, K); if (e === 3) { px(4, 6, 2, 1, K); px(6, 7, 1, 1, K); px(10, 6, 2, 1, K); px(9, 7, 1, 1, K); } }
    if (e !== 4 && F.beard !== 3) { px(4, 10, 1, 1, "#f19a8f"); px(11, 10, 1, 1, "#f19a8f"); }
    px(7, 11, 2, 1, "#a8483f");
    if (F.beard === 1) px(6, 11, 4, 1, H_); else if (F.beard === 2) px(7, 12, 2, 2, H_);
    else if (F.beard === 3) { px(4, 10, 8, 3, H_); px(7, 11, 2, 1, "#a8483f"); }
    px(7, 13, 2, 1, SK); px(6, 13, 1, 1, "#fbf6ea"); px(7, 14, 1, 1, "#fbf6ea"); px(9, 13, 1, 1, "#fbf6ea"); px(8, 14, 1, 1, "#fbf6ea");
    if (!nobi) { px(8, 15, 1, 3, RIB); px(9, 15, 1, 2, RIB); }
    px(4, 18, 8, 1, shade(CL, -.22));
  } else if (up) {
    px(5, 12, 6, 1, SK); if (hs !== 8) px(4, 4, 2, 1, shade(H_, .2)); px(4, 18, 8, 1, shade(CL, -.22));
    if (hs === 2) px(7, 17, 2, 2, RIB); if (hs === 3) px(3, 9, 10, 1, "#d4af37");
  } else {
    if (hs !== 8) { px(8, 4, 5, hs === 1 ? 8 : 6, H_); px(11, 9, 2, 2, H_); px(3, 5, 2, 1, H_); } else px(6, 4, 2, 1, "#fff2d8");
    const e = F.eyes;
    if (e === 1) { px(3, 8, 2, 2, "#fff"); px(4, 8, 1, 2, K); }
    else if (e === 2) { px(3, 9, 1, 1, K); px(4, 8, 1, 1, K); px(5, 9, 1, 1, K); }
    else if (e === 4) { px(3, 7, 3, 3, "#2a2a2a"); px(4, 8, 1, 1, "#bfe0ff"); px(6, 8, 3, 1, "#2a2a2a"); }
    else { px(4, 8, 1, 2, K); if (e === 3) { px(3, 6, 2, 1, K); px(5, 7, 1, 1, K); } }
    if (e !== 4) px(4, 10, 1, 1, "#f19a8f"); px(3, 9, 1, 1, SK);
    if (F.beard === 1) px(3, 11, 3, 1, H_); else if (F.beard === 2) px(3, 12, 2, 2, H_); else if (F.beard === 3) px(3, 10, 5, 3, H_);
    px(5, 13, 1, 1, "#fbf6ea"); px(6, 14, 1, 1, "#fbf6ea"); px(5, 18, 6, 1, shade(CL, -.22));
    if (hs === 2) px(11, 17, 2, 2, RIB); if (hs === 3) px(10, 7, 5, 1, "#d4af37");
  }
  if (nobi) {                               // 노비 — 무명옷 기운 자국 · 새끼줄 허리띠
    px(side ? 6 : 5, 15, 2, 2, "#a8946a"); px(side ? 9 : 10, 16, 1, 1, "#a8946a"); px(side ? 5 : 4, 17, side ? 6 : 8, 1, "#7a5a30");
  }
  // 역할 머리 장식 (서버가 정한 것)
  const HAT = [];
  if (role === "leader") {                  // 왕관
    const G = "#e8b923";
    HAT.push([4, 1, 8, 2, G], [4, -1, 2, 2, G], [7, -2, 2, 3, G], [10, -1, 2, 2, G]);
    draw(HAT); px(4, 1, 8, 1, "#fff0a0"); px(7, 1, 2, 1, "#d62d3a"); px(5, 2, 1, 1, "#2e7bd6"); px(10, 2, 1, 1, "#2e7bd6"); px(7, -2, 2, 1, "#fff0a0");
  } else if (role === "unit") {             // 사모 — 날개 달린 관모
    HAT.push([5, -1, 6, 2, K, true], [4, 0, 8, 4, K, true]);
    if (side) HAT.push([12, -1, 2, 4, K, true]); else HAT.push([-1, 1, 4, 2, K, true], [13, 1, 4, 2, K, true]);
    draw(HAT); px(4, 3, 8, 1, "#3a2c1e"); if (down) px(7, 1, 2, 1, "#c9a227"); px(5, 0, 2, 1, "#3c3c3c");
  } else if (role === "member") {           // 관모
    HAT.push([5, -1, 6, 2, "#2a2a2a", true], [4, 0, 8, 4, "#2a2a2a", true]);
    draw(HAT); px(4, 3, 8, 1, "#4a3a2a"); px(5, 0, 2, 1, "#474747");
  } else if (role === "operator") {         // 노비 — 두건
    const B = "#e7dfc8";
    HAT.push([3, 4, 10, 2, B]);
    if (up) HAT.push([7, 6, 1, 3, B], [8, 6, 1, 2, B]); else if (side) HAT.push([12, 4, 3, 2, B], [13, 6, 2, 2, B]);
    draw(HAT); px(3, 5, 10, 1, "#cfc4a4");
  }
  spriteCache.set(key, c); return c;
}

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
  g.fillStyle = "#2a1a12"; g.fillRect(3, -3, 25, 6);
  g.fillStyle = "#d8b07a"; g.fillRect(9, -2, 18, 4); g.fillStyle = "#f0d3a2"; g.fillRect(9, -2, 18, 1);
  g.fillStyle = "#2a1a12"; g.fillRect(8, -5, 3, 10);
  g.fillStyle = "#6e4527"; g.fillRect(3, -2, 5, 4);
  g.restore();
}

// ── 상태 ───────────────────────────────────────────────────────────────
const S = { id: null, name: "", look: 0, face: null, role: "member", me: null, others: new Map(), logSeq: 0,
  typing: false, keys: new Set(), panel: false, status: "", atkHeld: false };
const cv = $("#pz-map"), ctx = cv.getContext("2d");

function newActor(p) { return { id: p.id, name: p.name, face: p.face || null, role: p.role || "member", tx: p.x, ty: p.y, x: p.x * T, y: p.y * T,
  dir: p.dir || 0, gx: p.x, gy: p.y, from: null, t0: 0, moving: false, steps: 0, bubble: null, sayseq: p.say_seq || 0,
  actseq: p.act_seq || 0, hitseq: p.hit_seq || 0, attack: 0, hit: null, status: p.status || "" }; }

function walkable(x, y) { return inside(x, y) && !solid[at(x, y)]; }
// 캐릭터끼리 겹치지 않음 (2026-10-16 대시보드): 다른 사람이 서 있거나(서버 칸) 가고 있는 칸은 막힘 — 서버도 같은 규칙으로 막음
function occupied(x, y) { for (const a of S.others.values()) if ((a.gx === x && a.gy === y) || (a.tx === x && a.ty === y)) return true; return false; }
function freeNear(x, y) {                   // 들어오자마자 남과 같은 칸이면 가장 가까운 빈 칸으로
  for (let r = 1; r < 8; r++) for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
    if (Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
    const nx = x + dx, ny = y + dy; if (walkable(nx, ny) && !occupied(nx, ny)) return [nx, ny]; }
  return null;
}
function spawn() {                          // 이름마다 늘 같은 자리에서 시작한다 (흙마당 가운데)
  const r = rng(hash(S.name || "x"));
  for (let i = 0; i < 200; i++) { const x = 22 + Math.floor(r() * 12), y = 13 + Math.floor(r() * 8); if (walkable(x, y) && ground[at(x, y)] !== LAWN) return [x, y]; }
  return [27, 15];
}

// ── 서버 ───────────────────────────────────────────────────────────────
async function post(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), keepalive: true });
  if (!r.ok) { let msg = String(r.status); try { msg = (await r.json()).detail || msg; } catch (_) { /* 글 없음 */ }
    const e = new Error(msg); e.status = r.status; throw e; }
  return r.json();
}
function storedFace() { try { return JSON.parse(localStorage.getItem("pid.plaza.face") || "null"); } catch (_) { return null; } }
let es = null, joining = null;
async function join() {
  if (joining) return joining;
  joining = (async () => {
    const [sx, sy] = S.me ? [S.me.tx, S.me.ty] : spawn();
    const res = await post("/plaza/api/join", { name: S.name, look: S.look, face: S.face || storedFace(), x: sx, y: sy, status: S.status });
    S.id = res.id; S.face = res.face || S.face; S.role = res.role || "member";
    if (!S.me) S.me = newActor({ id: res.id, name: res.name, face: S.face, role: S.role, x: sx, y: sy, dir: 0 });
    S.me.id = res.id; S.me.face = S.face; S.me.role = S.role;
    $("#pz-roles").hidden = S.role !== "operator";
    if (es) es.close();
    es = new EventSource(`/plaza/api/stream?id=${encodeURIComponent(S.id)}`);
    es.onmessage = ev => { try { applySnapshot(JSON.parse(ev.data)); } catch (_) { /* 한 틀 건너뜀 */ } };
    window.__plaza = S;
  })();
  try { await joining; } finally { joining = null; }
}
function sendMove() {
  if (!S.id || !S.me) return;
  post("/plaza/api/move", { id: S.id, x: S.me.tx, y: S.me.ty, dir: S.me.dir })
    .then(r => { if (r && r.blocked && S.me) { S.me.tx = r.x; S.me.ty = r.y; S.me.x = r.x * T; S.me.y = r.y * T; S.me.moving = false; } })   // 남이 먼저 선 칸 → 되돌아감
    .catch(e => { if (e.status === 404) join().catch(() => {}); });
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
      if (p.role && p.role !== S.role) { S.role = S.me.role = p.role; $("#pz-roles").hidden = S.role !== "operator"; }
      continue;
    }
    let a = S.others.get(p.id);
    if (!a) { a = newActor(p); S.others.set(p.id, a); }
    a.name = p.name; a.face = p.face || null; a.role = p.role || "member"; a.status = p.status || "";
    a.gx = p.x; a.gy = p.y;
    if (Math.abs(p.x - a.tx) + Math.abs(p.y - a.ty) > 3) { a.tx = p.x; a.ty = p.y; a.x = p.x * T; a.y = p.y * T; a.moving = false; }
    if (!a.moving && a.tx === a.gx && a.ty === a.gy) a.dir = p.dir;
    if (p.act_seq !== a.actseq) { a.actseq = p.act_seq; if (p.act_age < .6) a.attack = tnow - p.act_age * 1000; }
    if (p.hit_seq !== a.hitseq) { a.hitseq = p.hit_seq; if (p.hit_age < .8) a.hit = { t0: tnow - p.hit_age * 1000, by: p.hit_by }; }
    if (p.say && p.say_seq !== a.sayseq) { a.sayseq = p.say_seq; a.bubble = { text: p.say, until: performance.now() + p.say_left * 1000 }; }
  }
  for (const id of [...S.others.keys()]) if (!seen.has(id)) S.others.delete(id);
  if (S.me && !S.me.moving && occupied(S.me.tx, S.me.ty)) {   // 남과 같은 칸 → 가장 가까운 빈 칸으로 비켜섬
    const f = freeNear(S.me.tx, S.me.ty); if (f) { S.me.tx = f[0]; S.me.ty = f[1]; S.me.x = f[0] * T; S.me.y = f[1] * T; sendMove(); }
  }
  S.online = s.players;
  $("#pz-online").textContent = `접속 ${s.online}명`;
  const who = $("#pz-who"); who.textContent = "";
  const b = document.createElement("b"); b.textContent = "광장에 있는 사람"; who.append(b);
  const order = { leader: 0, unit: 1, member: 2, operator: 3 };
  for (const p of [...s.players].sort((u, v) => (order[u.role] ?? 2) - (order[v.role] ?? 2))) {
    const d = document.createElement("div");
    if (ROLE_LABEL[p.role]) { const t = document.createElement("span"); t.className = "role " + p.role; t.textContent = ROLE_LABEL[p.role]; d.append(t); }
    d.append(document.createTextNode(p.name + (p.id === S.id ? " (나)" : "") + (p.status ? ` (${p.status})` : "")));
    if (p.id === S.id) d.classList.add("me");
    who.append(d);
  }
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
// 이동은 키보드 방향키(←↑→↓)만.  key 대신 code 를 먼저 본다 — 한글 입력기가 켜져 있으면 key 가
// "Process"/"Unidentified" 로 오는 PC 가 있다.  "Up"/"Down" … 은 옛 브라우저가 쓰는 이름.
const KEYDIR = { ArrowDown: 0, ArrowUp: 1, ArrowLeft: 2, ArrowRight: 3, Down: 0, Up: 1, Left: 2, Right: 3 };
const KEYCODE = { 40: "ArrowDown", 38: "ArrowUp", 37: "ArrowLeft", 39: "ArrowRight" };
function arrowOf(ev) { return [ev.code, ev.key, KEYCODE[ev.keyCode]].find(k => k && k in KEYDIR) || null; }
function heldDir() { const ks = [...S.keys]; return ks.length ? KEYDIR[ks[ks.length - 1]] : null; }
function stepActor(a, now, mine) {
  if (a.moving) {
    const k = Math.min(1, (now - a.t0) / STEP_MS);
    a.x = (a.from[0] + (a.tx - a.from[0]) * k) * T; a.y = (a.from[1] + (a.ty - a.from[1]) * k) * T;
    if (k >= 1) { a.moving = false; a.steps++; }
  }
  if (!a.moving && mine && !(a.attack && now - a.attack < ATK_MS)) {
    const d = heldDir();
    if (d != null && !S.typing && !S.panel) {
      const [dx, dy] = DIRV[d]; const changed = a.dir !== d; a.dir = d;
      if (walkable(a.tx + dx, a.ty + dy) && !occupied(a.tx + dx, a.ty + dy)) { a.from = [a.tx, a.ty]; a.tx += dx; a.ty += dy; a.t0 = now; a.moving = true; sendMove(); }
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
function bubbleBox(g, cx, top, name, text) {   // 바람의나라처럼 "이름 : 말"
  g.font = `12px ${FONT}`;
  const lines = wrap(g, `${name} : ${text}`, 170), lw = Math.max(...lines.map(l => g.measureText(l).width));
  const w = Math.ceil(lw) + 16, h = lines.length * 16 + 8;
  return { lines, w, h, x: Math.round(cx - w / 2), y: Math.round(top - h - 10), cx, tip: top - 2 };
}
function drawBubble(g, b) {                 // 겹치면 위로 올린 자리에서 꼬리를 머리까지 늘인다
  const { x, y, w, h, cx, tip, lines } = b;
  g.font = `12px ${FONT}`;
  g.fillStyle = "rgba(0,0,0,.22)"; roundRect(g, x + 2, y + 3, w, h, 9); g.fill();
  g.fillStyle = "#f4f2ec"; g.strokeStyle = "#1e1e1e"; g.lineWidth = 2;
  const tx = Math.max(x + 10, Math.min(x + w - 10, cx));
  g.beginPath(); g.moveTo(tx - 5, y + h - 1); g.lineTo(cx, tip); g.lineTo(tx + 5, y + h - 1); g.closePath(); g.fill(); g.stroke();
  roundRect(g, x, y, w, h, 9); g.fill(); g.stroke();
  g.fillStyle = "#f4f2ec"; g.fillRect(tx - 4, y + h - 2, 8, 3);
  g.fillStyle = "#111"; g.textAlign = "left"; g.textBaseline = "top";
  lines.forEach((l, i) => g.fillText(l, x + 8, y + 5 + i * 16));
}
function roundRect(g, x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
function nameTag(g, cx, y, a, mine) {       // [그룹장] 이름 — 칭호는 역할 색
  g.font = `bold 12px ${FONT}`; g.textBaseline = "top"; g.textAlign = "left"; g.lineWidth = 3; g.strokeStyle = "#111";
  const title = ROLE_LABEL[a.role] ? `[${ROLE_LABEL[a.role]}] ` : "";
  const tw = g.measureText(title).width, nw = g.measureText(a.name).width, x0 = Math.round(cx - (tw + nw) / 2);
  if (title) { g.strokeText(title, x0, y); g.fillStyle = ROLE_COLOR[a.role]; g.fillText(title, x0, y); }
  g.strokeText(a.name, x0 + tw, y); g.fillStyle = mine ? "#ffe066" : "#ffffff"; g.fillText(a.name, x0 + tw, y);
}

function statusTag(g, cx, y, text) {       // 대시보드에서 보는 화면 — '(P&ID 분석 중...)' (글자로만 그림)
  g.font = `bold 11px ${FONT}`; g.textBaseline = "top"; g.textAlign = "center"; g.lineWidth = 3; g.strokeStyle = "#111";
  const t = `(${text})`; g.strokeText(t, cx, y); g.fillStyle = "#8fe3ff"; g.fillText(t, cx, y); g.textAlign = "left";
}
// 대시보드(부모 창)가 지금 보는 화면을 알려 줌 → 서버에 남겨 모두에게 보임
function setStatus(text) {
  S.status = String(text || "").replace(/\s+/g, " ").trim().slice(0, 24);
  if (S.id) post("/plaza/api/status", { id: S.id, text: S.status }).catch(e => { if (e.status === 404) join().catch(() => {}); });
}
window.addEventListener("message", ev => {
  if (ev.source !== window.parent || !ev.data || ev.data.type !== "plaza-status") return;
  setStatus(ev.data.text);
});
function resize() {
  const dpr = window.devicePixelRatio || 1, r = cv.getBoundingClientRect();
  cv.width = Math.max(1, Math.round(r.width * dpr)); cv.height = Math.max(1, Math.round(r.height * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.imageSmoothingEnabled = false;
}
window.addEventListener("resize", resize);

function drawActor(g, a, sx, sy, now) {
  const k = a.moving ? Math.min(1, (now - a.t0) / STEP_MS) : 0;
  const fr = a.moving && k > .15 && k < .85 ? (a.steps % 2 ? 1 : 2) : 0;
  const atk = a.attack && now - a.attack < ATK_MS ? (now - a.attack) / ATK_MS : -1;
  const hit = a.hit && now - a.hit.t0 < HIT_MS ? (now - a.hit.t0) / HIT_MS : -1;
  let ox = 0, oy = 0;
  if (atk >= 0) { const [dx, dy] = DIRV[a.dir], l = Math.sin(atk * Math.PI) * 3; ox = Math.round(dx * l); oy = Math.round(dy * l); }
  if (hit >= 0 && hit < .5) ox += Math.round(Math.sin(hit * 60) * 2);
  ell(g, sx + 16, sy + 28, 10, 4, "rgba(40,20,5,.3)");
  if (atk >= 0 && a.dir === 1) drawSwing(g, sx + ox, sy + oy, a.dir, atk);
  const spr = charSprite(faceOf(a), a.role, a.dir, atk >= 0 ? 0 : fr);
  g.drawImage(hit >= 0 && hit < .6 && Math.floor(hit * 12) % 2 === 0 ? tinted(spr) : spr,
              sx - OX * PX + ox, sy + 28 - 46 - OY * PX - (fr && atk < 0 ? 1 : 0) + oy);
  if (atk >= 0 && a.dir !== 1) drawSwing(g, sx + ox, sy + oy, a.dir, atk);
}

function frame(now) {
  requestAnimationFrame(frame);
  if (S.panel) drawPreview(now);
  if (!S.me) return;
  if (S.atkHeld && !S.typing && !S.panel) attack();   // Space 를 누르고 있는 동안 계속 휘두름
  stepActor(S.me, now, true);
  for (const a of S.others.values()) stepActor(a, now, false);
  const vw = cv.clientWidth, vh = cv.clientHeight;
  let cx = Math.round(S.me.x + T / 2 - vw / 2), cy = Math.round(S.me.y + T / 2 - vh / 2);
  cx = W * T <= vw ? Math.round((W * T - vw) / 2) : Math.max(-FRAME, Math.min(W * T - vw + FRAME, cx));
  cy = H * T <= vh ? Math.round((H * T - vh) / 2) : Math.max(-FRAME, Math.min(H * T - vh + FRAME, cy));
  ctx.fillStyle = "#3a2414"; ctx.fillRect(0, 0, vw, vh);
  ctx.drawImage(groundImg, -cx, -cy);
  const actors = [S.me, ...S.others.values()];
  const items = [];
  for (const p of props) if (p.x - cx < vw + 40 && p.x + p.img.width - cx > -40 && p.y - cy > -10 && p.y - p.img.height - cy < vh + 10) items.push({ y: p.y, p });
  for (const a of actors) items.push({ y: a.y + 28, a });
  items.sort((u, v) => u.y - v.y);
  for (const it of items) {
    if (it.p) { ctx.drawImage(it.p.img, Math.round(it.p.x - cx), Math.round(it.p.y - it.p.img.height - cy)); continue; }
    drawActor(ctx, it.a, Math.round(it.a.x - cx), Math.round(it.a.y - cy), now);
  }
  const boxes = [];
  for (const a of actors) {                 // 이름 · 말풍선은 맨 위
    const sx = Math.round(a.x - cx) + 16, sy = Math.round(a.y - cy);
    nameTag(ctx, sx, sy + 32, a, a === S.me);
    if (a.status) statusTag(ctx, sx, sy + 47, a.status);
    if (a.bubble && now < a.bubble.until) boxes.push(bubbleBox(ctx, sx, sy + 28 - 46 - 6, a.name, a.bubble.text));
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
    const ty = sy + 2 - Math.round(k * 16), tx = sx + 24;
    ctx.lineWidth = 4; ctx.strokeStyle = "#3a0d06"; ctx.strokeText("퍽!", tx, ty);
    ctx.fillStyle = "#ffdf3d"; ctx.fillText("퍽!", tx, ty);
    if (k < .45) for (let i = 0; i < 6; i++) { const ang = i / 6 * Math.PI * 2 + k * 3, r = 10 + k * 24;
      ctx.fillStyle = i % 2 ? "#fff6b0" : "#ff9a3c"; ctx.fillRect(Math.round(sx + Math.cos(ang) * r) - 2, Math.round(sy + 6 + Math.sin(ang) * r * .7) - 2, 4, 4); }
    ctx.restore();
  }
  ctx.drawImage(frameImg(vw, vh), 0, 0);
}

// ── 얼굴 바꾸기 판 ─────────────────────────────────────────────────────
const FACE_ROWS = [["hairc", "머리 색", HAIRC], ["skin", "피부", SKINS], ["eyes", "눈", EYES], ["beard", "수염", BEARDS],
  ["cloth", "옷 색", CLOTHS], ["pants", "바지 색", PANTS]];
let draft = null;
function openFace() {
  if (!S.me) return;
  draft = { ...faceOf(S.me) }; S.panel = "face"; S.keys.clear();
  $("#pz-face").hidden = false; buildFace();
  $("#pz-face-note").textContent = S.role === "operator" ? "운영자는 노비 차림이라 옷 색 대신 무명옷을 입습니다."
    : S.role === "leader" ? "그룹장은 왕관을 씁니다." : S.role === "unit" ? "유닛장은 날개 달린 관모(사모)를 씁니다." : "부서원은 관모를 씁니다.";
}
function closeFace() { $("#pz-face").hidden = true; S.panel = false; draft = null; cv.focus(); }
function buildFace() {
  const grid = $("#pz-hairs"); grid.textContent = "";
  HAIRS.forEach((nm, i) => {               // 머리 모양 — 대가리 고르기
    const b = document.createElement("button"); b.type = "button"; b.className = "hairbtn" + (draft.hair === i ? " on" : "");
    const c = canvas(48, 48), g = c.getContext("2d"); g.imageSmoothingEnabled = false;
    const spr = charSprite({ ...draft, hair: i }, "bare", 0, 0);
    g.drawImage(spr, 0, 0, spr.width, 18 * PX, 0, -2, 48, 18 * PX * 48 / spr.width);
    const l = document.createElement("span"); l.textContent = nm;
    b.append(c, l); b.onclick = () => { draft.hair = i; buildFace(); };
    grid.append(b);
  });
  const rows = $("#pz-facerows"); rows.textContent = "";
  for (const [k, label, list] of FACE_ROWS) {
    const row = document.createElement("div"); row.className = "frow";
    const l = document.createElement("label"); l.textContent = label; row.append(l);
    if (list[0][0] === "#") list.forEach((col, i) => {
      const s = document.createElement("button"); s.type = "button"; s.className = "chip" + (draft[k] === i ? " on" : "");
      s.style.background = col; s.title = label + " " + (i + 1); s.onclick = () => { draft[k] = i; buildFace(); }; row.append(s);
    });
    else {
      const prev = document.createElement("button"), next = document.createElement("button"), v = document.createElement("span");
      prev.type = next.type = "button"; prev.textContent = "◀"; next.textContent = "▶"; v.className = "fval"; v.textContent = list[draft[k]];
      prev.onclick = () => { draft[k] = (draft[k] + list.length - 1) % list.length; buildFace(); };
      next.onclick = () => { draft[k] = (draft[k] + 1) % list.length; buildFace(); };
      row.append(prev, v, next);
    }
    rows.append(row);
  }
}
function drawPreview(now) {
  if (S.panel !== "face" || !draft) return;
  const c = $("#pz-preview"), g = c.getContext("2d"); g.imageSmoothingEnabled = false;
  g.fillStyle = "#c8834a"; g.fillRect(0, 0, c.width, c.height);
  g.fillStyle = "#b9743c"; for (let i = 0; i < 40; i++) g.fillRect((i * 37) % c.width, (i * 53) % c.height, 4, 4);
  const dir = [0, 2, 1, 3][Math.floor(now / 900) % 4], fr = Math.floor(now / 220) % 4;
  const spr = charSprite(draft, S.role, dir, fr === 1 ? 1 : fr === 3 ? 2 : 0), z = 3;
  ell(g, c.width / 2, c.height - 22, 30, 8, "rgba(40,20,5,.3)");
  g.drawImage(spr, Math.round(c.width / 2 - spr.width * z / 2), Math.round(c.height - 22 - (OY + 23) * PX * z), spr.width * z, spr.height * z);
}
async function saveFace() {
  const f = { ...draft };
  try {
    await post("/plaza/api/look", { id: S.id, look: f });
    S.face = S.me.face = f; try { localStorage.setItem("pid.plaza.face", JSON.stringify(f)); } catch (_) { /* 브라우저가 막으면 서버 것만 */ }
    closeFace();
  } catch (e) { $("#pz-face-note").textContent = "저장하지 못했습니다 — " + e.message; }
}
$("#pz-face-btn").onclick = openFace;
$("#pz-face-save").onclick = saveFace;
$("#pz-face-cancel").onclick = closeFace;
$("#pz-face-rand").onclick = () => { for (const k of Object.keys(RANGES)) draft[k] = Math.floor(Math.random() * RANGES[k]); buildFace(); };

// ── 역할 지정 판 (운영자만 — 서버도 운영자만 받는다) ──────────────────────
async function openRoles() {
  S.panel = "roles"; S.keys.clear(); $("#pz-rolep").hidden = false;
  const list = $("#pz-rolelist"); list.textContent = "불러오는 중…";
  try {
    const r = await fetch(`/plaza/api/roles?id=${encodeURIComponent(S.id)}`); if (!r.ok) throw new Error((await r.json()).detail || r.status);
    const data = await r.json(), names = new Map();
    for (const n of data.group_leader) names.set(n, "leader");
    for (const n of data.unit_leaders) if (!names.has(n)) names.set(n, "unit");
    for (const n of data.operators) if (!names.has(n)) names.set(n, "operator");
    for (const p of S.online || []) if (!names.has(p.name)) names.set(p.name, p.role || "member");
    list.textContent = "";
    for (const [n, role] of [...names].sort()) list.append(roleRow(n, role));
  } catch (e) { list.textContent = "읽지 못했습니다 — " + e.message; }
}
function roleRow(name, role) {
  const d = document.createElement("div"); d.className = "rrow";
  const l = document.createElement("span"); l.textContent = name;
  const sel = document.createElement("select");
  for (const [v, t] of [["member", "부서원 (관모)"], ["unit", "유닛장 (사모)"], ["leader", "그룹장 (왕관)"], ["operator", "운영자 (노비)"]]) {
    const o = document.createElement("option"); o.value = v; o.textContent = t; if (v === role) o.selected = true; sel.append(o);
  }
  sel.onchange = () => setRole(name, sel.value);
  d.append(l, sel); return d;
}
async function setRole(name, role) {
  try { await post("/plaza/api/role", { id: S.id, target: name, role }); $("#pz-role-note").textContent = `${name} — 바꿨습니다.`; }
  catch (e) { $("#pz-role-note").textContent = "바꾸지 못했습니다 — " + e.message; }
}
function closeRoles() { $("#pz-rolep").hidden = true; S.panel = false; cv.focus(); }
$("#pz-roles").onclick = openRoles;
$("#pz-role-close").onclick = closeRoles;
$("#pz-role-add").onclick = () => { const n = $("#pz-role-name").value.replace(/\s+/g, " ").trim(); if (n) setRole(n, $("#pz-role-sel").value).then(openRoles); };

// ── 자판 · 대화 ─────────────────────────────────────────────────────────
const input = $("#pz-input"), chatBox = document.querySelector(".pz-chat");
function setTyping(on) { S.typing = on; chatBox.classList.toggle("typing", on); if (on) { S.keys.clear(); input.focus(); } else { input.blur(); cv.focus(); } }
function attack() {                         // 스페이스 — 앞을 휘두른다 (맞은 사람은 서버가 가린다) · 꾹 누르면 0.32초마다 (서버는 0.3초에 한 번)
  const now = performance.now();
  if (!S.me || !S.id || (S.me.attack && now - S.me.attack < ATK_MS + 40)) return;
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
  const arrow = !S.typing && !S.panel ? arrowOf(ev) : null;
  if (arrow) { ev.preventDefault(); S.keys.delete(arrow); S.keys.add(arrow); return; }   // 입력기가 켜져 있어도 걷는다
  if (ev.isComposing || ev.keyCode === 229) return;          // 한글 조합 중
  if (S.panel) { if (ev.key === "Escape") { S.panel === "face" ? closeFace() : closeRoles(); } return; }
  if (ev.key === "Enter") {
    ev.preventDefault();
    if (!S.typing) { setTyping(true); return; }
    const t = input.value; input.value = ""; setTyping(false); say(t); return;
  }
  if (ev.key === "Escape" && S.typing) { input.value = ""; setTyping(false); return; }
  if (S.typing) return;
  if (ev.key === " " || ev.code === "Space" || ev.keyCode === 32) { ev.preventDefault(); S.atkHeld = true; if (!ev.repeat) attack(); return; }   // 꾹 누르면 계속 (frame 에서)
});
document.addEventListener("keyup", ev => { const a = arrowOf(ev); if (a) S.keys.delete(a); if (ev.key === " " || ev.code === "Space" || ev.keyCode === 32) S.atkHeld = false; });
input.addEventListener("focus", () => { S.typing = true; chatBox.classList.add("typing"); S.keys.clear(); });
input.addEventListener("blur", () => { S.typing = false; chatBox.classList.remove("typing"); });
cv.addEventListener("mousedown", () => { if (S.typing) setTyping(false); cv.focus(); });
function focusHint() { $("#pz-focus").hidden = !S.id || S.panel || document.hasFocus(); }
window.addEventListener("focus", focusHint); window.addEventListener("blur", () => { S.keys.clear(); S.atkHeld = false; focusHint(); });
setInterval(focusHint, 1000);

// ── 이름 ───────────────────────────────────────────────────────────────
function storedName() { try { return (localStorage.getItem("pid.author") || "").trim(); } catch (_) { return ""; } }
function start(name) {
  S.name = name.slice(0, 20); S.look = hash(S.name) % 100000;
  $("#pz-me").textContent = S.name + " :";
  // 대시보드 카드 안(embed)에서는 스스로 포커스를 가져가지 않는다 — 가져가면 대시보드의 생일 팝업 · 편집 창 키(Esc · 글쓰기)가 광장으로 감. 한 번 누르면 움직임
  join().then(() => { if (!EMBED) cv.focus(); focusHint(); }).catch(() => { $("#pz-online").textContent = "광장에 들어가지 못했습니다 — 서버를 확인하세요"; });
}
function askName() {
  const box = $("#pz-name"), inp = $("#pz-namein"); box.hidden = false; inp.focus();
  const go = () => { const n = inp.value.replace(/\s+/g, " ").trim(); if (!n) { inp.focus(); return; }
    try { localStorage.setItem("pid.author", n); } catch (_) { /* 저장 못 해도 들어간다 */ }
    box.hidden = true; start(n); };
  $("#pz-nameok").onclick = go;
  inp.addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); e.stopPropagation(); go(); } });
}
window.__plazaDebug = { charSprite, defaultFace, RANGES };
if (EMBED) document.body.classList.add("embed");
resize(); requestAnimationFrame(frame);
const nm = (Q.get("user") || "").trim() || storedName();
if (nm) start(nm); else askName();
})();
