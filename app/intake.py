"""새 프로젝트 점검표 — 이 문서가 무엇을 주었고, 무엇을 빌렸고, 무엇을 사람이 답해야 하나 (hotfix81).

새 PDF/DXF 가 올 때마다 "벽" 은 같은 자리에서 나왔다 (CLAUDE.md §9 · roadmap §4):
타이틀블록 칸 · 도면번호 형식 · 범례 유도 실패 · 승수표 없음 · 별표 정의줄 없음 · 획 글자 ·
증거 등급.  그리고 그 사실은 분석이 끝난 결과 json 에 **전부 이미 적혀 있었다** —
`applied_rules.layout` · `legend` · `legend_profile` · `borrowed` · `multipliers` · `unit_notes` ·
`evidence_tier` · `tag_grammar` · `valve_layout` · 행의 검토 사유.  없던 것은 그것을 한 장으로
모아 **사람이 다음에 무엇을 하면 되는지**로 바꿔 말하는 자리였다 (§9 3③ — 스물네 번째).

이 모듈은 **판정하지 않는다.**  저장된 사실을 읽어 규칙 가족별로 `유도 / 폴백 / 사람 몫` 으로
가르고, 사람 몫마다 **어느 판에서 답하는지**를 적는다.  엔진 모듈을 import 하지 않는다 —
결과 json(회귀 하네스의 blob)으로도, DB 의 분석으로도 같은 함수가 같은 점검표를 낸다.

상태 셋:
  ok    — 도면이 답했다 (유도 · 범례 · 실측)
  warn  — 대신한 값으로 돌았다 (설정 폴백 · 남의 프로필) — 틀린 것은 아니지만 이 도면의 값이 아니다
  todo  — 사람이 답해야 한다 (판 이름과 함께)
"""
from __future__ import annotations

import collections
from typing import Iterable

# 검토 사유 중 "사람이 답할 자리가 이미 있는" 것 → (판 이름 · 한 줄).  `REVIEW_LABELS` 는 main.py 의
# 것이고 여기서는 **자리**만 말한다 (라벨은 호출자가 넘긴다 · 없으면 코드 그대로).
WHERE = {
    "MULTIPLIER_UNDEFINED": ("수량 승수 판", "유닛코드의 승수를 지정하면 다음 분석부터 Q'ty 가 찬다"),
    "MULTIPLIER_FROM_CONFIG": ("수량 승수 판", "지금 값은 설정 폴백(남의 도면 값)이다 — 유닛코드마다 확인·지정"),
    "MULTIPLIER_DEFAULT_ONE": ("수량 승수 판", "범례·NOTES 가 답하지 않아 x1 로 뒀다 — 유닛코드마다 확인"),
    "MULTIPLIER_NOTE_RANGE": ("수량 승수 판", "NOTES 가 범위(THRU)로만 말해 세지 않았다"),
    "MULTIPLIER_BY_USER": ("수량 승수 판", "사람이 지정한 값으로 돌았다 (감사용 — 할 일 아님)"),
    "DRAWING_NO_BY_USER": ("장 도면번호 판", "사람이 적은 도면번호로 읽은 장 (감사용 — 할 일 아님)"),
    "VENDOR_MARK_UNDEFINED": ("근거 패널 · SCOPE 칸", "별표가 있는데 그 장 NOTES 가 뜻을 정하지 않는다 — 공급 주체를 사람이 가른다"),
    "BUBBLE_DASHED": ("근거 패널 · SCOPE 칸", "파선으로 그린 버블 — 범례가 뜻을 정하지 않아 별표·NOTES 대로 두었다"),
    "TAGGED_VALVE_NO_ACTUATOR": ("목록 · 탭", "태그는 있는데 액추에이터가 없는 밸브 — 어느 산출물 탭인지 도면이 말하지 않는다"),
    "VALVE_TAG_NO_BODY": ("목록 · 근거 패널", "태그 버블은 있는데 몸체를 못 찾았다 — 몸체·액추에이터 칸이 비어 있다"),
    "TAG_TYPE_MISMATCH": ("근거 패널", "태그 기능코드와 버블 글자가 다르다 — 도면이 두 말을 한다"),
    "TAG_EVIDENCE_ROW": ("근거 패널 · SCOPE 칸", "태그만이 증거인 행 — 공급 주체 미판정"),
    "SCOPE_OVERRIDE_UNRESOLVED": ("근거 패널", "PLANT COMMON 같은 범위 문구가 있다 — 어느 항목이 해당하는지 사람이 가른다"),
    "UNKNOWN_SYMBOL": ("미지정 심볼 등록 화면", "범례에 없는 심볼 — 사람이 정한다"),
    "TYPICAL_AMBIGUOUS": ("근거 패널", "같은 표식의 Typical 상세가 둘 이상 — 어느 것인지 도면이 말하지 않는다"),
    "TYPICAL_POINT_UNLABELLED": ("근거 패널 · Q'ty", "Typical 표식 아래 이름표를 못 읽은 행"),
}

