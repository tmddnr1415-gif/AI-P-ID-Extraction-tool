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
const FRAME = 14;                           // 화면 둘레 철골 틀 두께
const PLACE = "EPC 발전플랜트 현장";
const $ = s => document.querySelector(s);
const Q = new URLSearchParams(location.search);
const EMBED = Q.get("embed") === "1";

// ── 씨앗 있는 난수 (지도는 누구에게나 같다) ─────────────────────────────
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0;
  let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
  return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function hash(s) { let h = 2166136261; for (const ch of String(s)) { h ^= ch.codePointAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }

// ── 지도: EPC 발전플랜트 현장 (2026-10-22) ──────────────────────────────────────────────
// 위(북) 주 발전동(터빈 홀 · 발전기동 · 연돌) · 공정/유틸리티(펌프 · 열교환기 · 냉각탑) → 배관랙 통로 → 가운데 동서 큰길
// 아래(남) 전기/계장(변전 · MCC · 마샬링) · 중앙 제어실 · 시운전 구역 · 정비동 → 현장 사무소 · 물류 야적장 · 주차 · 정문.
// 땅 종류와 막는 칸은 칸(32px) 단위 — 이동 · 충돌 · 경로 찾기는 이것만 본다. 그림은 buildWorld 가 처음 한 번 그린다.
// 좌표: 칸 (x, y) · 월드 px = 칸 × T · 화면 px = 월드 px − 카메라(S.cam).  그림 한 점 = PX(2)px.
const GRAV = 0, CONC = 1, ASPH = 2, GRAT = 3, GRASS = 4, EPOXY = 5;
const ground = new Uint8Array(W * H), solid = new Uint8Array(W * H);
const at = (x, y) => y * W + x;
const inside = (x, y) => x >= 0 && y >= 0 && x < W && y < H;
function fill(t, x0, y0, x1, y1) { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (inside(x, y)) ground[at(x, y)] = t; }
function block(x0, y0, x1, y1) { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (inside(x, y)) solid[at(x, y)] = 1; }
function unblock(x0, y0, x1, y1) { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (inside(x, y)) solid[at(x, y)] = 0; }
const props = [];                           // {img, x, y(바닥 px), z(정렬), fade(뒤에 서면 반투명), anim(g, sx, sy, now)}

fill(GRAV, 0, 0, W - 1, H - 1);             // 야적장 자갈
fill(GRASS, 0, 0, W - 1, 1); fill(GRASS, 0, 0, 1, H - 1); fill(GRASS, W - 2, 0, W - 1, H - 1); fill(GRASS, 0, 42, W - 1, H - 1);   // 둘레 녹지
fill(CONC, 2, 2, 29, 11);                   // A 주 발전동 마당
fill(CONC, 33, 2, 61, 11);                  // B 공정 · 유틸리티
fill(GRAT, 2, 12, 61, 14);                  // C 배관랙 밑 그레이팅 통로
fill(CONC, 2, 15, 61, 16);                  //   랙 앞 보도
fill(ASPH, 2, 20, 61, 21);                  // 동서 큰길
fill(ASPH, 30, 15, 31, 41);                 // 남북 큰길 (정문까지)
fill(CONC, 2, 22, 61, 22);                  // 큰길 남쪽 보도
fill(GRAV, 3, 23, 11, 30);                  // D 변전 (울타리 안 자갈)
fill(CONC, 12, 23, 18, 31);                 //   MCC · 마샬링
fill(CONC, 19, 23, 29, 32); fill(EPOXY, 20, 24, 28, 31);   // E 중앙 제어실 (지붕을 걷어낸 단면)
fill(CONC, 33, 23, 47, 31);                 // F 시운전 구역
fill(CONC, 48, 23, 61, 31);                 // G 정비동
fill(CONC, 33, 33, 61, 35);                 // H 현장 사무소 · 컨테이너 앞
fill(ASPH, 3, 35, 15, 40);                  //   주차장
fill(CONC, 18, 34, 27, 39);                 //   쉼터
fill(ASPH, 26, 40, 35, 41);                 //   정문 앞

block(0, 0, W - 1, 1); block(0, 0, 1, H - 1); block(W - 2, 0, W - 1, H - 1); block(0, 42, W - 1, H - 1);   // 둘레 울타리 · 녹지

// ── 그림 도구 ───────────────────────────────────────────────────────────
function canvas(w, h) { const c = document.createElement("canvas"); c.width = w; c.height = h; return c; }
function shade(hex, k) {                    // k<0 어둡게 · k>0 밝게
  const n = parseInt(hex.slice(1), 16), f = v => Math.max(0, Math.min(255, Math.round(k < 0 ? v * (1 + k) : v + (255 - v) * k)));
  return "#" + [n >> 16 & 255, n >> 8 & 255, n & 255].map(v => f(v).toString(16).padStart(2, "0")).join("");
}
function ell(g, x, y, rx, ry, c) { g.fillStyle = c; g.beginPath(); g.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2); g.fill(); }
// 값 잡음 (부드러운 난수 면) — 땅 무늬를 섞어 넓은 단색 · 되풀이 무늬를 줄임
function vnoise(x, y, seed) {
  const xi = Math.floor(x), yi = Math.floor(y), fx = x - xi, fy = y - yi, sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
  const v = (a, b) => (hash(`${a},${b},${seed}`) & 1023) / 1023;
  return (v(xi, yi) * (1 - sx) + v(xi + 1, yi) * sx) * (1 - sy) + (v(xi, yi + 1) * (1 - sx) + v(xi + 1, yi + 1) * sx) * sy;
}

// 산업 팔레트
const C = { navy: "#141c2b", navy2: "#1e2a40", steel: "#3d5a7a", steelL: "#5f82a6", steelD: "#2a3d55", gray: "#7d8794", grayL: "#a8b2bc", grayD: "#565e69",
  pipe: "#b9c3cc", pipeL: "#e6edf2", pipeD: "#7b8794", yel: "#f2c230", yelD: "#b88a12", org: "#e8752a", orgD: "#a94d16", grn: "#43c46a", grnD: "#23803f",
  red: "#e0443a", redD: "#98231d", white: "#e8eef2", glass: "#26445e", glassL: "#5d93b8", conc: "#8a929c", concD: "#646c76", ol: "#0b111c" };

// 점 그림: draw(R) 로 한 점 = 1 칸에 칠한 뒤 → (외곽선) → PX 배 (흐리지 않게).  돌려주는 canvas: .foot = 그림 위에서 바닥까지 px
// labels: 다 키운 뒤 또렷한 글씨 [{t, x, y, s, c}] (점 좌표)
function pix(w, h, draw, { ol = C.ol, labels = [] } = {}) {
  const c = canvas(w + 2, h + 2), g = c.getContext("2d", { willReadFrequently: true });
  const R = (x, y, ww, hh, col) => { if (ww <= 0 || hh <= 0) return; g.fillStyle = col; g.fillRect(Math.round(x) + 1, Math.round(y) + 1, Math.round(ww), Math.round(hh)); };
  R.disc = (cx, cy, rx, ry, col) => { for (let y = Math.floor(-ry); y <= Math.ceil(ry); y++) for (let x = Math.floor(-rx); x <= Math.ceil(rx); x++)
    if ((x / rx) ** 2 + (y / ry) ** 2 <= 1) R(cx + x, cy + y, 1, 1, col); };
  R.line = (x0, y0, x1, y1, col, t = 1) => { const n = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0)) || 1;
    for (let i = 0; i <= n; i++) R(Math.round(x0 + (x1 - x0) * i / n), Math.round(y0 + (y1 - y0) * i / n), t, t, col); };
  draw(R);
  if (ol) {
    const d = g.getImageData(0, 0, c.width, c.height), o = new Uint8ClampedArray(d.data), wd = c.width, hd = c.height;
    const [orr, og, ob] = [parseInt(ol.slice(1, 3), 16), parseInt(ol.slice(3, 5), 16), parseInt(ol.slice(5, 7), 16)];
    for (let y = 0; y < hd; y++) for (let x = 0; x < wd; x++) { const i = (y * wd + x) * 4; if (d.data[i + 3]) continue;
      if ((x > 0 && d.data[i - 1]) || (x < wd - 1 && d.data[i + 7]) || (y > 0 && d.data[i - wd * 4 + 3]) || (y < hd - 1 && d.data[i + wd * 4 + 3])) { o[i] = orr; o[i + 1] = og; o[i + 2] = ob; o[i + 3] = 255; } }
    g.putImageData(new ImageData(o, wd, hd), 0, 0);
  }
  const big = canvas(c.width * PX, c.height * PX), bg = big.getContext("2d"); bg.imageSmoothingEnabled = false; bg.drawImage(c, 0, 0, big.width, big.height);
  for (const L of labels) { bg.font = `bold ${L.s || 10}px ${FONT}`; bg.textAlign = "center"; bg.textBaseline = "middle"; bg.fillStyle = L.c || C.white; bg.fillText(L.t, (L.x + 1) * PX, (L.y + 1) * PX); }
  big.foot = (h + 1) * PX; return big;
}
const hz = (R, x, y, w, h) => { for (let i = 0; i < w; i++) R(x + i, y, 1, h, Math.floor((i + y) / 3) % 2 ? C.yel : "#1a1a1a"); };   // 노랑 · 검정 빗금 띠
function ribs(R, x, y, w, h, col, step = 4) { for (let i = x + 1; i < x + w; i += step) R(i, y, 1, h, col); }

