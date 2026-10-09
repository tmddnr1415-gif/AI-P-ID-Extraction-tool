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
물드는 쪽이 더 나쁘다.  움직인 거리는 `moved_pt` 로 이력과 상태에 **기록만**
한다.  근거 패널에서 보이므로 사람이 판단할 수 있다.

**hotfix43 — 개정의 변경은 태그로만 센다** (사용자 확정: *"위치변경이 아니라,
tag number 변경 또는 기존에 없었던 tag 가 추가되었거나 삭제되었을 때만 수정사항으로
간주한다"*).  hotfix38 까지는 `COMPARED_FIELDS` 어느 칸이든 다르면 '수정' 이었고,
QFE 실측에서 수정 458 중 411 이 Description **재생성**이었다 — 도면이 바뀐 것이
아니라 우리 문장이 바뀐 것이다.  이제 `MODIFIED` 는 **`tag_no` 가 달라졌을 때만**
이고(빈칸 → 태그도 포함한다 — 없던 태그가 생긴 것), `ADDED`·`DELETED_CANDIDATE` 는
전처럼 짝이 안 선 행·기록이다.  그 밖의 칸(수량 · SCOPE · Description …)이 다른
것은 `field_diffs` 로 **기록만** 하고 상태에 쓰지 않는다 — 근거 패널이 *"값이
다른 칸 (개정 판정에는 쓰지 않음)"* 으로 보인다.  이 판단은 뒤집을 수 있게
`_revision_state` 한 곳에 모여 있다.

**삭제는 여기서 확정하지 않는다.**  검출 실패와 실제 삭제는 구분되지 않는다 —
계기가 도면에 그대로 있는데 우리가 그 장에서 못 뽑으면 똑같이 매칭 실패로
보인다.  그래서 판정은 `DELETED_CANDIDATE` 까지이고, 사람이 확인해야 굳는다.
"""

from __future__ import annotations

import json
import time
import re
from datetime import datetime, timezone
import unicodedata
from pathlib import Path

# 상태.  문자열은 화면·산출물·저장 파일이 같은 낱말을 쓰도록 한 곳에 둔다.
UNCHANGED = "UNCHANGED"
ADDED = "ADDED"
MODIFIED = "MODIFIED"
DELETED_CANDIDATE = "DELETED_CANDIDATE"
DELETED = "DELETED"
# hotfix46 — 대조하지 않은 행.  태그가 없어(또는 입찰 프로젝트라) 짝지을 열쇠가 없는 행 —
# 추가도 삭제도 아니다.  위치로는 비교하지 않는다 (사용자 확정).
NOT_COMPARED = "NOT_COMPARED"
# hotfix47 — 짝의 근거.  TAG = 같은 (TYPE, 태그) · TYPE = 같은 도면에서 그 TYPE 의 짝 없는
# 행과 기록이 **하나씩**이라 태그가 바뀐 것으로 이은 짝 · AMBIGUOUS = 같은 도면에 짝 없는
# 태그가 양쪽에 남아 태그 변경인지 추가/삭제인지 도면이 가르지 않는 것 (변경으로만 표기).
BASIS_TAG = "TAG"
BASIS_TYPE = "TYPE"
BASIS_AMBIGUOUS = "AMBIGUOUS"

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

    1순위는 **그 도면 자신의 버블 크기**다.  버블 사각형은 캡의 모양(`cap_ratio`)과
    옆면(`side_slack`)의 짝짓기를 통과한 것만 남은 것이므로(크기 창은 37회차에 지웠다), 그 긴변은
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


def registry_snapshot_path(reg_path: Path, revision: str) -> Path:
    """그 리비전을 **처음 대조하기 전**의 장부 사본 자리 (hotfix38).

    `id_registry.json` 옆에 `id_registry.before_Rev.B.json` 꼴로 둔다.  같은
    리비전을 다시 대조할 때 여기서 시작해야 직전 대조가 만든 ID 가 "변경 없음"
    으로 둔갑하지 않는다.  리비전 이름은 `safe_name` 과 같은 글자 규칙을 지난다.
    """
    tag = "".join(c if c.isalnum() or c in "._-" else "_" for c in (revision or "none"))
    return reg_path.with_name(f"id_registry.before_{tag}.json")


def _tag_key(type_, tag):
    """태그 짝의 열쇠.  hotfix35 — 한 루프의 PI 와 PIT 는 **같은 태그**를 들므로
    태그만으로는 둘이 갈리지 않고 TYPE 을 함께 본다.  태그가 비면 열쇠가 없다."""
    tag = str(tag or "").strip()
    return (str(type_ or ""), tag) if tag else None


def _tag_matches(cur: list, recs: list) -> tuple[dict, dict]:
    """태그가 곧 이름이다 (§10 1급 · hotfix38).  **대조의 열쇠는 이것 하나다** (hotfix46).

    규칙: **그 도면 안에서 (TYPE, 태그) 가 현재 행에도 장부에도 정확히 하나씩**일 때만
    짝이다.  거리는 보지 않는다 — 심볼이 종이 한 장을 가로질러 옮겨 가도 같은 태그면
    같은 항목이고, 그 거리는 `moved_pt` 로 기록만 된다.  TYPE 을 함께 보는 이유는
    hotfix35 — 한 루프의 PI 와 PIT 가 **같은 태그**를 든다 (사용자: *"동일 tag 와
    abbreviation 기준"*).

    같은 (TYPE, 태그) 가 둘 이상이면(한 태그를 여러 버블에 찍는 문서 — UAD p30) 어느
    것이 어느 것인지 도면이 말하지 않으므로 **대조하지 않는다** — hotfix38 까지는 기하로
    넘겼지만 hotfix46 부터 위치로는 비교하지 않는다 (사용자 확정).
    """
    def count(items, get):
        seen: dict = {}
        for idx, it in enumerate(items):
            k = get(it)
            if k:
                seen.setdefault(k, []).append(idx)
        return seen
    rows_by = count(cur, lambda r: _tag_key(r.get("type"), r.get("tag_no")))
    recs_by = count(recs, lambda r: _tag_key(
        r.get("type"), (r.get("values") or {}).get("tag_no")))
    matched: dict[int, int] = {}
    dup = {"rows": sorted(k for k, v in rows_by.items() if len(v) > 1),
           "recs": sorted(k for k, v in recs_by.items() if len(v) > 1)}
    for k, ii in rows_by.items():
        jj = recs_by.get(k)
        if len(ii) == 1 and jj and len(jj) == 1:
            matched[ii[0]] = jj[0]
    return matched, dup


def _match_one_drawing(cur: list, recs: list) -> tuple[dict, dict, dict]:
    """1:1 짝짓기 — **태그로만** (hotfix46).

    hotfix38 의 세 단계(태그 → 상호 최근접 → 거리순 → 태그가 다른 쌍)에서 기하 둘을
    뺐다.  사용자 확정: *"나란히 대조는 실행 프로젝트만 해당되며 tag 위주로 비교한다.
    동일 tag 와 abbreviation 기준.  PDF 상의 위치 좌표로는 비교하지 않는다."*
    그래서 같은 자리에 번호만 다시 매긴 심볼은 "수정" 이 아니라 **삭제 후보 + 추가**다 —
    같은 항목이라는 것을 도면이 태그로 말하지 않았기 때문이다.

    셋째 값은 근거 — 행마다 `basis`(전부 TAG) · 태그가 겹쳐 대조하지 않은 열쇠.
    """
    matched, dup = _tag_matches(cur, recs)
    basis = {i: "TAG" for i in matched}
    evidence = {"basis": basis, "tag_changed": [], "tag_duplicates": dup}
    return matched, {j: i for i, j in matched.items()}, evidence


def _sheet_tags(rows: list) -> set:
    return {(str(r.get("type") or ""), str(r.get("tag_no") or "").strip())
            for r in rows if str(r.get("tag_no") or "").strip()}


def pair_renumbered_sheets(by_drawing: dict, registry: "Registry") -> dict:
    """hotfix38 — **도면번호가 바뀐 장**을 태그로 알아본다.

    QFE 실측: 260112 의 `30GKC10-M05-0001~0003` 이 260326 에서 `…-0201~0203` 이
    됐다 (같은 제목 · 태그 17/22 · 18/19 · 13/47 공유).  도면번호로만 묶으면 그
    세 장의 행 전부가 "삭제 + 추가" 가 된다 — 장이 통째로 사라졌다는 거짓말이다.

    규칙: 장부에만 있는 도면번호 ↔ 이번 분석에만 있는 도면번호 사이에서, 공유하는
    (TYPE, 태그) 가 **둘 이상이고 작은 쪽 집합의 절반 이상**이며 서로가 서로의
    최선일 때만 같은 장으로 본다.  태그가 없는 장(`…-0004` ↔ `…-0204` · 공유 0)은
    짝짓지 않는다 — 제목이 같아도 네 장이 다 같은 제목이라 근거가 못 된다.
    돌려주는 것: {옛 도면번호: {"now", "shared", "before_tags", "now_tags"}}.
    """
    reg_drawings = {}
    for rec in registry.data["ids"].values():
        if rec.get("status") != "active":
            continue
        tag = str((rec.get("values") or {}).get("tag_no") or "").strip()
        if tag:
            reg_drawings.setdefault(rec["drawing_no"], set()).add(
                (str(rec.get("type") or ""), tag))
        else:
            reg_drawings.setdefault(rec["drawing_no"], set())
    only_before = {d: t for d, t in reg_drawings.items() if d not in by_drawing}
    only_now = {d: _sheet_tags(rows) for d, rows in by_drawing.items()
                if d not in reg_drawings}
    if not only_before or not only_now:
        return {}

    def best(src, pool):
        scored = sorted(((len(src & t), d) for d, t in pool.items()), reverse=True)
        return scored[0] if scored and scored[0][0] else None

    out = {}
    for old, ta in only_before.items():
        b = best(ta, only_now)
        if not b:
            continue
        shared, new = b
        tb = only_now[new]
        # 둘 이상 — 태그 하나가 다른 장으로 옮겨 간 것은 장이 바뀐 것이 아니다
        if shared < 2 or shared < 0.5 * min(len(ta), len(tb)):
            continue
        back = best(tb, only_before)
        if not back or back[1] != old:
            continue
        out[old] = {"now": new, "shared": shared,
                    "before_tags": len(ta), "now_tags": len(tb)}
    return out


# 개정 상태를 가르는 칸.  hotfix43 — 태그 하나다.  이 튜플에 칸을 더하면
# 그 칸이 다른 행이 '수정' 이 된다 (hotfix38 까지는 COMPARED_FIELDS 전부였다).
STATE_FIELDS = ("tag_no",)


def _changed_fields(row: dict, rec: dict) -> list:
    """어느 칸이 다른지.  화면에 나가는 칸만 본다 — 기록용이고 상태는 아니다."""
    out = []
    snap = rec.get("values") or {}
    for f in COMPARED_FIELDS:
        was, now = snap.get(f), row.get(f)
        if (was or "") != (now or ""):
            out.append({"field": f, "was": was, "now": now})
    return out


def _revision_state(diffs: list) -> tuple[str, list, list]:
    """(상태, 상태를 정한 칸, 그 밖에 값이 다른 칸).

    **태그가 달라졌을 때만 `MODIFIED`** 다 (hotfix43).  빈칸 → 태그(없던 태그가
    생김)도 태그가 달라진 것이다.  나머지 칸은 `field_diffs` 로 돌려주고 상태에
    쓰지 않는다 — 수량·SCOPE·Description 은 도면이 아니라 우리 판정이 바뀌어도
    달라지는 칸이라, 그것으로 '수정' 을 세면 개정이 아닌 것이 개정으로 보인다.
    """
    changed = [c for c in diffs if c["field"] in STATE_FIELDS]
    others = [c for c in diffs if c["field"] not in STATE_FIELDS]
    return (MODIFIED if changed else UNCHANGED), changed, others


def compare(rows: list, registry: "Registry", revision: str,
            *, compared_with: str = "", legend_bubble: float = None,
            tagged: bool = True) -> dict:
    """현재 리비전의 행들을 장부와 맞추고 상태를 매긴다.

    비교 대상이 없으면(`compared_with` 가 비어 있으면) 모든 행이 BASELINE 이고
    어디에도 표기가 붙지 않는다.  Rev.A 가 그 경우다.

    hotfix46 — **대조의 열쇠는 (TYPE, 태그) 하나다.  위치로는 비교하지 않는다.**
    `tagged` 는 이 프로젝트가 실행(태그가 곧 이름)인가 — `_mode_facts` 의 `effective`
    가 `epc` 일 때다.  입찰 프로젝트(`tagged=False`)는 태그가 없어 대조할 열쇠가 없으므로
    **대조하지 않는다** — 모든 행이 `NOT_COMPARED` 이고 추가·삭제 후보가 서지 않는다.
    실행 프로젝트에서도 태그 없는 행(Typical 상세 · 태그 안 찍힌 밸브)과 같은 태그가 둘
    이상인 행은 `NOT_COMPARED` 다 — 위치로 짝지으면 그것이 곧 위치 비교다.
    `legend_bubble` 은 호환을 위해 남겼고 쓰지 않는다 (반경이 더 이상 없다).

    짝지은 기록의 `last_anchor` 는 **기록**으로만 갱신한다 (화면이 이전 자리에 MOD 고리를
    그리는 데 쓴다) — 판정에는 쓰지 않는다.
    """
    by_drawing: dict[str, list] = {}
    for r in rows:
        by_drawing.setdefault(r.get("drawing_no", ""), []).append(r)

    states, radii, deleted = {}, {}, []
    baseline = not compared_with
    # hotfix38 — 장부에만 있는 도면도 돈다.  이번 분석에 그 도면의 행이 **하나도**
    # 없으면(장이 빠졌거나 못 읽었거나) 예전 코드는 그 도면을 아예 안 보아 기록이
    # 삭제 후보로 올라오지 않았다 — 통째로 빠진 장이 조용히 사라지는 길이었다.
    sheets = {"renumbered": [], "only_before": [], "only_now": []}
    if not baseline:
        # 도면번호가 바뀐 장 — 그 장의 기록을 새 번호 아래로 옮긴다.  안정 ID 는
        # 그대로다 (계통코드가 같으면 번호도 같다 · 바뀌어도 ID 는 재부여하지 않는다).
        # 짝은 공유 태그로 짓는다 — 입찰 프로젝트에는 태그가 없어 아무 장도 안 짝지어진다.
        for old, info in sorted(pair_renumbered_sheets(by_drawing, registry).items()):
            for rec in registry.data["ids"].values():
                if rec.get("status") == "active" and rec["drawing_no"] == old:
                    rec["drawing_no"] = info["now"]
                    rec.setdefault("renumbered", []).append(
                        {"revision": revision, "from": old, "to": info["now"]})
            sheets["renumbered"].append(dict(info, before=old))
        reg_drawings = {rec["drawing_no"] for rec in registry.data["ids"].values()
                        if rec.get("status") == "active"}
        sheets["only_before"] = sorted(reg_drawings - set(by_drawing))
        sheets["only_now"] = sorted(set(by_drawing) - reg_drawings)
    renamed = {e["now"]: e["before"] for e in sheets["renumbered"]}
    drawings = set(by_drawing)
    if not baseline:
        drawings |= {rec["drawing_no"] for rec in registry.data["ids"].values()
                     if rec.get("status") == "active"}
    compare_now = (not baseline) and tagged

    for dwg in sorted(drawings):
        cur = sorted(by_drawing.get(dwg, []), key=sort_key)
        recs = sorted(registry.by_drawing(dwg), key=lambda r: r["seq"])
        info: dict = {"basis": "TAG" if tagged else "NONE"}
        radii[dwg] = info
        matched, back, how = (_match_one_drawing(cur, recs) if compare_now else
                              ({}, {}, {"basis": {}, "tag_changed": [],
                                        "tag_duplicates": {"rows": [], "recs": []}}))
        info["tag_changed"] = how["tag_changed"]
        info["tag_duplicates"] = how["tag_duplicates"]
        if dwg in renamed:
            info["renumbered_from"] = renamed[dwg]
        dup_rows = set(how["tag_duplicates"]["rows"])
        # 어느 길로 짝지었는지 · 대조하지 않은 행 수 — 태그가 있는 문서에서 이 수가
        # 곧 "이 대조가 무엇을 덮는가" 다.  GEOMETRY 는 hotfix46 부터 언제나 0 이다.
        info["matched_by"] = {"TAG": len(how["basis"]), "GEOMETRY": 0, "NOT_COMPARED": 0}
        dup_recs = set(how["tag_duplicates"]["recs"])
        left_rows, left_recs, pairs, ambiguous = _leftovers(cur, recs, matched, back,
                                                            dup_rows, dup_recs, compare_now)
        info["ambiguous"] = ambiguous
        info["type_pairs"] = len(pairs)

        for i, row in enumerate(cur):
            tag = str(row.get("tag_no") or "").strip()
            if i in matched or i in pairs:
                rec = recs[matched[i] if i in matched else pairs[i]]
                state, changed, others = _revision_state(_changed_fields(row, rec))
                was = rec.get("last_anchor") or rec["anchor"]
                now = anchor(row)
                # 얼마나 움직였는지는 기록하되 상태로 삼지 않는다 — §설계 주석
                moved = round(((was[0] - now[0]) ** 2
                               + (was[1] - now[1]) ** 2) ** 0.5, 2)
                rec["last_anchor"] = [round(v, 2) for v in now]
                rec["values"] = {f: row.get(f) for f in COMPARED_FIELDS}
                basis = how["basis"].get(i, BASIS_TAG) if i in matched else BASIS_TYPE
                rec["history"].append({"revision": revision, "state": state,
                                       "row_key": row.get("key", ""),
                                       "moved_pt": moved, "changed": changed,
                                       "field_diffs": others, "basis": basis})
                states[row["key"]] = {"id": rec["id"], "state": state,
                                      "moved_pt": moved, "changed": changed,
                                      "field_diffs": others, "basis": basis}
                if i in pairs:
                    # hotfix47 — 같은 도면에서 그 TYPE 의 짝 없는 행·기록이 하나씩 — 태그가
                    # 바뀐 한 항목으로 잇는다 (안정 ID 그대로).  위치는 보지 않았다.
                    was_tag = next((c.get("was") for c in changed
                                    if isinstance(c, dict) and c.get("field") == "tag_no"), "")
                    states[row["key"]]["reason"] = (
                        f"변경 — 같은 도면의 유일한 {row.get('type') or ''} 끼리 짝 "
                        f"(태그 {was_tag or '(없음)'} → {tag or '(없음)'}) — 위치는 보지 않음")
                if dwg in renamed:
                    states[row["key"]]["sheet_renumbered_from"] = renamed[dwg]
                continue
            ident = registry.assign(row, revision)
            rec = registry.data["ids"][ident]
            rec["last_anchor"] = list(rec["anchor"])
            rec["values"] = {f: row.get(f) for f in COMPARED_FIELDS}
            if baseline:
                state, reason, basis = BASELINE, "", ("TAG" if tag else "NONE")
            elif not tagged:
                state, basis = NOT_COMPARED, "NONE"
                reason = "입찰 프로젝트 — 태그가 없어 대조하지 않음 (위치로는 비교하지 않는다)"
                info["matched_by"]["NOT_COMPARED"] += 1
            elif not tag:
                state, basis = NOT_COMPARED, "NONE"
                reason = "태그 없음 — 대조하지 않음 (위치로는 비교하지 않는다)"
                info["matched_by"]["NOT_COMPARED"] += 1
            elif _tag_key(row.get("type"), tag) in dup_rows:
                state, basis = NOT_COMPARED, "NONE"
                reason = (f"같은 태그 {tag} ({row.get('type') or ''}) 가 이 도면에 둘 이상 — "
                          f"어느 것인지 도면이 말하지 않아 대조하지 않음")
                info["matched_by"]["NOT_COMPARED"] += 1
            elif ambiguous:
                # hotfix47 — 같은 도면에 짝 없는 태그가 양쪽에 남았다.  태그가 바뀐 것인지
                # 지워지고 새로 선 것인지 도면이 가르지 않으므로 **변경(MOD)으로만** 표기한다
                # (사용자: "태그 변경인지, 삭제 추가인지 확인이 어려우니 모두 MOD").
                state, basis = MODIFIED, BASIS_AMBIGUOUS
                gone = [str((recs[j].get("values") or {}).get("tag_no") or "")
                        for j in left_recs if j not in pairs.values()]
                # 같은 태그를 든 사라진 기록이 있으면(TYPE 만 다름) 그 사실도 적는다 — 표기
                # (abbreviation)가 바뀐 것일 수 있다.  고르지는 않는다 (TYPE 이 다르면 다른 항목).
                same = sorted({str(recs[j].get("type") or "") for j in left_recs
                               if j not in pairs.values()
                               and str((recs[j].get("values") or {}).get("tag_no") or "").strip() == tag})
                reason = (f"변경 — 태그 {tag} ({row.get('type') or ''}) 는 {compared_with} 장부에 없고, "
                          f"같은 도면에서 태그 {len(gone)}개가 사라졌습니다 ({', '.join(gone)}) — "
                          f"태그 변경인지 추가인지 도면이 가르지 않아 변경으로만 표기"
                          + (f" · 같은 태그가 {compared_with} 에서는 {'/'.join(same)} 로 있었습니다 (표기가 바뀐 것일 수 있음)"
                             if same else ""))
            else:
                state, basis = ADDED, BASIS_TAG
                reason = f"태그 {tag} ({row.get('type') or ''}) 가 {compared_with} 장부에 없음"
            rec["history"][-1]["state"] = state
            states[row["key"]] = {"id": ident, "state": state, "changed": [],
                                  "basis": basis, "reason": reason}

        if not compare_now:
            continue
        # 삭제 후보 — **태그가 있던 기록**이 이번 분석에서 짝이 없을 때만.  태그 없던
        # 기록은 대조할 열쇠가 없으므로 삭제 후보가 아니다 (위치로는 비교하지 않는다).
        paired_recs = set(pairs.values())
        new_tags = [str(cur[i].get("tag_no") or "").strip() for i in left_rows if i not in pairs]
        for j, rec in enumerate(recs):
            if j in back or j in paired_recs:
                continue
            tag = str((rec.get("values") or {}).get("tag_no") or "").strip()
            if not tag or _tag_key(rec.get("type"), tag) in dup_recs:
                continue
            ax, ay = rec.get("last_anchor") or rec["anchor"]
            # hotfix47 — 같은 도면에 새 태그도 섰으면 삭제 후보가 아니라 **변경(이전 태그)** 다.
            # 태그 변경인지 삭제인지 도면이 가르지 않는다.  사람이 '삭제로 확정' 할 수는 있다.
            rec_state = MODIFIED if ambiguous else DELETED_CANDIDATE
            rec["history"].append({"revision": revision, "state": rec_state,
                                   **({"ambiguous": True} if ambiguous else {})})
            # 그 태그가 이번 분석의 **어디에도** 없는지를 적는다 — 다른 도면에 같은
            # 태그가 섰으면 삭제가 아니라 옮김일 수 있다.
            elsewhere = sorted({r.get("drawing_no", "") for r in rows
                                if str(r.get("tag_no") or "").strip() == tag
                                and r.get("drawing_no", "") != dwg})
            deleted.append({
                "id": rec["id"], "drawing_no": dwg, "page_no": rec.get("page_no"),
                "type": rec.get("type", ""), "description": rec.get("description", ""),
                "tag_no": tag,
                "basis": BASIS_AMBIGUOUS if ambiguous else BASIS_TAG,
                "state": rec_state,
                "ambiguous": ambiguous,
                # 같은 도면에서 새로 선(짝 없는) 태그 — 이 기록의 태그가 그중 하나로 바뀐
                # 것일 수 있다.  고르지 않고 목록으로만 둔다 (위치로 고르면 위치 비교다).
                "tag_candidates": new_tags if ambiguous else [],
                # 같은 태그를 든 새 행의 TYPE (표기만 바뀐 것일 수 있다 · 고르지 않는다)
                "same_tag_now": sorted({str(cur[i].get("type") or "") for i in left_rows
                                        if i not in pairs and str(cur[i].get("tag_no") or "").strip() == tag})
                                if ambiguous else [],
                "tag_elsewhere": elsewhere,
                # 산출물에서 원래 자리와 원래 번호를 지키기 위해 함께 옮긴다
                "tab": rec.get("tab") or "FIELD",
                "excel_no": rec.get("excel_no"),
                "values": dict(rec.get("values") or {}),
                # 직전 리비전의 자리 — 화면이 이전 도면 위에 표식을 그리는 데 쓴다 (판정 아님)
                "anchor": [round(ax, 2), round(ay, 2)],
                "confirmed": False,
            })

    return {"states": states, "deleted_candidates": deleted, "radii": radii,
            "compared_with": compared_with, "revision": revision,
            "baseline": baseline, "sheets": sheets,
            "basis": "TAG" if tagged else "NONE",
            "counts": {
                ADDED: sum(1 for s in states.values() if s["state"] == ADDED),
                MODIFIED: sum(1 for s in states.values() if s["state"] == MODIFIED),
                UNCHANGED: sum(1 for s in states.values() if s["state"] == UNCHANGED),
                BASELINE: sum(1 for s in states.values() if s["state"] == BASELINE),
                NOT_COMPARED: sum(1 for s in states.values() if s["state"] == NOT_COMPARED),
                DELETED_CANDIDATE: sum(1 for d in deleted if d["state"] == DELETED_CANDIDATE),
                # hotfix47 — 변경(이전 태그): 짝 없는 기록인데 같은 도면에 새 태그가 서서
                # 삭제 후보가 아니라 변경으로 표기한 것
                "MODIFIED_BEFORE": sum(1 for d in deleted if d["state"] == MODIFIED),
            }}


def _leftovers(cur: list, recs: list, matched: dict, back: dict,
               dup_rows: set, dup_recs: set, compare_now: bool):
    """hotfix47 — 한 도면에서 (TYPE, 태그)로 짝이 안 선 **태그 있는** 행·기록.

    둘 다 남아 있으면 이 도면은 `ambiguous` 다 — 태그가 바뀐 것인지, 지워지고 새로 선
    것인지 도면이 가르지 않는다 (사용자: *"tag 변경인지, 삭제 추가인지 확인이 어려우니
    이런 사항들은 모두 MOD 로 변경으로만 표기한다"*).  한쪽만 남으면 뜻이 하나뿐이라
    (사라진 태그가 없는데 새 태그 = 추가 · 새 태그가 없는데 사라진 태그 = 삭제 후보)
    예전 그대로다.

    `pairs` 는 그 도면에서 **같은 TYPE 의 짝 없는 행과 기록이 정확히 하나씩**일 때만
    잇는다 — 태그가 바뀐 한 항목(안정 ID 유지).  둘 이상이면 어느 것이 어느 것인지
    도면이 말하지 않으므로 잇지 않는다.  **위치는 어디서도 보지 않는다.**
    """
    if not compare_now:
        return [], [], {}, False
    left_rows = [i for i, r in enumerate(cur)
                 if i not in matched and str(r.get("tag_no") or "").strip()
                 and _tag_key(r.get("type"), str(r.get("tag_no") or "").strip()) not in dup_rows]
    left_recs = [j for j, rec in enumerate(recs)
                 if j not in back and str((rec.get("values") or {}).get("tag_no") or "").strip()
                 and _tag_key(rec.get("type"), str((rec.get("values") or {}).get("tag_no") or "").strip())
                 not in dup_recs]
    ambiguous = bool(left_rows) and bool(left_recs)
    pairs: dict[int, int] = {}
    if ambiguous:
        by_type_rows: dict[str, list] = {}
        by_type_recs: dict[str, list] = {}
        for i in left_rows:
            by_type_rows.setdefault(str(cur[i].get("type") or ""), []).append(i)
        for j in left_recs:
            by_type_recs.setdefault(str(recs[j].get("type") or ""), []).append(j)
        for t, ii in by_type_rows.items():
            jj = by_type_recs.get(t) or []
            if len(ii) == 1 and len(jj) == 1:
                pairs[ii[0]] = jj[0]
    return left_rows, left_recs, pairs, ambiguous


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


DELETED_DIR = "_deleted"


def tombstones(data_dir: Path, name: str) -> list:
    """그 이름으로 지워진 프로젝트의 **안정 ID 장부** 무덤들 (최신 순).

    프로젝트를 지워도 장부는 남긴다 — §7.3 이 "Rev.A 에서 한 번만 부여하고
    회수하지 않는다" 이므로, 같은 이름으로 다시 만든 프로젝트가 번호를 1부터
    다시 내면 이미 발주처에 나간 산출물과 번호가 겹친다.  무덤은 `project.json`
    을 갖지 않으므로 `list_projects` 에 보이지 않는다(첫 화면에서 사라진다).
    """
    root = projects_root(Path(data_dir)) / DELETED_DIR
    if not root.is_dir():
        return []
    pre = safe_name(name) + "-"
    out = [d for d in root.iterdir()
           if d.is_dir() and d.name.startswith(pre)
           and (d / "id_registry.json").exists()]
    return sorted(out, key=lambda d: d.name, reverse=True)


def create_project(data_dir: Path, name: str) -> dict:
    """Rev.A 를 여는 자리.  같은 이름이 있으면 덮어쓰지 않고 거절한다."""
    d = project_dir(data_dir, name)
    if (d / "project.json").exists():
        raise FileExistsError(safe_name(name))
    d.mkdir(parents=True, exist_ok=True)
    meta = {"name": safe_name(name), "revisions": []}
    _save_project(data_dir, meta)
    # 같은 이름이 지워진 적이 있으면 **그 장부를 이어받는다** (§7.3).
    # 값을 지어내지 않는다 — 지울 때 그대로 옮겨 둔 파일을 그대로 읽는다.
    old = tombstones(data_dir, name)
    reg = (Registry.load(old[0] / "id_registry.json") if old
           else Registry({"version": 1, "project": meta["name"],
                          "revisions": [], "ids": {}}))
    reg.data["project"] = meta["name"]
    if old:
        reg.data.setdefault("inherited_from", []).append(old[0].name)
    reg.save(d / "id_registry.json")
    return meta


def bury_project(data_dir: Path, name: str, *, author: str = "", at: str = "") -> dict:
    """프로젝트 폴더를 지우되 **안정 ID 장부만 무덤으로 옮긴다**.

    되돌릴 수 없다.  무엇을 옮겼는지·누가 지웠는지를 무덤에 함께 적는다.
    """
    import shutil
    d = project_dir(data_dir, name)
    if not d.is_dir():
        return {"buried": False, "reason": "그 이름의 프로젝트 폴더가 없습니다"}
    stamp = at or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    grave = projects_root(Path(data_dir)) / DELETED_DIR / f"{safe_name(name)}-{stamp}"
    grave.mkdir(parents=True, exist_ok=True)
    kept = []
    reg = d / "id_registry.json"
    if reg.exists():
        shutil.copy2(reg, grave / "id_registry.json")
        kept.append("id_registry.json")
    (grave / "deleted.json").write_text(json.dumps(
        {"project": safe_name(name), "deleted_at": stamp,
         "author": author or "", "kept": kept,
         "why": "안정 ID 는 회수하지 않는다 (§7.3) — 같은 이름으로 다시 만들면 "
                "이 장부를 이어받는다"},
        ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    removed = sorted(p.name for p in d.iterdir())
    shutil.rmtree(d)
    return {"buried": True, "grave": str(grave), "kept": kept, "removed": removed}


# 38회차 — 입찰 / 실행 선언.  §10 증거 등급을 **사람이 미리 말하는 것**이다.
#   bid  입찰 — 태그가 인쇄되지 않은 도면.  1급(태그) 경로를 끈다.
#   epc  실행 — 태그가 인쇄된 도면.  1급 + 2급을 함께 쓴다.
#   ""   선언 없음 — 도면 실측(`tags.assign`)이 정한다.
# 선언은 기대값이고 실측이 사실이다.  둘이 다르면 파이프라인이 `evidence_tier`
# 에 그 사실을 적고 화면이 말한다 — 조용히 덮지 않는다.
MODES = ("bid", "epc")


def set_mode(data_dir: Path, name: str, mode: str, author: str) -> dict:
    """프로젝트의 입찰/실행 선언.  `mode=""` 는 선언을 지운다(자동 판정)."""
    mode = (mode or "").strip().lower()
    if mode and mode not in MODES:
        raise ValueError(f"mode 는 {MODES} 중 하나이거나 비워야 합니다: {mode!r}")
    meta = load_project(data_dir, name)
    if mode:
        meta["mode"] = {"value": mode, "author": (author or "").strip(),
                        "set_at": time.time()}
    else:
        meta.pop("mode", None)
    _save_project(data_dir, meta)
    return meta


def declared_mode(meta: dict | None) -> str:
    """선언된 모드 문자열 (`bid` · `epc` · 없으면 `""`)."""
    m = (meta or {}).get("mode") or {}
    return str(m.get("value") or "") if isinstance(m, dict) else ""


def _save_project(data_dir: Path, meta: dict) -> None:
    d = project_dir(data_dir, meta["name"])
    d.mkdir(parents=True, exist_ok=True)
    (d / "project.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")


# 문서 대표 개정 — 장마다 다른 Rev 를 하나로 접는 규칙 (13회차).
#
# **이 규칙은 도면에서 유도되지 않는다.**  AL NOUF1 58장을 세 후보로 재면 답이
# 갈린다: 사전순 최댓값 `D`(1장) · 최빈값 `B`(19장) · 1쪽 도면목록 `B`.
# rev_date 는 9장에만 있고 가장 늦은 날짜(24.NOV.2025)에 C 3장과 D 1장이 섞여
# 갈라지지 않는다.  그래서 셋 다 근거가 되지 못하고, **사용자가 실무 기준으로
# `max`(가장 앞서간 장이 문서 Rev)를 확정했다.**  프로젝트마다 다를 수 있으므로
# config `revision.document_rule` 로 갈아 끼운다 - 코드에 박지 않는다.
#
# 사전순 비교가 개정 순서와 같은 것은 형식이 `^[A-Z][0-9]?$` 이기 때문이다:
# A < A1 < B < C < D.  형식이 다른 문서에서는 이 함수가 정렬을 바꿔야 한다.
DOC_REV_RULES = ("max", "mode", "first_sheet")


def document_revision(pages: list, rule: str = "max") -> dict:
    """장별 Rev 를 문서 하나로 접는다.  접은 값과 **접기 전 분포**를 함께 준다.

    분포를 같이 돌려주는 이유는, 대표값 하나만 보이면 "53장 중 3장만 C" 라는
    사실이 사라지기 때문이다.  화면은 둘 다 적는다.
    """
    pid = [p for p in pages if (p.get("page_kind") or "") == "PID"]
    seen = [str(p.get("rev") or "").strip() for p in (pid or pages)]
    revs = [r for r in seen if r]
    dist = {}
    for r in revs:
        dist[r] = dist.get(r, 0) + 1
    out = {"rule": rule, "sheets": len(pid or pages), "read": len(revs),
           "unread": len(seen) - len(revs), "distribution": dist}
    if not revs:
        out["rev"] = ""
        out["why"] = "어느 장에서도 개정을 읽지 못했습니다"
        return out
    if rule == "mode":
        out["rev"] = max(sorted(dist), key=lambda r: (dist[r], r))
        out["why"] = f"가장 많은 장의 개정 ({dist[out['rev']]}/{len(revs)}장)"
    elif rule == "first_sheet":
        first = sorted(pages, key=lambda p: p.get("page_no") or 0)
        got = [str(p.get("rev") or "").strip() for p in first
               if str(p.get("rev") or "").strip()]
        out["rev"] = got[0] if got else ""
        out["why"] = "첫 장의 개정"
    else:
        out["rev"] = max(revs)
        out["why"] = (f"가장 앞서간 장의 개정 ({dist[out['rev']]}/{len(revs)}장이 "
                      f"{out['rev']})")
    return out


def compare_document_revision(now: str, before: str, *, now_date: str = "",
                              before_date: str = "", order=()) -> dict:
    """이 PDF 가 이전 리비전보다 나중인가.  판정은 네 가지뿐이고 추정하지 않는다.

    hotfix62 — **Rev 가 같으면 PDF 에 인쇄된 날짜가 정한다** (사용자 확정).  Rev 가 다르면
    두 문서의 이력 표가 말하는 앞뒤(`order` — `pdf_facts` 의 `rev_before`)가 정하고, 이력 표가
    둘의 앞뒤를 모르면 날짜가, 날짜도 없으면 예전처럼 글자 순서가 정한다.  날짜는 ISO 문자열이고
    없으면 빈 문자열이다 — 날짜 없이 불린 예전 호출은 예전 판정 그대로다.
    """
    n, b = (now or "").strip(), (before or "").strip()
    nd, bd = (now_date or "").strip(), (before_date or "").strip()
    if not n or not b:
        return {"verdict": "UNKNOWN", "now": n, "before": b,
                "label": ("이 도면의 개정을 읽지 못했습니다" if not n
                          else "이전 리비전의 개정 기록이 없습니다")}

    def by(sign, why):
        if sign > 0:
            return {"verdict": "NEWER", "now": n, "before": b, "basis": why,
                    "label": f"개정본입니다 — {b} 다음 {n}"}
        if sign < 0:
            return {"verdict": "OLDER", "now": n, "before": b, "basis": why,
                    "label": f"이전 개정입니다 — 등록된 것은 {b} 인데 이 도면은 {n}"}
        return {"verdict": "SAME", "now": n, "before": b, "basis": why,
                "label": f"같은 개정입니다 — 둘 다 {n}"}

    if n == b:
        if nd and bd and nd != bd:
            return by(1 if nd > bd else -1, "DATE")
        return by(0, "DATE" if nd and bd else "REV")
    pairs = {tuple(x) for x in (order or ())}
    if (b, n) in pairs and (n, b) not in pairs:
        return by(1, "HISTORY")
    if (n, b) in pairs and (b, n) not in pairs:
        return by(-1, "HISTORY")
    if nd and bd and nd != bd:
        return by(1 if nd > bd else -1, "DATE")
    return by(1 if n > b else -1, "REV")


def _sheets_by_drawing(pages: list) -> dict:
    """도면번호 -> 그 번호를 쓰는 PID 장들."""
    out = {}
    for p in pages:
        if (p.get("page_kind") or "") != "PID":
            continue
        out.setdefault(str(p.get("drawing_no") or ""), []).append(p)
    return out


def compare_sheet_revisions(now: list, before: list) -> dict:
    """장 단위 대조 — 도면번호로 짝을 짓는다.  대표값과 달리 임의값이 없다.

    **⚠ 도면번호가 장을 유일하게 가리키지 않는다.**  AL NOUF1 실측: 같은
    도면번호를 쓰는 PID 장이 3쌍 있고 그 장들의 개정이 서로 다르다
    (`D00P-10LBG10-M05-0001` p12 `B` ↔ p15 `A` · `D00P-00GHC10-M05-0001`
    p46 `C` ↔ p47 `B` · `D00P-00GMA10-M05-0001` p52 `A` ↔ p55 `B`).
    한쪽만 골라 비교하면 **같은 PDF 를 두 번 넣어도 "개정 2장 · 역행 1장"이
    나온다** — 13회차 캡처가 실제로 그것을 잡았다.

    그래서 그런 도면번호는 **판정하지 않고 `ambiguous` 로 센다.**  어느 장이
    어느 장의 후속인지는 도면번호로 알 수 없고, 짝을 지어 주는 규칙을 만들면
    그것이 곧 임의값이다 (§2.1 ③).  쪽 번호로 짝을 짓는 것도 안 된다: 개정
    때 장 순서가 바뀌는 것이 개정의 흔한 모습이다.
    """
    prev_by = _sheets_by_drawing(before)
    now_by = _sheets_by_drawing(now)
    up, same, down, unknown, added, ambiguous = [], 0, [], 0, 0, []
    for dn, sheets in sorted(now_by.items()):
        prev_sheets = prev_by.get(dn)
        if not prev_sheets:
            added += len(sheets)
            continue
        if len(sheets) > 1 or len(prev_sheets) > 1:
            ambiguous.append({"drawing_no": dn, "now_sheets": len(sheets),
                              "before_sheets": len(prev_sheets)})
            continue
        r = str(sheets[0].get("rev") or "").strip()
        b = str(prev_sheets[0].get("rev") or "").strip()
        if not r or not b:
            unknown += 1
        elif r > b:
            up.append({"drawing_no": dn, "before": b, "now": r})
        elif r == b:
            same += 1
        else:
            down.append({"drawing_no": dn, "before": b, "now": r})
    return {"raised": up, "unchanged": same, "lowered": down,
            "unreadable": unknown, "new_sheets": added, "ambiguous": ambiguous}


def next_revision(meta: dict) -> str:
    """다음 리비전 이름.  A 부터 순서대로, 건너뛰지 않는다."""
    n = len(meta.get("revisions") or [])
    if n >= len(REV_LETTERS):
        raise ValueError("리비전이 26개를 넘었습니다")
    return f"Rev.{REV_LETTERS[n]}"


def default_compare_target(meta: dict) -> str:
    """기본 비교 대상은 직전 리비전.  없으면 빈 문자열(비교 없음)."""
    revs = [r for r in (meta.get("revisions") or []) if not r.get("deleted")]
    return revs[-1]["revision"] if revs else ""


def compare_choices(meta: dict) -> list:
    """고를 수 있는 비교 대상.  이미 등록된 리비전 중 **분석 기록이 살아 있는 것**.

    hotfix42 — 분석을 지운 리비전(`deleted`)은 뺀다: 그 job 이 없어 화면이 "이전 결과" 로
    열 수 없다.  장부 항목 자체는 남긴다 (안정 ID 가 그 리비전에서 부여됐고 §7.3 은 번호를
    되돌리지 않는다 — 다음 리비전 글자도 건너뛰지 않고 이어 간다).
    """
    return [r["revision"] for r in (meta.get("revisions") or []) if not r.get("deleted")]


def mark_revision_deleted(data_dir: Path, name: str, job_id: str, author: str = "") -> dict | None:
    """hotfix42 — 분석 하나를 지울 때 장부의 그 리비전에 `deleted{at, author}` 를 적는다.
    항목을 빼지 않는다 (ID 장부 · 대조 기록은 그 리비전의 사실이다).  없으면 None."""
    import time as _t
    try:
        meta = load_project(data_dir, name)
    except (KeyError, ValueError, FileNotFoundError):
        return None
    hit = None
    for r in meta.get("revisions") or []:
        if r.get("job_id") == job_id:
            r["deleted"] = {"at": _t.time(), "author": author or ""}
            hit = r
    if hit is not None:
        _save_project(data_dir, meta)
    return hit


def record_revision(data_dir: Path, name: str, revision: str, *, job_id: str,
                    pdf_name: str, compared_with: str, result: dict) -> dict:
    """대조 결과를 프로젝트에 적어 넣는다."""
    meta = load_project(data_dir, name)
    entry = {"revision": revision, "job_id": job_id, "pdf_name": pdf_name,
             "compared_with": compared_with,
             "label": (f"{revision} vs {compared_with}" if compared_with
                       else f"{revision} (비교 대상 없음)"),
             "counts": result["counts"],
             "basis": result.get("basis") or "",          # hotfix46 — TAG | NONE(입찰)
             "sheets": result.get("sheets") or {},
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
    # hotfix39 — 실행 프로젝트는 태그가 우선: 같은 장 안에서 태그 있는 행이 태그 순으로
    # 앞에 선다.  태그 없는 문서(AL NOUF1 · TC2 · SADARA)는 모든 행의 태그가 비어 예전 순서
    # 그대로다 — 안정 ID 와 Rev.A 산출물 번호가 안 흔들린다.
    tag = str(row.get("tag_no") or "").strip()
    return ((row.get("system") or ""), row.get("page_no") or 0,
            0 if tag else 1, tag, row.get("key") or "")


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
