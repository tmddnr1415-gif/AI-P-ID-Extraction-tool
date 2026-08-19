"""Drive the real UI and check that edits survive everything a reviewer does.

`test_determinism.py` proves the merge rules at the storage layer.  This proves
the layer above it, where the failures are different in kind: a re-render that
drops `user_json`, a filter that rebuilds rows from a stale array, a tab switch
that reloads from the server and loses an unsaved blur.  None of those show up
in a unit test, and all of them are one line of JavaScript away.

Each of the seven steps asserts separately and names itself in the failure, so a
red run says which interaction broke rather than "the UI is wrong".

Run with `pytest -q -m ui`.  Needs a server; it starts its own on a free port
and reuses `app/_data/app.db`, so it does not re-analyse.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
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


@pytest.fixture(scope="module")
def server():
    """A server on its own port, reusing whatever is already analysed."""
    db = ROOT / "app" / "_data" / "app.db"
    if not db.exists():
        pytest.skip("no analysis in app/_data/app.db; run ./run.sh and upload a PDF")
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
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
    return done[0]["id"]


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
    page.click("#row-copy")
    page.wait_for_timeout(500)
    page.click("#row-add")
    page.wait_for_timeout(500)
    added = page.evaluate(
        "() => [...document.querySelectorAll('#body tr')]"
        ".filter(tr => tr.dataset.added === '1').map(tr => tr.dataset.key)")
    assert len(added) >= 2, "step 5: copy and add did not produce new rows"
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
