/* 가상 광장 — 부여성 남쪽.  부서원이 캐릭터로 돌아다니며 말풍선으로 대화하고, Space 로 목검을 휘두른다.
 *
 * 그림은 전부 이 파일이 그린다 (그림 파일 0 · 외부 요청 0).  지도와 소품은 처음에 한 번 그려 두고
 * 매 틀마다 붙인다.  사람이 적은 글(이름 · 말)은 canvas 글자와 textContent 로만 그린다.
 * 서버(app/plaza.py)는 칸 좌표 · 말 · 이름 · 외형 번호 · 역할만 들고 있다.
 * 역할(머리 장식)은 서버가 정한다 — 그룹장 왕관 · 유닛장 사모 · 부서원 관모 · 운영자 노비 차림.
 */
(() => {
"use strict";
const T = 32, W = 64, H = 44;               // 칸 크기 · 지도 칸 수 (서버 MAP_W/MAP_H 와 같다)
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

// ── 지도: 조선 마을 (2026-10-19) — 북쪽 관아 · 서쪽 주거 · 가운데 광장 · 동쪽 시장 · 북동 연못 · 남쪽 성문, 둘레는 숲 ─────────
// 땅 종류만 칸마다 정하고(이동 · 충돌은 칸 단위), 그림은 buildWorld 가 한 번 그린다.
const DIRT = 0, LAWN = 1, PAVE = 2, WATER = 3, MOSS = 4;
const ground = new Uint8Array(W * H), solid = new Uint8Array(W * H);
const at = (x, y) => y * W + x;
const inside = (x, y) => x >= 0 && y >= 0 && x < W && y < H;
function fill(t, x0, y0, x1, y1) { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (inside(x, y)) ground[at(x, y)] = t; }
function oval(t, cx, cy, rx, ry) { for (let y = Math.floor(cy - ry); y <= Math.ceil(cy + ry); y++) for (let x = Math.floor(cx - rx); x <= Math.ceil(cx + rx); x++)
  if (inside(x, y) && ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1) ground[at(x, y)] = t; }
function block(x0, y0, x1, y1) { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (inside(x, y)) solid[at(x, y)] = 1; }
function unblock(x0, y0, x1, y1) { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (inside(x, y)) solid[at(x, y)] = 0; }
const props = [];                           // {img, x, y(바닥 px), z(정렬), fade(뒤에 서면 반투명)}

fill(LAWN, 0, 0, W - 1, H - 1);             // 바탕은 풀
// 길 — 관아(북) → 광장 → 성문(남) 큰길, 광장에서 서쪽(주거) · 동쪽(시장)
fill(PAVE, 26, 10, 37, 13);                 // 관아 앞 돌판 마당
fill(DIRT, 29, 13, 34, 16);
oval(DIRT, 31.5, 21.5, 10.5, 7);            // 가운데 광장 (흙)
oval(LAWN, 31.5, 20.6, 2.6, 2);             // 당산나무 둘레 풀
fill(PAVE, 29, 28, 34, 37);                 // 성문 가는 돌길
fill(MOSS, 26, 36, 37, 37);                 // 성문 앞 이끼 낀 돌
fill(DIRT, 3, 20, 22, 23);                  // 서쪽 길
fill(DIRT, 11, 4, 13, 36);                  // 주거 골목 (남북)
fill(DIRT, 3, 12, 10, 14); fill(DIRT, 14, 12, 20, 13);   // 집 앞마당
fill(DIRT, 2, 31, 10, 33); fill(DIRT, 14, 31, 20, 32);
fill(DIRT, 41, 20, 59, 23);                 // 동쪽 길
fill(DIRT, 43, 24, 59, 34);                 // 시장 마당
fill(DIRT, 51, 12, 53, 19);                 // 연못 가는 길
oval(WATER, 47, 8.6, 3.8, 3.6); oval(WATER, 56.6, 8.6, 3.2, 3.4); fill(WATER, 49, 8, 55, 10);   // 연못 두 개 + 잇는 물길
fill(DIRT, 51, 5, 53, 7);                   // 다리 건너 정자 앞
fill(LAWN, 0, 41, W - 1, H - 1);            // 성 밖

block(0, 0, W - 1, 1); block(0, 0, 1, H - 1); block(W - 2, 0, W - 1, H - 1); block(0, 38, W - 1, H - 1);   // 둘레 숲 · 성벽 너머
for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (ground[at(x, y)] === WATER) block(x, y, x, y);
unblock(51, 8, 53, 10);                     // 물길 위 나무다리

// ── 그림 도구 ───────────────────────────────────────────────────────────
function canvas(w, h) { const c = document.createElement("canvas"); c.width = w; c.height = h; return c; }
function shade(hex, k) {                    // k<0 어둡게 · k>0 밝게
  const n = parseInt(hex.slice(1), 16), f = v => Math.max(0, Math.min(255, Math.round(k < 0 ? v * (1 + k) : v + (255 - v) * k)));
  return "#" + [n >> 16 & 255, n >> 8 & 255, n & 255].map(v => f(v).toString(16).padStart(2, "0")).join("");
}
function ell(g, x, y, rx, ry, c) { g.fillStyle = c; g.beginPath(); g.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2); g.fill(); }
// 2026-10-16 (9) 지도 그림도 캐릭터와 같은 굵기로: 소품을 보통 크기로 그린 뒤 pixelize 가 2px 한 점으로 바꾼다
//   반으로 줄여 색을 고름 → 반투명 가장자리 없앰 → 둘레에 짙은 외곽선(옆 색을 어둡게) → 2배.  그림자(c.shadow)는 따로 점으로,
//   글자(c.after)는 다 바꾼 뒤 또렷하게 덧쓴다.  결과는 둘레로 한 점(PX)씩 커진다.
function layers(w, h) { const c = canvas(w, h), s = canvas(w, h); c.shadow = s; return [c, c.getContext("2d"), s.getContext("2d")]; }
function shrink(src, w, h) {
  const s = canvas(w + 2, h + 2), g = s.getContext("2d", { willReadFrequently: true });
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high"; g.drawImage(src, 1, 1, w, h);
  return [s, g, g.getImageData(0, 0, w + 2, h + 2)];
}
function palette(src, n) {                  // 원래 그림에서 가장 많이 쓴 색 n 개 (섞인 중간색을 없애 또렷하게)
  const d = src.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, src.width, src.height).data, cnt = new Map();
  for (let i = 0; i < d.length; i += 4) if (d[i + 3] === 255) { const k = d[i] << 16 | d[i + 1] << 8 | d[i + 2]; cnt.set(k, (cnt.get(k) || 0) + 1); }
  const min = d.length / 4 * .002;               // 아주 조금 쓴 색(가장자리 섞임)은 뺌
  return [...cnt.entries()].filter(([, v]) => v >= min).sort((a, b) => b[1] - a[1]).slice(0, n).map(([k]) => [k >> 16 & 255, k >> 8 & 255, k & 255]);
}
function pixelize(src) {
  const w = Math.ceil(src.width / PX), h = Math.ceil(src.height / PX), sw = w + 2, sh = h + 2;
  const [s, g, img] = shrink(src, w, h), d = img.data, op = new Uint8Array(sw * sh), pal = palette(src, 16);
  for (let i = 0; i < sw * sh; i++) if (d[i * 4 + 3] >= 128) {
    op[i] = 1; d[i * 4 + 3] = 255;
    let best = null, bd = 1e9;
    for (const p of pal) { const e = (p[0] - d[i * 4]) ** 2 * 2 + (p[1] - d[i * 4 + 1]) ** 2 * 4 + (p[2] - d[i * 4 + 2]) ** 2 * 3; if (e < bd) { bd = e; best = p; } }
    if (best) { d[i * 4] = best[0]; d[i * 4 + 1] = best[1]; d[i * 4 + 2] = best[2]; }
  } else d[i * 4 + 3] = 0;
  for (let y = 0; y < sh; y++) for (let x = 0; x < sw; x++) {
    const i = y * sw + x; if (op[i]) continue;
    const n = [[1, 0], [-1, 0], [0, 1], [0, -1]].map(([dx, dy]) => { const xx = x + dx, yy = y + dy; return xx >= 0 && yy >= 0 && xx < sw && yy < sh && op[yy * sw + xx] ? yy * sw + xx : -1; }).find(j => j >= 0);
    if (n == null) continue;
    d[i * 4] = d[n * 4] * .3 + 8; d[i * 4 + 1] = d[n * 4 + 1] * .28 + 5; d[i * 4 + 2] = d[n * 4 + 2] * .26 + 4; d[i * 4 + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  const out = canvas(sw * PX, sh * PX), og = out.getContext("2d"); og.imageSmoothingEnabled = false;
  if (src.shadow) {                          // 그림자 — 점으로 · 반투명 그대로
    const [ss, sg2, si] = shrink(src.shadow, w, h), sd = si.data;
    for (let i = 0; i < sw * sh; i++) { const on = sd[i * 4 + 3] >= 30; sd[i * 4] = 30; sd[i * 4 + 1] = 20; sd[i * 4 + 2] = 10; sd[i * 4 + 3] = on ? 70 : 0; }
    sg2.putImageData(si, 0, 0); og.drawImage(ss, 0, 0, out.width, out.height);
  }
  og.drawImage(s, 0, 0, out.width, out.height);
  if (src.after) { og.save(); og.translate(PX, PX); src.after(og); og.restore(); }
  return out;
}

// ── 마을 그림 (2026-10-19) ───────────────────────────────────────────────
// 캐릭터: 사용자가 준 '마을' 시트에서 뽑은 static/village_chars.png
// 배경: 사용자가 준 '조선 마을 타일셋'에서 뽑은 static/joseon.png — 덩어리(배경으로 떨어진 그림)마다 그 덩어리의 픽셀만 썼고
//       땅 타일은 덩어리 안쪽만 (경계 추측 없음).  배경 투명 · 그림 한 칸 = 원래 도트 한 점 · 화면엔 PX 배 (흐리지 않게)
// 기준점: [x, y, w, h, 가운데 x, 발바닥 y] — 그림 안 점 단위
const CHR_FR = {"cat_d0":[0,0,22,30,10.7,29],"cat_d1":[23,0,21,29,9.8,28],"cat_d2":[45,0,22,29,10.3,27],"cat_d3":[68,0,21,29,9.5,28],"cat_s0":[90,0,22,29,10.3,28],"cat_s1":[113,0,20,29,9.9,27],"cat_a":[134,0,37,28,13.9,26],"panda_d0":[172,0,19,30,8.7,29],"panda_d1":[192,0,20,29,9.4,28],"panda_s0":[213,0,21,28,10.4,27],"panda_s1":[235,0,20,29,9.8,28],"panda_a":[256,0,30,30,11.3,29],"lion_d0":[287,0,23,30,10.9,29],"lion_d1":[311,0,22,30,10.8,28],"lion_d2":[334,0,22,30,10.0,29],"lion_d3":[357,0,20,29,9.2,28],"lion_s0":[378,0,22,30,10.3,29],"lion_s1":[401,0,22,28,10.5,27],"lion_a":[424,0,46,33,16.9,32],"tiger_d0":[471,0,22,28,10.3,27],"tiger_d1":[0,34,20,28,9.0,27],"tiger_a":[21,34,48,29,25.6,28],"nobi_d0":[70,34,20,26,8.5,24],"nobi_d1":[91,34,19,28,9.2,27],"nobi_s0":[111,34,21,26,10.0,24],"nobi_s1":[133,34,20,26,8.9,25],"nobi_s2":[154,34,20,26,9.1,24],"nobi_s3":[175,34,18,26,8.0,24],"p_cat":[194,34,64,90,33.4,89],"p_panda":[259,34,58,88,28.9,86],"p_lion":[318,34,66,91,32.4,90],"p_tiger":[385,34,63,88,30.5,87],"p_nobi":[449,34,57,72,27.3,71]};
const JOS_FR = {"dirt":[574,91,40,40,20.0,40],"dirt2":[958,91,36,32,18.0,32],"grass":[615,91,36,40,18.0,40],"grass2":[51,143,36,30,18.0,30],"grass3":[652,91,38,40,19.0,40],"pave":[691,91,40,40,20.0,40],"moss":[732,91,38,38,19.0,38],"water":[482,176,28,13,14.0,13],"bush1":[23,143,27,31,13.5,31],"bush2":[879,91,30,34,15.0,34],"bush3":[910,91,30,34,15.0,34],"patch1":[657,143,30,22,15.0,22],"patch2":[885,143,22,21,11.0,21],"patch3":[294,176,22,18,11.0,18],"bushR":[908,143,23,21,11.5,21],"flowY":[999,143,23,20,11.5,20],"flowW":[932,143,27,21,13.5,21],"flowP":[0,176,24,20,12.0,20],"flowP2":[25,176,22,20,11.0,20],"sap1":[454,143,20,24,10.0,24],"sap2":[638,143,18,23,9.0,23],"sap3":[688,143,18,22,9.0,22],"sap4":[48,176,17,20,8.5,20],"clump":[66,176,28,20,14.0,20],"cherry1":[580,0,44,58,22.0,58],"cherry2":[183,91,37,47,18.5,47],"cherry3":[707,143,16,22,8.0,22],"cherry4":[822,0,42,53,21.0,53],"pine":[724,0,31,56,15.5,56],"tree1":[625,0,42,58,21.0,58],"bigtree":[668,0,55,58,27.5,58],"tree2":[349,91,36,44,18.0,44],"lantern":[278,143,14,26,7.0,26],"fenceP":[138,143,34,29,17.0,29],"rocks1":[95,176,28,20,14.0,20],"rocks2":[124,176,24,20,12.0,20],"treeS1":[225,143,22,27,11.0,27],"treeS2":[293,143,18,26,9.0,26],"treeS3":[149,176,18,20,9.0,20],"pinkbush":[511,176,16,13,8.0,13],"stump":[435,176,18,14,9.0,14],"tuft1":[545,176,14,11,7.0,11],"tuft2":[454,176,14,14,7.0,14],"tuft3":[528,176,16,12,8.0,12],"fl1":[415,176,19,15,9.5,15],"fl2":[383,176,13,16,6.5,16],"fl3":[397,176,17,16,8.5,16],"well":[832,91,36,36,18.0,36],"post":[869,91,9,36,4.5,36],"lanternW":[475,143,12,24,6.0,24],"stall1":[474,91,46,42,23.0,42],"potstall":[88,143,22,30,11.0,30],"stall2":[111,143,26,30,13.0,30],"banner1":[995,91,13,32,6.5,32],"barrel":[168,176,14,20,7.0,20],"fence1":[407,143,46,25,23.0,25],"fence2":[312,143,38,26,19.0,26],"swall1":[183,176,58,20,29.0,20],"bucket":[469,176,12,14,6.0,14],"bushtree":[192,143,32,28,16.0,28],"shelf":[0,143,22,32,11.0,32],"barrels":[269,176,24,19,12.0,19],"table":[724,143,36,22,18.0,22],"vegstall":[248,143,29,27,14.5,27],"rack":[173,143,18,29,9.0,29],"swall2":[960,143,20,21,10.0,21],"swall3":[242,176,26,20,13.0,20],"swall4":[761,143,38,22,19.0,22],"swall5":[800,143,41,22,20.5,22],"cart":[488,143,28,24,14.0,24],"tub":[981,143,17,21,8.5,21],"crates":[842,143,28,22,14.0,22],"bannerR":[351,143,16,26,8.0,26],"bannerB":[941,91,16,33,8.0,33],"house1":[350,0,108,68,54.0,68],"house2":[459,0,59,68,29.5,68],"house3":[265,0,84,69,42.0,69],"house4":[880,0,86,52,43.0,52],"house5":[0,91,40,51,20.0,51],"pole":[865,0,14,53,7.0,53],"bannerW":[386,91,14,44,7.0,44],"pondbr":[0,0,74,90,37.0,90],"rockbush":[517,143,45,24,22.5,24],"pine2":[204,0,60,73,30.0,73],"barrel2":[366,176,16,17,8.0,17],"rockwater":[221,91,34,46,17.0,46],"stall3":[521,91,52,41,26.0,41],"lantern2":[563,143,12,24,6.0,24],"lanternR":[871,143,13,22,6.5,22],"steps":[771,91,60,38,30.0,38],"hall":[75,0,128,82,64.0,82],"bannerP":[756,0,18,56,9.0,56],"wallroof":[41,91,106,50,53.0,50],"wallseg":[148,91,34,50,17.0,50],"bannerP2":[775,0,16,54,8.0,54],"bridge":[256,91,92,46,46.0,46],"stream":[519,0,60,68,30.0,68],"tree3":[967,0,32,52,16.0,52],"bamboo":[317,176,48,18,24.0,18],"jars":[576,143,61,24,30.5,24],"bushrock":[368,143,38,26,19.0,26],"wallpill":[792,0,29,54,14.5,54],"gatewall":[401,91,72,44,36.0,44]};
const JOS = { data: null, ready: false }, CHR = { data: null, ready: false };
function loadAtlas(o, src) {
  return new Promise(res => {
    const im = new Image();
    im.onload = () => { const c = canvas(im.width, im.height), g = c.getContext("2d", { willReadFrequently: true }); g.drawImage(im, 0, 0);
      o.data = g.getImageData(0, 0, im.width, im.height); o.ready = true; res(); };
    im.onerror = () => res();                 // 못 받으면 그림 없이 땅 색만
    im.src = src;
  });
}
function atlasSprite(A, FR, name, mirror, scale = PX) {   // 한 칸 → scale 배 (뒤집기) · canvas.cx · canvas.foot (px)
  const key = `${A === JOS ? "j" : "c"}|${name}|${mirror ? 1 : 0}|${scale}`; if (spriteCache.has(key)) return spriteCache.get(key);
  const [fx, fy, fw, fh, cx, foot] = FR[name], src = A.data, small = new ImageData(fw, fh);
  for (let y = 0; y < fh; y++) for (let x = 0; x < fw; x++) {
    const si = ((fy + y) * src.width + fx + x) * 4; if (src.data[si + 3] < 128) continue;
    const di = (y * fw + (mirror ? fw - 1 - x : x)) * 4;
    small.data[di] = src.data[si]; small.data[di + 1] = src.data[si + 1]; small.data[di + 2] = src.data[si + 2]; small.data[di + 3] = 255;
  }
  const s1 = canvas(fw, fh); s1.getContext("2d").putImageData(small, 0, 0);
  const c = canvas(fw * scale, fh * scale), g = c.getContext("2d"); g.imageSmoothingEnabled = false; g.drawImage(s1, 0, 0, c.width, c.height);
  c.cx = (mirror ? fw - cx : cx) * scale; c.foot = foot * scale;
  spriteCache.set(key, c); return c;
}
const js = (name, mirror) => atlasSprite(JOS, JOS_FR, name, mirror);

// 값 잡음 (부드러운 난수 면) — 땅 경계를 일렁이게 · 풀 무늬를 섞는 데 씀
function vnoise(x, y, seed) {
  const xi = Math.floor(x), yi = Math.floor(y), fx = x - xi, fy = y - yi, sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
  const v = (a, b) => (hash(`${a},${b},${seed}`) & 1023) / 1023;
  return (v(xi, yi) * (1 - sx) + v(xi + 1, yi) * sx) * (1 - sy) + (v(xi, yi + 1) * (1 - sx) + v(xi + 1, yi + 1) * sx) * sy;
}

// ── 땅 (한 번 그린다 — 점 해상도로 칠한 뒤 PX 배) ─────────────────────────
const groundImg = canvas(W * T, H * T);
function drawGround() {
  const g = groundImg.getContext("2d"), TP = T / PX, AW = W * TP, AH = H * TP;   // TP = 한 칸의 점 수 (16)
  const img = new ImageData(AW, AH), D = img.data, tmap = new Uint8Array(AW * AH);
  const tile = (ax, ay) => { const x = Math.min(W - 1, Math.max(0, Math.floor(ax / TP))), y = Math.min(H - 1, Math.max(0, Math.floor(ay / TP))); return ground[at(x, y)]; };
  // 1) 점마다 땅 종류 — 흙 · 풀 · 물 경계는 잡음으로 일렁이게 (돌판은 반듯하게)
  for (let y = 0; y < AH; y++) for (let x = 0; x < AW; x++) {
    let t = tile(x, y);
    if (t !== PAVE && t !== MOSS) {
      const jx = (vnoise(x / 7, y / 7, 1) - .5) * 11, jy = (vnoise(x / 7, y / 7, 2) - .5) * 11, t2 = tile(x + jx, y + jy);
      if (t2 !== PAVE && t2 !== MOSS) t = t2;
    }
    tmap[y * AW + x] = t;
  }
  // 2) 색 — 시트 타일을 거울처럼 뒤집어 이어 깜 (이음매 없음) · 풀은 세 가지를 잡음으로 섞어 넓은 단색 · 되풀이 무늬를 줄임
  const TX = {}, tex = n => TX[n] || (TX[n] = JOS_FR[n]);
  const refl = (u, n) => { const p = ((u % (2 * n)) + 2 * n) % (2 * n); return p < n ? p : 2 * n - 1 - p; };
  const pick = (t, x, y) => {
    if (t === LAWN) { const v = vnoise(x / 46, y / 46, 3); return v < .62 ? "grass" : v < .82 ? "grass2" : "grass3"; }
    if (t === DIRT) return vnoise(x / 38, y / 38, 4) < .55 ? "dirt" : "dirt2";
    return t === PAVE ? "pave" : t === MOSS ? "moss" : "water";
  };
  // 칸(16점)마다 타일의 다른 자리를 떼어 쓰고 뒤집기도 칸마다 달리 — 같은 무늬가 규칙적으로 되풀이되지 않음 (점은 늘이지 않아 선명)
  // 물은 시트 연못의 밝은 청록 4 색을 잡음으로 섞고 가끔 물결
  const A = JOS.data, WC = [[52, 138, 176], [62, 152, 188], [44, 122, 162], [98, 180, 208]];
  for (let y = 0; y < AH; y++) for (let x = 0; x < AW; x++) {
    const t = tmap[y * AW + x], di = (y * AW + x) * 4;
    if (t === WATER) {
      const v = vnoise(x / 4, y / 3, 9), c = WC[v < .45 ? 0 : v < .75 ? 1 : v < .93 ? 2 : 3];
      const wave = Math.sin(x / 4 + vnoise(x / 24, y / 24, 8) * 10) > .9 && (hash(`w${x >> 3},${y}`) % 9 === 0);
      D[di] = wave ? 196 : c[0]; D[di + 1] = wave ? 232 : c[1]; D[di + 2] = wave ? 240 : c[2]; D[di + 3] = 255; continue;
    }
    const [fx, fy, fw, fh] = tex(pick(t, x, y)), cx = Math.floor(x / TP), cy = Math.floor(y / TP), hc = hash(`c${cx},${cy},${t}`);
    const ou = hc % (fw - TP + 1), ov = (hc >>> 8) % (fh - TP + 1), ru = x - cx * TP, rv = y - cy * TP;   // 이 칸이 쓸 타일 조각 (16×16) 의 자리
    const u = ou + (hc & 0x10000 ? TP - 1 - ru : ru), w = ov + (hc & 0x20000 ? TP - 1 - rv : rv);       // 좌우 · 위아래 뒤집기
    const si = ((fy + Math.max(0, Math.min(fh - 1, w))) * A.width + fx + Math.max(0, Math.min(fw - 1, u))) * 4;
    D[di] = A.data[si]; D[di + 1] = A.data[si + 1]; D[di + 2] = A.data[si + 2]; D[di + 3] = 255;
  }
  // 3) 경계 그늘 · 물가 — 풀이 흙 · 돌을 만나는 곳은 풀 끝을 어둡게, 물가는 돌 · 짙은 물
  const tAt = (x, y) => x < 0 || y < 0 || x >= AW || y >= AH ? LAWN : tmap[y * AW + x];
  const mul = (di, k) => { D[di] *= k; D[di + 1] *= k; D[di + 2] *= k; };
  for (let y = 0; y < AH; y++) for (let x = 0; x < AW; x++) {
    const t = tmap[y * AW + x], di = (y * AW + x) * 4;
    if (t === LAWN && (tAt(x, y + 1) !== LAWN || tAt(x + 1, y) !== LAWN || tAt(x - 1, y) !== LAWN || tAt(x, y - 1) !== LAWN) && tAt(x, y + 1) !== WATER) mul(di, .72);
    else if (t === DIRT && (tAt(x, y - 1) === LAWN || tAt(x, y - 2) === LAWN)) mul(di, .88);     // 풀 아래 흙에 그늘
    else if (t === WATER) {
      let near = 9; for (let r = 1; r <= 2 && near > 8; r++) if (tAt(x - r, y) !== WATER || tAt(x + r, y) !== WATER || tAt(x, y - r) !== WATER || tAt(x, y + r) !== WATER) near = r;
      if (near === 1) { const v = hash(`s${x >> 1},${y >> 1}`) % 3; D[di] = [138, 132, 118][v]; D[di + 1] = [136, 128, 112][v]; D[di + 2] = [126, 118, 104][v]; }   // 물가 돌
      else if (near === 2) mul(di, .7);
    }
  }
  g.imageSmoothingEnabled = false;
  const s1 = canvas(AW, AH); s1.getContext("2d").putImageData(img, 0, 0); g.drawImage(s1, 0, 0, W * T, H * T);
  // 4) 흩뿌림 — 풀포기 · 작은 꽃 · 흙자국 · 연잎 (밟고 지나가는 땅 그림)
  const r = rng(21), grassOK = (x, y) => inside(x, y) && ground[at(x, y)] === LAWN && !solid[at(x, y)];
  for (let i = 0; i < 520; i++) {
    const x = Math.floor(r() * W), y = Math.floor(r() * H), v = r();
    if (!grassOK(x, y)) continue;
    const n = v < .35 ? ["tuft1", "tuft2", "tuft3"][i % 3] : v < .62 ? ["fl1", "fl2", "fl3"][i % 3] : v < .7 ? ["patch1", "patch2", "patch3"][i % 3] : v < .86 ? ["flowY", "flowW", "flowP", "flowP2"][i % 4] : "clump";
    const s = js(n, i & 1); g.drawImage(s, Math.round(x * T + r() * 12 - s.width / 2 + 16), Math.round(y * T + 28 - s.height + r() * 6));
  }
  for (let i = 0; i < 900; i++) {            // 흙 · 돌판 위 자갈 (1~2 점)
    const x = Math.floor(r() * W), y = Math.floor(r() * H), t = inside(x, y) && ground[at(x, y)];
    if (t !== DIRT && t !== PAVE) continue;
    const X = x * T + Math.floor(r() * 15) * 2, Y = y * T + Math.floor(r() * 15) * 2, v = r();
    g.fillStyle = v < .5 ? "#9c8466" : v < .8 ? "#c9b08a" : "#7d6a52"; g.fillRect(X, Y, 2 + (v < .3 ? 2 : 0), 2); g.fillStyle = "rgba(60,40,20,.35)"; g.fillRect(X, Y + 2, 2, 2);
  }
  for (let i = 0; i < 160; i++) {            // 흙길 가장자리 풀포기
    const x = Math.floor(r() * W), y = Math.floor(r() * H);
    if (!inside(x, y) || ground[at(x, y)] !== DIRT || ![[0, 1], [0, -1], [1, 0], [-1, 0]].some(([a, b]) => inside(x + a, y + b) && ground[at(x + a, y + b)] === LAWN)) continue;
    const s2 = js(["tuft1", "tuft2", "tuft3"][i % 3], i & 1); g.drawImage(s2, Math.round(x * T + r() * 16), Math.round(y * T + r() * 12));
  }
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (ground[at(x, y)] === WATER && hash(`l${x},${y}`) % 4 === 0) {   // 연잎
    const X = x * T + 6 + hash(`a${x},${y}`) % 14, Y = y * T + 6 + hash(`b${x},${y}`) % 14;
    g.fillStyle = "#1f3a1c"; g.fillRect(X - 2, Y - 2, 14, 10); g.fillStyle = "#4f8a34"; g.fillRect(X, Y, 10, 6); g.fillStyle = "#79b04a"; g.fillRect(X + 2, Y, 4, 2);
    if (hash(`f${x},${y}`) % 3 === 0) { g.fillStyle = "#f2a2c0"; g.fillRect(X + 6, Y - 2, 4, 4); g.fillStyle = "#fff0f6"; g.fillRect(X + 6, Y - 2, 2, 2); }
  }
}
function drawGroundPlain() {                // 그림 파일을 못 받았을 때 — 땅 색만
  const g = groundImg.getContext("2d"), C = { [DIRT]: "#c8a060", [LAWN]: "#6f9a3c", [PAVE]: "#b8ad94", [WATER]: "#3d7393", [MOSS]: "#7e8460" };
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { g.fillStyle = C[ground[at(x, y)]]; g.fillRect(x * T, y * T, T, T); }
}

// ── 장독대 — 시트에 없어 같은 화풍(2px 점 · 짙은 외곽선 · 3단 음영)으로 그림 ─────────────────
function jangdokImg() {
  const w = 34, h = 22, c = canvas(w, h), g = c.getContext("2d");
  const px = (x, y, ww, hh, col) => { g.fillStyle = col; g.fillRect(x, y, ww, hh); };
  px(1, 14, 32, 7, "#8d8778"); px(1, 14, 32, 1, "#b3ad9c"); px(1, 20, 32, 1, "#5f5a4e");          // 돌 단
  for (let x = 3; x < 32; x += 6) px(x, 16, 1, 3, "#6e695c");
  const jar = (x, y, r, hh) => {                // 옹기 — 몸통 · 빛 · 뚜껑
    for (let j = 0; j < hh; j++) { const k = Math.round(r * Math.sin(Math.PI * (j + .5) / hh) + 1); px(x - k, y + j, k * 2, 1, j < hh * .35 ? "#7a4a2a" : "#5a3420"); }
    px(x - 2, y + 1, 1, Math.max(1, hh - 4), "#a8703e"); px(x - r + 1, y - 2, (r - 1) * 2, 2, "#3e2416"); px(x - 1, y - 3, 2, 1, "#5a3420");
  };
  jar(7, 7, 4, 9); jar(16, 4, 5, 11); jar(26, 7, 4, 9); jar(11, 10, 3, 6); jar(22, 10, 3, 6);
  const d = g.getImageData(0, 0, w, h), o = new Uint8ClampedArray(d.data);   // 외곽선
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const i = (y * w + x) * 4; if (d.data[i + 3]) continue;
    if ([[1, 0], [-1, 0], [0, 1], [0, -1]].some(([a, b]) => { const xx = x + a, yy = y + b; return xx >= 0 && yy >= 0 && xx < w && yy < h && d.data[(yy * w + xx) * 4 + 3]; })) { o[i] = 27; o[i + 1] = 18; o[i + 2] = 14; o[i + 3] = 255; } }
  g.putImageData(new ImageData(o, w, h), 0, 0);
  const big = canvas(w * PX, h * PX), bg = big.getContext("2d"); bg.imageSmoothingEnabled = false; bg.drawImage(c, 0, 0, big.width, big.height);
  return big;
}

// ── 소품 놓기 — buildWorld 가 그림을 받은 뒤 한 번에 만든다 ───────────────────────────────
// put(그림, 왼쪽 칸, 바닥 칸, { fw: 차지 폭(칸), solid: 막는 칸 [x0,y0,x1,y1], fade: 뒤에 서면 반투명, flat: 땅처럼 밑에 그림, mirror })
const PLACES = [];
function put(name, tx, ty, opts = {}) { PLACES.push({ name, tx, ty, opts }); if (opts.solid) block(...opts.solid); }
// 건물 — 지붕은 막지 않음(뒤로 지나가면 지붕에 가려지고 반투명해짐), 아래 벽 · 기단만 막음
function bld(name, tx, ty, fw, rows, mirror) { put(name, tx, ty, { fw, fade: true, mirror, solid: [tx, ty - rows + 1, tx + fw - 1, ty] }); }
// 북쪽 관아
bld("house1", 28, 9, 7, 3);
put("lantern", 27, 12, { solid: [27, 12, 27, 12] }); put("lantern", 36, 12, { solid: [36, 12, 36, 12] });
put("bannerP", 26, 10, { solid: [26, 10, 26, 10] }); put("bannerP2", 37, 10, { solid: [37, 10, 37, 10] });
// 가운데 광장 — 당산나무 · 석등 넷 · 우물 · 장승
put("bigtree", 31, 21, { fw: 2, solid: [31, 20, 32, 21] });
for (const [x, y] of [[24, 17], [39, 17], [24, 26], [39, 26]]) put(y < 20 ? "lantern2" : "lanternR", x, y, { solid: [x, y, x, y] });
put("well", 36, 18, { fw: 2, solid: [36, 17, 37, 18] });
put("@jang1", 27, 33, { solid: [27, 33, 27, 33] }); put("@jang2", 36, 33, { solid: [36, 33, 36, 33] });
// 서쪽 주거 — 한옥 넷 · 돌담 · 울타리 · 장독대 · 우물
bld("house3", 4, 11, 6, 3); bld("house2", 15, 11, 4, 3);
bld("house4", 3, 30, 6, 2); bld("house5", 16, 30, 3, 2);
put("@jang", 8, 16, { fw: 2, solid: [8, 16, 9, 16] }); put("@jang", 4, 35, { fw: 2, solid: [4, 35, 5, 35] }); put("@jang", 19, 15, { fw: 2, solid: [19, 15, 20, 15] });
put("swall1", 3, 17, { fw: 4, solid: [3, 17, 6, 17] }); put("swall4", 14, 17, { fw: 3, solid: [14, 17, 16, 17] }); put("swall3", 18, 17, { fw: 2, solid: [18, 17, 19, 17] });
put("swall2", 2, 26, { fw: 2, solid: [2, 26, 3, 26] }); put("swall5", 5, 26, { fw: 3, solid: [5, 26, 7, 26] }); put("swall1", 15, 26, { fw: 4, solid: [15, 26, 18, 26] });
put("fence1", 7, 35, { fw: 3, solid: [7, 35, 9, 35] }); put("fence2", 15, 35, { fw: 3, solid: [15, 35, 17, 35] });
put("tub", 9, 33, { solid: [9, 33, 9, 33] }); put("bucket", 19, 32, {}); put("barrel2", 20, 31, { solid: [20, 31, 20, 31] });
put("cart", 15, 24, { fw: 2, solid: [15, 24, 16, 24] }); put("post", 10, 15, { solid: [10, 15, 10, 15] });
// 동쪽 시장 — 좌판 두 줄 (가운데 줄은 비워 걸어 다님) · 수레 · 통 · 깃발
put("stall1", 44, 27, { fw: 3, fade: true, solid: [44, 26, 46, 27] }); put("stall2", 48, 27, { fw: 2, solid: [48, 26, 49, 27] });
put("stall3", 51, 27, { fw: 3, fade: true, solid: [51, 26, 53, 27] }); put("vegstall", 55, 27, { fw: 2, solid: [55, 26, 56, 27] }); put("potstall", 58, 27, { solid: [58, 26, 58, 27] });
put("table", 44, 32, { fw: 3, solid: [44, 31, 46, 32] }); put("shelf", 48, 32, { solid: [48, 31, 48, 32] }); put("jars", 51, 32, { fw: 4, solid: [51, 32, 54, 32] });
put("cart", 56, 32, { fw: 2, solid: [56, 32, 57, 32] }); put("barrels", 58, 32, { solid: [58, 32, 58, 32] });
put("bannerR", 43, 24, { solid: [43, 24, 43, 24] }); put("bannerB", 59, 24, { solid: [59, 24, 59, 24] }); put("rack", 59, 30, { solid: [59, 30, 59, 30] });
put("crates", 47, 34, { fw: 2, solid: [47, 34, 48, 34] }); put("barrel", 50, 34, { solid: [50, 34, 50, 34] }); put("stall2", 54, 34, { fw: 2, mirror: true, solid: [54, 33, 55, 34] });
// 북동 연못 — 나무다리 · 정자 · 바위 · 대나무 울타리
put("bridge", 50, 11, { fw: 5, flat: true });                 // 다리는 땅처럼 (위로 걸어감)
bld("house5", 51, 5, 3, 2, true);
for (const [n, x, y] of [["rocks1", 43, 12], ["rocks2", 45, 13], ["rockbush", 58, 13], ["bushrock", 54, 13], ["rocks1", 59, 5], ["rocks2", 42, 6]]) put(n, x, y, { fw: 2, solid: [x, y, x + 1, y] });
put("bamboo", 44, 3, { fw: 3, solid: [44, 3, 46, 3] }); put("lanternW", 50, 13, { solid: [50, 13, 50, 13] }); put("lanternW", 54, 12, { solid: [54, 12, 54, 12] });
// 남쪽 성문 — 기와 담장 · 문루(붉은 대문 · 깃발) · 석등
for (const x of [0, 6, 12, 18, 22]) put("wallroof", x, 40, { fw: 6, fade: true });
for (const x of [36, 42, 48, 54, 58]) put("wallroof", x, 40, { fw: 6, fade: true });
put("hall", 28, 40, { fw: 8, fade: true, solid: [28, 35, 35, 40] });   // 문루 지붕 앞에서 멈춤
put("lantern", 27, 36, { solid: [27, 36, 27, 36] }); put("lantern", 36, 36, { solid: [36, 36, 36, 36] });

const TREES = ["tree1", "tree2", "tree3", "pine", "pine2", "cherry1", "cherry2", "bushtree", "treeS1", "treeS2"];
function scatter() {                        // 둘레 숲 + 풀밭 나무 · 덤불 · 꽃 (길 · 건물 · 이미 막힌 칸은 피함)
  const r = rng(77);
  const near = (x, y, k) => { for (let yy = y - k; yy <= y + k; yy++) for (let xx = x - k; xx <= x + k; xx++) if (inside(xx, yy) && (ground[at(xx, yy)] !== LAWN || solid[at(xx, yy)])) return true; return false; };
  const edge = (x, y) => x <= 1 || y <= 1 || x >= W - 2 || y >= 41;
  for (let y = 0; y < H; y += 2) for (let x = 0; x < W; x += 2) {      // 둘레 숲 (막힌 칸 위)
    const jx = x + (hash(`tx${x},${y}`) % 2), jy = y + (hash(`ty${x},${y}`) % 2);
    if (!edge(jx, jy) || (jy >= 38 && jy <= 40)) continue;
    const n = TREES[hash(`t${x},${y}`) % TREES.length]; PLACES.push({ name: n, tx: jx, ty: jy, opts: { mirror: (x + y) & 2 } });
  }
  for (let i = 0; i < 900; i++) {                                      // 안쪽 풀밭
    const x = 2 + Math.floor(r() * (W - 4)), y = 2 + Math.floor(r() * 35), v = r();
    if (ground[at(x, y)] !== LAWN || solid[at(x, y)]) continue;
    if (v < .5) { if (near(x, y, 1)) continue; const n = TREES[Math.floor(r() * TREES.length)]; block(x, y, x, y); PLACES.push({ name: n, tx: x, ty: y, opts: { mirror: i & 1 } }); }
    else if (v < .8) { if (near(x, y, 0)) continue; PLACES.push({ name: ["bush1", "bush2", "bush3", "bushR", "pinkbush", "sap1", "sap2", "sap3", "sap4"][i % 9], tx: x, ty: y, opts: { mirror: i & 1 } }); block(x, y, x, y); }
    else PLACES.push({ name: ["flowY", "flowW", "flowP", "flowP2", "clump"][i % 5], tx: x, ty: y, opts: { flat: true, mirror: i & 1 } });
  }
  for (const [x, y] of [[44, 15], [41, 4], [57, 15], [22, 15], [6, 18], [20, 27], [41, 36], [57, 36]]) if (!solid[at(x, y)] && ground[at(x, y)] === LAWN) {
    block(x, y, x, y); PLACES.push({ name: ["cherry1", "cherry2", "cherry4"][x % 3], tx: x, ty: y, opts: {} }); }   // 눈에 띄는 자리 벚꽃
}
const WORLD = { ready: false, built: false };
WORLD.promise = new Promise(res => { WORLD.done = res; });
function buildWorld() {                     // 나무 흩기 → 땅 → 소품 그림 (한 번만)
  if (WORLD.built) return; WORLD.built = true;
  scatter();
  if (JOS.ready) {
    drawGround();
    const special = { "@jang": jangdokImg, "@jang1": () => jangseungImg(true), "@jang2": () => jangseungImg(false) };
    for (const p of PLACES) {
      const img = special[p.name] ? special[p.name]() : JOS_FR[p.name] ? js(p.name, p.opts.mirror) : null; if (!img) continue;
      const fw = p.opts.fw || 1, y = (p.ty + 1) * T - (p.opts.flat ? 0 : 2);
      props.push({ img, x: Math.round(p.tx * T + fw * T / 2 - img.width / 2), y, z: p.opts.flat ? y - 3 * T : y, fade: !!p.opts.fade });
    }
  } else drawGroundPlain();
  WORLD.ready = true; WORLD.done();
}
Promise.all([loadAtlas(JOS, "/static/joseon.png"), loadAtlas(CHR, "/static/village_chars.png")]).then(buildWorld);
setTimeout(buildWorld, 8000);               // 그림이 끝내 안 오면 땅 색만으로
function jangseungImg(top) {
  const [c, g, sg] = layers(28, 84);
  ell(sg, 14, 78, 10, 3, "#000");
  g.fillStyle = "#9b6a3f"; g.fillRect(6, 10, 16, 68); g.fillStyle = "#7d522d"; g.fillRect(6, 10, 3, 68);
  g.fillStyle = "#1e1e1e"; g.fillRect(4, 4, 20, 8); g.fillRect(9, 0, 10, 6);
  g.fillStyle = "#f2efe6"; g.fillRect(9, 16, 4, 3); g.fillRect(15, 16, 4, 3);
  g.fillStyle = "#111"; g.fillRect(10, 17, 2, 2); g.fillRect(16, 17, 2, 2);
  g.fillStyle = "#b8332d"; g.fillRect(12, 22, 4, 6); g.fillStyle = "#f2efe6"; g.fillRect(9, 30, 10, 3);
  c.after = a => { a.fillStyle = "#111"; a.font = "bold 9px serif"; a.textAlign = "center";
    [...(top ? "天下大將軍" : "地下女將軍")].forEach((ch, i) => a.fillText(ch, 14, 44 + i * 8)); };
  return pixelize(c);
}

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
// 2026-10-19 고양이 기사 — 종류 · 동물(털) · 갑옷 · 망토 (서버 LOOK_EXTRA 와 같은 개수)
const KINDS = ["고양이 기사", "사람", "고양이 양반", "팬더 학자", "사자 무관", "호랑이 무관", "노비"];   // 2~6 = 마을 시트 캐릭터 (노비는 운영자만)
const FURS = ["치즈 고양이", "회색 고양이", "검은 고양이", "흰 고양이", "호랑이", "여우"];
const ARMORS = ["은빛 갑옷", "황금 갑옷", "흑철 갑옷", "청동 갑옷", "푸른 강철", "백은 갑옷"];
const CAPES = ["빨간 망토", "파란 망토", "초록 망토", "보라 망토", "검은 망토", "흰 망토", "노란 망토"];
const RANGES = { hair: HAIRS.length, hairc: HAIRC.length, skin: SKINS.length, eyes: EYES.length, beard: BEARDS.length,
  cloth: CLOTHS.length, pants: PANTS.length, kind: KINDS.length, fur: FURS.length, armor: ARMORS.length, cape: CAPES.length };
const ROLE_LABEL = { leader: "그룹장", unit: "유닛장", operator: "운영자", member: "" };
const ROLE_COLOR = { leader: "#ffd84a", unit: "#ffb36b", operator: "#d8c59a" };
function defaultFace(name) {                // 처음 들어온 사람 — 이름에서 정한 외형
  const n = hash(name);
  return { hair: n % 10, hairc: (n >>> 4) % 3, skin: (n >>> 7) % 3, eyes: (n >>> 9) % 3, beard: 0,
    cloth: (n >>> 12) % 12, pants: (n >>> 16) % 6, kind: 0, fur: 0, armor: 0, cape: 0 };   // 처음엔 누구나 원본 고양이 기사 (갈색 털 · 은빛 갑옷 · 빨간 망토)
}
function faceOf(a) {                       // 서버가 준 값도 범위 밖이면 이름에서 정한 값으로
  const d = defaultFace(a.name), f = a.face || d, out = {};
  for (const k of Object.keys(RANGES)) out[k] = Number.isInteger(f[k]) && f[k] >= 0 && f[k] < RANGES[k] ? f[k] : d[k];
  return out;
}

// 2026-10-16 (10) 그림체 한 번 더: 사용자가 보낸 도트 캐릭터처럼 — 얼굴보다 넓고 풍성한 머리(가닥 · 빛띠) · 세로로 큰 눈(4점, 빛 두 점) ·
// 키보다 긴 목검 · 둥근 3단 음영 · 진한 외곽선.  옷은 우리 것(저고리 · 흰 깃 · 고름 · 통 넓은 바지 · 대님 · 노비 무명옷) 그대로.
// 점 판(격자)에 색을 칠한 뒤, 빈 칸 가운데 그림에 닿은 칸을 외곽선으로 둘러 그린다.
const OL = "#150e0b", K = "#141010", OX = 4, OY = 6;   // 장식 · 목검 · 날개가 나갈 여백 (점 단위)
const GW = 22, GH = 31;                     // 몸 격자 (가로 22 · 세로 31 — 발바닥 = 31 줄) · 머리 = 위 16 줄
const CW = GW + OX * 2, CH = GH + OY + 1;
const FOOT = (OY + GH) * PX;                // 그림 위에서 발바닥까지 (px)
const HEAD_PX = (GH + 4) * PX;              // 발바닥에서 모자 꼭대기까지 — 상태 글자 · 말풍선 자리
const spriteCache = new Map();
// dir: 0 아래 · 1 위 · 2 왼쪽 · 3 오른쪽 / frame: 0 섬 · 1 · 2 걸음 / role: member · unit · leader · operator · bare / armed: 목검 들기
function charSprite(F, role, dir, frame, armed = false) {
  const key = `${JSON.stringify(F)}|${role}|${dir}|${frame}|${armed ? 1 : 0}`; if (spriteCache.has(key)) return spriteCache.get(key);
  const grid = new Array(CW * CH).fill(null);
  const flip = dir === 3, side = dir >= 2, up = dir === 1, down = dir === 0;
  const put = (x, y, col) => { const X = OX + (flip ? GW - 1 - x : x), Y = OY + y; if (col && X >= 0 && X < CW && Y >= 0 && Y < CH) grid[Y * CW + X] = col; };
  const get = (x, y) => { const X = OX + (flip ? GW - 1 - x : x), Y = OY + y; return X >= 0 && X < CW && Y >= 0 && Y < CH ? grid[Y * CW + X] : null; };
  const box = (x, y, w, h, col) => { for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) put(x + i, y + j, col); };
  const rbox = (x, y, w, h, col) => { for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
    if ((i === 0 || i === w - 1) && (j === 0 || j === h - 1) && w > 2 && h > 2) continue; put(x + i, y + j, col); } };
  // 둥근 덩어리 — 왼쪽 위가 밝고 오른쪽 아래 둘레가 어두움 (3단 음영) · keep(x, y) 로 일부만
  const blob = (cx, cy, rx, ry, col, hi, dk, keep) => {
    for (let y = Math.floor(cy - ry); y <= Math.ceil(cy + ry); y++) for (let x = Math.floor(cx - rx); x <= Math.ceil(cx + rx); x++) {
      const nx = (x + .5 - cx) / rx, ny = (y + .5 - cy) / ry, r = nx * nx + ny * ny;
      if (r > 1 || (keep && !keep(x, y))) continue;
      put(x, y, nx * .55 + ny * .8 > .62 && r > .42 ? dk : hi && nx * .5 + ny * .85 < -.5 && r > .2 && r < .75 ? hi : col);
    }
  };
  const H_ = HAIRC[F.hairc], Hd = shade(H_, -.34), Hdd = shade(H_, -.55), Hh = shade(H_, F.hairc === 0 ? .3 : .32), Hs = shade(H_, .55);
  const SK = SKINS[F.skin], SKd = shade(SK, -.15), SKdd = shade(SK, -.28), SKh = shade(SK, .45);
  const nobi = role === "operator", hat = role === "member" || role === "unit" || role === "leader";
  const CL = nobi ? "#a8956c" : CLOTHS[F.cloth], CLd = shade(CL, -.25), CLdd = shade(CL, -.45), CLh = shade(CL, .3);
  const PA = nobi ? "#7d6c4e" : PANTS[F.pants], PAd = shade(PA, -.2), PAdd = shade(PA, -.38), PAh = shade(PA, .2);
  const RIB = ["#c0262d", "#7a1fa2", "#d9480f"][F.cloth % 3], RIBh = shade(RIB, .3), RIBd = shade(RIB, -.3);
  const WH = "#fbf6ea", WHd = "#d9d2c0", SH = "#2a211c", SHh = "#5a4a3c", GOLD = "#d4af37";
  const step = frame === 1 ? 1 : frame === 2 ? -1 : 0, hs = nobi ? -1 : F.hair, bald = hs === 8;   // 노비 = 머리 모양 대신 늘 산발
  // 목검 — 키보다 길게, 손에 세워 듦 (휘두를 때는 drawSwing 이 그림).  x = 날 왼쪽, y0 = 칼끝, hy = 코등이 줄
  const sword = (x, y0, hy) => {
    put(x + 1, y0, "#e9c99a"); put(x + 1, y0 + 1, "#f6dfb6"); put(x + 2, y0 + 1, "#c99d68");
    for (let y = y0 + 2; y < hy; y++) { put(x, y, "#f6dfb6"); put(x + 1, y, "#dcb47e"); put(x + 2, y, "#b0814e"); }
    for (let y = y0 + 4; y < hy - 2; y += 5) put(x + 1, y, "#c99d68");                    // 나뭇결
    box(x - 1, hy, 5, 1, "#3e2818"); put(x - 1, hy, "#5a3a22");
    for (let y = hy + 1; y < hy + 6; y++) { put(x, y, "#7a4a28"); put(x + 1, y, "#5e3820"); put(x + 2, y, "#4a2c18"); }
    for (let y = hy + 2; y < hy + 6; y += 2) box(x, y, 3, 1, "#a06a3a");                 // 손잡이 감은 끈
    box(x, hy + 6, 3, 1, "#3e2818");
  };

  // ── 몸 뒤 (긴 머리 · 양갈래 · 포니테일 · 등 뒤 목검) ──
  if (armed && side) sword(16, 1, 21);
  if (armed && up) sword(18, 0, 21);
  if (!bald && hs === 7) {
    if (up) blob(11, 16, 9.5, 9, H_, Hh, Hd, (x, y) => y >= 9);
    else if (side) blob(14, 15, 6, 9, H_, Hh, Hd, (x, y) => y >= 8);
    else { blob(11, 15, 10, 9, H_, null, Hd, (x, y) => y >= 8); for (const x of [2, 19]) box(x, 12, 1, 10, Hd); }
  }
  if (hs === 4 && !up) {
    const tail = x => { blob(x, 14, 2.6, 5.5, H_, Hh, Hd); box(Math.round(x - 2), 9, 4, 1, RIB); put(Math.round(x - 1), 9, RIBh); for (let y = 12; y < 19; y += 3) put(Math.round(x), y, Hd); };
    if (side) tail(17); else { tail(1); tail(20); }
  }
  if (hs === 9 && side) { blob(18, 9, 3, 7, H_, Hh, Hd); box(16, 3, 3, 1, RIB); for (let y = 6; y < 15; y += 3) put(18, y, Hd); }

  // ── 다리 · 신 (통 넓은 바지 + 대님) ──
  if (!side) {
    const l = step > 0 ? 1 : 0, r = step < 0 ? 1 : 0;
    rbox(5, 25, 12, 3, PA); box(5, 25, 2, 3, PAh); box(15, 25, 2, 3, PAd); box(10, 26, 2, 2, PAdd);
    box(6, 28 - l, 4, 1, PAdd); box(12, 28 - r, 4, 1, PAdd); box(6, 28 - l, 4, 1, PAdd);
    for (const [x, d] of [[5, l], [12, r]]) { rbox(x, 29 - d, 5, 2, SH); box(x + 1, 29 - d, 3, 1, SHh); }
  } else {
    rbox(6, 25, 10, 3, PA); box(6, 25, 2, 3, PAh); box(14, 25, 2, 3, PAd);
    box(7 - step, 28, 4, 1, PAdd); box(11 + step, 28, 4, 1, PAdd);
    rbox(5 - step, 29, 6, 2, SH); box(6 - step, 29, 3, 1, SHh); rbox(11 + step, 29, 5, 2, SH);
  }
  // ── 몸 (저고리) · 팔 ──
  if (!side) {
    rbox(6, 17, 10, 8, CL); box(5, 18, 12, 2, CL); box(6, 18, 1, 6, CLh); box(15, 18, 1, 6, CLd); box(7, 24, 8, 1, CLd); box(6, 23, 10, 1, CLd);
    if (down && armed) sword(1, 0, 22);
    const la = step > 0 ? -1 : step < 0 ? 1 : 0;
    for (const [x, d] of [[3, la], [16, -la]]) {
      const left = x < 10;
      rbox(x, 17 + d, 3, 6, CL); box(left ? x + 2 : x, 18 + d, 1, 4, CLdd); box(left ? x : x + 2, 18 + d, 1, 4, left ? CLh : CLd);
      box(x, 22 + d, 3, 1, CLdd);
      rbox(x, 23 + d, 3, 2, SK); put(left ? x + 2 : x, 24 + d, SKd); put(left ? x : x + 2, 23 + d, SKh);
    }
    if (down) {
      if (!nobi) {
        for (const [x, y] of [[8, 17], [9, 17], [9, 18], [10, 18], [10, 19], [13, 17], [12, 17], [12, 18]]) put(x, y, WH);
        put(10, 17, SK); put(11, 17, SK); put(11, 18, SKd); put(11, 19, CLd); put(13, 18, WHd);
        put(11, 20, RIBd); put(12, 20, RIB); put(10, 20, RIB); box(11, 21, 1, 4, RIB); box(12, 21, 1, 3, RIBh); put(12, 24, RIB);
      } else { put(10, 17, SK); put(11, 17, SK); put(9, 17, CLd); put(12, 17, CLd); }
    } else { box(8, 17, 6, 1, WH); box(9, 17, 4, 1, WHd); box(10, 18, 2, 5, CLd); }
  } else {
    rbox(7, 17, 8, 8, CL); box(7, 18, 1, 6, CLh); box(13, 18, 2, 6, CLd); box(8, 24, 7, 1, CLd);
    if (!nobi) { put(7, 17, WH); put(8, 17, WH); put(8, 18, WH); put(7, 21, RIB); put(8, 21, RIBd); put(7, 22, RIB); put(6, 23, RIB); put(7, 24, RIBh); }
    rbox(9 + step, 17, 4, 6, CL); box(9 + step, 18, 1, 4, CLh); box(12 + step, 18, 1, 4, CLdd); box(9 + step, 22, 4, 1, CLdd);
    rbox(9 + step, 23, 4, 2, SK); put(12 + step, 24, SKd); put(9 + step, 23, SKh);
  }
  if (nobi) {                               // 노비 — 거지 같은 누더기: 기운 헝겊 · 얼룩 · 너덜한 밑단 · 찢어진 소매 · 새끼줄 띠 · 맨 정강이 · 짚신
    const bx = side ? 7 : 6, bw = side ? 8 : 10, P1 = "#6e7f8c", P2 = "#8a6440", ST = "#3e3424", DIRT = shade(CL, -.5);
    if (!side) {
      box(7, 19, 3, 2, up ? P2 : P1); put(7, 19, shade(up ? P2 : P1, .25)); put(9, 20, ST); put(7, 21, ST);       // 기운 헝겊 + 바늘땀
      box(13, 21, 2, 2, up ? P1 : P2); put(14, 20, ST); put(12, 22, ST);
      for (const [x, y] of [[8, 23], [12, 18], [14, 19], [6, 21]]) put(x, y, DIRT);                                // 얼룩
      for (const [x, h] of [[6, 1], [8, 2], [9, 1], [11, 2], [13, 1], [15, 2]]) for (let k = 0; k < h; k++) put(x, 25 + k, k ? CLd : CL);   // 너덜한 밑단
      for (const x of [3, 16]) { box(x, 21, 3, 1, SK); put(x + 1, 22, SK); put(x + (x < 10 ? 2 : 0), 22, CL); put(x + (x < 10 ? 0 : 2), 22, SKd); }   // 찢어진 소매 — 팔뚝이 보임
      box(7, 26, 2, 1, SK); put(8, 27, SKd); box(13, 26, 2, 1, SK); put(13, 27, SKd);                                 // 무릎 구멍
    } else {
      box(9, 19, 3, 2, P2); put(11, 20, ST); for (const [x, y] of [[13, 21], [8, 23]]) put(x, y, DIRT);
      for (const [x, h] of [[7, 1], [9, 2], [11, 1], [13, 2]]) for (let k = 0; k < h; k++) put(x, 25 + k, k ? CLd : CL);
      box(9 + step, 21, 4, 1, SK); put(10 + step, 22, SK); box(8, 26, 2, 1, SK);
    }
    box(bx, 22, bw, 1, "#6a4c26"); for (let i = bx; i < bx + bw; i += 2) put(i, 22, "#9a7440");                     // 새끼줄 띠
    if (!up) { put(bx + bw - 2, 23, "#6a4c26"); put(bx + bw - 2, 24, "#9a7440"); }                                 // 띠 끝 늘어짐
    // 맨 정강이 + 짚신
    const STRAW = "#b8954a", STRAWh = "#dcbc72", STRAWd = "#8a6a30";
    const legs = side ? [[7 - step, 4], [11 + step, 4]] : [[5, 4], [12, 4]], lift = side ? [0, 0] : [step > 0 ? 1 : 0, step < 0 ? 1 : 0];
    legs.forEach(([x, w], i) => { const d = lift[i]; box(x, 28 - d, w, 1, SKd); put(x + 1, 28 - d, SK);
      box(x - (side && i === 0 ? 1 : 0), 29 - d, w + 1, 2, STRAW); box(x, 29 - d, w, 1, STRAWh); for (let k = x; k < x + w + 1; k += 2) put(k, 30 - d, STRAWd);
      if (!up) put(side ? x - 1 : x + 1, 29 - d, SK); });                                                             // 발가락
  }
  // ── 머리 뒤 장식 (몸 위 · 얼굴 아래) ──
  if (!bald && hs === 2 && !down) {         // 댕기머리 — 땋은 머리 + 댕기
    const bx = up ? 10 : 15;
    for (let y = up ? 15 : 13; y < 24; y++) { put(bx, y, (y % 2) ? Hd : H_); put(bx + 1, y, (y % 2) ? H_ : Hh); }
    box(bx - 1, 24, 4, 2, RIB); put(bx - 1, 24, RIBh); put(bx, 26, RIBd); put(bx + 2, 26, RIBd);
  }
  if (!bald && hs === 3 && !down) {         // 쪽머리 — 뒤통수 쪽 + 비녀
    if (up) { blob(11, 12, 3.6, 3, H_, Hh, Hd); box(5, 12, 12, 1, GOLD); put(5, 12, "#fff0a0"); }
    else { blob(17, 11, 3, 3, H_, Hh, Hd); box(14, 11, 8, 1, GOLD); put(21, 11, "#fff0a0"); }
  }
  if (!bald && hs === 9 && up) { blob(11, 13, 2.6, 6, H_, Hh, Hd); box(9, 7, 5, 1, RIB); }

  // ── 머리 (큰 얼굴) ──
  const fcx = side ? 9.8 : 11, frx = side ? 6.8 : 7.6;
  if (up && !bald) blob(11, 8.6, 8.4, 7.6, H_, Hh, Hd);
  else blob(fcx, 9.8, frx, 6.4, SK, null, SKd);                                           // 얼굴
  if (!up) { for (let x = 5; x < 18; x++) if (get(x, 15) === SK) put(x, 15, SKd); }         // 턱 그늘
  if (side && !bald) { blob(13.4, 8.4, 6.6, 7.4, H_, Hh, Hd, (x, y) => x >= 9 || y <= 6); }  // 옆: 뒤통수 머리
  // 머리 위 장식 (모자 쓴 역할은 가려져 안 그림)
  if (!hat && !bald) {
    if (hs === 0) { blob(11, -1.6, 2.4, 2.4, H_, Hh, Hd); box(9, 0, 5, 1, "#7a5a30"); }
    if (hs === 5) { blob(11, -1.2, 4.4, 3.6, H_, Hh, Hd); for (const x of [9, 12]) put(x, -1, Hd); }
    if (hs === 6) for (const [x, h] of [[3, 3], [6, 4], [10, 5], [14, 4], [17, 3]]) for (let k = 0; k < h; k++) {
      const w = Math.max(1, Math.round((h - k) * .7)); box(x + (side ? 1 : 0), 2 - k, w, 1, k === h - 1 ? Hh : H_); }
  }
  if (!bald) {
    if (up) { box(6, 2, 6, 1, Hh); box(5, 3, 2, 1, Hh); box(13, 2, 2, 1, Hs);                  // 뒤: 빛띠 · 가닥
      for (const x of [6, 9, 13, 16]) box(x, 7, 1, 7, Hd); for (let x = 4; x < 19; x++) if (get(x, 15) === H_) put(x, 15, Hd); }
    else if (down) {
      blob(11, 7.2, 9.4, 7.6, H_, Hh, Hd, (x, y) => y <= 7 || x <= 3 || x >= 18);               // 머리 덮개 (얼굴보다 넓게)
      const sideLen = hs === 1 ? 16 : hs === 7 ? 17 : hs === 2 ? 14 : 13;                      // 옆머리
      for (const x of [2, 3, 18, 19]) for (let y = 8; y < sideLen - (x === 2 || x === 19 ? 1 : 0); y++) put(x, y, x === 3 || x === 18 ? H_ : Hd);
      const bang = [9, 10, 9, 8, 10, 10, 9, 8, 9, 10, 10, 9, 8, 9];                            // 앞머리 가닥 (들쭉날쭉)
      for (let i = 0; i < bang.length; i++) { const x = 4 + i;
        for (let y = 6; y < bang[i]; y++) put(x, y, y === bang[i] - 1 ? Hd : H_); }
      for (const x of [6, 9, 12, 15]) put(x, 7, Hd);                                          // 가닥 사이 그늘
      box(6, 2, 5, 1, Hh); box(5, 3, 2, 1, Hh); put(11, 2, Hs); box(14, 3, 2, 1, Hh); put(13, 2, Hh);   // 빛띠
      if (hs === 3) { box(10, 1, 2, 4, SKh); put(10, 5, SKd); }                               // 쪽머리 가르마
      if (hs === 3) { for (const x of [0, 1, 20, 21]) put(x, 12, GOLD); }                    // 비녀 끝
      if (hs === 9) { blob(19.5, 11, 1.8, 4, H_, null, Hd); put(19, 7, RIB); put(20, 7, RIB); }   // 포니테일 끝
    } else {                                                                                   // 옆 (왼쪽 보기)
      blob(10.5, 7, 8.6, 7.2, H_, Hh, Hd, (x, y) => y <= 6 || x >= 10);
      for (const [x, b] of [[3, 8], [4, 9], [5, 8], [6, 9], [7, 8], [8, 7]]) for (let y = 6; y < b; y++) put(x, y, y === b - 1 ? Hd : H_);
      box(5, 2, 5, 1, Hh); box(4, 3, 2, 1, Hh); put(11, 2, Hs); for (const x of [13, 16]) box(x, 6, 1, 7, Hd);
      if (hs === 1) blob(14, 13, 5, 3, H_, null, Hd, (x, y) => y >= 12); if (hs === 7) blob(14, 14, 5.4, 4, H_, null, Hd, (x, y) => y >= 12);
      rbox(10, 10, 3, 4, SK); put(11, 11, SKdd); put(12, 12, SKd); put(10, 10, SKh);         // 귀
    }
  } else { if (up) blob(11, 9.8, 7.6, 6.4, SK, null, SKd); box(7, 4, 3, 1, SKh); box(6, 5, 2, 1, SKh); }   // 민머리 빛
  // 노비 — 산발: 사방으로 뻗친 머리칼 · 엉킨 옆머리 · 들쭉날쭉 긴 앞머리 (머리 모양 고른 것과 상관없이)
  if (nobi) {
    const spike = (x, y, dx, dy, n, col) => { for (let k = 0; k < n; k++) put(x + dx * k, y + dy * k, k === n - 1 ? Hd : col || H_); };
    for (const [x, y, dx, dy, n] of [[4, 0, -1, -1, 3], [7, -1, 0, -1, 3], [10, -1, 1, -1, 2], [12, -2, 0, -1, 2], [15, -1, 1, -1, 3], [18, 1, 1, -1, 3],
      [1, 4, -1, 0, 3], [0, 8, -1, 1, 2], [20, 4, 1, 0, 3], [21, 8, 1, 1, 2], [2, 2, -1, -1, 2], [19, 2, 1, -1, 2]]) spike(x, y, dx, dy, n);
    for (const [x, y0, y1] of [[1, 9, 15], [2, 8, 18], [3, 12, 17], [20, 9, 17], [19, 8, 19], [18, 13, 16]]) for (let y = y0; y < y1; y++) put(x, y, (x + y) % 3 ? H_ : Hd);   // 엉킨 옆머리
    for (const [x, y] of [[0, 15], [3, 18], [21, 16], [18, 17], [1, 17]]) put(x, y, Hd);                              // 삐져나온 가닥
    if (up) for (let x = 4; x < 19; x++) { const b = 15 + ((x * 7) % 4); for (let y = 14; y < b; y++) put(x, y, (x + y) % 3 ? H_ : Hd); }   // 뒤 — 들쭉날쭉 긴 뒷머리
    else if (down) { for (const [x, b] of [[4, 11], [5, 9], [7, 11], [8, 8], [10, 10], [11, 12], [12, 9], [15, 11], [16, 9], [17, 12]]) for (let y = 7; y < b; y++) put(x, y, y === b - 1 ? Hd : H_); }
    else for (const [x, b] of [[3, 11], [5, 10], [7, 12], [8, 9]]) for (let y = 7; y < b; y++) put(x, y, y === b - 1 ? Hd : H_);
    put(8, 3, Hs); put(13, 2, Hs);
  }
  // 얼굴 — 눈은 세로 4점 (속눈썹 · 눈동자 · 빛 두 점)
  const e = F.eyes, BL = "#f39a92", IR = "#3a2216", IM = "#6b3a20", IL = "#9a5a32";
  const eye = (x, out) => {                  // x = 눈 왼쪽 칸, out = 바깥쪽 (-1 왼쪽 · 1 오른쪽)
    const o = out < 0 ? x - 1 : x + 3, hiX = x;
    if (e === 0) { box(x, 11, 2, 3, K); put(x + (out < 0 ? 0 : 1), 10, K); put(hiX, 11, "#ffffff"); put(x + 1, 13, "#3a3030"); }
    else if (e === 1) { box(x, 10, 3, 1, K); put(o, 10, K); put(o, 11, K);
      box(x, 11, 3, 1, IR); put(hiX, 11, "#ffffff"); box(x, 12, 3, 1, IM); put(x + 1, 12, IR); box(x, 13, 3, 1, IL); put(x + 2, 12, "#ffffff"); }
    else if (e === 2) { put(x - (out < 0 ? 1 : 0), 12, K); box(x, 11, 3, 1, K); put(x + 3 - (out < 0 ? 0 : 0), 12, K); }
    else if (e === 3) { box(x, 11, 3, 1, K); box(x, 12, 3, 1, IR); put(hiX, 12, "#ffffff"); put(o, 9, K); put(out < 0 ? x : x + 2, 9, K); put(x + 1, 10, K); }
    else { box(x - 1, 10, 5, 1, "#2a2a2a"); box(x - 1, 13, 5, 1, "#2a2a2a"); box(x - 1, 11, 1, 2, "#2a2a2a"); box(x + 3, 11, 1, 2, "#2a2a2a");
      box(x, 11, 3, 2, "#cfe8ff"); put(x, 11, "#ffffff"); box(x + 1, 12, 1, 1, K); }
  };
  if (down) {
    eye(6, -1); eye(13, 1);
    if (e === 4) box(10, 11, 2, 1, "#2a2a2a");
    if (e !== 4 && F.beard !== 3 && !nobi) { box(4, 14, 2, 1, BL); box(16, 14, 2, 1, BL); }
    if (nobi) { put(5, 14, SKdd); put(16, 13, SKdd); put(15, 15, SKd); put(7, 15, SKd); for (let y = 9; y < 13; y++) put(14, y, y === 12 ? Hd : H_); put(15, 10, H_); }   // 때 자국 · 눈을 덮는 머리칼
    put(10, 14, "#b0574a"); put(11, 14, "#8a3a32");
    if (F.beard === 1) { box(8, 14, 2, 1, H_); box(12, 14, 2, 1, H_); put(10, 14, H_); put(11, 14, Hd); put(10, 15, "#8a3a32"); }
    else if (F.beard === 2) { box(10, 15, 2, 3, H_); put(10, 17, Hd); }
    else if (F.beard === 3) { box(5, 14, 12, 2, H_); box(6, 16, 10, 1, Hd); box(10, 14, 2, 1, "#8a3a32"); put(4, 13, H_); put(17, 13, H_); }
  } else if (side) {
    eye(4, -1);
    if (e !== 4 && !nobi) box(6, 14, 2, 1, BL); if (nobi) { put(6, 14, SKdd); put(8, 12, SKdd); for (let y = 9; y < 12; y++) put(5, y, H_); }
    put(3, 14, "#8a3a32"); put(2, 11, SK); put(2, 12, SKd);   // 볼 · 입 · 코
    if (F.beard === 1) box(2, 14, 3, 1, H_); else if (F.beard === 2) box(3, 15, 2, 3, H_); else if (F.beard === 3) { box(3, 13, 7, 3, H_); put(3, 14, "#8a3a32"); }
  }
  // ── 역할 머리 장식 (서버가 정한 것) ──
  const L = side ? 3 : 2, R = side ? 19 : 19;                                  // 머리 폭 (모자 둘레)
  if (role === "leader") {                  // 왕관
    const G = "#e8b923", Gd = "#a8780b", Gh = "#fff0a0";
    box(L + 1, 0, R - L - 1, 3, G); box(L + 1, 0, R - L - 1, 1, Gh); box(L + 1, 2, R - L - 1, 1, Gd);
    for (const [x, h] of side ? [[4, 2], [8, 3], [12, 2], [16, 2]] : [[3, 2], [7, 3], [10, 4], [13, 3], [17, 2]]) { box(x, -h, 2, h, G); put(x, -h, Gh); put(x + 1, -1, Gd); }
    if (!up) { const gx = side ? 7 : 10; box(gx, 1, 2, 1, "#d62d3a"); put(gx, 1, "#ff8a8a"); for (const x of side ? [12] : [5, 15]) put(x, 1, "#2e7bd6"); }
  } else if (role === "unit" || role === "member") {   // 사모(날개 관모) · 관모
    const B = "#242424", Bh = "#4c4c4c", Bd = "#0e0e0e";
    rbox(L + 3, -3, R - L - 5, 4, B); rbox(L + 1, -1, R - L - 1, 4, B); box(L + 4, -2, 4, 1, Bh); put(L + 3, -1, Bh);
    box(L + 1, 2, R - L - 1, 1, "#3a2c1e"); box(L + 2, 2, 3, 1, "#5a4630");
    if (role === "unit") {
      if (side) { rbox(17, -2, 6, 3, B); box(18, -1, 4, 1, Bh); }
      else { rbox(-3, 0, 6, 3, B); rbox(19, 0, 6, 3, B); box(-2, 1, 4, 1, Bh); box(20, 1, 4, 1, Bd); }
    }
  } else if (role === "operator") {         // 노비 — 산발 위에 흰 머리띠 (좀 때 탄 무명) + 묶은 끝이 늘어짐
    const B = "#f2eee4", Bd = "#cfc8b6", Bdd = "#a59d88";
    box(L, 4, R - L + 1, 2, B); box(L, 5, R - L + 1, 1, Bd); put(L + 4, 4, Bd); put(R - 5, 5, Bdd); put(L + 9, 5, Bdd);   // 띠 · 주름 · 때
    if (up) { box(10, 6, 2, 2, B); put(9, 8, B); box(9, 9, 1, 3, Bd); box(12, 8, 1, 4, B); put(12, 11, Bd); }          // 뒤통수 매듭 · 늘어진 두 끝
    else if (side) { box(19, 4, 2, 2, B); box(20, 6, 1, 4, B); put(21, 7, Bd); box(21, 8, 1, 3, Bd); }                // 옆 — 뒤로 늘어진 끝
    else { put(R + 1, 4, B); put(R + 2, 5, Bd); put(R + 1, 6, B); put(R + 2, 7, Bd); }                                 // 앞 — 옆으로 삐져나온 끝
  }

  // ── 외곽선 · 칠하기 ──
  const c = canvas(CW * PX, CH * PX), g = c.getContext("2d");
  const outG = grid.slice();
  for (let Y = 0; Y < CH; Y++) for (let X = 0; X < CW; X++) {
    if (grid[Y * CW + X]) continue;
    const n = (dx, dy) => { const x = X + dx, y = Y + dy; return x >= 0 && y >= 0 && x < CW && y < CH && grid[y * CW + x]; };
    if (n(1, 0) || n(-1, 0) || n(0, 1) || n(0, -1)) outG[Y * CW + X] = OL;
  }
  for (let Y = 0; Y < CH; Y++) for (let X = 0; X < CW; X++) { const col = outG[Y * CW + X]; if (col) { g.fillStyle = col; g.fillRect(X * PX, Y * PX, PX, PX); } }
  spriteCache.set(key, c); return c;
}

