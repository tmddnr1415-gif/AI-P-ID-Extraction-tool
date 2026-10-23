"""hotfix109 — DCS HMI 그래픽: 사람 값 저장 · 프로젝트로 P&ID 찾기 · LOGIC 창 연동 (태그 1/0 → 그림)."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import dcs
from app.main import app

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "app" / "static"


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


class _Job(dict):
    def __getitem__(self, k): return dict.get(self, k)
    def keys(self): return dict.keys(self)


# ---------------------------------------------------------------- 사람 값 (태그 · 이름 · Key Parameters · Trend)

def test_hmi_values_live_outside_the_analysis_and_keep_history(tmp_path, monkeypatch):
    monkeypatch.setattr(dcs, "_hmi_path", lambda job: tmp_path / "dcs" / job / "hmi.json")
    with pytest.raises(ValueError):                                                       # 이름이 없으면 저장하지 않는다
        dcs.hmi_save("ab12", {"tags": {"k1": "14LBA11CP001"}}, "")
    out = dcs.hmi_save("ab12", {"tags": {"k1": "14LBA11CP001"}, "names": {"HRSG#12 BD TANK": "BD Tank #12"}}, "홍길동")
    assert out["tags"] == {"k1": "14LBA11CP001"} and out["names"]["HRSG#12 BD TANK"] == "BD Tank #12"
    assert [h["kind"] for h in out["history"]] == ["tag", "name"] and out["history"][0]["by"] == "홍길동"
    out = dcs.hmi_save("ab12", {"tags": {"k1": ""}, "params": {"5": ["A", "B"]}, "trend": {"5": "A"}}, "홍길동")
    assert "k1" not in out["tags"] and out["params"] == {"5": ["A", "B"]} and out["trend"] == {"5": "A"}
    assert len(out["history"]) == 3 and out["history"][-1]["from"] == "14LBA11CP001"      # 지우지 않고 이력에 남는다
    assert dcs.hmi_load("ab12")["params"] == {"5": ["A", "B"]}
    with pytest.raises(ValueError):                                                       # 태그 꼴이 아니면
        dcs.hmi_save("ab12", {"tags": {"k1": "<script>"}}, "홍길동")
    with pytest.raises(ValueError):
        dcs.hmi_save("ab12", {"params": ["x"]}, "홍길동")


def test_hmi_api_404_for_unknown_job_and_demo_page_serves(client):
    assert client.get("/dcs/api/jobs/zzzz/hmi").status_code == 404
    assert client.post("/dcs/api/jobs/zzzz/hmi", json={"tags": {}}, headers={"X-Author": quote("홍")}).status_code == 404
    r = client.get("/dcs/demo")
    assert r.status_code == 200 and "hmi-core.js" in r.text


# ---------------------------------------------------------------- 같은 프로젝트의 P&ID 를 찾는다 (LOGIC 창이 쓴다)

def test_pid_job_for_project_matches_by_name_loosely(monkeypatch):
    from app import main
    jobs = [_Job(id="j1", status="done", project="DCS TEST", pdf_name="a.pdf", revision="Rev.B", created_at=2.0),
            _Job(id="j0", status="done", project="DCS-TEST", pdf_name="a.pdf", revision="Rev.A", created_at=1.0),
            _Job(id="bid", status="done", project="OTHER", pdf_name="b.pdf", revision="Rev.A", created_at=3.0),
            _Job(id="run", status="running", project="DCS-TEST", pdf_name="c.pdf", revision="Rev.C", created_at=4.0)]
    monkeypatch.setattr(main.db, "list_jobs", lambda con: jobs)
    monkeypatch.setattr(dcs, "_eligibility", lambda j: (None, {"eligible": j != "bid", "tagged_rows": 7}))
    r = dcs.pid_jobs_for_project("dcs_test")
    assert r["match"]["job_id"] == "j1" and r["match"]["revision"] == "Rev.B"              # 띄어쓰기 · 붙임표 · 대소문자 무시 · 최근 것
    assert [c["job_id"] for c in r["candidates"]] == ["j1", "j0"]                            # 입찰 · 분석 중은 후보가 아니다
    assert dcs.pid_jobs_for_project("NOPE")["match"] is None and dcs.pid_jobs_for_project("")["match"] is None


def test_for_project_endpoint(client, monkeypatch):
    monkeypatch.setattr(dcs, "pid_jobs_for_project", lambda name: {"project": name, "match": None, "candidates": []})
    r = client.get("/dcs/api/for_project?name=X")
    assert r.status_code == 200 and r.json()["project"] == "X"


# ---------------------------------------------------------------- LOGIC 창 ↔ DCS 창 — 화면 코드가 그 길을 갖는가

def test_logic_screen_opens_graphic_and_posts_tag_states():
    html = (STATIC / "logic.html").read_text(encoding="utf-8")
    js = (STATIC / "logic.js").read_text(encoding="utf-8")
    page = (STATIC / "dcs.html").read_text(encoding="utf-8")
    assert 'id="dcs-btn"' in html
    assert "/dcs/api/for_project?name=" in js and "kind: \"dcs-states\"" in js and "dcs-ready" in js and "dcs-go" in js
    assert "dcsSendSoon();" in js.split("function paint() {")[1].split("\n", 6)[3]     # 흐름 틀마다 (paint) 보낸다
    assert "function openDcsWindow" in js and "placeOnOtherScreen" in js.split("function dcsPlaceOnOtherScreen")[0] or "getScreenDetails" in js
    assert "logicReady" in page and "applyLogic" in page and "dcs-go" in page and "Q.get('logic')" in page
    # 절전모드 — 그래픽의 사람 값 저장은 보관되고, 서버가 그리는 /render 만 거절한다
    off = (STATIC / "offline.js").read_text(encoding="utf-8")
    assert re.search(r"dcs:\s*/\\/render", off)


def test_row_values_become_tag_states_by_the_words_the_drawing_printed(tmp_path):
    """dcsStates 를 node 로 그대로 돌린다 — 뜻은 행 설명의 낱말로만 (OPEN · TRIP · RUN · NOT TRIP 은 반대)."""
    js = (STATIC / "logic.js").read_text(encoding="utf-8")
    fn = js[js.index("function dcsStates()"):js.index("function dcsSendSoon()")]
    script = """
