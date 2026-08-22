"""Drive the real UI and check that edits survive everything a reviewer does.

`test_determinism.py` proves the merge rules at the storage layer.  This proves
the layer above it, where the failures are different in kind: a re-render that
drops `user_json`, a filter that rebuilds rows from a stale array, a tab switch
that reloads from the server and loses an unsaved blur.  None of those show up
in a unit test, and all of them are one line of JavaScript away.

Each of the seven steps asserts separately and names itself in the failure, so a
red run says which interaction broke rather than "the UI is wrong".

Run with `pytest -q -m ui`.  Needs a server; it starts its own on a free port
and drives it against a *copy* of `app/_data/app.db`, so it does not re-analyse
and does not write to the database the deliverables are built from.  The copy is
made per session, pointed at with `PID_DATA_DIR`, and deleted afterwards;
`test_zzz_the_suite_left_the_real_database_alone` checks the original came
through byte for byte.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.ui

playwright = pytest.importorskip("playwright.sync_api",
                                 reason="playwright not installed")
from playwright.sync_api import sync_playwright, expect  # noqa: E402

CHROMIUM = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium")

# The drawing set these steps were written against.
PDF_NAME = "pid_total.pdf"

# The five edits the scenario makes, as (column, new value).
EDITS = [
    ("qty", "7"),
    ("type", "UI-TYPE-A"),
    ("vendor_supply", "UI-VENDOR"),
    ("tag_no", "UI-TAG-01"),
    ("description", "UI 편집 확인"),
]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


REAL_DB = ROOT / "app" / "_data" / "app.db"


def _sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


@pytest.fixture(scope="session")
def real_db_before():
    """The untouched database's digest, taken before anything starts."""
    if not REAL_DB.exists():
        pytest.skip("no analysis in app/_data/app.db; run ./run.sh and upload a PDF")
    return _sha(REAL_DB)


@pytest.fixture(scope="session")
def data_root(real_db_before, tmp_path_factory):
    """A throwaway writing root holding a copy of the analysis.

    Only `app.db` is copied.  The uploaded PDF is not: the job row stores its
    absolute path, so the server opens the original where it already is, and
    opening a file to render a page does not change it.  Everything the run
    *writes* - exports, diagnostics, revisions - lands in here and goes away.
    """
    root = tmp_path_factory.mktemp("pid_data")
    shutil.copyfile(REAL_DB, root / "app.db")
    yield root
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture(scope="module")
def server(data_root):
    """A server on its own port, driven against the copy."""
    port = _free_port()
    env = dict(os.environ, PID_DATA_DIR=str(data_root))
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    import urllib.request
    for _ in range(120):
        try:
            urllib.request.urlopen(base + "/jobs", timeout=1).read()
            break
        except Exception:
            time.sleep(0.5)
    else:
        proc.kill()
        pytest.fail("server did not come up")
    yield base
    proc.terminate()
    proc.wait(timeout=20)


@pytest.fixture(scope="module")
def job_id(server):
    import urllib.request
    jobs = json.loads(urllib.request.urlopen(server + "/jobs").read())
    done = [j for j in jobs if j["status"] == "done"]
    if not done:
        pytest.skip("no completed analysis to review")
    # These steps are written against this repository's own drawing set, so the
    # job is chosen by the PDF rather than by whichever analysis ran last.  The
    # database holds more than one project now, and taking the newest job made
    # step 5 and step 11 fail against a document they were never about.
    own = [j for j in done if j["pdf_name"] == PDF_NAME]
    return (own or done)[0]["id"]


@pytest.fixture(scope="module")
def page(server, job_id):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROMIUM)
        pg = browser.new_page(viewport={"width": 1720, "height": 1000})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(f"{server}/#{job_id}")
        pg.wait_for_selector("#body tr", timeout=120_000)
        pg.wait_for_timeout(1200)
        pg.errors = errors
        yield pg
        browser.close()


def _cell(page, key, col):
    """The td for one row/column, by the column's position in the header."""
    idx = page.evaluate(
        "col => [...document.querySelectorAll('#head th')]"
        ".findIndex(t => t.dataset.col === col)", col)
    assert idx >= 0, f"no column '{col}' in the grid header"
    return page.locator(f'#body tr[data-key="{key}"] td').nth(idx)


def _values(page, keys, col):
    return page.evaluate(
        """([keys, col]) => {
          const i = [...document.querySelectorAll('#head th')]
            .findIndex(t => t.dataset.col === col);
          return keys.map(k => {
            const tr = document.querySelector(`#body tr[data-key="${k}"]`);
            return tr ? tr.children[i].textContent : null;
          });
        }""", [keys, col])


