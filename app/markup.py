"""사용자 마크업 — 누락 행 추가 · 오검출 표시 · 피드백 내보내기 (44회차).

★ 마크업은 **편집값 층**에 산다.  추출값(`ai_json`) · 지문 · 축1 · 축2 · 축3 은
이 모듈이 닿지 않는 자리다 — 지문은 `pipeline.fingerprint(result)` 가 분석
결과에서 만들고, 축은 `spike/accuracy.py` · `spike/identification.py` 가
결과 json 만 읽는다.  이 모듈은 DB 의 `item` 행(`added=1` · `reject_json`)과
`feedback` 표만 쓴다.  `tests/test_markup.py` 가 그것을 소스 검사로 못박는다.

새로 만든 것은 **잇는 코드**뿐이다 (`out/round44_survey.md` §0):
  · 제안값 — 도면에서 먼저 읽는다 (§9 ①②).  SCOPE 는 파이프라인이 밸브 행에
    쓰는 11회차 순서 그대로(`pipeline.propose_at`), 수량은 **같은 장의 행이
    이미 받은 값**, TYPE 은 사각형 안 낱말 중 이 프로젝트 앵커 사전에 있는 것.
  · 안정 ID — 같은 장부(`revisions.Registry`)에서 같은 `next_seq` 로 받는다.
    회수 없음 · 단조 증가는 §7.3 그대로다.
  · 내보내기 — 있는 표(`item` · `feedback` · `report`)를 zip 하나로 꺼낸다.
"""
from __future__ import annotations

import collections
import datetime as _dt
import io
import json
import time
import zipfile
from pathlib import Path

from app import db, revisions

# 사유 분류 (요구 [D-4]).  값은 저장되는 문자열이고 화면 라벨은 따로다.
CLASSES = {
    "MISSING": "㉡ 미검출 — 도면에 있는데 행이 없음",
    "FALSE_POSITIVE": "㉢ 오검출 — 행이 있는데 도면에 없음",
    "WRONG_VALUE": "㉣ 값 틀림 — 행은 맞는데 칸이 틀림",
    "UNKNOWN_SYMBOL": "미지정 심볼 — 범례에 없어 무엇인지 사람이 정함",
    "OTHER": "기타",
}
SOURCE_DRAWING = "DRAWING"
SOURCE_USER = "USER"
CODE_ADD = "MANUAL_ADD"
CODE_REJECT = "MANUAL_REJECT"


# --------------------------------------------------------------------------
# 제안값 — 도면이 말하는 것을 먼저 읽는다
# --------------------------------------------------------------------------

def _type_from_words(words: list) -> dict:
    """사각형 안 낱말 중 **이 프로젝트 앵커 사전**에 있는 것.  없으면 빈칸.

    사전은 엔진이 쓰는 그것(`detect_symbols.RULESET_V3`)이고 여기서 낱말을
    나열하지 않는다.  둘 이상이면 고르지 않고 후보만 낸다 (§9 ④).
    """
    from app.engine import detect_symbols as ds
    rules = ds.RULESET_V3
    seen = []
    for w in words:
        t = str(w.get("text") or "").strip().upper()
        if t and t in rules.anchors and t not in seen:
            seen.append(t)
    if len(seen) == 1:
        t = seen[0]
        if t in rules.field_type_map:
            return {"type": rules.field_type_map[t], "anchor": t, "tab": "FIELD",
                    "candidates": seen}
        return {"type": "", "anchor": t, "tab": _valve_tab(t), "candidates": seen}
    return {"type": "", "anchor": "", "tab": "", "candidates": seen}


def _valve_tab(tag: str) -> str:
    """밸브 태그 글자 → 산출물 탭.  근거는 산출물 정의(`excel_out.DELIVERABLES`)
    가 아니라 10회차 실측(MOV 48 · XV/TCV/PCV/FCV 공압)이고, 확실하지 않으면
    빈칸으로 두어 사람이 고른다."""
    if tag in ("MOV", "HOV"):
        return "MOV"
    if tag in ("XV", "FCV", "PCV", "TCV", "LCV", "CV"):
        return "PNEUMATIC"
    return ""