// ── 고양이 기사 (2026-10-19) ─────────────────────────────────────────────
// 사용자가 준 캐릭터 시트에서 캐릭터 부분만 뽑은 그림 static/catknight.png (배경 투명 · 그림 한 칸 = 원래 도트 한 점).
// 화면에는 PX 배로 키워 붙인다 (imageSmoothing 끔 — 흐리지 않게).  털 · 갑옷 · 망토는 팔레트 묶음별로 색만 바꾼다.
// 칸: down · up · left · right (서 있기) · walk0~4 (오른쪽 걷기, 왼쪽은 뒤집음) · atk0~4 (오른쪽 공격, 칼바람 포함) · hurt · idle(얼굴 판 미리보기)
// 기준점: [x, y, w, h, 가운데 x, 발바닥 y] — 그림 안 점 단위
const CAT_FR = {"down":[0,0,31,37,15.6,36],"up":[32,0,29,36,14.0,35],"left":[62,0,33,39,16.9,38],"right":[96,0,33,36,13.7,35],"walk0":[130,0,32,35,14.7,34],"walk1":[163,0,31,35,13.8,34],"walk2":[195,0,28,34,13.4,33],"walk3":[224,0,28,34,13.1,33],"walk4":[253,0,30,34,13.7,33],"atk0":[284,0,30,33,13.8,31],"atk1":[315,0,34,32,15.3,31],"atk2":[350,0,46,34,18.7,33],"atk3":[397,0,54,31,23.1,29],"atk4":[452,0,31,31,13.7,30],"hurt":[484,0,26,30,12.5,29],"idle":[511,0,36,48,17.1,47]};
const CAT_PAL = "0d0d12O571c18C2b1211O949288A090508O884522Fcc372bC020102O715743ffdfbedGe6b16cf5e6b76A4e443fOa85427Fdc8239F2d3039Aaf2c27C1c222cAfae7a3Gbe8f57f401515C384556Afaf3c5G9b6c3ff412b23ff8ba4cG8f2122C741b1dC68361ff15161dOada390mf8d888G877765Ocebe9em1b090aOfbd368Gc46b30F4b5967A777f83Aec9a47F";
// CAT_PAL = 7자씩 "rrggbbG" — G: O 외곽선 · 눈(안 바꿈) · F 털 · f 털(머리 쪽에 있을 때만 — 갑옷 반사에도 쓰인 색) · m 주둥이(머리 쪽만) · A 갑옷 · G 금 장식 · 검(안 바꿈) · C 망토
const CAT = { data: null, ready: false };
(function loadCat() {
  const im = new Image();
  im.onload = () => { const c = canvas(im.width, im.height), g = c.getContext("2d", { willReadFrequently: true }); g.drawImage(im, 0, 0);
    CAT.data = g.getImageData(0, 0, im.width, im.height); CAT.ready = true; };
  im.src = "/static/catknight.png";
})();
function rgb2hsl(r, g, b) {
  r /= 255; g /= 255; b /= 255; const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn;
  if (!d) return [0, 0, l];
  const s = l > .5 ? d / (2 - mx - mn) : d / (mx + mn);
  const h = mx === r ? ((g - b) / d + (g < b ? 6 : 0)) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s, l];
}
function hsl2rgb(h, s, l) {
  h = ((h % 360) + 360) % 360 / 360; s = Math.max(0, Math.min(1, s)); l = Math.max(0, Math.min(1, l));
  if (!s) return [l * 255, l * 255, l * 255].map(Math.round);
  const q = l < .5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
  const f = t => { t = (t + 1) % 1; return t < 1 / 6 ? p + (q - p) * 6 * t : t < .5 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p; };
  return [f(h + 1 / 3), f(h), f(h - 1 / 3)].map(v => Math.round(v * 255));
}
// 바꾸는 방법 — h: 색상(원래 색의 흔들림은 일부 남김) · s: 채도(수 또는 함수) · l: 밝기 함수.  0 번 = 원본 그대로
const FUR_T = [null, { h: 210, s: .07 }, { h: 230, s: .1, l: l => l * .36 + .03 }, { h: 38, s: .16, l: l => .58 + l * .42 },
  { h: 26, s: x => Math.min(1, x * 1.35), l: l => l < .3 ? l * .4 : Math.min(.9, l * 1.08) }, { h: 14, s: x => Math.min(1, x * 1.25), l: l => l * .96 }];
