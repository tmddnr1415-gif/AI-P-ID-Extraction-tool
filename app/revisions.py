"""프로젝트 저장소 · 안정 ID · 리비전 대조.

도면에 TAG 가 없으므로(`.....` 로 미부여) 개정 사이에 같은 계기를 다시 알아볼
방법이 없다.  그래서 Rev.A 에서 좌표 기반 식별자를 한 번 발급하고, 이후로는
**절대 다시 매기지 않는다.**

    {KKS 계통코드}-{3자리 순번}      10LBA10-001 · 00PAB10-014

계통코드는 도면번호에서 나온다 (`D00P-10LBA10-M05-0001` -> `10LBA10`).
SYSTEM 명은 쓰지 않는다 — 한 계통이 여러 장에 걸쳐 있어 순번이 충돌한다.

**왜 다시 매기지 않는가.**  좌표순으로 매번 다시 매기면 도면 중간에 계기 하나가
추가될 때 뒤 번호가 전부 밀린다.  실제로는 1건 추가인데 대조 결과가
"1건 추가 + 40건 수정" 이 된다.  그래서 새 항목은 그 도면의 **최대 순번 + 1**
을 받고, 삭제가 나도 번호를 회수하지 않는다.  단조 증가한다.

**최초 부여 순서는 결정적이다.**  부동소수 좌표로 정렬하면 같은 입력에서도
순서가 흔들릴 수 있으므로, 정렬 키를 반올림한 정수 좌표로 고정한다
(y -> x -> TYPE -> 행 키).  같은 PDF 를 두 번 넣으면 같은 레지스트리가 나온다.

**자리를 옮긴 것만으로는 '수정' 이 아니다.**  얼마를 움직여야 수정인지에는
근거가 없고, 어떤 값을 골라도 임의값이다 (§2.3).  그리고 검토자가 보는 것은
좌표가 아니라 칸의 값이므로, 시트를 다시 그린 개정에서 전 행이 '수정' 으로
물드는 쪽이 더 나쁘다.  그래서 상태는 `COMPARED_FIELDS` 의 값으로만 정하고,
움직인 거리는 `moved_pt` 로 이력과 상태에 **기록만** 한다.  근거 패널에서
보이므로 사람이 판단할 수 있다.  이 판단은 뒤집을 수 있게 한 곳에 모여 있다.

**삭제는 여기서 확정하지 않는다.**  검출 실패와 실제 삭제는 구분되지 않는다 —
계기가 도면에 그대로 있는데 우리가 그 장에서 못 뽑으면 똑같이 매칭 실패로
보인다.  그래서 판정은 `DELETED_CANDIDATE` 까지이고, 사람이 확인해야 굳는다.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

# 상태.  문자열은 화면·산출물·저장 파일이 같은 낱말을 쓰도록 한 곳에 둔다.
UNCHANGED = "UNCHANGED"
ADDED = "ADDED"
MODIFIED = "MODIFIED"
DELETED_CANDIDATE = "DELETED_CANDIDATE"
DELETED = "DELETED"

# 도면번호에서 KKS 계통코드를 떼는 자리.  `D00P-10LBA10-M05-0001` 의 두 번째
# 하이픈 구획이 그것이다.  형식이 다른 문서에서는 조용히 실패하지 않고
# 도면번호 전체를 쓰고, 그 사실을 레지스트리에 적는다.
SYSTEM_CODE = re.compile(r"^[A-Z0-9]+-([A-Z0-9]+)-")

# 대조에서 값이 같은지 보는 칸.  화면에 나가는 칸만 본다 — 근거 패널의 내부
# 값까지 비교하면 사람이 볼 수 없는 이유로 '수정' 이 뜬다.
COMPARED_FIELDS = ("type", "valve_type", "qty", "system", "vendor_supply",
                   "scope", "tag_no", "description")


def system_code(drawing_no: str) -> tuple[str, str]:
    """(계통코드, 근거).  떼지 못하면 도면번호 전체를 쓴다."""
    m = SYSTEM_CODE.match((drawing_no or "").strip())
    if m:
        return m.group(1), "도면번호 2번째 구획"
    return (drawing_no or "UNKNOWN").strip(), "도면번호에서 계통코드를 떼지 못함"


def safe_name(name: str) -> str:
    """프로젝트명을 디렉터리 이름으로.  경로를 벗어날 수 있는 글자를 막는다."""
    name = unicodedata.normalize("NFC", (name or "").strip())
    if not name:
        raise ValueError("프로젝트명이 비어 있습니다")
    if name in (".", "..") or any(c in name for c in '/\\:*?"<>|\0'):
        raise ValueError(f"프로젝트명에 쓸 수 없는 글자가 있습니다: {name!r}")
    return name


def sort_key(row: dict) -> tuple:
    """최초 ID 부여 순서.  반올림한 정수 좌표로 정렬해 결정성을 고정한다.

    부동소수 좌표를 그대로 비교하면 같은 문서에서도 미세한 차이로 순서가
    뒤집힐 수 있다.  1pt 격자로 반올림하면 그 흔들림이 사라지고, 같은 격자에
    두 심볼이 들어오면 TYPE 과 행 키가 순서를 정한다.
    """
    rect = row.get("rect") or [0, 0, 0, 0]
    return (round(rect[1]), round(rect[0]),
            str(row.get("type") or ""), str(row.get("key") or ""))


def anchor(row: dict) -> tuple[float, float]:
    """그 행의 좌표.  심볼 사각형의 가운데."""
    r = row.get("rect") or [0, 0, 0, 0]
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


# --------------------------------------------------------------------------
# 매칭 반경 — 임의값을 쓰지 않는다
# --------------------------------------------------------------------------

def match_radius(rows: list, legend_bubble: float = None) -> dict:
    """이 도면에서 "같은 심볼로 볼 수 있는 거리".  임의값을 쓰지 않는다.

    1순위는 **그 도면 자신의 버블 크기**다.  버블 사각형은 범례에서 유도된
    `cap_span`·`cap_ratio`·`side_slack` 을 통과한 것만 남은 것이므로, 그 긴변은
    이 문서가 정한 심볼 치수다.  심볼 하나 크기 안에서 움직였으면 같은 것으로
    본다.  실측하면 도면마다 다르다 — 이 문서에는 68.0pt 짜리와 85.1pt 짜리가
    함께 있으므로, 문서 하나에 값 하나를 두지 않고 도면마다 다시 잰다.

    2순위는 그 도면 안 같은 TYPE 앵커 사이의 최근접 거리 절반이다.  버블 사각형이
    없는 행(수기 추가 등)뿐인 도면에서 쓴다.

    두 값을 다 담아 돌려준다 — 어느 쪽을 썼는지와 다른 쪽이 얼마였는지가 보고에
    그대로 실려야 하기 때문이다.
    """
    longs = []
    for r in rows:
        rect = r.get("rect") or []
        if len(rect) == 4 and rect[2] > rect[0] and rect[3] > rect[1]:
            longs.append(max(rect[2] - rect[0], rect[3] - rect[1]))
    nearest = None
    by_type: dict[str, list] = {}
    for r in rows:
        by_type.setdefault(str(r.get("type") or ""), []).append(anchor(r))
    for pts in by_type.values():
        for i, a in enumerate(pts):
            for b in pts[i + 1:]:
                d = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
                if d > 0 and (nearest is None or d < nearest):
                    nearest = d
    out = {"bubble_long_side": None,
           "nearest_same_type": None if nearest is None else round(nearest, 2),
           "radius": 0.0, "source": "NONE",
           "note": "버블 사각형도 같은 TYPE 이웃도 없어 유도하지 못했습니다"}
    if legend_bubble:
        out.update(radius=float(legend_bubble), source="LEGEND_BUBBLE",
                   bubble_long_side=round(float(legend_bubble), 2),
                   note=f"넘겨받은 버블 긴변 {legend_bubble:.1f}pt")
        return out
    if longs:
        longs.sort()
        med = longs[len(longs) // 2]
        out.update(radius=med, source="DRAWING_BUBBLE",
                   bubble_long_side=round(med, 2),
                   note=f"이 도면 버블 긴변의 중앙값 {med:.1f}pt (n={len(longs)})")
        return out
    if nearest is not None:
        out.update(radius=nearest / 2, source="NEAREST_SAME_TYPE",
                   note=f"같은 TYPE 최근접 {nearest:.1f}pt 의 절반")
    return out


# --------------------------------------------------------------------------

class Registry:
    """한 프로젝트의 ID 장부.  파일 하나로 저장된다."""

    def __init__(self, data: dict = None):
        self.data = data or {"version": 1, "project": "", "revisions": [],
                             "ids": {}}

    # -- 저장 -----------------------------------------------------------
    @classmethod
    def load(cls, path: Path) -> "Registry":
        if path.exists():
            return cls(json.loads(path.read_text(encoding="utf-8")))
        return cls()

    def save(self, path: Path) -> None:
        """정렬 키를 고정해 쓴다 — 두 번 저장하면 같은 파일이어야 한다."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1,
                                   sort_keys=True) + "\n", encoding="utf-8")

    # -- 조회 -----------------------------------------------------------
    def next_seq(self, code: str) -> int:
        """그 계통의 최대 순번 + 1.  삭제된 번호도 최대값 계산에 넣는다."""
        top = 0
        for rec in self.data["ids"].values():
            if rec["system_code"] == code:
                top = max(top, rec["seq"])
        return top + 1

    def by_drawing(self, drawing_no: str) -> list:
        return [r for r in self.data["ids"].values()
                if r["drawing_no"] == drawing_no and r["status"] == "active"]

    # -- 발급 -----------------------------------------------------------
    def assign(self, row: dict, revision: str) -> str:
        code, basis = system_code(row.get("drawing_no", ""))
        seq = self.next_seq(code)
        ident = f"{code}-{seq:03d}"
        x, y = anchor(row)
        self.data["ids"][ident] = {
            "id": ident,
            "system_code": code,
            "system_code_basis": basis,
            "seq": seq,
            "first_revision": revision,
            "drawing_no": row.get("drawing_no", ""),
            "page_no": row.get("page_no"),
            "type": row.get("type", ""),
            "anchor": [round(x, 2), round(y, 2)],
            "description": (row.get("description") or ""),
            "status": "active",
            "history": [{"revision": revision, "state": ADDED,
                         "row_key": row.get("key", "")}],
        }
        return ident


