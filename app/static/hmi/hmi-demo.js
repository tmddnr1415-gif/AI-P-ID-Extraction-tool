/* 예시 모델 — 참고 그림 "DCS Graphic – Compressor Train (Example)" 를 같은 모델 꼴로 (hotfix109).
 * 식별 P&ID 없이 부품을 확인하는 데 쓰고, 다른 공정 그림을 손으로 짤 때의 본보기다.  값은 예시이지 실제가 아니다. */
(function () {
  "use strict";
  const H = (window.HMI = window.HMI || {});
  H.demoCompressorTrain = function () {
    return {
      width: 1100, height: 520, title: "Compressor Train (Example)",
      pipes: [
        { id: "p-suction", service: "process", flow: "fwd", width: 7, points: [[20, 262], [396, 262]], label: "Suction" },
        { id: "p-disch-1", service: "discharge", flow: "fwd", width: 7, points: [[554, 262], [700, 262], [700, 190], [790, 190]], label: "Discharge" },
        { id: "p-disch-2", service: "discharge", flow: "fwd", width: 7, points: [[825, 168], [825, 110], [980, 110]], label: "" },
        { id: "p-cw", service: "cooling", flow: "fwd", width: 6, points: [[862, 300], [920, 300], [920, 380], [1000, 380]], label: "Cooling Water" },
        { id: "p-cw-ret", service: "cooling", flow: "rev", width: 6, points: [[560, 330], [700, 330], [700, 300], [788, 300]], label: "" },
        { id: "p-drain", service: "drain", flow: "fwd", width: 6, points: [[825, 352], [825, 430], [980, 430]], label: "Drain" },
      ],
      signals: [{ id: "s1", points: [[602, 164], [602, 440], [445, 440]] }, { id: "s2", points: [[475, 312], [475, 440]] }],
      equipment: [
        { id: "mtr", kind: "motor", x: 240, y: 300, w: 110, h: 90, name: "Motor", tag: "M-101", state: "run", params: { Current: "156 A", Voltage: "4.5 kV", Speed: "2980 rpm", Power: "1.2 MW" } },
        { id: "comp", kind: "compressor", x: 400, y: 215, w: 155, h: 95, name: "COMP-101", tag: "COMP-101", state: "run" },
        { id: "sep", kind: "drum", x: 790, y: 168, w: 70, h: 184, name: "SEP-101", tag: "SEP-101", state: "run" },
      ],
      instruments: [
        { id: "pt101", tag: "PT-101", fn: "PT", x: 150, y: 222, r: 14, value: 52.3, unit: "bar", face: "above" },
        { id: "tt102", tag: "TT-102", fn: "TT", x: 250, y: 222, r: 14, value: 48.7, unit: "°C", face: "above" },
        { id: "pt103", tag: "PT-103", fn: "PT", x: 588, y: 222, r: 14, value: 118.6, unit: "bar", face: "above" },
        { id: "tt104", tag: "TT-104", fn: "TT", x: 648, y: 222, r: 14, value: 76.2, unit: "°C", face: "above" },
        { id: "lt101", tag: "LT-101", fn: "LT", x: 870, y: 232, r: 14, value: 72.4, unit: "%", face: "right" },
        { id: "pic101", tag: "PIC-101", fn: "PIC", x: 416, y: 426, r: 14, loc: 1, value: 45.0, unit: "bar", face: "right" },
      ],
      valves: [
        { id: "xv101", tag: "XV-101", kind: "valve-pneumatic", x: 330, y: 246, size: 32, state: "open" },
        { id: "xv102", tag: "XV-102", kind: "valve-electric", x: 880, y: 284, size: 32, state: "open" },
        { id: "xv103", tag: "XV-103", kind: "valve-electric", x: 809, y: 395, size: 32, state: "closed", rot: 90 },
      ],
      connectors: [
        { id: "c-in", text: "From Upstream", x: 20, y: 232, dir: "in", side: "right" },
        { id: "c-hp", text: "To HP Header", x: 985, y: 110, dir: "out", side: "right" },
        { id: "c-cw", text: "Cooling Water", x: 1005, y: 380, dir: "out", side: "right" },
        { id: "c-dr", text: "Drain", x: 985, y: 430, dir: "out", side: "right" },
      ],
      labels: [],
    };
  };
  /* 예시 값 — 추이가 보이게 조금씩 흔들린다 */
  H.demoStates = function (tick) {
    const t = tick || 0, j = (a, s) => +(a + Math.sin(t / 3) * s + (Math.random() - 0.5) * s * 0.4).toFixed(1);
    return { "PT-101": { v: j(52.3, 0.6), u: "bar" }, "TT-102": { v: j(48.7, 0.5), u: "°C" }, "PT-103": { v: j(118.6, 1.2), u: "bar" }, "TT-104": { v: j(76.2, 0.8), u: "°C" },
             "LT-101": { v: j(72.4, 1.5), u: "%" }, "PIC-101": { v: 45.0, u: "bar" }, "XV-101": { open: true }, "XV-102": { open: true }, "XV-103": { open: false },
             "M-101": { state: "run", params: { Current: `${j(156, 3)} A`, Voltage: "4.5 kV", Speed: `${Math.round(j(2980, 6))} rpm`, Power: `${j(1.2, 0.03)} MW` } }, "COMP-101": { state: "run" }, "SEP-101": { state: "run" } };
  };
})();