// ── 건물 (지붕 + 앞 벽) — 탑다운 3/4 시점, 빛은 왼쪽 위 ───────────────────────
function building({ w, roofH, wallH, roof = C.steel, wall = "#8e9aa7", doors = [], wins = [], sign, vents = [], louver = [] }) {
  const lab = sign ? [{ t: sign.t, x: sign.x + sign.w / 2, y: roofH + sign.y + sign.h / 2, s: sign.s || 10, c: "#e9f2ff" }] : [];
  return pix(w, roofH + wallH, R => {
    R(0, 0, w, roofH, roof); ribs(R, 0, 2, w, roofH - 4, shade(roof, -.18));   // 골강판 지붕
    R(0, 0, w, 2, shade(roof, .25)); R(0, roofH - 3, w, 3, shade(roof, -.35)); R(0, 2, 2, roofH - 5, shade(roof, .12));
    for (const v of vents) { R(v.x, v.y, v.w, v.h, C.grayD); R(v.x + 1, v.y + 1, v.w - 2, v.h - 3, C.gray); R(v.x + 1, v.y + 1, v.w - 2, 1, C.grayL); }
    R(0, roofH, w, wallH, wall); for (let y = roofH + 2; y < roofH + wallH - 4; y += 3) R(0, y, w, 1, shade(wall, -.08));   // 가로 골 외장판
    R(0, roofH, w, 2, shade(wall, -.3)); R(0, roofH + wallH - 4, w, 4, C.concD); R(0, roofH + wallH - 4, w, 1, C.conc);
    R(0, roofH, 1, wallH, shade(wall, .15)); R(w - 2, roofH, 2, wallH, shade(wall, -.25));
    for (const L of louver) { R(L.x, roofH + L.y, L.w, L.h, C.grayD); for (let y = 1; y < L.h; y += 2) R(L.x + 1, roofH + L.y + y, L.w - 2, 1, C.grayL); }
    for (const q of wins) { R(q.x, roofH + q.y, q.w, q.h, C.glass); R(q.x, roofH + q.y, q.w, 1, C.glassL); R(q.x + 1, roofH + q.y + 1, 2, q.h - 2, C.glassL);
      R(q.x - 1, roofH + q.y + q.h, q.w + 2, 1, C.grayL); }
    for (const d of doors) {
      const y = roofH + wallH - 4 - d.h;
      if (d.roll) { hz(R, d.x - 2, y - 2, d.w + 4, 2); R(d.x - 2, y, 2, d.h, C.yel); R(d.x + d.w, y, 2, d.h, C.yel);
        R(d.x, y, d.w, d.h, "#7a8592"); for (let i = y + 1; i < y + d.h; i += 2) R(d.x, i, d.w, 1, "#5f6a77"); }
      else { R(d.x, y, d.w, d.h, d.c || "#2f4f78"); R(d.x + 1, y + 1, d.w - 2, 4, C.glassL); R(d.x + d.w - 3, y + d.h / 2, 1, 2, C.yel); }
    }
    if (sign) { R(sign.x, roofH + sign.y, sign.w, sign.h, C.navy2); R(sign.x, roofH + sign.y, sign.w, 1, C.steelL); }
  }, { labels: lab });
}
// ── 굴뚝 (연돌) · 냉각탑 · 펌프 · 열교환기 · 배관랙 ─────────────────────────────
function stackImg() {
  return pix(28, 128, R => {
    R(4, 10, 20, 114, C.gray); R(4, 10, 5, 114, C.grayL); R(19, 10, 5, 114, C.grayD);
    for (let y = 30; y < 120; y += 22) { R(3, y, 22, 2, C.steelD); }
    for (let k = 0; k < 4; k++) R(4, 10 + k * 4, 20, 2, k % 2 ? C.white : C.red);
    R(2, 6, 24, 5, C.grayD); R(5, 0, 18, 7, "#2a2f38"); R(6, 1, 16, 2, "#40464f");
    R(0, 56, 28, 3, C.yel); R(0, 59, 28, 1, C.yelD); for (let x = 1; x < 28; x += 4) R(x, 53, 1, 3, C.yel);
    R(2, 122, 24, 6, C.concD);
  });
}
function coolingImg() {                     // 기계 통풍식 냉각탑 2셀 (192 × 128 점) — 날개는 anim 이 돌림
  return pix(192, 128, R => {
    R(0, 74, 192, 50, "#55708f"); for (let y = 78; y < 120; y += 3) R(2, y, 188, 1, "#3c5470");   // 앞면 루버
    R(0, 74, 192, 2, "#7f9ab8"); R(0, 120, 192, 8, C.concD); R(0, 120, 192, 1, C.conc);
    for (const x of [64, 128]) R(x - 1, 74, 3, 46, "#2f4560");
    R(0, 10, 192, 64, "#6f7f92"); ribs(R, 0, 12, 192, 60, "#62717f", 6); R(0, 10, 192, 2, "#9aa8b8"); R(0, 70, 192, 4, "#4f5d6c");
    for (const cx of [48, 144]) { R.disc(cx, 38, 40, 30, "#4a5866"); R.disc(cx, 36, 38, 28, "#8796a6"); R.disc(cx, 36, 34, 24, "#1d2836"); R.disc(cx, 36, 30, 21, "#26364a"); }
    for (let x = 4; x < 188; x += 6) R(x, 4, 2, 6, C.yel); R(0, 4, 192, 1, C.yel);       // 위 난간
  });
}
function pumpImg() {                        // 펌프 스키드 (48 × 34): 노란 받침 · 파란 펌프 · 회색 모터
  return pix(48, 34, R => {
    R(0, 24, 48, 10, C.yelD); R(0, 24, 48, 2, C.yel); hz(R, 0, 32, 48, 2);
    R(3, 8, 18, 18, "#2f6db5"); R(3, 8, 18, 3, "#5d94d6"); R.disc(12, 17, 6, 6, "#1f4f8a"); R(10, 2, 5, 8, C.pipe); R(9, 0, 7, 3, C.pipeD);
    R(21, 14, 5, 8, C.yel); R(26, 9, 20, 16, C.gray); R(26, 9, 20, 3, C.grayL); for (let x = 28; x < 45; x += 3) R(x, 12, 1, 12, C.grayD);
    R(42, 20, 5, 4, C.grayD);
  });
}
function hxImg() {                          // 셸앤튜브 열교환기 (200 × 36)
  return pix(200, 36, R => {
    R(10, 4, 176, 24, "#c9d2da"); R(10, 4, 176, 5, "#eef3f6"); R(10, 22, 176, 6, "#97a3ad");
    for (let x = 30; x < 180; x += 36) R(x, 4, 2, 24, "#a7b2bb");
    R(0, 2, 12, 28, C.steel); R(0, 2, 12, 4, C.steelL); R(186, 6, 12, 20, "#aab5be");
    for (const x of [40, 150]) { R(x - 6, 26, 14, 8, C.steelD); R(x - 6, 26, 14, 2, C.steelL); }
    for (const x of [60, 120]) { R(x, 0, 8, 6, C.pipe); R(x - 1, 0, 10, 2, C.pipeD); }
  });
}
function pipeRackImg(wTiles, colsAt) {      // 배관랙 (여러 층 배관 · 케이블 트레이 · 철골) — colsAt = 기둥 칸 (랙 왼쪽 기준)
  const w = wTiles * 16;
  return pix(w, 66, R => {
    for (const c of colsAt) { R(c * 16 + 5, 14, 6, 34, C.steelD); }                       // 뒤 기둥 (한 칸 위)
    R(0, 0, w, 3, "#4f5965"); R(0, 3, w, 6, "#6d7782");                                   // 케이블 트레이 (위층)
    for (let x = 0; x < w; x += 5) R(x, 3, 1, 6, "#4a535e");
    for (let x = 0; x < w; x += 2) { R(x, 4, 1, 1, (x >> 3) % 3 ? "#1d232b" : C.org); R(x, 6, 1, 1, (x >> 2) % 4 ? "#262c35" : "#3d6fb0"); }
    const pipes = [[10, 5, C.pipe], [15, 4, "#3f9a5c"], [19, 5, C.yel], [24, 4, "#c63a33"], [28, 6, "#d9dde0"], [34, 4, "#4f7fb8"]];
    for (const [y, h, col] of pipes) { R(0, y, w, h, col); R(0, y, w, 1, shade(col, .35)); R(0, y + h - 1, w, 1, shade(col, -.35));
      for (let x = 23 + (y % 7) * 5; x < w; x += 70) R(x, y - 1, 2, h + 2, shade(col, -.45)); }
    for (let x = 0; x < w; x += 24) R(x, 28, 3, 6, "#c4cdd5");                               // 보온 밴드
    R(0, 38, w, 4, C.steel); R(0, 38, w, 1, C.steelL); R(0, 41, w, 1, C.steelD);             // 앞 보
    for (const c of colsAt) { R(c * 16 + 4, 38, 8, 28, C.steel); R(c * 16 + 4, 38, 2, 28, C.steelL); R(c * 16 + 10, 38, 2, 28, C.steelD); R(c * 16 + 2, 62, 12, 4, C.concD); }
    for (const c of colsAt.filter((_, i) => i % 3 === 1)) { for (let y = 10; y < 62; y += 3) R(c * 16 + 13, y, 4, 1, C.yel); R(c * 16 + 13, 10, 1, 52, C.yel); R(c * 16 + 16, 10, 1, 52, C.yel); }   // 사다리
  });
}
// ── 전기 · 계장 ───────────────────────────────────────────────────────────
function transformerImg() {                 // 주변압기 (48 × 50): 방열판 · 붓싱 · 콘서베이터
  return pix(48, 50, R => {
    R(2, 44, 44, 6, C.concD);
    R(0, 18, 8, 26, "#3d6a4a"); R(40, 18, 8, 26, "#3d6a4a"); for (let y = 19; y < 44; y += 2) { R(0, y, 8, 1, "#2c4f37"); R(40, y, 8, 1, "#2c4f37"); }
    R(8, 14, 32, 32, "#4c805a"); R(8, 14, 32, 4, "#6ea57b"); R(36, 14, 4, 32, "#35603f"); R(14, 26, 12, 8, "#2b2f36"); R(15, 27, 10, 3, C.yel);
    R(10, 6, 28, 8, "#5a8f67"); R(10, 6, 28, 2, "#7fb88b");
    for (const x of [13, 22, 31]) { for (let y = 0; y < 8; y += 2) R(x, y, 5, 1, "#d8dde2"); R(x + 1, 0, 3, 9, "#b9c1c9"); R(x + 1, 0, 3, 1, "#6b7480"); }
  });
}
function switchImg() {                      // 단로기 철구 (40 × 40)
  return pix(40, 40, R => {
    for (const x of [4, 32]) { R(x, 10, 4, 28, C.grayD); for (let y = 12; y < 36; y += 6) R.line(x, y, x + 3, y + 5, C.grayL); }
    R(2, 8, 36, 4, C.gray); R(2, 8, 36, 1, C.grayL);
    for (const x of [9, 18, 27]) { for (let y = 0; y < 8; y += 2) R(x, y, 4, 1, "#dfe3e7"); R(x + 1, 0, 2, 8, "#aab2ba"); }
    R(0, 36, 40, 4, C.concD);
  });
}
function fenceH(n) { const w = n * 16; return pix(w, 20, R => { R(0, 2, w, 1, "#9aa5b1"); R(0, 15, w, 1, "#77828e");
  for (let y = 3; y < 15; y++) for (let x = (y % 2); x < w; x += 2) R(x, y, 1, 1, "rgba(150,163,176,.55)");
  for (let x = 0; x < w; x += 16) { R(x, 0, 2, 20, "#6b7682"); R(x, 0, 2, 1, "#c3ccd5"); } }, { ol: null }); }
function fenceV(n) { const h = n * 16; return pix(6, h + 20, R => { R(2, 0, 2, h + 20, "#77828e"); for (let y = 0; y < h + 20; y += 16) R(1, y, 4, 4, "#6b7682"); }, { ol: null }); }
function cabinetImg(kind) {                 // 계장 · 전기 캐비닛 (DCS · IO · PLC · MC · MCC 판)
  const body = { DCS: "#26324a", IO: "#8a96a3", PLC: "#b9c2cb", MC: "#7f8b97", MCC: "#9aa5b0" }[kind] || "#8a96a3";
  return pix(18, 34, R => {
    R(0, 2, 18, 30, body); R(0, 2, 18, 2, shade(body, .3)); R(16, 4, 2, 28, shade(body, -.3)); R(8, 4, 1, 28, shade(body, -.35));
    R(1, 32, 16, 2, "#2a2f36");
    if (kind === "DCS") { for (let y = 6; y < 28; y += 5) { R(2, y, 5, 3, "#3b4a66"); R(10, y, 5, 3, "#3b4a66"); } R(2, 6, 2, 1, C.grn); }
    else if (kind === "IO") { for (let y = 6; y < 28; y += 4) { R(2, y, 14, 3, "#2a3a2f"); for (let x = 3; x < 15; x += 2) R(x, y, 1, 1, (x + y) % 3 ? C.grn : "#9bd18a"); } }
    else if (kind === "PLC") { R(2, 8, 14, 9, "#3f4a56"); for (let x = 3; x < 15; x += 3) R(x, 9, 2, 7, "#2b333c"); R(3, 10, 1, 1, C.grn); R(2, 20, 14, 6, "#c7cfd6"); }
    else { for (let y = 6; y < 30; y += 2) R(2, y, 14, 1, shade(body, -.15)); R(13, 15, 2, 4, C.yel); }
  });
}
function consoleImg() {                     // DCS 운전 콘솔 (34 × 26): 모니터 3 · 책상
  return pix(34, 26, R => {
    R(0, 14, 34, 10, "#3a4556"); R(0, 14, 34, 2, "#5c6a80"); R(2, 24, 30, 2, "#232a35");
    for (const x of [1, 12, 23]) { R(x, 1, 10, 9, "#1c2333"); R(x + 1, 2, 8, 6, "#14385c"); R(x + 1, 6, 8, 1, C.grn); R(x + 2, 4, 2, 1, C.yel); R(x + 5, 3, 3, 1, "#61b3ff");
      R(x + 4, 10, 2, 4, "#2a3140"); }
    R(10, 16, 14, 3, "#1c2230"); R(26, 16, 4, 3, "#1c2230");
  });
}
function chairImg() { return pix(12, 14, R => { R(1, 0, 10, 7, "#2b3a55"); R(1, 0, 10, 2, "#45597d"); R(0, 7, 12, 4, "#22304a"); R(5, 11, 2, 3, C.grayD); }); }
function jbImg() {                          // 정션 박스 (16 × 26): 노란 함 · 받침대 · 케이블 그랜드
  return pix(16, 26, R => {
    R(7, 14, 2, 12, C.grayD); R(4, 24, 8, 2, C.concD);
    R(1, 2, 14, 13, "#e0b52e"); R(1, 2, 14, 2, "#f4d36a"); R(13, 4, 2, 11, "#a57e14"); R(3, 6, 10, 1, "#a57e14");
    for (const x of [3, 7, 11]) R(x, 15, 2, 2, "#2b2f36"); R(3, 17, 1, 6, "#20242b"); R(11, 17, 1, 6, C.org);
  });
}
function trayImg() {                        // 케이블 트레이 점검 구간 (30 × 22)
  return pix(30, 22, R => {
    for (const x of [3, 25]) R(x, 8, 2, 14, C.steelD);
    R(0, 4, 30, 5, "#7a8591"); R(0, 4, 30, 1, "#a8b2bc"); for (let x = 1; x < 30; x += 3) R(x, 5, 1, 3, "#5c6672");
    for (let x = 0; x < 30; x += 1) { R(x, 2, 1, 2, x % 5 ? "#20252d" : C.org); }
    R(12, 0, 6, 4, C.yel);
  });
}
function xmtrImg(t) {                       // 계장 전송기 · 밸브 · 계기 (24 × 28 안팎) — t: PT DPT TT FT LT CV PG
  return pix(24, 30, R => {
    R(6, 27, 12, 3, C.concD);
    if (t === "CV") {                       // 제어밸브: 배관 · 글로브 몸통 · 요크 · 노란 다이어프램 · 포지셔너
      R(0, 20, 24, 5, C.pipe); R(0, 20, 24, 1, C.pipeL); R(0, 24, 24, 1, C.pipeD); R(2, 18, 2, 9, C.pipeD); R(20, 18, 2, 9, C.pipeD);
      R(8, 17, 8, 10, "#4f6f96"); R(8, 17, 8, 2, "#7393bb"); R(11, 9, 2, 8, C.grayL); R(9, 11, 1, 6, C.grayD); R(14, 11, 1, 6, C.grayD);
      R.disc(12, 6, 8, 4, C.yel); R(4, 6, 16, 2, C.yelD); R(16, 12, 6, 6, "#c9d0d6"); R(17, 13, 4, 2, "#3b4a66");
    } else if (t === "PG") {
      R(10, 18, 4, 10, C.pipeD); R.disc(12, 11, 8, 8, "#d9dee2"); R.disc(12, 11, 6, 6, C.white); R.line(12, 11, 16, 7, C.red); R(11, 10, 2, 2, "#222");
      for (let i = 0; i < 6; i++) R(Math.round(12 + Math.cos(Math.PI * (.8 + i * .28)) * 5), Math.round(11 + Math.sin(Math.PI * (.8 + i * .28)) * 5), 1, 1, "#555");
    } else if (t === "FT" || t === "TT") {  // 배관 위 계기
      R(0, 19, 24, 6, C.pipe); R(0, 19, 24, 1, C.pipeL); R(0, 24, 24, 1, C.pipeD);
      if (t === "FT") { R(6, 16, 12, 12, "#3e6fa8"); R(5, 16, 2, 12, C.pipeD); R(17, 16, 2, 12, C.pipeD); R(10, 9, 4, 7, C.grayD); }
      else { R(11, 12, 2, 7, C.grayL); }
      R(6, 2, 12, 9, "#5a87b8"); R(6, 2, 12, 2, "#86acd4"); R(8, 4, 8, 5, "#cfe8d6"); R(9, 5, 6, 1, "#2f5f3b");
    } else if (t === "LT") {                // 작은 용기 + 레이더 레벨
      R(4, 8, 16, 19, "#b6c0c9"); R(4, 8, 16, 3, "#dfe6eb"); R(17, 10, 3, 17, "#8a96a1"); R(5, 15, 10, 1, "#7e8a95");
      R(9, 2, 6, 6, "#5a87b8"); R(9, 2, 6, 2, "#86acd4"); R(11, 0, 2, 2, C.grayD);
    } else {                                // PT · DPT: 2" 계기 받침대 위 전송기
      R(11, 12, 2, 16, C.grayD); R(7, 26, 10, 2, C.grayD);
      if (t === "DPT") { R(3, 12, 18, 5, "#9aa6b1"); R(3, 12, 18, 1, "#c4cdd5"); R(2, 16, 3, 4, C.pipeD); R(19, 16, 3, 4, C.pipeD); }
      R(6, 2, 12, 10, "#5a87b8"); R(6, 2, 12, 2, "#86acd4"); R.disc(12, 7, 4, 3, "#cfe8d6"); R(10, 7, 4, 1, "#2f5f3b"); R(9, 12, 6, 2, C.grayL);
    }
  });
}
// ── 정비 · 물류 · 사무 ────────────────────────────────────────────────────
function drumImg(col) { return pix(26, 24, R => { R.disc(13, 12, 12, 11, "#8a5a32"); R.disc(13, 12, 10, 9, col); for (let y = 4; y < 21; y += 2) R(4, y, 18, 1, shade(col, -.25));
  R.disc(13, 12, 3, 3, "#5a3a20"); R(1, 21, 24, 3, "#6e4a2b"); }); }
