/* Phase 2 회귀 테스트 픽스처 — HP Steam (p6, D00P-10LBA10-M05-0001)
 *
 * 실제 타일 이미지를 눈으로 읽어 만든 "Pass 2 가 이렇게 답해야 맞다" 는 정답 응답이다.
 * 이걸로 검증하는 것은 **파이프라인**(중복 제거·정렬·Q'ty·DESCRIPTION 조립·공급 역무
 * 분리)이지 모델의 판독력이 아니다. 판독력은 실호출로만 잴 수 있다.
 *
 * 계기는 **페이지 좌표로 한 번만** 적는다. 타일 배분은 계산으로 한다.
 * 분할을 3×3 에서 4×4 로 바꿔도 픽스처를 다시 쓰지 않아도 된다 — 격자를 바꿀 때마다
 * 손으로 좌표를 옮기면 그 자체가 오류원이 된다.
 *
 * 좌표 출처: PDF 텍스트 레이어의 계기 문자 위치 34건 (도면의 계기 총수와 일치).
 * 공급 역무(vs)와 배관 맥락(line/pos)은 타일 이미지에서 읽었다.
 */

/** 도면 위 계기 34건. x,y 는 페이지 정규 좌표. */
const PAGE_ITEMS = [];

const add = (type, x, y, o = {}) => PAGE_ITEMS.push({
  type, x, y,
  line_context: o.line || null, equipment: o.eq || 'HP STEAM', position: o.pos || null,
  redundancy: o.red || null, vendor_scope: o.vs || null, note_ref: o.note || null,
});

/* HRSG 출구 한 벌 — 전부 `*` (HRSG 공급 범위). 상·하반부 동일 구조. */
for (const [unit, y] of [[12, 0.282], [11, 0.600]]) {
  const from = `FROM HRSG#${unit}`;
  add('TIT', 0.110, y, { line: from, vs: '*' });
  add('TIT', 0.121, y, { line: from, vs: '*' });
  add('TIT', 0.131, y, { line: from, vs: '*' });
  add('PIT', 0.142, y, { line: from, vs: '*' });
  add('PIT', 0.153, y, { line: from, vs: '*' });
  // 점선 박스 안 유량 3점 — 박스 우상단에 `*` 하나가 박스 전체에 걸린다
  add('FIT', 0.195, y - 0.019, { line: from, vs: '*' });
  add('FIT', 0.195, y + 0.005, { line: from, vs: '*' });
  add('FE',  0.195, y + 0.028, { line: from, vs: '*' });
  // SCT/HRSG 경계 하류 — 여기서부터 우리 범위
  add('PIT', 0.278, y, { line: `${from} / DN550`, red: 'A' });
  add('TIT', 0.289, y, { line: `${from} / DN550`, red: 'A' });
}

/* 각 호기 드레인 (DN300 → TO HRSG#nn BD TANK) */
add('TIT', 0.321, 0.359, { line: 'TO HRSG#12 BD TANK', pos: 'DRAIN' });
add('TIT', 0.321, 0.376, { line: 'TO HRSG#12 BD TANK', pos: 'DRAIN' });
add('TIT', 0.321, 0.673, { line: 'TO HRSG#11 BD TANK', pos: 'DRAIN' });
add('TIT', 0.321, 0.690, { line: 'TO HRSG#11 BD TANK', pos: 'DRAIN' });

/* STG#10 터빈 입구 — 전부 `**` (ST SUPPLIER 공급 범위) */
for (const [type, x, y] of [
  ['TIT', 0.500, 0.456], ['PIT', 0.500, 0.532], ['PIT', 0.500, 0.557],
  ['TIT', 0.562, 0.456], ['TIT', 0.562, 0.482], ['PIT', 0.562, 0.557],
]) add(type, x, y, { line: 'TO STG#10', eq: 'HP TURBINE', vs: '**' });

/* 그룹 공용 헤더 드레인 (DN350 → TO CLEAN DRAIN TANK) */
for (const [x, y] of [[0.558, 0.678], [0.558, 0.695], [0.394, 0.788], [0.394, 0.805]])
  add('TIT', x, y, { line: 'TO CLEAN DRAIN TANK', pos: 'DRAIN' });

/** index.html 의 tileRects() 와 같은 계산. 겹침 10%. */
function tileRects(cols, rows, overlap = 0.10) {
  const out = [];
  const ovx = (1 / cols) * overlap, ovy = (1 / rows) * overlap;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const x0 = Math.max(0, c / cols - ovx / 2), x1 = Math.min(1, (c + 1) / cols + ovx / 2);
      const y0 = Math.max(0, r / rows - ovy / 2), y1 = Math.min(1, (r + 1) / rows + ovy / 2);
      out.push({ r, c, x: x0, y: y0, w: x1 - x0, h: y1 - y0 });
    }
  }
  return out;
}

