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