function benchImg() { return pix(32, 22, R => { R(0, 8, 32, 5, "#8b6a45"); R(0, 8, 32, 1, "#b8925f"); R(2, 13, 3, 9, C.grayD); R(27, 13, 3, 9, C.grayD);
  R(3, 3, 8, 5, C.grayD); R(4, 2, 6, 2, C.gray); R(16, 5, 10, 3, C.red); R(18, 4, 6, 1, C.redD); R(27, 4, 3, 4, C.yel); }); }
function toolRackImg() { return pix(22, 30, R => { R(0, 0, 22, 26, "#5c6b7a"); for (let y = 2; y < 25; y += 3) for (let x = 2; x < 21; x += 3) R(x, y, 1, 1, "#3e4a57");
  R(3, 3, 2, 10, C.red); R(7, 4, 2, 8, C.yel); R(11, 3, 6, 2, C.grayL); R(12, 5, 2, 8, C.grayL); R(17, 14, 3, 8, C.org); R(3, 16, 8, 2, "#2f6db5"); R(0, 26, 22, 4, C.concD); }); }
function shelfImg() { return pix(22, 32, R => { for (const x of [0, 20]) R(x, 0, 2, 32, C.steelD); for (const y of [2, 12, 22]) { R(0, y + 7, 22, 2, C.steel);
  R(3, y + 1, 6, 6, "#c79b5c"); R(3, y + 1, 6, 1, "#e2bd84"); R(11, y + 3, 7, 4, "#5a87b8"); } }); }
function containerImg(col) {                // 해상 컨테이너 (48 × 32): 윗면 + 골판 옆면
  return pix(48, 32, R => { R(0, 0, 48, 12, shade(col, .2)); R(0, 0, 48, 1, shade(col, .45)); R(0, 12, 48, 18, col);
    for (let x = 2; x < 47; x += 3) R(x, 13, 1, 16, shade(col, -.25)); R(0, 12, 48, 1, shade(col, -.4)); R(0, 28, 48, 4, "#2a2f36");
    for (const x of [0, 46]) R(x, 0, 2, 32, shade(col, -.45)); R(20, 16, 8, 4, C.white); });
}
function officeImg() {                      // 현장 사무소 (2층 컨테이너 사무실 · 계단)
  return pix(144, 68, R => {
    for (const [y, x0] of [[0, 8], [32, 0]]) {
      R(x0, y + 0, 136, 6, "#dfe6ec"); R(x0, y + 0, 136, 1, "#ffffff"); R(x0, y + 6, 136, 24, "#cfd8e0"); R(x0, y + 6, 136, 2, "#2f6db5");
      for (let x = x0 + 8; x < x0 + 130; x += 22) { R(x, y + 12, 12, 9, C.glass); R(x, y + 12, 12, 1, C.glassL); R(x + 1, y + 13, 2, 7, C.glassL); }
      R(x0, y + 28, 136, 2, "#8a96a1");
    }
    R(116, 46, 10, 16, "#2f4f78"); R(117, 47, 8, 4, C.glassL);
    for (let i = 0; i < 8; i++) R(128 + i, 32 + i * 4, 8, 2, C.grayD); R(128, 30, 14, 2, C.yel);
    R(0, 62, 144, 6, C.concD);
  }, { labels: [{ t: "현장 사무소  SITE OFFICE", x: 60, y: 39, s: 9, c: "#1d2f4f" }] });
}
function craneImg() {                       // 크롤러 · 이동식 크레인 (100 × 80)
  return pix(100, 80, R => {
    R(4, 58, 64, 16, "#d9a520"); R(4, 58, 64, 3, "#f2c654"); R(4, 72, 64, 6, "#2a2f36"); for (let x = 8; x < 66; x += 8) R.disc(x, 75, 3, 3, "#1a1d22");
    R(50, 46, 16, 14, "#c4901a"); R(52, 48, 10, 6, C.glass); R(0, 62, 6, 4, C.yelD); R(66, 62, 6, 4, C.yelD);
    for (let i = 0; i < 52; i++) { const x = 56 - i * .9, y = 48 - i * .9; R(x, y, 5, 4, i % 4 ? "#e0b02a" : "#a57e14"); }   // 붐
    R(6, 2, 2, 34, "#1d1d1d"); R(4, 36, 6, 4, C.grayD); R(5, 40, 4, 3, C.red);
    hz(R, 4, 56, 64, 2);
  });
}
function forkliftImg() { return pix(30, 28, R => { R(2, 12, 20, 10, C.yel); R(2, 12, 20, 2, "#f7dc7a"); R(6, 2, 2, 12, "#2a2f36"); R(18, 2, 2, 12, "#2a2f36");
  R(6, 2, 14, 2, "#2a2f36"); R(22, 0, 3, 22, C.grayD); R(24, 18, 6, 2, C.gray); R(24, 22, 6, 2, C.gray); R.disc(7, 23, 4, 4, "#1a1d22"); R.disc(18, 23, 4, 4, "#1a1d22"); R(9, 14, 6, 4, "#26324a"); }); }
function truckImg(col) { return pix(44, 24, R => { R(0, 8, 44, 10, col); R(0, 8, 44, 2, shade(col, .3)); R(26, 2, 16, 8, col); R(28, 3, 10, 5, C.glass); R(29, 3, 3, 4, C.glassL);
  R(2, 10, 22, 6, shade(col, -.12)); R.disc(9, 19, 4, 4, "#1a1d22"); R.disc(35, 19, 4, 4, "#1a1d22"); R(40, 12, 4, 2, C.yel); R(0, 12, 2, 2, C.red); }); }
function spoolImg() { return pix(46, 22, R => { R(0, 18, 46, 4, "#7a5534"); for (let k = 0; k < 3; k++) for (let i = 0; i < 4 - k; i++) {
  const x = 6 + i * 11 + k * 5.5, y = 13 - k * 8; R.disc(x, y, 5, 5, "#9aa6b1"); R.disc(x, y, 3, 3, "#3b434d"); } }); }
function lightPoleImg() { return pix(14, 70, R => { R(6, 6, 2, 62, C.grayD); R(5, 6, 1, 62, C.gray); R(1, 0, 12, 6, "#3a4250"); R(2, 4, 10, 2, "#fff4c2"); R(3, 66, 8, 4, C.concD); }); }
function treeImg(seed) { const r = rng(seed); return pix(30, 38, R => { R(13, 24, 4, 14, "#4a3423"); R.disc(15, 15, 14, 13, "#1f3d26");
  for (let i = 0; i < 9; i++) R.disc(6 + r() * 18, 6 + r() * 14, 4 + r() * 3, 4 + r() * 3, i % 3 ? "#2f5a35" : "#3f7343"); R.disc(10, 8, 3, 3, "#5a9256"); }); }
function shrubImg(seed) { const r = rng(seed); return pix(18, 12, R => { R.disc(9, 6, 9, 6, "#23432a"); for (let i = 0; i < 4; i++) R.disc(3 + r() * 12, 3 + r() * 5, 3, 3, "#386a3c"); }); }
function coneImg() { return pix(10, 14, R => { R(1, 12, 8, 2, "#2a2f36"); for (let y = 0; y < 12; y++) { const w = 2 + Math.floor(y / 2); R(5 - w / 2, y, w, 1, y === 4 || y === 5 ? C.white : C.org); } }); }
function signImg(text, col, sub) { return pix(34, 34, R => { R(16, 18, 2, 16, C.grayD); R(0, 0, 34, 18, col); R(0, 0, 34, 1, shade(col, .4)); R(1, 17, 32, 1, shade(col, -.4)); },
  { labels: [{ t: text, x: 17, y: sub ? 6 : 9, s: 10, c: C.white }].concat(sub ? [{ t: sub, x: 17, y: 13, s: 8, c: C.white }] : []) }); }
function boardImg() { return pix(34, 34, R => { for (const x of [3, 29]) R(x, 18, 2, 16, C.grayD); R(0, 0, 34, 20, C.white); R(0, 0, 34, 2, C.steel);
  for (let y = 5; y < 18; y += 4) { R(4, y, 3, 2, C.grn); R(9, y + 1, 20, 1, "#7a8591"); } }, { labels: [{ t: "LOOP CHECK", x: 17, y: 1, s: 7, c: C.white }] }); }
function testBenchImg() { return pix(36, 22, R => { R(0, 8, 36, 5, "#5b6878"); R(0, 8, 36, 1, "#8494a8"); R(2, 13, 2, 9, C.grayD); R(32, 13, 2, 9, C.grayD);
  R(3, 2, 12, 6, "#1c2333"); R(4, 3, 10, 4, "#14385c"); R(5, 5, 8, 1, C.grn); R(18, 3, 8, 5, C.org); R(19, 4, 4, 2, "#222"); R(28, 4, 6, 4, C.yel); R(29, 5, 4, 1, "#333"); }); }
function vendingImg() { return pix(18, 32, R => { R(0, 0, 18, 30, C.red); R(0, 0, 18, 2, "#ff7b6e"); R(2, 4, 10, 18, "#1c2333");
  for (let y = 6; y < 21; y += 4) for (let x = 3; x < 11; x += 3) R(x, y, 2, 2, ["#ffd35a", "#61b3ff", "#7be08f"][(x + y) % 3]); R(13, 8, 3, 6, "#eee"); R(0, 30, 18, 2, "#2a2f36"); }); }
function parkBenchImg() { return pix(32, 16, R => { R(0, 2, 32, 3, "#8b6a45"); R(0, 7, 32, 3, "#8b6a45"); R(0, 2, 32, 1, "#b8925f"); R(2, 10, 2, 6, C.grayD); R(28, 10, 2, 6, C.grayD); }); }
function boothImg() { return pix(36, 44, R => { R(0, 0, 36, 8, C.steel); R(0, 0, 36, 2, C.steelL); R(2, 8, 32, 32, "#dfe6ec"); R(4, 12, 28, 12, C.glass);
  R(5, 13, 3, 10, C.glassL); R(0, 40, 36, 4, C.concD); }, { labels: [{ t: "경비실", x: 18, y: 31, s: 9, c: "#1d2f4f" }] }); }
function gateImg() { return pix(192, 40, R => {                // 정문 — 기둥 · 미닫이 철문 · 차단기 · 간판
  for (const x of [0, 184]) { R(x, 0, 8, 40, C.steel); R(x, 0, 8, 2, C.steelL); }
  R(8, 14, 176, 2, C.grayD); R(8, 36, 176, 2, C.grayD); for (let x = 10; x < 184; x += 6) R(x, 16, 2, 20, "#9aa5b1");
  R(56, 2, 80, 10, C.navy2); R(56, 2, 80, 1, C.steelL);
  for (let i = 0; i < 70; i++) R(30 + i, 26, 1, 3, Math.floor(i / 5) % 2 ? C.red : C.white); R(26, 22, 4, 12, C.yel); }, { labels: [{ t: "정문  MAIN GATE", x: 96, y: 7, s: 10, c: "#e9f2ff" }] }); }
// 제어실 벽 (지붕 없는 단면): 북쪽 벽은 안쪽 면(영상 벽 · 경보창), 옆 · 남쪽은 낮은 벽 윗면
function crWallN(wTiles, screens) { const w = wTiles * 16; return pix(w, 40, R => { R(0, 0, w, 4, "#9aa3ad"); R(0, 4, w, 34, "#c9d1d9"); R(0, 4, w, 2, "#5d6772"); R(0, 36, w, 4, "#7d8794");
  if (screens) { R(6, 9, w - 12, 18, "#0f1a2b"); R(7, 10, w - 14, 16, "#132a45");
    for (let x = 10; x < w - 12; x += 3) R(x, 12 + Math.round(Math.sin(x / 7) * 3 + 4), 2, 1, C.grn);
    for (let x = 10; x < w - 12; x += 14) { R(x, 20, 8, 3, "#2f6db5"); R(x + 2, 21, 4, 1, C.yel); }
    for (let x = 8; x < w - 8; x += 4) R(x, 29, 3, 3, ["#3a4a3a", "#3a4a3a", "#7a5a1a"][x % 3]); } }); }
