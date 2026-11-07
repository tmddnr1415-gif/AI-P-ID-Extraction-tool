/* Anatomy — 계측제어 품목을 "부품 단위"로 분해한 파라메트릭 3D 정의.
 *
 * 품목 하나 = 파라미터 목록 + build(파라미터) → 부품(part) 목록.
 * 부품 = 이름 붙은 기본 도형(prim) 묶음. three.js 에 의존하지 않는 순수 데이터라
 * 브라우저 뷰어, Node 검증 스크립트, Claude 스킬이 같은 정의를 공유한다.
 *
 * 좌표계: mm, Y 위쪽.
 *   밸브     — 원점 = 배관 중심선과 밸브 중심, 배관 축 = X
 *   캐비닛   — 원점 = 바닥 위, 첫 베이의 전면 중앙 하단. 전면 = +Z
 *   훅업     — 원점 = 바닥(Y=0) 위, 공정배관 탭 바로 아래. 공정배관 축 = X
 *
 * 치수 출처(source) 는 네 가지로 추적한다.
 *   drawing  — 도면에서 읽은 값 (Claude 판독 또는 사람이 입력하며 도면 근거 표시)
 *   user     — 사람이 직접 고친 값
 *   standard — RefData 표준 참고표에서 가져온 값
 *   estimate — 비례식 추정값. 도면으로 확인되기 전까지는 형상 참고용
 */
'use strict';

