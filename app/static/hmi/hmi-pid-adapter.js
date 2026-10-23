/* 식별된 P&ID(서버 `/dcs/api/jobs/{id}/sheet/{p}/model` — hotfix107 모델) → HMI 모델 (hotfix109).
 *
 * 규칙 — 지어내지 않는다:
 *  · 자리는 P&ID 좌표 그대로 (버블 사각형 · 몸체 사각형 · 기기 라벨 자리 · 런).  y 는 아래로 갈수록 큰 PDF 좌표 그대로.
 *  · 계기 기능 글자(fn)는 그 행의 TYPE, 태그는 그 행의 태그 번호, 사람이 고친 태그(`overrides.tags[key]`)가 있으면 그것.
 *  · 배관 서비스(색)는 라인 번호의 **계통 코드**(KKS 둘째 묶음 `12LBB50` → `LBB` · 없으면 그 계기의 라인)로 고른다 —
 *    표는 KKS 계통 글자의 **첫 글자**만 쓴다 (L 증기·물 · P 냉각수 · G 보조·가스 · H 연료 · M 기계 · Q 약품 …).  모르면 'other'.
 *  · 흐름 방향은 도면이 말한 곳에서만 — 런 끝의 `TO …` 커넥터가 있으면 그쪽으로, `FROM …` 이면 들어오는 화살.  나머지는 화살 없음.
 *  · 기기 심볼은 도면이 인쇄한 이름의 명사로 고른다 (`HMI.Symbols.kindForName`) · 밸브는 몸체·액추에이터로. */
