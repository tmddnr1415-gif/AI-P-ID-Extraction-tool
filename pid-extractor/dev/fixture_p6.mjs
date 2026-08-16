/* Phase 2 검증 픽스처 — HP Steam (p6, D00P-10LBA10-M05-0001)
 *
 * 실제 타일 이미지(r0c0 / r1c0 / r2c1)를 눈으로 읽어 만든 "Pass 2 가 이렇게 답해야
 * 맞다" 는 정답 응답이다. 좌표는 텍스트 레이어의 계기 문자 위치를 타일 상대좌표로
 * 환산했다. 이걸로 검증하는 것은 **파이프라인**(중복 제거·정렬·Q'ty·DESCRIPTION
 * 조립)이지 모델의 판독력이 아니다. 판독력은 실제 호출로만 잴 수 있다.
 */

// 3×3 · 10% 겹침 타일의 페이지 좌표 범위
const R = {
  c0: { x: 0, w: 0.35 }, c1: { x: 0.31667, w: 0.36667 }, c2: { x: 0.65, w: 0.35 },
  r0: { y: 0, h: 0.35 }, r1: { y: 0.31667, h: 0.36667 }, r2: { y: 0.65, h: 0.35 },
};
const rel = (tile, px, py) => {
  const [r, c] = [tile[1], tile[3]];
  const cc = R['c' + c], rr = R['r' + r];
  return { x: +((px - cc.x) / cc.w).toFixed(4), y: +((py - rr.y) / rr.h).toFixed(4) };
};

/** 계기 하나. page 좌표를 주면 타일 상대좌표로 바꿔 준다. */
const I = (tile, type, px, py, o = {}) => ({
  type, ...rel(tile, px, py),
  line_context: o.line || null, equipment: o.eq || null, position: o.pos || null,
  redundancy: o.red || null, vendor_scope: o.vs || null, note_ref: o.note || null,
});

/* HRSG 공급 범위(`*`)로 묶인 한 벌 — 출구 계기 5개 + 유량 3개. 상·하반부 동일. */
const hrsgSet = (tile, y0, unit) => [
  I(tile, 'TIT', 0.110, y0, { line: `FROM HRSG#${unit}`, eq: 'HP STEAM', vs: '*' }),
  I(tile, 'TIT', 0.121, y0, { line: `FROM HRSG#${unit}`, eq: 'HP STEAM', vs: '*' }),
  I(tile, 'TIT', 0.131, y0, { line: `FROM HRSG#${unit}`, eq: 'HP STEAM', vs: '*' }),
  I(tile, 'PIT', 0.142, y0, { line: `FROM HRSG#${unit}`, eq: 'HP STEAM', vs: '*' }),
  I(tile, 'PIT', 0.153, y0, { line: `FROM HRSG#${unit}`, eq: 'HP STEAM', vs: '*' }),
  I(tile, 'FIT', 0.195, y0 - 0.019, { line: `FROM HRSG#${unit}`, eq: 'HP STEAM', vs: '*' }),
  I(tile, 'FIT', 0.195, y0 + 0.005, { line: `FROM HRSG#${unit}`, eq: 'HP STEAM', vs: '*' }),
  I(tile, 'FE', 0.195, y0 + 0.028, { line: `FROM HRSG#${unit}`, eq: 'HP STEAM', vs: '*' }),
];

/* SCT/HRSG 경계 하류의 우리 범위 계기 — 주증기 압력·온도 한 쌍. */
const mainPair = (tile, y0, unit) => [
  I(tile, 'PIT', 0.278, y0, { line: `FROM HRSG#${unit} / DN550`, eq: 'HP STEAM', red: 'A' }),
  I(tile, 'TIT', 0.289, y0, { line: `FROM HRSG#${unit} / DN550`, eq: 'HP STEAM', red: 'A' }),
];

export const FIXTURE_P6 = {
  'p6:r0c0': [...hrsgSet('r0c0', 0.282, 12), ...mainPair('r0c0', 0.282, 12)],

  'p6:r0c1': [],
  'p6:r0c2': [],

  'p6:r1c0': [
    // HRSG#12 드레인 (DN300 → TO HRSG#12 BD TANK)
    I('r1c0', 'TIT', 0.321, 0.359, { line: 'TO HRSG#12 BD TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
    I('r1c0', 'TIT', 0.321, 0.376, { line: 'TO HRSG#12 BD TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
    ...hrsgSet('r1c0', 0.600, 11),
    ...mainPair('r1c0', 0.600, 11),
    I('r1c0', 'TIT', 0.321, 0.673, { line: 'TO HRSG#11 BD TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
  ],

  'p6:r1c1': [
    I('r1c1', 'TIT', 0.321, 0.359, { line: 'TO HRSG#12 BD TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
    I('r1c1', 'TIT', 0.321, 0.376, { line: 'TO HRSG#12 BD TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
    // STG#10 터빈 입구 — ** (ST SUPPLIER 공급 범위)
    I('r1c1', 'TIT', 0.500, 0.456, { line: 'TO STG#10', eq: 'HP TURBINE', vs: '**' }),
    I('r1c1', 'PIT', 0.500, 0.532, { line: 'TO STG#10', eq: 'HP TURBINE', vs: '**' }),
    I('r1c1', 'PIT', 0.500, 0.557, { line: 'TO STG#10', eq: 'HP TURBINE', vs: '**' }),
    I('r1c1', 'TIT', 0.562, 0.456, { line: 'TO STG#10', eq: 'HP TURBINE', vs: '**' }),
    I('r1c1', 'TIT', 0.562, 0.482, { line: 'TO STG#10', eq: 'HP TURBINE', vs: '**' }),
    I('r1c1', 'PIT', 0.562, 0.557, { line: 'TO STG#10', eq: 'HP TURBINE', vs: '**' }),
    I('r1c1', 'TIT', 0.321, 0.673, { line: 'TO HRSG#11 BD TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
    I('r1c1', 'TIT', 0.558, 0.678, { line: 'TO CLEAN DRAIN TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
  ],

  'p6:r1c2': [],

  'p6:r2c0': [
    I('r2c0', 'TIT', 0.321, 0.673, { line: 'TO HRSG#11 BD TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
    I('r2c0', 'TIT', 0.321, 0.690, { line: 'TO HRSG#11 BD TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
  ],

  'p6:r2c1': [
    I('r2c1', 'TIT', 0.321, 0.673, { line: 'TO HRSG#11 BD TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
    I('r2c1', 'TIT', 0.321, 0.690, { line: 'TO HRSG#11 BD TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
    I('r2c1', 'TIT', 0.558, 0.678, { line: 'TO CLEAN DRAIN TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
    I('r2c1', 'TIT', 0.558, 0.695, { line: 'TO CLEAN DRAIN TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
    I('r2c1', 'TIT', 0.394, 0.788, { line: 'TO CLEAN DRAIN TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
    I('r2c1', 'TIT', 0.394, 0.805, { line: 'TO CLEAN DRAIN TANK', eq: 'HP STEAM', pos: 'DRAIN' }),
  ],

  'p6:r2c2': [],
};
