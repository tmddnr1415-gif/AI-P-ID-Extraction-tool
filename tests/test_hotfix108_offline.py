"""hotfix108 — 절전모드: 서버가 꺼져도 보관된 화면·자료로 보고 고치고, 켜지면 보관한 순서대로 서버에 덮어쓴다.

판정은 하나도 없다 — 여기서 못박는 것은 (가) 서비스워커·보관 목록이 서버 뿌리에서 나간다 (나) 네 화면이 공용 offline.js 를
다른 스크립트보다 **먼저** 싣는다 (다) 화면이 미리 정한 id 를 서버가 받아 같은 보관본을 두 번 보내도 하나가 된다 (라) 보관하지
않을 것(분석 · 시뮬레이션 · 삭제)과 보관할 것의 경계 (마) 브라우저 대화상자 없음."""
from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import sheet_memo, space
from app.logic import memo as lmemo
from app.main import app

ROOT = Path(__file__).resolve().parent.parent
ME = {"X-Author": quote("홍길동")}
STATIC = ROOT / "app" / "static"


@pytest.fixture()
def client():
    shutil.rmtree(space._root(), ignore_errors=True)
    with TestClient(app) as c:
        yield c
    shutil.rmtree(space._root(), ignore_errors=True)


def test_service_worker_and_shell_list_come_from_the_root(client):
    r = client.get("/sw.js")
    assert r.status_code == 200 and "serviceWorker" not in r.headers.get("content-type", "")
    assert r.headers["cache-control"] == "no-store" and r.headers["service-worker-allowed"] == "/"
    assert "pid-offline" in r.text and "offline-mode" in r.text and "prefetch" in r.text
    shell = client.get("/offline/shell").json()["urls"]
    for page in ("/", "/logic", "/logic/test", "/space", "/dcs"):
        assert page in shell
    assert any(u.startswith("/static/app.js?v=") for u in shell) and any(u.startswith("/static/offline.js?v=") for u in shell)
    assert "/static/logic.js" in shell and "/static/space/index.html" in shell and "/static/dcs.html" in shell
    assert "/static/sw.js" not in shell                                          # 워커 자신은 /sw.js 로만


def test_every_screen_loads_offline_js_first():
    for name, app_tag in (("index.html", "pid"), ("logic.html", "logic"), ("logic_test.html", "logic"),
                          ("space/index.html", "space"), ("dcs.html", "dcs")):
        html = (STATIC / name).read_text(encoding="utf-8")
        i = html.find('src="/static/offline.js"')
        assert i > 0 and f'data-app="{app_tag}"' in html[i:i + 80], name
        others = [m.start() for m in re.finditer(r"<script(?![^>]*offline\.js)", html)]
        assert others and min(others) > i, f"{name}: offline.js 가 다른 스크립트보다 먼저여야 한다"


def test_index_tags_offline_js_like_app_js(client):
    html = client.get("/").text
    assert re.search(r'/static/offline\.js\?v=[0-9a-f]{8}', html) and re.search(r'/static/app\.js\?v=[0-9a-f]{8}', html)


def test_offline_js_rules_and_no_dialogs():
    src = (STATIC / "offline.js").read_text(encoding="utf-8")
    for bad in ("prompt(", "confirm(", "alert("):
        assert bad not in src
    assert "X-Offline-Replay" in src and "navigator.locks" in src and "indexedDB" in src
    sw = (STATIC / "sw.js").read_text(encoding="utf-8")
    assert "self.addEventListener(\"fetch\"" in sw and "req.method !== \"GET\"" in sw
    never = re.search(r"const NEVER_RE = (/.*/);", sw).group(1)
    assert "version" in never and "events" in never and "plaza" in never and "xlsx" in never


def test_space_accepts_client_ids_so_a_replayed_request_is_one_record(client):
    pid = "6f1c2a3b4d5e"
    a = client.post("/space/api/projects", json={"name": "ABSENT", "id": pid}, headers=ME).json()
    b = client.post("/space/api/projects", json={"name": "ABSENT", "id": pid}, headers=ME).json()
    assert a["id"] == pid and b["id"] == pid and len(client.get("/space/api/projects").json()["projects"]) == 1
    # 이름이 같고 id 가 없는 되보냄(X-Offline-Replay)은 409 가 아니라 있는 것을 돌려준다
    c = client.post("/space/api/projects", json={"name": "absent"}, headers={**ME, "X-Offline-Replay": "1700000000000"})
    assert c.status_code == 200 and c.json()["id"] == pid
    assert client.post("/space/api/projects", json={"name": "absent"}, headers=ME).status_code == 409
    plan = {"room": {"w": 1, "l": 1}, "types": [], "panels": [], "info": {}}
    sid = "7a7a7a7a7a7a"
    m1 = client.post(f"/space/api/{pid}/saves", json={"data": plan, "sid": sid}, headers=ME).json()
    m2 = client.post(f"/space/api/{pid}/saves", json={"data": plan, "sid": sid}, headers=ME).json()
    assert m1["id"] == sid and m2 == m1 and len(client.get(f"/space/api/{pid}").json()["saves"]) == 1
    n1 = client.post(f"/space/api/{pid}/notes", json={"text": "x", "id": "abcdef123456"}, headers=ME).json()
    client.post(f"/space/api/{pid}/notes", json={"text": "x", "id": "abcdef123456"}, headers=ME)
    assert n1["id"] == "abcdef123456" and len(client.get(f"/space/api/{pid}").json()["notes"]) == 1
    bad = client.post(f"/space/api/{pid}/notes", json={"text": "y", "id": "NOT VALID!!"}, headers=ME).json()
    assert bad["id"] != "NOT VALID!!" and space.SPACE_ID_RE.match(bad["id"])    # 꼴이 틀리면 서버가 정한다