function crWallV(rows) { return pix(8, rows * 16 + 8, R => { R(0, 0, 8, rows * 16 + 8, "#9aa3ad"); R(0, 0, 2, rows * 16 + 8, "#c9d1d9"); R(6, 0, 2, rows * 16 + 8, "#6b7480"); }); }
function crWallS(wTiles) { const w = wTiles * 16; return pix(w, 14, R => { R(0, 0, w, 4, "#9aa3ad"); R(0, 4, w, 10, "#7d8794"); R(0, 4, w, 1, "#5d6772"); }); }

// ── 소품 놓기 — buildWorld 가 한 번에 그린다 ─────────────────────────────────────
// put(그림 만들기, 왼쪽 칸, 바닥 칸, { fw: 차지 폭(칸), solid: 막는 칸 [x0,y0,x1,y1], fade: 뒤에 서면 반투명, flat: 땅처럼 밑에, anim, dy })
const PLACES = [], SHADOWS = [], LIGHTS = [], ANIM = [];
function put(make, tx, ty, opts = {}) { PLACES.push({ make, tx, ty, opts }); if (opts.solid) block(...opts.solid); }
// A 주 발전동
put(() => building({ w: 256, roofH: 60, wallH: 48, roof: "#3b5878", wall: "#8e9aa7", sign: { t: "TURBINE HALL  터빈 홀", x: 70, y: 6, w: 116, h: 10, s: 11 },
  doors: [{ x: 22, w: 34, h: 30, roll: true }, { x: 200, w: 34, h: 30, roll: true }, { x: 104, w: 10, h: 18 }, { x: 140, w: 10, h: 18 }],
  wins: [{ x: 68, y: 22, w: 28, h: 8 }, { x: 158, y: 22, w: 28, h: 8 }], vents: [{ x: 30, y: 12, w: 18, h: 10 }, { x: 120, y: 10, w: 22, h: 12 }, { x: 206, y: 12, w: 18, h: 10 }] }),
  4, 9, { fw: 16, solid: [4, 3, 19, 9], fade: true, shadow: [20, 4, 20, 9] });
put(() => building({ w: 112, roofH: 44, wallH: 40, roof: "#34506e", wall: "#9aa6b2", sign: { t: "GENERATOR 발전기", x: 18, y: 4, w: 76, h: 9, s: 10 },
  louver: [{ x: 8, y: 16, w: 20, h: 14 }, { x: 84, y: 16, w: 20, h: 14 }], doors: [{ x: 46, w: 20, h: 22, roll: true }], vents: [{ x: 40, y: 12, w: 30, h: 12 }] }),
  21, 9, { fw: 7, solid: [21, 4, 27, 9], fade: true, shadow: [28, 5, 28, 9] });
put(stackImg, 28, 9, { fw: 2, solid: [28, 8, 29, 9], fade: true, anim: (g, X, Y, now) => { if (Math.floor(now / 600) % 2) { g.fillStyle = "#ff4a3a"; g.fillRect(X + 22, Y + 2, 12, 4); } } });   // 항공 경고등
// B 공정 · 유틸리티
for (const x of [34, 38, 42]) put(pumpImg, x, 5, { fw: 3, solid: [x, 4, x + 2, 5] });
put(hxImg, 34, 9, { fw: 13, solid: [34, 8, 46, 9] });
put(coolingImg, 49, 9, { fw: 12, solid: [49, 2, 60, 9], fade: true, anim: (g, X, Y, now) => {   // 냉각탑 팬 6 날개 (천천히 돎)
  g.fillStyle = "#93a2b2";
  for (const [fx, n] of [[48, 0], [144, 1.1]]) for (let i = 0; i < 6; i++) { const an = now / 300 + i * Math.PI / 3 + n;
    for (let r = 4; r < 30; r += 2) g.fillRect(X + Math.round(fx + Math.cos(an) * r) * PX, Y + Math.round(36 + Math.sin(an) * r * .74) * PX, PX * 2, PX * 2); }
} });
// C 배관랙 (2 ~ 61 칸, 기둥은 5 칸마다 · 남북 큰길 칸은 비움)
{ const cols = []; for (let x = 4; x <= 59; x += 5) { cols.push(x - 2); block(x, 13, x, 14); }
  put(() => pipeRackImg(60, cols), 2, 14, { fw: 60, fade: true, shadow: [2, 12, 61, 14] }); }
// D 변전 · MCC
for (const [x0, y0, n, vert] of [[3, 23, 9, 0], [3, 30, 4, 0], [9, 30, 3, 0], [3, 23, 8, 1], [11, 23, 8, 1]]) {
  if (vert) { put(() => fenceV(n), x0, y0 + n - 1, { solid: [x0, y0, x0, y0 + n - 1] }); }
  else { put(() => fenceH(n), x0, y0, { fw: n, solid: [x0, y0, x0 + n - 1, y0] }); }
}
put(transformerImg, 4, 26, { fw: 3, solid: [5, 25, 6, 26] }); put(transformerImg, 7, 26, { fw: 3, solid: [8, 25, 9, 26] });
put(switchImg, 4, 28, { fw: 2, solid: [5, 28, 5, 28] }); put(switchImg, 8, 28, { fw: 2, solid: [8, 28, 9, 28] });
put(() => building({ w: 96, roofH: 22, wallH: 50, roof: "#455a72", wall: "#a3adb8", sign: { t: "MCC / E-HOUSE", x: 14, y: 4, w: 68, h: 9, s: 9 },
  doors: [{ x: 10, w: 12, h: 22 }, { x: 74, w: 12, h: 22 }], louver: [{ x: 34, y: 18, w: 28, h: 12 }] }), 13, 27, { fw: 6, solid: [13, 23, 18, 27], fade: true });
// E 중앙 제어실 — 북벽(입구 23~25 칸) · 옆벽 · 남벽
put(() => crWallN(4, true), 19, 23, { fw: 4, solid: [19, 23, 22, 23] }); put(() => crWallN(4, true), 26, 23, { fw: 4, solid: [26, 23, 29, 23] });
put(() => crWallV(8), 19, 31, { solid: [19, 24, 19, 31], dy: 0 }); put(() => crWallV(8), 29, 31, { solid: [29, 24, 29, 31] });
put(() => crWallS(11), 19, 32, { fw: 11, solid: [19, 32, 29, 32] });
put(() => signImg("중앙 제어실", C.steel, "CCR"), 22, 22, {});
for (const x of [22, 23, 25, 26]) put(chairImg, x, 27, {});
put(() => cabinetImg("MC"), 23, 30, { solid: [23, 30, 23, 30] }); put(() => cabinetImg("MC"), 26, 30, { solid: [26, 30, 26, 30] });
// F 시운전
put(testBenchImg, 42, 29, { fw: 2, solid: [42, 29, 43, 29] }); put(boardImg, 45, 29, { fw: 2, solid: [45, 29, 46, 29] });
for (const [x, y] of [[34, 27], [47, 27], [34, 31], [47, 31]]) put(coneImg, x, y, {});
put(() => signImg("시운전 구역", C.org, "COMMISSIONING"), 33, 23, { solid: [33, 23, 33, 23] });
// G 정비동
put(() => building({ w: 128, roofH: 34, wallH: 44, roof: "#3f566f", wall: "#94a0ad", sign: { t: "정비동  MAINTENANCE", x: 24, y: 3, w: 80, h: 9, s: 9 },
  doors: [{ x: 10, w: 30, h: 26, roll: true }, { x: 86, w: 30, h: 26, roll: true }], vents: [{ x: 56, y: 10, w: 16, h: 10 }] }), 53, 27, { fw: 8, solid: [53, 23, 60, 27], fade: true });
put(benchImg, 48, 29, { fw: 2, solid: [48, 29, 49, 29] }); put(toolRackImg, 51, 29, { solid: [51, 29, 51, 29] });
put(() => drumImg("#2b2f36"), 55, 30, { solid: [55, 30, 55, 30] }); put(() => drumImg(C.org), 57, 30, { solid: [57, 30, 57, 30] }); put(() => drumImg("#3d6fb0"), 59, 30, { solid: [59, 30, 59, 30] });
put(shelfImg, 60, 29, { solid: [60, 29, 60, 29] });
// H 현장 사무소 · 물류 · 쉼터 · 주차 · 정문
put(officeImg, 52, 36, { fw: 9, solid: [52, 33, 60, 36], fade: true });
for (const [x, col] of [[35, "#2f6fb5"], [38, "#d9692b"], [41, "#7c8a94"]]) put(() => containerImg(col), x, 34, { fw: 3, solid: [x, 33, x + 2, 34], fade: true });
put(craneImg, 45, 39, { fw: 5, solid: [45, 38, 49, 39], fade: true, anim: (g, X, Y, now) => { if (Math.floor(now / 500) % 2) { g.fillStyle = "#ffb03a"; g.fillRect(X + 8, Y + 80, 8, 6); } } });
put(forkliftImg, 43, 38, { solid: [43, 38, 43, 38] });
put(spoolImg, 36, 39, { fw: 3, solid: [36, 39, 38, 39] }); put(spoolImg, 39, 39, { fw: 3, solid: [39, 39, 41, 39] });
for (const [x, y] of [[33, 38], [33, 40], [51, 39]]) put(coneImg, x, y, {});
for (const [x, y, col] of [[4, 36, "#e8eef2"], [7, 36, "#2f6db5"], [10, 36, "#e8eef2"], [4, 39, "#7c8a94"], [10, 39, "#c63a33"]]) put(() => truckImg(col), x, y, { fw: 2, solid: [x, y, x + 1, y] });
put(vendingImg, 19, 35, { solid: [19, 35, 19, 35] }); put(parkBenchImg, 21, 37, { fw: 2, solid: [21, 37, 22, 37] }); put(parkBenchImg, 24, 37, { fw: 2, solid: [24, 37, 25, 37] });
put(() => signImg("안전제일", C.grnD, "SAFETY FIRST"), 26, 34, { solid: [26, 34, 26, 34] });
put(() => signImg("보호구 착용", "#2f6db5", "PPE"), 34, 22, { solid: [34, 22, 34, 22] });
put(() => signImg("고압 위험", C.redD, "HIGH VOLTAGE"), 12, 22, { solid: [12, 22, 12, 22] });
put(boothImg, 27, 39, { fw: 2, solid: [27, 38, 28, 39], fade: true });
put(gateImg, 26, 42, { fw: 12 });
for (const [x, y] of [[3, 17], [13, 17], [22, 17], [37, 17], [47, 17], [57, 17], [20, 33], [32, 33], [45, 32], [10, 34]]) {   // 조명탑 (땅에 불빛 웅덩이)
  put(lightPoleImg, x, y, { solid: [x, y, x, y] }); LIGHTS.push([x + .5, y + .8]); }
// 둘레 녹지 · 나무
for (let x = 0; x < W; x += 2) { put(() => treeImg(x * 7 + 1), x, 1, {}); put(() => treeImg(x * 11 + 3), x, 43, {}); }
for (let y = 3; y < H - 2; y += 3) { put(() => treeImg(y * 5 + 2), 0, y, {}); put(() => treeImg(y * 13 + 4), W - 1, y, {}); }
for (const [x, y] of [[2, 18], [27, 18], [33, 18], [61, 18], [2, 32], [17, 33], [28, 36], [16, 40], [61, 32]]) put(() => shrubImg(x * 31 + y), x, y, {});

