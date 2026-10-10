"""hotfix53 - pip requirements files are ASCII only.

Field (company PC, moving the server to C:\\Claude\\PID):
    .venv\\Scripts\\python -m pip install --no-index --find-links wheels -r requirements-win.txt
    UnicodeDecodeError: 'cp949' codec can't decode byte 0xec in position 32

pip reads a requirements file with the locale codepage when it has no BOM and no
coding line.  On Korean Windows that is cp949, and the UTF-8 Korean comments in
the file stopped the install before a single package.  Same family as hotfix51
(batch files): files that Windows tools read must not depend on the codepage.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_every_requirements_file_is_ascii():
    files = sorted(ROOT.glob("requirements*.txt"))
    assert {p.name for p in files} >= {"requirements.txt", "requirements-win.txt",
                                       "requirements-win.lock.txt",
                                       "requirements-win-dxf.txt",
                                       "requirements-win-test.txt"}
    for p in files:
        raw = p.read_bytes()
        bad = [i for i, b in enumerate(raw) if b > 0x7F]
        assert not bad, f"{p.name}: non-ASCII byte at {bad[:3]}"


def test_pins_survive_the_rewrite():
    win = (ROOT / "requirements-win.txt").read_text(encoding="ascii")
    for pin in ("pymupdf==1.28.2", "numpy==2.4.6", "uvicorn==0.52.3", "fastapi==0.141.1"):
        assert pin in win
    assert "uvloop" not in [ln.split("==")[0] for ln in win.splitlines() if ln and not ln.startswith("#")]
    dxf = (ROOT / "requirements-win-dxf.txt").read_text(encoding="ascii")
    assert "ezdxf==1.4.4" in dxf and "packaging==26.3" in dxf