STATUS_ORDER = {"todo": 0, "warn": 1, "ok": 2, "info": 3}


def _n(x, default=0):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def _codes(row: dict) -> list:
    ev = row.get("evidence") or {}
    if isinstance(ev, str):
        return []
    return list(ev.get("review_codes") or [])


def _values(row: dict) -> dict:
    v = row.get("values")
    if isinstance(v, dict):
        return v
    # 회귀 blob 의 행은 평평하다 (Row dataclass 그대로)
    return row


def _sec(key, title, status, lines, todo=None, facts=None):
    return {"key": key, "title": title, "status": status,
            "lines": [str(x) for x in lines if x], "todo": list(todo or []),
            "facts": facts or {}}


def _worst(*statuses):
    return min(statuses, key=lambda s: STATUS_ORDER.get(s, 9)) if statuses else "ok"


# --------------------------------------------------------------------------
# 섹션
# --------------------------------------------------------------------------

def _input(engine, pages, job) -> dict:
    kinds = collections.Counter(str(p.get("page_kind") or "") for p in pages)
    sizes = collections.Counter(
        f"{round(float(p.get('width') or 0))}x{round(float(p.get('height') or 0))}" for p in pages
        if p.get("width") and p.get("height"))
    lay = ((engine.get("applied_rules") or {}).get("layout") or {})
    notes = [n for n in (lay.get("notes") or []) if "page size" in str(n)]
    kind = (job or {}).get("input_kind") or ("DXF" if engine.get("dxf") else "PDF")
    lines = [f"입력 {kind} · {len(pages)}장 · " + " · ".join(f"{k or '종류 없음'} {n}장" for k, n in kinds.most_common())]
    if len(sizes) > 1:
        lines.append("종이 크기가 섞여 있다: " + " · ".join(f"{k} pt {n}장" for k, n in sizes.most_common())
                     + " — 다수 크기의 장으로 양식을 쟀다 (소수 장은 대상에서 빠진다)")
    elif sizes:
        lines.append(f"종이 {sizes.most_common(1)[0][0]} pt (전 장 같음)")
    lines += notes
    dx = engine.get("dxf") or {}
    if dx.get("skipped_inputs"):
        lines.append(f"DXF 묶음에서 건너뛴 파일 {len(dx['skipped_inputs'])}개")
    if dx.get("roles_note"):
        lines.append(str(dx["roles_note"]))
    return _sec("input", "입력", "info", lines, facts={"kinds": dict(kinds), "sizes": dict(sizes)})