// ── 땅 (한 번 그린다 — 점 해상도로 칠한 뒤 PX 배) ─────────────────────────
const groundImg = canvas(W * T, H * T);
function drawGround() {
  const g = groundImg.getContext("2d"), TP = T / PX, AW = W * TP, AH = H * TP, img = new ImageData(AW, AH), D = img.data;
  const tile = (ax, ay) => ground[at(Math.min(W - 1, Math.max(0, ax >> 4)), Math.min(H - 1, Math.max(0, ay >> 4)))];
  for (let y = 0; y < AH; y++) for (let x = 0; x < AW; x++) {
    const t = tile(x, y), n = hash(`${x},${y}`) & 255, big = vnoise(x / 40, y / 40, t + 1), di = (y * AW + x) * 4;
    let r, gg, b;
    if (t === GRAV) { const v = n < 60 ? -14 : n < 120 ? -6 : n < 200 ? 0 : 10; r = 66 + v; gg = 72 + v; b = 84 + v; if (n > 246) { r += 30; gg += 28; b += 24; } }
    else if (t === CONC) { const v = (n & 15) - 8; r = 118 + v; gg = 126 + v; b = 136 + v; if (x % 32 === 0 || y % 32 === 0) { r -= 22; gg -= 22; b -= 20; } }
    else if (t === ASPH) { const v = (n & 15) - 8; r = 40 + v; gg = 45 + v; b = 58 + v; }
    else if (t === GRAT) { const on = x % 3 === 0 || y % 3 === 0; r = on ? 52 : 76; gg = on ? 60 : 86; b = on ? 72 : 100; }
    else if (t === GRASS) { const v = (n & 31) - 16; r = 38 + v / 2; gg = 70 + v; b = 44 + v / 2; }
    else { const v = (n & 7) - 4; r = 44 + v; gg = 96 + v; b = 116 + v; if (x % 16 === 0 || y % 16 === 0) { r -= 10; gg -= 16; b -= 16; } if ((x + y) % 23 === 0) { r += 10; gg += 14; b += 14; } }
    const k = .86 + big * .24; D[di] = r * k; D[di + 1] = gg * k; D[di + 2] = b * k; D[di + 3] = 255;
  }
  const mul = (x0, y0, x1, y1, k) => { for (let y = Math.max(0, y0); y < Math.min(AH, y1); y++) for (let x = Math.max(0, x0); x < Math.min(AW, x1); x++) { const i = (y * AW + x) * 4; D[i] *= k; D[i + 1] *= k; D[i + 2] *= k; } };
  const paint = (x0, y0, w, h, col) => { for (let y = y0; y < y0 + h; y++) for (let x = x0; x < x0 + w; x++) { if (x < 0 || y < 0 || x >= AW || y >= AH) continue; const i = (y * AW + x) * 4; D[i] = col[0]; D[i + 1] = col[1]; D[i + 2] = col[2]; } };
  // 큰길 차선 (가운데 노란 점선 · 가장자리 흰 선) · 횡단보도 · 정지선
  const Y = [214, 178, 60], Wt = [210, 214, 218];
  for (let x = 2 * 16; x < 62 * 16; x++) { if (x >= 30 * 16 && x < 32 * 16) continue; paint(x, 20 * 16 + 1, 1, 1, Wt); paint(x, 22 * 16 - 2, 1, 1, Wt); if ((x >> 3) % 2) paint(x, 21 * 16 - 1, 1, 2, Y); }
  for (let y = 15 * 16; y < 42 * 16; y++) { if (y >= 20 * 16 && y < 22 * 16) continue; paint(30 * 16 + 1, y, 1, 1, Wt); paint(32 * 16 - 2, y, 1, 1, Wt); if ((y >> 3) % 2) paint(31 * 16 - 1, y, 2, 1, Y); }
  for (const cx of [23, 40]) for (let i = 0; i < 6; i++) paint(cx * 16 + i * 6, 20 * 16 + 3, 3, 26, Wt);
  for (let x = 4 * 16; x < 16 * 16; x += 48) for (const y of [35, 38]) paint(x, y * 16, 1, 40, Wt);   // 주차 칸
  // 구역 바닥 노란 안전선 (테두리 안쪽 1점)
  for (const [x0, y0, x1, y1] of [[2, 2, 29, 11], [33, 2, 61, 11], [33, 23, 47, 31], [48, 23, 61, 31], [12, 23, 18, 31], [33, 33, 61, 35]]) {
    paint(x0 * 16 + 2, y0 * 16 + 2, (x1 - x0 + 1) * 16 - 4, 1, Y); paint(x0 * 16 + 2, (y1 + 1) * 16 - 3, (x1 - x0 + 1) * 16 - 4, 1, Y);
    paint(x0 * 16 + 2, y0 * 16 + 2, 1, (y1 - y0 + 1) * 16 - 4, Y); paint((x1 + 1) * 16 - 3, y0 * 16 + 2, 1, (y1 - y0 + 1) * 16 - 4, Y); }
  for (let x = 2 * 16; x < 62 * 16; x += 6) paint(x, 15 * 16 + 1, 3, 1, Y);                     // 랙 앞 보도 안전선
  // 그림자 (건물 · 랙 오른쪽 아래) · 조명 불빛 웅덩이
  for (const p of PLACES) if (p.opts.shadow) { const [a, b, c, d] = p.opts.shadow; mul(a * 16, b * 16 + 6, (c + 1) * 16, (d + 1) * 16 + 6, .66); }
  mul(2 * 16, 12 * 16, 62 * 16, 15 * 16, .78);
  for (const [lx, ly] of LIGHTS) { const cx = lx * 16, cy = ly * 16, R2 = 58;
    for (let y = Math.round(cy - R2); y < cy + R2; y++) for (let x = Math.round(cx - R2 * 1.4); x < cx + R2 * 1.4; x++) {
      if (x < 0 || y < 0 || x >= AW || y >= AH) continue; const d = Math.hypot((x - cx) / 1.4, y - cy) / R2; if (d >= 1) continue;
      const k = 1 + .32 * (1 - d) * (1 - d), i = (y * AW + x) * 4; D[i] = Math.min(255, D[i] * k + 6 * (1 - d)); D[i + 1] = Math.min(255, D[i + 1] * k + 4 * (1 - d)); D[i + 2] = Math.min(255, D[i + 2] * k); } }
  // 바닥 장식 — 맨홀 · 배수구 · 기름 자국 · 시운전 임시 케이블(주황)
  for (const [x, y] of [[8, 16], [24, 16], [44, 16], [56, 16], [16, 22], [38, 22], [52, 22]]) { const cx = x * 16 + 8, cy = y * 16 + 8;
    for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) if (dx * dx + dy * dy <= 16) paint(cx + dx, cy + dy, 1, 1, (dx + dy) % 2 ? [70, 76, 86] : [96, 102, 112]); }
  for (let i = 0; i < 40; i++) { const r = rng(900 + i), x = Math.floor(r() * AW), y = Math.floor(r() * AH); if (tile(x, y) === CONC || tile(x, y) === ASPH) mul(x, y, x + 6 + Math.floor(r() * 8), y + 3 + Math.floor(r() * 4), .82); }
  for (const [x0, y0, x1, y1] of [[35, 26, 44, 28], [37, 26, 41, 30], [44, 26, 43, 29]]) { let x = x0 * 16 + 8, y = y0 * 16 + 4; const tx = x1 * 16 + 8, ty = y1 * 16 + 4;
    while (Math.abs(x - tx) + Math.abs(y - ty) > 1) { paint(x, y, 1, 1, [232, 117, 42]); if (Math.abs(x - tx) > Math.abs(y - ty)) x += Math.sign(tx - x); else y += Math.sign(ty - y); if (hash(`c${x},${y}`) % 5 === 0) y += Math.sign(ty - y); } }
  g.imageSmoothingEnabled = false;
  const s1 = canvas(AW, AH); s1.getContext("2d").putImageData(img, 0, 0); g.drawImage(s1, 0, 0, W * T, H * T);
}
function drawGroundPlain() { const g = groundImg.getContext("2d"), P = { [GRAV]: "#464e5a", [CONC]: "#7a828c", [ASPH]: "#2a2f3c", [GRAT]: "#4a5566", [GRASS]: "#2c4a2e", [EPOXY]: "#2f6274" };
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { g.fillStyle = P[ground[at(x, y)]]; g.fillRect(x * T, y * T, T, T); } }

// ── 설비 (서버가 목록 · 상태를 준다 — 점검 · 교정 · 수리 대상) ────────────────────
const EQUIP = [], EQ_BY = new Map(), EQ_ST = {};          // EQ_ST[id] = [상태, 작업 중인 사람]
const EQ_CAT = { PT: "계장", DPT: "계장", TT: "계장", FT: "계장", LT: "계장", PG: "계장", CV: "현장", DCS: "DCS", IO: "DCS", PLC: "DCS", CON: "DCS", MC: "DCS", JB: "케이블", TRAY: "케이블" };
function eqImg(t) { return t === "CON" ? consoleImg() : ["DCS", "IO", "PLC", "MC"].includes(t) ? cabinetImg(t) : t === "JB" ? jbImg() : t === "TRAY" ? trayImg() : xmtrImg(t); }
async function loadEquip() {
  try { const r = await fetch("/plaza/api/equip", { cache: "no-store" }); if (!r.ok) return; const d = await r.json();
    for (const e of d.equip || []) { EQUIP.push(e); EQ_BY.set(e.id, e); block(e.x, e.y, e.x + (e.w || 1) - 1, e.y); }
    if (d.heal_radius) S.healR = d.heal_radius; if (Array.isArray(d.jobs)) S.jobs = d.jobs;
  } catch (_) { /* 설비 없이 */ }
}

// ── 캐릭터 그림 (마을 시트에서 뽑은 static/village_chars.png — 디자인 그대로) ───────────
const CHR_FR = {"cat_d0":[0,0,22,30,10.7,29],"cat_d1":[23,0,21,29,9.8,28],"cat_d2":[45,0,22,29,10.3,27],"cat_d3":[68,0,21,29,9.5,28],"cat_s0":[90,0,22,29,10.3,28],"cat_s1":[113,0,20,29,9.9,27],"cat_a":[134,0,37,28,13.9,26],"panda_d0":[172,0,19,30,8.7,29],"panda_d1":[192,0,20,29,9.4,28],"panda_s0":[213,0,21,28,10.4,27],"panda_s1":[235,0,20,29,9.8,28],"panda_a":[256,0,30,30,11.3,29],"lion_d0":[287,0,23,30,10.9,29],"lion_d1":[311,0,22,30,10.8,28],"lion_d2":[334,0,22,30,10.0,29],"lion_d3":[357,0,20,29,9.2,28],"lion_s0":[378,0,22,30,10.3,29],"lion_s1":[401,0,22,28,10.5,27],"lion_a":[424,0,46,33,16.9,32],"tiger_d0":[471,0,22,28,10.3,27],"tiger_d1":[0,34,20,28,9.0,27],"tiger_a":[21,34,48,29,25.6,28],"nobi_d0":[70,34,20,26,8.5,24],"nobi_d1":[91,34,19,28,9.2,27],"nobi_s0":[111,34,21,26,10.0,24],"nobi_s1":[133,34,20,26,8.9,25],"nobi_s2":[154,34,20,26,9.1,24],"nobi_s3":[175,34,18,26,8.0,24],"p_cat":[194,34,64,90,33.4,89],"p_panda":[259,34,58,88,28.9,86],"p_lion":[318,34,66,91,32.4,90],"p_tiger":[385,34,63,88,30.5,87],"p_nobi":[449,34,57,72,27.3,71]};
const CHR = { data: null, ready: false };
function loadAtlas(o, src) {
  return new Promise(res => {
    const im = new Image();
    im.onload = () => { const c = canvas(im.width, im.height), g = c.getContext("2d", { willReadFrequently: true }); g.drawImage(im, 0, 0);
      o.data = g.getImageData(0, 0, im.width, im.height); o.ready = true; res(); };
    im.onerror = () => res();
    im.src = src;
  });
}
function atlasSprite(A, FR, name, mirror, scale = PX) {   // 한 칸 → scale 배 (뒤집기) · canvas.cx · canvas.foot (px)
  const key = `c|${name}|${mirror ? 1 : 0}|${scale}`; if (spriteCache.has(key)) return spriteCache.get(key);
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

const WORLD = { ready: false, built: false };
WORLD.promise = new Promise(res => { WORLD.done = res; });
function buildWorld() {                     // 설비 막기 → 땅 → 소품 · 설비 그림 → NPC 경로 (한 번만)
  if (WORLD.built) return; WORLD.built = true;
  try { drawGround(); } catch (_) { drawGroundPlain(); }
  for (const p of PLACES) {
    const img = p.make(); if (!img) continue;
    const fw = p.opts.fw || 1, y = (p.ty + 1) * T + (p.opts.dy || 0);
    props.push({ img, x: Math.round(p.tx * T + fw * T / 2 - img.width / 2), y, z: p.opts.flat ? y - 3 * T : y, fade: !!p.opts.fade, anim: p.opts.anim });
  }
  for (const e of EQUIP) { const img = eqImg(e.t), fw = e.w || 1, y = (e.y + 1) * T;
    props.push({ img, x: Math.round(e.x * T + fw * T / 2 - img.width / 2), y, z: y, eq: e }); }
  try { npcInit(); } catch (_) { NPCS.length = 0; }
  WORLD.ready = true; WORLD.done();
}
Promise.all([loadAtlas(CHR, "/static/village_chars.png"), loadEquip()]).then(buildWorld);
setTimeout(buildWorld, 8000);               // 그림 · 설비가 끝내 안 오면 있는 것만으로

// ── 경로 찾기 (A*, 4 방향 · 막힌 칸 피함) — NPC 가 씀 ───────────────────────────
function findPath(sx, sy, tx, ty) {
  if (sx === tx && sy === ty) return [[sx, sy]];
  const N = W * H, gS = new Float32Array(N).fill(1e9), came = new Int32Array(N).fill(-1), open = [[0, at(sx, sy)]], closed = new Uint8Array(N);
  gS[at(sx, sy)] = 0;
  while (open.length) {
    let bi = 0; for (let i = 1; i < open.length; i++) if (open[i][0] < open[bi][0]) bi = i;
    const [, cur] = open.splice(bi, 1)[0]; if (closed[cur]) continue; closed[cur] = 1;
    const cx = cur % W, cy = (cur / W) | 0;
    if (cx === tx && cy === ty) { const path = []; for (let c = cur; c !== -1; c = came[c]) path.push([c % W, (c / W) | 0]); return path.reverse(); }
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = cx + dx, ny = cy + dy; if (!inside(nx, ny) || solid[at(nx, ny)]) continue;
      const ni = at(nx, ny), ng = gS[cur] + 1 + (ground[ni] === GRAV ? .3 : 0);   // 포장된 길을 조금 더 좋아함
      if (ng < gS[ni]) { gS[ni] = ng; came[ni] = cur; open.push([ng + Math.abs(nx - tx) + Math.abs(ny - ty), ni]); }
    }
  }
  return null;
}

