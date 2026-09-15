# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe: one file, code and config only.

What ships:
  app/static/   the UI, served from inside the bundle
  config/       every profile plus the trade dictionary - a new site picks its
                own by dropping a `config/` folder beside the exe, or by
                PID_PROJECT_CONFIG; with neither, the built-in default is used
                and the sheet's own geometry is measured on top of it
  the wheels    PyMuPDF, numpy, openpyxl, PyYAML, fastapi/uvicorn and their
                binary parts, collected rather than guessed

What does NOT ship, and must not:
  data/         the drawings and the client's workbooks.  They are the client's
                and they are gitignored for the same reason; an exe that carried
                them would put one site's documents on another site's PC
  out/, logs/   this machine's own output
  tests/, spike/

Build:  build.bat   (or: pyinstaller --clean --noconfirm pid_extract.spec)
"""

import os as _os

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []
for pkg in ("fitz", "pymupdf", "numpy", "openpyxl", "yaml", "uvicorn",
            "fastapi", "starlette", "anyio", "h11", "click", "multipart"):
    try:
        d, b, h = collect_all(pkg)
    except Exception:                       # a package that is not installed
        continue
    datas += d
    binaries += b
    hiddenimports += h

# uvicorn reaches for its protocol implementations by name at run time, so they
# are not on any import graph and have to be named here or the server starts and
# then fails on the first request.
hiddenimports += collect_submodules("uvicorn")
hiddenimports += ["app.main", "app.pipeline", "app.db", "app.excel_out",
                  "app.paths", "app.version"]

# The engine modules import each other by *bare* name - `import pidcache`, not
# `import app.engine.pidcache` - through the sys.path insert each one carries, so
# that one copy of every module-level LAYOUT and of the config singleton exists
# (app/pipeline.py says why).  A frozen build has no sys.path to insert into, so
# the bare names have to be in the bundle under those same names, which is what
# `pathex` below and this list do together.  Miss one and the exe starts and then
# dies on `ModuleNotFoundError: No module named 'pidcache'`.
ENGINE_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(SPEC)), "app", "engine")
ENGINE_MODULES = sorted(
    f[:-3] for f in _os.listdir(ENGINE_DIR)
    if f.endswith(".py") and f != "__init__.py")
hiddenimports += ENGINE_MODULES

datas += [
    ("app/static", "app/static"),
    ("config", "config"),
]

# The build date, written by build.bat just before this runs.  It is a datas
# entry rather than a constant in the source because a date compiled into a
# committed file would claim a release that never happened; when it is absent
# `app/version.py` says so and falls back to the source's own mtime.
if _os.path.exists(_os.path.join(_os.path.dirname(_os.path.abspath(SPEC)),
                                 "app", "_build.json")):
    datas += [("app/_build.json", "app")]

a = Analysis(
    ["app/desktop.py"],
    pathex=[".", "app/engine"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PIL", "pytest", "playwright",
              "anthropic", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="PID_Extract",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,                 # the window IS the error report - see desktop.py
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