const MUZ_T = [null, { s: .05 }, { h: 220, s: .06, l: l => l * .5 }, { h: 40, s: .08, l: l => .84 + l * .14 }, null, { h: 40, s: .05, l: l => .86 + l * .12 }];
const ARM_T = [null, { h: 42, s: .62, l: l => Math.min(.9, l * 1.1 + .06) }, { h: 228, s: .14, l: l => l * .55 }, { h: 24, s: .5, l: l => l * 1.04 },
  { h: 212, s: .5, l: l => l * 1.06 }, { h: 210, s: .05, l: l => Math.min(.95, .22 + l * .9) }];
const CAPE_T = [null, { h: 218 }, { h: 128, s: x => x * .85 }, { h: 282 }, { h: 0, s: .1, l: l => l * .42 },
  { h: 30, s: .06, l: l => Math.min(.95, .45 + l * 1.1) }, { h: 44, l: l => Math.min(.85, l * 1.3 + .05) }];
const catMaps = new Map();
function catMap(F) {                         // 원본 색 → 이 사람 색
  const key = `${F.fur}|${F.armor}|${F.cape}`; if (catMaps.has(key)) return catMaps.get(key);
  const m = new Map();
  for (let i = 0; i < CAT_PAL.length; i += 7) {
    const n = parseInt(CAT_PAL.slice(i, i + 6), 16), grp = CAT_PAL[i + 6], r = n >> 16 & 255, g = n >> 8 & 255, b = n & 255;
    const t = grp === "F" || grp === "f" ? FUR_T[F.fur] : grp === "m" ? MUZ_T[F.fur] : grp === "A" ? ARM_T[F.armor] : grp === "C" ? CAPE_T[F.cape] : null;
    if (!t) continue;
    let [h, s, l] = rgb2hsl(r, g, b); const h0 = h > 180 ? h - 360 : h;
    if (t.h != null) h = t.h + (grp === "C" ? h0 : grp === "F" || grp === "f" ? (h - 25) * .6 : 0);   // 망토 · 털은 원래 색 흔들림을 조금 남김 (갑옷 · 주둥이는 회색이 섞여 한 색으로)
    s = typeof t.s === "function" ? t.s(s) : t.s ?? s; l = t.l ? t.l(l) : l;
    m.set(n, { c: hsl2rgb(h, s, l), head: grp === "f" || grp === "m" });
  }
  catMaps.set(key, m); return m;
}
function catSprite(F, name, mirror) {      // 한 칸을 이 사람 색으로 · PX 배 · (뒤집기)  → canvas 에 cx · foot(px) 를 붙여 돌려줌
  const key = `cat|${F.fur}|${F.armor}|${F.cape}|${name}|${mirror ? 1 : 0}`; if (spriteCache.has(key)) return spriteCache.get(key);
  const [fx, fy, fw, fh, cx, foot] = CAT_FR[name], src = CAT.data, map = catMap(F), small = new ImageData(fw, fh);
  for (let y = 0; y < fh; y++) for (let x = 0; x < fw; x++) {
    const si = ((fy + y) * src.width + fx + x) * 4; if (src.data[si + 3] < 128) continue;
    const n = src.data[si] << 16 | src.data[si + 1] << 8 | src.data[si + 2], e = map.get(n), c = e && (!e.head || y < foot * .47) ? e.c : null;   // 머리 쪽 = 발바닥 높이의 위 47%
    const di = (y * fw + (mirror ? fw - 1 - x : x)) * 4;
    small.data[di] = c ? c[0] : src.data[si]; small.data[di + 1] = c ? c[1] : src.data[si + 1]; small.data[di + 2] = c ? c[2] : src.data[si + 2]; small.data[di + 3] = 255;
  }
  const s1 = canvas(fw, fh); s1.getContext("2d").putImageData(small, 0, 0);
  const c = canvas(fw * PX, fh * PX), g = c.getContext("2d"); g.imageSmoothingEnabled = false; g.drawImage(s1, 0, 0, c.width, c.height);
  c.cx = (mirror ? fw - cx : cx) * PX; c.foot = foot * PX;
  spriteCache.set(key, c); return c;
}
// 지금 모습에 맞는 칸 — 시트에 있는 포즈만 쓴다 (위 · 아래 걷기 칸은 시트에 없어 서 있는 칸을 한 점씩 들썩임)
function catPose(a, now, atk, hit) {
  const side = a.dir >= 2, left = a.dir === 2;
  if (atk >= 0 && side) return [`atk${Math.min(4, Math.floor(atk * 5))}`, left];
  if (hit >= 0 && hit < .7 && side) return ["hurt", left];
  if (a.moving && side) return [`walk${Math.floor(now / 110) % 5}`, left];
  return [["down", "up", "left", "right"][a.dir] || "down", false];
}
const isCat = F => F.kind === 0 && CAT.ready;
// 마을 시트 캐릭터 (2026-10-19): d = 앞모습 대기 칸(번갈아 숨쉬기) · w = 앞으로 걷기 · s = 옆(비스듬) 칸 · sf = 옆 칸이 보는 쪽 · a = 공격 칸 · af = 공격 칸이 보는 쪽 · p = 큰 그림(얼굴 판)
// 시트에 뒷모습은 없어 위로 갈 때도 앞모습 칸을 씀
const KIND_FR = {
  2: { d: ["cat_d0", "cat_d1"], w: ["cat_d2", "cat_d3", "cat_d0", "cat_d1"], s: ["cat_s0", "cat_s1"], sf: "R", a: "cat_a", af: "R", p: "p_cat" },
  3: { d: ["panda_d0", "panda_d1"], w: ["panda_d1", "panda_d0"], s: ["panda_s0", "panda_s1"], sf: "L", a: "panda_a", af: "R", p: "p_panda" },
  4: { d: ["lion_d0", "lion_d1"], w: ["lion_d2", "lion_d3", "lion_d0", "lion_d1"], s: ["lion_s0", "lion_s1"], sf: "L", a: "lion_a", af: "R", p: "p_lion" },
  5: { d: ["tiger_d0", "tiger_d1"], w: ["tiger_d0", "tiger_d1"], s: ["tiger_d1", "tiger_d0"], sf: "L", a: "tiger_a", af: "L", p: "p_tiger" },
  6: { d: ["nobi_d0", "nobi_d1"], w: ["nobi_d1", "nobi_d0"], s: ["nobi_s0", "nobi_s1", "nobi_s2", "nobi_s3"], sf: "L", a: null, p: "p_nobi" },
};
const isChr = F => F.kind >= 2 && CHR.ready && !!KIND_FR[F.kind];
const chrSprite = (name, mirror) => atlasSprite(CHR, CHR_FR, name, mirror);
function chrPose(K, a, now, atk, seed = 0) {
  const side = a.dir >= 2, want = a.dir === 2 ? "L" : "R";
  if (atk >= 0 && K.a) return [K.a, side ? K.af !== want : false];
  if (side) { const L = a.moving ? K.s : [K.s[0]]; return [L[Math.floor(now / 150) % L.length], K.sf !== want]; }
  if (a.moving) return [K.w[Math.floor(now / 160) % K.w.length], false];
  return [K.d[Math.floor((now + seed) / 650) % K.d.length], false];
}
// 2026-10-19 역할: 그룹장 = 황금 갑옷 + 금빛 후광 · 유닛장 = 은색(백은) 갑옷 + 은빛 후광 — 역할이 정하므로 갑옷은 고를 수 없음
const ROLE_ARMOR = { leader: 1, unit: 5 };
const roleFace = (F, role) => role === "operator" ? { ...F, kind: 6 }               // 운영자 = 늘 노비
  : F.kind === 6 ? { ...F, kind: 0 }                                                     // 노비는 운영자만
  : role in ROLE_ARMOR ? { ...F, armor: ROLE_ARMOR[role] } : F;