BASELINE = "BASELINE"          # 비교 대상이 없다.  Rev.A 가 여기 해당한다


def _pairs_within(cur: list, recs: list, radius: float) -> list:
    """(현재 행, 장부 기록, 거리) 중 반경 안인 것.  같은 TYPE 끼리만 만든다."""
    out = []
    for i, row in enumerate(cur):
        ax, ay = anchor(row)
        for j, rec in enumerate(recs):
            if str(row.get("type") or "") != str(rec.get("type") or ""):
                continue                       # TYPE 게이트
            bx, by = rec.get("last_anchor") or rec["anchor"]
            d = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
            if d <= radius:
                out.append((d, i, j))
    return sorted(out)


def _match_one_drawing(cur: list, recs: list, radius: float) -> tuple[dict, dict]:
    """1:1 짝짓기.  상호 최근접을 먼저 확정하고 남은 것을 거리순으로 붙인다."""
    pairs = _pairs_within(cur, recs, radius)
    best_for_row: dict[int, int] = {}
    best_for_rec: dict[int, int] = {}
    for d, i, j in pairs:
        best_for_row.setdefault(i, j)
        best_for_rec.setdefault(j, i)
    taken_rows, taken_recs, matched = set(), set(), {}
    # 1) 서로가 서로의 최근접인 짝
    for i, j in best_for_row.items():
        if best_for_rec.get(j) == i:
            matched[i] = j
            taken_rows.add(i)
            taken_recs.add(j)
    # 2) 남은 것을 거리순으로.  이미 쓰인 쪽은 건너뛴다 (1:1 유지)
    for d, i, j in pairs:
        if i in taken_rows or j in taken_recs:
            continue
        matched[i] = j
        taken_rows.add(i)
        taken_recs.add(j)
    return matched, {j: i for i, j in matched.items()}