def test_logic_memo_and_pid_pin_take_client_ids_once():
    d = Path(tempfile.mkdtemp())
    try:
        a = lmemo.add(d, 3, "G001", "글", "홍길동", mid="k7f3abcd12")
        b = lmemo.add(d, 3, "G001", "글", "홍길동", mid="k7f3abcd12")
        assert a["id"] == "k7f3abcd12" and b == a and len(lmemo.load(d)["items"]) == 1
        assert lmemo.add(d, 3, "G001", "글", "홍길동", mid="BAD ID")["id"] != "BAD ID"
        kw = dict(key="D-1|1", rect=[1, 1, 5, 5], text="핀", author="홍길동", revision="A", page_no=1,
                  drawing_no="D-1", page_w=100.0, page_h=100.0)
        p1 = sheet_memo.add_pin(d, "P", "job1", pin_id="Pabc123xyz", **kw)
        p2 = sheet_memo.add_pin(d, "P", "job1", pin_id="Pabc123xyz", **kw)
        assert p1["id"] == "Pabc123xyz" and p2["id"] == p1["id"]
        assert len(sheet_memo.load(d, "P", "job1")["pins"]["D-1|1"]) == 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_replay_header_does_not_change_the_answer(client):
    r = client.get("/version", headers={"X-Offline-Replay": "1700000000000", "X-Offline-App": "pid"})
    assert r.status_code == 200 and r.json().get("version")


def test_queue_boundary_in_offline_js():
    """보관하지 않는 것: 업로드 · 분석 · 시뮬레이션 · 삭제.  보관하는 것: 칸 편집 · 평가 · 메모 · 사람 값 · 판넬 저장."""
    src = (STATIC / "offline.js").read_text(encoding="utf-8")
    rules = dict(re.findall(r"^\s+(pid|logic|space|dcs): (/.*?/),$", src, re.M))
    assert set(rules) == {"pid", "logic", "space", "dcs"}

    def js_re(s):           # JS 정규식 → 파이썬 (이 파일의 식은 공통 문법만 쓴다)
        return re.compile(s.strip("/").replace("\\/", "/"))
    pid, logic, sp = js_re(rules["pid"]), js_re(rules["logic"]), js_re(rules["space"])
    for kept in ("/jobs/j1/rows/k1", "/jobs/j1/rows_edit", "/jobs/j1/rows_delete", "/jobs/j1/verdicts", "/jobs/j1/memo/5",
                 "/jobs/j1/memo/5/pins", "/jobs/j1/multipliers", "/jobs/j1/sheet_numbers", "/jobs/j1/rows/k1/review/X", "/voc", "/projects"):
        assert not pid.search(kept), kept
    for no in ("/jobs", "/jobs/j1/reanalyse", "/jobs/j1/cancel", "/jobs/j1/markup/propose", "/jobs/j1/rows", "/jobs/j1/save",
               "/jobs/j1/snapshot", "/jobs/j1/revision", "/jobs/j1/teach", "/templates"):
        assert pid.search(no), no
    for kept in ("/logic/api/jobs/x/overrides/block", "/logic/api/jobs/x/memo", "/logic/api/jobs/x/memo/m1", "/logic/api/jobs/x/review/mark", "/logic/api/projects"):
        assert not logic.search(kept), kept
    for no in ("/logic/api/jobs", "/logic/api/jobs/x/sheet/3/simulate", "/logic/api/jobs/x/simulate", "/logic/api/jobs/x/sequence",
               "/logic/api/jobs/x/grouptest", "/logic/api/jobs/x/teach/preview", "/logic/api/jobs/x"):
        assert logic.search(no), no
    assert not sp.search("/space/api/projects") and not sp.search("/space/api/p1/saves") and sp.search("/space/api/import_dashboard")