def _qty_from_page(con, job_id: str, page_no: int) -> dict:
    """같은 장의 행이 이미 받은 수량.  그 장의 배수는 장 단위 사실이고
    `_note_factor` 의 순서(①범례 → ②NOTES → ③사람 → ④설정 → ⑤빈칸)가 이미
    그 행들에 찍혀 있다 — 여기서 다시 읽지 않고 **그대로 옮긴다**.

    값이 갈리면(Typical 상자 안·밖이 섞인 장) 고르지 않고 빈칸 + 사유다.
    """
    rows = [r for r in db.merged_rows(con, job_id)
            if r["page_no"] == page_no and not r["added"] and not r["removed"]
            and not r["deleted"]]
    vals = collections.Counter()
    basis = {}
    for r in rows:
        q = (r.get("ai") or {}).get("qty")
        if isinstance(q, (int, float)):
            vals[int(q)] += 1
            basis.setdefault(int(q), (r.get("evidence") or {}).get("qty_basis", ""))
    if not vals:
        return {"qty": None, "qty_source": SOURCE_USER,
                "qty_basis": "같은 장에 추출 행이 없어 배수를 옮길 수 없음 — 직접 적는다"}
    if len(vals) == 1:
        q = next(iter(vals))
        return {"qty": q, "qty_source": SOURCE_DRAWING,
                "qty_basis": f"같은 장 {vals[q]}행이 받은 값을 옮김 — {basis[q]}"}
    detail = " · ".join(f"{q} ({n}행)" for q, n in sorted(vals.items()))
    return {"qty": None, "qty_source": SOURCE_USER,
            "qty_basis": f"같은 장의 수량이 갈립니다 ({detail}) — 어느 쪽인지 도면이 말하지 않아 직접 적는다"}


def propose(con, job, page_no: int, rect) -> dict:
    """마크업 사각형 하나에 대한 제안값.  **아무것도 쓰지 않는다.**"""
    from app import pipeline
    page = con.execute(
        "SELECT drawing_no, width, height FROM pid_page WHERE job_id=? AND page_no=?",
        (job["id"], page_no)).fetchone()
    drawing_no = page["drawing_no"] if page else ""
    rect = [float(v) for v in rect]
    read = pipeline.propose_at(Path(job["pdf_path"]), page_no, rect)
    out = {"page_no": page_no, "drawing_no": drawing_no, "rect": rect}
    out.update(_type_from_words(read.get("words") or []))
    out.update({k: read.get(k) for k in ("scope", "scope_source", "scope_evidence",
                                         "words", "stars", "notes")})
    out.update(_qty_from_page(con, job["id"], page_no))
    return out


# --------------------------------------------------------------------------
# 안정 ID — 같은 장부 · 같은 규칙
# --------------------------------------------------------------------------

def assign_stable_id(data_dir: Path, con, job, key: str, row: dict) -> dict:
    """프로젝트가 있으면 그 장부에서 ID 를 받는다.  없으면 받지 않고 그렇게 말한다.

    `Registry.assign` 은 `next_seq` = 그 계통의 최대 순번 + 1 이라 회수·재정렬이
    없다 (§7.3).  기록에 `origin: user` 를 남겨 사람이 먼저 본 행임을 적는다.
    상태는 `compare()` 와 같은 규칙 — 비교 대상이 없으면 BASELINE, 있으면 ADDED.
    """
    name = job["project"] or ""
    if not name:
        return {"stable_id": "", "excel_no": 0,
                "why": "프로젝트에 묶이지 않은 분석이라 ID 장부가 없습니다"}
    reg_path = revisions.project_dir(data_dir, name) / "id_registry.json"
    registry = revisions.Registry.load(reg_path)
    revision = job["revision"] or ""
    ident = registry.assign(dict(row, key=key), revision)
    rec = registry.data["ids"][ident]
    rec["origin"] = "user"
    rec["last_anchor"] = list(rec["anchor"])
    rec["values"] = {f: row.get(f) for f in revisions.COMPARED_FIELDS}
    state = revisions.BASELINE if not (job["compared_with"] or "") else revisions.ADDED
    rec["history"][-1]["state"] = state
    numbers = revisions.assign_excel_numbers(
        [dict(row, key=key, stable_id=ident)], registry)
    registry.save(reg_path)
    excel_no = numbers.get(key, 0)
    db.set_row_revision_state(con, job["id"], key, ident, state, excel_no)
    return {"stable_id": ident, "excel_no": excel_no, "state": state, "why": ""}


