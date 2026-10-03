#!/usr/bin/env bash
# One command to bring the app up.
#
# There is no separate frontend server: the UI is plain HTML/JS with no build
# step, served by the same FastAPI process from app/static/. One port, one log.
#
#   ./run.sh              start on 8000, reload on code change
#   ./run.sh 9000         another port
#   ./run.sh --no-reload  don't watch files (a little faster)
#
# Analyses already in app/_data/app.db are kept, so an earlier result opens
# immediately - the landing screen lists them and the app jumps straight to the
# grid without re-analysing. Delete app/_data/ to start clean.
set -euo pipefail
cd "$(dirname "$0")"

PORT=8000
RELOAD=--reload
for arg in "$@"; do
  case "$arg" in
    --no-reload) RELOAD="" ;;
    [0-9]*) PORT="$arg" ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

python3 - <<'PY' || { echo; echo "의존성이 없습니다:  pip install -r requirements.txt"; exit 1; }
import importlib.util, sys
missing = [m for m in ("fastapi", "uvicorn", "multipart", "pymupdf", "openpyxl",
                       "yaml", "numpy") if not importlib.util.find_spec(m)]
if missing:
    print("missing:", ", ".join(missing), file=sys.stderr)
    sys.exit(1)
PY

mkdir -p logs
DB=app/_data/app.db
if [ -f "$DB" ]; then
  N=$(python3 - "$DB" <<'PY'
import sqlite3, sys
try:
    c = sqlite3.connect(sys.argv[1])
    print(c.execute("SELECT COUNT(*) FROM job WHERE status='done'").fetchone()[0])
except Exception:
    print(0)
PY
)
  echo "이미 분석된 작업 ${N}건 — 재분석 없이 바로 열립니다."
fi

echo "→ http://127.0.0.1:${PORT}"
echo "→ 로그: logs/server.log (화면에도 같이 출력)"
echo
exec python3 -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" ${RELOAD} \
  2>&1 | tee -a logs/server.log
