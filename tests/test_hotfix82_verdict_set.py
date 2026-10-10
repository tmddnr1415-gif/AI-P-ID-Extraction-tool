"""hotfix82 — 재학습 경로: VOC 함의 O/X 평가 · 마크업 → 프로젝트 정답지 → 결과를 그 정답지로 잰다 (참고축)."""
from __future__ import annotations

import ast
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "spike"))


def _recs():
    return [
        {"id": "VOC-1", "source": "VERDICT", "created_ts": 1, "author": "홍", "category": "VERDICT", "reason": "O 1",
         "context": {"project": "QFE", "revision": "Rev.B", "drawing_no": "D-1"},
         "rows": [{"identity": {"drawing_no": "D-1", "page_no": 6, "type": "PIT", "tag_no": "T1", "rect": [10, 10, 20, 30]}, "verdict": "O"},
                  {"identity": {"drawing_no": "D-1", "page_no": 6, "type": "PI", "tag_no": "", "rect": [100, 100, 120, 130]}, "verdict": "X"}]},
        {"id": "VOC-2", "source": "VERDICT", "created_ts": 2, "author": "홍", "category": "VERDICT", "reason": "X",
         "context": {"project": "QFE"},
         "rows": [{"identity": {"drawing_no": "D-1", "page_no": 6, "type": "PIT", "tag_no": "T1", "rect": [10, 10, 20, 30]}, "verdict": "X"}]},
        {"id": "VOC-3", "source": "MARKUP_ADD", "created_ts": 3, "author": "김", "category": "MISSING", "reason": "못 읽음",
         "context": {"project": "QFE", "drawing_no": "D-2", "page_no": 7}, "rect": [50, 50, 70, 80],
         "rows": [{"identity": {"drawing_no": "D-2", "page_no": 7, "type": "LIT", "tag_no": "", "rect": [50, 50, 70, 80]}}]},
        {"id": "VOC-4", "source": "MARKUP_REJECT", "created_ts": 4, "author": "김", "category": "FALSE_POSITIVE", "reason": "주석",
         "context": {"project": "QFE"},
         "rows": [{"identity": {"drawing_no": "D-2", "page_no": 7, "type": "TI", "tag_no": "T9", "rect": [0, 0, 5, 5]}}]},
        {"id": "VOC-5", "source": "GENERAL", "created_ts": 5, "category": "UI", "reason": "느림", "context": {"project": "QFE"}},
        {"id": "VOC-6", "source": "VERDICT", "created_ts": 6, "category": "VERDICT", "reason": "O", "context": {"project": "TC2"},
         "rows": [{"identity": {"drawing_no": "T-1", "page_no": 1, "type": "FIT", "tag_no": "", "rect": [1, 1, 9, 9]}, "verdict": "O"}]},
    ]


def test_build_keeps_the_latest_verdict_per_item_and_splits_by_project():
    import verdict_set as V
    sets = V.build(_recs(), built_at=0)
    assert set(sets) == {"QFE", "TC2"}
    q = sets["QFE"]
    assert q["counts"] == {"O": 0, "X": 3, "MISSED": 1} and q["vocs"] == 4        # GENERAL 은 정답지가 아니다
    by = {(i["type"], i["tag_no"]): i for i in q["items"]}
    assert by[("PIT", "T1")]["verdict"] == "X" and by[("PIT", "T1")]["voc_id"] == "VOC-2"   # 나중 것이 이긴다
    assert by[("LIT", "")]["verdict"] == "MISSED" and by[("TI", "T9")]["verdict"] == "X"
    assert sets["TC2"]["counts"] == {"O": 1, "X": 0, "MISSED": 0}