const AURA = { leader: ["255,236,120", "#fff6c8", "#ffd23a", "#d99a10"], unit: ["226,236,250", "#ffffff", "#d6e2f2", "#a9b9cf"] };   // 빛 · 반짝이 두 색 · 고리 테
function drawAura(g, cx, footY, role, now, seed) {   // 몸 뒤 후광 — 천천히 숨쉬는 빛 + 둘레를 도는 반짝이 점 (점은 PX 칸에 맞춤)
  const A = AURA[role]; if (!A) return;
  const cy = footY - 34, k = .5 + .5 * Math.sin(now / 500 + seed);
  g.save();
  const gr = g.createRadialGradient(cx, cy, 4, cx, cy, 40 + k * 4);
  gr.addColorStop(0, `rgba(${A[0]},${.62 + k * .15})`); gr.addColorStop(.6, `rgba(${A[0]},${.32 + k * .12})`); gr.addColorStop(1, `rgba(${A[0]},0)`);
  g.fillStyle = gr; g.beginPath(); g.ellipse(cx, cy, 30 + k * 3, 42 + k * 4, 0, 0, Math.PI * 2); g.fill();
  const hy = footY - 58, R = 21 + Math.round(k);   // 머리 뒤 둥근 고리 (후광) — PX 칸 점으로
  for (let t = 0; t < 56; t++) { const a = t / 56 * Math.PI * 2, x = Math.round((cx + Math.cos(a) * R) / PX) * PX, y = Math.round((hy + Math.sin(a) * R * .9) / PX) * PX;
    g.fillStyle = A[3]; g.fillRect(x - PX / 2, y - PX / 2 + PX, PX, PX); g.fillStyle = A[1]; g.fillRect(x - PX / 2, y - PX / 2, PX, PX); }
  for (let i = 0; i < 6; i++) {             // 반짝이 6개 — 몸 둘레를 돌며 깜빡
    const ang = now / 900 + i * Math.PI / 3 + seed, r = 26 + 4 * Math.sin(now / 300 + i);
    const x = Math.round((cx + Math.cos(ang) * r) / PX) * PX, y = Math.round((cy + Math.sin(ang) * r * 1.3) / PX) * PX;
    const on = (Math.floor(now / 160) + i) % 3; if (!on) continue;
    g.fillStyle = on === 1 ? A[1] : A[2]; g.fillRect(x - PX, y, PX * 3, PX); g.fillRect(x, y - PX, PX, PX * 3);
  }
  g.restore();
}