@pytest.fixture(scope="module")
def edited(page):
    """Step 1 - edit five rows, one column each, and read back what stuck."""
    # Field rows only.  The five columns exercised here all exist in the
    # instrument form; the valve form has no Vendor column at all, so editing a
    # MOV row's Vendor would test the client's template rather than this app.
    # Such an edit is stored and reported in the export MANIFEST as
    # `unmapped_values` - see test_step6_reports_unmappable_edits.
    page.evaluate(
        "() => [...document.querySelectorAll('#tabs button')]"
        ".find(b => b.textContent.startsWith('Field')).click()")
    page.wait_for_timeout(500)
    # Rows that are struck out are deliberately not editable, and this suite
    # strikes one out in step 5 - so on a database it has already run against,
    # taking "the first five rows" can pick one of its own casualties and the
    # failure looks like an editing bug.  Take five live ones.
    keys = page.evaluate(
        "[...document.querySelectorAll('#body tr')]"
        ".filter(tr => !tr.classList.contains('deleted')"
        "           && !tr.classList.contains('added'))"
        ".slice(0, 5).map(tr => tr.dataset.key)")
    assert len(keys) == 5, "need five live Field rows to edit"
    for key, (col, value) in zip(keys, EDITS):
        cell = _cell(page, key, col)
        cell.click()
        page.keyboard.press("Control+A")
        page.keyboard.type(value)
        page.keyboard.press("Enter")
        page.wait_for_timeout(250)
    made = {k: (c, v) for k, (c, v) in zip(keys, EDITS)}
    for key, (col, value) in made.items():
        assert _cell(page, key, col).text_content().strip() == value, (
            f"step 1: edit to {col} on {key} did not stick in the grid")
    return made


def test_step1_edits_are_saved_server_side(page, edited, server, job_id):
    import urllib.request
    rows = {r["key"]: r for r in json.loads(
        urllib.request.urlopen(f"{server}/jobs/{job_id}/rows?tab=ALL").read())}
    for key, (col, value) in edited.items():
        assert col in rows[key]["user"], f"step 1: {col} not stored in user_values"
        assert str(rows[key]["user"][col]) == value.lstrip("0") or \
            str(rows[key]["user"][col]) == value, \
            f"step 1: {col} stored as {rows[key]['user'][col]!r}, expected {value!r}"


def test_step2_survives_page_navigation(page, edited):
    """Move to another sheet and back; the grid must not lose the edits."""
    first = page.eval_on_selector("#page-select", "s => s.value")
    other = page.evaluate(
        "s => [...document.querySelectorAll('#page-select option')]"
        ".map(o => o.value).find(v => v !== s)", first)
    page.select_option("#page-select", other)
    page.wait_for_timeout(900)
    page.select_option("#page-select", first)
    page.wait_for_timeout(900)
    for key, (col, value) in edited.items():
        assert _cell(page, key, col).text_content().strip() == value, \
            f"step 2: {col} lost after page navigation"


def test_step3_survives_origin_filter(page, edited):
    # Which origins exist depends on whether an answer key was supplied, so the
    # test picks one that is actually on the menu rather than naming MATCHED,
    # which only verification mode produces.
    origin = page.evaluate(
        "[...document.querySelectorAll('#origin-filter option')]"
        ".map(o => o.value).find(v => v)")
    assert origin, "the origin filter has nothing to choose"
    page.select_option("#origin-filter", origin)
    page.wait_for_timeout(400)
    page.select_option("#origin-filter", "")
    page.wait_for_timeout(400)
    for key, (col, value) in edited.items():
        assert _cell(page, key, col).text_content().strip() == value, \
            f"step 3: {col} lost after applying and clearing the origin filter"


def test_step4_survives_tab_switching(page, edited):
    for label in ("Field", "MOV", "Field", "전체"):
        page.evaluate(
            "l => [...document.querySelectorAll('#tabs button')]"
            ".find(b => b.textContent.startsWith(l)).click()", label)
        page.wait_for_timeout(400)
    for key, (col, value) in edited.items():
        assert _cell(page, key, col).text_content().strip() == value, \
            f"step 4: {col} lost after Field -> MOV -> Field -> 전체"


# What the grid was showing, for a failure message that says more than a count.
_ADD_STATE = """() => ({
  tab: S.tab, page: S.page && S.page.page_no, sel: S.sel,
  search: S.filter || null, origin: S.originFilter || null,
  drawing: S.drawing || null, grade: S.gradeFilter, reason: S.reasonFilter,
  onlyReview: S.onlyReview, rows_in_state: S.rows.length,
  added_in_state: S.rows.filter(r => r.added).map(r => r.key),
  added_in_dom: [...document.querySelectorAll('#body tr')]
    .filter(tr => tr.dataset.added === '1').map(tr => tr.dataset.key),
})"""

# Both row-creating buttons finish with a round trip and a re-render, so the test
# waits for the rows rather than for a stopwatch.  A fixed 500ms read the *previous*
# render often enough to look like '＋행' does nothing - the server had the row and
# the grid did not have it yet.
_ADDED_KEYS = ("() => [...document.querySelectorAll('#body tr')]"
               ".filter(tr => tr.dataset.added === '1').map(tr => tr.dataset.key)")


def _wait_for_added(page, want: int) -> None:
    """Wait until the grid shows `want` reviewer-added rows; never assert here."""
    try:
        page.wait_for_function(
            "n => [...document.querySelectorAll('#body tr')]"
            ".filter(tr => tr.dataset.added === '1').length >= n",
            arg=want, timeout=15_000)
    except Exception:
        pass          # the caller's assertion reports what is actually there