// ── 화면 틀 (붉은 꼰 기둥 · 모서리 장식 · 지명 현판) ──────────────────────
function twist(len, horiz) {
  const c = horiz ? canvas(len, FRAME) : canvas(FRAME, len), g = c.getContext("2d");
  g.fillStyle = "#1a2638"; g.fillRect(0, 0, c.width, c.height);   // 철골 틀 — 남색 강판 · 노랑 검정 빗금
  for (let i = -FRAME; i < len; i += 10) {
    g.fillStyle = (Math.floor(i / 10) % 6 === 0) ? "#e0b52e" : "#2c3f5a"; g.beginPath();
    if (horiz) { g.moveTo(i, FRAME); g.lineTo(i + 6, FRAME); g.lineTo(i + 6 + FRAME, 0); g.lineTo(i + FRAME, 0); }
    else { g.moveTo(0, i); g.lineTo(0, i + 6); g.lineTo(FRAME, i + 6 + FRAME); g.lineTo(FRAME, i + FRAME); }
    g.fill();
    g.fillStyle = "rgba(170,200,240,.25)"; if (horiz) g.fillRect(i + FRAME, 2, 3, 2); else g.fillRect(2, i + FRAME, 2, 3);
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
  for (const [x, y] of [[0, 0], [vw - 34, 0], [0, vh - 34], [vw - 34, vh - 34]]) {   // 모서리 — 볼트 박은 강판
    g.fillStyle = "#101826"; g.fillRect(x, y, 34, 34); g.fillStyle = "#3d5a7a"; g.fillRect(x + 3, y + 3, 28, 28);
    g.fillStyle = "#5f82a6"; g.fillRect(x + 3, y + 3, 28, 3);
    for (const [bx, by] of [[8, 8], [24, 8], [8, 24], [24, 24]]) { g.fillStyle = "#1a2638"; g.fillRect(x + bx - 2, y + by - 2, 5, 5); g.fillStyle = "#a8b2bc"; g.fillRect(x + bx - 1, y + by - 1, 2, 2); }
  }
  g.font = `bold 14px ${FONT}`;                // 현판
  const tw = Math.ceil(g.measureText(PLACE).width) + 60, tx = Math.round(vw / 2 - tw / 2);
  g.fillStyle = "#101826"; g.beginPath(); g.moveTo(tx, 0); g.lineTo(tx + tw, 0); g.lineTo(tx + tw - 14, 26); g.lineTo(tx + 14, 26); g.closePath(); g.fill();
  g.strokeStyle = "#5f82a6"; g.lineWidth = 2; g.stroke();
  g.fillStyle = "#e9f2ff"; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(PLACE, vw / 2, 13);
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
  cloth: CLOTHS.length, pants: PANTS.length, kind: KINDS.length, fur: FURS.length, armor: ARMORS.length, cape: CAPES.length, job: 5 };
const ROLE_LABEL = { leader: "그룹장", unit: "유닛장", operator: "운영자", member: "" };
const ROLE_COLOR = { leader: "#ffd84a", unit: "#ffb36b", operator: "#d8c59a" };
function defaultFace(name) {                // 처음 들어온 사람 — 이름에서 정한 외형
  const n = hash(name);
  return { hair: n % 10, hairc: (n >>> 4) % 3, skin: (n >>> 7) % 3, eyes: (n >>> 9) % 3, beard: 0,
    cloth: (n >>> 12) % 12, pants: (n >>> 16) % 6, kind: 0, fur: 0, armor: 0, cape: 0, job: [0, 1, 3, 4][(n >>> 20) % 4] };   // 처음엔 누구나 원본 고양이 기사 (갈색 털 · 은빛 갑옷 · 빨간 망토)
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
  hp: p.hp ?? 100, hpMax: p.hp_max || 100, ghost: !!p.ghost, kills: p.kills || 0, killer: !!p.killer,
  hpShow: p.hp ?? 100, xp: p.xp || 0, lv: p.lv || 1, job: p.job ?? 0, healer: !!p.healer, healseq: p.heal_seq || 0, work: null, cheer: 0, stepMs: STEP_MS }; }

function walkable(x, y) { return inside(x, y) && !solid[at(x, y)]; }
// 캐릭터끼리 겹치지 않음 (2026-10-16 대시보드): 다른 사람이 서 있거나(서버 칸) 가고 있는 칸은 막힘 — 서버도 같은 규칙으로 막음
// 유령(체력 0)은 남과 겹쳐 지나가고, 남도 유령 칸은 지나감 (서버와 같은 규칙)
function occupied(x, y) { if (S.me && S.me.ghost) return false; if (npcAt(x, y)) return true;
  for (const a of S.others.values()) if (!a.ghost && ((a.gx === x && a.gy === y) || (a.tx === x && a.ty === y))) return true; return false; }
function freeNear(x, y) {                   // 들어오자마자 남과 같은 칸이면 가장 가까운 빈 칸으로
  for (let r = 1; r < 8; r++) for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
    if (Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
    const nx = x + dx, ny = y + dy; if (walkable(nx, ny) && !occupied(nx, ny)) return [nx, ny]; }
  return null;
}
function spawn() {                          // 이름마다 늘 같은 자리 — 가운데 네거리 둘레(3~10칸)의 길 · 보도에 흩어져 시작 (정문 앞에 몰리지 않게)
  const r = rng(hash(S.name || "x"));
  for (let i = 0; i < 600; i++) {
    const a = r() * Math.PI * 2, d = 3 + r() * 7, x = Math.round(31 + Math.cos(a) * d * 2), y = Math.round(20.5 + Math.sin(a) * d * .5);
    if (walkable(x, y) && !occupied(x, y) && ground[at(x, y)] !== GRASS) return [x, y];
  }
  return [28, 22];
}

// ── EPC 작업 · 기력 · NPC · 효과 (2026-10-22) ─────────────────────────────────────────
// 모든 값은 광장 안의 놀이 — 실제 DCS · 계장 설비에는 아무것도 보내지 않는다.
const JOB_SHORT = ["계장", "DCS", "시운전 리드", "현장", "케이블"];
const JOB_COL = ["#7fd0ff", "#c3a8ff", "#7be08f", "#ffb36b", "#ffd35a"];
const RUN_MS = 125, TIRED_MS = 260;          // 달릴 때 · 지쳤을 때 한 칸 걷는 시간
const ST_MAX = 100, ST_RUN = 24, ST_REGEN = 12, ST_TIRED = 15;   // 기력: 달리면 초당 −24 · 쉬면 +12 (유닛장 곁이면 2배) · 15 밑이면 지침
const WORK_NAME = { loop: "Loop Check", calib: "교정", repair: "수리" };
const ST_NAME = { ok: "정상", warn: "경고", fault: "고장" };
const DCS_T = new Set(["DCS", "IO", "PLC", "CON", "MC"]), CABLE_T = new Set(["JB", "TRAY"]);
Object.assign(S, { stamina: ST_MAX, run: false, work: null, healR: 4, jobs: ["계장 엔지니어", "DCS 엔지니어", "시운전 리드", "현장 기술자", "케이블 기술자"] });

// 효과: 입자(재사용 풀 · 최대 180) · 떠오르는 글씨(최대 40)
const PARTS = Array.from({ length: 180 }, () => ({ on: false })); let partI = 0;
function puff(x, y, vx, vy, life, col, size = 1) { const p = PARTS[partI++ % PARTS.length]; p.on = true; p.x = x; p.y = y; p.vx = vx; p.vy = vy; p.t0 = performance.now(); p.life = life; p.col = col; p.size = size; }
function drawParts(g, cx, cy, now) {
  for (const p of PARTS) { if (!p.on) continue; const k = (now - p.t0) / p.life; if (k >= 1) { p.on = false; continue; }
    g.globalAlpha = Math.min(1, (1 - k) * 1.4); g.fillStyle = p.col;
    g.fillRect(Math.round((p.x + p.vx * k - cx) / PX) * PX, Math.round((p.y + p.vy * k - cy) / PX) * PX, p.size * PX, p.size * PX); }
  g.globalAlpha = 1;
}
const FLOATS = [];
function floater(a, text, col, dur = 1400) { if (!a) return; FLOATS.push({ x: a.x + 16, y: a.y - 18, text, col, t0: performance.now(), dur }); if (FLOATS.length > 40) FLOATS.shift(); }
function drawFloats(g, cx, cy, now) {
  g.font = `bold 12px ${FONT}`; g.textAlign = "center"; g.textBaseline = "bottom"; g.lineWidth = 3; g.strokeStyle = "#0b111c";
  for (let i = FLOATS.length - 1; i >= 0; i--) { const f = FLOATS[i], k = (now - f.t0) / f.dur; if (k >= 1) { FLOATS.splice(i, 1); continue; }
    const x = Math.round(f.x - cx), y = Math.round(f.y - cy - k * 26); g.globalAlpha = k < .7 ? 1 : (1 - k) / .3;
    g.strokeText(f.text, x, y); g.fillStyle = f.col; g.fillText(f.text, x, y); }
  g.globalAlpha = 1; g.textAlign = "left";
}

// ── 설비 점검 · 교정 · 수리 ─────────────────────────────────────────────
function eqReach(e, tx, ty) { for (let i = 0; i < (e.w || 1); i++) if (Math.max(Math.abs(tx - (e.x + i)), Math.abs(ty - e.y)) <= 1) return true; return false; }
function nearEquip() {
  if (!S.me) return null; let best = null, bd = 1e9;
  for (const e of EQUIP) { if (!eqReach(e, S.me.tx, S.me.ty)) continue; const d = Math.hypot(S.me.tx - (e.x + ((e.w || 1) - 1) / 2), S.me.ty - e.y); if (d < bd) { bd = d; best = e; } }
  return best;
}
function faceTo(a, e) { const dx = e.x + ((e.w || 1) - 1) / 2 - a.tx, dy = e.y - a.ty; a.dir = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 3 : 2) : (dy > 0 ? 0 : 1); }
async function interact() {
  if (!S.me || !S.id) return;
  if (S.work) { cancelWork(); floater(S.me, "작업 그만", "#c9d4e0"); return; }
  const e = nearEquip();
  if (!e) { floater(S.me, "가까이에 점검할 설비가 없습니다", "#c9d4e0", 1600); return; }
  try {
    const r = await post("/plaza/api/work", { id: S.id, eq: e.id, phase: "start" });
    faceTo(S.me, e); sendMove();
    S.work = { eq: e, kind: r.kind, need: r.need * 1000, t0: performance.now(), label: r.label, state: r.state };
  } catch (err) { floater(S.me, err.message, "#ffb3a8", 2000); if (err.status === 404 && /캐릭터/.test(err.message)) join().catch(() => {}); }
}
function cancelWork() { if (!S.work) return; const e = S.work.eq; S.work = null; post("/plaza/api/work", { id: S.id, eq: e.id, phase: "cancel" }).catch(() => {}); }
async function finishWork() {
  const w = S.work; S.work = null;
  try {
    const r = await post("/plaza/api/work", { id: S.id, eq: w.eq.id, phase: "done" });
    floater(S.me, `${r.was === "ok" ? "OK ✓" : "✓"} ${w.eq.id} ${r.label} 완료  +${r.gained} XP`, "#7be08f", 2200);
    S.me.cheer = performance.now(); for (let i = 0; i < 14; i++) puff(S.me.x + 16, S.me.y - 10, (Math.random() - .5) * 60, -30 - Math.random() * 40, 900, i % 2 ? "#ffe066" : "#7be08f");
    if (r.lv > (S.me.lv || 1)) floater(S.me, `레벨 업!  Lv ${r.lv}`, "#ffd84a", 2600);
    S.me.xp = r.xp; S.me.lv = r.lv;
  } catch (err) { floater(S.me, err.message, "#ffb3a8", 2000); }
}

// ── NPC (역할별 작업자 — 정해진 설비를 돌며 일함) ──────────────────────────────
// 누구 화면에서나 같은 자리에 보이도록 위치를 '지금 시각'으로 계산한다 (서버 없이, 길은 A*).
// NPC 는 공격 · 회복 대상이 아니고, 내 캐릭터는 NPC 칸으로 못 들어간다 (NPC 는 사람을 지나쳐 감).
const NPC_DEF = [
  { name: "계장 엔지니어", kind: 2, job: 0, eqs: ["PT-101", "TT-102", "FT-103", "PT-501", "DPT-502", "TT-503"] },
  { name: "DCS 엔지니어", kind: 3, job: 1, eqs: ["CON-401", "DCS-403", "IO-404", "PLC-405", "CON-402", "MC-302"] },
  { name: "시운전 리드", kind: 4, job: 2, eqs: ["LT-505", "FT-506", "CV-504", "PT-202", "TT-204"] },
  { name: "현장 기술자", kind: 5, job: 3, eqs: ["CV-201", "FT-203", "LT-205", "CV-104", "PG-602"] },
  { name: "케이블 기술자", kind: 6, job: 4, eqs: ["JB-151", "TRAY-152", "JB-153", "TRAY-154", "JB-601", "JB-301"] },
];
const NPC_STEP = .42, NPC_WORK = 7;          // 한 칸 0.42초 · 설비마다 7초 작업
const NPCS = [];
function standOf(e) {                        // 설비 옆 설 자리 (아래쪽 먼저 — 설비를 바라봄)
  for (const [dx, dy] of [[0, 1], [-1, 0], [(e.w || 1), 0], [0, -1]]) { const x = e.x + (dx > 0 ? dx : dx < 0 ? -1 : 0), y = e.y + dy; if (inside(x, y) && !solid[at(x, y)]) return [x, y]; }
  return null;
}
function npcInit() {
  for (const [i, d] of NPC_DEF.entries()) {
    const stops = d.eqs.map(id => EQ_BY.get(id)).filter(Boolean).map(e => ({ e, s: standOf(e) })).filter(o => o.s);
    if (stops.length < 2) continue;
    const legs = []; let total = 0;
    for (let k = 0; k < stops.length; k++) {
      const a = stops[k].s, b = stops[(k + 1) % stops.length].s, path = findPath(a[0], a[1], b[0], b[1]);
      if (!path) continue;
      const walk = (path.length - 1) * NPC_STEP; legs.push({ path, walk, e: stops[(k + 1) % stops.length].e, t0: total }); total += walk + NPC_WORK;
    }
    if (!legs.length) continue;
    NPCS.push({ d, legs, total, off: i * 37.3, a: { id: "npc" + i, name: d.name, npc: true, face: { kind: d.kind }, role: "member", job: d.job,
      x: legs[0].path[0][0] * T, y: legs[0].path[0][1] * T, tx: legs[0].path[0][0], ty: legs[0].path[0][1], dir: 0, moving: false, steps: 0, hp: 100, hpMax: 100, stepMs: NPC_STEP * 1000 } });
  }
}
function npcUpdate(now) {
  const t = Date.now() / 1000;
  for (const n of NPCS) {
    const tc = (t + n.off) % n.total, a = n.a;
    let L = n.legs[n.legs.length - 1]; for (const l of n.legs) if (tc >= l.t0) L = l;
    const lt = tc - L.t0;
    if (lt < L.walk) {
      const f = lt / NPC_STEP, i = Math.min(L.path.length - 2, Math.floor(f)), k = f - i, [x0, y0] = L.path[i], [x1, y1] = L.path[i + 1];
      a.x = (x0 + (x1 - x0) * k) * T; a.y = (y0 + (y1 - y0) * k) * T; a.tx = x1; a.ty = y1; a.fx = x0; a.fy = y0;
      a.dir = x1 > x0 ? 3 : x1 < x0 ? 2 : y1 > y0 ? 0 : 1; a.moving = true; a.steps = i; a.t0 = now - k * a.stepMs; a.work = null;
      a.cheer = lt < .8 && L !== n.legs[0] ? now - lt * 1000 : 0;
    } else {
      const [x, y] = L.path[L.path.length - 1]; a.x = x * T; a.y = y * T; a.tx = a.fx = x; a.ty = a.fy = y; a.moving = false; faceTo(a, L.e);
      const age = lt - L.walk; a.work = { eq: L.e.id, kind: (EQ_ST[L.e.id] || ["ok"])[0] === "ok" ? "loop" : "repair", age, need: NPC_WORK, t0: now - age * 1000, label: "" };
    }
  }
}
const npcAt = (x, y) => NPCS.some(n => (n.a.tx === x && n.a.ty === y) || (n.a.fx === x && n.a.fy === y));

