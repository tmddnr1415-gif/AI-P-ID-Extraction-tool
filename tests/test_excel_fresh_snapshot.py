"""hotfix15 — Excel 은 지금의 데이터로 나간다.

검토 완료를 체크한 뒤의 편집·삭제·마크업이 있으면 Excel 단추가 같은 조건으로 스냅샷을
**새로 찍고** 내려받는다.  고치기 전에는 체크할 때의 스냅샷을 그대로 내려받아 그 뒤의
변경이 파일에 하나도 없었다 (`spike/excel_reflect_check.py` 가 옛 코드에서 다섯 항목
전부 실패로 재현한다).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
DB = (ROOT / "app/db.py").read_text(encoding="utf-8")


def test_mutations_mark_the_snapshot_stale_in_one_place():
    assert JS.count("window.fetch = (url, opts) =>") == 1
    m = re.search(r"const _MUTATES = /(.+)/;", JS)
    pat = re.compile(m.group(1).replace("\\/", "/"))
    for url in ("/jobs/a/rows", "/jobs/a/rows/k?reason=x", "/jobs/a/rows/k/restore",
                "/jobs/a/rows/k/review/C", "/jobs/a/deleted/3", "/jobs/a/axis_overrides"):
        assert pat.search(url), url
    for url in ("/jobs/a/snapshot", "/jobs/a/markup/propose"):
        assert not pat.search(url), url


def test_excel_button_retakes_a_stale_snapshot_before_download():
    click = JS.split('$req("#excel").addEventListener("click", async () => {', 1)[1].split("});", 1)[0]
    assert "S.snapStale && S.snapParams" in click
    assert click.index("takeSnapshot(S.snapParams)") < click.index("/revisions/")


def test_snapshot_itself_uses_merged_values_and_drops_removed_rows():
    snap = DB.split("def snapshot(", 1)[1].split("\ndef ", 1)[0]
    assert "merged_rows(con, job_id)" in snap and 'not r["removed"]' in snap