def test_step5_survives_row_add_copy_delete(page, edited, server, job_id):
    """Adding, duplicating and dropping rows must not disturb other rows.

    Row add / copy / delete are reviewer actions on the *list*, so they go
    through the same user-value layer; what matters here is that touching one
    row leaves the other four alone.
    """
    keys = list(edited)
    page.evaluate("k => document.querySelector(`#body tr[data-key='${k}']`).click()",
                  keys[0])
    page.wait_for_timeout(200)
    before = page.evaluate(_ADDED_KEYS)
    page.click("#row-copy")
    _wait_for_added(page, len(before) + 1)
    # '＋행' only arms the point pick - the row is created when the reviewer says
    # where it belongs, or cancels the pick.  Clicking the button and counting
    # rows straight after asserts a step the UI does not have; this test used to
    # pass that way only because the database still held rows an earlier run had
    # left behind, which is the same trap [0-1] found in the deliverable.
    page.click("#row-add")
    page.wait_for_selector("#pick-note:not(.hidden)")
    page.click("#pick-cancel")
    _wait_for_added(page, len(before) + 2)
    added = [k for k in page.evaluate(_ADDED_KEYS) if k not in before]
    assert len(added) == 2, (
        "step 5: copy and add produced "
        f"{len(added)} rows, not 2 — {page.evaluate(_ADD_STATE)}")
    page.evaluate("k => document.querySelector(`#body tr[data-key='${k}']`).click()",
                  added[0])
    page.wait_for_timeout(200)
    page.click("#row-delete")
    page.wait_for_timeout(500)
    for key, (col, value) in edited.items():
        assert _cell(page, key, col).text_content().strip() == value, \
            f"step 5: {col} disturbed by add / copy / delete"


def test_step6_edits_reach_the_excel(page, edited, server, job_id, tmp_path):
    """Gate, export, and find the five edited values in the workbook cells."""
    import urllib.request
    page.check("#gate-check")
    page.wait_for_timeout(1500)
    rev = page.evaluate("() => window.__rev || null")
    assert rev, "step 6: checking the gate did not produce a revision"

    data = urllib.request.urlopen(f"{server}/revisions/{rev}/excel").read()
    zip_path = tmp_path / "out.zip"
    zip_path.write_bytes(data)
    import openpyxl
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if n.endswith(".xlsx")]
        assert names, "step 6: the export contained no workbook"
        found = set()
        for name in names:
            z.extract(name, tmp_path)
            wb = openpyxl.load_workbook(tmp_path / name)
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    for cell in row:
                        if isinstance(cell, str) and cell in {v for _, v in EDITS}:
                            found.add(cell)
                        elif cell == 7:
                            found.add("7")
    expected = {v for _, v in EDITS}
    missing = expected - found
    assert not missing, f"step 6: these edits never reached a cell: {sorted(missing)}"


def test_step6_reports_unmappable_edits(page, edited, server, job_id, tmp_path):
    """An edit the target form cannot carry must be named, not dropped quietly.

    The valve deliverables have no Vendor column, so a Vendor edit on a MOV row
    has nowhere to go.  The export says so in its MANIFEST instead of losing it.
    """
    import urllib.request
    mov = page.evaluate(
        """() => {
          const btn = [...document.querySelectorAll('#tabs button')]
            .find(b => b.textContent.startsWith('MOV'));
          btn.click();
          return null;
        }""")
    page.wait_for_timeout(600)
    key = page.evaluate(
        "() => (document.querySelector('#body tr') || {}).dataset?.key || null")
    if not key:
        pytest.skip("no MOV rows to test the unmapped path with")
    cell = _cell(page, key, "vendor_supply")
    cell.click()
    page.keyboard.press("Control+A")
    page.keyboard.type("UI-UNMAPPABLE")
    page.keyboard.press("Enter")
    page.wait_for_timeout(400)

    req = urllib.request.Request(
        f"{server}/jobs/{job_id}/snapshot", method="POST",
        data=json.dumps({"label": "unmapped"}).encode(),
        headers={"Content-Type": "application/json"})
    rev = json.loads(urllib.request.urlopen(req).read())["revision_id"]
    data = urllib.request.urlopen(f"{server}/revisions/{rev}/excel").read()
    zip_path = tmp_path / "u.zip"
    zip_path.write_bytes(data)
    with zipfile.ZipFile(zip_path) as z:
        manifest = json.loads(z.read("MANIFEST.json"))
    mov_entry = next(w for w in manifest["written"] if w["kind"] == "MOV")
    assert mov_entry.get("unmapped_values", {}).get("vendor_supply"), (
        "step 6b: a Vendor edit on a valve row vanished without being reported; "
        f"manifest said {mov_entry.get('unmapped_values')}")


def test_step7_reanalysis_keeps_edits_and_refreshes_ai(page, edited, server, job_id):
    """The slow one: re-run the engine and check both halves of the split."""
    import urllib.request
    before = {r["key"]: r for r in json.loads(
        urllib.request.urlopen(f"{server}/jobs/{job_id}/rows?tab=ALL").read())}

    req = urllib.request.Request(f"{server}/jobs/{job_id}/reanalyse", method="POST")
    urllib.request.urlopen(req).read()
    # The POST queues the job before it answers, so the first read has to show the
    # new run rather than the finished one before it.  Checking that first is what
    # makes the wait below a wait for *this* analysis: without it a `done` left
    # over from the previous run would end the loop immediately and the rows read
    # afterwards would be the old ones.  Re-analysis writes no revision of its own,
    # so the status is the only thing there is to watch.
    state = json.loads(urllib.request.urlopen(f"{server}/jobs/{job_id}").read())
    assert state["status"] in ("queued", "running"), (
        f"step 7: after POST /reanalyse the job reads {state['status']!r}, so the "
        f"wait below would not be waiting for this run")
    for _ in range(180):
        state = json.loads(urllib.request.urlopen(f"{server}/jobs/{job_id}").read())
        if state["status"] in ("done", "failed"):
            break
        time.sleep(10)
    assert state["status"] == "done", f"step 7: re-analysis {state['status']}"

    after = {r["key"]: r for r in json.loads(
        urllib.request.urlopen(f"{server}/jobs/{job_id}/rows?tab=ALL").read())}
    for key, (col, value) in edited.items():
        assert key in after, f"step 7: row {key} vanished after re-analysis"
        assert col in after[key]["user"], \
            f"step 7: the edit to {col} was lost by re-analysis"
        assert str(after[key]["user"][col]) == value, \
            f"step 7: {col} changed to {after[key]['user'][col]!r}"
        assert after[key]["ai"] == before[key]["ai"], \
            f"step 7: ai_values for {key} should be refreshed identically"


