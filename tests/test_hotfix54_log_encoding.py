"""hotfix54 — 서버가 켜지다 죽고 10초마다 다시 켜지던 것 (회사 PC · C:\\Claude\\PID).

hotfix52 가 서버 출력을 `logs\\server.log` 로 돌리자, 한국어 Windows 의 파이썬은 그 파일을
cp949 로 썼다.  cp949 에는 `—` 가 없고, 사람이 손으로 더한 행이 있는 DB 에서는 기동 감사가
`—` 가 든 한 줄을 출력한다 → `UnicodeEncodeError` → `import app.main` 에서 죽음.
여기서는 그 조건(cp949 · 파일로 돌림 · 손으로 더한 행)을 그대로 세워 본다.
"""
from __future__ import annotations

import io
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import console, lan_check  # noqa: E402


def _seed(data: pathlib.Path) -> None:
    """회사 DB 처럼 손으로 더한 행 하나 — 감사가 `—` 줄을 내는 조건."""
    code = (
        "import time; from pathlib import Path; from app import db\n"
        f"con = db.connect(Path({str(data)!r}) / 'app.db')\n"
        "con.execute(\"INSERT INTO job (id,pdf_name,pdf_sha256,pdf_path,created_at,status,"
        "progress,message,fingerprint,project,revision) VALUES ('j1','x.pdf','s','p',?,'done',"
        "1.0,'','','P','A')\", (time.time(),))\n"
        "db.add_row(con, 'j1', page_no=7, tab='FIELD', drawing_no='D-1',"
        " values={'type': 'PIT', 'scope': 'SCT', 'qty': 1}, evidence={})\n"
        "con.commit()\n")
    env = dict(os.environ, PID_DATA_DIR=str(data))
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True)


def test_server_module_starts_when_the_log_is_cp949(tmp_path):
    data = tmp_path / "data"; data.mkdir()
    _seed(data)
    log = tmp_path / "server.log"
    env = dict(os.environ, PID_DATA_DIR=str(data), PID_LAN="1", PYTHONIOENCODING="cp949")
    env.pop("PYTHONUTF8", None)
    with open(log, "wb") as out:                       # 서비스처럼 파일로 돌린다
        r = subprocess.run([sys.executable, "-c", "import app.main"], cwd=ROOT, env=env,
                           stdout=out, stderr=subprocess.STDOUT, timeout=300)
    text = log.read_bytes().decode("cp949", "replace")
    assert r.returncode == 0, text[-2000:]
    assert "UnicodeEncodeError" not in text
    assert "위 두 값이 0 이 아니면" in text            # 그 줄이 실제로 출력됐다 (조건이 섰다)


def test_safe_stdio_replaces_instead_of_raising(monkeypatch):
    buf = io.BytesIO()
    stream = io.TextIOWrapper(buf, encoding="cp949", errors="strict", write_through=True)
    monkeypatch.setattr(sys, "stdout", stream)
    console.safe_stdio()
    console.safe_stdio()                               # 두 번 불러도 같다
    print("값이 들어갑니다 — 확인 ✎")
    assert buf.getvalue().decode("cp949") == "값이 들어갑니다 ? 확인 ?\n"
    assert stream.encoding == "cp949"                  # 인코딩은 바꾸지 않는다


def test_exe_tee_survives_a_cp949_window(tmp_path):
    from app.desktop import _Tee
    buf = io.BytesIO()
    win = io.TextIOWrapper(buf, encoding="cp949", errors="strict", write_through=True)
    tee = _Tee(win, tmp_path / "pid.log")
    tee.write("감사 — ⚠\n")
    tee.file.close()
    assert buf.getvalue().decode("cp949") == "감사 ? ?\n"
    assert (tmp_path / "pid.log").read_text(encoding="utf-8") == "감사 — ⚠\n"


def _code(name: str) -> str:
    text = (ROOT / name).read_text(encoding="ascii")
    return "\n".join(ln for ln in text.splitlines() if not ln.strip().lower().startswith("rem"))


def test_service_writes_the_log_in_utf8_and_shows_it_when_stopped():
    body = _code("run_lan_service.bat")
    assert body.index("set PYTHONUTF8=1") < body.index("uvicorn app.main:app")
    stopped = body[body.index(":stopped"):]
    assert "-m app.lan_check --tail" in stopped
    assert "set PYTHONUTF8=1" in _code("check_pid_server.bat")


def test_tail_shows_the_last_exception_from_a_mixed_log(tmp_path):
    log = tmp_path / "server.log"
    old = "INFO: 옛 줄\n".encode("cp949")                # hotfix53 까지 cp949 로 쓰인 줄
    tb = ("Traceback (most recent call last):\n"
          '  File "app/main.py", line 3545, in _audit_on_start\n'
          "UnicodeEncodeError: 'cp949' codec can't encode character '\\u2014'\n")
    log.write_bytes(old + tb.encode("utf-8") + "[감사] 새 줄 — 끝\n".encode("utf-8"))
    out = lan_check.tail(log)
    assert out[0].startswith("Traceback") and any("UnicodeEncodeError" in ln for ln in out)
    assert out[-1] == "[감사] 새 줄 — 끝"
    plain = tmp_path / "plain.log"
    plain.write_bytes(("\n".join(f"줄 {i}" for i in range(40)) + "\n").encode("cp949"))
    assert lan_check.tail(plain, n=5) == [f"줄 {i}" for i in range(35, 40)]
    assert "로그가 없습니다" in lan_check.tail(tmp_path / "none.log")[0]