const tintCache = new WeakMap();
function tinted(img) {                      // 맞은 순간 — 붉게 번쩍
  let c = tintCache.get(img); if (c) return c;
  c = canvas(img.width, img.height); const g = c.getContext("2d");
  g.drawImage(img, 0, 0); g.globalCompositeOperation = "source-atop"; g.fillStyle = "rgba(255,70,50,.65)"; g.fillRect(0, 0, c.width, c.height);
  tintCache.set(img, c); return c;
}
const ghostCache = new Map();
function ghostly(img) {                      // 유령 — 희푸르게
  let c = ghostCache.get(img); if (c) return c;
  c = canvas(img.width, img.height); const g = c.getContext("2d");
  g.drawImage(img, 0, 0); g.globalCompositeOperation = "source-atop"; g.fillStyle = "rgba(205,228,255,.7)"; g.fillRect(0, 0, c.width, c.height);
  ghostCache.set(img, c); return c;
}
// 목검을 휘두른다 — 바라보는 쪽으로 반원을 긋고 흰 칼바람을 남긴다
const BASE_ANG = { 0: Math.PI / 2, 1: -Math.PI / 2, 2: Math.PI, 3: 0 };
function drawSwing(g, sx, sy, dir, k, gold) {   // gold = 고양이 기사의 황금 검
  const px = sx + 16 + (dir === 2 ? -4 : dir === 3 ? 4 : 0), py = sy + 12 + (dir === 0 ? 2 : dir === 1 ? -4 : 0);   // 손 높이
  const side = dir === 2 ? -1 : 1, span = 1.35, base = BASE_ANG[dir];
  const ease = 1 - Math.pow(1 - k, 3), ang = base - side * span + side * 2 * span * ease;
  g.save();
  g.globalAlpha = .75 * (1 - k * .6); g.strokeStyle = "#ffffff"; g.lineWidth = 5; g.lineCap = "round";
  g.beginPath(); g.arc(px, py, 30, Math.min(base - side * span, ang), Math.max(base - side * span, ang)); g.stroke();
  g.globalAlpha = .35 * (1 - k); g.lineWidth = 9; g.strokeStyle = "#cfe9ff";
  g.beginPath(); g.arc(px, py, 26, Math.min(base - side * span, ang), Math.max(base - side * span, ang)); g.stroke();
  g.globalAlpha = 1; g.translate(px, py); g.rotate(ang); g.scale(1.4, 1.4);   // 손의 긴 목검에 맞춰 크게
  g.fillStyle = "#2a1a12"; g.fillRect(3, -3, 25, 6);
  g.fillStyle = gold ? "#f8ba4c" : "#d8b07a"; g.fillRect(9, -2, 18, 4); g.fillStyle = gold ? "#fbe7a3" : "#f0d3a2"; g.fillRect(9, -2, 18, 1);
  g.fillStyle = "#2a1a12"; g.fillRect(8, -5, 3, 10); if (gold) { g.fillStyle = "#d4a020"; g.fillRect(9, -4, 1, 8); }
  g.fillStyle = gold ? "#8a5a20" : "#6e4527"; g.fillRect(3, -2, 5, 4);
  g.restore();
}