def _changed_fields(row: dict, rec: dict) -> list:
    """어느 칸이 바뀌었는지.  화면에 나가는 칸만 본다."""
    out = []
    snap = rec.get("values") or {}
    for f in COMPARED_FIELDS:
        was, now = snap.get(f), row.get(f)
        if (was or "") != (now or ""):
            out.append({"field": f, "was": was, "now": now})
    return out


def compare(rows: list, registry: "Registry", revision: str,
            *, compared_with: str = "", legend_bubble: float = None) -> dict:
    """현재 리비전의 행들을 장부와 맞추고 상태를 매긴다.

    비교 대상이 없으면(`compared_with` 가 비어 있으면) 모든 행이 BASELINE 이고
    어디에도 표기가 붙지 않는다.  Rev.A 가 그 경우다.

    장부의 `last_anchor` 와 맞춘다.  최초 `anchor` 는 부여 시점 기록으로 남기고
    바꾸지 않는다 — 매번 최초 좌표와 대면 개정이 거듭될수록 조금씩 밀려 반경을
    벗어나기 때문이다.
    """
    by_drawing: dict[str, list] = {}
    for r in rows:
        by_drawing.setdefault(r.get("drawing_no", ""), []).append(r)

    states, radii, deleted = {}, {}, []
    baseline = not compared_with

    for dwg in sorted(by_drawing):
        cur = sorted(by_drawing[dwg], key=sort_key)
        recs = sorted(registry.by_drawing(dwg), key=lambda r: r["seq"])
        info = match_radius(cur, legend_bubble)
        radii[dwg] = info
        matched, back = ({}, {}) if baseline else _match_one_drawing(
            cur, recs, info["radius"])

        for i, row in enumerate(cur):
            if i in matched:
                rec = recs[matched[i]]
                changed = _changed_fields(row, rec)
                state = MODIFIED if changed else UNCHANGED
                was = rec.get("last_anchor") or rec["anchor"]
                now = anchor(row)
                # 얼마나 움직였는지는 기록하되 상태로 삼지 않는다 — §설계 주석
                moved = round(((was[0] - now[0]) ** 2
                               + (was[1] - now[1]) ** 2) ** 0.5, 2)
                rec["last_anchor"] = [round(v, 2) for v in now]
                rec["values"] = {f: row.get(f) for f in COMPARED_FIELDS}
                rec["history"].append({"revision": revision, "state": state,
                                       "row_key": row.get("key", ""),
                                       "moved_pt": moved, "changed": changed})
                states[row["key"]] = {"id": rec["id"], "state": state,
                                      "moved_pt": moved, "changed": changed}
            else:
                ident = registry.assign(row, revision)
                rec = registry.data["ids"][ident]
                rec["last_anchor"] = list(rec["anchor"])
                rec["values"] = {f: row.get(f) for f in COMPARED_FIELDS}
                state = BASELINE if baseline else ADDED
                rec["history"][-1]["state"] = state
                states[row["key"]] = {"id": ident, "state": state, "changed": []}

        if baseline:
            continue
        for j, rec in enumerate(recs):
            if j in back:
                continue
            ax, ay = rec.get("last_anchor") or rec["anchor"]
            near = None
            for row in cur:
                if str(row.get("type") or "") != str(rec.get("type") or ""):
                    continue
                bx, by = anchor(row)
                d = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
                if near is None or d < near[0]:
                    near = (d, row.get("key", ""))
            rec["history"].append({"revision": revision,
                                   "state": DELETED_CANDIDATE})
            deleted.append({
                "id": rec["id"], "drawing_no": dwg, "page_no": rec.get("page_no"),
                "type": rec.get("type", ""), "description": rec.get("description", ""),
                # 산출물에서 원래 자리와 원래 번호를 지키기 위해 함께 옮긴다
                "tab": rec.get("tab") or "FIELD",
                "excel_no": rec.get("excel_no"),
                "values": dict(rec.get("values") or {}),
                # 근거: 이 셋이 있어야 사람이 '검출 실패' 와 '실제 삭제' 를 가른다
                "anchor": [round(ax, 2), round(ay, 2)],
                "radius": round(info["radius"], 2),
                "radius_source": info["source"],
                "nearest_distance": None if near is None else round(near[0], 2),
                "nearest_row_key": None if near is None else near[1],
                "confirmed": False,
            })

    return {"states": states, "deleted_candidates": deleted, "radii": radii,
            "compared_with": compared_with, "revision": revision,
            "baseline": baseline,
            "counts": {
                ADDED: sum(1 for s in states.values() if s["state"] == ADDED),
                MODIFIED: sum(1 for s in states.values() if s["state"] == MODIFIED),
                UNCHANGED: sum(1 for s in states.values() if s["state"] == UNCHANGED),
                BASELINE: sum(1 for s in states.values() if s["state"] == BASELINE),
                DELETED_CANDIDATE: len(deleted),
            }}