# --------------------------------------------------------------------------
# 집계 — 화면 범례 · 보고서가 읽는 수
# --------------------------------------------------------------------------

def summary(con, job_id: str) -> dict:
    rows = db.merged_rows(con, job_id)
    out = {"added": 0, "added_with_rect": 0, "scope_user": 0, "qty_user": 0,
           "rejected": 0, "rejected_excluded": 0, "by_page": {}}
    for r in rows:
        mk = (r.get("evidence") or {}).get("markup") or {}
        pg = out["by_page"].setdefault(str(r["page_no"]), {"added": 0, "rejected": 0})
        if r["added"]:
            out["added"] += 1
            pg["added"] += 1
            if r.get("rect"):
                out["added_with_rect"] += 1
            if mk.get("scope_source") == SOURCE_USER:
                out["scope_user"] += 1
            if mk.get("qty_source") == SOURCE_USER:
                out["qty_user"] += 1
        if r.get("reject") or r["removed"]:
            out["rejected"] += 1
            pg["rejected"] += 1
            if r["removed"]:
                out["rejected_excluded"] += 1
    return out


# --------------------------------------------------------------------------
# 피드백 내보내기 — 있는 표를 zip 하나로
# --------------------------------------------------------------------------

def _items(con, job_id: str) -> list:
    rows = db.merged_rows(con, job_id)
    by_key = {r["key"]: r for r in rows}
    items = []
    for r in rows:
        ev = r.get("evidence") or {}
        mk = ev.get("markup") or {}
        v = r.get("values") or {}
        if r["added"]:
            items.append({
                "kind": "missing", "row_key": r["key"], "page": r["page_no"],
                "pid_no": r.get("drawing_no") or "", "rect": r.get("rect") or [],
                "tab": r["tab"], "type": v.get("type") or "",
                "scope": v.get("scope") or "",
                "scope_source": mk.get("scope_source") or "",
                "qty": v.get("qty"), "qty_source": mk.get("qty_source") or "",
                "description": v.get("description") or "",
                "class": mk.get("class") or "MISSING",
                "note": mk.get("note") or "", "by": mk.get("author") or "",
                "at": mk.get("at"), "stable_id": mk.get("stable_id") or "",
                "proposal": mk.get("proposal") or {},
                "clip": "",
            })
        rj = r.get("reject") or {}
        if rj or r["removed"]:
            items.append({
                "kind": "false_positive", "row_key": r["key"], "page": r["page_no"],
                "pid_no": r.get("drawing_no") or "", "rect": r.get("rect") or [],
                "tab": r["tab"], "type": v.get("type") or "",
                "scope": v.get("scope") or "", "qty": v.get("qty"),
                "class": rj.get("class") or "FALSE_POSITIVE",
                "note": rj.get("note") or "", "by": rj.get("author") or "",
                "at": rj.get("at"), "excluded_from_excel": bool(r["removed"]),
                "rules_hit": list(ev.get("rules_hit") or []),
                "clip": "",
            })
    # 값 틀림 — 편집 이력 중 (행, 칸) 의 마지막 것.  추가 행의 편집은 그 행의
    # 값이지 "틀린 값의 정정" 이 아니므로 뺀다.
    latest = {}
    for f in db.feedback_rows(con, job_id, limit=1_000_000):
        if f["kind"] != "EDITED" or f["row_key"] not in by_key:
            continue
        if by_key[f["row_key"]]["added"]:
            continue
        latest[(f["row_key"], f["field"])] = f
    for (key, field), f in sorted(latest.items()):
        r = by_key[key]
        items.append({
            "kind": "wrong_value", "row_key": key, "page": r["page_no"],
            "pid_no": r.get("drawing_no") or "", "rect": r.get("rect") or [],
            "tab": r["tab"], "type": (r.get("values") or {}).get("type") or "",
            "column": field, "current": f["ai_value"], "should_be": f["user_value"],
            "note": f.get("reason") or "", "by": f.get("author") or "",
            "at": f.get("created_at"), "clip": "",
        })
    for rep in db.list_reports(con, job_id):
        items.append({
            "kind": "report", "row_key": rep.get("row_key") or "",
            "page": rep.get("page_no"), "pid_no": rep.get("drawing_no") or "",
            "rect": rep.get("rect") or [], "what": rep.get("what"),
            "note": rep.get("detail") or "", "at": rep.get("created_at"),
            "report_kind": rep.get("kind"), "clip": "",
        })
    items.sort(key=lambda it: (it.get("page") or 0, it["kind"], str(it.get("row_key"))))
    return items