def test_score_matches_by_tag_or_place_and_ignores_removed_rows():
    import verdict_set as V
    vs = V.build(_recs(), built_at=0)["QFE"]
    rows = [{"drawing_no": "D-1", "page_no": 6, "type": "PIT", "tag_no": "T1", "rect": [11, 11, 21, 31]},   # X 인데 다시 섰다
            {"drawing_no": "D-2", "page_no": 7, "type": "LIT", "tag_no": "", "rect": [52, 49, 71, 82]},    # 누락을 읽었다 (자리로)
            {"drawing_no": "D-1", "page_no": 6, "type": "PI", "tag_no": "", "rect": [100, 100, 120, 130], "removed": 1}]  # 지운 행 = 없음
    sc = V.score(rows, vs)
    assert (sc["total"], sc["agree"], sc["pct"]) == (4, 3, 75.0)
    assert sc["X"]["back"] == ["D-1 PIT T1"] and sc["X"]["excluded"] == 2
    assert sc["MISSED"]["found"] == 1 and sc["MISSED"]["still"] == []
    assert "일치 3/4" in V.summary_line(sc) and V.summary_line({}) == "정답지 없음"
    # 자리가 다른 같은 TYPE 은 짝이 아니다
    far = [{"drawing_no": "D-2", "page_no": 7, "type": "LIT", "tag_no": "", "rect": [500, 500, 520, 530]}]
    assert V.score(far, vs)["MISSED"]["found"] == 0


def test_cli_builds_files_from_an_inbox_and_scores_a_result(tmp_path):
    from app import voc
    root = tmp_path / "voc"
    for r in _recs():
        rec = {k: v for k, v in r.items() if k not in ("id", "created_ts")}
        voc.write(rec, root=root)
    out = tmp_path / "verdicts"
    p = subprocess.run([sys.executable, "spike/voc.py", "--inbox", str(root / "inbox"), "--ledger", str(tmp_path / "ledger.json"),
                        "verdicts", "--out", str(out)], cwd=str(ROOT), capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert (out / "QFE.json").is_file() and (out / "TC2.json").is_file()
    q = json.loads((out / "QFE.json").read_text(encoding="utf-8"))
    assert q["counts"]["X"] == 3 and q["counts"]["MISSED"] == 1
    res = tmp_path / "res.json"
    res.write_text(json.dumps({"result": {"rows": [
        {"drawing_no": "D-1", "page_no": 6, "type": "PIT", "tag_no": "T1", "rect": [11, 11, 21, 31]}]}}), encoding="utf-8")
    p = subprocess.run([sys.executable, "spike/verdict_set.py", "score", str(res), str(out / "QFE.json")],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert p.returncode == 0 and "일치 2/4" in p.stdout and "D-1 PIT T1" in p.stdout
    # `list` 는 평가를 숨기고 안내만 한다
    p = subprocess.run([sys.executable, "spike/voc.py", "--inbox", str(root / "inbox"), "--ledger", str(tmp_path / "ledger.json"), "list"],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert "O/X 평가" in p.stdout and p.stdout.count("VOC-") == 3           # 마크업 둘 + 일반 하나만 반영 목록에


def test_harness_reads_the_verdict_file_as_a_reference_not_a_gate():
    src = (ROOT / "spike/regression_3p.py").read_text(encoding="utf-8")
    assert 'verdict_set.verdict_file(proj["name"])' in src and "verdict_set.score(rows" in src
    assert 'CHECK = ("rows", "fingerprint", "qty_sum", "score")' in src        # 게이트 넷 그대로
    assert '"verdict_reference"' in src and "참고 — 게이트가 아닙니다" in src


def test_engine_never_reads_the_verdict_file():
    """정답지는 재는 자이지 규칙이 아니다 — 판정 코드는 VOC 도 정답지도 읽지 않는다."""
    for f in sorted((ROOT / "app" / "engine").glob("*.py")) + [ROOT / "app" / "pipeline.py"]:
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            names = []
            if isinstance(n, ast.Import):
                names = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                names = [n.module or ""] + [a.name for a in n.names]
            for nm in names:
                assert "voc" not in nm.split(".") and "verdict_set" not in nm, (f.name, nm)
        assert "row_verdict" not in f.read_text(encoding="utf-8"), f.name