// ── 상태 ───────────────────────────────────────────────────────────────
const S = { id: null, name: "", look: 0, face: null, role: "member", me: null, others: new Map(), logSeq: 0,
  typing: false, keys: new Set(), panel: false, status: "", atkHeld: false };
const cv = $("#pz-map"), ctx = cv.getContext("2d");

function newActor(p) { return { id: p.id, name: p.name, face: p.face || null, role: p.role || "member", tx: p.x, ty: p.y, x: p.x * T, y: p.y * T,
  dir: p.dir || 0, gx: p.x, gy: p.y, from: null, t0: 0, moving: false, steps: 0, bubble: null, sayseq: p.say_seq || 0,
  actseq: p.act_seq || 0, hitseq: p.hit_seq || 0, attack: 0, hit: null, status: p.status || "",
  hp: p.hp ?? 100, hpMax: p.hp_max || 100, ghost: !!p.ghost, kills: p.kills || 0, killer: !!p.killer }; }

function walkable(x, y) { return inside(x, y) && !solid[at(x, y)]; }
// 캐릭터끼리 겹치지 않음 (2026-10-16 대시보드): 다른 사람이 서 있거나(서버 칸) 가고 있는 칸은 막힘 — 서버도 같은 규칙으로 막음
// 유령(체력 0)은 남과 겹쳐 지나가고, 남도 유령 칸은 지나감 (서버와 같은 규칙)
function occupied(x, y) { if (S.me && S.me.ghost) return false;
  for (const a of S.others.values()) if (!a.ghost && ((a.gx === x && a.gy === y) || (a.tx === x && a.ty === y))) return true; return false; }