def _titleblock(engine, pages, user_sheets: dict, user_cells: bool) -> dict:
    lay = ((engine.get("applied_rules") or {}).get("layout") or {})
    prof = engine.get("profile") or {}
    bor = engine.get("borrowed") or {}
    items = [it for it in (lay.get("items") or []) if isinstance(it, dict)]
    by_src = collections.Counter(str(it.get("source") or "") for it in items)
    unavailable = [it["key"] for it in items if it.get("source") == "UNAVAILABLE"]
    lines, todo = [], []
    status = "ok"
    if not prof:
        lines.append("프로필 기록이 없는 옛 분석이다 (56회차 이전)")
    elif prof.get("matched"):
        lines.append(f"프로필 {prof.get('name') or prof.get('path')} ({prof.get('code')}) 이 이 도면의 것이다"
                     + (" — 환경변수로 못박힘" if prof.get("env_pinned") else " — 도면번호의 프로젝트 코드로 자동 선택"))
    else:
        code = prof.get("document_code") or ""
        n = _n(bor.get("count"))
        lines.append((f"코드 {code} 에 맞는 프로필이 없다 → 새 프로젝트" if code
                      else "도면번호에서 프로젝트 코드를 읽지 못해 프로필을 고르지 못했다")
                     + f" — 기본 설정({prof.get('borrowed_from') or prof.get('path')})에서 {n}칸을 빌려 썼다")
        status = "warn"
        todo.append({"what": f"config/project_<이름>.yaml 을 만든다 (project.code: {code or '?'})",
                     "where": "GET /jobs/{id}/measured_config → measured_yaml 을 붙여 넣는다",
                     "why": f"빌린 {n}칸이 다음 분석부터 이 프로젝트의 값이 된다"})
    if items:
        lines.append("타이틀블록·도면틀 유도: " + " · ".join(f"{k} {n}" for k, n in by_src.most_common()))
    if unavailable:
        lines.append("재지 못한 항목 (설정값 그대로): " + ", ".join(unavailable))
    uc = lay.get("user_cells") or {}
    if uc.get("applied"):
        lines.append(f"사람이 도면 위에 그은 칸을 썼다 ({', '.join(str(k) for k in uc['applied'])})")
    elif uc.get("reason"):
        lines.append(f"사람이 그은 칸이 있으나 얹지 않았다 — {uc['reason']}")
    elif user_cells:
        lines.append("프로젝트에 사람이 그은 타이틀블록 칸이 있다 (이번 분석에는 안 쓰였다)")
    # 도면번호 · REV
    pid = [p for p in pages if str(p.get("page_kind")) == "PID"]
    unknown = [int(p["page_no"]) for p in pages if str(p.get("page_kind")) == "UNKNOWN"]
    legend_pages = set(_n(x) for x in ((engine.get("legend_profile") or {}).get("legend_sheets") or []))
    unknown_real = [n for n in unknown if n not in legend_pages]
    rev_read = sum(1 for p in pid if str(p.get("rev") or ""))
    lines.append(f"도면번호 읽힌 장 {len(pid)} · 못 읽은 장 {len(unknown)}"
                 + (f" (그중 범례 장 {len(unknown) - len(unknown_real)})" if len(unknown) != len(unknown_real) else "")
                 + f" · REV 읽힌 장 {rev_read}/{len(pid)}")
    set_sheets = {str(k) for k in (user_sheets or {})}
    missing = [n for n in unknown_real if str(n) not in set_sheets]
    if missing:
        status = _worst(status, "todo")
        todo.append({"what": f"도면번호를 못 읽은 장 {len(missing)}장 — 타이틀블록이 획이거나 양식이 다르다"
                             f" (p{', p'.join(str(n) for n in missing[:8])}{' …' if len(missing) > 8 else ''})",
                     "where": "장 도면번호 판 (못 읽은 장만 나온다) 또는 [타이틀블록 칸 지정]",
                     "why": "적으면 다시 분석할 때 그 장이 분석 대상이 된다 — 안 적으면 그 장의 계기가 통째로 빠진다"})
    if pid and rev_read == 0:
        status = _worst(status, "warn")
        lines.append("REV 를 한 장도 못 읽었다 — 이력 표가 획이거나 개정 표기 꼴이 다르다 (검출·수량·SCOPE 에는 안 쓰인다)")
    facts = {"profile_matched": bool(prof.get("matched")), "document_code": prof.get("document_code"),
             "borrowed": _n(bor.get("count")), "unavailable": unavailable,
             "pid_pages": len(pid), "unknown_pages": unknown_real, "rev_read": rev_read}
    return _sec("titleblock", "양식 · 타이틀블록", status, lines, todo, facts)


