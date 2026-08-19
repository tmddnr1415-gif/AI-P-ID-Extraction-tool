"""Where the files are, whether this is a checkout or a packaged exe.

Two roots, and they are different on purpose:

  `resource(...)`  read-only things that ship *inside* the build - the profiles,
                   the trade dictionary, the UI.  In a PyInstaller one-file exe
                   these are unpacked to a temporary directory that is deleted on
                   exit, so nothing may ever be written there.

  `data_dir()`     everything the run produces - the database, the uploaded PDFs,
                   the exports, the log.  Beside the exe, so the user can see it,
                   back it up and delete it, and so a second run finds the first
                   run's analyses still there.  Never inside the bundle.

Both stay on this machine.  Nothing in this module reaches the network, and the
only absolute path either of them can produce is one the user chose by putting
the exe somewhere.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parent.parent


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """Where the bundled read-only files live."""
    if frozen():
        # PyInstaller one-file: the bundle is unpacked here for this process.
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return _SRC_ROOT


def resource(*parts) -> Path:
    return resource_root().joinpath(*parts)


def data_dir() -> Path:
    """Where this run writes.  Beside the exe when packaged, in the tree if not."""
    if frozen():
        return Path(sys.executable).resolve().parent / "pid_data"
    return _SRC_ROOT / "app" / "_data"


def log_path() -> Path:
    return data_dir() / "logs" / "server.log" if frozen() else _SRC_ROOT / "logs" / "server.log"