@pytest.mark.ui
def test_step8_review_panel_groups_every_reason_by_axis(page, server, job_id):
    """The panel is the screen's answer to 'what am I being asked to decide'.

    Every reason has to appear under exactly one axis, and the axis totals have to
    add up to the reason totals - a screen that quietly drops a reason is worse
    than no screen.
    """
    import urllib.request
    review = json.loads(
        urllib.request.urlopen(f"{server}/jobs/{job_id}/review").read())
    assert review["axes"], "no review axes came back"
    for axis in review["axes"]:
        assert axis["open"] + axis["done"] == sum(
            c["open"] + c["done"] for c in axis["codes"]), axis["axis"]
    buttons = page.eval_on_selector_all(
        "#review-panel button.axis:not(.clear)", "els => els.length")
    assert buttons == len(review["axes"]), "an axis is missing from the panel"


@pytest.mark.ui
def test_step9_a_reason_filters_the_grid_and_survives_a_reload(page, server, job_id):
    """Axis -> reason -> grid, with the filters in the URL so a link keeps them."""
    # The page fixture is shared, so start from a known view rather than from
    # whatever the test before this one left selected.
    page.goto(f"{server}/#{job_id}")
    page.wait_for_selector("#body tr", timeout=120_000)
    page.wait_for_timeout(1200)
    page.click("#review-panel button.axis:not(.clear)")
    page.wait_for_timeout(500)
    assert page.eval_on_selector_all("#review-codes button.rcode", "e => e.length")
    page.click("#review-codes button.rcode")
    page.wait_for_timeout(500)
    chips = page.eval_on_selector_all(".chip", "els => els.map(e => e.textContent)")
    assert any("축" in c for c in chips) and any("사유" in c for c in chips)
    assert "axis=" in page.evaluate("location.hash")
    before = page.eval_on_selector_all("#body tr", "e => e.length")
    page.goto(page.evaluate("location.href"))
    page.wait_for_selector("#chips .chip", timeout=120_000)
    page.wait_for_timeout(1500)
    assert page.eval_on_selector_all("#body tr", "e => e.length") == before


@pytest.mark.ui
def test_step10_deciding_a_reason_moves_the_progress(page, server, job_id):
    """`확인함` is work: judging the value right is a review, and it has to count."""
    import urllib.request
    # Enter through the URL rather than by clicking: it is the contract a shared
    # link relies on, and it puts the test in a known view whatever ran before.
    review = json.loads(
        urllib.request.urlopen(f"{server}/jobs/{job_id}/review").read())
    axis = next(a for a in review["axes"] if a["open"])
    code = axis["codes"][0]["code"]
    page.goto(f"{server}/#{job_id}?axis={axis['axis']}&code={code}")
    page.wait_for_selector("#body tr", timeout=120_000)
    page.wait_for_timeout(1500)
    page.click("#body tr")
    page.wait_for_timeout(900)
    before = json.loads(
        urllib.request.urlopen(f"{server}/jobs/{job_id}/review").read())
    done_before = sum(a["done"] for a in before["axes"])
    page.click("#evidence button.rstate")           # 확인함
    page.wait_for_timeout(1200)
    after = json.loads(
        urllib.request.urlopen(f"{server}/jobs/{job_id}/review").read())
    done_after = sum(a["done"] for a in after["axes"])
    assert done_after != done_before, "deciding a reason did not move the count"
    page.click("#evidence button.rstate")           # toggle it back off
    page.wait_for_timeout(1200)


