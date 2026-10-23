/* HMI 심볼 라이브러리 — 재사용 부품 (hotfix109).
 *
 * 모든 심볼은 100×100 상자 안에 그린 <symbol> 이고, `HMI.Symbols.use(kind, {x,y,w,h,rot,cls,extra})` 가 <use> 로 놓는다.
 * 색은 CSS 변수와 상태 class(`st-run` · `st-standby` · `st-trip` · `st-stop` · `st-oos`)가 정한다 — 심볼 안에는 색을 박지 않는다
 * (`fill="var(--hmi-equip)"` 꼴).  그래서 같은 심볼이 어느 화면에서든 그 화면의 테마와 상태 색을 따른다.
 *
 * 등록표(`REG`)가 하나이고 범례 · 심볼 라이브러리 패널은 이 표에서 만들어진다 — 심볼을 더하면 범례에도 저절로 선다.
 *   { kind, group: 'line'|'valve'|'rotating'|'vessel'|'instrument'|'misc', label, draw: (옵션) → 안쪽 SVG 글 }
 * 참고 그림(DCS Graphic — Compressor Train)의 Symbol Library (Detailed) 를 그대로 따랐다. */
(function () {
  "use strict";
  const H = (window.HMI = window.HMI || {});
  const EQ = 'fill="var(--hmi-equip)" stroke="var(--hmi-equip-line)" stroke-width="2.5"';
  const EQ2 = 'fill="var(--hmi-equip-dark)" stroke="var(--hmi-equip-line)" stroke-width="2"';
  const LN = 'fill="none" stroke="var(--hmi-equip-line)" stroke-width="2.5"';
  const FACE = 'fill="var(--hmi-face)" stroke="var(--hmi-face-line)" stroke-width="2.5"';

  // 밸브 나비 — 두 삼각형이 가운데서 만난다.  상태 색은 class 가 fill 을 바꾼다
  const bowtie = (fillAttr) => `<polygon points="8,30 50,50 8,70" ${fillAttr}/><polygon points="92,30 50,50 92,70" ${fillAttr}/>`;
  const stem = `<line x1="50" y1="50" x2="50" y2="22" stroke="var(--hmi-equip-line)" stroke-width="3"/>`;
  const VB = 'class="hmi-valve-body" stroke="var(--hmi-equip-line)" stroke-width="2.5"';

  const REG = [
    // ---------------- 선 (범례용 — 배관은 path 로 그리고 이 심볼은 범례 표본)
    { kind: "pipe", group: "line", label: "Process Line", draw: () => `<line x1="5" y1="50" x2="95" y2="50" stroke="var(--hmi-svc-process)" stroke-width="7" stroke-linecap="round"/>` },
    { kind: "signal", group: "line", label: "Instrument Signal (Dashed)", draw: () => `<line x1="5" y1="50" x2="95" y2="50" stroke="var(--hmi-signal)" stroke-width="3" stroke-dasharray="10 7"/>` },
    { kind: "flow", group: "line", label: "Flow Direction", draw: () => `<line x1="8" y1="50" x2="70" y2="50" stroke="var(--hmi-ink)" stroke-width="6"/><polygon points="66,34 96,50 66,66" fill="var(--hmi-ink)"/>` },
    { kind: "linebreak", group: "line", label: "Line Break", draw: () => `<line x1="5" y1="50" x2="38" y2="50" ${LN}/><line x1="62" y1="50" x2="95" y2="50" ${LN}/><path d="M38 36 L44 64 M56 36 L62 64" ${LN}/>` },
    // ---------------- 밸브
    { kind: "valve-manual", group: "valve", label: "Manual Valve", draw: () => bowtie(VB) + stem + `<line x1="34" y1="22" x2="66" y2="22" stroke="var(--hmi-equip-line)" stroke-width="3"/>` },
    { kind: "valve-pneumatic", group: "valve", label: "Control Valve (Pneumatic)", draw: () => bowtie(VB) + stem + `<path d="M28 22 A22 14 0 0 1 72 22 Z" ${EQ2}/>` },
    { kind: "valve-electric", group: "valve", label: "Control Valve (Electric)", draw: () => bowtie(VB) + stem + `<rect x="34" y="4" width="32" height="24" rx="3" ${EQ2}/><text x="50" y="21" font-size="15" text-anchor="middle" font-weight="700" fill="var(--hmi-ink)">M</text>` },
    { kind: "valve-check", group: "valve", label: "Check Valve", draw: () => `<polygon points="10,28 10,72 86,50" ${VB}/><line x1="86" y1="26" x2="86" y2="74" stroke="var(--hmi-equip-line)" stroke-width="4"/>` },
    { kind: "valve-block", group: "valve", label: "Block Valve", draw: () => bowtie(VB) + `<circle cx="50" cy="50" r="8" fill="var(--hmi-equip-line)"/>` },
    { kind: "valve-3way", group: "valve", label: "3-Way Valve", draw: () => bowtie(VB) + `<polygon points="30,92 50,50 70,92" ${VB}/>` + stem },
    { kind: "valve-angle", group: "valve", label: "Angle Valve", draw: () => `<polygon points="8,30 50,50 8,70" ${VB}/><polygon points="30,92 50,50 70,92" ${VB}/>` + stem },
    // ---------------- 회전 기기
    { kind: "pump", group: "rotating", label: "Pump", draw: () => `<circle cx="50" cy="52" r="32" ${EQ}/><circle cx="50" cy="52" r="14" ${EQ2}/><path d="M50 20 L50 10 L92 10" ${LN}/><path d="M30 78 L22 92 L78 92 L70 78" ${LN}/>` },
    { kind: "compressor", group: "rotating", label: "Compressor", draw: () => `<rect x="8" y="26" width="84" height="48" rx="8" ${EQ}/><rect x="16" y="34" width="68" height="32" rx="4" ${EQ2}/>` + [22, 32, 42, 52, 62, 72].map((x) => `<line x1="${x}" y1="36" x2="${x}" y2="64" stroke="var(--hmi-equip-line)" stroke-width="2"/>`).join("") + `<rect x="0" y="40" width="10" height="20" ${EQ2}/><rect x="90" y="40" width="10" height="20" ${EQ2}/><rect x="20" y="74" width="60" height="8" ${EQ2}/>` },
    { kind: "motor", group: "rotating", label: "Motor", draw: () => `<rect x="14" y="30" width="60" height="44" rx="6" ${EQ}/>` + [24, 34, 44, 54, 64].map((x) => `<line x1="${x}" y1="34" x2="${x}" y2="70" stroke="var(--hmi-equip-line)" stroke-width="2"/>`).join("") + `<rect x="30" y="18" width="28" height="12" rx="2" ${EQ2}/><rect x="74" y="44" width="18" height="12" ${EQ2}/><rect x="10" y="74" width="68" height="8" ${EQ2}/><text x="44" y="57" font-size="16" text-anchor="middle" font-weight="700" fill="var(--hmi-ink)">M</text>` },
    { kind: "turbine", group: "rotating", label: "Turbine", draw: () => `<polygon points="10,36 90,20 90,80 10,64" ${EQ}/><line x1="0" y1="50" x2="10" y2="50" ${LN}/><line x1="90" y1="50" x2="100" y2="50" ${LN}/><rect x="30" y="80" width="40" height="8" ${EQ2}/>` },
    { kind: "blower", group: "rotating", label: "Blower", draw: () => `<circle cx="50" cy="50" r="34" ${EQ}/><path d="M50 50 L50 20 A30 30 0 0 1 78 40 Z M50 50 L78 60 A30 30 0 0 1 40 78 Z M50 50 L26 66 A30 30 0 0 1 24 36 Z" ${EQ2}/><rect x="84" y="42" width="16" height="16" ${EQ2}/>` },
    { kind: "fan", group: "rotating", label: "Fan", draw: () => `<circle cx="50" cy="50" r="36" ${LN}/>` + [0, 72, 144, 216, 288].map((a) => `<path d="M50 50 L62 18 Q50 26 38 18 Z" transform="rotate(${a} 50 50)" ${EQ2}/>`).join("") + `<circle cx="50" cy="50" r="7" ${EQ}/>` },
    // ---------------- 열교환기 · 용기
    { kind: "heat-exchanger", group: "vessel", label: "Heat Exchanger (Shell & Tube)", draw: () => `<rect x="14" y="32" width="72" height="36" rx="18" ${EQ}/><line x1="26" y1="32" x2="26" y2="68" ${LN}/><line x1="74" y1="32" x2="74" y2="68" ${LN}/><path d="M26 44 H74 M26 56 H74" stroke="var(--hmi-equip-line)" stroke-width="2"/><path d="M0 50 H14 M86 50 H100 M50 20 V32 M50 68 V80" ${LN}/>` },
    { kind: "air-cooler", group: "vessel", label: "Air Cooler", draw: () => `<rect x="10" y="40" width="80" height="22" ${EQ}/><path d="M18 40 V62 M30 40 V62 M42 40 V62 M54 40 V62 M66 40 V62 M78 40 V62" stroke="var(--hmi-equip-line)" stroke-width="1.5"/><circle cx="50" cy="78" r="12" ${EQ2}/><path d="M50 78 L58 68 M50 78 L42 68 M50 78 L50 90" ${LN}/>` },
    { kind: "drum", group: "vessel", label: "Drum / Separator", draw: () => `<rect x="30" y="8" width="40" height="84" rx="20" ${EQ}/><line x1="30" y1="34" x2="70" y2="34" ${LN}/><line x1="30" y1="66" x2="70" y2="66" ${LN}/><path d="M0 24 H30 M70 24 H100 M50 92 V100" ${LN}/>` },
    { kind: "column", group: "vessel", label: "Column", draw: () => `<rect x="36" y="4" width="28" height="92" rx="14" ${EQ}/>` + [24, 38, 52, 66, 80].map((y) => `<line x1="36" y1="${y}" x2="64" y2="${y}" stroke="var(--hmi-equip-line)" stroke-width="1.5"/>`).join("") },
    { kind: "tank", group: "vessel", label: "Storage Tank", draw: () => `<rect x="12" y="22" width="76" height="68" rx="6" ${EQ}/><path d="M12 22 Q50 4 88 22" ${EQ2}/><line x1="12" y1="56" x2="88" y2="56" stroke="var(--hmi-equip-line)" stroke-width="1.5" stroke-dasharray="4 3"/>` },
    { kind: "vessel-h", group: "vessel", label: "Horizontal Vessel", draw: () => `<rect x="6" y="30" width="88" height="40" rx="20" ${EQ}/><line x1="26" y1="30" x2="26" y2="70" ${LN}/><line x1="74" y1="30" x2="74" y2="70" ${LN}/>` },
    { kind: "header", group: "vessel", label: "Header", draw: () => `<rect x="4" y="40" width="92" height="20" rx="10" ${EQ}/><path d="M24 40 V24 M50 40 V24 M76 40 V24" ${LN}/>` },
    { kind: "box", group: "vessel", label: "Equipment (Generic)", draw: () => `<rect x="8" y="22" width="84" height="56" rx="6" ${EQ}/>` },
    // ---------------- 계기 (버블)
    { kind: "inst-field", group: "instrument", label: "Field Instrument (Transmitter)", draw: () => `<circle cx="50" cy="50" r="40" ${FACE}/>` },
    { kind: "inst-dcs", group: "instrument", label: "DCS Function (Controller)", draw: () => `<circle cx="50" cy="50" r="40" ${FACE}/><line x1="10" y1="50" x2="90" y2="50" stroke="var(--hmi-face-line)" stroke-width="2.5"/>` },
    { kind: "inst-panel", group: "instrument", label: "Local Panel", draw: () => `<circle cx="50" cy="50" r="40" ${FACE}/><line x1="10" y1="46" x2="90" y2="46" stroke="var(--hmi-face-line)" stroke-width="2"/><line x1="10" y1="54" x2="90" y2="54" stroke="var(--hmi-face-line)" stroke-width="2"/>` },
    { kind: "inst-local", group: "instrument", label: "Local Indicator / Display", draw: () => `<rect x="12" y="24" width="76" height="52" rx="4" ${FACE}/>` },
    // ---------------- 그 밖
    { kind: "junction-box", group: "misc", label: "Junction Box", draw: () => `<rect x="18" y="26" width="64" height="48" rx="4" ${EQ2}/><circle cx="34" cy="50" r="5" fill="var(--hmi-equip-line)"/><circle cx="50" cy="50" r="5" fill="var(--hmi-equip-line)"/><circle cx="66" cy="50" r="5" fill="var(--hmi-equip-line)"/>` },
    { kind: "plc", group: "misc", label: "PLC / RTU", draw: () => `<rect x="14" y="22" width="72" height="56" rx="4" ${EQ2}/><rect x="22" y="30" width="56" height="12" fill="var(--hmi-acc)"/><rect x="22" y="48" width="20" height="20" ${EQ}/><rect x="48" y="48" width="30" height="20" ${EQ}/>` },
    { kind: "cabinet", group: "misc", label: "DCS Cabinet", draw: () => `<rect x="24" y="8" width="52" height="84" rx="4" ${EQ2}/><rect x="32" y="16" width="36" height="22" ${EQ}/><rect x="32" y="44" width="36" height="10" fill="var(--hmi-acc)"/><rect x="32" y="60" width="36" height="22" ${EQ}/>` },
    { kind: "hmi", group: "misc", label: "Panel / HMI", draw: () => `<rect x="10" y="18" width="80" height="54" rx="4" ${EQ2}/><rect x="18" y="26" width="64" height="38" fill="var(--hmi-bg)"/><rect x="36" y="76" width="28" height="8" ${EQ2}/>` },
    { kind: "workstation", group: "misc", label: "Computer / Workstation", draw: () => `<rect x="12" y="16" width="76" height="50" rx="4" ${EQ2}/><rect x="20" y="24" width="60" height="34" fill="var(--hmi-bg)"/><rect x="40" y="66" width="20" height="10" ${EQ2}/><rect x="26" y="78" width="48" height="8" ${EQ2}/>` },
    { kind: "trend", group: "misc", label: "Trend Display", draw: () => `<rect x="10" y="18" width="80" height="60" rx="4" ${EQ2}/><polyline points="18,66 32,50 46,56 60,36 74,42 84,28" fill="none" stroke="var(--hmi-ok)" stroke-width="3"/>` },
  ];
  const BY = Object.fromEntries(REG.map((r) => [r.kind, r]));

  const Symbols = (H.Symbols = {
    list: () => REG.slice(),
    get: (kind) => BY[kind] || null,
    groups: { line: "Piping & Lines", valve: "Valves", rotating: "Pumps & Compressors", vessel: "Heat Exchangers & Vessels", instrument: "Instruments (Tag Symbols)", misc: "Miscellaneous" },
    /* <defs> 에 넣을 전체 심볼 */
    defs() {
      return "<defs>" + REG.map((r) => `<symbol id="hmi-sym-${r.kind}" viewBox="0 0 100 100" overflow="visible">${r.draw()}</symbol>`).join("")
        + `<marker id="hmi-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="14" markerHeight="14" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M0 0 L10 5 L0 10 Z" fill="context-stroke"/></marker>`
        + "</defs>";
    },
    /* 한 심볼을 놓는다.  w·h 는 화면 단위 · rot 는 중심을 축으로 도는 각도 */
    use(kind, o) {
      const r = BY[kind] ? kind : "box";
      const w = o.w || 60, h = o.h || w, x = o.x || 0, y = o.y || 0;
      const t = `translate(${x} ${y})` + (o.rot ? ` rotate(${o.rot} ${w / 2} ${h / 2})` : "");
      return `<g class="hmi-sym hmi-${r}${o.cls ? " " + o.cls : ""}" transform="${t}"${o.attrs || ""}><use href="#hmi-sym-${r}" width="${w}" height="${h}"/>${o.extra || ""}</g>`;
    },
    /* 범례 · 라이브러리 패널용 작은 SVG 하나 */
    icon(kind, size) {
      const s = size || 34;
      return `<svg class="hmi-icon" width="${s}" height="${s}" viewBox="0 0 100 100" aria-hidden="true"><use href="#hmi-sym-${BY[kind] ? kind : "box"}"/></svg>`;
    },
  });

  /* 식별된 기기 이름(도면 낱말)에서 심볼을 고른다 — 낱말이 없으면 generic.  뜻은 영어 기기 명사 (프로젝트 값 아님). */
  const NOUN = [
    [/COMPRESSOR|COMPR\b|\bCOMP\b/, "compressor"], [/\bMOTOR\b|\bM\/?E\b/, "motor"], [/TURBINE|\bST\b(?!EAM)|\bGT\b/, "turbine"],
    [/BLOWER/, "blower"], [/\bFAN\b|FANS\b/, "fan"], [/PUMP|\bP-?\d/, "pump"],
    [/HEAT ?EXCHANGER|\bHEX\b|COOLER|CONDENSER|HEATER|ECONOMIZER|ECONOMISER|EVAPORATOR|SUPERHEATER|REHEATER/, "heat-exchanger"],
    [/AIR ?COOL|FIN ?FAN/, "air-cooler"], [/SEPARATOR|DRUM|\bKO\b|KNOCK|FLASH|RECEIVER|ACCUMULATOR|DEAERATOR/, "drum"],
    [/COLUMN|TOWER|STRIPPER|ABSORBER|SCRUBBER|STACK/, "column"], [/TANK|SUMP|PIT\b|BASIN|SILO|HOPPER/, "tank"],
    [/VESSEL|FILTER|STRAINER|SKID|PACKAGE/, "vessel-h"], [/HEADER|MANIFOLD/, "header"],
  ];
  Symbols.kindForName = (name) => {
    const u = String(name || "").toUpperCase();
    for (const [re, k] of NOUN) if (re.test(u)) return k;
    return "box";
  };
  /* 밸브 몸체 · 액추에이터 → 심볼 */
  Symbols.kindForValve = (body, actuator) => {
    const b = String(body || "").toUpperCase(), a = String(actuator || "").toUpperCase();
    if (/CHECK|NRV/.test(b)) return "valve-check";
    if (/THREE|3-?WAY/.test(b)) return "valve-3way";
    if (/ANGLE/.test(b)) return "valve-angle";
    if (/MOTOR|ELECTRIC|HYDRAULIC|\bE\/?H\b/.test(a)) return "valve-electric";
    if (/PNEUMATIC|DIAPHRAGM|PISTON|CYLINDER|AIR/.test(a)) return "valve-pneumatic";
    return "valve-manual";
  };
})();
