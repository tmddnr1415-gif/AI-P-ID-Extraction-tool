"""hotfix63 — 좌/우 경계를 끝까지 · 장별 메모 (도면번호 열쇠 · 같은 프로젝트의 모든 Rev · 지우지 않고 쌓음)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


def test_split_goes_all_the_way():
    init = JS[JS.index("(function initSplit()"):JS.index("function placeScope(")]
    assert "const MIN = 0, GRIP = 7;" in init and "leftCap" not in init.split("hotfix63")[-1]
    assert "paddingLeft" in init                       # 안쪽 여백을 빼야 손잡이가 화면 안에 남는다
    assert 'window.addEventListener("resize", () => clampLeft())' in init
    assert 'v.left != null' in JS                       # 0(왼쪽 끝)도 값이다
    assert "minmax(0, 1fr)" in CSS and "minmax(260px, 1fr)" not in CSS


def test_memo_store_appends_and_shares_across_revisions(tmp_path):
    from app import sheet_memo
    a = sheet_memo.add(tmp_path, "QFE", "jobA", key="1A1Y-00EKG00-M05-0001", text="첫 메모", author="홍길동",
                       revision="Rev.A", page_no=6, drawing_no="1A1Y-00EKG00-M05-0001")
    b = sheet_memo.add(tmp_path, "QFE", "jobB", key="1A1Y-00EKG00-M05-0001", text="", author="",
                       revision="Rev.B", page_no=7, drawing_no="1A1Y-00EKG00-M05-0001")
    es = sheet_memo.entries(sheet_memo.load(tmp_path, "QFE", "jobX"), ["1A1Y-00EKG00-M05-0001"])
    assert [e["text"] for e in es] == ["첫 메모", ""]          # 비워서 저장해도 앞 판은 남는다
    assert (a["seq"], b["seq"]) == (1, 2) and es[-1]["revision"] == "Rev.B"
    assert sheet_memo.key_of("", 12) == "page:12"
    # 묶이지 않은 분석은 그 분석에서만
    sheet_memo.add(tmp_path, "", "loose1", key="X", text="t", author="a", revision="", page_no=1, drawing_no="X")
    assert sheet_memo.entries(sheet_memo.load(tmp_path, "", "loose2"), ["X"]) == []


def test_memo_api_is_separate_from_the_notes_reading():
    # `/notes/{page}` 는 53회차 NOTES 판독 자리 — 사람 메모는 `/memo`
    assert '@app.get("/jobs/{job_id}/memo/{page_no}")' in MAIN and '@app.post("/jobs/{job_id}/memo/{page_no}")' in MAIN
    assert MAIN.count('@app.get("/jobs/{job_id}/notes/{page_no}")') == 1
    body = MAIN[MAIN.index("def _note_aliases("):MAIN.index("def _note_keys(")]
    assert "renumbered" in body                          # 도면번호가 바뀐 장도 같은 메모


def test_memo_opens_from_the_wheel_and_lives_under_the_drawing():
    assert 'id="memo"' in HTML and HTML.index('id="stage"') < HTML.index('id="memo"')
    wheel = JS[JS.index('$req("#stage").addEventListener("wheel"'):][:600]
    assert "scrollHeight" in wheel and "memoOpen(true)" in wheel
    assert "showMemo(page.page_no)" in JS and "fetch(`/jobs/${S.job.id}/memo/${pg}`" in JS
    assert "askAuthor(" in JS[JS.index("async function saveMemo("):JS.index("(function initMemo()")]