@pytest.mark.ui
def test_step11_bulk_apply_fills_its_group_and_nothing_else(page, server, job_id):
    """`일괄 적용` writes the rows this one is indistinguishable from - no more.

    The reach has to include the sentence.  Drawing and Type alone put the PARTIAL
    rows into fewer, larger groups than the reviewer sees, and those groups also
    contain rows the engine already filled from the drawing - one click would
    overwrite them.  So this drives the real button on the largest PARTIAL group
    and checks both halves: every row of the group filled, every other row of the
    same drawing and Type untouched.
    """
    import urllib.request
    page.on("dialog", lambda d: d.accept())
    page.goto(f"{server}/#{job_id}?gradeFilter=PARTIAL")
    page.wait_for_selector("#body tr", timeout=120_000)
    page.wait_for_timeout(1500)
    target = page.evaluate("""() => {
      const by = {};
      for (const r of S.rows.filter(r => r.values.description_grade === 'PARTIAL')) {
        const k = [r.drawing_no, r.values.type, r.values.description].join('|');
        (by[k] = by[k] || []).push(r);
      }
      const best = Object.values(by).sort((a, b) => b.length - a.length)[0] || [];
      return best.length ? {keys: best.map(r => r.key), n: best.length,
                            dwg: best[0].drawing_no, type: best[0].values.type,
                            was: best[0].values.description} : null;
    }""")
    assert target and target["n"] > 1, "no PARTIAL group with more than one row"
    page.evaluate("k => select(k, true)", target["keys"][0])
    page.wait_for_timeout(1200)
    text = "UI 일괄 확인 " + target["was"]
    page.fill("#cand-input", text)
    page.click("#cand-bulk")
    page.wait_for_timeout(2500)
    rows = json.loads(urllib.request.urlopen(
        f"{server}/jobs/{job_id}/rows?tab=ALL").read())
    rows = rows["rows"] if isinstance(rows, dict) else rows
    filled = [r for r in rows if (r["values"].get("description") or "") == text]
    assert sorted(r["key"] for r in filled) == sorted(target["keys"]), (
        "the bulk apply did not land on exactly its own group")
    others = [r for r in rows if r["drawing_no"] == target["dwg"]
              and r["values"].get("type") == target["type"]
              and r["key"] not in target["keys"]]
    assert all(r["values"].get("description_grade") != "USER_ENTERED"
               for r in others), "rows outside the group were overwritten"
    # Put the group back, so the next run starts where this one did.
    for key in target["keys"]:
        for field in ("description", "description_grade"):
            req = urllib.request.Request(
                f"{server}/jobs/{job_id}/rows/{key}", method="PATCH",
                data=json.dumps({"field": field, "value": ""}).encode(),
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req).read()


def test_step12_a_row_can_be_reported_in_two_answers(page, server, job_id):
    """C-1: press 신고 on a row, choose an axis, write one line, done.

    The point of the test is what it does *not* do: it never types a coordinate,
    a rule name or a value, and the stored record has them anyway.  If the dialog
    ever starts asking for one of those, this fails.
    """
    page.goto(f"{server}/#{job_id}")
    page.wait_for_selector("#body tr", timeout=120_000)
    page.wait_for_timeout(1200)
    page.evaluate("() => closeModal()")
    before = json.loads(urllib.request.urlopen(
        f"{server}/jobs/{job_id}/reports").read())["count"]

    key = page.evaluate("() => S.rows.find(r => !r.deleted && !r.removed).key")
    page.click(f"#body tr[data-key='{key}'] button.mini-rep")
    page.wait_for_selector("#modal:not(.hidden)")
    # exactly two inputs are asked for
    assert page.locator(".rep-what input[type=radio]").count() == 5
    assert page.locator("#modal-body input[type=text], #modal-body textarea").count() == 1
    page.check(".rep-what input[value='DESCRIPTION']")
    page.fill("#rep-detail", "UI 신고 확인 — 발주처 표기와 다릅니다")
    page.click("#rep-save")
    page.wait_for_selector("#modal", state="hidden")

    out = json.loads(urllib.request.urlopen(
        f"{server}/jobs/{job_id}/reports").read())
    assert out["count"] == before + 1
    rec = out["reports"][0]
    assert rec["what"] == "DESCRIPTION"
    assert rec["detail"].startswith("UI 신고 확인")
    cap = rec["capture"]["row"]
    assert cap["identity"]["row_key"] == key
    assert cap["identity"]["page_no"] and rec["drawing_no"]
    assert "ai_values" in cap and "evidence" in cap and "applied_rules" in cap
    assert rec["capture"]["fingerprint"] and rec["capture"]["build"]["version"]
    assert page.locator("#report-n").inner_text() == str(out["count"])

    # C-3: the list shows it, and withdrawing it puts the count back
    page.click("#report-list")
    page.wait_for_selector(".rep-row")
    assert page.locator(".rep-row").count() == out["count"]
    page.once("dialog", lambda d: d.accept())
    page.locator(f".rep-row[data-id='{rec['id']}'] .rep-del").click()
    page.wait_for_timeout(800)
    assert json.loads(urllib.request.urlopen(
        f"{server}/jobs/{job_id}/reports").read())["count"] == before
    page.click("#rep-close")


