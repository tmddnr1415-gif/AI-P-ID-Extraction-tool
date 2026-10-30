"""L78 — 시운전 단계 · System Description(Word) · 끊긴 선 끝을 같은 그물 몸통까지 늘이기 · 씨앗 판 올리기."""
from __future__ import annotations

import gzip
import io
import json
from pathlib import Path

import pytest

from app.logic import api, behavior, commission, draw, store
from tests.test_logic_l32_sequence import _client, _job, _sheet, _B, _P
from tests.test_logic_l35_understand import _latched, _pair

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PID_LOGIC_WARM", "0")
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()


def test_steps_follow_the_learned_behaviour_and_simulate():
    sheets = _latched()
    learned = behavior.learn(sheets, {})
    st = commission.structure({"sheets": sheets}, learned)
    steps = commission.steps_of(st["equips"]["FAN A"]["items"])
    kinds = [s["kind"] for s in steps]
    assert kinds[0] == "base" and "perm" in kinds and "hold" in kinds and "stop" in kinds and "block" in kinds
    perm = [s for s in steps if s["kind"] == "perm"]
    assert [s["expect"] for s in perm] == [0] * (len(perm) - 1) + [1]      # 마지막 조건에서만 켜진다
    r = commission.run_steps(sheets, steps, {})
    assert r["status"] == "pass", [(s["title"], s.get("got"), s.get("why")) for s in r["steps"]]


def test_pair_step_warns_when_opposite_commands_can_both_run():
    learned = behavior.learn(_pair(False), {})
    st = commission.structure({"sheets": _pair(False)}, learned)
    r = commission.run_steps(_pair(False), commission.steps_of(st["equips"]["VALVE"]["items"]), {})
    assert [s["status"] for s in r["steps"] if s["kind"] == "pair"] == ["warn"]


def test_condition_from_another_sheet_is_expanded_to_its_real_signals():
    """G002 의 START 는 G001 출력(FM G001-90)을 받는다 → 시운전 단계는 G001 의 허가 · 누름단추까지 펼친다."""
    g1 = _latched()[0]
    g1["rows"][-1]["to"] = "G002-5"
    g2 = _sheet(2, "G002", [{"n": 5, "side": "L", "net": "in", "desc": "FAN A START CMD", "fm": "G001-90"},
                            {"n": 91, "side": "R", "net": "out", "desc": "FAN A START", "to": ""}],
                {"P": _B("or")}, [_P("P", "in", "in"), _P("P", "out", "out")], title="FAN A RELAY")
    sheets = [g1, g2]
    from app.logic import analyse
    analyse._cross_refs(sheets)
    learned = behavior.learn(sheets, {})
    x = dict(behavior.learn_one(sheets, 2, 91, 1, {}), sheet="G002", action="START", desc="FAN A START")
    assert x["reached"] and {k for f in x["forces"].values() for k in f} == {"row:5"}   # 이 장만 보면 앞 시트 출력 하나
    resolve = commission.resolver({"sheets": sheets}, learned, sheets, {}, 10)
    steps = commission.steps_of([x], None, resolve)
    perm = [s for s in steps if s["kind"] == "perm"]
    assert len(perm) >= 2 and all(s["added"]["page"] == 1 for s in perm)
    r = commission.run_steps(sheets, steps, {})
    assert r["steps"][len(perm)]["status"] == "pass"


def test_docx_and_api():
    job = _job(_latched())
    c = _client()
    d = c.get(f"/logic/api/jobs/{job}/commission").json()
    assert d["systems"] and d["dangling"].startswith("로직(G)")
    s = c.get(f"/logic/api/jobs/{job}/commission/steps", params={"equip": "FAN A"}).json()
    assert s["steps"]
    r = c.post(f"/logic/api/jobs/{job}/commission/run", json={"equip": "FAN A"}).json()
    assert r["status"] == "pass"
    learned = behavior.learn(_latched(), {})
    data = commission.docx_bytes({"sheets": _latched()}, learned, {"name": "toy"})
    from docx import Document
    text = "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    assert "System Description" in text and "시운전 절차" in text and "FAN A" in text
    assert c.get("/logic/commission").status_code == 200


def test_mend_extends_a_short_end_to_the_same_net_body():
    segs = [[100, 50, 100, 98.44], [20, 100, 200, 100]]           # 세로선이 가로선 몸통 1.56pt 앞에서 멈춤 (19VA QM02_G001)
    out = draw._mend(segs, [])
    assert any(sg[0] == 100 and max(sg[1], sg[3]) == 100 for sg in out)


def test_seed_revision_replaces_only_untouched_drawings(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DRAW_SEED", "1")
    sd = tmp_path / "seed"
    sd.mkdir()
    monkeypatch.setattr(draw, "seed_dir", lambda: sd)
    a = {"id": "aaaaaaaaaaaa", "name": "A", "saves": 0, "updated": 1.0, "blocks": [], "wires": []}
    b = {"id": "bbbbbbbbbbbb", "name": "B", "saves": 0, "updated": 1.0, "blocks": [], "wires": []}

    def pack(rev, docs):
        (sd / "s.json.gz").write_bytes(gzip.compress(json.dumps({"rev": rev, "docs": docs}).encode()))
        draw._SEED_DONE.clear()
        return draw.install_seeds()
    pack(1, [a, b])
    cur = draw.read_doc(draw._path(b["id"]))
    cur.update(saves=1, updated=2.0, name="사람이 고침")
    draw.save_new(cur)
    a2 = dict(a, wires=[{"id": "w", "pts": [[0, 0], [1, 0]]}])
    b2 = dict(b, wires=[{"id": "w", "pts": [[0, 0], [1, 0]]}])
    out = pack(2, [a2, b2])
    assert out and out[0]["updated"] == 1
    assert draw.read_doc(draw._path(a["id"]))["wires"]                  # 손대지 않은 그림은 새 판
    assert draw.read_doc(draw._path(b["id"]))["name"] == "사람이 고침"   # 사람이 고친 그림은 그대로