/** 격자에 맞춰 타일별 응답을 만든다. 타일에 걸친 계기는 양쪽에 다 들어간다(겹침). */
export function fixtureFor(cols = 4, rows = 4, page = 6) {
  const fx = {};
  for (const rect of tileRects(cols, rows)) {
    fx[`p${page}:r${rect.r}c${rect.c}`] = PAGE_ITEMS
      .filter((it) => it.x >= rect.x && it.x < rect.x + rect.w
                   && it.y >= rect.y && it.y < rect.y + rect.h)
      .map((it) => ({
        type: it.type,
        x: +((it.x - rect.x) / rect.w).toFixed(4),
        y: +((it.y - rect.y) / rect.h).toFixed(4),
        line_context: it.line_context, equipment: it.equipment, position: it.position,
        redundancy: it.redundancy, vendor_scope: it.vendor_scope, note_ref: it.note_ref,
      }));
  }
  return fx;
}

/** 타일당 계기 수 — max_tokens 상한(8개)을 넘는지 보는 용도. */
export function loadPerTile(cols, rows) {
  const fx = fixtureFor(cols, rows);
  return Object.fromEntries(Object.entries(fx).filter(([, v]) => v.length).map(([k, v]) => [k, v.length]));
}

export const PAGE_ITEM_COUNT = PAGE_ITEMS.length;
export const FIXTURE_P6 = fixtureFor(4, 4);

/* ── p38 · CCW (D00P-10PGB10-M05-0004) ─────────────────────────────────────
 * 여러 도면을 한 번에 돌리는 경로를 시험하려고 둘째 도면을 붙인다.
 * 이 도면에는 공급 역무 표기가 없다. 공급 헤더 분기 8곳에 PI, 회수 라인 8곳에
 * PI 와 TI. 좌표는 텍스트 레이어에서 뽑은 24건 그대로다.
 */
const CCW_BRANCHES = [
  'AUXILIARY BOILER COOLER', 'UNIT #11 BFP A/B COOLER', 'UNIT #11 BFP A/B COOLER',
  'UNIT #11 BFP A/B MOTOR COOLER', 'UNIT #11 BFP A/B MOTOR COOLER',
  'UNIT #11 HRSG COOLERS', 'UNIT #11 HRSG COOLERS', 'UNIT #11 SAMPLING SYSTEM',
];
const CCW_SUPPLY_X = [0.102, 0.220, 0.280, 0.343, 0.396, 0.459, 0.512, 0.595];
const CCW_RETURN_X = [0.172, 0.289, 0.343, 0.406, 0.459, 0.522, 0.575, 0.665];

const CCW_ITEMS = [];
CCW_SUPPLY_X.forEach((x, i) => CCW_ITEMS.push({
  type: 'PI', x, y: 0.281, line_context: 'FROM GROUP#20 CCW SUPPLY',
  equipment: `${CCW_BRANCHES[i]} CCW`, position: 'SUPPLY',
  redundancy: null, vendor_scope: null, note_ref: null,
}));
CCW_RETURN_X.forEach((x, i) => {
  for (const [type, y] of [['PI', 0.674], ['TI', i === 0 ? 0.703 : 0.700]]) {
    CCW_ITEMS.push({
      type, x, y, line_context: 'TO GROUP#20 CCW RETURN',
      equipment: `${CCW_BRANCHES[i]} CCW`, position: 'RETURN',
      redundancy: null, vendor_scope: null, note_ref: null,
    });
  }
});

function fixtureFrom(items, cols, rows, page) {
  const fx = {};
  for (const rect of tileRects(cols, rows)) {
    fx[`p${page}:r${rect.r}c${rect.c}`] = items
      .filter((it) => it.x >= rect.x && it.x < rect.x + rect.w
                   && it.y >= rect.y && it.y < rect.y + rect.h)
      .map((it) => ({ ...it,
        x: +((it.x - rect.x) / rect.w).toFixed(4),
        y: +((it.y - rect.y) / rect.h).toFixed(4) }));
  }
  return fx;
}

/** 6쪽(HP Steam) + 38쪽(CCW) 을 한 번에. 여러 도면 선택 경로 시험용. */
export function fixtureMulti(cols = 4, rows = 4) {
  return { ...fixtureFor(cols, rows, 6), ...fixtureFrom(CCW_ITEMS, cols, rows, 38) };
}
export const CCW_ITEM_COUNT = CCW_ITEMS.length;