(function () {
  "use strict";
  const H = (window.HMI = window.HMI || {});
  const S = H.Symbols;
  const SVC_BY_LETTER = { L: "steam", P: "cooling", G: "air", H: "fuel", M: "process", Q: "chem", N: "water", E: "process", U: "other", W: "water", A: "process", B: "process", C: "process", S: "other" };
  const SVC_BY_SYS = { LBA: "steam", LBB: "steam", LBC: "steam", LBG: "steam", LBQ: "steam", LCA: "water", LCB: "water", LCH: "water", LAB: "water", LAE: "water", LAC: "water", LAA: "water",
                       PAB: "cooling", PCB: "cooling", PGB: "cooling", PGA: "cooling", PAC: "cooling", GHC: "drain", GHB: "drain", GMA: "drain", LCM: "drain", GKB: "fuel", EKG: "fuel", EGB: "fuel",
                       QCA: "chem", QUP: "chem", GKC: "air", QFB: "air", MBP: "process", MAG: "process", MBA: "process", HAD: "process", HAC: "process" };
  function serviceOf(lineNo) {
    const m = String(lineNo || "").toUpperCase().match(/^\d{0,2}([A-Z]{3})/);
    if (!m) return "other";
    return SVC_BY_SYS[m[1]] || SVC_BY_LETTER[m[1][0]] || "other";
  }
  H.serviceOf = serviceOf;
  const key = (a) => a.map((v) => Math.round(v * 10) / 10).join(",");

  H.fromPid = function (model, overrides) {
    const ov = overrides || {}, tags = ov.tags || {}, names = ov.names || {};
    const W = model.width || 2384, Hh = model.height || 1684;
    const out = { width: W, height: Hh, title: model.drawing_no || "", pipes: [], signals: [], equipment: [], instruments: [], valves: [], connectors: [], labels: [] };
    // 배관 — 런(가로·세로 선분) · 서비스는 그 런에 가장 가까운 라인 깃발 또는 그 런을 탭한 계기의 라인
    const lineOfRun = new Map();
    for (const lb of model.line_labels || []) if (lb.rect) lineOfRun.set("label:" + key(lb.rect), lb.line_no);
    const instLines = (model.instruments || []).filter((i) => i.line_no);
    const nearestLine = (seg) => {
      const mx = (seg[0] + seg[2]) / 2, my = (seg[1] + seg[3]) / 2; let best = null, bd = Infinity;
      for (const lb of model.line_labels || []) { if (!lb.rect) continue; const d = Math.hypot((lb.rect[0] + lb.rect[2]) / 2 - mx, (lb.rect[1] + lb.rect[3]) / 2 - my); if (d < bd) { bd = d; best = lb.line_no; } }
      if (best && bd < 400) return best;
      bd = Infinity;
      for (const i of instLines) { const d = Math.hypot((i.rect[0] + i.rect[2]) / 2 - mx, (i.rect[1] + i.rect[3]) / 2 - my); if (d < bd) { bd = d; best = i.line_no; } }
      return bd < 400 ? best : "";
    };
    const conns = model.connectors || [];
    // 라인 깃발도 계기 라인도 없는 런은 **그 장의 도면번호 계통 코드**(`D00P-10LBA10-M05-0001` → LBA)로 — 장의 주 계통이다
    const sheetSys = (String(model.drawing_no || "").toUpperCase().match(/-\d{2}([A-Z]{3})\d{2}-/) || [])[1] || "";
    (model.pipes || []).forEach((p, n) => {
      const s = p.seg; const ln = nearestLine(s);
      // 흐름: 런 끝 25pt 안에 TO 커넥터 → 그 끝으로 흐른다 · FROM → 그 끝에서 들어온다
      let flow = "none"; let a = [s[0], s[1]], b = [s[2], s[3]];
      for (const c of conns) {
        const dA = Math.hypot(c.at[0] - a[0], c.at[1] - a[1]), dB = Math.hypot(c.at[0] - b[0], c.at[1] - b[1]);
        if (Math.min(dA, dB) > 40) continue;
        const atB = dB <= dA;
        if (c.dir === "TO") flow = atB ? "fwd" : "rev"; else if (c.dir === "FROM") flow = atB ? "rev" : "fwd";
      }
      out.pipes.push({ id: `pipe${n}`, service: serviceOf(ln || (sheetSys ? "00" + sheetSys : "")), points: [a, b], flow, role: p.role, width: p.role === "line" ? 6 : p.role === "tap" ? 5 : 4, label: ln && p.role === "line" ? ln : "" });
    });
    // 기기 — 라벨 자리(글자 상자)에 심볼을 세운다 (실제 기기 크기가 아니다 — 모델 메모에 적는다)
    (model.equipment || []).forEach((e, n) => {
      const r = e.rect; const name = names[e.name] || e.name;
      const w = Math.max(70, Math.min(140, (r[2] - r[0]) * 1.1)), h = Math.max(50, Math.min(100, w * 0.7));
      out.equipment.push({ id: `eq${n}`, kind: S.kindForName(e.noun || e.name), x: (r[0] + r[2]) / 2 - w / 2, y: r[1] - h - 6, w, h, name, origName: e.name, noun: e.noun || "" });
    });
    // 계기 — 버블 사각형 그대로
    (model.instruments || []).forEach((i) => {
      const r = i.rect, rad = Math.max(8, Math.min(r[2] - r[0], r[3] - r[1]) / 2);
      const tag = tags[i.key] !== undefined ? tags[i.key] : i.tag;
      out.instruments.push({ id: i.key, key: i.key, tag, fn: i.type, x: (r[0] + r[2]) / 2 - rad, y: (r[1] + r[3]) / 2 - rad, r: rad, loc: i.lines || 0,
                             vendor: /^VENDOR/i.test(i.scope || ""), scope: i.scope, lineNo: i.line_no, lineSize: i.line_size, equip: i.equip, review: i.review,
                             unit: unitFor(i.type), face: "above" });
    });
    placeFaces(out.instruments);
    // 밸브 — 몸체 사각형 · 태그 버블 자리
    (model.valves || []).forEach((v) => {
      const r = v.rect, size = Math.max(16, Math.min(40, Math.max(r[2] - r[0], r[3] - r[1]) * 1.3));
      const tag = tags[v.key] !== undefined ? tags[v.key] : v.tag;
      const vertical = (r[3] - r[1]) > (r[2] - r[0]) * 1.3;
      out.valves.push({ id: v.key, key: v.key, tag, kind: S.kindForValve(v.body, v.actuator), x: (r[0] + r[2]) / 2 - size / 2, y: (r[1] + r[3]) / 2 - size / 2, size, rot: vertical ? 90 : 0,
                        state: /OPEN/i.test(v.state) ? "open" : /CLOS/i.test(v.state) ? "closed" : "", body: v.body, actuator: v.actuator, scope: v.scope, tab: v.tab });
    });
    conns.forEach((c, n) => out.connectors.push({ id: `conn${n}`, text: `${c.dir === "TO" ? "To" : c.dir === "FROM" ? "From" : ""} ${c.name}`.trim(), x: c.at[0], y: c.at[1], dir: c.dir === "TO" ? "out" : "in", side: c.at[0] > W / 2 ? "left" : "right" }));
    (model.line_labels || []).forEach((lb) => { if (lb.rect) out.labels.push({ text: `${lb.line_no} ${lb.size || ""}`.trim(), x: lb.rect[0], y: lb.rect[1] - 3, size: 10 }); });
    // 보이는 창 — 식별된 것 둘레(여백 80pt).  A1 도면 전체를 보이면 버블이 너무 작다.  좌표는 그대로다.
    const xs = [], ys = [];
    for (const p of out.pipes) for (const q of p.points) { xs.push(q[0]); ys.push(q[1]); }
    for (const i of out.instruments) { xs.push(i.x - 40, i.x + i.r * 2 + 40); ys.push(i.y - 40, i.y + i.r * 2 + 10); }
    for (const v of out.valves) { xs.push(v.x, v.x + v.size); ys.push(v.y - 12, v.y + v.size); }
    for (const e of out.equipment) { xs.push(e.x, e.x + e.w); ys.push(e.y - 24, e.y + e.h + 30); }
    for (const c of out.connectors) { xs.push(c.x - 120, c.x + 120); ys.push(c.y - 12, c.y + 12); }
    if (xs.length) {
      const x0 = Math.max(0, Math.min(...xs) - 80), y0 = Math.max(0, Math.min(...ys) - 80);
      out.view = [x0, y0, Math.min(W, Math.max(...xs) + 80) - x0, Math.min(Hh, Math.max(...ys) + 80) - y0];
    }
    return out;
  };
  /* 값 칸 자리 — 버블이 붙어 있으면(LS 묶음 · 나란한 계기) 칸이 서로 덮는다.  위 → 아래 → 오른쪽 → 왼쪽 순으로 비는 자리를 고르고,
   * 다 덮이면 위에 둔다 (자리는 P&ID 가 정한 것이라 그 이상 옮기지 않는다).  칸 크기는 hmi-core 의 _inst 와 같은 식. */
  function placeFaces(list) {
    const placed = [];
    const box = (i, side) => {
      const r = i.r, fw = Math.max(56, String(i.tag || "").length * 6.2 + 14), fh = 28;
      let fx = -fw / 2 + r, fy = -fh - 6;
      if (side === "below") fy = r * 2 + 6; else if (side === "left") { fx = -fw - 8; fy = r - fh / 2; } else if (side === "right") { fx = r * 2 + 8; fy = r - fh / 2; }
      return [i.x + fx, i.y + fy, i.x + fx + fw, i.y + fy + fh];
    };
    const hit = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
    for (const i of list.slice().sort((a, b) => a.y - b.y || a.x - b.x)) {
      const bubbles = list.filter((o) => o !== i).map((o) => [o.x, o.y, o.x + o.r * 2, o.y + o.r * 2]);
      let chosen = "above";
      for (const side of ["above", "below", "right", "left"]) {
        const b = box(i, side);
        if (!placed.some((q) => hit(q, b)) && !bubbles.some((q) => hit(q, b))) { chosen = side; break; }
      }
      i.face = chosen; placed.push(box(i, chosen));
    }
  }
  function unitFor(type) { const t = String(type || "").toUpperCase(); return t.startsWith("PD") ? "mbar" : t.startsWith("P") ? "barg" : t.startsWith("T") ? "°C" : t.startsWith("L") ? "%" : t.startsWith("F") ? "t/h" : t.startsWith("A") ? "ppm" : t.startsWith("Z") ? "%" : t.startsWith("S") ? "rpm" : ""; }
})();
