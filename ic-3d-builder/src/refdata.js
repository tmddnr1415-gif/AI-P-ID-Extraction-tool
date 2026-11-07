/* 표준 치수 참고표 — 도면에서 치수를 못 읽었을 때 쓰는 기본값.
 *
 * ⚠ 이 표는 공개 자료와 엔지니어링 지식으로 채운 "참고값"이다. 원문 표준
 *   (ASME B16.5 / B16.10 / ANSI/ISA-75.08.01 / API 526 / API 609)이나
 *   벤더 Dimensional Drawing 과 대조하지 않았다. 3D 에서 이 값을 쓴 치수는
 *   출처가 'standard' 로 표시되며, 배치 검토(간섭·공간) 용도로만 쓴다.
 *   제작·구매용 치수로 쓰지 않는다.
 *
 * 단위: mm. 키: NPS(inch) 문자열.
 */
'use strict';

const RefData = (() => {
  const NPS = ['0.5', '0.75', '1', '1.5', '2', '3', '4', '6', '8', '10', '12'];
  const row = (arr) => Object.fromEntries(NPS.map((k, i) => [k, arr[i]]));

  // ASME B36.10 파이프 외경
  const pipeOD = row([21.3, 26.7, 33.4, 48.3, 60.3, 88.9, 114.3, 168.3, 219.1, 273.1, 323.9]);

  // ASME B16.5 RF 플랜지: 외경, 두께, 볼트원 지름, 볼트 수, 볼트 지름
  const flange = {
    150: {
      od: row([89, 98, 108, 127, 152, 191, 229, 279, 343, 406, 483]),
      t: row([9.6, 11.2, 12.7, 15.9, 17.5, 22.3, 22.3, 23.9, 27.0, 28.6, 30.2]),
      bcd: row([60.3, 69.8, 79.4, 98.4, 120.7, 152.4, 190.5, 241.3, 298.5, 362.0, 431.8]),
      n: row([4, 4, 4, 4, 4, 4, 8, 8, 8, 12, 12]),
      bolt: row([12.7, 12.7, 12.7, 12.7, 15.9, 15.9, 15.9, 19.1, 19.1, 22.2, 22.2]),
    },
    300: {
      od: row([95, 117, 124, 156, 165, 210, 254, 318, 381, 444, 521]),
      t: row([12.7, 14.3, 15.9, 19.1, 20.7, 27.0, 30.2, 35.0, 39.7, 46.1, 49.3]),
      bcd: row([66.7, 82.6, 88.9, 114.3, 127.0, 168.3, 200.0, 269.9, 330.2, 387.4, 450.8]),
      n: row([4, 4, 4, 4, 8, 8, 8, 12, 12, 16, 16]),
      bolt: row([12.7, 15.9, 15.9, 19.1, 15.9, 19.1, 19.1, 19.1, 22.2, 25.4, 28.6]),
    },
  };

  // 면간거리 (Face-to-Face, RF)
  const ftf = {
    gate: { 150: row([108, 117, 127, 165, 178, 203, 229, 267, 292, 330, 356]),
            300: row([140, 152, 165, 190, 216, 283, 305, 403, 419, 457, 502]) },
    globe: { 150: row([108, 117, 127, 165, 203, 241, 292, 406, 495, 622, 698]),
             300: row([152, 178, 203, 229, 267, 318, 356, 444, 559, 622, 711]) },
    // 볼밸브 short pattern (B16.10) — 150/300 모두 gate 와 동일 계열
    ball: { 150: row([108, 117, 127, 165, 178, 203, 229, 267, 292, 330, 356]),
            300: row([140, 152, 165, 190, 216, 283, 305, 403, 419, 457, 502]) },
    // 조절밸브 글로브 (ANSI/ISA-75.08.01 integral flanged)
    control_globe: { 150: row([184, 184, 184, 222, 254, 298, 352, 451, 543, 673, 737]),
                     300: row([190, 194, 197, 235, 267, 317, 368, 473, 568, 708, 775]) },
    // 버터플라이 wafer/lug (API 609 Cat A 계열 근사) — 2" 미만은 없음
    butterfly: { 150: row([43, 43, 43, 43, 43, 46, 52, 56, 60, 68, 78]),
                 300: row([43, 43, 43, 43, 43, 48, 54, 59, 73, 83, 92]) },
  };

  const SOURCES = {
    pipeOD: 'ASME B36.10M (참고값)',
    flange: 'ASME B16.5 Class 150/300 RF (참고값)',
    gate: 'ASME B16.10 Gate (참고값)',
    globe: 'ASME B16.10 Globe (참고값)',
    ball: 'ASME B16.10 Ball short pattern (참고값)',
    control_globe: 'ANSI/ISA-75.08.01 (참고값)',
    butterfly: 'API 609 Cat A 근사 (참고값)',
  };

  function nearestNps(nps) {
    const v = Number(nps);
    let best = NPS[0];
    for (const k of NPS) if (Math.abs(Number(k) - v) < Math.abs(Number(best) - v)) best = k;
    return best;
  }

  function cls(c) { return Number(c) >= 300 ? 300 : 150; }

  /** 플랜지·파이프 치수 묶음 */
  function flangeOf(nps, c) {
    const k = nearestNps(nps); const f = flange[cls(c)];
    return { od: f.od[k], t: f.t[k], bcd: f.bcd[k], n: f.n[k], bolt: f.bolt[k], pipeOD: pipeOD[k] };
  }

  function ftfOf(kind, nps, c) {
    const t = ftf[kind]; if (!t) return null;
    return t[cls(c)][nearestNps(nps)];
  }

  return { NPS, pipeOD, flange, ftf, SOURCES, nearestNps, flangeOf, ftfOf };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = RefData;
