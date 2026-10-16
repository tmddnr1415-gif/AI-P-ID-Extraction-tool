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

import os
import sys
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parent.parent

# One override, for tests: point the writing root somewhere disposable.
#
# The UI suite drives the real server against a real analysis, and until this
# existed it did that against `app/_data/app.db` itself - so a single run left
# reviewer edits, hand-added rows and revision snapshots in the database the
# deliverables are built from.  That is not a test artefact; it reaches the
# workbook, and `git status` cannot see it because `app/_data/` is gitignored.
#
# Named rather than inferred: nothing decides on its own that it is "in a test".
# The variable is set by whoever wants a throwaway root, and unset means the
# normal one.
_ENV_DATA_DIR = "PID_DATA_DIR"


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
    override = os.environ.get(_ENV_DATA_DIR)
    if override:
        return Path(override).expanduser().resolve()
    if frozen():
        return Path(sys.executable).resolve().parent / "pid_data"
    return _SRC_ROOT / "app" / "_data"


def log_path() -> Path:
    return data_dir() / "logs" / "server.log" if frozen() else _SRC_ROOT / "logs" / "server.log"
