"""L77 — 업데이트에 실은 그림 묶음(아미랄 19VA 827장)이 로직 그리기 메뉴에 저절로 저장된다.

처음 목록을 열 때 한 번 들이고, 들인 표시가 있으면 다시 들이지 않는다 (지운 묶음이 되살아나지 않게) · 이미 있는 그림은 덮지 않는다.
"""
from __future__ import annotations

import pytest

from app.logic import draw


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PID_DRAW_SEED", "1")
    draw._SEED_DONE.clear()
    yield tmp_path
    draw._SEED_DONE.clear()


def test_amiral_set_is_in_the_drawing_menu_after_update(seeded):
    items = draw.listing()
    am = [i for i in items if (i.get("set_name") or "").startswith("AMIRAL")]
    assert len(am) == 827 and len({i["set"] for i in am}) == 1
    assert sum(1 for i in am if i.get("typical")) == 8
    assert any(i.get("sheet_no") == "HH10_G144" for i in am)


def test_seed_installs_once_and_never_overwrites(seeded):
    items = draw.listing()
    one = next(i for i in items if i.get("sheet_no") == "HH10_G144")
    doc = draw.load(one["id"])
    doc["title"] = "사람이 고친 제목"
    draw.save_new(doc)
    draw._path(items[0]["id"]).unlink()                      # 사람이 한 장을 지움
    draw._SEED_DONE.clear()                                  # 서버를 다시 켠 것처럼
    again = draw.listing()
    assert len(again) == len(items) - 1, "지운 그림이 되살아나지 않는다"
    assert draw.load(one["id"])["title"] == "사람이 고친 제목"


def test_seed_switch_off(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PID_DRAW_SEED", "0")
    draw._SEED_DONE.clear()
    assert draw.listing() == []