def _legend(engine, labels: dict) -> dict:
    lp = engine.get("legend_profile") or {}
    leg = engine.get("legend") or {}
    prof = engine.get("profile") or {}
    whose = prof.get("borrowed_from") or prof.get("path") or "프로젝트 설정"
    lines, todo = [], []
    status = "ok"
    mode = lp.get("mode") or "unknown"
    sheets = lp.get("legend_sheets") or []
    lines.append({"derived": f"이 문서의 범례를 직접 읽었다 (값을 읽은 장 {len(sheets)})",
                  "reused": "프로젝트에 저장된 범례 프로필을 썼다" + (" · 이 PDF 의 범례와 대조함" if lp.get("compared") else " · 이 PDF 에 범례가 없어 대조 못 함"),
                  "unknown": "범례 기록이 없는 옛 분석"}.get(mode, mode))
    fell = []
    for key, d in leg.items():
        if not isinstance(d, dict):
            continue
        src = str(d.get("source") or "")
        if src in ("LEGEND", "MEASURED", "DERIVED", "PROFILE"):
            continue
        fell.append((key, src, str(d.get("note") or "")))
    if fell:
        status = "warn"
        for key, src, note in fell:
            lines.append(f"{labels.get(key, key)}: {src} — {note or '사유 없음'}"
                         + (f" (값은 {whose} 의 것)" if src == "CONFIG_FALLBACK" else ""))
        if any(src == "NEEDS_REVIEW" for _k, src, _n_ in fell):
            status = "todo"
            todo.append({"what": "범례가 그 항목을 그리지 않고 설정에도 값이 없다",
                         "where": "config/project_<이름>.yaml valves.legend_fallback",
                         "why": "그 판정(밸브 몸체·액추에이터·신호선)은 값이 없으면 돌지 않는다"})
        else:
            todo.append({"what": "범례에서 재지 못한 항목 " + ", ".join(k for k, _s, _n_ in fell) + " 이 설정 폴백으로 돌았다",
                         "where": "Symbol & Legend 장 확인 (그 심볼이 범례에 그려져 있는가) → 없으면 프로젝트 설정에 그 도면 값을 적는다",
                         "why": f"지금 값은 {whose} 에서 잰 것이라 이 도면의 축척·그리기 방식과 다를 수 있다"})
    vl = engine.get("valve_layout") or {}
    if vl:
        sc = vl.get("legend_scale")
        if sc and float(sc) != 1.0:
            lines.append(f"범례 장과 본문 장의 종이가 다르다 — 범례에서 잰 길이에 x{sc} 를 곱했다 ({vl.get('legend_scale_source') or ''})")
        for k, lab in (("act_box_source", "액추에이터 울타리 창"), ("source", "밸브 몸체 창")):
            s = str(vl.get(k) or "")
            if s and "LEGEND" not in s.upper():
                status = _worst(status, "warn")
                lines.append(f"{lab}: {s} — {vl.get(k.replace('source', 'basis')) or ''}".rstrip(" —"))
    isa = ((engine.get("description_build") or {}).get("isa_table") or {})
    first = isa.get("first") or isa.get("first_letters") or {}
    succ = isa.get("succeeding") or isa.get("succeeding_letters") or {}
    if isa:
        lines.append(f"ISA 문자표: FIRST {len(first)} · SUCCEEDING {len(succ)}"
                     + (f" (p{isa.get('page_no')})" if isa.get("page_no") else ""))
        if first and not succ:
            status = _worst(status, "warn")
            lines.append("SUCCEEDING 열을 못 읽었다 — 사전에 없는 태그(AIT 등)가 행이 되지 않는다")
            todo.append({"what": "범례 ISA 문자표의 SUCCEEDING 열 판형 확인",
                         "where": "Symbol & Legend 의 ISA 표 장 (TYPICAL SYMBOL 머리줄 또는 `( ) X` 칸)",
                         "why": "그 열이 있어야 두 글자 이상 태그가 분해된다 (50회차 · hotfix31)"})
    ia = engine.get("isa_anchors") or {}
    if ia.get("total"):
        lines.append(f"사전에 없던 낱말을 ISA 표가 앵커로 세움 {ia.get('total')}개")
    facts = {"mode": mode, "sheets": sheets, "fallbacks": [k for k, _s, _n_ in fell],
             "legend_scale": vl.get("legend_scale")}
    return _sec("legend", "범례", status, lines, todo, facts)