// ── 회복 오라 (유닛장 = 시운전 리드) · 작업 도구 · 지침 ─────────────────────────────
function drawHealAura(g, a, cx, cy, now) {   // 발밑 둥근 오라 — 은은한 바닥빛 · 맥동하는 점선 고리 · 퍼지는 물결 · 올라가는 빛 입자
  const R = (S.healR || 4) * T, x = a.x + 16 - cx, y = a.y + 26 - cy, k = .5 + .5 * Math.sin(now / 520);
  g.save();
  const gr = g.createRadialGradient(x, y, 4, x, y, R); gr.addColorStop(0, `rgba(90,240,170,${.16 + k * .06})`); gr.addColorStop(.75, "rgba(70,220,190,.07)"); gr.addColorStop(1, "rgba(70,220,190,0)");
  g.fillStyle = gr; g.beginPath(); g.ellipse(x, y, R, R * .62, 0, 0, Math.PI * 2); g.fill();
  for (let i = 0; i < 64; i++) { if ((i + Math.floor(now / 140)) % 4 === 0) continue; const an = i / 64 * Math.PI * 2;
    g.fillStyle = i % 2 ? "rgba(120,255,200,.75)" : "rgba(80,220,255,.6)"; g.fillRect(Math.round((x + Math.cos(an) * R) / PX) * PX, Math.round((y + Math.sin(an) * R * .62) / PX) * PX, PX, PX); }
  const w = (now / 1700) % 1; g.strokeStyle = `rgba(120,255,210,${.45 * (1 - w)})`; g.lineWidth = 2; g.beginPath(); g.ellipse(x, y, R * w, R * w * .62, 0, 0, Math.PI * 2); g.stroke();
  g.restore();
  if (Math.random() < .25) { const an = Math.random() * Math.PI * 2, r = Math.sqrt(Math.random()) * R;
    puff(a.x + 16 + Math.cos(an) * r, a.y + 26 + Math.sin(an) * r * .62, (Math.random() - .5) * 6, -30 - Math.random() * 30, 1300, Math.random() < .5 ? "#7cffc8" : "#7fe7ff"); }
}
function drawTool(g, a, sx, sy, now, w) {    // 작업 표시 — 손에 든 도구 + 진행 막대 (sx = 캐릭터 가운데, sy = 발바닥)
  const eid = typeof w.eq === "string" ? w.eq : w.eq.id, e = EQ_BY.get(eid), t = e ? e.t : "", hx = sx + ([10, 0, -14, 14][a.dir] || 10), hy = sy - 26, b = Math.floor(now / 160) % 2 * PX;
  const P = (x, y, ww, hh, col) => { g.fillStyle = col; g.fillRect(Math.round(x / PX) * PX, Math.round(y / PX) * PX, ww, hh); };
  if (w.kind === "repair") {                 // 렌치 · 불똥
    g.save(); g.translate(hx, hy); g.rotate(Math.sin(now / 90) * .6); P(-2, -12, 4, 14, "#c9d2da"); P(-5, -16, 10, 5, "#c9d2da"); P(-2, -15, 4, 3, "#2a2f36"); g.restore();
    if (Math.random() < .3) puff(hx, hy - 10, (Math.random() - .5) * 50, -20 - Math.random() * 30, 450, Math.random() < .5 ? "#ffd35a" : "#ff8a3a");
  } else if (DCS_T.has(t)) {                 // 콘솔 · 캐비닛 — 화면 빛 · 타자
    g.fillStyle = `rgba(97,179,255,${.22 + .12 * Math.sin(now / 200)})`; g.fillRect(sx - 18, sy - 52, 36, 30); P(hx - 6, hy + 6 + b, 12, 4, "#1c2230"); P(hx - 4, hy + 6 + b, 2, 2, C.grn);
  } else if (CABLE_T.has(t)) {               // 케이블 릴
    P(hx - 7, hy - 7, 14, 14, "#6e4a2b"); P(hx - 5, hy - 5, 10, 10, C.org); P(hx - 2, hy - 2, 4, 4, "#3a2716"); P(hx - 12, hy + 4 + b, 10, 2, C.org);
  } else {                                   // HART 통신기 / 루프 교정기 — 손 + 신호선
    const col = w.kind === "calib" ? C.org : C.yel; P(hx - 5, hy - 8 + b, 10, 16, col); P(hx - 3, hy - 6 + b, 6, 6, "#1d2b3a"); P(hx - 2, hy - 4 + b, 4, 1, C.grn);
    if (e) { const ex = (e.x + ((e.w || 1)) / 2) * T - (S.cam ? S.cam[0] : 0), ey = e.y * T + 6 - (S.cam ? S.cam[1] : 0);
      for (let i = 1; i < 10; i++) { if ((i + Math.floor(now / 90)) % 3) continue; const k = i / 10; P(hx + (ex - hx) * k, hy + (ey - hy) * k - Math.sin(k * Math.PI) * 10, PX, PX, "#7fe7ff"); } }
  }
  const k = Math.min(1, (now - w.t0) / (w.need * (w.need > 50 ? 1 : 1000))), bw = 40, bx = Math.round(sx - bw / 2), by = sy - HEAD_PX - 30;   // 진행 막대
  g.fillStyle = "#0b111c"; g.fillRect(bx - 1, by - 1, bw + 2, 7); g.fillStyle = "#24364f"; g.fillRect(bx, by, bw, 5);
  g.fillStyle = w.kind === "repair" ? C.org : w.kind === "calib" ? C.yel : "#5fd0ff"; g.fillRect(bx, by, Math.round(bw * k), 5);
  g.font = `bold 10px ${FONT}`; g.textAlign = "center"; g.textBaseline = "bottom"; g.lineWidth = 3; g.strokeStyle = "#0b111c";
  const lab = `${eid} ${WORK_NAME[w.kind] || ""} ${Math.round(k * 100)}%`; g.strokeText(lab, sx, by - 1); g.fillStyle = "#e9f2ff"; g.fillText(lab, sx, by - 1); g.textAlign = "left";
}
function drawEqMarks(g, cx, cy, now) {       // 설비 상태 표시 (정상 초록 점 · 경고 주황 ! · 고장 빨간 ✕ 깜빡) + 가까운 설비 [E] 안내
  const near = S.work ? null : nearEquip();
  for (const p of props) { if (!p.eq) continue; const e = p.eq, [st, busy] = EQ_ST[e.id] || ["ok", ""];
    const x = Math.round(p.x + p.img.width / 2 - cx), y = Math.round(p.y - p.img.height - cy) - 4;
    if (x < -40 || y < -40 || x > cv.clientWidth + 40 || y > cv.clientHeight + 60) continue;
    if (st === "ok") { g.fillStyle = "#0b111c"; g.fillRect(x - 3, y - 3, 6, 6); g.fillStyle = C.grn; g.fillRect(x - 2, y - 2, 4, 4); }
    else { const bob = Math.round(Math.sin(now / 220) * 2), fault = st === "fault";
      if (fault) { g.fillStyle = `rgba(224,68,58,${.18 + .14 * Math.sin(now / 150)})`; g.beginPath(); g.ellipse(x, p.y - cy - 4, 20, 9, 0, 0, Math.PI * 2); g.fill(); }
      g.fillStyle = "#0b111c"; g.fillRect(x - 7, y - 14 + bob, 14, 14); g.fillStyle = fault ? (Math.floor(now / 300) % 2 ? C.red : C.redD) : C.org; g.fillRect(x - 6, y - 13 + bob, 12, 12);
      g.fillStyle = "#fff"; if (fault) { for (let i = 0; i < 6; i++) { g.fillRect(x - 4 + i, y - 11 + i + bob, 2, 2); g.fillRect(x + 2 - i, y - 11 + i + bob, 2, 2); } }
      else { g.fillRect(x - 1, y - 11 + bob, 2, 5); g.fillRect(x - 1, y - 4 + bob, 2, 2); } }
    if (busy) { g.font = `10px ${FONT}`; g.textAlign = "center"; g.fillStyle = "#e9f2ff"; g.strokeStyle = "#0b111c"; g.lineWidth = 3; g.strokeText(`${busy} 작업 중`, x, y - 18); g.fillText(`${busy} 작업 중`, x, y - 18); g.textAlign = "left"; }
    if (near === e) {                         // [E] 점검 안내
      const txt = `[E] ${e.id} ${e.name} — ${ST_NAME[st]}: ${st === "ok" ? "Loop Check" : st === "warn" ? "교정" : "수리"}`;
      g.font = `bold 11px ${FONT}`; const tw = Math.ceil(g.measureText(txt).width) + 14, bx = Math.round(x - tw / 2), by = y - 40;
      g.fillStyle = "rgba(11,17,28,.86)"; roundRect(g, bx, by, tw, 20, 4); g.fill(); g.strokeStyle = st === "ok" ? "#5fd0ff" : st === "warn" ? C.org : C.red; g.lineWidth = 1.5; g.stroke();
      g.fillStyle = "#e9f2ff"; g.textBaseline = "middle"; g.fillText(txt, bx + 7, by + 10); g.textBaseline = "alphabetic";
    }
  }
}
let hudAt = 0;
function updateHud(now) {                    // 왼쪽 위 작은 판 — HP · 기력 · 레벨/XP · 지금 하는 일 · 설비 현황 (초당 6번만)
  if (now - hudAt < 160 || !S.me) return; hudAt = now;
  const set = (id, v) => { const el = document.getElementById(id); if (el && el.textContent !== v) el.textContent = v; };
  const bar = (id, k) => { const el = document.getElementById(id); if (el) el.style.width = Math.round(Math.max(0, Math.min(1, k)) * 100) + "%"; };
  const hp = Math.round(S.me.hpShow ?? S.me.hp), lv = S.me.lv || 1, xp = S.me.xp || 0, lo = 25 * (lv - 1) ** 2, hi = 25 * lv ** 2;
  bar("hud-hp", hp / (S.me.hpMax || 100)); set("hud-hpt", S.me.ghost ? "유령" : `${hp}/${S.me.hpMax || 100}`);
  bar("hud-st", S.stamina / ST_MAX); set("hud-stt", `${Math.round(S.stamina)}` + (S.stamina < ST_TIRED ? " 지침" : ""));
  bar("hud-xp", (xp - lo) / Math.max(1, hi - lo)); set("hud-lv", `Lv ${lv}`); set("hud-xpt", `${xp} XP`);
  set("hud-job", `${(S.jobs || [])[S.me.job ?? 0] || ""}${S.role === "unit" ? " · 회복 오라" : ""}`);
  const w = S.work; set("hud-work", w ? `${w.eq.id} ${WORK_NAME[w.kind]} ${Math.min(100, Math.round((now - w.t0) / w.need * 100))}%` : S.healNear ? "유닛장 회복 오라 안 — 체력 · 기력 회복 중" : "대기 — 설비 옆에서 E");
  const c = { ok: 0, warn: 0, fault: 0 }; for (const v of Object.values(EQ_ST)) c[v[0]] = (c[v[0]] || 0) + 1;
  set("hud-eq", `설비 정상 ${c.ok} · 경고 ${c.warn} · 고장 ${c.fault}`);
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

function epcFields(a, p, tnow) {            // 경험치 · 직무 · 회복 오라 · 회복(+1) · 축하
  a.xp = p.xp || 0; a.lv = p.lv || 1; a.job = p.job ?? 0; a.healer = !!p.healer;
  if ((p.heal_seq || 0) !== a.healseq) { if (a.healseq != null && p.heal_age < 1.5) { floater(a, "+1 HP", "#7cffc8", 1100);
    for (let i = 0; i < 5; i++) puff(a.x + 8 + Math.random() * 16, a.y + 20, (Math.random() - .5) * 10, -34 - Math.random() * 20, 900, i % 2 ? "#7cffc8" : "#c8fff0"); }
    a.healseq = p.heal_seq || 0; }
  if (p.cheer_age != null && p.cheer_age < 1 && a !== S.me) a.cheer = tnow - p.cheer_age * 1000;
}
function applySnapshot(s) {
  if (s.eq) Object.assign(EQ_ST, s.eq);
  if (s.heal_r) S.healR = s.heal_r;
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
      epcFields(S.me, p, tnow);
      continue;
    }
    let a = S.others.get(p.id);
    if (!a) { a = newActor(p); S.others.set(p.id, a); }
    a.name = p.name; a.face = p.face || null; a.role = p.role || "member"; a.status = p.status || "";
    a.hp = p.hp ?? 100; a.hpMax = p.hp_max || 100; a.ghost = !!p.ghost; a.kills = p.kills || 0; a.killer = !!p.killer;
    epcFields(a, p, tnow);
    a.work = p.work ? { ...p.work, t0: tnow - p.work.age * 1000 } : null;
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
  $("#pz-online").textContent = `접속 ${s.online}명` + (S.me && S.me.ghost ? " · 나는 유령 (주간 마감 때 부활)" : "");
  const who = $("#pz-who"); who.textContent = "";
  const b = document.createElement("b"); b.textContent = "광장에 있는 사람"; who.append(b);
  const order = { leader: 0, unit: 1, member: 2, operator: 3 };
  for (const p of [...s.players].sort((u, v) => (order[u.role] ?? 2) - (order[v.role] ?? 2))) {
    const d = document.createElement("div");
    if (ROLE_LABEL[p.role]) { const t = document.createElement("span"); t.className = "role " + p.role; t.textContent = ROLE_LABEL[p.role]; d.append(t); }
    if (p.killer) { const t = document.createElement("span"); t.className = "role killer"; t.textContent = `killer ${p.kills}`; d.append(t); }
    d.append(document.createTextNode(p.name + (p.id === S.id ? " (나)" : "") + (p.ghost ? " [유령]" : "") + (p.status ? ` (${p.status})` : "")));
    const sm = document.createElement("small"); sm.className = "hpv"; sm.textContent = ` ${JOB_SHORT[p.job ?? 0] || ""} · Lv${p.lv || 1} · ${p.hp ?? 100}`; d.append(sm);
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
const KEYDIR = { ArrowDown: 0, ArrowUp: 1, ArrowLeft: 2, ArrowRight: 3, Down: 0, Up: 1, Left: 2, Right: 3, KeyS: 0, KeyW: 1, KeyA: 2, KeyD: 3 };   // WASD 도 (code — 한글 입력기여도 됨)
const KEYCODE = { 40: "ArrowDown", 38: "ArrowUp", 37: "ArrowLeft", 39: "ArrowRight" };
function arrowOf(ev) { return [ev.code, ev.key, KEYCODE[ev.keyCode]].find(k => k && k in KEYDIR) || null; }
function heldDir() { const ks = [...S.keys]; return ks.length ? KEYDIR[ks[ks.length - 1]] : null; }
function stepActor(a, now, mine) {
  if (a.moving) {
    const k = Math.min(1, (now - a.t0) / (a.stepMs || STEP_MS));
    a.x = (a.from[0] + (a.tx - a.from[0]) * k) * T; a.y = (a.from[1] + (a.ty - a.from[1]) * k) * T;
    if (k >= 1) { a.moving = false; a.steps++; }
  }
  if (!a.moving && mine && !(a.attack && now - a.attack < ATK_MS)) {
    const d = heldDir();
    if (d != null && !S.typing && !S.panel) {
      const [dx, dy] = DIRV[d]; const changed = a.dir !== d; a.dir = d;
      if (walkable(a.tx + dx, a.ty + dy) && !occupied(a.tx + dx, a.ty + dy)) {
        if (S.work) cancelWork();                     // 걸으면 작업은 그만
        a.running = S.run && S.stamina > 5; a.stepMs = a.running ? RUN_MS : S.stamina < ST_TIRED ? TIRED_MS : STEP_MS;
        a.from = [a.tx, a.ty]; a.tx += dx; a.ty += dy; a.t0 = now; a.moving = true; sendMove(); }
      else if (changed) sendMove();
    }
  }
  if (!a.moving && !mine && (a.tx !== a.gx || a.ty !== a.gy)) {   // 남의 캐릭터 — 서버 칸으로 한 칸씩
    const dx = Math.sign(a.gx - a.tx), dy = dx ? 0 : Math.sign(a.gy - a.ty);
    a.stepMs = Math.abs(a.gx - a.tx) + Math.abs(a.gy - a.ty) > 1 ? RUN_MS : STEP_MS;   // 밀려 있으면(달리는 중) 빨리
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
  g.strokeText(a.name, x0 + kw + tw, y); g.fillStyle = a.npc ? "#b9c6d6" : kc || (mine ? "#ffe066" : "#ffffff"); g.fillText(a.name, x0 + kw + tw, y);
  if (a.killer) g.restore();
}

function hpBar(g, cx, y, a) {               // 이름 밑 체력 막대 (100, 부드럽게 늘어남) · 그 밑 직무 — 유령이면 '유령' · NPC 는 직무만
  if (a.npc) { jobTag(g, cx, y, a); return; }
  if (!a.ghost) jobTag(g, cx, y + 6, a);
  if (a.ghost) { g.font = `bold 11px ${FONT}`; g.textBaseline = "top"; g.textAlign = "center"; g.lineWidth = 3; g.strokeStyle = "#111";
    g.strokeText("유령", cx, y); g.fillStyle = "#cfe3ff"; g.fillText("유령", cx, y); g.textAlign = "left"; return; }
  const w = 32, k = Math.max(0, Math.min(1, (a.hpShow ?? a.hp) / (a.hpMax || 100))), x = Math.round(cx - w / 2);
  g.fillStyle = "#111"; g.fillRect(x - 1, y - 1, w + 2, 6);
  g.fillStyle = "#4a1410"; g.fillRect(x, y, w, 4);
  g.fillStyle = k > .5 ? "#4cd964" : k > .2 ? "#ffcc33" : "#ff4b3a"; g.fillRect(x, y, Math.max(k > 0 ? 1 : 0, Math.round(w * k)), 4);
}
function jobTag(g, cx, y, a) {
  g.font = `bold 10px ${FONT}`; g.textBaseline = "top"; g.textAlign = "center"; g.lineWidth = 3; g.strokeStyle = "#0b111c";
  const t = (a.npc ? "NPC · " : "") + (JOB_SHORT[a.job ?? 0] || "") + (a.npc ? "" : ` Lv${a.lv || 1}`);
  g.strokeText(t, cx, y); g.fillStyle = JOB_COL[a.job ?? 0] || "#ccc"; g.fillText(t, cx, y); g.textAlign = "left";
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
  const cheer = a.cheer && now - a.cheer < 900 ? (now - a.cheer) / 900 : -1;      // 작업 끝 — 세 번 깡충
  if (cheer >= 0) { sy -= Math.round(Math.abs(Math.sin(cheer * Math.PI * 3)) * 8 / PX) * PX; if (Math.random() < .2) puff(a.x + 16, a.y, (Math.random() - .5) * 40, -30, 700, "#ffe066"); }
  drawActorBody(g, a, sx, sy, now);
  const w = a === S.me ? S.work : a.work;
  if (w) drawTool(g, a, sx + 16, sy + 28, now, w);
  if (a === S.me && S.stamina < ST_TIRED && Math.floor(now / 400) % 3 === 0) { g.fillStyle = "#7fe7ff"; g.fillRect(sx + 26, sy + 28 - HEAD_PX + 10 + Math.floor(now / 100) % 4 * 2, 4, 6); }   // 땀
  if (a === S.me && a.moving && a.running && Math.random() < .5) puff(a.x + 16, a.y + 28, (Math.random() - .5) * 20, -6, 400, "#9aa6b1");   // 흙먼지
}
function drawActorBody(g, a, sx, sy, now) {
  const k = a.moving ? Math.min(1, (now - a.t0) / (a.stepMs || STEP_MS)) : 0;
  const fr = a.moving && k > .15 && k < .85 ? (a.steps % 2 ? 1 : 2) : 0;
  const atk = a.attack && now - a.attack < ATK_MS ? (now - a.attack) / ATK_MS : -1;
  const hit = a.hit && now - a.hit.t0 < HIT_MS ? (now - a.hit.t0) / HIT_MS : -1;
  let ox = 0, oy = 0;
  if (atk >= 0) { const [dx, dy] = DIRV[a.dir], l = Math.sin(atk * Math.PI) * 3; ox = Math.round(dx * l); oy = Math.round(dy * l); }
  if (hit >= 0 && hit < .5) ox += Math.round(Math.sin(hit * 60) * 2);
  const F = a.npc ? a.face : roleFace(faceOf(a), a.role);
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
  const dt = Math.min(.1, (now - (S.lastFrame || now)) / 1000); S.lastFrame = now;
  stepActor(S.me, now, true);
  for (const a of S.others.values()) stepActor(a, now, false);
  npcUpdate(now);
  const healers = [S.me, ...S.others.values()].filter(a => a.healer && !a.ghost);
  S.healNear = healers.some(h => h !== S.me && Math.hypot(h.tx - S.me.tx, h.ty - S.me.ty) <= (S.healR || 4));
  if (S.me.moving && S.me.running) S.stamina = Math.max(0, S.stamina - ST_RUN * dt);
  else S.stamina = Math.min(ST_MAX, S.stamina + ST_REGEN * (S.healNear ? 2 : 1) * dt);   // 쉬면 · 유닛장 곁이면 2배
  for (const a of [S.me, ...S.others.values()]) a.hpShow = (a.hpShow ?? a.hp) + (a.hp - (a.hpShow ?? a.hp)) * Math.min(1, dt * 5);
  if (S.work && now - S.work.t0 >= S.work.need) finishWork();
  const vw = cv.clientWidth, vh = cv.clientHeight;
  let cx = Math.round(S.me.x + T / 2 - vw / 2), cy = Math.round(S.me.y + T / 2 - vh / 2);
  cx = W * T <= vw ? Math.round((W * T - vw) / 2) : Math.max(-FRAME, Math.min(W * T - vw + FRAME, cx));
  cy = H * T <= vh ? Math.round((H * T - vh) / 2) : Math.max(-FRAME, Math.min(H * T - vh + FRAME, cy));
  S.cam = [cx, cy];                          // 캐릭터 누르기(actorAt)에 씀
  ctx.fillStyle = "#0d1320"; ctx.fillRect(0, 0, vw, vh);
  ctx.drawImage(groundImg, -cx, -cy);
  for (const h of healers) drawHealAura(ctx, h, cx, cy, now);     // 바닥 효과 층 (사람 · 설비보다 밑)
  const actors = [S.me, ...S.others.values()], npcs = NPCS.map(n => n.a);
  const items = [];
  for (const p of props) if (p.x - cx < vw + 40 && p.x + p.img.width - cx > -40 && p.y - cy > -10 && p.y - p.img.height - cy < vh + 10) items.push({ y: p.z ?? p.y, p });
  for (const a of actors.concat(npcs)) items.push({ y: a.y + 28, a });
  items.sort((u, v) => u.y - v.y);
  for (const it of items) {
    if (it.p) {
      const p = it.p, mx = S.me.x + 16, my = S.me.y + 28;    // 건물 · 큰 좌판 뒤에 내가 서면 반투명하게 (가려도 보이게)
      const behind = p.fade && mx > p.x + 6 && mx < p.x + p.img.width - 6 && my < p.y - 4 && my > p.y - p.img.height + 24;
      if (behind) { ctx.save(); ctx.globalAlpha = .55; }
      ctx.drawImage(p.img, Math.round(p.x - cx), Math.round(p.y - p.img.height - cy));
      if (p.anim) p.anim(ctx, Math.round(p.x - cx) + PX, Math.round(p.y - p.img.height - cy) + PX, now);
      if (behind) ctx.restore();
      continue;
    }
    drawActor(ctx, it.a, Math.round(it.a.x - cx), Math.round(it.a.y - cy), now);
  }
  drawParts(ctx, cx, cy, now);              // 효과 층 (입자)
  drawEqMarks(ctx, cx, cy, now);            // 설비 상태 · [E] 안내
  const boxes = [];
  for (const a of actors.concat(npcs)) {    // 이름 · 말풍선은 맨 위
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
  drawFloats(ctx, cx, cy, now);
  ctx.drawImage(frameImg(vw, vh), 0, 0);
  updateHud(now);
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
function jobRow() {                        // 직무 — 유닛장은 '시운전 리드' 고정 (회복 오라), 다른 사람은 시운전 리드를 못 고름
  const J = S.jobs || [];
  if (S.role === "unit") { const row = document.createElement("div"); row.className = "frow"; const l = document.createElement("label"); l.textContent = "직무";
    const v = document.createElement("span"); v.className = "fval"; v.textContent = "시운전 리드 (유닛장)"; row.append(l, v); return row; }
  if (draft.job === 2) draft.job = 0;
  return arrowRow("job", "직무", J, i => i === 2);
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
    const rows = $("#pz-facerows"); rows.textContent = ""; rows.append(kindRow(), jobRow()); return;
  }
  const cat = isCat(draft);
  $("#pz-hairs").hidden = cat; $("#pz-hairs").previousElementSibling.hidden = cat;   // '머리 모양' 은 사람일 때만
  if (cat) { const rows = $("#pz-facerows"); rows.textContent = ""; rows.append(kindRow(), jobRow());
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
  rows.append(kindRow(), jobRow());
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
$("#pz-face-rand").onclick = () => { for (const k of Object.keys(RANGES)) if (k !== "kind" && k !== "job") draft[k] = Math.floor(Math.random() * RANGES[k]); buildFace(); };   // 종류 · 직무는 그대로   // 종류(고양이 · 사람)는 그대로

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
  S.run = ev.shiftKey;
  if (!S.typing && !S.panel && (ev.code === "KeyE" || ev.key === "e" || ev.key === "E")) { ev.preventDefault(); if (!ev.repeat) interact(); return; }   // 점검 · 수리
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
document.addEventListener("keyup", ev => { S.run = ev.shiftKey; const a = arrowOf(ev); if (a) S.keys.delete(a); if (ev.key === " " || ev.code === "Space" || ev.keyCode === 32) S.atkHeld = false; });
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
window.__plazaDebug = { charSprite, defaultFace, RANGES, catSprite, CAT, solid, ground, W, H, props, WORLD, EQUIP, EQ_ST, NPCS, findPath };
if (EMBED) document.body.classList.add("embed");
resize(); requestAnimationFrame(frame);
const nm = (Q.get("user") || "").trim() || storedName();
if (nm) start(nm); else askName();
})();