_CLIP_MARGIN_PT = 60.0     # 조각 그림의 여백 — 화면 근거가 아니라 보기 편의


def _render_pages(pdf_path: Path, wanted: dict, zoom: float):
    """`{page_no: [(rect, colour, label), ...]}` → `{page_no: PIL.Image}` (표시 좌표)."""
    import pymupdf
    from PIL import Image, ImageDraw
    doc = pymupdf.open(str(pdf_path))
    out = {}
    for pno, boxes in sorted(wanted.items()):
        if not 1 <= pno <= doc.page_count:
            continue
        pg = doc[pno - 1]
        pm = pg.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        im = Image.open(io.BytesIO(pm.tobytes("png"))).convert("RGB")
        dr = ImageDraw.Draw(im)
        for rect, colour, label in boxes:
            if len(rect) != 4:
                continue
            x0, y0, x1, y1 = [v * zoom for v in rect]
            dr.rectangle([x0, y0, x1, y1], outline=colour, width=max(2, int(zoom * 1.5)))
            if label:
                dr.text((x0, max(0, y0 - 12 * zoom)), label, fill=colour)
        out[pno] = im
    doc.close()
    return out


def export_zip(con, job, out_dir: Path, data_dir: Path = None, by: str = "") -> dict:
    """피드백 zip 을 만든다.  `feedback.json` · `feedback.md` · `조각/` · `장/`.

    도면 내용(조각 그림 · 장 렌더)이 들어가므로 **저장소에 커밋하지 않는다**
    (`.gitignore` 의 `out/feedback_*.zip` · `{data}/feedback/`).
    """
    items = _items(con, job["id"])
    engine = json.loads(job["engine_json"] or "{}")
    rows_total = con.execute("SELECT COUNT(*) FROM item WHERE job_id=? AND removed=0",
                             (job["id"],)).fetchone()[0]
    project = job["project"] or Path(job["pdf_name"]).stem
    now = _dt.datetime.now(_dt.timezone.utc).astimezone()
    stamp = now.strftime("%Y-%m-%d")
    name = f"feedback_{revisions.safe_name(project)}_{stamp}.zip"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name

    # 조각과 장 — 사각형이 있는 항목만.  색은 화면 규칙과 같다:
    #   누락(사용자 추가) 초록 · 오검출 빨강 · 값 틀림 주황 · 신고 보라.
    colour = {"missing": (52, 199, 89), "false_positive": (255, 69, 58),
              "wrong_value": (255, 159, 10), "report": (191, 90, 242)}
    wanted: dict = {}
    for i, it in enumerate(items):
        if it.get("page") and len(it.get("rect") or []) == 4:
            wanted.setdefault(int(it["page"]), []).append(
                (it["rect"], colour[it["kind"]], f"{i + 1} {it['kind']}"))
    clips: dict = {}
    if wanted and job["pdf_path"] and Path(job["pdf_path"]).exists():
        zoom = 2.0
        pages = _render_pages(Path(job["pdf_path"]), wanted, zoom)
        for i, it in enumerate(items):
            pno = int(it.get("page") or 0)
            im = pages.get(pno)
            if im is None or len(it.get("rect") or []) != 4:
                continue
            x0, y0, x1, y1 = it["rect"]
            m = _CLIP_MARGIN_PT
            box = (max(0, int((x0 - m) * zoom)), max(0, int((y0 - m) * zoom)),
                   min(im.width, int((x1 + m) * zoom)), min(im.height, int((y1 + m) * zoom)))
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            buf = io.BytesIO()
            im.crop(box).save(buf, "PNG")
            fname = f"조각/{i + 1:03d}_p{pno}_{it['kind']}.png"
            clips[fname] = buf.getvalue()
            it["clip"] = fname
        full: dict = {}
        for pno, im in pages.items():
            small = im.resize((max(1, im.width // 3), max(1, im.height // 3)))
            buf = io.BytesIO()
            small.save(buf, "PNG")
            full[f"장/p{pno}.png"] = buf.getvalue()
        clips.update(full)

    authors = sorted({str(it.get("by") or "") for it in items} - {""})
    payload = {
        "project": project, "job_id": job["id"], "pdf_name": job["pdf_name"],
        "pdf_sha256": job["pdf_sha256"], "revision": job["revision"] or "",
        "fingerprint": job["fingerprint"] or "", "rows_total": rows_total,
        "exported_at": now.isoformat(timespec="seconds"),
        "by": by or ", ".join(authors),
        "authors": authors,
        "counts": collections.Counter(it["kind"] for it in items),
        "summary": summary(con, job["id"]),
        "legend_source": (engine.get("legend_profile") or {}).get("mode", ""),
        "items": items,
    }
    md = _markdown(payload)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("feedback.json", json.dumps(payload, ensure_ascii=False,
                                               indent=1, default=str))
        z.writestr("feedback.md", md)
        for fname in sorted(clips):
            z.writestr(fname, clips[fname])
    return {"path": str(path), "name": name, "items": len(items),
            "counts": dict(payload["counts"]), "clips": len(clips)}


def _markdown(p: dict) -> str:
    lines = [f"# 피드백 — {p['project']} ({p['exported_at']})", "",
             f"* 분석 `{p['job_id']}` · 지문 `{(p['fingerprint'] or '')[:8]}` · "
             f"행 {p['rows_total']} · 리비전 {p['revision'] or '(없음)'}",
             f"* 작성자: {p['by'] or '(이름 없음)'}",
             "* 종류: " + " · ".join(f"{k} {n}" for k, n in sorted(p["counts"].items())),
             "", "| # | 종류 | 장 | P&ID No. | Type | 내용 | 작성자 | 조각 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for i, it in enumerate(p["items"], 1):
        if it["kind"] == "missing":
            body = (f"누락 추가 — scope {it.get('scope') or '(빈칸)'} ({it.get('scope_source')})"
                    f" · qty {it.get('qty')} ({it.get('qty_source')})"
                    + (f" · {it['note']}" if it.get("note") else ""))
        elif it["kind"] == "false_positive":
            body = (f"{CLASSES.get(it.get('class'), it.get('class'))}"
                    + (" · Excel 제외" if it.get("excluded_from_excel") else " · Excel 유지")
                    + (f" · {it['note']}" if it.get("note") else ""))
        elif it["kind"] == "wrong_value":
            body = f"{it.get('column')}: `{it.get('current')}` → `{it.get('should_be')}`"
            if it.get("note"):
                body += f" · {it['note']}"
        else:
            body = f"신고 {it.get('what')}: {it.get('note')}"
        lines.append(f"| {i} | {it['kind']} | p{it.get('page') or '?'} | "
                     f"{it.get('pid_no') or ''} | {it.get('type') or ''} | {body} | "
                     f"{it.get('by') or ''} | {it.get('clip') or ''} |")
    return "\n".join(lines) + "\n"