def _multipliers(engine, rows, user_mults: dict) -> dict:
    m = engine.get("multipliers") or {}
    src = str(m.get("source") or "")
    un = engine.get("unit_notes") or {}
    lines, todo = [], []
    status = "ok"
    table = m.get("table") or {}
    lines.append({"LEGEND": "범례 UNIT IDENTIFICATION 표에서 읽었다",
                  "CONFIG_FALLBACK": "범례에 승수표가 없어 설정 폴백으로 돌았다 (남의 도면 값일 수 있다)",
                  "USER": "사람이 지정한 승수로 돌았다"}.get(src, src or "승수 기록 없음")
                 + (" — " + " · ".join(f"{k}:x{v}" for k, v in sorted(table.items())) if table else ""))
    if isinstance(un, dict) and un:
        counted = sum(1 for v in un.values() if isinstance(v, dict) and v.get("counted"))
        if counted:
            lines.append(f"그 장 NOTES 가 '유닛 몇 개에 같이 쓰인다' 를 말한 장 {counted}")
    want = {"MULTIPLIER_UNDEFINED", "MULTIPLIER_FROM_CONFIG", "MULTIPLIER_DEFAULT_ONE", "MULTIPLIER_NOTE_RANGE"}
    hit = collections.Counter()
    for r in rows:
        cs = set(_codes(r)) & want
        if cs:
            hit.update(cs)
    if hit:
        n = sum(hit.values())
        status = "todo"
        lines.append("승수를 묻는 행 " + " · ".join(f"{c} {k}" for c, k in hit.most_common()))
        set_units = {str(k) for k in (user_mults or {})}
        todo.append({"what": f"유닛코드 승수 지정 — 묻는 행 {n}" + (f" (이미 지정 {len(set_units)}개 유닛 — 다시 분석해야 반영)" if set_units else ""),
                     "where": "수량 승수 판 (유닛코드로 묶어 묻는다 · 작성자 필수)",
                     "why": "도면이 승수를 말하지 않는다 — 세 프로젝트에서 사람 몫 1위 (roadmap §2)"})
    by_user = sum(1 for r in rows if "MULTIPLIER_BY_USER" in _codes(r))
    if by_user:
        lines.append(f"사람이 지정한 승수로 돈 행 {by_user} (감사용 사유가 남는다)")
    return _sec("multipliers", "수량 승수", status, lines, todo,
                facts={"source": src, "table": table, "asking": dict(hit)})


def _tier(engine, mode: dict) -> dict:
    t = engine.get("evidence_tier") or {}
    tg = engine.get("tag_grammar") or {}
    lines, todo = [], []
    status = "ok"
    if not t:
        return _sec("tier", "증거 등급 · 모드", "info", ["입찰/실행 기록이 없는 옛 분석"])
    tier = t.get("tier")
    lines.append((mode or {}).get("line") or f"등급 {tier}")
    rows = _n(t.get("rows")); tagged = _n(t.get("tagged_rows"))
    if tier == 1:
        lines.append(f"태그가 인쇄된 1급 문서 — 태그 붙은 행 {tagged}/{rows} · 모양 {', '.join((t.get('shapes') or [])[:3])}")
    else:
        lines.append("태그가 인쇄되지 않은 2급 문서 — 기하·거리·별표로 읽는다 (SCOPE 는 언제나 2급)")
    if (mode or {}).get("conflict"):
        status = "todo"
        todo.append({"what": "선언한 모드와 실측이 다르다", "where": "첫 화면 프로젝트 설정 (입찰/실행) → 다시 분석",
                     "why": (mode or {}).get("line") or ""})
    g = tg.get("grammar") or {}
    if tg.get("enabled") and g.get("learned"):
        lines.append(f"태그 문법 학습됨 — 어긋남 {len(tg.get('mismatch') or [])}행 · 태그가 증거인 행 {len(tg.get('evidence_rows') or [])}")
    return _sec("tier", "증거 등급 · 모드", status, lines, todo,
                facts={"tier": tier, "tagged_rows": tagged, "rows": rows})


