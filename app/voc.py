"""VOC — 부서원이 남긴 오류·요청을 개발하는 쪽(회사 Claude Code)이 읽을 수 있게 파일로 쌓는다 (hotfix71).

왜 DB 가 아니라 파일인가
------------------------
신고(`report` 표)는 그 분석의 DB 안에 있어서, 고치는 쪽이 읽으려면 서버를 띄우고 분석을 열거나
진단 zip 을 받아야 했다.  VOC 는 **고칠 사람이 그 자리에서 읽는 것**이 목적이므로 운영 폴더 옆
`voc/inbox/<VOC-id>/` 에 한 건이 폴더 하나로 남는다:

    voc/inbox/VOC-20261009-142233-a1b2c3/
        voc.json      무엇이 틀렸나(분류·사유·작성자) + 자동으로 담은 맥락(분석 · 장 · 사각형 · 행 · 빌드)
        crop.png      (있으면) 그 자리의 도면 조각 — 사각형을 붉게 둘렀다
        resolution.json  (반영된 뒤) 누가 · 언제 · 어느 업데이트로 반영했나

중복 반영을 막는 것 — 장부 하나
------------------------------
같은 VOC 를 두 번 고치지 않게 하는 것은 **id** 와 **장부**다.  id 는 만들 때 한 번 정해지고
(시각 + 무작위 6자리) 폴더 이름이 곧 id 다 — 운영 폴더의 inbox 를 복사해 와도, 같은 VOC 가
두 inbox 에 있어도 같은 id 로 하나로 센다.  반영하면 `spike/voc.py resolve` 가 개발 폴더의
`voc/ledger.json` 에 그 id 를 적고, 그 VOC 가 온 inbox 폴더에도 `resolution.json` 을 남긴다.
`list` 는 둘 중 하나라도 있으면 다시 보이지 않는다.  **장부는 지우지 않고 쌓기만 한다.**

이 모듈은 서버(쓰기 · 목록)와 `spike/voc.py`(읽기 · 반영 표시)가 같이 쓴다 — 상태를 판정하는
곳이 둘이면 언젠가 갈린다.

어디에 쌓나 (`voc_root`)
------------------------
① `PID_VOC_DIR` 이 있으면 거기 ② `PID_DATA_DIR`(시험 · 화면 자기검증) 이면 그 밑 `voc/`
③ exe 면 `pid_data/voc/` ④ 소스로 돌면 **저장소 뿌리의 `voc/`** — 운영 PC 의 `C:\\Claude\\PID\\voc`.
`voc/` 는 `.gitignore` 대상이다 (도면 조각과 사람 이름이 들어간다).
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import time
from datetime import datetime
from pathlib import Path

from app import paths

ENV_DIR = "PID_VOC_DIR"
ID_RE = re.compile(r"^VOC-\d{8}-\d{6}-[0-9a-f]{6}$")

# 어디서 온 VOC 인가 — 화면의 입구마다 하나.
SOURCES = {
    "MARKUP_ADD": "마크업 — 누락 행 추가",
    "MARKUP_REJECT": "마크업 — 기존 상자 표시",
    "ROW_REPORT": "오류 신고 (행 · 도면 위치)",
    "GENERAL": "일반 VOC",
    "ANALYSIS_FAILED": "분석 실패 화면",
}

# 무엇이 틀렸나 — 마크업 분류(44회차 `markup.CLASSES`)와 일반 VOC 분류를 한 표로.
CATEGORIES = {
    "MISSING": "㉡ 미검출 — 도면에 있는데 행이 없음",
    "FALSE_POSITIVE": "㉢ 오검출 — 행이 있는데 도면에 없음",
    "WRONG_VALUE": "㉣ 값 틀림 — 행은 맞는데 칸이 틀림",
    "UNKNOWN_SYMBOL": "미지정 심볼 — 범례에 없어 못 읽음",
    "NOT_SUPPLY": "공급 대상 아님 — SCT 도 VENDOR 도 아님",
    "SCOPE": "Scope 판정 틀림",
    "QTY": "Q'ty 틀림",
    "TYPE": "Type / Valve Type 틀림",
    "DESCRIPTION": "Description 틀림",
    "ANALYSIS_FAILED": "분석이 멈춤 / 실패",
    "SLOW": "느림 · 무거움",
    "UI": "화면 · 사용법 불편",
    "FEATURE": "기능 요청",
    "OTHER": "기타",
}

# 반영 장부의 상태.  RESOLVED 만 "고쳤다" 이고 나머지는 "고치지 않기로 했다" 이지만,
# 넷 다 **다시 볼 목록에서 빠진다** — 중복 반영을 막는 것이 장부의 일이다.
STATUSES = {
    "RESOLVED": "반영됨",
    "DUPLICATE": "중복 — 다른 VOC 로 반영",
    "WONTFIX": "반영 안 함 (사유 있음)",
    "NEED_INFO": "정보 부족 — 다시 신고 필요",
}

MAX_TEXT = 4000


# ---------------------------------------------------------------- 자리
def voc_root() -> Path:
    env = os.environ.get(ENV_DIR)
    if env:
        return Path(env).expanduser().resolve()
    if os.environ.get(paths._ENV_DATA_DIR) or paths.frozen():
        return paths.data_dir() / "voc"
    return paths._SRC_ROOT / "voc"


def inbox_dir(root: Path | None = None) -> Path:
    return (root or voc_root()) / "inbox"


def ledger_path(root: Path | None = None) -> Path:
    return (root or voc_root()) / "ledger.json"


def new_id(now: float | None = None) -> str:
    t = datetime.fromtimestamp(now if now is not None else time.time())
    return f"VOC-{t:%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"


def _clean(s, n=MAX_TEXT) -> str:
    return str(s or "").replace("\r\n", "\n").strip()[:n]


# ---------------------------------------------------------------- 쓰기
def write(record: dict, *, crop_png: bytes | None = None, root: Path | None = None) -> dict:
    """한 건을 inbox 에 쓴다.  다 쓴 뒤에 이름을 바꿔 넣으므로 반쯤 쓴 VOC 는 보이지 않는다."""
    category = str(record.get("category") or "").upper()
    if category not in CATEGORIES:
        raise ValueError(f"unknown VOC category {category!r}")
    source = str(record.get("source") or "GENERAL").upper()
    if source not in SOURCES:
        raise ValueError(f"unknown VOC source {source!r}")
    reason = _clean(record.get("reason"))
    if not reason:
        raise ValueError("VOC 에는 사유가 필요합니다")
    now = time.time()
    vid = new_id(now)
    rec = dict(record)
    rec.update({
        "id": vid, "schema": 1,
        "created_at": datetime.fromtimestamp(now).isoformat(timespec="seconds"),
        "created_ts": now,
        "source": source, "source_label": SOURCES[source],
        "category": category, "category_label": CATEGORIES[category],
        "reason": reason,
        "author": " ".join(str(record.get("author") or "").split())[:60],
        "has_crop": bool(crop_png),
    })
    inbox = inbox_dir(root)
    inbox.mkdir(parents=True, exist_ok=True)
    tmp = inbox / f".tmp-{vid}"
    tmp.mkdir()
    try:
        (tmp / "voc.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True, default=str),
            encoding="utf-8")
        if crop_png:
            (tmp / "crop.png").write_bytes(crop_png)
        os.replace(tmp, inbox / vid)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return rec


# ---------------------------------------------------------------- 읽기
def read_item(folder: Path) -> dict | None:
    f = folder / "voc.json"
    if not ID_RE.match(folder.name) or not f.exists():
        return None
    try:
        rec = json.loads(f.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if rec.get("id") != folder.name:
        return None
    rec["_dir"] = str(folder)
    res = folder / "resolution.json"
    if res.exists():
        try:
            rec["_resolution"] = json.loads(res.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return rec


def scan(inboxes) -> dict:
    """여러 inbox 를 훑어 id 로 하나씩.  같은 id 가 둘이면 먼저 찾은 것을 쓰고 자리를 함께 적는다."""
    out: dict[str, dict] = {}
    for ib in inboxes:
        ib = Path(ib)
        if not ib.is_dir():
            continue
        for d in sorted(ib.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            rec = read_item(d)
            if rec is None:
                continue
            if rec["id"] in out:
                out[rec["id"]].setdefault("_also", []).append(rec["_dir"])
                if "_resolution" in rec and "_resolution" not in out[rec["id"]]:
                    out[rec["id"]]["_resolution"] = rec["_resolution"]
                continue
            out[rec["id"]] = rec
    return out


def load_ledger(path: Path | None = None) -> dict:
    path = path or ledger_path()
    if not path.exists():
        return {"schema": 1, "entries": {}}
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        raise ValueError(f"장부를 읽지 못했습니다: {path} — 고치기 전에는 아무것도 반영 표시하지 않습니다")
    d.setdefault("entries", {})
    return d


def save_ledger(ledger: dict, path: Path | None = None) -> None:
    path = path or ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ledger, ensure_ascii=False, indent=1, sort_keys=True),
                   encoding="utf-8")
    os.replace(tmp, path)


def status_of(rec: dict, ledger: dict | None) -> dict | None:
    """그 VOC 가 처리됐으면 처리 기록, 아니면 None.  장부가 먼저, 없으면 inbox 의 표시."""
    if ledger and rec.get("id") in ledger.get("entries", {}):
        return ledger["entries"][rec["id"]]
    return rec.get("_resolution")


def pending(items: dict, ledger: dict | None) -> list:
    return sorted((r for r in items.values() if status_of(r, ledger) is None),
                  key=lambda r: r.get("created_ts") or 0)


def mark(items: dict, ids, *, status: str, by: str, release: str = "", note: str = "",
         duplicate_of: str = "", ledger_file: Path | None = None,
         write_marker: bool = True, force: bool = False) -> list:
    """반영 표시.  이미 처리된 id 는 `force` 없이는 건드리지 않고 사유를 돌려준다 — 중복 반영 방지."""
    status = status.upper()
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    if not str(by or "").strip():
        raise ValueError("누가 반영했는지(--by) 가 필요합니다")
    if status == "DUPLICATE" and not duplicate_of:
        raise ValueError("중복이면 어느 VOC 의 중복인지(--of) 가 필요합니다")
    ledger = load_ledger(ledger_file)
    done = []
    for vid in ids:
        rec = items.get(vid)
        if rec is None:
            done.append((vid, "없음 — inbox 에서 찾지 못했습니다"))
            continue
        prev = status_of(rec, ledger)
        if prev is not None and not force:
            done.append((vid, f"이미 처리됨 ({prev.get('status')} · {prev.get('release') or ''}"
                              f" · {prev.get('at') or ''}) — 건너뜀"))
            continue
        entry = {"id": vid, "status": status, "by": " ".join(str(by).split())[:60],
                 "at": datetime.now().isoformat(timespec="seconds"),
                 "release": str(release or ""), "note": _clean(note, 1000),
                 "category": rec.get("category"), "reason": rec.get("reason", "")[:200]}
        if duplicate_of:
            entry["duplicate_of"] = duplicate_of
        ledger["entries"][vid] = entry
        if write_marker:
            for d in [rec["_dir"], *rec.get("_also", [])]:
                try:
                    (Path(d) / "resolution.json").write_text(
                        json.dumps(entry, ensure_ascii=False, indent=1, sort_keys=True),
                        encoding="utf-8")
                except OSError as exc:            # 남의 폴더에 못 쓰면 장부만으로 막는다
                    entry.setdefault("marker_errors", []).append(f"{d}: {exc}")
        done.append((vid, f"{status} 표시"))
    save_ledger(ledger, ledger_file)
    return done


# ---------------------------------------------------------------- 화면용
def _rev_number(name: str) -> int | None:
    m = re.search(r"(\d+)", str(name or ""))
    return int(m.group(1)) if m else None


def public(rec: dict, ledger: dict | None, applied_update: dict | None) -> dict:
    """화면에 낼 한 건.  반영된 업데이트가 이 서버에 이미 깔렸는지도 말한다."""
    st = status_of(rec, ledger)
    out = {k: rec.get(k) for k in ("id", "created_at", "source", "source_label", "category",
                                   "category_label", "reason", "author", "has_crop")}
    ctx = rec.get("context") or {}
    out.update({"job_id": ctx.get("job_id"), "pdf_name": ctx.get("pdf_name"),
                "project": ctx.get("project"), "page_no": ctx.get("page_no"),
                "drawing_no": ctx.get("drawing_no")})
    if st is None:
        out["state"] = "OPEN"
        out["state_label"] = "접수됨 — 개발 대기"
        return out
    out["state"] = st.get("status")
    label = STATUSES.get(st.get("status"), st.get("status"))
    rel = st.get("release") or ""
    if st.get("status") == "RESOLVED" and rel:
        want, have = _rev_number(rel), _rev_number((applied_update or {}).get("name"))
        if want is not None and have is not None and have >= want:
            label += f" — {rel} (이 서버에 적용됨)"
        else:
            label += f" — {rel} (다음 업데이트에 포함)"
    out["state_label"] = label
    out["resolution"] = {k: st.get(k) for k in ("status", "by", "at", "release", "note",
                                                "duplicate_of")}
    return out
