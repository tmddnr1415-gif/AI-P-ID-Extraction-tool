/* HMI 심볼 라이브러리 — 개별 SVG 컴포넌트 (viewBox 0 0 100 100).
 *
 * 한 사전(HMI_SYM) 이 세 곳을 먹인다: 공정 그래픽 · 오른쪽 Symbol & Legend · 아래 Symbol Library.
 * 그래서 그림과 설명이 어긋날 길이 없다.  참고 PNG 는 쓰지 않는다 — 전부 선·면으로 다시 그린 것이다.
 * 다른 Process Diagram 에서도 그대로 쓴다: 장면 JSON 이 `sym` 이름으로 이 사전을 가리킨다.
 *
 *   HMI_SYM.<name> = { cat, label, ko, draw(opts) → SVG 안쪽 글자, ports: {in:[x,y], out:[x,y]} }
 *   HMI_SYM_CATS   = 범례 묶음 순서
 *   HMI_LINES      = 배관 종류 (색 · 점선 · 설명)
 *   HMI_STATUS     = 상태 색
 */
(function (root) {
  "use strict";
  const C = {
    body: "#9fb0c3", bodyDark: "#5f6f82", bodyLight: "#d7e0ea", edge: "#2c3a4b",
    ink: "#dbe6f2", dcs: "#0d1b2a"
  };
  // 배관 종류 — 색은 참고 화면의 네 색 + 신호선 (ISA 5.1 의 뜻을 따르지는 않는다 · 현장 HMI 관례)
  const LINES = {
    process:   { color: "#f5b400", ko: "공정 (Process Fluid)",        en: "Process",   dash: "" },
    discharge: { color: "#2d8cff", ko: "토출 (High Pressure)",        en: "Discharge", dash: "" },
    cooling:   { color: "#1fbf9f", ko: "냉각수 / Utility",            en: "Cooling Water / Utility", dash: "" },
    drain:     { color: "#b24cff", ko: "드레인 / Waste",               en: "Drain / Waste", dash: "" },
    signal:    { color: "#9fb3c8", ko: "계장 신호 (전기 · 공압)",       en: "Instrument Signal", dash: "6 5" },
    // hotfix110 — 식별된 P&ID 의 라인 번호 계통(KKS)에서 고르는 종류 (app/hmi/scene.py service_of) · 범례는 장면에 쓰인 것만 보인다
    steam:     { color: "#ff8a3d", ko: "증기 (Steam)",                 en: "Steam", dash: "" },
    water:     { color: "#5bd6ff", ko: "급수 · 응축수 (Water)",         en: "Feed / Condensate Water", dash: "" },
    fuel:      { color: "#d9a35b", ko: "연료 (Fuel Gas · Oil)",          en: "Fuel", dash: "" },
    air:       { color: "#a3e05b", ko: "공기 · 가스 (Air / Gas)",        en: "Air / Gas", dash: "" },
    chem:      { color: "#ff7fbf", ko: "약품 (Chemical)",               en: "Chemical", dash: "" }
  };
  const STATUS = {
    running: { color: "#2ecc71", ko: "Running / Normal", en: "Running" },
    standby: { color: "#f5c518", ko: "Standby",          en: "Standby" },
    trip:    { color: "#ff3b6b", ko: "Trip / Alarm",     en: "Trip / Alarm" },
    stopped: { color: "#7f8c9a", ko: "Stopped",          en: "Stopped" },
    oos:     { color: "#eef2f6", ko: "Not In Service",   en: "Not In Service" }
  };

  // ---- 작은 그리기 도우미 (전부 글자 — 렌더러가 <g> 안에 넣는다)
  const px = (n) => Math.round(n * 100) / 100;
  function rect(x, y, w, h, fill, extra) {
    return `<rect x="${px(x)}" y="${px(y)}" width="${px(w)}" height="${px(h)}" fill="${fill}" stroke="${C.edge}" stroke-width="2" ${extra || ""}/>`;
  }
  function stadium(x, y, w, h, fill) {     // 둥근 양 끝 (용기 · 드럼)
    const r = Math.min(w, h) / 2;
    return `<rect x="${px(x)}" y="${px(y)}" width="${px(w)}" height="${px(h)}" rx="${px(r)}" ry="${px(r)}" fill="${fill}" stroke="${C.edge}" stroke-width="2"/>`;
  }
  function fins(x0, x1, y0, y1, n) {       // 압축기 · 모터 · 열교환기의 가로 줄무늬
    let s = "";
    for (let i = 1; i < n; i++) {
      const y = y0 + (y1 - y0) * i / n;
      s += `<line x1="${px(x0)}" y1="${px(y)}" x2="${px(x1)}" y2="${px(y)}" stroke="${C.bodyDark}" stroke-width="1.5"/>`;
    }
    return s;
  }
  function bowtie(cx, cy, w, h, fill) {     // 밸브 몸체 — 꼭짓점을 맞댄 두 삼각형
    const l = cx - w / 2, r = cx + w / 2, t = cy - h / 2, b = cy + h / 2;
    return `<path d="M${px(l)},${px(t)} L${px(cx)},${px(cy)} L${px(l)},${px(b)} Z M${px(r)},${px(t)} L${px(cx)},${px(cy)} L${px(r)},${px(b)} Z" fill="${fill}" stroke="${C.edge}" stroke-width="2" stroke-linejoin="round"/>`;
  }
  function stem(cx, cy, top) {
    return `<line x1="${px(cx)}" y1="${px(cy)}" x2="${px(cx)}" y2="${px(top)}" stroke="${C.edge}" stroke-width="2.5"/>`;
  }
  function gradientDefs(id, light, dark) {
    return `<linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${light}"/><stop offset="1" stop-color="${dark}"/></linearGradient>`;
  }
  const METAL = "url(#hmi-metal)";     // 렌더러가 <defs> 에 한 번 둔다 (defs() 참조)

  const SYM = {};
  function def(name, cat, label, ko, draw, ports) {
    SYM[name] = { name, cat, label, ko, draw, ports: ports || { in: [0, 50], out: [100, 50] } };
  }

  // ---- 밸브
  def("valve_manual", "valve", "Manual Valve", "수동 밸브", (o) =>
    bowtie(50, 60, 60, 36, o && o.closed ? C.bodyDark : C.bodyLight) + stem(50, 60, 32) +
    `<line x1="36" y1="32" x2="64" y2="32" stroke="${C.edge}" stroke-width="3"/>`,
    { in: [20, 60], out: [80, 60] });
  def("valve_control_pneumatic", "valve", "Control Valve (Pneumatic)", "제어 밸브 (공압)", (o) =>
    bowtie(50, 62, 60, 36, o && o.closed ? C.bodyDark : C.bodyLight) + stem(50, 62, 36) +
    `<path d="M24,36 A26,16 0 0 1 76,36 Z" fill="${C.body}" stroke="${C.edge}" stroke-width="2"/>`,
    { in: [20, 62], out: [80, 62] });
  def("valve_control_electric", "valve", "Control Valve (Electric / MOV)", "전동 밸브 (MOV)", (o) =>
    bowtie(50, 64, 60, 34, o && o.closed ? C.bodyDark : C.bodyLight) + stem(50, 64, 40) +
    `<circle cx="50" cy="26" r="14" fill="${C.body}" stroke="${C.edge}" stroke-width="2"/>` +
    `<text x="50" y="31" font-size="15" font-weight="700" text-anchor="middle" fill="${C.edge}">M</text>`,
    { in: [20, 64], out: [80, 64] });
  def("valve_check", "valve", "Check Valve", "체크 밸브", () =>
    `<path d="M20,32 L80,50 L20,68 Z" fill="${C.bodyLight}" stroke="${C.edge}" stroke-width="2" stroke-linejoin="round"/>` +
    `<line x1="80" y1="30" x2="80" y2="70" stroke="${C.edge}" stroke-width="4"/>`);
  def("valve_block", "valve", "Block Valve (XV)", "차단 밸브 (XV)", (o) =>
    bowtie(50, 62, 60, 36, o && o.closed ? C.bodyDark : C.bodyLight) + stem(50, 62, 34) +
    rect(36, 20, 28, 14, C.body) +
    `<text x="50" y="31" font-size="10" text-anchor="middle" fill="${C.edge}">S</text>`,
    { in: [20, 62], out: [80, 62] });
  def("valve_3way", "valve", "3-Way Valve", "3방 밸브", () =>
    bowtie(50, 60, 60, 36, C.bodyLight) +
    `<path d="M32,78 L50,60 L68,78 Z" fill="${C.bodyLight}" stroke="${C.edge}" stroke-width="2" stroke-linejoin="round"/>` +
    stem(50, 60, 34) + `<line x1="36" y1="34" x2="64" y2="34" stroke="${C.edge}" stroke-width="3"/>`);

  // ---- 펌프 · 압축기 · 회전기기
  def("pump", "rotating", "Pump", "펌프 (원심)", () =>
    `<circle cx="50" cy="52" r="26" fill="${METAL}" stroke="${C.edge}" stroke-width="2"/>` +
    `<circle cx="50" cy="52" r="9" fill="${C.bodyDark}" stroke="${C.edge}" stroke-width="2"/>` +
    `<path d="M50,26 L86,26 L86,34" fill="none" stroke="${C.edge}" stroke-width="3"/>` +
    rect(28, 78, 44, 8, C.bodyDark),
    { in: [24, 52], out: [86, 30] });
  def("compressor", "rotating", "Compressor", "압축기", () =>
    rect(10, 34, 80, 36, METAL, 'rx="6"') + fins(14, 86, 36, 68, 6) +
    rect(0, 44, 10, 16, C.bodyDark) + rect(90, 44, 10, 16, C.bodyDark) +
    rect(20, 70, 60, 8, C.bodyDark) + rect(14, 78, 72, 6, C.bodyLight),
    { in: [0, 52], out: [100, 52] });
  def("motor", "rotating", "Motor", "전동기", () =>
    rect(14, 30, 64, 44, METAL, 'rx="8"') + fins(18, 74, 34, 70, 7) +
    rect(78, 44, 14, 16, C.bodyDark) + rect(32, 20, 28, 10, C.body, 'rx="3"') +
    rect(8, 74, 76, 8, C.bodyDark) + `<text x="46" y="57" font-size="16" font-weight="700" text-anchor="middle" fill="${C.edge}">M</text>`,
    { in: [14, 52], out: [92, 52] });
  def("turbine", "rotating", "Turbine", "터빈", () =>
    `<path d="M14,34 L86,22 L86,78 L14,66 Z" fill="${METAL}" stroke="${C.edge}" stroke-width="2" stroke-linejoin="round"/>` +
    fins(18, 82, 30, 70, 5) + rect(86, 42, 10, 16, C.bodyDark) + rect(10, 74, 80, 8, C.bodyDark),
    { in: [14, 50], out: [96, 50] });
  def("blower", "rotating", "Blower", "송풍기", () =>
    `<circle cx="50" cy="52" r="26" fill="${METAL}" stroke="${C.edge}" stroke-width="2"/>` +
    `<path d="M50,26 L90,26 L90,38" fill="none" stroke="${C.edge}" stroke-width="3"/>` +
    `<circle cx="50" cy="52" r="7" fill="${C.bodyDark}"/>` +
    `<path d="M50,30 L50,74 M28,52 L72,52" stroke="${C.bodyDark}" stroke-width="3"/>` + rect(30, 78, 40, 8, C.bodyDark));
  def("fan", "rotating", "Fan", "팬", () =>
    `<circle cx="50" cy="50" r="30" fill="${C.bodyLight}" stroke="${C.edge}" stroke-width="2"/>` +
    `<path d="M50,50 C60,30 76,34 70,48 C64,62 50,56 50,50 Z M50,50 C30,60 34,76 48,70 C62,64 56,50 50,50 Z M50,50 C40,30 24,34 30,48 C36,62 50,56 50,50 Z M50,50 C70,60 66,76 52,70 C38,64 44,50 50,50 Z" fill="${C.body}" stroke="${C.edge}" stroke-width="1.5"/>` +
    `<circle cx="50" cy="50" r="5" fill="${C.bodyDark}"/>`);

  // ---- 열교환기 · 용기
  def("heat_exchanger", "vessel", "Heat Exchanger (Shell & Tube)", "열교환기 (셸 & 튜브)", () =>
    rect(12, 34, 76, 32, METAL, 'rx="10"') + fins(16, 84, 38, 62, 4) +
    rect(2, 42, 10, 16, C.bodyDark) + rect(88, 42, 10, 16, C.bodyDark) +
    rect(36, 24, 8, 10, C.bodyDark) + rect(56, 66, 8, 10, C.bodyDark),
    { in: [2, 50], out: [98, 50] });
  def("air_cooler", "vessel", "Air Cooler", "공랭식 냉각기", () =>
    rect(10, 36, 80, 28, C.bodyLight) + fins(12, 88, 36, 64, 6) +
    `<circle cx="50" cy="50" r="10" fill="${C.body}" stroke="${C.edge}" stroke-width="2"/>` +
    rect(14, 64, 6, 14, C.bodyDark) + rect(80, 64, 6, 14, C.bodyDark));
  def("separator", "vessel", "Drum / Separator", "드럼 / 분리기", () =>
    stadium(32, 8, 36, 84, METAL) + `<line x1="32" y1="24" x2="68" y2="24" stroke="${C.bodyDark}" stroke-width="1.5"/>` +
    `<line x1="32" y1="76" x2="68" y2="76" stroke="${C.bodyDark}" stroke-width="1.5"/>` +
    rect(44, 92, 12, 6, C.bodyDark) + rect(22, 46, 10, 8, C.bodyDark) + rect(68, 46, 10, 8, C.bodyDark),
    { in: [22, 50], out: [78, 50] });
  def("column", "vessel", "Column", "탑 (칼럼)", () =>
    stadium(38, 4, 24, 92, METAL) + fins(38, 62, 14, 86, 8) + rect(28, 40, 10, 6, C.bodyDark) + rect(62, 60, 10, 6, C.bodyDark));
  def("storage_tank", "vessel", "Storage Tank", "저장 탱크", () =>
    rect(16, 30, 68, 56, METAL, 'rx="4"') + `<path d="M16,30 A34,10 0 0 1 84,30" fill="${C.bodyLight}" stroke="${C.edge}" stroke-width="2"/>` +
    `<line x1="16" y1="58" x2="84" y2="58" stroke="${C.bodyDark}" stroke-width="1.5"/>` + rect(12, 86, 76, 6, C.bodyDark));

  // ---- 계기 — 하나의 컴포넌트에 글자(PT · TT · PIC …)와 종류(현장 · DCS · 현지 표시)를 준다
  function bubble(letters, kind) {
    const k = kind || "field";
    let s = "";
    if (k === "local") {
      s += rect(18, 18, 64, 64, C.dcs, 'rx="6"');
    } else {
      s += `<circle cx="50" cy="50" r="32" fill="${k === "dcs" ? C.dcs : "#13263a"}" stroke="${C.ink}" stroke-width="3"/>`;
      if (k === "dcs") s += `<line x1="18" y1="50" x2="82" y2="50" stroke="${C.ink}" stroke-width="2"/>`;
    }
    const fs = (letters || "").length > 3 ? 20 : 24;
    s += `<text x="50" y="${k === "dcs" ? 44 : 58}" font-size="${fs}" font-weight="700" text-anchor="middle" fill="${C.ink}" font-family="Segoe UI, Malgun Gothic, sans-serif">${letters || ""}</text>`;
    return s;
  }
  def("instrument", "instrument", "Instrument (Tag Bubble)", "계기 버블", (o) => bubble(o && o.letters, o && o.kind),
    { in: [50, 82], out: [50, 18] });
  // 범례에 보일 계기 글자 — 뜻은 ISA 5.1 머리글자 (P·T·L·F · I 표시 · T 전송 · C 제어)
  const INSTRUMENTS = [
    ["PT", "Pressure Transmitter", "압력 전송기", "field"],
    ["TT", "Temperature Transmitter", "온도 전송기", "field"],
    ["LT", "Level Transmitter", "레벨 전송기", "field"],
    ["FT", "Flow Transmitter", "유량 전송기", "field"],
    ["PIC", "Pressure Indicating Controller", "압력 지시 제어기", "dcs"],
    ["TIC", "Temperature Indicating Controller", "온도 지시 제어기", "dcs"],
    ["FIC", "Flow Indicating Controller", "유량 지시 제어기", "dcs"],
    ["LIC", "Level Indicating Controller", "레벨 지시 제어기", "dcs"],
    ["TI", "Local Indicator / Display", "현지 표시계", "local"]
  ];

  // ---- 기타
  def("junction_box", "misc", "Junction Box", "정션 박스", () =>
    rect(22, 28, 56, 44, C.bodyDark, 'rx="3"') + `<circle cx="34" cy="40" r="3" fill="${C.ink}"/><circle cx="66" cy="40" r="3" fill="${C.ink}"/><circle cx="34" cy="60" r="3" fill="${C.ink}"/><circle cx="66" cy="60" r="3" fill="${C.ink}"/>`);
  def("plc", "misc", "PLC / RTU", "PLC / RTU", () =>
    rect(18, 26, 64, 48, C.dcs, 'rx="3"') + rect(24, 32, 18, 36, C.bodyDark) + rect(46, 32, 30, 10, "#2d8cff") + rect(46, 46, 30, 22, C.bodyDark));
  def("dcs_cabinet", "misc", "DCS Cabinet", "DCS 캐비닛", () =>
    rect(26, 10, 48, 80, C.dcs, 'rx="3"') + rect(32, 16, 36, 22, C.bodyDark) + rect(32, 42, 36, 22, C.bodyDark) + `<circle cx="50" cy="78" r="4" fill="#2ecc71"/>`);
  def("panel_hmi", "misc", "Panel / HMI", "패널 / HMI", () =>
    rect(14, 22, 72, 50, C.dcs, 'rx="3"') + rect(20, 28, 60, 38, "#1f6feb") + rect(40, 72, 20, 8, C.bodyDark) + rect(28, 80, 44, 4, C.bodyDark));
  def("workstation", "misc", "Computer / Workstation", "운전원 워크스테이션", () =>
    rect(14, 24, 72, 44, C.dcs, 'rx="3"') + rect(20, 30, 60, 32, "#2d8cff") + rect(44, 68, 12, 8, C.bodyDark) + rect(26, 76, 48, 6, C.bodyDark));
  def("trend_display", "misc", "Trend Display", "트렌드 표시", () =>
    rect(14, 22, 72, 56, C.dcs, 'rx="3"') + `<polyline points="22,66 36,54 48,58 60,40 74,44 80,32" fill="none" stroke="#2ecc71" stroke-width="3"/>`);

  const CATS = [
    { key: "line", label: "Piping & Lines", ko: "배관 · 신호선" },
    { key: "valve", label: "Valves", ko: "밸브" },
    { key: "rotating", label: "Pumps & Compressors", ko: "펌프 · 압축기" },
    { key: "vessel", label: "Heat Exchangers & Vessels", ko: "열교환기 · 용기" },
    { key: "instrument", label: "Instruments (Tag Symbols)", ko: "계기 (태그 심볼)" },
    { key: "misc", label: "Miscellaneous", ko: "기타" }
  ];

  /** 독립 <svg> 로 — 범례 · 라이브러리 · 시험용. */
  function svg(name, opts, size) {
    const s = SYM[name];
    if (!s) return "";
    const sz = size || 40;
    return `<svg class="hmi-sym hmi-sym-${name}" viewBox="0 0 100 100" width="${sz}" height="${sz}" aria-label="${s.label}">${defs()}${s.draw(opts || {})}</svg>`;
  }
  /** 장면 안 <g> 로 — 왼쪽 위 (x,y) · 폭 w · 높이 h · 회전 rot(도). */
  function g(name, x, y, w, h, opts, rot) {
    const s = SYM[name];
    if (!s) return "";
    const sx = (w || 100) / 100, sy = (h || 100) / 100;
    const r = rot ? ` rotate(${rot} 50 50)` : "";
    return `<g class="hmi-sym hmi-sym-${name}" transform="translate(${px(x)} ${px(y)}) scale(${px(sx)} ${px(sy)})${r}">${s.draw(opts || {})}</g>`;
  }
  function defs() {
    return `<defs>${gradientDefs("hmi-metal", "#e3eaf2", "#8b9bb0")}</defs>`;
  }
  /** 라인 그리기용 <defs> (렌더러가 장면 svg 에 한 번) — 종류마다 화살촉. */
  function lineDefs() {
    let s = gradientDefs("hmi-metal", "#e3eaf2", "#8b9bb0");
    for (const k of Object.keys(LINES)) {
      s += `<marker id="hmi-arrow-${k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="${LINES[k].color}"/></marker>`;
    }
    return `<defs>${s}</defs>`;
  }
  /** 글자(태그 머리글자)로 계기 종류를 정한다 — ISA 5.1: 둘째 이후 글자에 C(제어)가 있으면 DCS, I 만 있고 전송(T)이 없으면 현지 표시. */
  function instrumentKind(letters) {
    const L = (letters || "").toUpperCase();
    if (L.length < 2) return "field";
    const tail = L.slice(1);
    if (tail.includes("C")) return "dcs";
    if (tail.includes("T")) return "field";
    if (tail === "I" || tail === "G") return "local";
    return "field";
  }

  root.HMI_SYM = SYM;
  root.HMI_SYM_CATS = CATS;
  root.HMI_LINES = LINES;
  root.HMI_STATUS = STATUS;
  root.HMI_INSTRUMENTS = INSTRUMENTS;
  root.HMI_SYMBOLS = { svg, g, defs, lineDefs, instrumentKind, bubble };
})(typeof window !== "undefined" ? window : (typeof module !== "undefined" ? module.exports : globalThis));