def test_step13_an_undetected_position_is_reportable_from_the_drawing(
        page, server, job_id):
    """C-2: right-click bare drawing files a report with the geometry there.

    A missed item has no row to report against, which is the whole difficulty:
    the record has to say what *was* drawn at that point instead.
    """
    page.goto(f"{server}/#{job_id}")
    page.wait_for_selector("#body tr", timeout=120_000)
    page.wait_for_timeout(1500)
    # `goto` to the same URL only changes the hash, so the document is not
    # reloaded and whatever the previous step left armed is still armed - step 5
    # ends inside the '＋행' point-picking mode, which swallows clicks on the
    # sheet by design.  Put the page back to rest explicitly.
    page.evaluate("() => { closeModal(); endPick(); }")
    before = json.loads(urllib.request.urlopen(
        f"{server}/jobs/{job_id}/reports").read())["count"]

    # Right-click a spot with no detection on it.  Two things make this awkward
    # with the mouse and neither is about the feature: the sheet is far larger
    # than the viewport, so most of it cannot be clicked without scrolling, and a
    # click that lands on an overlay box is a *different* report (SYMBOL, not
    # MISSED).  So the empty spot is worked out from the overlay's own boxes and
    # a real contextmenu event is dispatched at it - the same handler, the same
    # `ev.clientX/clientY` arithmetic, without driving the scrollbars.
    fired = page.evaluate("""() => {
      const boxes = overlayItems(S.page).map(i => i.rect);
      const clear = (x, y) => !boxes.some(([a, b, c, d]) =>
        x > a - 30 && x < c + 30 && y > b - 30 && y < d + 30);
      const img = document.querySelector('#sheet');
      const r = img.getBoundingClientRect();
      for (let fx = 0.2; fx < 0.9; fx += 0.05)
        for (let fy = 0.2; fy < 0.9; fy += 0.05) {
          if (!clear(S.page.width * fx, S.page.height * fy)) continue;
          img.dispatchEvent(new MouseEvent('contextmenu', {
            bubbles: true, cancelable: true,
            clientX: r.left + r.width * fx, clientY: r.top + r.height * fy}));
          return [fx, fy];
        }
      return null;
    }""")
    assert fired, "every part of this sheet carries a detection"
    page.wait_for_selector("#modal:not(.hidden)")
    assert "검출되지 않은 위치" in page.locator("#modal-title").inner_text()
    page.fill("#rep-detail", "UI 미검출 신고 확인")
    page.click("#rep-save")
    page.wait_for_selector("#modal", state="hidden", timeout=60_000)

    out = json.loads(urllib.request.urlopen(
        f"{server}/jobs/{job_id}/reports").read())
    assert out["count"] == before + 1
    rec = out["reports"][0]
    assert rec["kind"] == "MISSED" and rec["row_key"] == ""
    missed = rec["capture"]["missed"]
    assert len(missed["point"]) == 2
    geom = missed["geometry"]
    assert "paths" in geom and "words" in geom and "detections" in geom
    urllib.request.urlopen(urllib.request.Request(
        f"{server}/reports/{rec['id']}", method="DELETE")).read()


def test_step14_the_diagnostic_export_says_its_size_and_what_it_leaves_out(
        page, server, job_id, tmp_path):
    """D: one button, and the screen states the size and the exclusions."""
    page.goto(f"{server}/#{job_id}")
    page.wait_for_selector("#body tr", timeout=120_000)
    page.wait_for_timeout(1200)
    page.evaluate("() => closeModal()")
    page.click("#diag")
    page.wait_for_selector("#modal:not(.hidden)", timeout=120_000)
    body = page.locator("#modal-body").inner_text()
    assert "MB" in body and "bytes" in body
    assert "빠진 것" in body and "PDF" in body
    href = page.locator("#diag-dl").get_attribute("href")
    raw = urllib.request.urlopen(server + href).read()
    z = zipfile.ZipFile(io.BytesIO(raw))
    names = set(z.namelist())
    assert "MANIFEST.json" in names and "analysis/derived_layout.json" in names
    assert not [n for n in names if n.lower().endswith((".pdf", ".xlsx"))]
    page.click("#diag-close")


def test_step15_the_screen_names_the_build(page, server, job_id):
    """E: which exe this is, readable without opening anything."""
    page.goto(f"{server}/#{job_id}")
    page.wait_for_selector("#build-text", timeout=120_000)
    page.wait_for_timeout(800)
    text = page.locator("#build-text").inner_text()
    info = json.loads(urllib.request.urlopen(server + "/version").read())
    assert f"v{info['version']}" in text
    assert info["built_at"] in text


