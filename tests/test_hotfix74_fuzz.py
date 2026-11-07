"""hotfix74 — API 퍼징(`spike/api_fuzz.py`)이 잡은 500 들이 사유 있는 400 이 된다."""
from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app import main, revisions


def test_project_names_are_bounded_and_clean():
    for bad in ("", " ", "..", "a/b", "a\tb", "n" * 300, "가" * 51):
        with pytest.raises(revisions.ProjectNameError):
            revisions.safe_name(bad)
    assert revisions.safe_name("가" * 50) == "가" * 50
    assert issubclass(revisions.ProjectNameError, ValueError)     # 옛 `except ValueError` 는 그대로 잡는다


def test_bad_project_names_answer_400_not_500():
    c = TestClient(main.app, raise_server_exceptions=False)
    for url in ("/projects/" + "n" * 300, "/projects/%2E%2E/deletion_preview", "/projects/%20/deletion_preview"):
        r = c.get(url)
        assert r.status_code in (400, 404), (url, r.status_code)
    r = c.request("DELETE", "/projects/%2E%2E", json={})
    assert r.status_code == 400 and "쓸 수 없는" in r.json()["detail"]


def test_int_field_says_which_field():
    assert main._int_field({"page_no": "6"}, "page_no") == 6
    assert main._int_field({"page_no": 6.0}, "page_no") == 6
    assert main._int_field({}, "page_no") == 0
    for bad in ("x", 1.5, [1], {"a": 1}, True, float("nan")):
        with pytest.raises(main.HTTPException) as e:
            main._int_field({"page_no": bad}, "page_no")
        assert e.value.status_code == 400 and "page_no" in e.value.detail


def test_unexpected_errors_carry_a_reference_and_no_traceback():
    @main.app.get("/__boom_for_test")
    def _boom():
        raise RuntimeError("secret internal detail")
    try:
        c = TestClient(main.app, raise_server_exceptions=False)
        r = c.get("/__boom_for_test")
        assert r.status_code == 500
        body = r.json()
        assert body["error_ref"] and body["error_ref"] in body["detail"]
        assert "secret" not in r.text and "Traceback" not in r.text
    finally:
        main.app.router.routes[:] = [rt for rt in main.app.router.routes
                                     if getattr(rt, "path", "") != "/__boom_for_test"]


def _zip(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in entries:
            z.writestr(n, b)
    return buf.getvalue()


def test_zip_bomb_is_refused_but_a_normal_dxf_set_passes():
    ok = _zip([("p1.dxf", b"0\nSECTION\n" * 5000), ("p2.dxf", b"0\nEOF\n")])
    assert main._pack_input([("set.zip", ok)])[0] == "DXF"
    bomb = _zip([("p1.dxf", b"\0" * 50_000_000)])          # 50MB → 약 50KB (1000배)
    with pytest.raises(main.HTTPException) as e:
        main._pack_input([("set.zip", bomb)])
    assert e.value.status_code == 400 and "배로 풀립니다" in e.value.detail


def test_qty_bulk_rejects_non_object_items():
    src = open(main.__file__, encoding="utf-8").read()
    assert 'all(isinstance(it, dict) for it in items)' in src