def _scope(engine, rows) -> dict:
    sc = collections.Counter(str(_values(r).get("scope") or "") for r in rows
                             if not r.get("deleted") and not r.get("removed"))
    lines, todo = [], []
    status = "ok"
    nameless = sc.get("VENDOR", 0)
    named = sum(n for k, n in sc.items() if k.startswith("VENDOR("))
    blank = sc.get("", 0)
    lines.append("SCOPE 분포: " + " · ".join(f"{k or '빈칸'} {n}" for k, n in sc.most_common(6)))
    # hotfix83 — 정의 없는 별표는 사용자 확정으로 그냥 VENDOR 다 (사람 몫이 아니다).
    # 예전 분석은 검토 사유가 남아 있으므로 세기만 한다.
    undefined = sum(1 for r in rows if "VENDOR_MARK_UNDEFINED" in _codes(r))
    if nameless:
        lines.append(f"이름 없는 VENDOR {nameless}행 — 그 장 NOTES 가 공급자를 적지 않았다 "
                     "(규칙: 적혀 있으면 그 이름 · 없으면 VENDOR)")
    if blank:
        lines.append(f"공급 주체 빈칸 {blank}행 (태그만이 증거인 행 · 사람이 더한 행)")
    dashed = sum(1 for r in rows if "BUBBLE_DASHED" in _codes(r))
    if dashed:
        lines.append(f"파선으로 그린 버블 {dashed}행 — 범례가 파선 버블의 뜻을 정하지 않는다 (실무 판단 15)")
    return _sec("scope", "공급 주체 (SCOPE)", status, lines, todo,
                facts={"dist": dict(sc), "undefined": undefined, "nameless": nameless})


def _review(rows, review_axes: list | None, labels: dict) -> dict:
    cnt = collections.Counter()
    if review_axes:
        for ax in review_axes:
            for c in ax.get("codes") or []:
                cnt[c["code"]] += _n(c.get("open"))
    else:
        for r in rows:
            for c in _codes(r):
                cnt[c] += 1
    lines, todo = [], []
    status = "ok"
    if cnt:
        lines.append(f"검토 사유 {sum(cnt.values())}건 · 종류 {len(cnt)}")
        for code, n in cnt.most_common(12):
            lines.append(f"{code} {n} — {labels.get(code, '')}".rstrip(" —"))
        # 사람이 답할 자리가 있는 사유만 todo 로 (감사용은 뺀다)
        for code, n in cnt.most_common():
            w = WHERE.get(code)
            if not w or "감사용" in w[1] or code.startswith("MULTIPLIER_") or code == "VENDOR_MARK_UNDEFINED":
                continue   # 승수·SCOPE 는 자기 섹션이 말한다
            todo.append({"what": f"{code} {n}행 — {w[1]}", "where": w[0], "why": labels.get(code, "")})
        if todo:
            status = "todo"
    else:
        lines.append("검토 사유가 붙은 행이 없다")
    return _sec("review", "검토 사유", status, lines, todo, facts={"counts": dict(cnt)})


def _policy(engine) -> dict:
    """hotfix83 — 사용자가 정한 '식별하지 않는 것' 이 무엇을 뺐나 (판정 아님 · 옮겨 적기)."""
    pol = engine.get("policy_excluded")
    if not pol:
        return _sec("policy", "사용자 방침으로 뺀 행", "info", ["기록 없음 (hotfix83 이전 분석)"])
    by_reason = pol.get("by_reason") or {}
    by_type = pol.get("by_type") or {}
    lines = [f"식별하지 않는 태그: {', '.join(pol.get('not_identified_tags') or []) or '없음'} · "
             f"제어실 기능 버블: {'넣지 않음' if pol.get('control_room_functions') == 'exclude' else '넣음'}"]
    if by_reason:
        lines.append(f"뺀 행 {sum(_n(v) for v in by_reason.values())} — "
                     + " · ".join(f"{'PSV 등 식별 안 함' if k == 'NOT_IDENTIFIED_TAG' else '제어실 기능'} {v}"
                                  for k, v in by_reason.items()))
        lines.append("종류: " + " · ".join(f"{k} {v}" for k, v in
                                           sorted(by_type.items(), key=lambda kv: -_n(kv[1]))[:10]))
    else:
        lines.append("이 문서에서 뺀 행이 없다")
    return _sec("policy", "사용자 방침으로 뺀 행", "info", lines,
                facts={"by_reason": by_reason, "by_type": by_type})