# --------------------------------------------------------------------------
# 프로젝트 저장소 — 사용자 PC 의 앱 데이터 디렉터리 안에만 산다
# --------------------------------------------------------------------------

REV_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def projects_root(data_dir: Path) -> Path:
    """`PID_DATA_DIR` 체계를 그대로 쓴다.

    exe 로 돌 때 이 뿌리는 **exe 옆 `pid_data/`** 이지 설치 디렉터리가 아니다
    (`app/paths.py`).  Program Files 밑이면 쓰기가 막히므로 그렇게 갈라 둔 것이고,
    프로젝트 저장도 같은 규칙을 따른다.  네트워크 경로는 쓰지 않는다.
    """
    return Path(data_dir) / "projects"


def list_projects(data_dir: Path) -> list:
    root = projects_root(data_dir)
    if not root.is_dir():
        return []
    out = []
    for d in sorted(root.iterdir()):
        meta = d / "project.json"
        if d.is_dir() and meta.exists():
            out.append(json.loads(meta.read_text(encoding="utf-8")))
    return out


def project_dir(data_dir: Path, name: str) -> Path:
    return projects_root(data_dir) / safe_name(name)


def load_project(data_dir: Path, name: str) -> dict:
    meta = project_dir(data_dir, name) / "project.json"
    if not meta.exists():
        raise KeyError(name)
    return json.loads(meta.read_text(encoding="utf-8"))


