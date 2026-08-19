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


def label() -> str:
    """One line for the bottom of the screen and for a file name."""
    i = info()
    suffix = "" if i["kind"] == "exe" else " (source)"
    return f"v{i['version']} · {i['built_at']}{suffix}"