const L = { mode: "sim", page: 1, analogResPage: 1, analogRes: { nets: { "9": 42.5 }, keys: { "row:9": { unit: "barg" } } },
  values: { "1": 1, "2": 0, "3": 1, "4": 1, "5": 0, "9": 1 },
  sheet: { rows: [ { n: 2, side: "L", net: "1", desc: "PUMP A RUN", kks: "10PAB01AP001" },
                   { n: 3, side: "L", net: "2", desc: "XV OPEN CMD", kks: "10LBA11AA001" },
                   { n: 4, side: "R", net: "3", desc: "NOT TRIP", kks: "10LBA11CP001" },
                   { n: 5, side: "R", net: "4", desc: "LEVEL HH", kks: "10LBA11CL001" },
                   { n: 6, side: "L", net: "5", desc: "NO KKS", kks: "" },
                   { n: 9, side: "L", net: "9", desc: "PRESS", kks: "10LBA11CP009" } ] },
  chain: [ { page: 2, inputs: [], outputs: [ { row: 51 } ] } ] };
const SC = { map: new Map([[2, { _v: { rows: [ { n: 51, side: "R", net: "7", desc: "MOV CLOSE", kks: "10LBA12AA002" } ] } }]]) };
""" + fn + "\nconsole.log(JSON.stringify(dcsStates()));\nL.mode='trace';console.log(JSON.stringify(dcsStates()));\n"
    p = tmp_path / "t.js"; p.write_text(script, encoding="utf-8")
    out = subprocess.run(["node", str(p)], capture_output=True, text=True, check=True).stdout.strip().splitlines()
    st = json.loads(out[0])
    assert st["10PAB01AP001"] == {"state": "run", "s": 1}
    assert st["10LBA11AA001"] == {"open": False, "s": 0}                                    # OPEN 행이 0 → 닫힘
    assert st["10LBA11CP001"] == {"s": 1} and "alarm" not in st["10LBA11CP001"]              # NOT TRIP = 1 은 건강
    assert st["10LBA11CL001"] == {"alarm": True, "s": 1}
    assert st["10LBA11CP009"] == {"s": 1, "v": 42.5, "u": "barg"}                            # 아날로그 공학값
    assert st["10LBA12AA002"] == {"open": False, "s": 1} and "" not in st                  # 캐시된 이웃 시트 · 태그 없는 행은 없다
    assert json.loads(out[1]) == {}                                                           # 시뮬레이션이 아니면 값이 없다
