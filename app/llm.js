/* LLM 답변 엔진(선택) — ic-expert 챗봇을 이 대시보드의 규칙에 맞춰 붙인 것.
   기본은 기존 로컬 검색형 답변이고, 헤더의 [답변 엔진] 버튼으로 Claude(LLM)로 바꾼다.
   - 근거: 해당 Item 의 Spec for each Item/{Item}/*_Knowledge.md + *_Integration_Spec.md (원문 그대로)
           + ic-expert 지식베이스(국제 코드·아이템별 선정; 출처 링크 포함)
   - 규칙: CLAUDE.md §5 근거 순위·'미확인', ic-concise-answer 형식, ic-safety-gate, ic-anatomy-link part:* 태그
   - API Key 는 이 브라우저(localStorage)에만 저장, 로그·화면에 출력하지 않는다. */
const LLM = (() => {
  "use strict";
  const RAW = /*__RAW__*/null;        // {folder: {knowledge, spec, kfile, sfile}}
  const EXPERT = /*__EXPERT__*/null;  // [{file, title, text}]
  const API = "https://api.anthropic.com/v1/messages";
  const ls = { get: (k, d) => { try { return localStorage.getItem(k) ?? d; } catch (e) { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const on = () => ls.get("ic-llm", "0") === "1" && !!ls.get("ic-llm-key", "");
  function setup() {
    const cur = ls.get("ic-llm", "0") === "1";
    if (cur) { ls.set("ic-llm", "0"); return false; }
    let key = ls.get("ic-llm-key", "");
    if (!key) {
      key = (prompt("Claude(LLM) 답변을 쓰려면 Anthropic API Key 를 입력하세요.\n이 브라우저에만 저장되고, 화면·로그에 표시하지 않습니다.") || "").trim();
      if (!key) return false;
      ls.set("ic-llm-key", key);
    }
    ls.set("ic-llm", "1"); return true;
  }
  function forgetKey() { ls.set("ic-llm-key", ""); ls.set("ic-llm", "0"); }

  /* system = [공통 규칙 + 보조 지식베이스 (모든 Item 공통 → 캐시 공유)] + [Item 에이전트 정체성 + Item 문서] */
  function system(a) {
    const raw = RAW && RAW[a.f];
    const parts = (typeof V3D !== "undefined" && V3D.MODELS[a.id]) ? Object.entries(V3D.MODELS[a.id].parts).map(([k, v]) => `${k} (${v})`).join(", ") : "";
    const common = [
      "당신은 계측제어(I&C) 통합 사양 검토 멀티에이전트의 Item 에이전트입니다. 설계자 질의에 Spec 근거로 간결하게 답합니다. 판정·승인은 항상 사람이 합니다.",
      "",
      "# 규칙 (CLAUDE.md §5)",
      "- 근거 순위: 프로젝트 Spec > 고객·회사 표준 > 국제·업계 표준 > 일반 지식. 충돌은 숨기지 말고 그대로 표시.",
      "- 출처 없는 수치·조항 번호는 만들지 않고 '미확인'으로 쓴다. 수치에는 문서명·Rev·절(또는 지식베이스 출처 URL)을 붙인다.",
      "- Item Spec 은 일반 EPC 기준 초안이므로 프로젝트 Spec 대조 전까지 '미확인' 취급한다.",
      "- 제조사 도면·저작물 복제 금지(수치와 링크만). 재무 정보는 다루지 않는다.",
      "- 안전 계통 Item(IPS, FGS, MMS, ESDV/SDV/BDV, PSV)이면 답변 맨 위에 '초안, 담당자 확인 필수'를 쓰고 확정 표현을 쓰지 않는다.",
      "",
      "# 답변 형식 (ic-concise-answer) — Markdown",
      "1. **결론 1줄**: 질문에 대한 직접 답.",
      "2. **핵심 항목**: 최대 5개, 각 1~2줄, 표·불릿 위주. 서론·사족 금지.",
      "3. **출처·미확인**: 수치마다 문서명·절 또는 출처 링크. 근거 없으면 '미확인'.",
      "4. **후속 제안 1개**.",
      "- 기기 부품과 관련된 항목 끝에는 part:{id} 태그를 붙인다(ic-anatomy-link). 허용 id 는 Item 블록에 있다. 목록에 없으면 붙이지 않는다.",
      "- 한국어로 답하고, 표준명·모델명·용어는 영어 그대로 쓴다.",
    ];
    if (EXPERT && EXPERT.length) {
      common.push("", "# 보조 지식베이스 (ic-expert, 웹 조사·출처 링크 포함. '[general knowledge — verify]' 표시는 미확인)");
      for (const k of EXPERT) common.push(`<kb file="${k.file}">\n${k.text}\n</kb>`);
    }
    const item = [
      `# 이번 질의의 담당: "${a.n}" Item 에이전트 (범위: ${a.sc})${a.s ? " — 안전 계통" : ""}`,
      parts ? `허용 part id: ${parts}` : "이 Item 은 부품 태그를 쓰지 않는다.",
      `## Item 지식 (Spec for each Item/${a.f}/)`,
      raw ? `<knowledge file="${raw.kfile}">\n${raw.knowledge}\n</knowledge>\n<integration_spec file="${raw.sfile}">\n${raw.spec}\n</integration_spec>` : "(없음 — 미확인)",
    ];
    return [
      { type: "text", text: common.join("\n"), cache_control: { type: "ephemeral" } },
      { type: "text", text: item.join("\n"), cache_control: { type: "ephemeral" } },
    ];
  }

  /* 간단·안전한 Markdown → HTML (escape 먼저) */
  function md(src, a) {
    const inline = (t) => {
      let h = esc(t).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
        .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
      // part:* → 기존 태그(클릭 시 Anatomy 점멸 / 실물 3D 강조)
      h = h.replace(/part:([a-z0-9-]+)/g, (m, p) => (typeof V3D !== "undefined" && V3D.MODELS[a.id] && V3D.MODELS[a.id].parts[p])
        ? `<span class="tag" data-i="${a.id}" data-p="${p}" title="${esc(V3D.MODELS[a.id].parts[p])}">part:${p}</span>` : m);
      return h;
    };
    const lines = String(src).split("\n"); const out = []; let i = 0;
    while (i < lines.length) {
      const l = lines[i];
      if (/^\s*\|.*\|\s*$/.test(l) && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
        const row = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
        const hd = row(l); i += 2; const body = [];
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) body.push(row(lines[i++]));
        out.push(`<table class="mt"><tr>${hd.map((c) => `<th>${inline(c)}</th>`).join("")}</tr>${body.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</table>`);
        continue;
      }
      let m;
      if ((m = /^#{1,4}\s+(.*)$/.exec(l))) { out.push(`<div class="sec">${inline(m[1])}</div>`); i++; continue; }
      if (/^\s*([-*]|\d+[.)])\s+/.test(l)) {
        const ol = /^\s*\d/.test(l); const items = [];
        while (i < lines.length && /^\s*([-*]|\d+[.)])\s+/.test(lines[i])) items.push(`<li>${inline(lines[i++].replace(/^\s*([-*]|\d+[.)])\s+/, ""))}</li>`);
        out.push(ol ? `<ol class="pts">${items.join("")}</ol>` : `<ul class="pts">${items.join("")}</ul>`); continue;
      }
      if (!l.trim()) { i++; continue; }
      out.push(`<p>${inline(l)}</p>`); i++;
    }
    return out.join("");
  }

  function shell(a, via) {
    return `<div class="who">${esc(a.n)} 에이전트 · Claude(LLM)${via ? " · 오케스트레이터 경유" : ""}</div>${a.s ? '<span class="gate">⚠ 초안, 담당자 확인 필수 — 확정 판단은 담당 엔지니어·SIS 담당자가 합니다</span>' : ""}<div class="llm-body"><p class="src">근거 문서를 읽는 중…</p></div>`;
  }

  /* el(.llm-body)에 스트리밍으로 답을 채운다. onDone(text) */
  async function answer(a, q, el, onDone) {
    const key = ls.get("ic-llm-key", ""); const model = ls.get("ic-llm-model", "claude-opus-5-5");
    const body = {
      model, max_tokens: 8000, stream: true, thinking: { type: "adaptive" }, output_config: { effort: "medium" },
      system: system(a),
      fallbacks: "default",
      messages: [{ role: "user", content: q }],
    };
    let text = "";
    try {
      const res = await fetch(API, { method: "POST", credentials: "omit", headers: {
        "content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01",
        "anthropic-beta": "server-side-fallback-2026-07-01", "anthropic-dangerous-direct-browser-access": "true" }, body: JSON.stringify(body) });
      if (!res.ok) {
        let msg = ""; try { const j = await res.json(); msg = j?.error?.message || ""; } catch (e) {}
        throw new Error(`HTTP ${res.status}${msg ? " — " + msg : ""}${res.status === 401 ? " (API Key 확인)" : ""}`);
      }
      const rd = res.body.getReader(); const dec = new TextDecoder(); let buf = ""; const tb = new Set(); let stop = null;
      for (;;) {
        const { done, value } = await rd.read(); if (done) break;
        buf += dec.decode(value, { stream: true }); let k;
        while ((k = buf.indexOf("\n\n")) >= 0) {
          const line = buf.slice(0, k).split("\n").find((x) => x.startsWith("data:")); buf = buf.slice(k + 2);
          if (!line) continue; let ev; try { ev = JSON.parse(line.slice(5)); } catch (e) { continue; }
          if (ev.type === "message_start") { text = ""; tb.clear(); }
          else if (ev.type === "content_block_start" && ev.content_block?.type === "text") tb.add(ev.index);
          else if (ev.type === "content_block_delta" && ev.delta?.type === "text_delta" && tb.has(ev.index)) { text += ev.delta.text; el.innerHTML = md(text, a); }
          else if (ev.type === "message_delta" && ev.delta?.stop_reason) stop = ev.delta.stop_reason;
          else if (ev.type === "error") throw new Error(ev.error?.message || "스트리밍 오류");
        }
      }
      if (stop === "refusal") throw new Error("모델이 답변을 거절했습니다(refusal).");
      el.innerHTML = md(text || "_(빈 응답)_", a) + `<div class="src" style="margin-top:6px">근거: ${esc(RAW?.[a.f]?.kfile || "-")} · ${esc(RAW?.[a.f]?.sfile || "-")}${EXPERT?.length ? " · ic-expert 지식베이스" : ""} — 수치·조항은 프로젝트 Spec·Datasheet 원본과 사람이 대조·승인해야 합니다.</div>`;
    } catch (e) {
      el.innerHTML = `<p class="src" style="color:var(--warn)">LLM 답변 실패: ${esc(e.message)} → 로컬 검색형 답변으로 바꾸려면 [답변 엔진] 버튼을 누르세요.</p>`;
    }
    onDone && onDone(text);
  }

  return { on, setup, forgetKey, answer, shell, md };
})();