const Anatomy = (() => {
  const R = (typeof RefData !== 'undefined') ? RefData
    : (typeof require !== 'undefined' ? require('./refdata.js') : null);

  // ───────────────────────── 기본 도형 헬퍼 ─────────────────────────
  const cyl = (axis, r, h, at, extra = {}) => ({ k: 'cyl', axis, r, h, at, ...extra });
  const cone = (axis, r, r2, h, at) => ({ k: 'cyl', axis, r, r2, h, at });
  const box = (s, at, extra = {}) => ({ k: 'box', s, at, ...extra });
  const sph = (r, at, scale) => ({ k: 'sph', r, at, ...(scale ? { scale } : {}) });
  const tor = (R0, r, axis, at) => ({ k: 'tor', R: R0, r, axis, at });
  const tube = (a, b, r) => ({ k: 'tube', a, b, r });
  const part = (id, label, mat, prims, ex = [0, 0, 0], desc = '') => ({ id, label, mat, prims, ex, desc });
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  /** 축 방향 단위벡터 성분 */
  const AX = { x: [1, 0, 0], y: [0, 1, 0], z: [0, 0, 1] };
  const along = (axis, d, base = [0, 0, 0]) => base.map((b, i) => b + AX[axis][i] * d);
  /** 축에 수직인 평면의 두 기저 */
  const perp = { x: [[0, 1, 0], [0, 0, 1]], y: [[1, 0, 0], [0, 0, 1]], z: [[1, 0, 0], [0, 1, 0]] };

  /**
   * 플랜지 끝단 하나. face = 밸브 중심에서 플랜지 면까지 거리, sign = ±1.
   * 플랜지 디스크 + 허브 + 볼트.
   */
  function flangeEnd(id, label, axis, sign, face, f, opts = {}) {
    const prims = [];
    const c = (d) => along(axis, sign * d);
    prims.push(cyl(axis, f.od / 2, f.t, c(face - f.t / 2)));
    const hubL = opts.hubL ?? f.t * 1.1;
    prims.push(cone(axis, f.pipeOD / 2 * 1.35, f.pipeOD / 2 * 1.35, hubL, c(face - f.t - hubL / 2)));
    const bolts = [];
    const [u, v] = perp[axis];
    for (let i = 0; i < f.n; i++) {
      const a = (i + 0.5) / f.n * Math.PI * 2;
      const off = [0, 1, 2].map((j) => (u[j] * Math.cos(a) + v[j] * Math.sin(a)) * f.bcd / 2);
      const base = c(face - f.t / 2 + sign * f.bolt * 0.4);
      bolts.push(cyl(axis, f.bolt / 2, f.t + f.bolt * 1.6, base.map((b, j) => b + off[j])));
    }
    const out = [part(`${id}`, label, 'flange', prims, along(axis, sign * 1),
      `RF 플랜지 Ø${f.od} × t${f.t}`)];
    out.push(part(`${id}_bolts`, `${label} 볼트`, 'bolt', bolts, along(axis, sign * 1.2),
      `${f.n} × Ø${f.bolt} @ BCD ${f.bcd}`));
    if (opts.stub) {
      out.push(part(`${id}_pipe`, `${label} 배관(참조)`, 'ghost',
        [cyl(axis, f.pipeOD / 2, opts.stub, c(face + opts.stub / 2 + 2))], along(axis, sign * 1.4),
        '배치 참조용 배관. 범위 밖'));
    }
    return out;
  }

  // ───────────────────────── 파라미터 정의 ─────────────────────────
  // p: { key, label, unit, type: 'num'|'enum'|'bool', options, default, group, when(v), std(v)→{value,src}, est(v)→value, desc }
  //   std  : 표준표로 정해지는 값 → source 'standard'
  //   est  : 비례 추정 → source 'estimate'
  //   when : 이 품목 구성에서 의미 있는 파라미터인지

  const BODY = ['globe', 'gate', 'ball', 'butterfly', 'psv'];
  const OPERATOR = ['handwheel', 'lever', 'gear', 'pneumatic_diaphragm', 'pneumatic_rotary', 'electric', 'spring'];
  const isRot = (v) => v.body === 'ball' || v.body === 'butterfly';
  const flg = (v) => R.flangeOf(v.nps, v.cls);

  const VALVE_PARAMS = [
    { key: 'tag', label: 'Tag No.', type: 'text', default: '', group: '식별' },
    { key: 'body', label: '바디 형식', type: 'enum', options: BODY, default: 'globe', group: '구성',
      desc: 'globe / gate / ball / butterfly / psv(앵글형 안전밸브)' },
    { key: 'operator', label: '조작기', type: 'enum', options: OPERATOR, default: 'pneumatic_diaphragm', group: '구성',
      desc: 'handwheel, lever, gear(웜기어), pneumatic_diaphragm(CV), pneumatic_rotary(랙피니언/스카치요크), electric(MOV), spring(PSV)' },
    { key: 'service', label: '용도', type: 'enum', options: ['control', 'on_off'], default: 'control', group: '구성',
      desc: 'control 이면 글로브 면간거리를 ISA-75.08.01 로 잡는다' },
    { key: 'nps', label: '호칭경 (inlet)', unit: 'in', type: 'num', default: 4, min: 0.5, max: 12, step: 0.25, group: '구성' },
    { key: 'cls', label: '압력등급 (inlet)', type: 'enum', options: ['150', '300'], default: '150', group: '구성' },
    { key: 'outlet_nps', label: '출구 호칭경', unit: 'in', type: 'num', group: '구성', when: (v) => v.body === 'psv',
      est: (v) => R.NPS.map(Number).find((n) => n >= v.nps * 1.5) || 12 },
    { key: 'outlet_cls', label: '출구 등급', type: 'enum', options: ['150', '300'], default: '150', group: '구성',
      when: (v) => v.body === 'psv' },

    { key: 'ftf', label: '면간거리 F-F', unit: 'mm', type: 'num', group: '바디', when: (v) => v.body !== 'psv',
      std: (v) => {
        const kind = v.body === 'globe' && v.service === 'control' ? 'control_globe' : v.body;
        const val = R.ftfOf(kind, v.nps, v.cls);
        return val ? { value: val, ref: R.SOURCES[kind] } : null;
      },
      desc: '플랜지 면과 면 사이 거리' },
    { key: 'cti', label: '중심-입구면 (C-I)', unit: 'mm', type: 'num', group: '바디', when: (v) => v.body === 'psv',
      est: (v) => Math.round(85 + 28 * v.nps), desc: '밸브 중심(출구 축)에서 입구 플랜지 면까지 수직거리' },
    { key: 'cto', label: '중심-출구면 (C-O)', unit: 'mm', type: 'num', group: '바디', when: (v) => v.body === 'psv',
      est: (v) => Math.round(95 + 32 * v.nps), desc: '밸브 중심(입구 축)에서 출구 플랜지 면까지 수평거리' },
    { key: 'body_h', label: '바디 높이 (CL→보닛 플랜지)', unit: 'mm', type: 'num', group: '바디',
      est: (v) => {
        const f = flg(v);
        return Math.round({ globe: 0.55 * f.od + 20, gate: 0.85 * f.od + 20, ball: 0.62 * f.od + 25,
          butterfly: 0.55 * f.od + 60, psv: 1.0 * f.od }[v.body]);
      } },
    { key: 'body_w', label: '바디 최대폭', unit: 'mm', type: 'num', group: '바디',
      est: (v) => {
        const f = flg(v);
        return Math.round({ globe: 0.95 * f.od, gate: 0.75 * f.od, ball: 1.0 * f.od, butterfly: 0.95 * f.od,
          psv: 0.9 * f.od }[v.body]);
      } },
    { key: 'bonnet_h', label: '보닛/넥 높이', unit: 'mm', type: 'num', group: '바디',
      est: (v) => Math.round({ globe: 70 + 25 * v.nps, gate: 90 + 45 * v.nps, ball: 40 + 12 * v.nps,
        butterfly: 40 + 10 * v.nps, psv: 160 + 70 * v.nps }[v.body]),
      desc: '보닛 플랜지 위 ~ 요크/조작기 장착면 (PSV 는 스프링 하우징 높이)' },
    { key: 'pipe_stub', label: '참조 배관 길이', unit: 'mm', type: 'num', default: 150, group: '바디',
      desc: '0 이면 표시 안 함' },

    { key: 'yoke_h', label: '요크/브래킷 높이', unit: 'mm', type: 'num', group: '조작기',
      when: (v) => ['pneumatic_diaphragm', 'pneumatic_rotary', 'electric', 'handwheel', 'gear'].includes(v.operator),
      est: (v) => Math.round({ pneumatic_diaphragm: 150 + 45 * v.nps, pneumatic_rotary: 60 + 10 * v.nps,
        electric: 90 + 25 * v.nps, handwheel: v.body === 'gate' ? 120 + 70 * v.nps : 60 + 20 * v.nps,
        gear: 50 + 10 * v.nps }[v.operator] || 100) },
    { key: 'act_d', label: '액추에이터 지름/폭', unit: 'mm', type: 'num', group: '조작기',
      when: (v) => ['pneumatic_diaphragm', 'pneumatic_rotary', 'electric', 'gear'].includes(v.operator),
      est: (v) => Math.round({ pneumatic_diaphragm: clamp(200 + 55 * v.nps, 220, 600),
        pneumatic_rotary: clamp(80 + 18 * v.nps, 90, 320), electric: clamp(230 + 15 * v.nps, 240, 450),
        gear: clamp(110 + 18 * v.nps, 120, 340) }[v.operator]) },
    { key: 'act_h', label: '액추에이터 높이', unit: 'mm', type: 'num', group: '조작기',
      when: (v) => ['pneumatic_diaphragm', 'electric', 'gear'].includes(v.operator),
      est: (v) => Math.round({ pneumatic_diaphragm: clamp(110 + 30 * v.nps, 130, 380),
        electric: clamp(300 + 18 * v.nps, 320, 560), gear: clamp(90 + 12 * v.nps, 100, 260) }[v.operator]) },
    { key: 'act_l', label: '실린더 길이 (로터리)', unit: 'mm', type: 'num', group: '조작기',
      when: (v) => v.operator === 'pneumatic_rotary', est: (v) => Math.round(clamp(240 + 60 * v.nps, 260, 900)) },
    { key: 'hw_d', label: '핸드휠 지름', unit: 'mm', type: 'num', group: '조작기',
      when: (v) => ['handwheel', 'electric', 'gear'].includes(v.operator) || (v.operator === 'pneumatic_diaphragm' && v.cv_handwheel),
      est: (v) => Math.round(clamp(100 + 40 * v.nps, 100, 610)) },
    { key: 'lever_l', label: '레버 길이', unit: 'mm', type: 'num', group: '조작기',
      when: (v) => v.operator === 'lever', est: (v) => Math.round(clamp(120 + 60 * v.nps, 120, 700)) },
    { key: 'stem_ext', label: '스템 노출 (Rising stem 열림)', unit: 'mm', type: 'num', group: '조작기',
      when: (v) => v.operator === 'handwheel' && v.body === 'gate', est: (v) => Math.round(25.4 * v.nps * 1.05) },
    { key: 'positioner', label: '포지셔너', type: 'bool', default: true, group: '조작기',
      when: (v) => ['pneumatic_diaphragm', 'pneumatic_rotary'].includes(v.operator) },
    { key: 'cv_handwheel', label: '상부 수동 핸드휠', type: 'bool', default: false, group: '조작기',
      when: (v) => v.operator === 'pneumatic_diaphragm' },
    { key: 'psv_lever', label: '리프팅 레버', type: 'bool', default: false, group: '조작기', when: (v) => v.body === 'psv' },
    { key: 'overall_h', label: '전체 높이 (CL→최상단)', unit: 'mm', type: 'num', group: '검증',
      desc: '도면에 전체 높이만 있으면 여기 넣는다. 추정 높이 치수들을 이 값에 맞춰 비례 조정한다' },
  ];

  const CAB_PARAMS = [
    { key: 'tag', label: 'Cabinet No.', type: 'text', default: '', group: '식별' },
    { key: 'bays', label: '연결 베이 수', type: 'num', default: 1, min: 1, max: 10, step: 1, group: '외형' },
    { key: 'w', label: '폭 W (베이당)', unit: 'mm', type: 'num', default: 800, group: '외형' },
    { key: 'h', label: '높이 H (플린스 제외)', unit: 'mm', type: 'num', default: 2000, group: '외형' },
    { key: 'd', label: '깊이 D', unit: 'mm', type: 'num', default: 800, group: '외형' },
    { key: 'plinth_h', label: '플린스(베이스) 높이', unit: 'mm', type: 'num', default: 100, group: '외형' },
    { key: 'doors', label: '전면 도어 수', type: 'enum', options: ['1', '2'], default: '1', group: '도어',
      est: (v) => (v.w >= 1000 ? '2' : '1') },
    { key: 'rear_door', label: '후면 도어', type: 'bool', default: true, group: '도어' },
    { key: 'door_open', label: '도어 열림각 (간섭검토)', unit: '°', type: 'num', default: 0, min: 0, max: 180, step: 5, group: '도어' },
    { key: 'louvers', label: '도어 루버', type: 'bool', default: true, group: '부속' },
    { key: 'fan', label: '루프 팬', type: 'bool', default: false, group: '부속' },
    { key: 'lifting_eyes', label: '리프팅 아이볼트', type: 'bool', default: true, group: '부속' },
    { key: 'mounting_plate', label: '마운팅 플레이트', type: 'bool', default: true, group: '내부' },
    { key: 'modules', label: 'I/O·DIN 모듈 행', type: 'num', default: 4, min: 0, max: 12, step: 1, group: '내부' },
    { key: 'gland_plate', label: '하부 케이블 글랜드 플레이트', type: 'bool', default: true, group: '부속' },
    { key: 'clearance', label: '전면 유지보수 공간 표시', unit: 'mm', type: 'num', default: 1000, group: '검증',
      desc: '0 이면 표시 안 함' },
  ];

  const HOOK_PARAMS = [
    { key: 'tag', label: 'Tag No.', type: 'text', default: '', group: '식별' },
    { key: 'inst', label: '계기', type: 'enum', options: ['PT', 'DPT', 'LT_DP', 'FT_DP'], default: 'PT', group: '구성',
      desc: 'PT=압력, DPT=차압(오리피스), LT_DP=차압식 레벨(탱크 노즐 2개), FT_DP=유량(오리피스 탭)' },
    { key: 'service', label: '유체', type: 'enum', options: ['gas', 'liquid', 'steam'], default: 'liquid', group: '구성',
      desc: 'gas=계기 위(탭 상부), liquid/steam=계기 아래(탭 측면/하부). 튜빙 기울기 방향이 바뀐다' },
    { key: 'proc_nps', label: '공정배관 호칭경', unit: 'in', type: 'num', default: 6, min: 0.5, max: 24, group: '공정' },
    { key: 'pipe_el', label: '배관 중심 높이 (바닥 기준)', unit: 'mm', type: 'num', default: 2500, group: '공정' },
    { key: 'tap', label: '탭 방향', type: 'enum', options: ['top', 'side', 'bottom', 'side45'], group: '공정',
      est: (v) => (v.service === 'gas' ? 'top' : 'side') },
    { key: 'tap_sep', label: 'HP-LP 탭 간격', unit: 'mm', type: 'num', group: '공정',
      when: (v) => v.inst !== 'PT', est: (v) => (v.inst === 'LT_DP' ? 2000 : 110) ,
      desc: 'DP: 오리피스 플랜지 탭 간격, LT_DP: 상·하부 노즐 고저차' },
    { key: 'mount', label: '설치', type: 'enum', options: ['stand', 'close_coupled'], default: 'stand', group: '설치' },
    { key: 'stand_h', label: '스탠드 높이', unit: 'mm', type: 'num', default: 1200, group: '설치', when: (v) => v.mount === 'stand' },
    { key: 'stand_dx', label: '스탠드 위치 X (배관 축 방향)', unit: 'mm', type: 'num', default: 600, group: '설치', when: (v) => v.mount === 'stand' },
    { key: 'stand_dz', label: '스탠드 위치 Z (배관에서 이격)', unit: 'mm', type: 'num', default: 700, group: '설치', when: (v) => v.mount === 'stand' },
    { key: 'tube_od', label: '임펄스 튜브 OD', unit: 'mm', type: 'num', default: 12.7, group: '튜빙' },
    { key: 'slope', label: '튜빙 기울기', unit: '1:x', type: 'num', default: 12, group: '튜빙',
      desc: '수평 구간 최소 기울기. 1:12 가 일반적' },
    { key: 'root_valve', label: '루트밸브', type: 'bool', default: true, group: '밸브' },
    { key: 'manifold', label: '매니폴드', type: 'enum', options: ['none', '2V', '3V', '5V'], group: '밸브',
      est: (v) => (v.inst === 'PT' ? '2V' : '5V') },
    { key: 'drain', label: '드레인/벤트 밸브', type: 'bool', default: true, group: '밸브' },
    { key: 'sunshade', label: '선쉐이드', type: 'bool', default: false, group: '부속' },
  ];

  // ───────────────────────── 값 결정 (출처 추적) ─────────────────────────
  /**
   * inputs: { key: { value, src, evidence? } | 원시값 }
   * return: { values: {key: value}, meta: {key: {src, ref?, evidence?, active}} }
   */
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
    // 두 번 돈다: 1차에서 enum/bool 이 정해져야 when/est 가 맞게 계산된다.
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
        if (e !== undefined && e !== null && !Number.isNaN(e)) {
          v[p.key] = norm(p, e); meta[p.key] = { src: 'estimate' }; continue;
        }
        if (p.default !== undefined) { v[p.key] = norm(p, p.default); meta[p.key] = { src: 'default' }; continue; }
        v[p.key] = undefined; meta[p.key] = { src: 'none' };
      }
    }
    for (const p of T.params) meta[p.key].active = !p.when || !!p.when(v);
    if (T.fit) T.fit(v, meta);
    return { values: v, meta };
  }

  // ───────────────────────── 밸브 ─────────────────────────
  /** 전체 높이만 도면에 있을 때 추정 높이 치수를 비례로 맞춘다 */
  function fitValve(v, meta) {
    if (!(v.overall_h > 0) || !meta.overall_h || !['drawing', 'user'].includes(meta.overall_h.src)) return;
    const keys = ['body_h', 'bonnet_h', 'yoke_h', 'act_h', 'stem_ext'];
    const total = estimateHeight(v);
    if (!(total > 0)) return;
    const fixed = keys.filter((k) => meta[k]?.active && v[k] > 0 && !['estimate'].includes(meta[k].src))
      .reduce((s, k) => s + v[k], 0);
    const scalable = keys.filter((k) => meta[k]?.active && v[k] > 0 && meta[k].src === 'estimate');
    const scal = scalable.reduce((s, k) => s + v[k], 0);
    const extra = total - fixed - scal;                 // 핸드휠 두께 등 키 밖의 높이
    if (scal <= 0) return;
    const k = (v.overall_h - fixed - extra) / scal;
    if (!(k > 0.3 && k < 3)) return;                    // 터무니없는 비율이면 손대지 않는다
    for (const key of scalable) {
      v[key] = Math.round(v[key] * k);
      meta[key] = { ...meta[key], src: 'estimate', ref: `전체높이 ${v.overall_h} 에 맞춰 ×${k.toFixed(2)}` };
    }
  }

  function estimateHeight(v) {
    const parts = buildValve(v);
    let top = -Infinity;
    for (const pt of parts) for (const pr of pt.prims) top = Math.max(top, primTop(pr));
    return top;
  }

  function primTop(pr) {
    const y = pr.at ? pr.at[1] : 0;
    switch (pr.k) {
      case 'cyl': return y + (pr.axis === 'y' ? pr.h / 2 : Math.max(pr.r, pr.r2 || 0));
      case 'box': return y + pr.s[1] / 2;
      case 'sph': return y + pr.r * (pr.scale ? pr.scale[1] : 1);
      case 'tor': return y + (pr.axis === 'y' ? pr.r : pr.R + pr.r);
      case 'tube': return Math.max(pr.a[1], pr.b[1]) + pr.r;
      default: return y;
    }
  }

  function handwheel(id, y, d, axis = 'y', at = null, label = '핸드휠') {
    const c = at || [0, y, 0];
    const rim = Math.max(6, d * 0.04);
    const prims = [tor(d / 2 - rim, rim, axis, c), cyl(axis, d * 0.08, rim * 2.4, c)];
    const [u, w] = perp[axis];
    for (let i = 0; i < 3; i++) {
      const a = i / 3 * Math.PI * 2;
      const e = [0, 1, 2].map((j) => c[j] + (u[j] * Math.cos(a) + w[j] * Math.sin(a)) * (d / 2 - rim));
      prims.push(tube(c, e, rim * 0.55));
    }
    return part(id, label, 'wheel', prims, [0, 1, 0], `Ø${Math.round(d)}`);
  }

  function buildValve(v) {
    const out = [];
    const f = R.flangeOf(v.nps, v.cls);
    const stub = v.pipe_stub > 0 ? v.pipe_stub : 0;

    if (v.body === 'psv') return buildPSV(v, f, stub);

    const half = v.ftf / 2;
    const bw = v.body_w;
    const neckR = f.pipeOD / 2 * 1.3;

    // 플랜지
    out.push(...flangeEnd('flange_in', '입구 플랜지', 'x', -1, half, f, { stub }));
    out.push(...flangeEnd('flange_out', '출구 플랜지', 'x', 1, half, f, { stub }));

    // 바디
    const bodyPrims = [];
    const neckL = Math.max(5, half - f.t - f.t * 1.1);
    if (v.body === 'globe') {
      bodyPrims.push(sph(bw / 2, [0, 0, 0], [Math.min(1.15, (half - f.t) / (bw / 2)), 0.9, 0.9]));
      bodyPrims.push(cyl('x', neckR, 2 * (half - f.t), [0, 0, 0]));
      bodyPrims.push(cyl('y', bw * 0.33, v.body_h - bw * 0.2, [0, (v.body_h + bw * 0.2) / 2 - bw * 0.1, 0]));
    } else if (v.body === 'gate') {
      bodyPrims.push(cyl('x', neckR, 2 * (half - f.t), [0, 0, 0]));
      bodyPrims.push(box([bw * 0.55, v.body_h + bw * 0.25, bw], [0, (v.body_h - bw * 0.25) / 2, 0]));
      bodyPrims.push(cyl('z', bw / 2, bw * 0.55, [0, -bw * 0.05, 0]));
    } else if (v.body === 'ball') {
      bodyPrims.push(sph(bw / 2, [0, 0, 0], [Math.min(1, (half - f.t) / (bw / 2)), 1, 1]));
      bodyPrims.push(cyl('x', neckR * 1.1, 2 * (half - f.t), [0, 0, 0]));
      bodyPrims.push(cyl('y', f.pipeOD * 0.32, v.body_h - bw * 0.4, [0, bw * 0.4 + (v.body_h - bw * 0.4) / 2, 0]));
    } else if (v.body === 'butterfly') {
      bodyPrims.push(cyl('x', f.bcd / 2 - f.bolt, v.ftf, [0, 0, 0]));
      bodyPrims.push(cyl('y', f.pipeOD * 0.22, v.body_h - f.bcd / 2, [0, f.bcd / 2 + (v.body_h - f.bcd / 2) / 2 - f.bolt, 0]));
      bodyPrims.push(box([v.ftf * 1.4, 10, v.ftf * 1.4], [0, v.body_h - 5, 0]));
    }
    // 버터플라이는 플랜지가 배관측 → 바디 자체 플랜지를 빼고, wafer 앞뒤 메이팅 플랜지를 ghost 로
    if (v.body === 'butterfly') {
      out.splice(0, out.length);
      out.push(part('mating_flanges', '메이팅 플랜지(배관측)', 'ghost', [
        cyl('x', f.od / 2, f.t, [-half - f.t / 2, 0, 0]), cyl('x', f.od / 2, f.t, [half + f.t / 2, 0, 0]),
        ...(stub ? [cyl('x', f.pipeOD / 2, stub, [-half - f.t - stub / 2, 0, 0]),
          cyl('x', f.pipeOD / 2, stub, [half + f.t + stub / 2, 0, 0])] : []),
      ], [0, 0, 0], '배관측 플랜지 — wafer 바디는 이 사이에 체결'));
      out.push(part('disc', '디스크', 'accent', [cyl('x', f.bcd / 2 - f.bolt - 4, 6, [0, 0, 0], { rotY: Math.PI / 5 })],
        [0, 0, 1], '회전 디스크 (일부 열림 표시)'));
    }
    out.push(part('body', '바디', 'body', bodyPrims, [0, 0, 0],
      `${v.body} body, F-F ${v.ftf}`));

    // 보닛 / 넥
    let y = v.body_h;
    if (v.body === 'globe' || v.body === 'gate') {
      out.push(part('bonnet', '보닛', 'body', [
        cyl('y', bw * 0.42, 14, [0, y + 7, 0]),
        cone('y', bw * 0.3, bw * 0.2, v.bonnet_h - 14, [0, y + 14 + (v.bonnet_h - 14) / 2, 0]),
      ], [0, 1, 0], `보닛 높이 ${v.bonnet_h}`));
      y += v.bonnet_h;
    } else {
      out.push(part('bonnet', '스템 넥/마운팅 패드', 'body', [
        cyl('y', f.pipeOD * 0.2, v.bonnet_h, [0, y + v.bonnet_h / 2, 0]),
        box([f.pipeOD * 0.9, 12, f.pipeOD * 0.9], [0, y + v.bonnet_h - 6, 0]),
      ], [0, 1, 0], 'ISO 5211 마운팅 패드'));
      y += v.bonnet_h;
    }
    out.push(...buildOperator(v, y, f));
    return out;
  }

  function buildOperator(v, y0, f) {
    const out = [];
    const op = v.operator;
    let y = y0;
    if (op === 'handwheel') {
      if (v.body === 'gate') {
        const yh = v.yoke_h;
        out.push(part('yoke', '요크', 'body', [
          box([18, yh, 26], [-v.hw_d * 0.18, y + yh / 2, 0]), box([18, yh, 26], [v.hw_d * 0.18, y + yh / 2, 0]),
          box([v.hw_d * 0.45, 22, 40], [0, y + yh - 11, 0]),
        ], [0, 1, 0]));
        y += yh;
        out.push(part('stem', '스템 (Rising)', 'bolt', [cyl('y', Math.max(8, f.pipeOD * 0.08), v.stem_ext + 40, [0, y + (v.stem_ext + 40) / 2, 0])],
          [0, 1.4, 0], `열림 시 노출 ${v.stem_ext}`));
        out.push(handwheel('handwheel', y + 25, v.hw_d));
      } else {
        out.push(part('stem', '스템', 'bolt', [cyl('y', 10, v.yoke_h, [0, y + v.yoke_h / 2, 0])], [0, 1, 0]));
        out.push(handwheel('handwheel', y + v.yoke_h, v.hw_d));
      }
    } else if (op === 'lever') {
      out.push(part('lever', '레버 핸들', 'wheel', [
        cyl('y', 16, 24, [0, y + 12, 0]),
        box([v.lever_l, 10, 34], [v.lever_l / 2 - 20, y + 30, 0]),
        box([v.lever_l * 0.3, 22, 40], [v.lever_l * 0.82, y + 30, 0]),
      ], [0, 1, 0], `레버 L ${v.lever_l} — 열림 시 배관 방향`));
    } else if (op === 'gear') {
      out.push(part('bracket', '브래킷', 'body', [cyl('y', f.pipeOD * 0.35, v.yoke_h, [0, y + v.yoke_h / 2, 0])], [0, 1, 0]));
      y += v.yoke_h;
      out.push(part('gearbox', '웜 기어박스', 'act', [
        box([v.act_d, v.act_h, v.act_d * 0.8], [0, y + v.act_h / 2, 0]),
        cyl('z', v.act_d * 0.18, v.act_d * 0.7, [0, y + v.act_h * 0.5, v.act_d * 0.75]),
      ], [0, 1, 0.3]));
      out.push(handwheel('handwheel', 0, v.hw_d, 'z', [0, y + v.act_h * 0.5, v.act_d * 0.4 + v.act_d * 0.7]));
    } else if (op === 'pneumatic_diaphragm') {
      const yh = v.yoke_h; const D = v.act_d; const H = v.act_h;
      out.push(part('yoke', '요크', 'body', [
        cyl('y', D * 0.16, 22, [0, y + 11, 0]),
        box([20, yh, 30], [-D * 0.17, y + yh / 2, 0]), box([20, yh, 30], [D * 0.17, y + yh / 2, 0]),
        cyl('y', D * 0.2, 24, [0, y + yh - 12, 0]),
      ], [0, 1, 0], `요크 높이 ${yh}`));
      out.push(part('stem', '스템/커넥터', 'bolt', [cyl('y', 9, yh, [0, y + yh / 2, 0]), box([40, 28, 30], [0, y + yh * 0.45, 0])], [0, 0.6, 0]));
      if (v.positioner) {
        out.push(part('positioner', '포지셔너', 'tx', [
          box([110, 150, 85], [D * 0.17 + 75, y + yh * 0.55, 0]),
          cyl('z', 34, 14, [D * 0.17 + 75, y + yh * 0.6, 48]),
          box([90, 16, 20], [D * 0.17 + 18, y + yh * 0.55, 0]),
        ], [1, 0, 0], '스마트 포지셔너 (요크 측면 장착)'));
        out.push(part('airset', '에어셋/필터레귤레이터', 'tx', [
          cyl('y', 28, 110, [D * 0.17 + 75, y + yh * 0.55 - 150, 0]),
          cyl('y', 34, 30, [D * 0.17 + 75, y + yh * 0.55 - 80, 0]),
        ], [1, -0.3, 0]));
      }
      y += yh;
      out.push(part('actuator', '다이어프램 케이스', 'act', [
        cone('y', D * 0.22, D / 2, H * 0.42, [0, y + H * 0.21, 0]),
        cyl('y', D / 2 + 6, 10, [0, y + H * 0.45, 0]),
        cone('y', D / 2, D * 0.25, H * 0.5, [0, y + H * 0.45 + 5 + H * 0.25, 0]),
      ], [0, 1, 0], `Ø${D} × H${H}`));
      y += H * 0.95;
      out.push(part('act_top', '상부 커버/벤트', 'act', [cyl('y', D * 0.1, 30, [0, y + 15, 0])], [0, 1.2, 0]));
      y += 30;
      if (v.cv_handwheel) {
        out.push(part('hw_stem', '핸드휠 스템', 'bolt', [cyl('y', 10, 90, [0, y + 45, 0])], [0, 1.3, 0]));
        out.push(handwheel('handwheel', y + 90, v.hw_d));
      }
    } else if (op === 'pneumatic_rotary') {
      const yh = v.yoke_h; const D = v.act_d; const L = v.act_l;
      out.push(part('bracket', '브래킷/커플링', 'body', [
        box([D * 0.9, yh, D * 0.9], [0, y + yh / 2, 0]),
      ], [0, 1, 0]));
      y += yh;
      out.push(part('actuator', '공압 액추에이터 (랙피니언)', 'act', [
        box([L, D * 1.05, D * 1.1], [0, y + D * 0.53, 0]),
        cyl('x', D * 0.48, 16, [-L / 2 - 8, y + D * 0.53, 0]), cyl('x', D * 0.48, 16, [L / 2 + 8, y + D * 0.53, 0]),
      ], [0, 1, 0], `L${L} × Ø${D}`));
      out.push(part('indicator', '개도 표시기', 'accent', [cyl('y', D * 0.3, 30, [0, y + D * 1.05 + 15, 0])], [0, 1.3, 0]));
      if (v.positioner) {
        out.push(part('positioner', '포지셔너/리밋스위치 박스', 'tx', [
          box([120, 110, 100], [0, y + D * 1.05 + 30 + 55, 0]),
          box([30, 30, 30], [75, y + D * 1.05 + 30 + 55, 0]),
        ], [0, 1.6, 0]));
      }
      out.push(part('solenoid', '솔레노이드밸브', 'tx', [box([60, 70, 50], [0, y + D * 0.5, D * 0.55 + 25])], [0, 0, 1]));
    } else if (op === 'electric') {
      const yh = v.yoke_h; const W = v.act_d; const H = v.act_h;
      const rising = v.body === 'gate' || v.body === 'globe';
      out.push(part('bracket', rising ? '요크/스러스트 베이스' : '브래킷/커플링', 'body', [
        cyl('y', W * 0.25, yh, [0, y + yh / 2, 0]),
        cyl('y', W * 0.34, 16, [0, y + yh - 8, 0]),
      ], [0, 1, 0]));
      y += yh;
      out.push(part('actuator', '전동 액추에이터 본체', 'act', [
        cyl('y', W * 0.38, H * 0.55, [0, y + H * 0.275, 0]),
        box([W * 0.75, H * 0.38, W * 0.7], [0, y + H * 0.55 + H * 0.19, 0]),
      ], [0, 1, 0], `W${W} × H${H}`));
      out.push(part('motor', '모터', 'act', [
        cyl('x', W * 0.24, W * 0.55, [-(W * 0.38 + W * 0.27), y + H * 0.3, 0]),
        cyl('x', W * 0.26, 14, [-(W * 0.38 + W * 0.55), y + H * 0.3, 0]),
      ], [-1, 0, 0], '모터 (측면)'));
      out.push(part('control_unit', '컨트롤 유닛/로컬 조작부', 'tx', [
        cyl('z', W * 0.3, W * 0.22, [0, y + H * 0.74, W * 0.35 + W * 0.11]),
        cyl('z', W * 0.16, 8, [0, y + H * 0.74, W * 0.35 + W * 0.22 + 4]),
        cyl('z', 16, 30, [-W * 0.18, y + H * 0.6, W * 0.35 + W * 0.22 + 10]),
        cyl('z', 16, 30, [W * 0.18, y + H * 0.6, W * 0.35 + W * 0.22 + 10]),
      ], [0, 0, 1], '디스플레이 · Local/Remote 셀렉터'));
      out.push(handwheel('handwheel', 0, v.hw_d, 'x', [W * 0.38 + 60, y + H * 0.3, 0], '비상 핸드휠'));
      out.push(part('hw_shaft', '핸드휠 축', 'bolt', [cyl('x', 12, 60, [W * 0.38 + 30, y + H * 0.3, 0])], [1, 0, 0]));
      if (rising) {
        out.push(part('stem_cover', '스템 보호관', 'bolt', [cyl('y', W * 0.1, 25.4 * v.nps * 1.05, [0, y + H * 0.93 + 25.4 * v.nps * 0.52, 0])],
          [0, 1.4, 0], 'Rising stem 보호관'));
      }
      out.push(part('conduit', '케이블 엔트리', 'bolt', [
        cyl('x', 12, 40, [W * 0.375 + 20, y + H * 0.74, -W * 0.15]),
        cyl('x', 12, 40, [W * 0.375 + 20, y + H * 0.74, W * 0.05]),
      ], [1, 0, 0]));
    }
    return out;
  }

  function buildPSV(v, f, stub) {
    const out = [];
    const fo = R.flangeOf(v.outlet_nps, v.outlet_cls);
    out.push(...flangeEnd('flange_in', '입구 플랜지 (아래)', 'y', -1, v.cti, f, { stub }));
    out.push(...flangeEnd('flange_out', '출구 플랜지 (측면)', 'x', 1, v.cto, fo, { stub }));
    const bw = v.body_w;
    out.push(part('body', '바디 (앵글형)', 'body', [
      sph(bw * 0.55, [0, 0, 0], [1, 1, 0.95]),
      cyl('y', f.pipeOD / 2 * 1.3, v.cti - f.t, [0, -(v.cti - f.t) / 2, 0]),
      cyl('x', fo.pipeOD / 2 * 1.25, v.cto - fo.t, [(v.cto - fo.t) / 2, 0, 0]),
      cyl('y', bw * 0.38, v.body_h - bw * 0.3, [0, bw * 0.3 + (v.body_h - bw * 0.3) / 2, 0]),
    ], [0, 0, 0], `C-I ${v.cti} / C-O ${v.cto}`));
    out.push(part('nozzle', '노즐/디스크(내부)', 'accent', [cyl('y', f.pipeOD * 0.32, 40, [0, -10, 0])], [0, 0, 1.2]));
    let y = v.body_h;
    const bh = v.bonnet_h;
    out.push(part('bonnet', '보닛 (스프링 하우징)', 'act', [
      cyl('y', bw * 0.5, 16, [0, y + 8, 0]),
      cone('y', bw * 0.42, bw * 0.26, bh, [0, y + 16 + bh / 2, 0]),
    ], [0, 1, 0], `스프링 하우징 높이 ${bh}`));
    y += 16 + bh;
    out.push(part('cap', v.psv_lever ? '레버 캡' : '스크루 캡', 'act', [
      cyl('y', bw * 0.2, 60, [0, y + 30, 0]),
      ...(v.psv_lever ? [box([bw * 1.1, 14, 22], [bw * 0.4, y + 45, 0]), sph(14, [bw * 0.95, y + 45, 0])] : []),
    ], [0, 1.4, 0]));
    return out;
  }

  // ───────────────────────── 캐비닛 ─────────────────────────
  function buildCabinet(v) {
    const out = [];
    const { w, h, d } = v; const ph = v.plinth_h; const n = Math.max(1, Math.round(v.bays));
    const totalW = w * n;
    const x0 = -totalW / 2;
    const post = 40; const skin = 2;
    out.push(part('plinth', '플린스(베이스)', 'plinth', [box([totalW, ph, d], [0, ph / 2, -d / 2])], [0, -1, 0],
      `H${ph}`));
    const frame = []; const sides = []; const roof = []; const rear = []; const doors = []; const handles = [];
    const louvers = []; const plates = []; const modules = []; const eyes = []; const gland = []; const fans = [];
    const yb = ph;
    for (let b = 0; b < n; b++) {
      const cx = x0 + w * b + w / 2;
      for (const sx of [-1, 1]) for (const sz of [0, 1]) {
        frame.push(box([post, h, post], [cx + sx * (w / 2 - post / 2), yb + h / 2, -post / 2 - sz * (d - post)]));
      }
      frame.push(box([w, post, d], [cx, yb + post / 2, -d / 2]));
      frame.push(box([w, post, d], [cx, yb + h - post / 2, -d / 2]));
      roof.push(box([w + 4, 3, d + 4], [cx, yb + h + 1.5, -d / 2]));
      if (v.rear_door) rear.push(box([w - 4, h - 4, 20], [cx, yb + h / 2, -d - 10]));
      else rear.push(box([w - 4, h - 4, skin], [cx, yb + h / 2, -d - skin / 2]));
      if (v.mounting_plate) plates.push(box([w - 2 * post - 20, h - 2 * post - 60, 3], [cx, yb + h / 2, -d + 60]));
      const mrows = Math.max(0, Math.round(v.modules));
      for (let m = 0; m < mrows; m++) {
        const my = yb + post + 120 + m * ((h - 2 * post - 240) / Math.max(1, mrows - 1 || 1));
        modules.push(box([w - 2 * post - 60, 35, 8], [cx, my, -d + 66]));           // DIN 레일/덕트
        const nmod = Math.floor((w - 2 * post - 80) / 45);
        for (let k = 0; k < nmod; k += 1) {
          modules.push(box([40, 110, 110], [cx - (w - 2 * post - 80) / 2 + 22 + k * 45, my + 75, -d + 120]));
        }
      }
      if (v.gland_plate) gland.push(box([w - 2 * post - 40, 4, d - 2 * post - 80], [cx, yb + 2, -d / 2]));
      if (v.fan) fans.push(box([w * 0.35, 60, w * 0.35], [cx, yb + h + 33, -d / 2]), cyl('y', w * 0.15, 8, [cx, yb + h + 67, -d / 2]));
      if (v.lifting_eyes) {
        for (const sx of [-1, 1]) for (const sz of [0, 1]) {
          eyes.push(tor(22, 6, 'z', [cx + sx * (w / 2 - 60), yb + h + 30, -60 - sz * (d - 120)]),
            cyl('y', 8, 20, [cx + sx * (w / 2 - 60), yb + h + 8, -60 - sz * (d - 120)]));
        }
      }
      // 전면 도어 (+Z 방향 열림, 경첩 축 Y)
      const nd = Number(v.doors);
      const dw = (w - 4) / nd; const dt = 22; const ang = (v.door_open || 0) * Math.PI / 180;
      for (let k = 0; k < nd; k++) {
        const hingeLeft = nd === 1 ? true : k === 0;
        const hx = hingeLeft ? cx - (w - 4) / 2 + k * dw : cx - (w - 4) / 2 + (k + 1) * dw;
        const s = hingeLeft ? 1 : -1;                    // 경첩에서 도어 끝 방향
        // 경첩 축(Y) 기준 회전. 앞(+Z)으로 열린다. th 는 three.js rotation.y 와 같은 부호.
        const th = s > 0 ? -ang : ang;
        const rot = (lx, lz) => [hx + lx * Math.cos(th) + lz * Math.sin(th), -lx * Math.sin(th) + lz * Math.cos(th)];
        const c0 = rot(s * dw / 2, dt / 2);
        doors.push(box([dw - 4, h - 4, dt], [c0[0], yb + h / 2, c0[1]], { ry: th }));
        const hpos = rot(s * (dw - 50), dt + 15);
        handles.push(box([20, 160, 30], [hpos[0], yb + h * 0.55, hpos[1]], { ry: th }));
        if (v.louvers) {
          for (const ly of [0.12, 0.85]) {
            const lp = rot(s * dw / 2, dt + 3);
            louvers.push(box([Math.min(320, dw * 0.5), 260, 8], [lp[0], yb + h * ly, lp[1]], { ry: th }));
          }
        }
      }
    }
    // 측판은 양 끝에만
    sides.push(box([skin, h, d], [x0 + skin / 2, yb + h / 2, -d / 2]), box([skin, h, d], [x0 + totalW - skin / 2, yb + h / 2, -d / 2]));
    out.push(part('frame', '프레임', 'cabframe', frame, [0, 0, 0], `${post}×${post} 포스트`));
    out.push(part('side_panels', '측판', 'cab', sides, [0, 0, 0]));
    out.push(part('roof', '루프', 'cab', roof, [0, 1, 0]));
    out.push(part('rear', v.rear_door ? '후면 도어' : '후면판', 'cab', rear, [0, 0, -1]));
    out.push(part('doors', '전면 도어', 'door', doors, [0, 0, 1], `${v.doors}도어 × ${n}베이, 열림 ${v.door_open}°`));
    out.push(part('handles', '도어 핸들/잠금', 'bolt', handles, [0, 0, 1.2]));
    if (louvers.length) out.push(part('louvers', '루버(필터팬)', 'accent', louvers, [0, 0, 1.3]));
    if (plates.length) out.push(part('mounting_plate', '마운팅 플레이트', 'plate', plates, [0, 0, -0.4]));
    if (modules.length) out.push(part('modules', 'DIN 레일·I/O 모듈', 'tx', modules, [0, 0, -0.1]));
    if (gland.length) out.push(part('gland_plate', '글랜드 플레이트', 'bolt', gland, [0, -0.6, 0]));
    if (fans.length) out.push(part('fan', '루프 팬', 'accent', fans, [0, 1.3, 0]));
    if (eyes.length) out.push(part('lifting_eyes', '리프팅 아이볼트', 'bolt', eyes, [0, 1.5, 0]));
    if (v.clearance > 0) {
      out.push(part('clearance', `전면 유지보수 공간 ${v.clearance}`, 'clear',
        [box([totalW, h + ph, v.clearance], [0, (h + ph) / 2, v.clearance / 2 + 1])], [0, 0, 0],
        '배치 검토용. 다른 설비가 이 영역에 들어오면 간섭'));
    }
    return out;
  }

  // ───────────────────────── 계기 훅업 ─────────────────────────
  function polylineTube(points, r) {
    const prims = [];
    for (let i = 0; i < points.length - 1; i++) prims.push(tube(points[i], points[i + 1], r));
    for (let i = 1; i < points.length - 1; i++) prims.push(sph(r * 1.25, points[i]));
    return prims;
  }

  function smallValve(id, label, at, axis, size = 40) {
    const hwAxis = axis === 'y' ? 'z' : 'y';
    const top = along(hwAxis, size * 0.9, at);
    return [part(id, label, 'body', [
      box(axis === 'x' ? [size * 1.5, size * 0.8, size * 0.8] : axis === 'y' ? [size * 0.8, size * 1.5, size * 0.8] : [size * 0.8, size * 0.8, size * 1.5], at),
      cyl(hwAxis, 6, size * 0.9, along(hwAxis, size * 0.45, at)),
    ], [0, 0, 0]), handwheel(`${id}_hw`, 0, size * 1.2, hwAxis, top, `${label} 핸들`)];
  }

  function buildHookup(v) {
    const out = [];
    const procOD = R.pipeOD[R.nearestNps(Math.min(12, v.proc_nps))] * (v.proc_nps > 12 ? v.proc_nps / 12 : 1);
    const pr = procOD / 2; const yP = v.pipe_el; const to = v.tube_od / 2;
    const dp = v.inst !== 'PT';
    const span = 1800 + (dp ? v.tap_sep : 0);
    // 공정 배관 (LT_DP 는 탱크 벽)
    if (v.inst === 'LT_DP') {
      out.push(part('vessel', '용기/탱크 쉘(참조)', 'ghost', [box([2400, v.tap_sep + 1200, 20], [0, yP - v.tap_sep / 2, -pr - 10 - 200])],
        [0, 0, -1], '노즐 고저차 = tap_sep'));
    } else {
      out.push(part('process_pipe', '공정 배관', 'ghost', [cyl('x', pr, span, [0, yP, 0])], [0, 0, 0],
        `NPS ${v.proc_nps}`));
      if (dp) {
        const f = R.flangeOf(Math.min(12, v.proc_nps), 300);
        out.push(part('orifice', '오리피스 플랜지 세트', 'flange', [
          cyl('x', f.od / 2, f.t * 1.4, [-f.t * 0.75, yP, 0]), cyl('x', f.od / 2, f.t * 1.4, [f.t * 0.75, yP, 0]),
          cyl('x', f.od / 2 - 8, 4, [0, yP, 0]),
        ], [0, 0, 0], '오리피스 플레이트 + 플랜지 탭'));
      }
    }

    // 탭 위치들
    const dir = { top: [0, 1, 0], side: [0, 0, 1], bottom: [0, -1, 0], side45: [0, Math.SQRT1_2, Math.SQRT1_2] }[v.tap] || [0, 0, 1];
    const taps = [];
    if (v.inst === 'PT') taps.push({ name: '', at: [0, yP, 0] });
    else if (v.inst === 'LT_DP') {
      taps.push({ name: 'HP', at: [0, yP - v.tap_sep, -pr - 200] }, { name: 'LP', at: [0, yP, -pr - 200] });
    } else {
      const s = Math.max(40, v.tap_sep / 2);
      taps.push({ name: 'HP', at: [-s, yP, 0] }, { name: 'LP', at: [s, yP, 0] });
    }
    const tapDir = v.inst === 'LT_DP' ? [0, 0, 1] : dir;
    const rTap = v.inst === 'LT_DP' ? 0 : pr;

    // 계기 위치
    const below = v.service !== 'gas';
    let txBase;
    if (v.mount === 'stand') {
      out.push(part('stand', '2" 계기 스탠드', 'cabframe', [
        box([220, 12, 220], [v.stand_dx, 6, v.stand_dz]),
        cyl('y', 30.15, v.stand_h, [v.stand_dx, v.stand_h / 2, v.stand_dz]),
        cyl('y', 34, 6, [v.stand_dx, v.stand_h + 3, v.stand_dz]),
        ...[[-80, -80], [80, -80], [-80, 80], [80, 80]].map(([a, b]) => cyl('y', 8, 25, [v.stand_dx + a, 18, v.stand_dz + b])),
      ], [0, -0.3, 0], `H${v.stand_h}, 베이스 220×220 앵커 4개`));
      txBase = [v.stand_dx, v.stand_h - 220, v.stand_dz + 60];
      out.push(part('ubolt', 'U볼트/브래킷', 'bolt', [
        box([70, 120, 8], [v.stand_dx, v.stand_h - 200, v.stand_dz + 36]),
        tor(36, 4, 'y', [v.stand_dx, v.stand_h - 160, v.stand_dz]), tor(36, 4, 'y', [v.stand_dx, v.stand_h - 240, v.stand_dz]),
      ], [0, 0, 0.5]));
    } else {
      const t0 = taps[0].at;
      txBase = [t0[0], t0[1] + (below ? -pr - 350 : pr + 250), t0[2] + 150];
    }

    // 매니폴드 + 트랜스미터
    const mx = txBase[0]; const my = txBase[1]; const mz = txBase[2];
    const nV = { none: 0, '2V': 2, '3V': 3, '5V': 5 }[v.manifold] || 0;
    if (nV) {
      const prims = [box([dp ? 120 : 60, 70, 60], [mx, my, mz])];
      for (let i = 0; i < nV; i++) {
        const sx = nV === 1 ? 0 : (i / (nV - 1) - 0.5) * (dp ? 100 : 40);
        prims.push(cyl('z', 6, 50, [mx + sx, my - 10, mz + 55]), cyl('x', 16, 6, [mx + sx, my - 10, mz + 82]));
      }
      out.push(part('manifold', `${v.manifold} 매니폴드`, 'body', prims, [0, -0.5, 0.6]));
    }
    const ty = my + 35 + 30;
    out.push(part('transmitter', v.inst === 'PT' ? '압력 트랜스미터' : '차압 트랜스미터', 'tx', [
      box([dp ? 110 : 60, 50, 90], [mx, ty, mz]),                          // 코플래너 플랜지
      cyl('y', 42, 90, [mx, ty + 25 + 45, mz]),                             // 센서 모듈
      cyl('z', 52, 120, [mx, ty + 25 + 90 + 50, mz]),                       // 전자부 하우징
      cyl('z', 50, 18, [mx, ty + 25 + 90 + 50, mz + 69]),                   // 디스플레이 커버
      cyl('z', 50, 18, [mx, ty + 25 + 90 + 50, mz - 69]),
      cyl('x', 11, 30, [mx + 58, ty + 25 + 90 + 50, mz - 20]),              // 전선관 엔트리
    ], [0, 0.5, 0.6], v.tag || ''));
    if (v.sunshade) {
      out.push(part('sunshade', '선쉐이드', 'cab', [box([240, 4, 260], [mx, ty + 300, mz]), box([240, 340, 4], [mx, ty + 130, mz - 130])], [0, 1, 0]));
    }

    // 튜빙
    const slope = 1 / Math.max(1, v.slope);
    taps.forEach((tp, i) => {
      const lbl = tp.name ? ` (${tp.name})` : '';
      const a = tp.at.map((c, j) => c + tapDir[j] * rTap);                 // 배관 표면
      const rv = a.map((c, j) => c + tapDir[j] * 70);                       // 루트밸브 위치
      const ax = Math.abs(tapDir[1]) > 0.9 ? 'y' : 'z';
      if (v.root_valve) out.push(...smallValve(`root_valve${i}`, `루트밸브${lbl}`, rv, ax, 36));
      const c = rv.map((x, j) => x + tapDir[j] * 70);                       // 루트밸브 출구 니플 끝
      const xOff = dp ? (i === 0 ? -27 : 27) : 0;
      // 매니폴드 후면(공정 쪽)으로 들어간다. 계기 위로 지나가지 않게.
      const inlet = [mx + xOff, my - 15, mz - 30];
      const d1 = Math.abs(inlet[0] - c[0]) * slope;                         // X 방향 수평 구간 낙차
      const d2 = Math.abs(inlet[2] - c[2]) * slope;                         // Z 방향 수평 구간 낙차
      // liquid/steam: 계기 쪽으로 계속 내려간다. gas: 계기 쪽으로 계속 올라간다(응축수는 탭으로).
      const sgn = below ? 1 : -1;
      const yH = inlet[1] + sgn * (d1 + d2);
      const pts = [a, c];
      if (Math.abs(yH - c[1]) > 1) pts.push([c[0], yH, c[2]]);
      pts.push([inlet[0], yH - sgn * d1, c[2]]);
      pts.push(inlet);
      out.push(part(`tubing${i}`, `임펄스 튜빙${lbl}`, 'tube', polylineTube(pts, to), [0, 0, 0],
        `OD ${v.tube_od}, 기울기 1:${v.slope} ${below ? '계기 쪽 하향' : '탭 쪽 하향(가스)'}`));
    });
    if (v.drain) {
      out.push(part('drain', below ? '드레인 밸브' : '벤트 밸브', 'body', [
        cyl('y', 8, 60, [mx, my - 35 - 30, mz - 40]), box([30, 30, 30], [mx, my - 35 - 70, mz - 40]),
      ], [0, -1, 0]));
    }
    // 바닥
    out.push(part('floor', '바닥/그레이팅(참조)', 'ghost', [box([span + 600, 10, 2200], [0, -5, 300])], [0, -1, 0]));
    return out;
  }

  // ───────────────────────── 설계 점검 ─────────────────────────
  // 3D 를 만들며 같이 볼 수 있는 기본 점검. 결론이 아니라 확인할 거리.
  function checkHookup(v) {
    const w = [];
    const txY = v.mount === 'stand' ? v.stand_h - 100 : (v.service === 'gas' ? v.pipe_el + 200 : v.pipe_el - 300);
    const tapY = v.inst === 'LT_DP' ? v.pipe_el - v.tap_sep : v.pipe_el;
    if (v.service === 'gas' && txY < tapY) w.push('가스 서비스인데 계기가 탭보다 낮습니다 — 응축수 포켓 위험. 계기를 탭 위로 올리거나 close_coupled 를 검토하세요.');
    if (v.service !== 'gas' && txY > tapY) w.push('액체/스팀 서비스인데 계기가 탭보다 높습니다 — 기체 포켓 위험.');
    if (v.service !== 'gas' && v.tap === 'top') w.push('액체/스팀 배관 상부 탭 — 기체가 임펄스 라인으로 들어갑니다.');
    if (v.service === 'gas' && v.tap === 'bottom') w.push('가스 배관 하부 탭 — 응축수·이물이 임펄스 라인으로 들어갑니다.');
    if (v.slope < 12) w.push(`튜빙 기울기 1:${v.slope} — 일반 기준(1:12)보다 완만합니다.`);
    return w;
  }
  function checkCabinet(v) {
    const w = [];
    const dw = v.w / Number(v.doors);
    if (v.clearance > 0 && v.clearance < dw) w.push(`전면 유지보수 공간 ${v.clearance} 이 도어 폭 ${Math.round(dw)} 보다 작습니다 — 도어 90° 개방 불가.`);
    if (v.h + v.plinth_h > 2400) w.push('전체 높이 2400 초과 — 운송·반입 경로 확인.');
    return w;
  }
  function checkValve(v) {
    const w = [];
    if (v.body === 'psv' && v.operator !== 'spring') w.push('PSV 조작기는 spring 이어야 합니다.');
    if (v.body !== 'psv' && v.operator === 'spring') w.push('spring 조작기는 PSV 에만 씁니다.');
    if (v.operator === 'pneumatic_rotary' && !['ball', 'butterfly'].includes(v.body)) w.push('로터리 액추에이터는 1/4회전 밸브(ball/butterfly)용입니다.');
    if (v.operator === 'pneumatic_diaphragm' && !['globe', 'gate'].includes(v.body)) w.push('다이어프램 액추에이터는 직선운동 밸브(globe)용입니다.');
    if (v.operator === 'lever' && v.nps > 6) w.push('6" 초과 레버 조작은 토크상 비현실적 — gear 검토.');
    return w;
  }

  // ───────────────────────── 품목 레지스트리 ─────────────────────────
  const TYPES = {
    valve: { label: '밸브 (CV · MOV · Manual · PSV)', params: VALVE_PARAMS, build: buildValve, fit: fitValve, checks: checkValve },
    cabinet: { label: 'System Cabinet', params: CAB_PARAMS, build: buildCabinet, checks: checkCabinet },
    hookup: { label: 'Instrument Hook-up', params: HOOK_PARAMS, build: buildHookup, checks: checkHookup },
  };

  const PRESETS = [
    { id: 'cv_globe', label: 'Control Valve — Globe (공압 다이어프램)', type: 'valve', set: { body: 'globe', operator: 'pneumatic_diaphragm', service: 'control' } },
    { id: 'cv_ball', label: 'Control Valve — Ball (공압 로터리)', type: 'valve', set: { body: 'ball', operator: 'pneumatic_rotary', service: 'control', nps: 4 } },
    { id: 'cv_bfv', label: 'Control Valve — Butterfly (공압 로터리)', type: 'valve', set: { body: 'butterfly', operator: 'pneumatic_rotary', service: 'control', nps: 8 } },
    { id: 'mov_gate', label: 'MOV — Gate', type: 'valve', set: { body: 'gate', operator: 'electric', service: 'on_off', nps: 6 } },
    { id: 'mov_globe', label: 'MOV — Globe', type: 'valve', set: { body: 'globe', operator: 'electric', service: 'on_off', nps: 4 } },
    { id: 'mov_ball', label: 'MOV — Ball', type: 'valve', set: { body: 'ball', operator: 'electric', service: 'on_off', nps: 6 } },
    { id: 'mov_bfv', label: 'MOV — Butterfly', type: 'valve', set: { body: 'butterfly', operator: 'electric', service: 'on_off', nps: 10 } },
    { id: 'man_gate', label: 'Manual — Gate (핸드휠, Rising stem)', type: 'valve', set: { body: 'gate', operator: 'handwheel', service: 'on_off', nps: 4 } },
    { id: 'man_globe', label: 'Manual — Globe (핸드휠)', type: 'valve', set: { body: 'globe', operator: 'handwheel', service: 'on_off', nps: 3 } },
    { id: 'man_ball', label: 'Manual — Ball (레버)', type: 'valve', set: { body: 'ball', operator: 'lever', service: 'on_off', nps: 2 } },
    { id: 'man_bfv', label: 'Manual — Butterfly (기어)', type: 'valve', set: { body: 'butterfly', operator: 'gear', service: 'on_off', nps: 8 } },
    { id: 'psv', label: 'PSV — Spring Loaded (앵글)', type: 'valve', set: { body: 'psv', operator: 'spring', service: 'on_off', nps: 1.5, cls: '300' } },
    { id: 'cabinet', label: 'System Cabinet', type: 'cabinet', set: {} },
    { id: 'hook_pt', label: 'Hook-up — PT (스탠드)', type: 'hookup', set: { inst: 'PT' } },
    { id: 'hook_dpt', label: 'Hook-up — DP 유량 (오리피스)', type: 'hookup', set: { inst: 'FT_DP', service: 'gas', mount: 'close_coupled', tap: 'top' } },
    { id: 'hook_lt', label: 'Hook-up — DP 레벨 (탱크)', type: 'hookup', set: { inst: 'LT_DP', pipe_el: 3000, tap_sep: 2000, stand_h: 900, stand_dx: 0, stand_dz: 900 } },
  ];

  /** 스펙(JSON) → 부품 목록. spec = { type, inputs } */
  function build(spec) {
    const { values, meta } = resolve(spec.type, spec.inputs || {});
    const T = TYPES[spec.type];
    const parts = T.build(values);
    const warnings = T.checks ? T.checks(values) : [];
    return { values, meta, parts, warnings, bbox: bboxOf(parts) };
  }

  function primBox(pr) {
    if (pr.k === 'tube') {
      return [[0, 1, 2].map((i) => Math.min(pr.a[i], pr.b[i]) - pr.r), [0, 1, 2].map((i) => Math.max(pr.a[i], pr.b[i]) + pr.r)];
    }
    let e;
    if (pr.k === 'box') {
      const ry = pr.ry || 0;
      const ex = Math.abs(Math.cos(ry)) * pr.s[0] / 2 + Math.abs(Math.sin(ry)) * pr.s[2] / 2;
      const ez = Math.abs(Math.sin(ry)) * pr.s[0] / 2 + Math.abs(Math.cos(ry)) * pr.s[2] / 2;
      e = [ex, pr.s[1] / 2, ez];
    } else if (pr.k === 'cyl') {
      const r = Math.max(pr.r, pr.r2 ?? pr.r);
      e = [r, r, r]; e['xyz'.indexOf(pr.axis)] = pr.h / 2;
    } else if (pr.k === 'sph') {
      const s = pr.scale || [1, 1, 1]; e = s.map((k) => pr.r * k);
    } else if (pr.k === 'tor') {
      const o = pr.R + pr.r; e = [o, o, o]; e['xyz'.indexOf(pr.axis)] = pr.r;
    }
    return [pr.at.map((c, i) => c - e[i]), pr.at.map((c, i) => c + e[i])];
  }

  function bboxOf(parts, filter = (p) => p.mat !== 'ghost' && p.mat !== 'clear') {
    const lo = [Infinity, Infinity, Infinity]; const hi = [-Infinity, -Infinity, -Infinity];
    for (const p of parts) {
      if (!filter(p)) continue;
      for (const pr of p.prims) {
        const [a, b] = primBox(pr);
        for (let i = 0; i < 3; i++) { lo[i] = Math.min(lo[i], a[i]); hi[i] = Math.max(hi[i], b[i]); }
      }
    }
    return { min: lo, max: hi, size: hi.map((h, i) => h - lo[i]) };
  }

  /** Claude 에게 줄 파라미터 사전 (스킬·앱 공용) */
  function describeSchema(typeId) {
    const T = TYPES[typeId];
    return T.params.map((p) => {
      const opt = p.options ? ` [${p.options.join(' | ')}]` : '';
      const u = p.unit ? ` (${p.unit})` : '';
      return `- ${p.key}${u}${opt}: ${p.label}${p.desc ? ' — ' + p.desc : ''}`;
    }).join('\n');
  }

  return { TYPES, PRESETS, resolve, build, bboxOf, describeSchema };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = Anatomy;