def create_project(data_dir: Path, name: str) -> dict:
    """Rev.A 를 여는 자리.  같은 이름이 있으면 덮어쓰지 않고 거절한다."""
    d = project_dir(data_dir, name)
    if (d / "project.json").exists():
        raise FileExistsError(safe_name(name))
    d.mkdir(parents=True, exist_ok=True)
    meta = {"name": safe_name(name), "revisions": []}
    _save_project(data_dir, meta)
    Registry({"version": 1, "project": meta["name"], "revisions": [], "ids": {}}
             ).save(d / "id_registry.json")
    return meta


def _save_project(data_dir: Path, meta: dict) -> None:
    d = project_dir(data_dir, meta["name"])
    d.mkdir(parents=True, exist_ok=True)
    (d / "project.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")


def next_revision(meta: dict) -> str:
    """다음 리비전 이름.  A 부터 순서대로, 건너뛰지 않는다."""
    n = len(meta.get("revisions") or [])
    if n >= len(REV_LETTERS):
        raise ValueError("리비전이 26개를 넘었습니다")
    return f"Rev.{REV_LETTERS[n]}"


def default_compare_target(meta: dict) -> str:
    """기본 비교 대상은 직전 리비전.  없으면 빈 문자열(비교 없음)."""
    revs = meta.get("revisions") or []
    return revs[-1]["revision"] if revs else ""


def compare_choices(meta: dict) -> list:
    """고를 수 있는 비교 대상.  이미 등록된 리비전 전부."""
    return [r["revision"] for r in (meta.get("revisions") or [])]


def record_revision(data_dir: Path, name: str, revision: str, *, job_id: str,
                    pdf_name: str, compared_with: str, result: dict) -> dict:
    """대조 결과를 프로젝트에 적어 넣는다."""
    meta = load_project(data_dir, name)
    entry = {"revision": revision, "job_id": job_id, "pdf_name": pdf_name,
             "compared_with": compared_with,
             "label": (f"{revision} vs {compared_with}" if compared_with
                       else f"{revision} (비교 대상 없음)"),
             "counts": result["counts"],
             "deleted_candidates": result["deleted_candidates"]}
    meta["revisions"] = [r for r in meta.get("revisions") or []
                         if r["revision"] != revision] + [entry]
    meta["revisions"].sort(key=lambda r: r["revision"])
    _save_project(data_dir, meta)
    return entry


# --------------------------------------------------------------------------
# Excel NO — ID 와 같은 원리로 단조 증가한다
# --------------------------------------------------------------------------

def excel_sort_key(row: dict) -> tuple:
    """산출물의 행 순서.  `excel_out.write_all` 이 쓰던 순서를 그대로 옮겼다.

    Rev.A 에서 이 순서로 NO 를 매기므로, 리비전을 쓰기 전과 쓴 뒤의 Rev.A
    산출물이 같은 순서·같은 번호를 갖는다.
    """
    return ((row.get("system") or ""), row.get("page_no") or 0,
            row.get("key") or "")


def assign_excel_numbers(rows: list, registry: "Registry") -> dict:
    """아직 번호가 없는 행에 그 산출물의 마지막 번호 + 1 을 준다.

    ID 와 같은 이유로 다시 매기지 않는다.  좌표순으로 매번 새로 매기면 도면
    가운데에 계기 하나가 들어올 때 뒤 번호가 전부 밀리고, 개정 대조가
    "1건 추가" 대신 "1건 추가 + 40건 수정" 으로 나온다.  삭제된 번호도
    회수하지 않는다 — 그 번호는 그 행의 이름이다.
    """
    tops: dict[str, int] = {}
    for rec in registry.data["ids"].values():
        t = rec.get("tab") or ""
        if rec.get("excel_no"):
            tops[t] = max(tops.get(t, 0), int(rec["excel_no"]))
    out = {}
    for row in sorted(rows, key=excel_sort_key):
        ident = row.get("stable_id")
        rec = registry.data["ids"].get(ident) if ident else None
        if rec is None:
            continue
        rec.setdefault("tab", row.get("tab") or "")
        if not rec.get("excel_no"):
            t = rec["tab"]
            tops[t] = tops.get(t, 0) + 1
            rec["excel_no"] = tops[t]
        out[row["key"]] = rec["excel_no"]
    return out
