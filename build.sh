#!/usr/bin/env bash
# The same build on Linux/macOS, so the recipe can be checked without Windows.
# `build.bat` is the one the release is made with; this exists so the spec file
# and the stamping are exercised on the machine the code is written on.
set -euo pipefail
cd "$(dirname "$0")"

python3 -c "
import json, datetime, sys
sys.path.insert(0, '.')
from app.version import VERSION
json.dump({'version': VERSION, 'built_at': datetime.date.today().isoformat()},
          open('app/_build.json', 'w'), indent=1)
print('build stamp:', VERSION, datetime.date.today().isoformat())
"
python3 -m pytest -q -m "not slow and not ui"
python3 -m PyInstaller "$@" --noconfirm pid_extract.spec
ls -la dist/