def test_step16_ctrl_wheel_and_keys_zoom_the_viewer_only(page, server, job_id):
    """[A] The four ways of zooming agree, and the keys stay off the grid.

    Ctrl+wheel has to hold the point under the cursor still - zooming to the
    middle and then hunting for the symbol again is the thing this replaces - and
    Ctrl +/-/0 must not fire while a reviewer is typing, which is why they are
    handled on the viewer rather than on the document.
    """
    page.goto(f"{server}/#{job_id}")
    page.wait_for_selector("#body tr", timeout=120_000)
    page.wait_for_timeout(2000)
    page.evaluate("() => { closeModal(); endPick(); }")

    # The page fixture is shared and selecting a row zooms in to read the bubble
    # (`SYMBOL_ZOOM`), so the viewer is not necessarily at rest.  Press 맞춤 to
    # establish the fitted magnification rather than assuming it.
    page.click("[data-z='0']")
    page.wait_for_timeout(200)
    fitted = page.evaluate("() => S.zoom")
    stage = page.evaluate("() => document.querySelector('#stage').clientWidth")
    natural = page.evaluate("() => S.natural.w")
    assert abs(fitted - (stage - 16) / natural) < 1e-9, "맞춤 is not what fit() computes"

    page.click("#stage")
    assert page.evaluate("() => document.activeElement.id") == "stage"

    # Scrolled to the origin first, so the cursor is over the sheet.  Below 1:1
    # the scroll extent stays the sheet's unscaled size while the sheet paints
    # smaller, so the viewer can be parked in the blank space beyond it - a
    # property of the existing transform-based zoom, not of this test - and a
    # zoom anchored out there is clamped by the browser rather than applied.
    page.evaluate("""() => { const st = document.querySelector('#stage');
                             st.scrollLeft = 0; st.scrollTop = 0; }""")
    page.wait_for_timeout(150)
    box = page.locator("#stage").bounding_box()
    cx, cy = box["x"] + box["width"] * 0.7, box["y"] + box["height"] * 0.3
    under = """([cx, cy]) => {
      const st = document.querySelector('#stage');
      const r = st.getBoundingClientRect();
      return [(st.scrollLeft + cx - r.left) / S.zoom,
              (st.scrollTop + cy - r.top) / S.zoom];
    }"""
    before = page.evaluate(under, [cx, cy])
    page.evaluate("""([cx, cy]) => document.querySelector('#stage').dispatchEvent(
      new WheelEvent('wheel', {deltaY: -120, ctrlKey: true, clientX: cx,
                               clientY: cy, bubbles: true, cancelable: true}))""",
                  [cx, cy])
    page.wait_for_timeout(200)
    after = page.evaluate(under, [cx, cy])
    zoomed = page.evaluate("() => S.zoom")
    step = page.evaluate("() => ZOOM_STEP")
    assert abs(zoomed / fitted - step) < 1e-6, "the wheel does not use the buttons' step"
    # Sub-point, not sub-pixel: scroll offsets are integers, and one device pixel
    # is several sheet points at this magnification.
    assert abs(after[0] - before[0]) < 4 and abs(after[1] - before[1]) < 4, \
        f"the point under the cursor moved: {before} -> {after}"

    page.keyboard.press("Control+Minus")
    page.wait_for_timeout(150)
    assert abs(page.evaluate("() => S.zoom") - fitted) < 1e-6
    page.keyboard.press("Control+Equal")
    page.wait_for_timeout(150)
    assert abs(page.evaluate("() => S.zoom") - zoomed) < 1e-6
    page.keyboard.press("Control+0")
    page.wait_for_timeout(150)
    assert abs(page.evaluate("() => S.zoom") - fitted) < 1e-9, "Ctrl+0 is not 맞춤"

    # not while the reviewer is typing
    page.evaluate("() => { S.zoom = 0.5; applyZoom(); }")
    page.click("#filter")
    page.keyboard.press("Control+Equal")
    page.wait_for_timeout(200)
    assert page.evaluate("() => S.zoom") == 0.5, \
        "the viewer took a key while the search box had focus"
    page.fill("#filter", "")

    # kept across pages, and `open()` - which is where re-analysis lands - refits
    page.click("#stage")
    page.evaluate("() => { S.zoom = 0.42; applyZoom(); }")
    other = page.evaluate("() => S.pages.find(p => p.page_no !== S.page.page_no).page_no")
    page.select_option("#page-select", str(other))
    page.wait_for_timeout(3000)
    assert page.evaluate("() => S.zoom") == 0.42, "changing page threw the zoom away"
    page.evaluate("j => open(j)", job_id)
    page.wait_for_timeout(4000)
    assert abs(page.evaluate("() => S.zoom") - fitted) < 1e-9, \
        "opening a job did not start fitted"


def test_step17_column_filters_and_with_everything_and_ride_in_the_url(
        page, server, job_id):
    """[B] Seven dropdowns, ANDed with each other and with the filters that
    already existed, visible as chips, and reproduced by the URL.

    The two defects this class of filter has had before are both checked: a
    condition that outlives a move back to the bare job id, and one that applies
    on a tab where nothing on screen says why the grid is short.
    """
    page.goto(f"{server}/#{job_id}")
    page.wait_for_selector("#body tr", timeout=120_000)
    page.wait_for_timeout(2000)
    page.evaluate("() => { closeModal(); endPick(); }")
    blank = page.evaluate("() => BLANK")
    total = page.evaluate("() => S.rows.length")

    cols = page.eval_on_selector_all("button.colf", "e => e.map(b => b.dataset.col)")
    assert cols == ["page_no", "pid_no", "type", "valve_type", "qty",
                    "system", "vendor_supply"]

    def choose(col, values):
        page.click(f"button.colf[data-col='{col}']")
        page.wait_for_selector("#colmenu:not(.hidden)")
        page.click("#cm-none")
        page.evaluate("""([vals]) => {
          for (const c of document.querySelectorAll('#colmenu .cm-v'))
            if (vals.includes(c._value)) c.checked = true;
        }""", [values])
        page.click("#cm-apply")
        page.wait_for_timeout(400)

    # the list is derived from the data, and its counts are the data's counts
    page.click("button.colf[data-col='type']")
    page.wait_for_selector("#colmenu:not(.hidden)")
    listed = page.eval_on_selector_all("#colmenu .cm-v", "e => e.map(c => c._value)")
    counts = page.eval_on_selector_all("#colmenu .cm-list .n", "e => e.map(n => +n.textContent)")
    assert listed and len(listed) == len(counts)
    for value, n in zip(listed, counts):
        real = page.evaluate(
            """([v, blank]) => S.rows.filter(r =>
                 (String(cellValue(r, 'type') ?? '') || blank) === v).length""",
            [value, blank])
        assert real == n, f"{value}: dropdown says {n}, the data says {real}"
    page.keyboard.press("Escape")

    choose("type", ["PIT"])
    shown = page.eval_on_selector_all("#body tr", "e => e.length")
    assert shown == page.evaluate("() => S.rows.filter(r => r.values.type === 'PIT').length")
    assert page.locator("th.filtered").count() == 1, "the filtered header is not marked"
    assert page.locator("#count").inner_text() == f"표시 {shown} / 전체 {total}"

    choose("page_no", ["6"])
    n_and = page.eval_on_selector_all("#body tr", "e => e.length")
    assert n_and == page.evaluate(
        "() => S.rows.filter(r => r.values.type === 'PIT' && r.page_no === 6).length")

    # ANDed with the tab, the grade and the free-text box as well
    page.evaluate("""() => { S.tab = 'FIELD'; S.gradeFilter = 'PARTIAL';
                             S.filter = 'HP STEAM'; syncUrl(); buildTabs(); renderGrid(); }""")
    page.wait_for_timeout(400)
    n_all = page.eval_on_selector_all("#body tr", "e => e.length")
    assert n_all == page.evaluate("""() => S.rows.filter(r => r.tab === 'FIELD'
      && r.values.type === 'PIT' && r.page_no === 6
      && r.values.description_grade === 'PARTIAL'
      && SEARCH_COLS.some(k => String(cellValue(r, k)).toLowerCase()
                                 .includes('hp steam'))).length""")
    chips = page.eval_on_selector_all(".chip", "e => e.map(c => c.textContent)")
    assert any("Page" in c for c in chips) and any("Type" in c for c in chips), \
        "a filtered column left no chip to clear it from"

    # the URL carries them, and reproduces the grid
    url = page.evaluate("() => location.hash")
    assert "col.type=PIT" in url and "col.page_no=6" in url
    page.goto(f"{server}/{url}")
    page.wait_for_selector("#body tr", timeout=120_000)
    page.wait_for_timeout(2000)
    assert page.eval_on_selector_all("#body tr", "e => e.length") == n_all
    assert page.evaluate("() => S.colFilters.type") == ["PIT"]

    # the blank choice survives the round trip - it is most of Vendor
    page.goto(f"{server}/#{job_id}")
    page.wait_for_selector("#body tr")
    page.wait_for_timeout(1500)
    choose("vendor_supply", [blank])
    blank_rows = page.eval_on_selector_all("#body tr", "e => e.length")
    assert blank_rows == page.evaluate(
        "() => S.rows.filter(r => !(r.values.vendor_supply || '')).length")
    page.goto(f"{server}/{page.evaluate('() => location.hash')}")
    page.wait_for_selector("#body tr")
    page.wait_for_timeout(2000)
    assert page.evaluate("() => S.colFilters.vendor_supply") == [blank]

    # back to the bare job id leaves nothing standing - the defect that was
    # fixed once already for the other filters
    page.evaluate("j => { location.hash = j; }", job_id)
    page.wait_for_timeout(1500)
    assert page.evaluate("() => Object.keys(S.colFilters).length") == 0
    assert page.locator(".chip").count() == 0
    assert page.locator("th.filtered").count() == 0
    assert page.eval_on_selector_all("#body tr", "e => e.length") == total


