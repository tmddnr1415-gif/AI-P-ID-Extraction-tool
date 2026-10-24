"""What this build is, so a report can say which one it came from.

The version is written here by hand.  The build date is *not*: it is stamped into
`_build.json` beside this file when `build.bat` packages an exe, and read back at
runtime.  Running from a source checkout there is no such file, and rather than
invent a date the answer is the source's own - the newest mtime of the code that
decides anything - labelled as a source run so no one reads it as a release.

Nothing here reaches the network and nothing here is written at runtime.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

VERSION = "1.0.0"

_HERE = Path(__file__).resolve().parent
_STAMP = _HERE / "_build.json"
# hotfix34 — 어느 꾸러미(hotfix zip)가 적용돼 있는가.  `spike/pack_hotfix.py` 가 꾸러미를
# 만들 때 저장소에 적고 꾸러미에 함께 넣는다.  없으면 "기록 없음" 이지 지어내지 않는다.
_UPDATE = _HERE / "_update.json"


def frozen() -> bool:
    """True when running from a PyInstaller bundle rather than a checkout."""
    return bool(getattr(sys, "frozen", False))


def _source_date() -> str:
    newest = 0.0
    for pat in ("*.py", "engine/*.py", "static/*"):
        for p in _HERE.glob(pat):
            newest = max(newest, p.stat().st_mtime)
    if not newest:
        return ""
    return _dt.datetime.fromtimestamp(newest).strftime("%Y-%m-%d")


def info() -> dict:
    """Version, build date and how the build was made - for screen and for zip."""
    stamp = {}
    if _STAMP.exists():
        try:
            stamp = json.loads(_STAMP.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            stamp = {}
    built = str(stamp.get("built_at") or "")
    return {
        "version": str(stamp.get("version") or VERSION),
        "built_at": built or _source_date(),
        "kind": "exe" if frozen() else "source",
        "dated": "build" if built else "source mtime",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}"
                  f".{sys.version_info.micro}",
    }


def update_info(path: Path | None = None) -> dict | None:
    """적용된 꾸러미의 사실 — 이름 · rev 번호 · zip 파일명 · 만든 시각 · 기준 커밋.

    꾸러미 생성기가 적은 그대로 돌려준다.  파일이 없거나 깨졌으면 None — 화면은
    "업데이트 기록 없음" 으로 말한다 (hotfix34 이전 꾸러미에는 이 파일이 없다).
    """
    path = path or _UPDATE
    if not path.exists():
        return None
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if not isinstance(d, dict) or not d.get("name"):
        return None
    return {"name": str(d.get("name") or ""), "rev": d.get("rev"),
            "zip": str(d.get("zip") or ""), "created_at": str(d.get("created_at") or ""),
            "base_commit": str(d.get("base_commit") or ""),
            "branch": str(d.get("branch") or "")}


def label() -> str:
    """One line for the bottom of the screen and for a file name."""
    i = info()
    suffix = "" if i["kind"] == "exe" else " (source)"
    return f"v{i['version']} · {i['built_at']}{suffix}"