def _borrowed(engine) -> dict:
    bor = engine.get("borrowed") or {}
    prof = engine.get("profile") or {}
    if not bor:
        return _sec("borrowed", "빌린 설정 값", "info", ["기록 없음 (56회차 이전 분석)"])
    n = _n(bor.get("count")); rep = len(bor.get("replaced_by_sheet") or [])
    bys = bor.get("by_section") or {}
    lines = [f"기본 설정({bor.get('from') or prof.get('path')})에서 읽은 잎 {_n(bor.get('read'))} · 그중 빌린 값 {n}"
             + (f" · 도면이 직접 답해 뺀 것 {rep}" if rep else "")]
    if bys:
        lines.append("구획별: " + " · ".join(f"{k} {v}" for k, v in sorted(bys.items(), key=lambda kv: -_n(kv[1]))[:8]))
    keys = list(bor.get("keys") or [])
    if keys:
        lines.append("예: " + ", ".join(keys[:10]) + (" …" if len(keys) > 10 else ""))
    status = "warn" if (n and not prof.get("matched")) else "ok"
    return _sec("borrowed", "빌린 설정 값", status, lines, facts={"count": n, "keys": keys})


def _extras(engine, rows) -> dict:
    lines = []
    ts = engine.get("typical_stats") or {}
    if ts:
        lines.append(f"Typical 상세 — 안 행 {ts.get('rows_in_detail', 0)} · 곱한 행 {ts.get('rows_multiplied', 0)} · 표식마다 가른 행 {ts.get('rows_from_split', 0)}")
    ro = engine.get("readouts") or {}
    if isinstance(ro, dict) and ro:
        fold = ro.get("folded")
        nf = len(fold) if isinstance(fold, list) else _n(fold)
        lines.append(f"한 가지의 표시기를 전송기에 접음 {nf} · 게이지 표기 {_n(ro.get('gauges'))}")
    uj = engine.get("unjudged_symbols")
    if isinstance(uj, list):
        lines.append(f"판정하지 못한 심볼 {len(uj)} — 등록 화면에서 사람이 정한다")
    ln = sum(1 for r in rows if _values(r).get("line_no"))
    if ln:
        lines.append(f"라인 번호 붙은 행 {ln}")
    return _sec("extras", "그 밖의 사실", "info", lines)


# --------------------------------------------------------------------------
# 조립
# --------------------------------------------------------------------------

def build(engine: dict, pages: Iterable[dict], rows: Iterable[dict], *, job: dict | None = None,
          user_mults: dict | None = None, user_sheets: dict | None = None, user_cells: bool = False,
          mode: dict | None = None, review_axes: list | None = None, labels: dict | None = None) -> dict:
    """점검표.  **판정 0 · 엔진 import 0** — 저장된 사실만 읽는다."""
    pages = list(pages or [])
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    labels = labels or {}
    secs = [_input(engine, pages, job),
            _titleblock(engine, pages, user_sheets or {}, user_cells),
            _legend(engine, labels),
            _multipliers(engine, rows, user_mults or {}),
            _tier(engine, mode or {}),
            _scope(engine, rows),
            _policy(engine),
            _review(rows, review_axes, labels),
            _borrowed(engine),
            _extras(engine, rows)]
    todo = [dict(t, section=s["key"]) for s in secs for t in s["todo"]]
    counts = collections.Counter(s["status"] for s in secs)
    verdict = ("todo" if counts.get("todo") else "warn" if counts.get("warn") else "ok")
    head = {"todo": f"사람 몫 {len(todo)}건 — 아래 순서대로 답하면 다음 분석이 이 도면의 값으로 돈다",
            "warn": "사람이 당장 답할 것은 없지만 대신한 값으로 돈 자리가 있다",
            "ok": "이 도면이 필요한 값을 전부 답했다"}[verdict]
    return {"verdict": verdict, "headline": head, "sections": secs, "todo": todo,
            "text": render_text(secs, todo, head)}


def render_text(secs, todo, head) -> str:
    mark = {"ok": "✔", "warn": "△", "todo": "★", "info": "·"}
    out = [f"# 새 프로젝트 점검표 — {head}", ""]
    if todo:
        out.append("## 사람 몫")
        for i, t in enumerate(todo, 1):
            out.append(f"{i}. {t['what']}")
            out.append(f"   어디서: {t['where']}")
            if t.get("why"):
                out.append(f"   왜: {t['why']}")
        out.append("")
    for s in secs:
        out.append(f"## {mark.get(s['status'], '·')} {s['title']}")
        out.extend(f"- {x}" for x in s["lines"])
        out.append("")
    return "\n".join(out)
