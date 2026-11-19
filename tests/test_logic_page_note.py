"""2026-11-19 — LOGIC 결과 화면도 도면 칸이 말없이 비지 않는다 (받는 중 · 못 받은 이유 · 다시 받기)."""
from app import paths


def _read(name):
    return paths.resource("app", "static", name).read_text(encoding="utf-8")


def test_logic_viewer_says_waiting_and_why_it_failed():
    js = _read("logic.js")
    assert "function pageNoteWait(page)" in js and "function pageNoteDone(page, url, img)" in js
    assert "도면 그림을 받는 중입니다" in js and "도면 그림을 불러오지 못했습니다" in js and "다시 받기" in js
    i = js.index("async function openSheet(page, opt)")
    body = js[i:i + 3500]
    assert "pageNoteWait(page);" in body and "pageNoteDone(page, url, img)" in body
    assert "Promise.race([im.ready, loaded])" in body          # decode 가 답이 없어도 받은 그림은 건다


def test_note_has_style():
    css = _read("logic.css")
    assert ".lg-page-note" in css and ".lg-page-note.err" in css and ".lg-page-note[hidden]" in css