function freeNear(x, y) {                   // 들어오자마자 남과 같은 칸이면 가장 가까운 빈 칸으로
  for (let r = 1; r < 8; r++) for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
    if (Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
    const nx = x + dx, ny = y + dy; if (walkable(nx, ny) && !occupied(nx, ny)) return [nx, ny]; }
  return null;
}
function spawn() {                          // 이름마다 늘 같은 자리 — 광장 둘레 고리(가운데에서 4~9칸)에 흩어져 시작 (성문 앞에 몰리지 않게)
  const r = rng(hash(S.name || "x"));
  for (let i = 0; i < 400; i++) {
    const a = r() * Math.PI * 2, d = 4 + r() * 5, x = Math.round(31.5 + Math.cos(a) * d * 1.4), y = Math.round(21.5 + Math.sin(a) * d * .8);
    if (walkable(x, y) && !occupied(x, y) && ground[at(x, y)] !== WATER) return [x, y];
  }
  return [30, 25];
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
    await WORLD.promise;                     // 막는 칸이 다 정해진 뒤 시작 자리를 고른다
    const [sx, sy] = S.me ? [S.me.tx, S.me.ty] : spawn();
    const res = await post("/plaza/api/join", { name: S.name, look: S.look, face: S.face || storedFace(), x: sx, y: sy, status: S.status });
    S.id = res.id; S.face = res.face || S.face; S.role = res.role || "member";
    // 같은 PC 의 다른 대시보드 창이 이미 이 캐릭터로 들어와 있으면(shared) 그 자리에서 시작 — 한 PC 에 캐릭터 하나
    const jx = res.shared ? res.x : sx, jy = res.shared ? res.y : sy;
    if (!S.me) S.me = newActor({ id: res.id, name: res.name, face: S.face, role: S.role, x: jx, y: jy, dir: res.dir || 0 });
    else if (res.shared) { S.me.tx = jx; S.me.ty = jy; S.me.x = jx * T; S.me.y = jy * T; S.me.moving = false; }
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
  S.lastMove = performance.now();
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
      // 같은 캐릭터를 다른 창에서 움직였으면(이 창에서 1초 넘게 안 움직임) 서버 자리를 따름
      if (!S.me.moving && tnow - (S.lastMove || 0) > 1000 && (p.x !== S.me.tx || p.y !== S.me.ty)) {
        S.me.tx = p.x; S.me.ty = p.y; S.me.x = p.x * T; S.me.y = p.y * T; S.me.dir = p.dir; }
      S.me.status = p.status || "";
      S.me.hp = p.hp ?? 100; S.me.hpMax = p.hp_max || 100; S.me.ghost = !!p.ghost; S.me.kills = p.kills || 0; S.me.killer = !!p.killer;
      continue;
    }
    let a = S.others.get(p.id);
    if (!a) { a = newActor(p); S.others.set(p.id, a); }
    a.name = p.name; a.face = p.face || null; a.role = p.role || "member"; a.status = p.status || "";
    a.hp = p.hp ?? 100; a.hpMax = p.hp_max || 100; a.ghost = !!p.ghost; a.kills = p.kills || 0; a.killer = !!p.killer;
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
  $("#pz-online").textContent = `접속 ${s.online}명` + (S.me ? (S.me.ghost ? " · 나는 유령 (주간 마감 때 부활)" : ` · 내 체력 ${S.me.hp}/${S.me.hpMax}`) : "");
  const who = $("#pz-who"); who.textContent = "";
  const b = document.createElement("b"); b.textContent = "광장에 있는 사람"; who.append(b);
  const order = { leader: 0, unit: 1, member: 2, operator: 3 };
  for (const p of [...s.players].sort((u, v) => (order[u.role] ?? 2) - (order[v.role] ?? 2))) {
    const d = document.createElement("div");
    if (ROLE_LABEL[p.role]) { const t = document.createElement("span"); t.className = "role " + p.role; t.textContent = ROLE_LABEL[p.role]; d.append(t); }
    if (p.killer) { const t = document.createElement("span"); t.className = "role killer"; t.textContent = `killer ${p.kills}`; d.append(t); }
    d.append(document.createTextNode(p.name + (p.id === S.id ? " (나)" : "") + (p.ghost ? " [유령]" : "") + (p.status ? ` (${p.status})` : "")));
    if (p.kills) d.style.color = killColor(p.kills);
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
// 처치 수 (2026-10-19): 1명부터 이름이 붉어지고 많이 쓰러뜨릴수록 짙은 붉은색 (10명 이상 가장 짙음) · 3명부터 [killer n]
function killColor(k) {
  const t = Math.min(1, Math.max(0, (k - 1) / 9)), stops = [[255, 125, 125], [255, 35, 35], [170, 0, 0]];   // 연분홍 → 새빨강 → 짙은 붉은색
  const [a, b, u] = t < .5 ? [stops[0], stops[1], t * 2] : [stops[1], stops[2], (t - .5) * 2];
  return "#" + a.map((v, i) => Math.round(v + (b[i] - v) * u).toString(16).padStart(2, "0")).join("");
}
function nameTag(g, cx, y, a, mine) {       // [killer n] [그룹장] 이름 — 칭호는 역할 색
  g.font = `bold 12px ${FONT}`; g.textBaseline = "top"; g.textAlign = "left"; g.lineWidth = 3; g.strokeStyle = "#111";
  const kt = a.killer ? `[killer ${a.kills}] ` : "", title = ROLE_LABEL[a.role] ? `[${ROLE_LABEL[a.role]}] ` : "";
  const kw = g.measureText(kt).width, tw = g.measureText(title).width, nw = g.measureText(a.name).width, x0 = Math.round(cx - (kw + tw + nw) / 2);
  const kc = a.kills ? killColor(a.kills) : null;
  if (a.killer) { g.save(); g.shadowColor = "rgba(255,0,0,.75)"; g.shadowBlur = 6; }      // killer — 붉은 빛무리
  if (kt) { g.strokeText(kt, x0, y); g.fillStyle = "#ff3030"; g.fillText(kt, x0, y); }
  if (title) { g.strokeText(title, x0 + kw, y); g.fillStyle = ROLE_COLOR[a.role]; g.fillText(title, x0 + kw, y); }
  g.strokeText(a.name, x0 + kw + tw, y); g.fillStyle = kc || (mine ? "#ffe066" : "#ffffff"); g.fillText(a.name, x0 + kw + tw, y);
  if (a.killer) g.restore();
}

function hpBar(g, cx, y, a) {               // 이름 밑 체력 막대 (100) — 유령이면 '유령'
  if (a.ghost) { g.font = `bold 11px ${FONT}`; g.textBaseline = "top"; g.textAlign = "center"; g.lineWidth = 3; g.strokeStyle = "#111";
    g.strokeText("유령", cx, y); g.fillStyle = "#cfe3ff"; g.fillText("유령", cx, y); g.textAlign = "left"; return; }
  const w = 32, k = Math.max(0, Math.min(1, a.hp / (a.hpMax || 100))), x = Math.round(cx - w / 2);
  g.fillStyle = "#111"; g.fillRect(x - 1, y - 1, w + 2, 6);
  g.fillStyle = "#4a1410"; g.fillRect(x, y, w, 4);
  g.fillStyle = k > .5 ? "#4cd964" : k > .2 ? "#ffcc33" : "#ff4b3a"; g.fillRect(x, y, Math.max(k > 0 ? 1 : 0, Math.round(w * k)), 4);
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
  const F = roleFace(faceOf(a), a.role);
  if (a.ghost) {                             // 유령 — 그림자 없이 반투명하게 둥둥
    const base = isCat(F) ? catSprite(F, catPose({ dir: a.dir }, now, -1, -1)[0], false) : isChr(F) ? chrSprite(KIND_FR[F.kind].d[0], false) : charSprite(F, a.role, a.dir, 0);
    const spr = ghostly(base), bob = Math.round(Math.sin(now / 420 + a.x * .01) * 2) - 3;
    g.save(); g.globalAlpha = .5; g.drawImage(spr, Math.round(sx + 16 - (base.cx ?? spr.width / 2)), sy + 28 - (base.foot ?? FOOT) + bob); g.restore();
    return;
  }
  if (isChr(F)) {                            // 마을 시트 캐릭터 — 대기 칸 번갈아 · 걷기 칸 · 옆 칸 · 공격 칸
    drawAura(g, sx + 16, sy + 28, a.role, now, hash(a.name) % 7);
    ell(g, sx + 16, sy + 28, 12, 4, "rgba(40,20,5,.3)");
    const K = KIND_FR[F.kind], [nm, mir] = chrPose(K, a, now, atk, hash(a.name) % 650), spr = chrSprite(nm, mir);
    const bob = a.moving && a.dir < 2 && fr ? -PX : 0;
    if (atk >= 0 && !K.a && a.dir === 1) drawSwing(g, sx + ox, sy + oy, a.dir, atk);
    g.drawImage(hit >= 0 && hit < .6 && Math.floor(hit * 12) % 2 === 0 ? tinted(spr) : spr, Math.round(sx + 16 - spr.cx + ox), sy + 28 - spr.foot + oy + bob);
    if (atk >= 0 && !K.a && a.dir !== 1) drawSwing(g, sx + ox, sy + oy, a.dir, atk);   // 공격 칸이 없는 노비는 예전 휘두르기
    return;
  }
  if (isCat(F)) {                            // 고양이 기사 — 시트의 포즈 (서기 · 걷기 · 공격 · 피격)
    drawAura(g, sx + 16, sy + 28, a.role, now, hash(a.name) % 7);
    ell(g, sx + 16, sy + 28, 13, 5, "rgba(40,20,5,.3)");
    const side = a.dir >= 2, [nm, mir] = catPose(a, now, atk, hit), spr = catSprite(F, nm, mir);
    let bob = 0;
    if (a.moving && !side) bob = fr ? -PX : 0;                                          // 위 · 아래로 걸을 때 한 점 들썩
    else if (!a.moving && atk < 0) bob = Math.floor((now + (hash(a.name) % 1600)) / 800) % 2 ? -PX : 0;   // 서 있을 때 숨쉬기 (한 점)
    if (atk >= 0 && a.dir === 1) drawSwing(g, sx + ox, sy + oy, a.dir, atk, true);
    g.drawImage(nm !== "hurt" && hit >= 0 && hit < .6 && Math.floor(hit * 12) % 2 === 0 ? tinted(spr) : spr,
                Math.round(sx + 16 - spr.cx + ox), sy + 28 - spr.foot + oy + bob);
    if (atk >= 0 && a.dir === 0) drawSwing(g, sx + ox, sy + oy, a.dir, atk, true);    // 옆 공격은 시트의 칼바람 칸이 그림
    return;
  }
  drawAura(g, sx + 16, sy + 28, a.role, now, hash(a.name) % 7);
  ell(g, sx + 16, sy + 28, 14, 5, "rgba(40,20,5,.3)");
  if (atk >= 0 && a.dir === 1) drawSwing(g, sx + ox, sy + oy, a.dir, atk);
  const spr = charSprite(F, a.role, a.dir, atk >= 0 ? 0 : fr, atk < 0);   // 휘두를 때는 손의 목검 대신 drawSwing
  g.drawImage(hit >= 0 && hit < .6 && Math.floor(hit * 12) % 2 === 0 ? tinted(spr) : spr,
              sx + 16 - spr.width / 2 + ox, sy + 28 - FOOT - (fr && atk < 0 ? 1 : 0) + oy);
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
  S.cam = [cx, cy];                          // 캐릭터 누르기(actorAt)에 씀
  ctx.fillStyle = "#3a2414"; ctx.fillRect(0, 0, vw, vh);
  ctx.drawImage(groundImg, -cx, -cy);
  const actors = [S.me, ...S.others.values()];
  const items = [];
  for (const p of props) if (p.x - cx < vw + 40 && p.x + p.img.width - cx > -40 && p.y - cy > -10 && p.y - p.img.height - cy < vh + 10) items.push({ y: p.z ?? p.y, p });
  for (const a of actors) items.push({ y: a.y + 28, a });
  items.sort((u, v) => u.y - v.y);
  for (const it of items) {
    if (it.p) {
      const p = it.p, mx = S.me.x + 16, my = S.me.y + 28;    // 건물 · 큰 좌판 뒤에 내가 서면 반투명하게 (가려도 보이게)
      const behind = p.fade && mx > p.x + 6 && mx < p.x + p.img.width - 6 && my < p.y - 4 && my > p.y - p.img.height + 24;
      if (behind) { ctx.save(); ctx.globalAlpha = .55; }
      ctx.drawImage(p.img, Math.round(p.x - cx), Math.round(p.y - p.img.height - cy));
      if (behind) ctx.restore();
      continue;
    }
    drawActor(ctx, it.a, Math.round(it.a.x - cx), Math.round(it.a.y - cy), now);
  }
  const boxes = [];
  for (const a of actors) {                 // 이름 · 말풍선은 맨 위
    const sx = Math.round(a.x - cx) + 16, sy = Math.round(a.y - cy);
    nameTag(ctx, sx, sy + 32, a, a === S.me);
    hpBar(ctx, sx, sy + 48, a);
    if (a.status) statusTag(ctx, sx, sy + 28 - HEAD_PX - 14, a.status);     // 머리 위 — '(주간업무보고 중...)' 등
    if (a.bubble && now < a.bubble.until) boxes.push(bubbleBox(ctx, sx, sy + 28 - HEAD_PX + 2 - (a.status ? 16 : 0), a.name, a.bubble.text));   // 상태가 있으면 말풍선을 그 위로
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
}
function closeFace() { $("#pz-face").hidden = true; S.panel = false; draft = null; cv.focus(); }
const CAT_ROWS = [["fur", "동물 · 털", FURS], ["armor", "갑옷", ARMORS], ["cape", "망토", CAPES]];
function faceNote() {
  const RK = roleFace(draft, S.role).kind;
  if (RK >= 2) { $("#pz-face-note").textContent = RK === 6 ? "운영자는 노비 — 마을 시트의 노비(평민) 그대로입니다." : `${KINDS[RK]} — 마을 시트의 캐릭터 그대로입니다 (색은 고르지 않음).` + (S.role === "leader" ? " 그룹장 금빛 후광." : S.role === "unit" ? " 유닛장 은빛 후광." : ""); return; }
  $("#pz-face-note").textContent = isCat(draft) ? (S.role === "leader" ? "그룹장 — 황금 갑옷에 금빛 후광이 나옵니다. 동물(털) · 망토를 고릅니다."
      : S.role === "unit" ? "유닛장 — 은색(백은) 갑옷에 은빛 후광이 나옵니다. 동물(털) · 망토를 고릅니다."
      : "고양이 기사 — 동물(털) · 갑옷 · 망토 색을 고릅니다. 황금 검은 그대로. 칭호(그룹장 · 유닛장 · 운영자)는 이름 앞에 나옵니다.")
    : S.role === "operator" ? "운영자는 노비 차림 — 머리는 늘 산발에 흰 머리띠, 옷은 기운 누더기에 짚신입니다 (머리 모양 · 옷 색 · 바지 색은 안 씀)."
    : S.role === "leader" ? "그룹장은 왕관을 쓰고 금빛 후광이 나옵니다." : S.role === "unit" ? "유닛장은 날개 달린 관모(사모)를 쓰고 은빛 후광이 나옵니다." : "부서원은 관모를 씁니다.";
}
function arrowRow(k, label, list, skip) {   // ◀ 값 ▶ (skip(i) 이 참인 값은 건너뜀)
  const row = document.createElement("div"); row.className = "frow";
  const l = document.createElement("label"); l.textContent = label; row.append(l);
  const prev = document.createElement("button"), next = document.createElement("button"), v = document.createElement("span");
  prev.type = next.type = "button"; prev.textContent = "◀"; next.textContent = "▶"; v.className = "fval"; v.textContent = list[draft[k]];
  const go = d => { let i = draft[k]; do i = (i + d + list.length) % list.length; while (skip && skip(i) && i !== draft[k]); draft[k] = i; buildFace(); };
  prev.onclick = () => go(-1); next.onclick = () => go(1);
  row.append(prev, v, next); return row;
}
function kindRow() {                       // 종류 — 운영자는 노비로 고정, 다른 사람은 노비를 못 고름
  if (S.role === "operator") { const row = document.createElement("div"); row.className = "frow"; const l = document.createElement("label"); l.textContent = "종류";
    const v = document.createElement("span"); v.className = "fval"; v.textContent = "노비 (운영자)"; row.append(l, v); return row; }
  return arrowRow("kind", "종류", KINDS, i => i === 6);
}
function buildFace() {
  faceNote();
  const RF = roleFace(draft, S.role);
  if (isChr(RF) || (RF.kind >= 2 && KIND_FR[RF.kind])) {   // 마을 시트 캐릭터 — 고를 것은 종류뿐
    $("#pz-hairs").hidden = true; $("#pz-hairs").previousElementSibling.hidden = true;
    const rows = $("#pz-facerows"); rows.textContent = ""; rows.append(kindRow()); return;
  }
  const cat = isCat(draft);
  $("#pz-hairs").hidden = cat; $("#pz-hairs").previousElementSibling.hidden = cat;   // '머리 모양' 은 사람일 때만
  if (cat) { const rows = $("#pz-facerows"); rows.textContent = ""; rows.append(kindRow());
    for (const [k, label, list] of CAT_ROWS) {
      if (k === "armor" && S.role in ROLE_ARMOR) {   // 그룹장 · 유닛장 — 역할 갑옷 (고를 수 없음)
        const row = document.createElement("div"); row.className = "frow"; const l = document.createElement("label"); l.textContent = label;
        const v = document.createElement("span"); v.className = "fval"; v.textContent = `${ARMORS[ROLE_ARMOR[S.role]]} (${ROLE_LABEL[S.role]})`; row.append(l, v); rows.append(row); continue;
      }
      rows.append(arrowRow(k, label, list));
    }
    return; }
  const grid = $("#pz-hairs"); grid.textContent = "";
  HAIRS.forEach((nm, i) => {               // 머리 모양 — 대가리 고르기
    const b = document.createElement("button"); b.type = "button"; b.className = "hairbtn" + (draft.hair === i ? " on" : "");
    const c = canvas(48, 48), g = c.getContext("2d"); g.imageSmoothingEnabled = false;
    const spr = charSprite({ ...draft, hair: i }, "bare", 0, 0);
    g.drawImage(spr, 0, 0, spr.width, (OY + 17) * PX, 0, 2, 48, (OY + 17) * PX * 48 / spr.width);
    const l = document.createElement("span"); l.textContent = nm;
    b.append(c, l); b.onclick = () => { draft.hair = i; buildFace(); };
    grid.append(b);
  });
  const rows = $("#pz-facerows"); rows.textContent = "";
  rows.append(kindRow());
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
  ell(g, c.width / 2, c.height - 22, 30, 8, "rgba(40,20,5,.3)");
  const RF = roleFace(draft, S.role);
  if (isChr(RF)) {                           // 마을 시트 캐릭터 — 시트 맨 위의 큰 그림
    const spr = chrSprite(KIND_FR[RF.kind].p, false);
    g.drawImage(spr, Math.round(c.width / 2 - spr.cx), Math.round(c.height - 22 - spr.foot));
    return;
  }
  if (isCat(draft)) {                        // 고양이 기사 — 아래 · 왼쪽 걷기 · 위 · 오른쪽 걷기 를 돌려 보임 (2배)
    const [nm, mir] = catPose({ dir, moving: dir >= 2 }, now, -1, -1), spr = catSprite(roleFace(draft, S.role), nm, mir), z = 2;
    g.drawImage(spr, Math.round(c.width / 2 - spr.cx * z), Math.round(c.height - 22 - spr.foot * z), spr.width * z, spr.height * z);
    return;
  }
  const spr = charSprite(draft, S.role, dir, fr === 1 ? 1 : fr === 3 ? 2 : 0, true), z = 2;
  g.drawImage(spr, Math.round(c.width / 2 - spr.width * z / 2), Math.round(c.height - 22 - FOOT * z), spr.width * z, spr.height * z);
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
$("#pz-face-rand").onclick = () => { for (const k of Object.keys(RANGES)) if (k !== "kind") draft[k] = Math.floor(Math.random() * RANGES[k]); buildFace(); };   // 종류(고양이 · 사람)는 그대로

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
  if (S.me.ghost) { if (now - (S.ghostNote || 0) > 4000) { S.ghostNote = now; localNote("유령은 공격할 수 없습니다 — 주간 마감 때 체력 100 으로 부활합니다."); } return; }
  S.me.attack = now;
  post("/plaza/api/attack", { id: S.id }).catch(e => { if (e.status === 404) join().catch(() => {}); });
}
function localNote(text) {                  // 대화창에 나만 보는 안내 한 줄
  const log = $("#pz-log"), d = document.createElement("div"); d.className = "sys"; d.textContent = text;
  log.append(d); while (log.childElementCount > 40) log.firstElementChild.remove(); log.scrollTop = log.scrollHeight;
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

// ── 캐릭터 누르기 → [캐릭터 정보] (2026-10-16 대시보드) ─────────────────────
// 대시보드 카드 안이면 대시보드(부모 창)에 이름을 알려 그 부서원 정보 창(사진 · 전화 · 담당 업무 · PJT · 업무 요약)을 연다.
// 이름 · 상태는 글자로만 넣는다 (textContent — README §5 규칙 1)
function actorAt(px, py) {
  if (!S.cam || !S.me) return null;
  const [cx, cy] = S.cam; let best = null, bd = 1e9;
  for (const a of [S.me, ...S.others.values()]) {
    const sx = a.x - cx, sy = a.y - cy;                       // 몸 + 이름표 자리
    if (px >= sx - 4 && px <= sx + T + 4 && py >= sy + 28 - HEAD_PX && py <= sy + 54) {
      const d = Math.hypot(px - sx - T / 2, py - sy); if (d < bd) { bd = d; best = a; }
    }
  }
  return best;
}
const ctxMenu = document.createElement("div"); ctxMenu.className = "pz-ctx"; ctxMenu.hidden = true; $("#pz").append(ctxMenu);
function hideCtx() { ctxMenu.hidden = true; }
function showCtx(a, x, y) {
  ctxMenu.textContent = "";
  const t = document.createElement("b");
  t.textContent = (ROLE_LABEL[a.role] ? `[${ROLE_LABEL[a.role]}] ` : "") + a.name + (a === S.me ? " (나)" : "");
  ctxMenu.append(t);
  if (a.status) { const st = document.createElement("small"); st.textContent = a.status; ctxMenu.append(st); }
  const hp = document.createElement("small"); hp.textContent = (a.ghost ? "유령 (주간 마감 때 부활)" : `체력 ${a.hp}/${a.hpMax}`) + (a.kills ? ` · 이번 주 ${a.kills}명 처치${a.killer ? " (killer)" : ""}` : ""); ctxMenu.append(hp);
  const btn = document.createElement("button"); btn.type = "button"; btn.textContent = "캐릭터 정보";
  btn.onclick = () => { hideCtx(); cv.focus();
    if (window.parent !== window) window.parent.postMessage({ type: "plaza-profile", name: a.name }, "*");
    else { const n = document.createElement("small"); n.textContent = "대시보드 안에서 열면 부서원 정보를 볼 수 있습니다"; ctxMenu.textContent = ""; ctxMenu.append(n); ctxMenu.hidden = false; setTimeout(hideCtx, 2500); } };
  ctxMenu.append(btn); ctxMenu.hidden = false;
  const box = $("#pz").getBoundingClientRect(), w = ctxMenu.offsetWidth, h = ctxMenu.offsetHeight;
  ctxMenu.style.left = Math.max(6, Math.min(x + 8, box.width - w - 6)) + "px";
  ctxMenu.style.top = Math.max(6, Math.min(y + 8, box.height - h - 6)) + "px";
}
cv.addEventListener("click", ev => {
  const r = cv.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top, a = actorAt(x, y);
  if (a) showCtx(a, x, y); else hideCtx();
});
document.addEventListener("keydown", ev => { if (ev.key === "Escape") hideCtx(); }, true);
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
window.__plazaDebug = { charSprite, defaultFace, RANGES, catSprite, CAT, solid, ground, W, H, props, WORLD };
if (EMBED) document.body.classList.add("embed");
resize(); requestAnimationFrame(frame);
const nm = (Q.get("user") || "").trim() || storedName();
if (nm) start(nm); else askName();
})();