def test_step18_the_search_box_looks_in_the_columns_it_names(page, server, job_id):
    """The drawing number is searchable, and a column name is not a match.

    Both were faults of searching `JSON.stringify(row.values)`: the drawing
    number is not in `values` at all, and stringifying an object puts its key
    names into the haystack.
    """
    page.goto(f"{server}/#{job_id}")
    page.wait_for_selector("#body tr", timeout=120_000)
    page.wait_for_timeout(2000)
    page.evaluate("() => { closeModal(); endPick(); }")
    total = page.evaluate("() => S.rows.length")

    # A drawing that has rows: the first *page* with a number is the drawing-list
    # sheet, which has none, and searching it correctly finds nothing.
    dwg = page.evaluate("() => cellValue(S.rows[0], 'pid_no')")
    assert dwg
    page.fill("#filter", dwg)
    page.wait_for_timeout(500)
    hits = page.eval_on_selector_all("#body tr", "e => e.length")
    assert hits > 0, f"searching the drawing number {dwg} still finds nothing"
    assert hits == page.evaluate(
        "d => S.rows.filter(r => cellValue(r, 'pid_no') === d).length", dwg)

    for name in ("type", "qty", "description_grade"):
        page.fill("#filter", name)
        page.wait_for_timeout(400)
        assert page.eval_on_selector_all("#body tr", "e => e.length") < total, \
            f"the column name {name!r} still matches every row"
    page.fill("#filter", "")


def test_zzz_the_suite_left_the_real_database_alone(real_db_before, data_root):
    """The steps above ran against a copy; the real database must be untouched.

    This is the check the round asked for, and it is placed last on purpose - the
    name sorts after every step so it sees the whole suite's damage, if any.  It
    compares bytes rather than row counts because the failure this guards against
    is not "a row appeared" but "anything at all was written": a revision
    snapshot, a feedback entry, a review mark, a `user_json` update.

    Until the copy existed, a single `-m ui` run left six overwritten cells, one
    hand-added row and two snapshots in the file the deliverables are built from,
    and nothing in the repository showed it - `app/_data/` is gitignored, so
    `git status` stayed clean the whole time.
    """
    assert _sha(REAL_DB) == real_db_before, (
        "app/_data/app.db changed while the UI suite ran; the server was not "
        "pointed at the copy")
    copy = data_root / "app.db"
    assert copy.exists(), "the copy the server ran against is missing"
    assert copy.resolve() != REAL_DB.resolve(), "the copy is the original"
    # And the copy did change - otherwise the suite proved nothing, because a
    # server that never wrote anywhere would also leave the original alone.
    assert _sha(copy) != real_db_before, (
        "the copy is byte-identical to the original: the steps above wrote "
        "nothing, so this test cannot tell isolation from inactivity")
