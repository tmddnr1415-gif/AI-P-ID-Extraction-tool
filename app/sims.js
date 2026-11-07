/* Item별 시뮬레이션 — 개념 모델. 설정값은 예시이며 프로젝트 Spec 대조 전까지 미확인. */
(function (G) {
  "use strict";
  const SIM = (id, sim) => { G.V3D.MODELS[id].sim = sim; };
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const follow = (cur, tgt, tau, dt) => cur + (tgt - cur) * (1 - Math.exp(-dt / Math.max(1e-3, tau)));
  const ramp = (cur, tgt, rate, dt) => cur + clamp(tgt - cur, -rate * dt, rate * dt);
  const D2R = Math.PI / 180;
  const G_ = [46, 190, 110], R_ = [235, 60, 50], O_ = [255, 150, 30], B_ = [60, 130, 255];
  function panel(ctx, x, y, w, h, cs) { ctx.fillStyle = cs.getPropertyValue("--card").trim() || "#fff"; ctx.globalAlpha = 0.92; ctx.beginPath(); if (ctx.roundRect) ctx.roundRect(x, y, w, h, 8); else ctx.rect(x, y, w, h); ctx.fill(); ctx.globalAlpha = 1; ctx.strokeStyle = cs.getPropertyValue("--line").trim() || "#ddd"; ctx.lineWidth = 1; ctx.stroke(); }
  function txt(ctx, s, x, y, cs, o = {}) { ctx.font = `${o.b ? "700 " : ""}${o.size || 11.5}px "Malgun Gothic",system-ui,sans-serif`; ctx.fillStyle = o.col || cs.getPropertyValue("--text").trim() || "#222"; ctx.textAlign = o.al || "left"; ctx.fillText(s, x, y); }
  function hbar(ctx, x, y, w, h, frac, col, cs, marks = []) { ctx.fillStyle = cs.getPropertyValue("--line").trim() || "#ddd"; ctx.fillRect(x, y, w, h); ctx.fillStyle = col; ctx.fillRect(x, y, w * clamp(frac, 0, 1), h); for (const [f, c] of marks) { ctx.fillStyle = c; ctx.fillRect(x + w * f - 1, y - 3, 2, h + 6); } }
  const mA = (s) => `${s.toFixed(2)} mA`;

  SIM("globe-valve", {
    init: { ma: 12, pos: 50, air: true, ato: true },
    controls: [{ t: "slider", k: "ma", label: "입력 신호", min: 4, max: 20, step: 0.1, unit: "mA" }, { t: "toggle", k: "air", label: "계장 Air 공급" }, { t: "toggle", k: "ato", label: "Air-to-Open(Fail-Close)" }],
    act: { "Step 4↔20 mA": (s) => { s.ma = s.ma > 12 ? 4 : 20; } },
    update(s, dt) { let sp = (s.ma - 4) / 16 * 100; if (!s.ato) sp = 100 - sp; const tgt = s.air ? sp : (s.ato ? 0 : 100); s.pos = follow(s.pos, tgt, 0.55, dt); },
    pose(s) { const y = s.pos / 100 * 12; return { stem: { tr: [0, y, 0] }, trim: { tr: [0, y, 0] }, positioner: s.air ? null : { glow: 0.5, gcol: R_ } }; },
    readout(s) { const sp = s.ato ? (s.ma - 4) / 16 * 100 : 100 - (s.ma - 4) / 16 * 100; return `입력 ${mA(s.ma)} → 설정 ${sp.toFixed(1)}% → 실제 개도 ${s.pos.toFixed(1)}%${s.air ? "" : " · Air 상실 → Fail " + (s.ato ? "Close" : "Open")}`; },
    overlay(ctx, W, H, s, cs) { panel(ctx, 10, 10, 190, 64, cs); txt(ctx, "Positioner 응답", 20, 28, cs, { b: 1 }); txt(ctx, `${mA(s.ma)}  →  ${s.pos.toFixed(1)} % 개도`, 20, 46, cs); hbar(ctx, 20, 56, 170, 8, s.pos / 100, "#2a78d6", cs); },
  });

  SIM("butterfly-valve", {
    init: { ma: 4, ang: 0, air: true },
    controls: [{ t: "slider", k: "ma", label: "입력 신호", min: 4, max: 20, step: 0.1, unit: "mA" }, { t: "toggle", k: "air", label: "계장 Air 공급" }],
    update(s, dt) { const tgt = s.air ? (s.ma - 4) / 16 * 90 : 0; s.ang = ramp(s.ang, tgt, 45, dt); },
    pose(s) { const a = (35 - s.ang) * D2R; return { disc: { rot: [[0, 1, 0], [0, 0, 0], a] }, shaft: { rot: [[0, 1, 0], [0, 0, 0], a] } }; },
    readout(s) { return `입력 ${mA(s.ma)} → Disc 각도 ${s.ang.toFixed(1)}° (0°=닫힘, 90°=완전 개방)${s.air ? "" : " · Air 상실 → Fail Close"} · 제어 사용 각도 범위는 프로젝트·제조사 기준 확인(미확인)`; },
    overlay(ctx, W, H, s, cs) { panel(ctx, 10, 10, 170, 62, cs); txt(ctx, "Disc 개도", 20, 28, cs, { b: 1 }); txt(ctx, `${s.ang.toFixed(1)}° / 90°`, 20, 46, cs); hbar(ctx, 20, 54, 150, 8, s.ang / 90, "#2a78d6", cs); },
  });

  SIM("ball-valve", {
    init: { pos: 1, tgt: 1, st: 6, sov: true, el: 0, msg: "정상 운전 · 완전 개방", pst: 0 },
    controls: [{ t: "slider", k: "st", label: "Stroke time 설정", min: 1, max: 20, step: 0.5, unit: "s" }],
    act: {
      "ESD Trip(SOV 차단)": (s) => { s.sov = false; s.tgt = 0; s.el = 0; s.msg = "ESD Trip → SOV de-energize → 스프링 복귀로 닫히는 중"; s.pst = 0; s.done0 = 0; },
      "Reset(개방)": (s) => { s.sov = true; s.tgt = 1; s.el = 0; s.msg = "Reset → SOV energize → 공압으로 개방 중"; s.pst = 0; },
      "PST 10%": (s) => { if (s.pos > 0.95 && s.sov) { s.pst = 1; s.tgt = 0.9; s.el = 0; s.msg = "Partial Stroke Test 진행(10% 이동 후 복귀)"; } },
    },
    update(s, dt) {
      s.el += dt; const rate = 1 / s.st; s.pos = ramp(s.pos, s.tgt, s.pst ? rate * 0.6 : rate, dt);
      if (s.pst === 1 && Math.abs(s.pos - 0.9) < 0.005) { s.pst = 2; s.tgt = 1; }
      if (s.pst === 2 && s.pos > 0.999) { s.pst = 0; s.msg = `PST 완료 · ${s.el.toFixed(1)} s · 고착 없음(시뮬레이션)`; }
      if (!s.pst && s.tgt === 0 && s.pos <= 0.001 && !s.done0) { s.done0 = 1; s.msg = `완전 닫힘(ZSC) · 실측 ${s.el.toFixed(1)} s / 설정 ${s.st} s`; }
      if (s.tgt === 1 && s.pos > 0.999 && /개방 중/.test(s.msg)) s.msg = `완전 개방(ZSO) · ${s.el.toFixed(1)} s`;
    },
    pose(s) { const a = (1 - s.pos) * 90 * D2R; const open = s.pos > 0.98, closed = s.pos < 0.02;
      return { ball: { rot: [[0, 1, 0], [0, 0, 0], a] }, stem: { rot: [[0, 1, 0], [0, 0, 0], a] }, "limit-switch": { glow: 0.55, gcol: open ? G_ : closed ? R_ : O_ }, solenoid: { glow: 0.5, gcol: s.sov ? G_ : R_ }, pst: s.pst ? { glow: 0.6, gcol: B_ } : null }; },
    readout(s) { return `${s.msg} · 개도 ${(s.pos * 100).toFixed(0)}% · SOV ${s.sov ? "통전" : "차단"} · ZSO ${s.pos > 0.98 ? "ON" : "OFF"} / ZSC ${s.pos < 0.02 ? "ON" : "OFF"} · 투시(X-ray)로 Ball 회전 확인`; },
    overlay(ctx, W, H, s, cs) { panel(ctx, 10, 10, 200, 70, cs); txt(ctx, "ESDV 상태", 20, 28, cs, { b: 1 }); txt(ctx, `개도 ${(s.pos * 100).toFixed(0)}%   경과 ${s.el.toFixed(1)} s`, 20, 46, cs); hbar(ctx, 20, 56, 180, 8, s.pos, s.sov ? "#1baf7a" : "#eb6834", cs, [[0.9, "#888"]]); },
  });

  SIM("psv", {
    init: { p: 8, set: 10, lift: 0, open: false, lever: false },
    controls: [{ t: "slider", k: "p", label: "입구 압력", min: 0, max: 13, step: 0.05, unit: "barg" }, { t: "slider", k: "set", label: "Set pressure", min: 5, max: 12, step: 0.5, unit: "barg" }, { t: "toggle", k: "lever", label: "Lifting lever" }],
    act: { "압력 상승(Blocked outlet)": (s) => { s.p = s.set * 1.1; }, "정상 운전 복귀": (s) => { s.p = s.set * 0.8; } },
    update(s, dt) { if (!s.open && s.p >= s.set) s.open = true; if (s.open && s.p < s.set * 0.93) s.open = false; const tgt = s.lever ? 0.35 : s.open ? clamp(0.25 + (s.p - s.set) / (0.1 * s.set) * 0.75, 0.25, 1) : 0; s.lift = follow(s.lift, tgt, 0.08, dt); },
    pose(s, t) { const y = s.lift * 6, f = (44 - y) / 44; const flow = s.lift > 0.05;
      return { disc: { tr: [0, y, 0] }, stem: { tr: [0, y, 0] }, spring: { sc: [[0, 75, 0], [1, f, 1]] }, nozzle: flow ? { glow: 0.4 + 0.3 * Math.sin(t * 12), gcol: O_ } : null, body: flow ? { glow: 0.12, gcol: O_ } : null }; },
    readout(s) { return `입구 ${s.p.toFixed(2)} barg / Set ${s.set} barg (${(s.p / s.set * 100).toFixed(0)}%) → ${s.lift > 0.05 ? `개방, Lift ${(s.lift * 100).toFixed(0)}%` : "닫힘"} · 예시: 10% 과압 Full lift, 7% Blowdown 재착좌(미확인) · 초안, 담당자 확인 필수`; },
    overlay(ctx, W, H, s, cs) { panel(ctx, 10, 10, 200, 72, cs); txt(ctx, "PSV 동작", 20, 28, cs, { b: 1 }); txt(ctx, `${s.p.toFixed(2)} barg · Lift ${(s.lift * 100).toFixed(0)}%`, 20, 46, cs); hbar(ctx, 20, 58, 180, 8, s.p / 13, s.p >= s.set ? "#eb6834" : "#2a78d6", cs, [[s.set / 13, "#c00"], [s.set * 0.93 / 13, "#888"]]); },
  });

  SIM("field-gauge", {
    init: { p: 40, puls: false, snub: false },
    controls: [{ t: "slider", k: "p", label: "공정 압력", min: 0, max: 100, step: 0.5, unit: "% Range" }, { t: "toggle", k: "puls", label: "맥동(펌프 토출)" }, { t: "toggle", k: "snub", label: "Snubber 설치" }],
    update(s, dt, t) { const amp = s.puls ? (s.snub ? 1.5 : 12) : 0; const v = clamp(s.p + amp * Math.sin(t * 17), 0, 100); s.v = follow(s.v == null ? v : s.v, v, s.snub ? 0.25 : 0.03, dt); },
    pose(s) { const a = (225 - 270 * (s.v == null ? s.p : s.v) / 100 - 120) * D2R; return { needle: { rot: [[0, 0, 1], [0, 0, 0], a] } }; },
    readout(s) { return `압력 ${(s.v == null ? s.p : s.v).toFixed(1)} % of Range${s.puls ? (s.snub ? " · Snubber 로 맥동 감쇠" : " · 맥동으로 지침 떨림 → Snubber/액체 충전 검토") : ""} · 정상 운전값의 Range 내 위치는 프로젝트 기준 확인(미확인)`; },
  });

  SIM("transmitter", {
    init: { dp: 50, sqrt: false, fail: "", eq: false, out: 12 },
    controls: [{ t: "slider", k: "dp", label: "차압(DP)", min: -5, max: 110, step: 0.5, unit: "% URV" }, { t: "toggle", k: "sqrt", label: "Square-root 출력(유량)" }, { t: "toggle", k: "eq", label: "Manifold Equalize" }],
    act: { "센서 고장(Downscale)": (s) => { s.fail = "lo"; }, "센서 고장(Upscale)": (s) => { s.fail = "hi"; }, "고장 해제": (s) => { s.fail = ""; } },
    update(s, dt) { const pv = s.eq ? 0 : s.dp; let f = clamp(pv / 100, -0.0125, 1.0375); if (s.sqrt) f = f > 0 ? Math.sqrt(f) : 0; let o = clamp(4 + 16 * f, 3.8, 20.5); if (s.fail === "lo") o = 3.6; if (s.fail === "hi") o = 21; s.out = follow(s.out, o, 0.2, dt); },
    pose(s) { return { display: { glow: 0.5, gcol: s.fail ? R_ : [120, 200, 255] }, manifold: s.eq ? { glow: 0.35, gcol: O_ } : null, sensor: s.fail ? { glow: 0.5, gcol: R_ } : null }; },
    readout(s) { return `DP ${s.eq ? 0 : s.dp}% → 출력 ${mA(s.out)}${s.sqrt ? " (√ 추출)" : ""}${s.fail ? " · 고장 신호(NAMUR NE 43 계열 ≤3.6 / ≥21 mA, 일반 지식·미확인)" : ""}`; },
    overlay(ctx, W, H, s, cs) { panel(ctx, 10, 10, 170, 66, cs); txt(ctx, "LCD", 20, 28, cs, { b: 1 }); txt(ctx, mA(s.out), 20, 52, cs, { b: 1, size: 20, col: s.fail ? "#d03b2f" : "#2a78d6" }); txt(ctx, `${((s.out - 4) / 16 * 100).toFixed(1)} %`, 170, 52, cs, { al: "right" }); hbar(ctx, 20, 62, 150, 5, (s.out - 4) / 16, "#2a78d6", cs); },
  });

  const head = (q) => clamp(1.18 - 0.42 * Math.pow(q / 100, 2), 0.2, 1.2);
  const surgeQ = (h) => 38 + 22 * (h - 0.8) / 0.4;
  SIM("ccs", {
    init: { dem: 85, asc: true, asv: 0, q: 85, h: 0.9, surge: 0, trail: [], qs: 40, qcl: 44 },
    controls: [{ t: "slider", k: "dem", label: "공정 유량 수요", min: 20, max: 110, step: 1, unit: "%" }, { t: "toggle", k: "asc", label: "Anti-surge 제어 ON" }],
    act: { "Surge 발생(하류 차단)": (s) => { s.dem = 30; }, "정상 부하 복귀": (s) => { s.dem = 85; } },
    update(s, dt, t) {
      const qc = s.dem + s.asv * 70; s.h = follow(s.h, head(qc), 0.4, dt);
      s.qs = surgeQ(s.h); s.qcl = s.qs * 1.1;
      if (s.asc) { const err = s.qcl - qc; s.asv = clamp(s.asv + (err > 0 ? err * 0.24 : err * 0.04) * dt, 0, 1); } else s.asv = ramp(s.asv, 0, 0.3, dt);
      s.surge = qc < s.qs ? Math.min(1, s.surge + dt * 2) : Math.max(0, s.surge - dt);
      s.q = follow(s.q, qc + (s.surge > 0.3 ? 25 * Math.sin(t * 6) * s.surge : 0), 0.15, dt);
      if (!s.tt || t - s.tt > 0.1 || t < s.tt) { s.tt = t; s.trail.push([s.q, s.h]); if (s.trail.length > 60) s.trail.shift(); }
    },
    pose(s, t) { const fl = s.surge > 0.3 ? 0.5 + 0.5 * Math.sin(t * 12) : 0;
      return { asv: { glow: s.asv * 0.7, gcol: O_ }, "recycle-line": { glow: s.asv > 0.02 ? 0.25 + 0.5 * s.asv * (0.6 + 0.4 * Math.sin(t * 8)) : 0, gcol: O_ }, compressor: fl ? { glow: fl * 0.8, gcol: R_ } : null, controller: s.asv > 0.02 ? { glow: 0.25, gcol: B_ } : null, "flow-element": { glow: 0.25, gcol: s.q < s.qcl ? O_ : G_ }, signal: s.asv > 0.02 ? { glow: 0.5, gcol: B_ } : null }; },
    readout(s) { return `${s.surge > 0.3 ? "⚠ SURGE 발생! " : s.q < s.qcl * 1.02 ? "Surge 제어선 접근 → ASV 개방 " : "정상 영역 "}· 압축기 유량 ${s.q.toFixed(0)}% (Surge선 ${s.qs.toFixed(0)}%, 제어선 ${s.qcl.toFixed(0)}%) · ASV 개도 ${(s.asv * 100).toFixed(0)}% · 제어 ${s.asc ? "ON" : "OFF"} (제어선 여유 10%는 예시·미확인)`; },
    overlay(ctx, W, H, s, cs) {
      const x0 = 12, y0 = 10, w = 220, h = 150; panel(ctx, x0, y0, w, h, cs); txt(ctx, "Compressor Map (개념)", x0 + 10, y0 + 18, cs, { b: 1 });
      const px = (q) => x0 + 30 + (q - 20) / 100 * (w - 44), py = (hh) => y0 + h - 22 - (hh - 0.3) / 0.95 * (h - 48);
      const mute = cs.getPropertyValue("--sub").trim() || "#888"; ctx.strokeStyle = mute; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(px(20), py(0.3)); ctx.lineTo(px(120), py(0.3)); ctx.moveTo(px(20), py(0.3)); ctx.lineTo(px(20), py(1.25)); ctx.stroke();
      txt(ctx, "Flow →", px(120), py(0.3) + 14, cs, { al: "right", size: 10, col: mute }); txt(ctx, "Head", x0 + 6, y0 + 34, cs, { size: 10, col: mute });
      ctx.strokeStyle = "#999"; ctx.beginPath(); for (let q = 20; q <= 120; q += 4) { const hh = head(q); q === 20 ? ctx.moveTo(px(q), py(hh)) : ctx.lineTo(px(q), py(hh)); } ctx.stroke();
      const line = (f, col, dash) => { ctx.strokeStyle = col; ctx.lineWidth = 1.6; ctx.setLineDash(dash); ctx.beginPath(); let first = true; for (let hh = 0.45; hh <= 1.2; hh += 0.05) { const q = f(hh); first ? ctx.moveTo(px(q), py(hh)) : ctx.lineTo(px(q), py(hh)); first = false; } ctx.stroke(); ctx.setLineDash([]); };
      line(surgeQ, "#d03b2f", []); line((hh) => surgeQ(hh) * 1.1, "#eb6834", [4, 3]);
      txt(ctx, "Surge", px(24), py(1.22), cs, { size: 10, col: "#d03b2f" }); txt(ctx, "Control", px(56), py(1.22), cs, { size: 10, col: "#eb6834" });
      ctx.fillStyle = "rgba(42,120,214,.35)"; for (const [q, hh] of s.trail) ctx.fillRect(px(clamp(q, 20, 120)) - 1, py(hh) - 1, 2, 2);
      ctx.fillStyle = s.surge > 0.3 ? "#d03b2f" : "#2a78d6"; ctx.beginPath(); ctx.arc(px(clamp(s.q, 20, 120)), py(s.h), 4.5, 0, 7); ctx.fill();
    },
  });

  SIM("mms", {
    init: { vib: 30, alm: 75, trip: 100, rot: 0, rpm: 3600, tripped: false },
    controls: [{ t: "slider", k: "vib", label: "축 진동", min: 0, max: 150, step: 1, unit: "µm pp" }, { t: "slider", k: "alm", label: "Alarm 설정", min: 20, max: 140, step: 5, unit: "µm" }, { t: "slider", k: "trip", label: "Trip 설정", min: 30, max: 150, step: 5, unit: "µm" }],
    act: { "베어링 손상(진동 증가)": (s) => { s.vib = 120; }, "Trip Reset": (s) => { s.tripped = false; s.vib = 30; } },
    update(s, dt) { if (s.vib >= s.trip) s.tripped = true; s.spd = follow(s.spd == null ? s.rpm : s.spd, s.tripped ? 0 : s.rpm, 1.5, dt); s.rot += (s.spd / 60) * 2 * Math.PI * dt * 0.05; },
    pose(s, t) { const amp = (s.spd / s.rpm) * s.vib / 150 * 1.4; const w = amp * Math.sin(t * 40), w2 = amp * Math.cos(t * 40); const lv = s.vib >= s.trip ? R_ : s.vib >= s.alm ? O_ : G_;
      return { shaft: { rot: [[1, 0, 0], [0, 0, 0], s.rot], tr: [0, w, w2] }, probe: { glow: 0.45, gcol: lv }, "monitor-rack": { glow: s.vib >= s.alm ? 0.35 : 0.1, gcol: lv }, keyphasor: Math.cos(s.rot) > 0.96 ? { glow: 0.9, gcol: B_ } : null }; },
    readout(s) { return `진동 ${s.vib} µm pp (Alarm ${s.alm} / Trip ${s.trip}, 예시 설정·미확인) → ${s.tripped ? "TRIP · 기계 정지 중 " + (s.spd || 0).toFixed(0) + " rpm" : s.vib >= s.alm ? "ALARM" : "정상"} · 실제 Trip 은 Voting·Time delay 를 프로젝트 기준으로 확인(초안, 담당자 확인 필수)`; },
    overlay(ctx, W, H, s, cs) { panel(ctx, 10, 10, 200, 66, cs); txt(ctx, "Radial vibration", 20, 28, cs, { b: 1 }); txt(ctx, `${s.vib} µm pp  ${s.tripped ? "TRIP" : s.vib >= s.alm ? "ALARM" : "OK"}`, 20, 46, cs, { col: s.tripped ? "#d03b2f" : s.vib >= s.alm ? "#eb6834" : undefined }); hbar(ctx, 20, 56, 180, 8, s.vib / 150, s.vib >= s.trip ? "#d03b2f" : s.vib >= s.alm ? "#eb6834" : "#1baf7a", cs, [[s.alm / 150, "#eb6834"], [s.trip / 150, "#d03b2f"]]); },
  });

  SIM("fgs", {
    init: { leak: false, fire: false, t: 0, lel: [0, 0, 0, 0], alm: 20, hi: 60 },
    controls: [],
    act: { "가스 누출": (s) => { s.leak = true; s.t = 0; }, "화염 감지": (s) => { s.fire = true; }, "Reset": (s) => { s.leak = false; s.fire = false; s.t = 0; s.lel = [0, 0, 0, 0]; } },
    update(s, dt) { if (s.leak) s.t += dt; const dist = [1.0, 1.6, 2.4, 3.2]; for (let i = 0; i < 4; i++) { const tgt = s.leak ? clamp((s.t - dist[i] * 2) * 14, 0, 90 / dist[i] * 1.4) : 0; s.lel[i] = follow(s.lel[i], Math.min(100, tgt), 0.6, dt); } s.nh = s.lel.filter((v) => v >= s.hi).length; s.na = s.lel.filter((v) => v >= s.alm).length; s.exec = s.nh >= 2 || s.fire; },
    pose(s, t) { const bl = s.exec ? (Math.sin(t * 10) > 0 ? 1 : 0.1) : s.na ? 0.4 : 0;
      return { "gas-detector": { glow: s.nh ? 0.7 : s.na ? 0.45 : 0, gcol: s.nh ? R_ : O_ }, beacon: { glow: bl, gcol: R_ }, "flame-detector": s.fire ? { glow: 0.5 + 0.5 * Math.sin(t * 14), gcol: O_ } : null, "fgs-panel": s.exec ? { glow: 0.35, gcol: R_ } : null, "op-gas": s.leak && s.t > 3 ? { glow: 0.5, gcol: O_ } : null }; },
    readout(s) { return `감지기 %LEL [${s.lel.map((v) => v.toFixed(0)).join(", ")}] · Alarm ${s.alm} / High ${s.hi} %LEL (예시 설정·미확인) · ${s.exec ? "⚠ Voting 충족 → Executive action(ESD 요청·경보)" : s.na ? "1차 경보" : "정상"}${s.fire ? " · 화염 감지" : ""} · 초안, 담당자 확인 필수`; },
    overlay(ctx, W, H, s, cs) { panel(ctx, 10, 10, 180, 92, cs); txt(ctx, "Gas detectors (%LEL)", 20, 28, cs, { b: 1 }); s.lel.forEach((v, i) => { txt(ctx, "GD-" + (i + 1), 20, 46 + i * 14, cs, { size: 10.5 }); hbar(ctx, 62, 39 + i * 14, 115, 7, v / 100, v >= s.hi ? "#d03b2f" : v >= s.alm ? "#eb6834" : "#1baf7a", cs, [[s.alm / 100, "#888"], [s.hi / 100, "#c00"]]); }); },
  });

  SIM("dcs", {
    init: { ma: 12, hi: 10, ph: 0 },
    controls: [{ t: "slider", k: "ma", label: "AI 입력(현장 Transmitter)", min: 3.5, max: 21, step: 0.1, unit: "mA" }, { t: "slider", k: "hi", label: "Range 상한", min: 5, max: 50, step: 1, unit: "barg" }],
    update(s, dt) { s.ph = (s.ph + dt * 1.2) % 1; },
    pose(s) { const seq = ["terminal", "io", "controller", "network", "hmi"]; const k = Math.floor(s.ph * seq.length); const bad = s.ma < 3.8 || s.ma > 20.5; const o = {}; seq.forEach((p, i) => (o[p] = { glow: i === k ? 0.6 : 0, gcol: bad ? R_ : B_ })); return o; },
    readout(s) { const pv = (s.ma - 4) / 16 * s.hi; const bad = s.ma < 3.8 || s.ma > 20.5; return `Terminal → AI 카드 → Controller → Network → HMI · ${mA(s.ma)} → PV ${bad ? "BAD(범위 밖)" : pv.toFixed(2) + " barg"} (0–${s.hi} barg 선형) · BAD 판정 범위는 프로젝트 기준 확인(미확인)`; },
  });

  SIM("ips", {
    init: { a: false, b: false, c: false, byp: false, pb: false, trip: false, n: 0, vote: "2oo3" },
    controls: [{ t: "toggle", k: "a", label: "TX-A Trip" }, { t: "toggle", k: "b", label: "TX-B Trip" }, { t: "toggle", k: "c", label: "TX-C Trip" }, { t: "toggle", k: "byp", label: "TX-A Bypass(MOS)" }],
    act: { "ESD Push button": (s) => { s.pb = true; }, "Reset": (s) => { s.a = s.b = s.c = s.pb = false; s.trip = false; } },
    update(s) { const v = [s.byp ? false : s.a, s.b, s.c]; const n = v.filter(Boolean).length; const need = s.byp ? 1 : 2; s.vote = s.byp ? "1oo2(A Bypass 중, 예시)" : "2oo3"; if (n >= need || s.pb) s.trip = true; s.n = n; },
    pose(s, t) { const f = s.trip ? (Math.sin(t * 9) > 0 ? 0.8 : 0.2) : 0; return { controller: { glow: s.trip ? f : 0.15, gcol: s.trip ? R_ : G_ }, "esd-pb": s.pb ? { glow: f, gcol: R_ } : null, "bypass-panel": s.byp ? { glow: 0.45, gcol: O_ } : null, io: s.n ? { glow: 0.3, gcol: O_ } : null }; },
    readout(s) { return `Voting ${s.vote} · Trip 입력 ${s.n}개${s.pb ? " · ESD PB 눌림" : ""} → ${s.trip ? "⚠ TRIP → Final element 닫힘 명령(De-energize to trip)" : "정상"} · Bypass 중 Voting 변경 방식은 SRS 기준 확인(초안, 담당자 확인 필수)`; },
  });

  SIM("bulk-material", {
    init: { ma: 12, ph: 0 },
    controls: [{ t: "slider", k: "ma", label: "Loop 전류", min: 0, max: 20, step: 0.1, unit: "mA" }],
    act: { "케이블 단선": (s) => { s.ma = 0; }, "정상 복귀": (s) => { s.ma = 12; } },
    update(s, dt) { s.ph = (s.ph + dt * (0.3 + s.ma / 20)) % 1; },
    pose(s, t) { const on = s.ma > 3.5; return { cable: { glow: on ? 0.2 + 0.4 * (0.5 + 0.5 * Math.sin(t * 6 + s.ph * 6)) * (s.ma / 20) : 0.55, gcol: on ? B_ : R_ }, gland: { glow: 0.2, gcol: on ? G_ : R_ }, jb: on ? null : { glow: 0.3, gcol: R_ } }; },
    readout(s) { return s.ma < 3.5 ? "⚠ 루프 단선 → 0 mA · DCS 는 BAD/Open-loop 로 판단 · Gland·JB·Terminal 점검" : `4-20 mA 루프 ${mA(s.ma)} · 250 Ω 수신저항이면 ${(s.ma * 0.25).toFixed(2)} V · JB → Gland → Cable → Tray 경로`; },
  });
})(typeof window !== "undefined" ? window : globalThis);
